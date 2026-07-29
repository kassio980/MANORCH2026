# ==================================================
# 🟣 BOT VIP — MONARCH API V8
# 📜 LICENÇA: SUA_LICENCA_AQUI | 🔑 API: SUA_API_KEY_AQUI
# 📅 DIAS: DIAS_AQUI | 🖥️ Render auto on/off
# ✅ TUDO INTERMEDIÁRIO + PERSONALIZAÇÃO + ESTATÍSTICAS + BACKUP
# ✅ 💰 NOVO: DEPÓSITO PIX + SAQUE COM TAXAS AUTOMÁTICAS
# ==================================================
import os, sqlite3, aiohttp, json, shutil
from datetime import datetime, timedelta
from dotenv import load_dotenv
import discord
from discord import app_commands, Interaction, Embed, ButtonStyle
from discord.ui import View, Button, Modal, TextInput

load_dotenv()
TOKEN = os.getenv('BOT_TOKEN','')

# DADOS INJETADOS
LICENCA='SUA_LICENCA_AQUI'; API_KEY='SUA_API_KEY_AQUI'; DIAS=int('DIAS_AQUI')
EMPRESA='MONARCH FINANCE LTDA'; COR=0x8B5CF6
API_URL='https://api.monarch.finance/v1'
ASAAS_WEBHOOK=f'{API_URL}/asaas/cliente'

# ========== CONFIG TAXAS ==========
TAXA_SAQUE_PCT  = 5.0    # 5%
TAXA_SAQUE_FIXA = 2.00   # R$ 2,00 fixo
SAQUE_MINIMO    = 10.00  # R$ 10,00

# BANCO
db = sqlite3.connect('vip.db', check_same_thread=False)
for q in [
    'CREATE TABLE IF NOT EXISTS produtos(id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT UNIQUE, preco REAL, estoque INTEGER DEFAULT -1, cat TEXT, desc TEXT)',
    'CREATE TABLE IF NOT EXISTS vendas(id INTEGER PRIMARY KEY AUTOINCREMENT, produto TEXT, qtd INTEGER, total REAL, cliente_uid TEXT, cliente_nome TEXT, cupom TEXT, data TEXT)',
    'CREATE TABLE IF NOT EXISTS cupons(codigo TEXT PRIMARY KEY, tipo TEXT, valor REAL, usos INTEGER DEFAULT 0, max_usos INTEGER DEFAULT 999, ativo INTEGER DEFAULT 1)',
    'CREATE TABLE IF NOT EXISTS carrinhos(uid TEXT PRIMARY KEY, itens TEXT)',
    'CREATE TABLE IF NOT EXISTS clientes(uid TEXT PRIMARY KEY, nick TEXT UNIQUE, saldo REAL DEFAULT 0, compras INTEGER DEFAULT 0, gasto REAL DEFAULT 0, primeiro TEXT)',
    'CREATE TABLE IF NOT EXISTS transacoes(id INTEGER PRIMARY KEY AUTOINCREMENT, uid TEXT, tipo TEXT, valor REAL, taxa REAL, status TEXT, ref TEXT, data TEXT)',
    'CREATE TABLE IF NOT EXISTS tickets(id INTEGER PRIMARY KEY AUTOINCREMENT, uid TEXT, nick TEXT, assunto TEXT, status TEXT, data TEXT)',
    'CREATE TABLE IF NOT EXISTS warns(id INTEGER PRIMARY KEY AUTOINCREMENT, uid TEXT, nick TEXT, motivo TEXT, mod TEXT, data TEXT)',
    'CREATE TABLE IF NOT EXISTS cfg(k TEXT PRIMARY KEY, v TEXT)']: db.execute(q)
db.commit()

async def api_post(path, data):
    """Envia dados para a API central (taxas, transações, etc)"""
    try:
        async with aiohttp.ClientSession() as s:
            await s.post(f'{API_URL}{path}', json={**data,'licenca':LICENCA,'api_key':API_KEY}, headers={'X-API-Key':API_KEY}, timeout=8)
    except: pass

async def lic_ativa():
    try:
        async with aiohttp.ClientSession() as s:
            r=await s.get(f'{API_URL}/licenca/{LICENCA}',headers={'X-API-Key':API_KEY},timeout=6)
            return (await r.json()).get('status')=='ativa'
    except: return True

