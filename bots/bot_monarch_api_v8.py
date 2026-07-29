import os, sqlite3, asyncio, aiohttp, secrets, random, json
from datetime import datetime, timedelta
from dotenv import load_dotenv
import discord
from discord import app_commands, ButtonStyle, Interaction, Embed
from discord.ui import View, Button, Modal, TextInput

load_dotenv()

TOKEN = os.getenv('BOT_MONARCH_API_TOKEN', '')
ASAAS_K = os.getenv('ASAAS_CHAVE_MESTRE', '')
ASAAS_C = os.getenv('ASAAS_CLIENTE_ID', 'cus_190077242')
ASAAS_URL = 'https://www.asaas.com/api/v3'
EMPRESA = 'MONARCH FINANCE LTDA'
COR = 0x6D28D9
COR_SUC = 0x10B981
COR_ERR = 0xEF4444

PLANOS = {
    'basico':      {'nome':'Básico',      'cor':'🟢','cor_hex':0x22C55E,'nivel':1,'arquivo':'bot_basico.py',
                    'precos':{30:8.99,90:24.99,180:47.99,365:89.99},
                    'comandos':10,'recursos':'API Básica · Estoque Infinito · Vendas'},
    'intermediario':{'nome':'Intermediário','cor':'🔵','cor_hex':0x3B82F6,'nivel':2,'arquivo':'bot_intermediario.py',
                    'precos':{30:19.99,90:54.99,180:104.99,365:199.99},
                    'comandos':18,'recursos':'Tudo Básico + Cupons + Relatórios + Carrinho'},
    'vip':         {'nome':'VIP',         'cor':'🟣','cor_hex':0x8B5CF6,'nivel':3,'arquivo':'bot_vip.py',
                    'precos':{30:39.99,90:109.99,180:209.99,365:399.99},
                    'comandos':26,'recursos':'Tudo Intermediário + Personalização + Estatísticas'},
    'premium':     {'nome':'Premium',     'cor':'🟠','cor_hex':0xF59E0B,'nivel':4,'arquivo':'bot_premium.py',
                    'precos':{30:79.99,90:219.99,180:419.99,365:799.99},
                    'comandos':35,'recursos':'TUDO LIBERADO + Moderação + Anti-Raid + IA + Suporte VIP'},
}
HIERARQUIA = ['premium','vip','intermediario','basico']
VALIDADES = [30,90,180,365]

# ==================================================
# 🖥️ SISTEMA DE HOSPEDAGEM AUTOMÁTICA — RENDER
# ==================================================
RENDER_TOKEN = os.getenv('RENDER_API_TOKEN', '')
RENDER_OWNER = os.getenv('RENDER_OWNER_ID', '')
RENDER_API = 'https://api.render.com/v1'
RENDER_HEADERS = lambda: {'Authorization': f'Bearer {RENDER_TOKEN}', 'Accept': 'application/json', 'Content-Type': 'application/json'}

# Cria tabela de serviços Render
db.execute('CREATE TABLE IF NOT EXISTS render_servicos(lid TEXT PRIMARY KEY, service_id TEXT UNIQUE, plano TEXT, uid TEXT, status TEXT, data_criado TEXT)')
db.commit()

async def render_criar_servico(licenca_id: str, plano: str, uid: str, nick: str) -> str:
    """Cria um serviço novo no Render para o bot do cliente"""
    if not RENDER_TOKEN: return ''
    try:
        arquivos = {'basico':'bot_basico.py','intermediario':'bot_intermediario.py','vip':'bot_vip.py','premium':'bot_premium.py'}
        arq = arquivos.get(plano, 'bot_basico.py')
        nome_servico = f'monarch-{plano}-{licenca_id.lower()}'
        async with aiohttp.ClientSession() as s:
            r = await s.post(f'{RENDER_API}/services', headers=RENDER_HEADERS(), json={
                'type': 'web_service',
                'name': nome_servico,
                'ownerId': RENDER_OWNER,
                'repo': 'https://github.com/SEU_USUARIO/MONARCH-BOTS.git',  # ← seu repo com os bots
                'branch': 'main',
                'rootDir': '.',
                'runtime': 'python',
                'buildCommand': 'pip install -r requirements.txt',
                'startCommand': f'python {arq}',
                'envVars': [
                    {'key':'BOT_TOKEN','value':'PREECHER_DEPOIS'},
                    {'key':'LICENCA_ID','value':licenca_id},
                ],
                'plan': 'starter',  # starter = mais barato / upgrade conforme plano
                'region': 'ohio',
                'autoDeploy': 'no'
            }, timeout=30)
            d = await r.json()
            sid = d.get('service',{}).get('id','')
            if sid:
                db.execute('INSERT OR REPLACE INTO render_servicos VALUES(?,?,?,?,?,?)',
                    (licenca_id, sid, plano, str(uid), 'criado', datetime.now().isoformat()))
                db.commit()
            return sid
    except Exception as ex:
        print(f'RENDER CRIAR ERRO: {ex}')
        return ''

