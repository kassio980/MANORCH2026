# ==================================================
# 🔵 BOT INTERMEDIÁRIO — MONARCH API V8
# 📜 LICENÇA: SUA_LICENCA_AQUI | 🔑 API: SUA_API_KEY_AQUI
# 📅 DIAS: DIAS_AQUI | 🖥️ Hospedagem: Render (auto on/off)
# ✅ TUDO DO BÁSICO + CUPONS + RELATÓRIOS + CARRINHO + CLIENTES + TICKETS
# ==================================================
import os, sqlite3, aiohttp, json, random
from datetime import datetime, timedelta
from dotenv import load_dotenv
import discord
from discord import app_commands, Interaction, Embed, ButtonStyle
from discord.ui import View, Button, Modal, TextInput

load_dotenv()
TOKEN = os.getenv('BOT_TOKEN', '')

# DADOS INJETADOS NA COMPRA
LICENCA = 'SUA_LICENCA_AQUI'
API_KEY = 'SUA_API_KEY_AQUI'
DIAS    = int('DIAS_AQUI')
EMPRESA = 'MONARCH FINANCE LTDA'
COR     = 0x3B82F6
API_URL = 'https://api.monarch.finance/v1'

# BANCO
db = sqlite3.connect('intermediario.db', check_same_thread=False)
for q in [
    'CREATE TABLE IF NOT EXISTS produtos(id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT UNIQUE, preco REAL, estoque INTEGER DEFAULT -1, cat TEXT, desc TEXT)',
    'CREATE TABLE IF NOT EXISTS vendas(id INTEGER PRIMARY KEY AUTOINCREMENT, produto TEXT, qtd INTEGER, total REAL, cliente_uid TEXT, cliente_nome TEXT, cupom TEXT, data TEXT)',
    'CREATE TABLE IF NOT EXISTS cupons(codigo TEXT PRIMARY KEY, tipo TEXT, valor REAL, usos INTEGER DEFAULT 0, max_usos INTEGER DEFAULT 999, ativo INTEGER DEFAULT 1)',
    'CREATE TABLE IF NOT EXISTS carrinhos(uid TEXT PRIMARY KEY, itens TEXT)',
    'CREATE TABLE IF NOT EXISTS clientes(uid TEXT PRIMARY KEY, nick TEXT UNIQUE, compras INTEGER DEFAULT 0, gasto REAL DEFAULT 0, primeiro TEXT)',
    'CREATE TABLE IF NOT EXISTS tickets(id INTEGER PRIMARY KEY AUTOINCREMENT, uid TEXT, nick TEXT, assunto TEXT, status TEXT DEFAULT "aberto", data TEXT)',
    'CREATE TABLE IF NOT EXISTS cfg(k TEXT PRIMARY KEY, v TEXT)']: db.execute(q)
db.commit()

# ==================================================
# 🔐 VERIFICA LICENÇA
# ==================================================
async def licenca_ativa() -> bool:
    try:
        async with aiohttp.ClientSession() as s:
            r = await s.get(f'{API_URL}/licenca/{LICENCA}', headers={'X-API-Key': API_KEY}, timeout=6)
            return (await r.json()).get('status') == 'ativa'
    except:
        return True  # Falha de rede = continua funcionando

# ==================================================
# 📦 SISTEMA DE ESTOQUE INFINITO (padrão: -1)
# ==================================================
def add_prod(nome, preco, estoque=-1, cat='Geral', desc=''):
    db.execute('INSERT OR REPLACE INTO produtos(nome,preco,estoque,cat,desc) VALUES(?,?,?,?,?)',(nome.lower(),float(preco),estoque,cat,desc)); db.commit()
def get_prod(nome): return db.execute('SELECT id,nome,preco,estoque,cat,desc FROM produtos WHERE nome=?',(nome.lower(),)).fetchone()
def list_prod(): return db.execute('SELECT nome,preco,estoque,cat FROM produtos ORDER BY cat').fetchall()
def del_prod(nome): db.execute('DELETE FROM produtos WHERE nome=?',(nome.lower(),)); db.commit()