# Estoque infinito
def add_p(n,p,e=-1,c='Geral',d=''): db.execute('INSERT OR REPLACE INTO produtos(nome,preco,estoque,cat,desc) VALUES(?,?,?,?,?)',(n.lower(),float(p),e,c,d)); db.commit()
def get_p(n): return db.execute('SELECT * FROM produtos WHERE nome=?',(n.lower(),)).fetchone()
def list_p(): return db.execute('SELECT nome,preco,estoque,cat FROM produtos').fetchall()
def saldo(uid): return db.execute('SELECT COALESCE(saldo,0) FROM clientes WHERE uid=?',(str(uid),)).fetchone()[0] or 0
def add_saldo(uid, valor, nick=''):
    db.execute('INSERT OR REPLACE INTO clientes VALUES(?,?,COALESCE((SELECT saldo FROM clientes WHERE uid=?),0)+?,COALESCE((SELECT compras FROM clientes WHERE uid=?),0),COALESCE((SELECT gasto FROM clientes WHERE uid=?),0),?)',
        (str(uid),nick or uid,str(uid),float(valor),str(uid),str(uid),datetime.now().isoformat()))
    db.commit()
def sub_saldo(uid, valor):
    db.execute('UPDATE clientes SET saldo=saldo-? WHERE uid=?',(float(valor),str(uid))); db.commit()

def vender(n,q=1,uid='0',nick='Anônimo',cupom=None,usar_saldo=False):
    p=get_p(n)
    if not p: return False,'Não existe'
    if p[3]>=0 and p[3]<q: return False,'Sem estoque'
    tot=round(p[2]*q,2)
    if cupom:
        c=db.execute('SELECT tipo,valor FROM cupons WHERE codigo=? AND ativo=1 AND usos<max_usos',(cupom.upper(),)).fetchone()
        if c: tot=max(0,tot-(c[1] if c[0]=='fixo' else tot*c[1]/100)); db.execute('UPDATE cupons SET usos=usos+1 WHERE codigo=?',(cupom.upper(),))
    if usar_saldo:
        if saldo(uid)<tot: return False,f'Saldo insuficiente (R${saldo(uid):.2f})'.replace('.',',')
        sub_saldo(uid,tot)
    if p[3]>0: db.execute('UPDATE produtos SET estoque=estoque-? WHERE nome=?',(q,n.lower()))
    db.execute('INSERT INTO vendas VALUES(NULL,?,?,?,?,?,?,?)',(n,q,tot,str(uid),nick,cupom or '',datetime.now().isoformat()))
    db.execute('INSERT OR REPLACE INTO clientes VALUES(?,?,COALESCE((SELECT saldo FROM clientes WHERE uid=?),0),COALESCE((SELECT compras FROM clientes WHERE uid=?),0)+1,COALESCE((SELECT gasto FROM clientes WHERE uid=?),0)+?,COALESCE((SELECT primeiro FROM clientes WHERE uid=?),?))',
        (str(uid),nick,str(uid),str(uid),str(uid),tot,str(uid),datetime.now().isoformat()))
    db.commit()
    return True,f'R${tot:.2f}'.replace('.',',')

def gc(u): r=db.execute('SELECT itens FROM carrinhos WHERE uid=?',(str(u),)).fetchone(); return json.loads(r[0]) if r else []
def sc(u,i): db.execute('INSERT OR REPLACE INTO carrinhos VALUES(?,?)',(str(u),json.dumps(i))); db.commit()
def cc(i,cupom=None):
    if not i: return 0,0
    t=sum(x['preco']*x['qtd'] for x in i); f=t
    if cupom:
        c=db.execute('SELECT tipo,valor FROM cupons WHERE codigo=? AND ativo=1 AND usos<max_usos',(cupom.upper(),)).fetchone()
        if c: f=max(0,t-(c[1] if c[0]=='fixo' else t*c[1]/100))
    return round(t,2),round(f,2)