async def render_ligar(service_id: str) -> bool:
    """Resume / liga o serviço"""
    if not service_id or not RENDER_TOKEN: return False
    try:
        async with aiohttp.ClientSession() as s:
            r = await s.post(f'{RENDER_API}/services/{service_id}/resume', headers=RENDER_HEADERS(), timeout=15)
            return r.status in (200,201,202)
    except: return False

async def render_desligar(service_id: str) -> bool:
    """Suspend / desliga o serviço"""
    if not service_id or not RENDER_TOKEN: return False
    try:
        async with aiohttp.ClientSession() as s:
            r = await s.post(f'{RENDER_API}/services/{service_id}/suspend', headers=RENDER_HEADERS(), timeout=15)
            return r.status in (200,201,202)
    except: return False

async def render_deletar(service_id: str) -> bool:
    """Deleta serviço (uso admin)"""
    if not service_id or not RENDER_TOKEN: return False
    try:
        async with aiohttp.ClientSession() as s:
            r = await s.delete(f'{RENDER_API}/services/{service_id}', headers=RENDER_HEADERS(), timeout=15)
            return r.status == 204
    except: return False


db = sqlite3.connect('monarch_api_v8.db', check_same_thread=False)
for q in [
    'CREATE TABLE IF NOT EXISTS lojas(gid TEXT PRIMARY KEY, dono TEXT, info_c TEXT, comprar_c TEXT, planos_c TEXT, termos_c TEXT, suporte_c TEXT, status_c TEXT, logs_c TEXT, criada TEXT)',
    'CREATE TABLE IF NOT EXISTS carrinhos(uid TEXT PRIMARY KEY, itens TEXT, atualizado TEXT)',
    'CREATE TABLE IF NOT EXISTS licencas(id TEXT PRIMARY KEY, uid TEXT, nick TEXT, email TEXT, plano TEXT, dias INTEGER, compra TEXT, vencimento TEXT, status TEXT DEFAULT "ativa", api_key TEXT UNIQUE, token_bot TEXT, config TEXT)',
    'CREATE TABLE IF NOT EXISTS clientes(uid TEXT PRIMARY KEY, nick TEXT, email TEXT, gasto REAL DEFAULT 0, compras INTEGER DEFAULT 0, nivel TEXT DEFAULT "basico", cadastro TEXT)',
    'CREATE TABLE IF NOT EXISTS cupons(id INTEGER PRIMARY KEY AUTOINCREMENT, codigo TEXT UNIQUE, tipo TEXT, valor REAL, usos INTEGER DEFAULT 0, max_usos INTEGER DEFAULT 999, ativo INTEGER DEFAULT 1)',
    'CREATE TABLE IF NOT EXISTS pagamentos(id TEXT PRIMARY KEY, uid TEXT, nick TEXT, itens TEXT, total REAL, pago REAL, cupom TEXT, asaas_id TEXT, status TEXT, data TEXT)',
    'CREATE TABLE IF NOT EXISTS logs(id INTEGER PRIMARY KEY AUTOINCREMENT, uid TEXT, nick TEXT, acao TEXT, det TEXT, data TEXT)',
    'CREATE TABLE IF NOT EXISTS avisos(lid TEXT, tipo TEXT, PRIMARY KEY(lid,tipo))',
]: db.execute(q)
db.commit()

def log_(u,n,a,d=''):
    db.execute('INSERT INTO logs(uid,nick,acao,det,data) VALUES(?,?,?,?,?)',(str(u),str(n),a,str(d),datetime.now().isoformat())); db.commit()