def vender_prod(nome, qtd=1, uid='0', nick='Anônimo', cupom=None):
    p = get_prod(nome)
    if not p: return False, 'Produto não existe'
    if p[3] >= 0 and p[3] < qtd: return False, f'Estoque insuficiente ({p[3]})'
    tot = round(p[2]*qtd, 2)
    if cupom:
        c = db.execute('SELECT tipo,valor FROM cupons WHERE codigo=? AND ativo=1 AND usos<max_usos',(cupom.upper(),)).fetchone()
        if c:
            tot = max(0, tot - (c[1] if c[0]=='fixo' else tot*c[1]/100))
            db.execute('UPDATE cupons SET usos=usos+1 WHERE codigo=?',(cupom.upper(),))
    if p[3] > 0:
        db.execute('UPDATE produtos SET estoque=estoque-? WHERE nome=?',(qtd, nome.lower()))
    db.execute('INSERT INTO vendas VALUES(NULL,?,?,?,?,?,?,?)',(nome,qtd,tot,str(uid),nick,cupom or '',datetime.now().isoformat()))
    db.execute('INSERT OR REPLACE INTO clientes VALUES(?,?,COALESCE((SELECT compras FROM clientes WHERE uid=?),0)+1,COALESCE((SELECT gasto FROM clientes WHERE uid=?),0)+?,?)',
        (str(uid),nick,str(uid),str(uid),tot,datetime.now().isoformat()))
    db.commit()
    return True, f'R${tot:.2f}'.replace('.',',')

# CARRINHO
def gc(uid):
    r = db.execute('SELECT itens FROM carrinhos WHERE uid=?',(str(uid),)).fetchone()
    return json.loads(r[0]) if r else []
def sc(uid,itens):
    db.execute('INSERT OR REPLACE INTO carrinhos VALUES(?,?)',(str(uid),json.dumps(itens))); db.commit()
def cc(itens, cupom=None):
    if not itens: return 0,0
    tot = sum(i['preco']*i['qtd'] for i in itens)
    final = tot
    if cupom:
        c = db.execute('SELECT tipo,valor FROM cupons WHERE codigo=? AND ativo=1 AND usos<max_usos',(cupom.upper(),)).fetchone()
        if c: final = max(0, tot - (c[1] if c[0]=='fixo' else tot*c[1]/100))
    return round(tot,2), round(final,2)

# ==================================================
# 🤖 BOT
# ==================================================
intents = discord.Intents.default(); intents.message_content = True; intents.members = True
bot = discord.Client(intents=intents); tree = app_commands.CommandTree(bot)

# ---------- HERDADOS DO BÁSICO ----------
@tree.command(name='info',description='ℹ️ Dados do bot e licença')
async def _(it: Interaction):
    if not await licenca_ativa():
        return await it.response.send_message('🚫 **LICENÇA EXPIRADA**\n\nSua hospedagem foi desligada automaticamente.\nRenove na Monarch API para religar.', ephemeral=True)
    e = Embed(title='ℹ️ BOT INTERMEDIÁRIO — MONARCH API', color=COR)
    e.add_field(name='Licença', value=f'`{LICENCA}`')
    e.add_field(name='Plano', value=f'🔵 Intermediário ({DIAS} dias)')
    e.add_field(name='API Key', value=f'`{API_KEY[:14]}...`')
    e.add_field(name='Estoque', value='♾️ **Infinito** nativo')
    e.add_field(name='Hospedagem', value='🖥️ Render (auto on/off)')
    e.set_footer(text=EMPRESA)
    await it.response.send_message(embed=e, ephemeral=True)

@tree.command(name='produto_add',description='📦 + Produto (estoque -1 = infinito)')
@app_commands.checks.has_permissions(administrator=True)
async def _(it, nome:str, preco:float, estoque:int=-1, categoria:str='Geral', descricao:str=''):
    add_prod(nome,preco,estoque,categoria,descricao)
    est = '♾️ Infinito' if estoque==-1 else str(estoque)
    await it.response.send_message(f'✅ **{nome}**\n💵 R${preco:.2f}\n📦 Estoque: {est}\n📂 {categoria}'.replace('.',','), ephemeral=True)

@tree.command(name='estoque',description='📊 Ver estoque completo')
async def _(it):
    r = list_prod()
    if not r: return await it.response.send_message('📭 Nenhum produto', ephemeral=True)
    txt = '\n'.join([f'• **{x[0]}** · R${x[1]:.2f} · {"♾️" if x[2]==-1 else x[2]} · [{x[3]}]'.replace('.',',') for x in r])
    await it.response.send_message(embed=Embed(title='📊 ESTOQUE · ♾️ Infinito disponível', color=COR, description=txt), ephemeral=True)

@tree.command(name='produto_del',description='🗑️ Remover produto')
@app_commands.checks.has_permissions(administrator=True)
async def _(it, nome:str): del_prod(nome); await it.response.send_message(f'🗑️ {nome} removido', ephemeral=True)

@tree.command(name='vender',description='💰 Registrar venda rápida')
async def _(it, produto:str, quantidade:int=1, cliente:discord.User=None, cupom:str=''):
    u = cliente or it.user
    ok, m = vender_prod(produto, quantidade, str(u.id), u.display_name, cupom or None)
    await it.response.send_message(f'{"✅" if ok else "❌"} {m}', ephemeral=True)