# ========== GERAR PIX DEPÓSITO ==========
async def gerar_pix_deposito(valor, uid, nick):
    ref=f'DEP-{uid}-{int(datetime.now().timestamp())}'
    try:
        async with aiohttp.ClientSession() as s:
            r=await s.post(f'{API_URL}/pix/gerar', json={'valor':round(valor,2),'ref':ref,'uid':uid,'nick':nick,'licenca':LICENCA}, headers={'X-API-Key':API_KEY}, timeout=10)
            d=await r.json()
            return {'cc':d.get('pix',''),'qr':d.get('qr',''),'ref':ref,'valor':valor}
    except: return None

intents=discord.Intents.default(); intents.message_content=True; intents.members=True
bot=discord.Client(intents=intents); tree=app_commands.CommandTree(bot)

# ---------- INFO ----------
@tree.command(name='info',description='ℹ️ Dados do bot')
async def _(it):
    if not await lic_ativa(): return await it.response.send_message('🚫 Licença expirada',ephemeral=True)
    e=Embed(title='ℹ️ BOT VIP',color=COR)
    e.add_field(name='Licença',value=f'`{LICENCA}`')
    e.add_field(name='Plano',value=f'🟣 VIP ({DIAS} dias)')
    e.add_field(name='Estoque',value='♾️ Infinito')
    e.add_field(name='💰 Sistema',value='Depósito + Saque com taxas')
    await it.response.send_message(embed=e,ephemeral=True)

# ---------- PRODUTOS / VENDAS / CARRINHO / CUPONS ----------
@tree.command(name='produto_add')
@app_commands.checks.has_permissions(administrator=True)
async def _(it,nome:str,preco:float,estoque:int=-1,categoria:str='Geral',desc:str=''):
    add_p(nome,preco,estoque,categoria,desc)
    await it.response.send_message(f'✅ {nome} · R${preco:.2f}'.replace('.',','),ephemeral=True)

@tree.command(name='estoque')
async def _(it):
    r=list_p()
    if not r: return await it.response.send_message('📭 Vazio',ephemeral=True)
    txt='\n'.join([f'• **{x[0]}** · R${x[1]:.2f} · {"♾️" if x[2]==-1 else x[2]}'.replace('.',',') for x in r])
    await it.response.send_message(embed=Embed(title='📊 ESTOQUE',color=COR,description=txt),ephemeral=True)

@tree.command(name='vender')
async def _(it,produto:str,qtd:int=1,cliente:discord.User=None,cupom:str='',usar_saldo:bool=False):
    u=cliente or it.user
    ok,m=vender(produto,qtd,str(u.id),u.display_name,cupom or None,usar_saldo)
    await it.response.send_message(f'{"✅" if ok else "❌"} {m}',ephemeral=True)

@tree.command(name='saldo')
async def _(it,usuario:discord.User=None):
    u=usuario or it.user
    await it.response.send_message(f'💰 **Saldo de {u.display_name}:** R${saldo(u.id):.2f}'.replace('.',','),ephemeral=True)

@tree.command(name='carrinho_add')
async def _(it,produto:str,qtd:int=1):
    p=get_p(produto)
    if not p: return await it.response.send_message('❌ Não existe',ephemeral=True)
    c=gc(it.user.id); c.append({'nome':p[1],'preco':p[2],'qtd':qtd}); sc(it.user.id,c)
    await it.response.send_message(f'✅ Adicionado · Total: R${cc(c)[1]:.2f}'.replace('.',','),ephemeral=True)

@tree.command(name='carrinho')
async def _(it):
    c=gc(it.user.id); b,f=cc(c)
    if not c: return await it.response.send_message('🛒 Vazio',ephemeral=True)
    txt='\n'.join([f'• {i["nome"]} x{i["qtd"]}' for i in c])
    await it.response.send_message(embed=Embed(title='🛒 CARRINHO',color=COR,description=f'{txt}\n\n💵 **R${f:.2f}**'.replace('.',',')),ephemeral=True)

@tree.command(name='finalizar')
async def _(it,cupom:str='',usar_saldo:bool=True):
    c=gc(it.user.id)
    if not c: return await it.response.send_message('❌ Vazio',ephemeral=True)
    b,f=cc(c,cupom or None)
    for i in c: vender(i['nome'],i['qtd'],str(it.user.id),it.user.display_name,cupom or None,usar_saldo)
    sc(it.user.id,[])
    await it.response.send_message(f'✅ Pago R${f:.2f}'.replace('.',','),ephemeral=True)