HDR = lambda: {'access_token': ASAAS_K, 'Content-Type': 'application/json'}
async def gerar_pix(valor, ref, email='contato@monarch.finance'):
    async with aiohttp.ClientSession() as s:
        r = await s.post(f'{ASAAS_URL}/payments', json={
            'customer': ASAAS_C, 'billingType': 'PIX',
            'value': round(valor,2), 'dueDate': datetime.now().strftime('%Y-%m-%d'),
            'externalReference': ref, 'description': f'{EMPRESA} — {ref}', 'postalService': False
        }, headers=HDR())
        d = await r.json()
        return {'cc':d.get('pixPayload',{}).get('payload',''),'qr':d.get('pixPayload',{}).get('encodedImage',''),'id':d.get('id'),'ref':ref,'valor':valor}

# Carrinho
def gc(uid):
    r = db.execute('SELECT itens FROM carrinhos WHERE uid=?',(str(uid),)).fetchone()
    return json.loads(r[0]) if r else []
def sc(uid,itens):
    db.execute('INSERT OR REPLACE INTO carrinhos VALUES(?,?,?)',(str(uid),json.dumps(itens),datetime.now().isoformat())); db.commit()
def calc(itens, cupom=None):
    if not itens: return 0,0,None,{}
    total = sum(i['preco'] for i in itens)
    niveis = {i['plano']: PLANOS[i['plano']]['nivel'] for i in itens}
    melhor = max(niveis, key=lambda p: niveis[p])
    sv = {}
    for i in itens: sv[i['plano']] = sv.get(i['plano'],0)+i['dias']
    final = total
    if cupom:
        c = db.execute('SELECT tipo,valor FROM cupons WHERE codigo=? AND ativo=1 AND usos<max_usos',(cupom.upper(),)).fetchone()
        if c: final = max(0, total - (c[1] if c[0]=='fixo' else total*c[1]/100))
    return round(total,2), round(final,2), melhor, sv

# ==========================================================
# 🚀 ENTREGA AUTOMÁTICA — GERA LICENÇA + API KEY + CÓDIGO BOT
# ==========================================================
async def entregar_pagamento(ref):
    pg = db.execute('SELECT uid,nick,itens,pago FROM pagamentos WHERE id=? AND status=?',(ref,'PENDENTE')).fetchone()
    if not pg: return
    uid,nick,itens_str,valor = pg
    itens = eval(itens_str)
    _,_,melhor,sv = calc(itens)
    agora = datetime.now()
    lic_ids = []
    for plano, dias in sv.items():
        p = PLANOS[plano]
        venc = agora + timedelta(days=dias)
        lid = secrets.token_hex(5).upper()
        api = 'MONARCH-' + secrets.token_urlsafe(28).upper()
        db.execute('INSERT OR REPLACE INTO licencas VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
            (lid, uid, nick, '', plano, dias, agora.isoformat(), venc.isoformat(), 'ativa', api, '', '{}'))
        lic_ids.append((lid, plano, api, dias))
    cli = db.execute('SELECT gasto,compras FROM clientes WHERE uid=?',(uid,)).fetchone()
    tg = (cli[0] if cli else 0) + valor
    cp = (cli[1] if cli else 0) + 1
    db.execute('INSERT OR REPLACE INTO clientes VALUES(?,?,?,?,?,?,?)',
        (uid, nick, '', tg, cp, melhor, agora.isoformat()))
    db.execute('UPDATE pagamentos SET status=? WHERE id=?',('CONFIRMADO',ref))
    db.commit()
    log_(uid,nick,'PAGAMENTO_OK',f'{ref} R${valor:.2f} → {melhor}')

    # Envia DM com TUDO
    try:
        u = bot.get_user(int(uid)) or await bot.fetch_user(int(uid))
        # 1) Embed principal
        e = Embed(title='👑 PAGAMENTO CONFIRMADO — MONARCH API', color=COR_SUC,
                  description=f'🏆 Plano máximo: **{PLANOS[melhor]["nome"]}**\n💰 Valor: **R${valor:.2f}**'.replace('.',','))
        for lid, plano, api, dias in lic_ids:
            p = PLANOS[plano]
            e.add_field(name=f'{p["cor"]} LICENÇA {lid}',
                value=f'''Plano: **{p["nome"]}**
Dias: **{dias}**
Vence: **{(agora+timedelta(days=dias)).strftime("%d/%m/%Y")}**
🔑 **API KEY:** `{api}`
📄 **Arquivo do bot:** `{p["arquivo"]}`''', inline=False)
        e.set_footer(text=f'100% Legal · Token oficial Discord · {EMPRESA}')
        await u.send(embed=e)

        # 2) Envia CADA arquivo de bot separado
        for lid, plano, api, dias in lic_ids:
            p = PLANOS[plano]
            arq = p['arquivo']
            if os.path.exists(arq):
                cod = open(arq, encoding='utf-8').read()
                # Injeta a licença e API KEY no código do cliente
                cod_cliente = cod.replace('SUA_LICENCA_AQUI', lid)\
                                 .replace('SUA_API_KEY_AQUI', api)\
                                 .replace('SEU_PLANO_AQUI', plano)\
                                 .replace('DIAS_AQUI', str(dias))
                arq_cliente = f'{plano}_{lid}.py'
                with open(f'/tmp/{arq_cliente}','w',encoding='utf-8') as f: f.write(cod_cliente)
                await u.send(
                    content=f'''📦 **ARQUIVO DO SEU BOT {p["nome"]}**

✅ **Como usar:**
1. Acesse: https://discord.com/developers/applications
2. Crie um **New Application** → pegue o **Token** do bot
3. Abra o arquivo, cole o token no final
4. Hospede no Render / Replit / VPS
5. **NUNCA compartilhe seu token ou API key**

📜 Licença: `{lid}`
🔑 API: `{api[:15]}...`
📅 Válido por: {dias} dias''',
                    file=discord.File(f'/tmp/{arq_cliente}', filename=arq_cliente)
                )
        await u.send('✅ **TUDO ENTREGUE!** Qualquer dúvida chame o suporte.')
    except Exception as ex: print('DM ERRO:',ex)