@tree.command(name='saldo',description='💵 Caixa total')
async def _(it):
    t = db.execute('SELECT COALESCE(SUM(total),0), COUNT(*) FROM vendas').fetchone()
    await it.response.send_message(f'💵 **CAIXA:** R${t[0]:.2f}\n🛒 **Vendas:** {t[1]}'.replace('.',','), ephemeral=True)

# ---------- NOVO: CUPONS ----------
class MC(Modal, title='🎟️ CRIAR CUPOM'):
    def __init__(self): super().__init__()
    self.add_item(TextInput(label='Código (ex: MONARCH15)', required=True))
    self.add_item(TextInput(label='Tipo: fixo ou pct', default='pct'))
    self.add_item(TextInput(label='Valor (10 = 10% ou R$10)', default='10'))
    self.add_item(TextInput(label='Máximo de usos', default='999', required=False))
    async def on_submit(self,it):
        cod=self.children[0].value.upper(); tp=self.children[1].value.lower(); vl=float(self.children[2].value); mx=int(self.children[3].value or 999)
        db.execute('INSERT OR REPLACE INTO cupons VALUES(?,?,?,0,?,1)',(cod,tp,vl,mx)); db.commit()
        await it.response.send_message(f'✅ Cupom `{cod}` criado!\nTipo: `{tp}` · Valor: `{vl}` · Usos: `{mx}`', ephemeral=True)

@tree.command(name='cupom',description='🎟️ Gerenciar cupons')
@app_commands.checks.has_permissions(administrator=True)
async def _(it, acao:str='criar'):
    if acao=='criar': return await it.response.send_modal(MC())
    if acao=='listar':
        r=db.execute('SELECT codigo,tipo,valor,usos,max_usos,ativo FROM cupons').fetchall()
        txt='\n'.join([f'• `{x[0]}` · {x[1]} {x[2]} · {x[3]}/{x[4]} · {"✅" if x[5] else "❌"}' for x in r]) or 'Nenhum'
        return await it.response.send_message(embed=Embed(title='🎟️ CUPONS',color=COR,description=txt),ephemeral=True)

# ---------- NOVO: CARRINHO ----------
@tree.command(name='carrinho_add',description='🛒 + item no carrinho')
async def _(it, produto:str, qtd:int=1):
    p=get_prod(produto)
    if not p: return await it.response.send_message('❌ Produto não existe',ephemeral=True)
    car=gc(str(it.user.id)); car.append({'nome':p[1],'preco':p[2],'qtd':qtd}); sc(str(it.user.id),car)
    t=cc(car)[1]
    await it.response.send_message(f'✅ **{p[1]} x{qtd}** adicionado\n🛒 Itens: {len(car)} · Total: R${t:.2f}'.replace('.',','), ephemeral=True)

@tree.command(name='carrinho',description='🛒 Ver carrinho')
async def _(it):
    car=gc(str(it.user.id)); bruto,final=cc(car)
    if not car: return await it.response.send_message('🛒 Carrinho vazio',ephemeral=True)
    txt='\n'.join([f'• **{i["nome"]}** x{i["qtd"]} — R${i["preco"]*i["qtd"]:.2f}'.replace('.',',') for i in car])
    e=Embed(title=f'🛒 CARRINHO · {it.user.display_name}',color=COR,description=txt)
    e.add_field(name='Subtotal',value=f'R${bruto:.2f}'.replace('.',','))
    e.add_field(name='💵 TOTAL',value=f'**R${final:.2f}**'.replace('.',','),inline=False)
    await it.response.send_message(embed=e,ephemeral=True)

@tree.command(name='carrinho_limpar',description='🗑️ Limpa carrinho')
async def _(it): sc(str(it.user.id),[]); await it.response.send_message('🗑️ Limpo!',ephemeral=True)

@tree.command(name='finalizar',description='💳 Finalizar compra do carrinho')
async def _(it, cupom:str=''):
    car=gc(str(it.user.id))
    if not car: return await it.response.send_message('❌ Vazio',ephemeral=True)
    bruto,final=cc(car,cupom or None)
    for i in car:
        vender_prod(i['nome'],i['qtd'],str(it.user.id),it.user.display_name,cupom or None)
    sc(str(it.user.id),[])
    await it.response.send_message(f'✅ **COMPRA FINALIZADA!**\n💵 R${final:.2f}\n🛒 {len(car)} itens\n🎟️ Cupom: {cupom or "nenhum"}'.replace('.',','), ephemeral=True)