class MC(Modal,title='🎟️ CUPOM'):
    def __init__(self): super().__init__()
    self.add_item(TextInput(label='Código')); self.add_item(TextInput(label='Tipo fixo/pct',default='pct'))
    self.add_item(TextInput(label='Valor',default='10')); self.add_item(TextInput(label='Max usos',default='999',required=False))
    async def on_submit(self,it):
        cod=self.children[0].value.upper(); tp=self.children[1].value.lower(); vl=float(self.children[2].value); mx=int(self.children[3].value or 999)
        db.execute('INSERT OR REPLACE INTO cupons VALUES(?,?,?,0,?,1)',(cod,tp,vl,mx)); db.commit()
        await it.response.send_message(f'✅ {cod}',ephemeral=True)

@tree.command(name='cupom')
@app_commands.checks.has_permissions(administrator=True)
async def _(it): await it.response.send_modal(MC())

@tree.command(name='relatorio')
async def _(it,periodo:str='dia'):
    dias={'dia':1,'semana':7,'mes':30}.get(periodo,1); d=datetime.now()-timedelta(days=dias)
    t=db.execute('SELECT COALESCE(SUM(total),0),COUNT(*) FROM vendas WHERE data>?',(d.isoformat(),)).fetchone()
    e=Embed(title=f'📊 RELATÓRIO {periodo}',color=COR)
    e.add_field(name='Faturamento',value=f'R${t[0]:.2f}'.replace('.',','))
    e.add_field(name='Vendas',value=str(t[1]))
    await it.response.send_message(embed=e,ephemeral=True)

@tree.command(name='clientes')
@app_commands.checks.has_permissions(administrator=True)
async def _(it,l:int=10):
    r=db.execute('SELECT nick,compras,gasto,saldo FROM clientes ORDER BY gasto DESC LIMIT ?',(l,)).fetchall()
    txt='\n'.join([f'• {x[0]} · {x[1]}c · G:R${x[2]:.2f} · S:R${x[3]:.2f}'.replace('.',',') for x in r]) or 'Nenhum'
    await it.response.send_message(embed=Embed(title='👥 CLIENTES',color=COR,description=txt),ephemeral=True)

# ==================================================
# 💰 NOVO VIP: DEPÓSITO + SAQUE COM TAXAS AUTOMÁTICAS
# ==================================================
@tree.command(name='depositar',description='💰 Gerar Pix para depositar saldo')
async def _(it, valor: float):
    if valor < 5: return await it.response.send_message('❌ Mínimo R$5,00',ephemeral=True)
    await it.response.defer(ephemeral=True,thinking=True)
    pix = await gerar_pix_deposito(valor, str(it.user.id), it.user.display_name)
    if not pix or not pix['cc']: return await it.followup.send('❌ Falha ao gerar Pix',ephemeral=True)
    db.execute('INSERT INTO transacoes VALUES(NULL,?,?,0,?,?,?,?)',(str(it.user.id),'DEPOSITO',valor,'PENDENTE',pix['ref'],datetime.now().isoformat()))
    db.commit()
    e=Embed(title=f'💰 DEPÓSITO · R${valor:.2f}'.replace('.',','),color=0x22C55E,
        description=f'Copie o Pix abaixo e pague.\n\n**Ref:** `{pix["ref"]}`\n\n```\n{pix["cc"]}\n```\n\n✅ Ao pagar, o saldo cai automaticamente.')
    if pix['qr']: e.set_image(url=pix['qr'])
    await it.followup.send(embed=e,ephemeral=True)

