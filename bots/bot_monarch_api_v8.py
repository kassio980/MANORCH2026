import os, sqlite3, asyncio, aiohttp, secrets, random
from datetime import datetime, timedelta
from dotenv import load_dotenv
import discord
from discord import app_commands, ButtonStyle, Interaction, Embed
from discord.ui import View, Button, Modal, TextInput, Select

load_dotenv()

# ==============================
# 🔐 CONFIGS FIXAS
# ==============================
TOKEN = os.getenv('BOT_MONARCH_API_TOKEN', '')
ASAAS_K = os.getenv('ASAAS_CHAVE_MESTRE', '')
ASAAS_C = os.getenv('ASAAS_CLIENTE_ID', 'cus_190077242')
ASAAS_URL = 'https://www.asaas.com/api/v3'
EMPRESA = 'MONARCH FINANCE LTDA'
COR = 0x6D28D9
COR_SUC = 0x10B981
COR_ERR = 0xEF4444
COR_AVS = 0xF59E0B

# ==============================
# 💎 PLANOS OFICIAIS + VALIDADES
# ==============================
PLANOS = {
    'basico':      {'nome':'Básico',      'cor':'🟢','cor_hex':0x22C55E,'precos':{30:8.99,  90:24.99,  180:47.99,  365:89.99},  'nivel':1},
    'intermediario':{'nome':'Intermediário','cor':'🔵','cor_hex':0x3B82F6,'precos':{30:19.99, 90:54.99,  180:104.99, 365:199.99}, 'nivel':2},
    'vip':         {'nome':'VIP',         'cor':'🟣','cor_hex':0x8B5CF6,'precos':{30:39.99, 90:109.99, 180:209.99, 365:399.99}, 'nivel':3},
    'premium':     {'nome':'Premium',     'cor':'🟠','cor_hex':0xF59E0B,'precos':{30:79.99, 90:219.99, 180:419.99, 365:799.99}, 'nivel':4},
}
HIERARQUIA = ['premium','vip','intermediario','basico']  # Maior → menor
VALIDADES = [30, 90, 180, 365]

# ==============================
# 🗄️ BANCO DE DADOS SEGURO
# ==============================
db = sqlite3.connect('monarch_api_v8.db', check_same_thread=False)
for q in [
    'CREATE TABLE IF NOT EXISTS lojas(gid TEXT PRIMARY KEY, dono TEXT, categoria TEXT, info_canal TEXT, comprar_canal TEXT, planos_canal TEXT, termos_canal TEXT, suporte_canal TEXT, status_canal TEXT, logs_canal TEXT, criada TEXT)',
    'CREATE TABLE IF NOT EXISTS carrinhos(uid TEXT PRIMARY KEY, itens TEXT, atualizado TEXT)',
    'CREATE TABLE IF NOT EXISTS licencas(id TEXT PRIMARY KEY, uid TEXT, nick TEXT, email TEXT, plano TEXT, validade_dias INTEGER, data_compra TEXT, data_vencimento TEXT, status TEXT DEFAULT "ativa", api_key TEXT UNIQUE, config TEXT)',
    'CREATE TABLE IF NOT EXISTS clientes(uid TEXT PRIMARY KEY, nick TEXT, email TEXT, total_gasto REAL DEFAULT 0, compras INTEGER DEFAULT 0, nivel TEXT DEFAULT "basico", data_cadastro TEXT)',
    'CREATE TABLE IF NOT EXISTS cupons(id INTEGER PRIMARY KEY AUTOINCREMENT, codigo TEXT UNIQUE, tipo TEXT, valor REAL, usos INTEGER DEFAULT 0, max_usos INTEGER DEFAULT 999, ativo INTEGER DEFAULT 1)',
    'CREATE TABLE IF NOT EXISTS pagamentos(id TEXT PRIMARY KEY, uid TEXT, nick TEXT, itens TEXT, valor_total REAL, valor_pago REAL, cupom TEXT, asaas_id TEXT, status TEXT, data TEXT)',
    'CREATE TABLE IF NOT EXISTS logs(id INTEGER PRIMARY KEY AUTOINCREMENT, uid TEXT, nick TEXT, acao TEXT, detalhes TEXT, data TEXT)',
    'CREATE TABLE IF NOT EXISTS avisos_enviados(licenca_id TEXT, tipo TEXT, PRIMARY KEY(licenca_id,tipo))',
]: db.execute(q)
db.commit()