# ---------- NOVO: RELATÓRIOS ----------
@tree.command(name='relatorio',description='📊 Relatório de vendas')
async def _(it, periodo:str='dia'):
    dias = {'dia':1,'semana':7,'mes':30,'ano':365}.get(periodo,1)
    d = datetime.now()-timedelta(days=dias)
    t = db.execute('SELECT COALESCE(SUM(total),0),COUNT(*) FROM vendas WHERE data>?',(d.isoformat(),)).fetchone()
    top = db.execute('SELECT produto,SUM(qtd),SUM(total) FROM vendas WHERE data>? GROUP BY produto ORDER BY SUM(total) DESC LIMIT 5',(d.isoformat(),)).fetchall()
    cl = db.execute('SELECT COUNT(DISTINCT cliente_uid) FROM vendas WHERE data>?',(d.isoformat(),)).fetchone()[0]
    e = Embed(title=f'📊 RELATÓRIO · ÚLTIMOS {dias} DIAS', color=COR)
    e.add_field(name='💵 Faturamento', value=f'R${t[0]:.2f}'.replace('.',','))
    e.add_field(name='🛒 Vendas', value=str(t[1]))
    e.add_field(name='👥 Clientes únicos', value=str(cl))
    e.add_field(name='🏆 Mais vendidos', value='\n'.join([f'• {x[0]} ({x[1]}) — R${x[2]:.2f}'.replace('.',',') for x in top]) or 'Nenhum', inline=False)
    await it.response.send_message(embed=e, ephemeral=True)

# ---------- NOVO: CLIENTES ----------
@tree.command(name='clientes',description='👥 Lista clientes')
@app_commands.checks.has_permissions(administrator=True)
async def _(it, limite:int=10):
    r = db.execute('SELECT nick,compras,gasto FROM clientes ORDER BY gasto DESC LIMIT ?',(limite,)).fetchall()
    txt='\n'.join([f'• **{x[0]}** · {x[1]} compras · R${x[2]:.2f}'.replace('.',',') for x in r]) or 'Nenhum'
    await it.response.send_message(embed=Embed(title='👥 CLIENTES',color=COR,description=txt),ephemeral=True)

# ---------- NOVO: TICKETS ----------
@tree.command(name='ticket',description='🎫 Abrir atendimento')
async def _(it, assunto:str):
    db.execute('INSERT INTO tickets VALUES(NULL,?,?,?,?,?)',(str(it.user.id),it.user.display_name,assunto,'aberto',datetime.now().isoformat()))
    db.commit()
    tid = db.execute('SELECT last_insert_rowid()').fetchone()[0]
    await it.response.send_message(f'🎫 **Ticket #{tid} aberto!**\nAssunto: {assunto}\n\nA equipe já foi avisada.', ephemeral=True)

@tree.command(name='tickets',description='📋 Ver tickets')
@app_commands.checks.has_permissions(administrator=True)
async def _(it, status:str='aberto'):
    r = db.execute('SELECT id,nick,assunto,data FROM tickets WHERE status=? ORDER BY id DESC LIMIT 10',(status,)).fetchall()
    txt='\n'.join([f'• **#{x[0]}** · {x[1]} · {x[2]}' for x in r]) or 'Nenhum'
    await it.response.send_message(embed=Embed(title=f'📋 TICKETS · {status.upper()}',color=COR,description=txt),ephemeral=True)

# ---------- GERAL ----------
@tree.command(name='ajuda',description='📖 Todos os comandos')
async def _(it):
    e=Embed(title='📖 AJUDA — INTERMEDIÁRIO',color=COR,description='♾️ Estoque infinito nativo · 🖥️ Hospedagem Render automática')
    e.add_field(name='📦 Produtos',value='/produto_add · /estoque · /produto_del')
    e.add_field(name='💰 Vendas',value='/vender · /saldo · /finalizar')
    e.add_field(name='🛒 Carrinho',value='/carrinho_add · /carrinho · /carrinho_limpar')
    e.add_field(name='🎟️ Cupons',value='/cupom criar/listar')
    e.add_field(name='📊 Relatórios',value='/relatorio dia/semana/mes/ano')
    e.add_field(name='👥 Clientes',value='/clientes')
    e.add_field(name='🎫 Tickets',value='/ticket · /tickets')
    e.add_field(name='ℹ️ Sistema',value='/info · /ajuda · /sync')
    await it.response.send_message(embed=e, ephemeral=True)

@tree.command(name='sync',description='🔁 Sincronizar comandos')
@app_commands.checks.has_permissions(administrator=True)
async def _(it): await it.response.defer(ephemeral=True); await tree.sync(); await it.followup.send('✅ Comandos atualizados!')

@bot.event
async def on_ready():
    await tree.sync()
    print(f'✅ BOT INTERMEDIÁRIO ONLINE · Lic {LICENCA} · {EMPRESA}')
    print(f'🖥️ Hospedado no Render · Auto on/off por validade')

# 👉 COLE SEU TOKEN AQUI
bot.run(TOKEN if TOKEN else 'SEU_TOKEN_AQUI')