@tree.command(name='sacar',description='💸 Solicitar saque (taxa aplicada automaticamente)')
async def _(it, valor: float, chave_pix: str):
    if valor < SAQUE_MINIMO:
        return await it.response.send_message(f'❌ Saque mínimo R${SAQUE_MINIMO:.2f}'.replace('.',','),ephemeral=True)
    if saldo(it.user.id) < valor:
        return await it.response.send_message(f'❌ Saldo insuficiente (R${saldo(it.user.id):.2f})'.replace('.',','),ephemeral=True)

    # Calcula taxas
    taxa_pct  = round(valor * TAXA_SAQUE_PCT / 100, 2)
    taxa_total = round(taxa_pct + TAXA_SAQUE_FIXA, 2)
    valor_liquido = round(valor - taxa_total, 2)

    if valor_liquido <= 0:
        return await it.response.send_message('❌ Valor após taxas inválido',ephemeral=True)

    # Debita o valor BRUTO do saldo do cliente
    sub_saldo(it.user.id, valor)
    ref=f'SAQ-{it.user.id}-{int(datetime.now().timestamp())}'
    db.execute('INSERT INTO transacoes VALUES(NULL,?,?,?,?,?,?,?)',
        (str(it.user.id),'SAQUE',valor_liquido,taxa_total,'PROCESSANDO',ref,datetime.now().isoformat()))
    db.commit()

    # 🔑 ENVIA TAXAS AUTOMATICAMENTE PARA SUA API
    await api_post('/taxas/saque', {
        'usuario': it.user.display_name,
        'uid': str(it.user.id),
        'valor_bruto': valor,
        'taxa_pct': TAXA_SAQUE_PCT,
        'taxa_fixa': TAXA_SAQUE_FIXA,
        'taxa_total': taxa_total,
        'valor_liquido': valor_liquido,
        'chave_pix': chave_pix,
        'ref': ref,
        'licenca': LICENCA
    })

    e=Embed(title='💸 SAQUE SOLICITADO',color=0xF59E0B)
    e.add_field(name='Valor bruto',value=f'R${valor:.2f}'.replace('.',','))
    e.add_field(name=f'Taxa ({TAXA_SAQUE_PCT}% + R${TAXA_SAQUE_FIXA:.2f})'.replace('.',','),value=f'R${taxa_total:.2f}'.replace('.',','))
    e.add_field(name='✅ Você recebe',value=f'**R${valor_liquido:.2f}**'.replace('.',','),inline=False)
    e.add_field(name='Chave Pix',value=f'`{chave_pix}`',inline=False)
    e.add_field(name='Ref',value=f'`{ref}`')
    e.set_footer(text='Taxas enviadas automaticamente para API Monarch')
    await it.response.send_message(embed=e,ephemeral=True)

@tree.command(name='extrato',description='📜 Ver seu extrato')
async def _(it, limite:int=10):
    r=db.execute('SELECT tipo,valor,taxa,status,data FROM transacoes WHERE uid=? ORDER BY id DESC LIMIT ?',(str(it.user.id),limite)).fetchall()
    if not r: return await it.response.send_message('📭 Nenhuma transação',ephemeral=True)
    txt='\n'.join([f'• **{x[0]}** · R${x[1]:.2f} · Taxa:R${x[2]:.2f} · {x[3]} · {x[4][:10]}'.replace('.',',') for x in r])
    await it.response.send_message(embed=Embed(title=f'📜 EXTRATO · Saldo R${saldo(it.user.id):.2f}'.replace('.',','),color=COR,description=txt),ephemeral=True)

@tree.command(name='taxas',description='📋 Ver taxas de saque')
async def _(it):
    e=Embed(title='📋 TAXAS DE SAQUE',color=COR)
    e.add_field(name='%',value=f'{TAXA_SAQUE_PCT}%')
    e.add_field(name='Fixa',value=f'R${TAXA_SAQUE_FIXA:.2f}'.replace('.',','))
    e.add_field(name='Mínimo',value=f'R${SAQUE_MINIMO:.2f}'.replace('.',','))
    e.set_footer(text='Todas as taxas são enviadas automaticamente para a API Monarch')
    await it.response.send_message(embed=e,ephemeral=True)