# ==============================
# 🤖 BOT + COMANDOS
# ==============================
intents = discord.Intents.default(); intents.members = True
bot = discord.Client(intents=intents); tree = app_commands.CommandTree(bot)

class MCupom(Modal, title='🎟️ CRIAR CUPOM'):
    def __init__(self): super().__init__()
    self.add_item(TextInput(label='Codigo', required=True))
    self.add_item(TextInput(label='Tipo (fixo/pct)', default='pct'))
    self.add_item(TextInput(label='Valor', default='10'))
    self.add_item(TextInput(label='Max usos', default='999', required=False))
    async def on_submit(self,it):
        cod=self.children[0].value.upper(); tp=self.children[1].value.lower(); vl=float(self.children[2].value); mx=int(self.children[3].value or 999)
        db.execute('INSERT OR REPLACE INTO cupons(codigo,tipo,valor,max_usos) VALUES(?,?,?,?)',(cod,tp,vl,mx)); db.commit()
        await it.response.send_message(f'✅ Cupom `{cod}` criado!', ephemeral=True)

class VPlanos(View):
    def __init__(self):
        super().__init__(timeout=None)
        for chave, p in PLANOS.items():
            for dias in VALIDADES:
                b = Button(label=f'{p["cor"]} {p["nome"]} {dias}d R${p["precos"][dias]:.2f}'.replace('.',','),
                          style=ButtonStyle.green, custom_id=f'add_{chave}_{dias}')
                async def cb(ii, c=chave, d=dias, pp=p):
                    uid=str(ii.user.id); car=gc(uid)
                    car.append({'plano':c,'dias':d,'preco':pp['precos'][d],'nome':pp['nome']})
                    sc(uid,car); log_(ii.user.id,ii.user.display_name,'ADD_CARRINHO',f'{c} {d}d')
                    tot=calc(car)[1]
                    await ii.response.send_message(f'✅ **{pp["nome"]} {d}d**\n🛒 {len(car)} itens · R${tot:.2f}'.replace('.',','), ephemeral=True)
                b.callback = cb; self.add_item(b)
        self.add_item(Button(label='🛒 VER',style=ButtonStyle.blurple,custom_id='ver_c'))
        self.add_item(Button(label='🗑️ LIMPAR',style=ButtonStyle.red,custom_id='limp_c'))