def log(uid, nick, acao, det=''):
    db.execute('INSERT INTO logs(uid,nick,acao,detalhes,data) VALUES(?,?,?,?,?)',(str(uid),str(nick),acao,str(det),datetime.now().isoformat()))
    db.commit()

# ==============================
# 💰 ASAAS — NOME EMPRESA FIXO
# ==============================
HDR = lambda: {'access_token': ASAAS_K, 'Content-Type': 'application/json'}

async def gerar_pix(valor: float, ref: str, email: str = 'contato@monarch.finance'):
    async with aiohttp.ClientSession() as s:
        await s.post(f'{ASAAS_URL}/customers', json={
            'name': EMPRESA, 'cpfCnpj': '00000000000100',
            'email': email, 'company': EMPRESA
        }, headers=HDR())
        r = await s.post(f'{ASAAS_URL}/payments', json={
            'customer': ASAAS_C, 'billingType': 'PIX',
            'value': round(valor,2),
            'dueDate': datetime.now().strftime('%Y-%m-%d'),
            'externalReference': ref,
            'description': f'{EMPRESA} — {ref}',
            'postalService': False
        }, headers=HDR())
        d = await r.json()
        return {
            'cc': d.get('pixPayload',{}).get('payload',''),
            'qr': d.get('pixPayload',{}).get('encodedImage',''),
            'id': d.get('id'),
            'ref': ref,
            'valor': valor
        }

# ==============================
# 🤖 BOT + COMANDOS
# ==============================
intents = discord.Intents.default(); intents.members = True; intents.guilds = True
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

# ==============================
# 🛒 CARRINHO HELPERS
# ==============================
def get_carrinho(uid):
    import json
    r = db.execute('SELECT itens FROM carrinhos WHERE uid=?',(str(uid),)).fetchone()
    return json.loads(r[0]) if r else []

def salvar_carrinho(uid, itens):
    import json
    db.execute('INSERT OR REPLACE INTO carrinhos VALUES(?,?,?)',(str(uid),json.dumps(itens),datetime.now().isoformat()))
    db.commit()

def calcular_carrinho(itens, cupom=None):
    """Retorna (total_bruto, total_final, melhor_plano, validade_somada_por_plano)"""
    if not itens: return 0,0,None,{}
    total = sum(i['preco'] for i in itens)
    # Melhor plano por hierarquia
    niveis = {i['plano']: PLANOS[i['plano']]['nivel'] for i in itens}
    melhor = max(niveis, key=lambda p: niveis[p])
    # Soma validades por plano
    soma_valid = {}
    for i in itens:
        soma_valid[i['plano']] = soma_valid.get(i['plano'],0) + i['dias']
    # Aplica cupom
    final = total
    if cupom:
        c = db.execute('SELECT tipo,valor FROM cupons WHERE codigo=? AND ativo=1 AND usos<max_usos',(cupom.upper(),)).fetchone()
        if c:
            if c[0]=='fixo': final = max(0, total - c[1])
            elif c[0]=='pct': final = total * (1 - c[1]/100)
    return round(total,2), round(final,2), melhor, soma_valid

# ==============================
# 📜 MODAIS
# ==============================
class MCupom(Modal, title='🎟️ CRIAR CUPOM'):
    def __init__(self):
        super().__init__()
        self.add_item(TextInput(label='Código (ex: MONARCH20)', required=True))
        self.add_item(TextInput(label='Tipo: fixo ou pct', default='pct', required=True))
        self.add_item(TextInput(label='Valor (R$ ou %)', default='10', required=True))
        self.add_item(TextInput(label='Máx usos (0=ilimitado)', default='999', required=False))
    async def on_submit(self, it):
        cod = self.children[0].value.upper()
        tp = self.children[1].value.lower()
        vl = float(self.children[2].value)
        mx = int(self.children[3].value or 999)
        db.execute('INSERT OR REPLACE INTO cupons(codigo,tipo,valor,max_usos) VALUES(?,?,?,?)',(cod,tp,vl,mx))
        db.commit()
        log(it.user.id,it.user.display_name,'CRIOU_CUPOM',f'{cod} {tp} {vl}')
        await it.response.send_message(f'✅ Cupom `{cod}` criado!\nTipo: `{tp}` · Valor: `{vl}` · Usos: `{mx}`', ephemeral=True)