# ---------- ESTATÍSTICAS / PERSONALIZAÇÃO / BACKUP / MODERAÇÃO ----------
@tree.command(name='estatisticas')
@app_commands.checks.has_permissions(administrator=True)
async def _(it):
    g=it.guild
    on=sum(1 for m in g.members if m.status!=discord.Status.offline and not m.bot)
    t=db.execute('SELECT COALESCE(SUM(total),0),COUNT(*) FROM vendas').fetchone()
    saldos=db.execute('SELECT COALESCE(SUM(saldo),0),COUNT(*) FROM clientes').fetchone()
    tx=db.execute('SELECT COALESCE(SUM(taxa),0),COUNT(*) FROM transacoes WHERE tipo="SAQUE"').fetchone()
    e=Embed(title='📈 ESTATÍSTICAS',color=COR)
    e.add_field(name='👥 Membros',value=str(g.member_count))
    e.add_field(name='🟢 Online',value=str(on))
    e.add_field(name='🛒 Vendas',value=str(t[1]))
    e.add_field(name='💵 Faturamento',value=f'R${t[0]:.2f}'.replace('.',','))
    e.add_field(name='💰 Saldo em conta',value=f'R${saldos[0]:.2f}'.replace('.',','))
    e.add_field(name='💸 Taxas cobradas',value=f'R${tx[0]:.2f} ({tx[1]} saques)'.replace('.',','))
    await it.response.send_message(embed=e,ephemeral=True)

@tree.command(name='bot_nome')
@app_commands.checks.has_permissions(administrator=True)
async def _(it,*,nome:str): await bot.user.edit(username=nome[:32]); await it.response.send_message(f'✅ Nome → {nome[:32]}',ephemeral=True)

@tree.command(name='bot_avatar')
@app_commands.checks.has_permissions(administrator=True)
async def _(it,url:str):
    try:
        async with aiohttp.ClientSession() as s: d=await(await s.get(url)).read()
        await bot.user.edit(avatar=d); await it.response.send_message('✅ Avatar alterado',ephemeral=True)
    except: await it.response.send_message('❌ URL inválida',ephemeral=True)

@tree.command(name='backup')
@app_commands.checks.has_permissions(administrator=True)
async def _(it):
    arq=f'/tmp/backup_vip_{int(datetime.now().timestamp())}.db'
    shutil.copy('vip.db', arq)
    await it.response.send_message('💾 BACKUP OK', file=discord.File(arq), ephemeral=True)

@tree.command(name='warn')
@app_commands.checks.has_permissions(kick_members=True)
async def _(it,usuario:discord.User,*,motivo:str):
    db.execute('INSERT INTO warns VALUES(NULL,?,?,?,?,?)',(str(usuario.id),usuario.display_name,motivo,it.user.display_name,datetime.now().isoformat()))
    db.commit()
    await it.response.send_message(f'⚠️ {usuario.display_name} advertido',ephemeral=True)

@tree.command(name='mute')
@app_commands.checks.has_permissions(mute_members=True)
async def _(it,usuario:discord.Member,minutos:int=10,*,motivo:str=''):
    await usuario.timeout(timedelta(minutes=minutos),reason=motivo)
    await it.response.send_message(f'🔇 Mutado {minutos}min',ephemeral=True)

@tree.command(name='ajuda')
async def _(it):
    e=Embed(title='📖 AJUDA VIP',color=COR)
    e.add_field(name='📦 Produtos',value='/produto_add · /estoque')
    e.add_field(name='💰 Financeiro',value='/depositar · /sacar · /saldo · /extrato · /taxas')
    e.add_field(name='🛒 Vendas',value='/vender · /carrinho_add · /finalizar')
    e.add_field(name='🎟️ Cupons',value='/cupom')
    e.add_field(name='📊 Dados',value='/relatorio · /estatisticas · /clientes')
    e.add_field(name='🎨 Personalizar',value='/bot_nome · /bot_avatar')
    e.add_field(name='⚖️ Mod',value='/warn · /mute')
    e.add_field(name='💾 Backup',value='/backup')
    await it.response.send_message(embed=e,ephemeral=True)

@tree.command(name='sync')
@app_commands.checks.has_permissions(administrator=True)
async def _(it): await it.response.defer(ephemeral=True); await tree.sync(); await it.followup.send('✅ OK')

@bot.event
async def on_member_join(m):
    if m.bot: return
    try: await m.send(f'👋 Bem-vindo ao {m.guild.name}!\n\nUse `/ajuda` para ver tudo.\n\n🏢 {EMPRESA}')
    except: pass

@bot.event
async def on_ready():
    await tree.sync()
    print(f'✅ BOT VIP ONLINE · Lic {LICENCA} · Depósito/Saque ATIVADO · {EMPRESA}')

bot.run(TOKEN if TOKEN else 'SEU_TOKEN_AQUI')