def emb_c(u,itens,cupom=None):
    bruto,final,melhor,sv = calc(itens,cupom)
    if not itens: return Embed(title='🛒 CARRINHO VAZIO',color=COR_AVS)
    txt='\n'.join([f'{PLANOS[i["plano"]]["cor"]} **{i["nome"]} {i["dias"]}d** — R${i["preco"]:.2f}'.replace('.',',') for i in itens])
    svt='\n'.join([f'{PLANOS[p]["cor"]} {PLANOS[p]["nome"]}: **{d} dias**' for p,d in sv.items()])
    e=Embed(title=f'🛒 CARRINHO · {u.display_name.upper()}',color=COR,description=txt)
    e.add_field(name='📅 Validade somada',value=svt or '-',inline=False)
    e.add_field(name='🏆 Bot entregue',value=f'{PLANOS[melhor]["cor"]} **{PLANOS[melhor]["nome"]}**' if melhor else '-',inline=False)
    e.add_field(name='💰 Subtotal',value=f'R${bruto:.2f}'.replace('.',','))
    if cupom:
        c=db.execute('SELECT tipo,valor FROM cupons WHERE codigo=?',(cupom,)).fetchone()
        e.add_field(name=f'🎟️ {cupom}',value=f'-{c[1]}{"%" if c[0]=="pct" else "R$"}'.replace('.',','))
    e.add_field(name='💵 TOTAL',value=f'**R${final:.2f}**'.replace('.',','),inline=False)
    return e

class VCar(View):
    def __init__(self,uid,itens,cupom=None):
        super().__init__(timeout=None); self.uid=str(uid); self.cupom=cupom
        _,self.final,self.melhor,_ = calc(itens,cupom)
        b=Button(label='💳 PAGAR COM PIX',style=ButtonStyle.green)
        async def fim(ii):
            if str(ii.user.id)!=self.uid: return
            if not itens: return await ii.response.send_message('❌ Vazio',ephemeral=True)
            await ii.response.defer(ephemeral=True,thinking=True)
            ref=f'API-{ii.user.id}-{int(datetime.now().timestamp())}'
            email=db.execute('SELECT email FROM clientes WHERE uid=?',(self.uid,)).fetchone()
            email=email[0] if email else f'{self.uid}@monarch.finance'
            pix=await gerar_pix(self.final,ref,email)
            if not pix['cc']: return await ii.followup.send('❌ Falha no pagamento',ephemeral=True)
            db.execute('INSERT OR REPLACE INTO pagamentos VALUES(?,?,?,?,?,?,?,?,?,?)',
                (ref,self.uid,ii.user.display_name,str([i["nome"] for i in itens]),self.final,self.final,self.cupom or '',pix['id'],'PENDENTE',datetime.now().isoformat()))
            db.commit()
            e = Embed(title=f'💳 PIX R${self.final:.2f}'.replace('.',','), color=COR_SUC,
                      description=f'Empresa: **{EMPRESA}**\nRef: `{ref}`\n\n```\n{pix["cc"]}\n```')
            if pix['qr']: e.set_image(url=pix['qr'])
            await ii.followup.send(embed=e, ephemeral=True)
        b.callback = fim; self.add_item(b)
        b2=Button(label='🎟️ CUPOM',style=ButtonStyle.grey)
        async def cup(ii):
            if str(ii.user.id)!=self.uid: return
            m=Modal(title='🎟️ CUPOM'); m.add_item(TextInput(label='Codigo'))
            async def scb(iii):
                cod=m.children[0].value.upper()
                if not db.execute('SELECT 1 FROM cupons WHERE codigo=? AND ativo=1',(cod,)).fetchone():
                    return await iii.response.send_message('❌ Cupom invalido',ephemeral=True)
                await iii.response.edit_message(embed=emb_c(ii.user,itens,cod),view=VCar(ii.user.id,itens,cod))
            m.on_submit=scb; await ii.response.send_modal(m)
        b2.callback=cup; self.add_item(b2)