# ==============================
# 🖱️ VIEWS
# ==============================
class VPlanos(View):
    def __init__(self):
        super().__init__(timeout=None)
        for chave, p in PLANOS.items():
            for dias in VALIDADES:
                b = Button(label=f'{p["cor"]} {p["nome"]} {dias}d R${p["precos"][dias]:.2f}'.replace('.',','),
                          style=ButtonStyle.green, custom_id=f'add_{chave}_{dias}', row=min(VALIDADES.index(dias),4))
                async def cb(ii, c=chave, d=dias, pp=p):
                    uid = str(ii.user.id)
                    car = get_carrinho(uid)
                    car.append({'plano':c,'dias':d,'preco':pp['precos'][d],'nome':pp['nome']})
                    salvar_carrinho(uid,car)
                    log(ii.user.id,ii.user.display_name,'ADD_CARRINHO',f'{c} {d}d')
                    tot = calcular_carrinho(car)[1]
                    await ii.response.send_message(f'✅ **{pp["nome"]} {dias}d** adicionado!\n🛒 Itens: {len(car)} · Total: R${tot:.2f}'.replace('.',','), ephemeral=True)
                b.callback = cb
                self.add_item(b)
        self.add_item(Button(label='🛒 VER CARRINHO', style=ButtonStyle.blurple, custom_id='ver_car'))
        self.add_item(Button(label='🗑️ LIMPAR', style=ButtonStyle.red, custom_id='limpar_car'))

class VCarrinho(View):
    def __init__(self, uid, itens, cupom=None):
        super().__init__(timeout=None)
        self.uid = str(uid); self.cupom = cupom
        bruto, final, melhor, soma = calcular_carrinho(itens, cupom)
        self.final = final; self.melhor = melhor; self.soma = soma
        b = Button(label='💳 FINALIZAR COMPRA', style=ButtonStyle.green)
        async def fim(ii):
            if str(ii.user.id) != self.uid: return
            if not itens: return await ii.response.send_message('❌ Carrinho vazio', ephemeral=True)
            await ii.response.defer(ephemeral=True, thinking=True)
            ref = f'API-{ii.user.id}-{int(datetime.now().timestamp())}'
            email = db.execute('SELECT email FROM clientes WHERE uid=?',(self.uid,)).fetchone()
            email = email[0] if email else f'{self.uid}@monarch.finance'
            pix = await gerar_pix(self.final, ref, email)
            if not pix['cc']: return await ii.followup.send('❌ Falha ao gerar pagamento', ephemeral=True)
            db.execute('INSERT OR REPLACE INTO pagamentos VALUES(?,?,?,?,?,?,?,?,?,?)',
                (ref,self.uid,ii.user.display_name,str([i['nome'] for i in itens]),bruto,self.final,self.cupom or '',pix['id'],'PENDENTE',datetime.now().isoformat()))
            db.commit()
            e = Embed(title=f'💳 PIX · R${self.final:.2f}'.replace('.',','), color=COR_SUC,
                      description=f'**Empresa:** {EMPRESA}\n**Ref:** `{ref}`\n\n```\n{pix["cc"]}\n```\n\nPague e receba tudo automaticamente.')
            if pix['qr']: e.set_image(url=pix['qr'])
            e.set_footer(text='No extrato: MONARCH FINANCE LTDA')
            await ii.followup.send(embed=e, ephemeral=True)
        b.callback = fim; self.add_item(b)

        b2 = Button(label='🎟️ USAR CUPOM', style=ButtonStyle.grey)
        async def cup(ii):
            if str(ii.user.id) != self.uid: return
            m = Modal(title='🎟️ CUPOM'); m.add_item(TextInput(label='Código'))
            async def sc(iii):
                cod = m.children[0].value.upper()
                c = db.execute('SELECT tipo,valor FROM cupons WHERE codigo=? AND ativo=1 AND usos<max_usos',(cod,)).fetchone()
                if not c: return await iii.response.send_message('❌ Cupom inválido', ephemeral=True)
                nv = VCarrinho(ii.user.id, itens, cod)
                e2 = _embed_carrinho(ii.user, itens, cod)
                await iii.response.edit_message(embed=e2, view=nv)
            m.on_submit = sc; await ii.response.send_modal(m)
        b2.callback = cup; self.add_item(b2)