@tree.command(name='gapi',description='👑 CRIA LOJA AUTOMATICAMENTE')
@app_commands.checks.has_permissions(administrator=True)
async def cmd_gapi(it: Interaction):
    g = it.guild; me = g.me
    if not me.guild_permissions.manage_channels:
        return await it.response.send_message('❌ Preciso GERENCIAR CANAIS',ephemeral=True)
    await it.response.defer(ephemeral=True,thinking=True)
    ow = {g.default_role: discord.PermissionOverwrite(view_channel=True,send_messages=False),
          me: discord.PermissionOverwrite(view_channel=True,manage_channels=True,send_messages=True,embed_links=True)}
    cat = await g.create_category('👑 MONARCH API STORE',overwrites=ow,position=0)
    cs = {}
    for nome in ['📢・informações','🛒・comprar-api','💎・planos','📜・termos','🎫・suporte','📊・status','📋・logs-admin']:
        cs[nome] = await g.create_text_channel(nome,category=cat)
    e = Embed(title='💎 PLANOS OFICIAIS MONARCH API', color=COR)
    for chave, p in PLANOS.items():
        pr = '\n'.join([f'• **{d} dias** — R${p["precos"][d]:.2f}'.replace('.',',') for d in VALIDADES])
        e.add_field(name=f'{p["cor"]} {p["nome"]} ({p["comandos"]} cmd)', value=f'{pr}\n_{p["recursos"]}_', inline=True)
    e.set_footer(text=f'Carrinho inteligente · Estoque infinito · Bots reais · {EMPRESA}')
    await cs['💎・planos'].send(embed=e, view=VPlanos())
    db.execute('INSERT OR REPLACE INTO lojas VALUES(?,?,?,?,?,?,?,?,?,?)',
        (str(g.id),str(it.user.id),str(cs['📢・informações'].id),str(cs['🛒・comprar-api'].id),
         str(cs['💎・planos'].id),str(cs['📜・termos'].id),str(cs['🎫・suporte'].id),
         str(cs['📊・status'].id),datetime.now().isoformat()))
    db.commit()
    await it.followup.send(f'✅ LOJA CRIADA!\n📂 {cat.name}\n✅ {len(cs)} canais')

@bot.event
async def on_interaction(it: Interaction):
    if it.type != discord.InteractionType.component: return
    cid = it.data.get('custom_id','')
    if cid == 'ver_c':
        car = gc(it.user.id)
        await it.response.send_message(embed=emb_c(it.user,car), view=VCar(it.user.id,car), ephemeral=True)
    elif cid == 'limp_c':
        sc(it.user.id,[]); await it.response.send_message('🗑️ Limpo!', ephemeral=True)

# WEBHOOK ASAAS
from aiohttp import web as aw
async def webhook(req):
    try:
        d = await req.json()
        ev = d.get('event',''); ref = d.get('payment',{}).get('externalReference','')
        if ev in ('PAYMENT_RECEIVED','PAYMENT_CONFIRMED') and ref.startswith('API-'):
            await entregar_pagamento(ref)
    except Exception as ex: print('WEBHOOK:',ex)
    return aw.Response()

# AVISOS VENCIMENTO
async def bg():
    await bot.wait_until_ready()
    while True:
        try:
            agora = datetime.now()

            # 🖥️ HOSPEDAGEM RENDER — LIGA/DESLIGA AUTOMÁTICO
            rs = db.execute('SELECT rs.lid, rs.service_id, rs.status, l.status FROM render_servicos rs LEFT JOIN licencas l ON l.id=rs.lid').fetchall()
            for lid, sid, status_render, status_lic in rs:
                if not sid: continue
                deve_ligar = (status_lic == 'ativa')
                if deve_ligar and status_render != 'ligado':
                    if await render_ligar(sid):
                        db.execute('UPDATE render_servicos SET status="ligado" WHERE lid=?',(lid,)); db.commit()
                        print(f'🟢 RENDER LIGADO: {lid}')
                elif not deve_ligar and status_render != 'desligado':
                    if await render_desligar(sid):
                        db.execute('UPDATE render_servicos SET status="desligado" WHERE lid=?',(lid,)); db.commit()
                        print(f'🔴 RENDER DESLIGADO: {lid}')

            for l in db.execute('SELECT id,uid,nick,plano,vencimento,status FROM licencas WHERE status="ativa"').fetchall():
                lid,uid,nick,plano,venc_str,status = l
                venc = datetime.fromisoformat(venc_str)
                dias = (venc - agora).days
                marcar = lambda t: db.execute('INSERT OR IGNORE INTO avisos VALUES(?,?)',(lid,t)) or db.commit()
                avisou = lambda t: db.execute('SELECT 1 FROM avisos WHERE licenca_id=? AND tipo=?',(lid,t)).fetchone()
                try:
                    u = bot.get_user(int(uid)) or await bot.fetch_user(int(uid))
                    if dias <= 0 and not avisou('venceu'):
                        db.execute('UPDATE licencas SET status="expirada" WHERE id=?',(lid,)); db.commit()
                        marcar('venceu'); await u.send(f'🚫 Licença {lid} ({PLANOS[plano]["nome"]}) **EXPIRADA**')
                    elif dias == 7 and not avisou('7d'): marcar('7d'); await u.send(f'⏰ 7 dias: {lid}')
                    elif dias == 3 and not avisou('3d'): marcar('3d'); await u.send(f'⏰ 3 dias: {lid}')
                    elif dias == 1 and not avisou('24h'): marcar('24h'); await u.send(f'⏰ 24h: {lid}')
                except: pass
        except: pass
        await asyncio.sleep(3600)

# ADMIN
@tree.command(name='clientes',description='👥 CLIENTES')
@app_commands.checks.has_permissions(administrator=True)
async def _(it,l:int=10):
    r=db.execute('SELECT nick,nivel,gasto,compras FROM clientes ORDER BY gasto DESC LIMIT ?',(l,)).fetchall()
    txt='\n'.join([f'• **{x[0]}** · {PLANOS[x[1]]["cor"]}{PLANOS[x[1]]["nome"]} · R${x[2]:.2f}'.replace('.',',') for x in r]) or 'Nenhum'
    await it.response.send_message(embed=Embed(title='👥 CLIENTES',color=COR,description=txt),ephemeral=True)

@tree.command(name='licencas',description='📜 LICENÇAS')
@app_commands.checks.has_permissions(administrator=True)
async def _(it,usuario:discord.User=None):
    uid=str(usuario.id) if usuario else '%'
    r=db.execute('SELECT id,nick,plano,dias,vencimento,status FROM licencas WHERE uid LIKE ? ORDER BY vencimento DESC LIMIT 15',(uid,)).fetchall()
    txt='\n'.join([f'• `{x[0]}` · {x[1]} · {PLANOS[x[2]]["cor"]}{PLANOS[x[2]]["nome"]} · {x[3]}d · {x[4][:10]} · **{x[5]}**' for x in r]) or 'Nenhuma'
    await it.response.send_message(embed=Embed(title='📜 LICENÇAS',color=COR,description=txt),ephemeral=True)

@tree.command(name='cupom',description='🎟️ CRIAR CUPOM')
@app_commands.checks.has_permissions(administrator=True)
async def _(it): await it.response.send_modal(MCupom())

@tree.command(name='estatisticas',description='📊 DADOS')
@app_commands.checks.has_permissions(administrator=True)
async def _(it):
    c=db.execute('SELECT COUNT(*) FROM clientes').fetchone()[0]
    l=db.execute('SELECT COUNT(*) FROM licencas').fetchone()[0]
    la=db.execute('SELECT COUNT(*) FROM licencas WHERE status="ativa"').fetchone()[0]
    tg=db.execute('SELECT COALESCE(SUM(gasto),0) FROM clientes').fetchone()[0]
    e=Embed(title='📊 ESTATÍSTICAS',color=COR)
    e.add_field(name='👥 Clientes',value=str(c))
    e.add_field(name='📜 Licenças',value=str(l))
    e.add_field(name='✅ Ativas',value=str(la))
    e.add_field(name='💰 Faturamento',value=f'R${tg:.2f}'.replace('.',','))
    await it.response.send_message(embed=e,ephemeral=True)

@tree.command(name='sync_api',description='🔁 SINCRONIZAR')
@app_commands.checks.has_permissions(administrator=True)
async def _(it):
    await it.response.defer(ephemeral=True); await tree.sync()
    await it.followup.send('✅ Comandos sincronizados!')

@bot.event
async def on_ready():
    await tree.sync()
    asyncio.create_task(bg())
    app = aw.Application()
    app.router.add_post('/webhook/asaas/api', webhook)
    asyncio.create_task(aw._run_app(app, host='0.0.0.0', port=int(os.getenv('PORT_API','10007'))))
    print(f'✅ MONARCH API V8 ONLINE · {bot.user} · {EMPRESA}')

bot.run(TOKEN)