def _embed_carrinho(user, itens, cupom=None):
    bruto, final, melhor, soma = calcular_carrinho(itens, cupom)
    if not itens: return Embed(title='🛒 CARRINHO VAZIO', color=COR_AVS)
    txt = '\n'.join([f'{PLANOS[i["plano"]]["cor"]} **{i["nome"]} {i["dias"]}d** — R${i["preco"]:.2f}'.replace('.',',') for i in itens])
    soma_txt = '\n'.join([f'{PLANOS[p]["cor"]} {PLANOS[p]["nome"]}: **{d} dias**' for p,d in soma.items()])
    e = Embed(title=f'🛒 CARRINHO DE {user.display_name.upper()}', color=COR, description=txt)
    e.add_field(name='📅 Validade acumulada', value=soma_txt or '-', inline=False)
    e.add_field(name='🏆 Plano entregue', value=f'{PLANOS[melhor]["cor"]} **{PLANOS[melhor]["nome"]}**' if melhor else '-', inline=False)
    e.add_field(name='💰 Subtotal', value=f'R${bruto:.2f}'.replace('.',','))
    if cupom:
        c = db.execute('SELECT tipo,valor FROM cupons WHERE codigo=?',(cupom,)).fetchone()
        e.add_field(name=f'🎟️ Cupom {cupom}', value=f'-{c[1]}{"%" if c[0]=="pct" else "R$"}'.replace('.',','))
    e.add_field(name='💵 TOTAL A PAGAR', value=f'**R${final:.2f}**'.replace('.',','), inline=False)
    e.set_footer(text=EMPRESA)
    return e

# ==============================
# 🎯 /gapi — CRIA LOJA AUTOMÁTICA
# ==============================
@tree.command(name='gapi', description='👑 CRIA LOJA MONARCH API AUTOMATICAMENTE')
@app_commands.checks.has_permissions(administrator=True)
async def cmd_gapi(it: Interaction):
    g = it.guild; me = g.me
    if not me.guild_permissions.manage_channels or not me.guild_permissions.manage_roles:
        return await it.response.send_message('❌ Preciso de permissões: GERENCIAR CANAIS + CARGOS', ephemeral=True)
    await it.response.defer(ephemeral=True, thinking=True)

    overwrites = {
        g.default_role: discord.PermissionOverwrite(view_channel=True, send_messages=False, read_messages=True),
        me: discord.PermissionOverwrite(view_channel=True, manage_channels=True, send_messages=True, embed_links=True)
    }
    cat = await g.create_category('👑 MONARCH API STORE', overwrites=overwrites, position=0)
    canais = {}
    for nome, tp, desc in [
        ('📢・informações','text','Tudo sobre a Monarch API'),
        ('🛒・comprar-api','text','Compre sua licença aqui'),
        ('💎・planos','text','Todos os planos e valores'),
        ('📜・termos','text','Termos de uso'),
        ('🎫・suporte','text','Fale com a equipe'),
        ('📊・status','text','Status das licenças'),
        ('📋・logs-admin','text','Logs do sistema'),
    ]:
        ch = await g.create_text_channel(nome, category=cat, topic=desc)
        canais[nome] = ch

    # Envia painel em 💎・planos
    e = Embed(title='💎 PLANOS OFICIAIS MONARCH API V8', color=COR,
              description='Escolha abaixo o plano + validade para adicionar ao carrinho.')
    for chave, p in PLANOS.items():
        pr = '\n'.join([f'• **{d} dias** — R${p["precos"][d]:.2f}'.replace('.',',') for d in VALIDADES])
        e.add_field(name=f'{p["cor"]} {p["nome"]}', value=pr, inline=True)
    e.set_footer(text=f'Carrinho inteligente • Soma validades • Melhor plano automático • {EMPRESA}')
    await canais['💎・planos'].send(embed=e, view=VPlanos())

    # Envia painel em 🛒・comprar-api
    e2 = Embed(title='🛒 COMO COMPRAR', color=COR,
               description='1. Vá em 💎・planos\n2. Clique no botão do plano que quer\n3. Clique em VER CARRINHO\n4. Finalize o Pix\n5. Tudo chega automaticamente na DM')
    await canais['🛒・comprar-api'].send(embed=e2)

    # Salva loja
    db.execute('INSERT OR REPLACE INTO lojas VALUES(?,?,?,?,?,?,?,?,?,?,?)',
        (str(g.id), str(it.user.id), str(cat.id),
         str(canais['📢・informações'].id), str(canais['🛒・comprar-api'].id),
         str(canais['💎・planos'].id), str(canais['📜・termos'].id),
         str(canais['🎫・suporte'].id), str(canais['📊・status'].id),
         datetime.now().isoformat()))
    db.commit()
    log(it.user.id,it.user.display_name,'CRIOU_LOJA',g.name)
    await it.followup.send(f'✅ LOJA CRIADA!\n\n📂 Categoria: `{cat.name}`\n✅ {len(canais)} canais criados\n✅ Painel de planos enviado\n✅ Tudo funcional!')

# ==============================
# 📦 HANDLER BOTÕES GLOBAIS
# ==============================
@bot.event
async def on_interaction(it: Interaction):
    if it.type != discord.InteractionType.component: return
    cid = it.data.get('custom_id','')
    if cid == 'ver_car':
        car = get_carrinho(it.user.id)
        await it.response.send_message(embed=_embed_carrinho(it.user,car), view=VCarrinho(it.user.id,car), ephemeral=True)
    elif cid == 'limpar_car':
        salvar_carrinho(it.user.id,[])
        await it.response.send_message('🗑️ Carrinho limpo!', ephemeral=True)

# ==============================
# 🔄 WEBHOOK ASAAS — CONFIRMA PAGAMENTO E ENTREGA TUDO
# ==============================
from aiohttp import web as aw
async def webhook_asaas(req):
    try:
        d = await r.json() if False else await req.json()
        ev = d.get('event',''); ref = d.get('payment',{}).get('externalReference','')
        if ev not in ('PAYMENT_RECEIVED','PAYMENT_CONFIRMED') or not ref.startswith('API-'):
            return aw.Response()
        pg = db.execute('SELECT uid,nick,itens,valor_pago FROM pagamentos WHERE id=? AND status=?',(ref,'PENDENTE')).fetchone()
        if not pg: return aw.Response()
        uid, nick, itens_str, valor = pg
        import json
        itens = eval(itens_str)
        bruto, final, melhor, soma_valid = calcular_carrinho(eval(itens_str))
        agora = datetime.now()
        lic_ids = []
        # Cria licença por plano com validade somada
        for plano, dias in soma_valid.items():
            venc = agora + timedelta(days=dias)
            lid = secrets.token_hex(6).upper()
            api = 'MONARCH-' + secrets.token_urlsafe(24).upper()
            db.execute('INSERT OR REPLACE INTO licencas VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                (lid, uid, nick, '', plano, dias, agora.isoformat(), venc.isoformat(), 'ativa', api, '{}'))
            lic_ids.append(lid)
        # Atualiza cliente
        cli = db.execute('SELECT total_gasto,compras FROM clientes WHERE uid=?',(uid,)).fetchone()
        tg = (cli[0] if cli else 0) + valor
        cp = (cli[1] if cli else 0) + 1
        db.execute('INSERT OR REPLACE INTO clientes VALUES(?,?,?,?,?,?,?)',
            (uid, nick, '', tg, cp, melhor, agora.isoformat()))
        db.execute('UPDATE pagamentos SET status=? WHERE id=?',('CONFIRMADO',ref))
        db.commit()
        log(uid,nick,'PAGAMENTO_OK',f'{ref} R${valor:.2f} → {melhor}')
        # Envia DM
        try:
            u = bot.get_user(int(uid)) or await bot.fetch_user(int(uid))
            e = Embed(title='👑 MONARCH API — PAGAMENTO CONFIRMADO', color=COR_SUC,
                      description=f'Sua licença foi criada automaticamente!\n\n🏆 Plano: **{PLANOS[melhor]["nome"]}**\n💰 Valor: **R${valor:.2f}**'.replace('.',','))
            for lid in lic_ids:
                l = db.execute('SELECT plano,validade_dias,data_vencimento,api_key FROM licencas WHERE id=?',(lid,)).fetchone()
                e.add_field(name=f'📜 LICENÇA {lid}',
                    value=f'Plano: {PLANOS[l[0]]["nome"]}\nDias: {l[1]}\nVence: {l[2][:10]}\n🔑 API: `{l[3]}`', inline=False)
            e.set_footer(text=EMPRESA)
            await u.send(embed=e)
        except: pass
    except Exception as ex: print('WEBHOOK ASAAS:',ex)
    return aw.Response()

# ==============================
# ⏰ TAREFA AUTOMÁTICA — VENCIMENTOS + AVISOS
# ==============================
async def tarefa_background():
    await bot.wait_until_ready()
    while True:
        try:
            agora = datetime.now()
            for l in db.execute('SELECT id,uid,nick,plano,data_vencimento,status FROM licencas WHERE status="ativa"').fetchall():
                lid, uid, nick, plano, venc_str, status = l
                venc = datetime.fromisoformat(venc_str)
                dias = (venc - agora).days
                marcar = lambda t: db.execute('INSERT OR IGNORE INTO avisos_enviados VALUES(?,?)',(lid,t)) or db.commit()
                avisou = lambda t: db.execute('SELECT 1 FROM avisos_enviados WHERE licenca_id=? AND tipo=?',(lid,t)).fetchone()
                try:
                    u = bot.get_user(int(uid)) or await bot.fetch_user(int(uid))
                    if dias <= 0 and not avisou('venceu'):
                        db.execute('UPDATE licencas SET status="expirada" WHERE id=?',(lid,)); db.commit()
                        marcar('venceu'); log(uid,nick,'LICENCA_EXPIROU',lid)
                        await u.send(f'🚫 **Licença {lid} EXPIRADA**\nPlano {PLANOS[plano]["nome"]} acabou. Use /renovar para reativar.')
                    elif dias == 7 and not avisou('7d'):
                        marcar('7d'); await u.send(f'⏰ **7 dias para expirar** sua licença {lid} ({PLANOS[plano]["nome"]})')
                    elif dias == 3 and not avisou('3d'):
                        marcar('3d'); await u.send(f'⏰ **3 dias para expirar** sua licença {lid}')
                    elif dias == 1 and not avisou('24h'):
                        marcar('24h'); await u.send(f'⏰ **24h para expirar** sua licença {lid}!')
                except: pass
        except: pass
        await asyncio.sleep(3600)  # Checa a cada 1 hora

# ==============================
# 👮 COMANDOS ADMIN
# ==============================
@tree.command(name='vapi', description='⚙️ GERENCIAR PLANOS (ADM)')
@app_commands.checks.has_permissions(administrator=True)
async def _(it): await it.response.send_message('⚙️ Em construção — use os outros comandos admin', ephemeral=True)

@tree.command(name='clientes', description='👥 VER CLIENTES (ADM)')
@app_commands.checks.has_permissions(administrator=True)
async def _(it, limite: int = 10):
    r = db.execute('SELECT nick,nivel,total_gasto,compras FROM clientes ORDER BY total_gasto DESC LIMIT ?',(limite,)).fetchall()
    txt = '\n'.join([f'• **{x[0]}** · {PLANOS[x[1]]["cor"]}{PLANOS[x[1]]["nome"]} · R${x[2]:.2f} · {x[3]} compras'.replace('.',',') for x in r]) or 'Nenhum'
    await it.response.send_message(embed=Embed(title='👥 CLIENTES',color=COR,description=txt), ephemeral=True)

@tree.command(name='licencas', description='📜 GERENCIAR LICENÇAS (ADM)')
@app_commands.checks.has_permissions(administrator=True)
async def _(it, usuario: discord.User = None):
    uid = str(usuario.id) if usuario else '%'
    r = db.execute('SELECT id,nick,plano,validade_dias,data_vencimento,status FROM licencas WHERE uid LIKE ? ORDER BY data_vencimento DESC LIMIT 15',(uid,)).fetchall()
    txt = '\n'.join([f'• `{x[0]}` · **{x[1]}** · {PLANOS[x[2]]["cor"]}{PLANOS[x[2]]["nome"]} · {x[3]}d · Vence: {x[4][:10]} · **{x[5]}**' for x in r]) or 'Nenhuma'
    await it.response.send_message(embed=Embed(title='📜 LICENÇAS',color=COR,description=txt), ephemeral=True)

@tree.command(name='logs', description='📋 HISTÓRICO (ADM)')
@app_commands.checks.has_permissions(administrator=True)
async def _(it, limite: int = 15):
    r = db.execute('SELECT nick,acao,detalhes,data FROM logs ORDER BY id DESC LIMIT ?',(limite,)).fetchall()
    txt = '\n'.join([f'• **{x[0]}** · {x[1]} · {x[2]}' for x in r]) or 'Nenhum'
    await it.response.send_message(embed=Embed(title='📋 LOGS',color=COR,description=txt), ephemeral=True)

@tree.command(name='estatisticas', description='📊 DADOS DA PLATAFORMA (ADM)')
@app_commands.checks.has_permissions(administrator=True)
async def _(it):
    c = db.execute('SELECT COUNT(*) FROM clientes').fetchone()[0]
    l = db.execute('SELECT COUNT(*) FROM licencas').fetchone()[0]
    la = db.execute('SELECT COUNT(*) FROM licencas WHERE status="ativa"').fetchone()[0]
    tg = db.execute('SELECT COALESCE(SUM(total_gasto),0) FROM clientes').fetchone()[0]
    e = Embed(title='📊 ESTATÍSTICAS MONARCH API V8', color=COR)
    e.add_field(name='👥 Clientes', value=str(c))
    e.add_field(name='📜 Licenças totais', value=str(l))
    e.add_field(name='✅ Ativas', value=str(la))
    e.add_field(name='💰 Faturamento total', value=f'R${tg:.2f}'.replace('.',','))
    await it.response.send_message(embed=e, ephemeral=True)

@tree.command(name='cupom', description='🎟️ CRIAR CUPOM (ADM)')
@app_commands.checks.has_permissions(administrator=True)
async def _(it): await it.response.send_modal(MCupom())

@tree.command(name='sync_api', description='🔁 ATUALIZA COMANDOS NO DISCORD')
@app_commands.checks.has_permissions(administrator=True)
async def _(it):
    await it.response.defer(ephemeral=True)
    await tree.sync()
    await it.followup.send('✅ Comandos sincronizados!')

# ==============================
# 🚀 INICIAR TUDO
# ==============================
@bot.event
async def on_ready():
    await tree.sync()
    asyncio.create_task(tarefa_background())
    app = aw.Application()
    app.router.add_post('/webhook/asaas/api', webhook_asaas)
    asyncio.create_task(aw._run_app(app, host='0.0.0.0', port=int(os.getenv('PORT_API','10007'))))
    print(f"""
╔══════════════════════════════════════════╗
║  👑 MONARCH API V8 — ONLINE               ║
║  🤖 Bot: {bot.user}                        ║
║  🏢 {EMPRESA}                             ║
║  💎 4 Planos · 🛒 Carrinho · 📜 Licenças  ║
║  🔔 Avisos automáticos · 🔄 Renovação     ║
╚══════════════════════════════════════════╝""")

bot.run(TOKEN)
