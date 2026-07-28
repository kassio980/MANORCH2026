import os, sqlite3, qrcode, io, asyncio, aiohttp
from datetime import datetime
from dotenv import load_dotenv
import discord
from discord import app_commands, ButtonStyle, Interaction, Embed, File
from discord.ui import View, Button, Modal, TextInput, Select
from PIL import Image, ImageDraw, ImageFont

load_dotenv()
TOKEN = os.getenv('BOT_VENDAS_TOKEN')
ASAAS_KEY = os.getenv('ASAAS_CHAVE_MESTRE','')
ASAAS_CLI = os.getenv('ASAAS_CLIENTE_ID','cus_190077242')
ASAAS_URL = 'https://www.asaas.com/api/v3'
PIX_TAXA = '11972146580'

db = sqlite3.connect('bots/vendas.db', check_same_thread=False)
for q in [
  'CREATE TABLE IF NOT EXISTS cfg(k TEXT PRIMARY KEY,v TEXT)',
  'CREATE TABLE IF NOT EXISTS produtos(id INTEGER PRIMARY KEY AUTOINCREMENT,nome TEXT,valor REAL,desc TEXT,banner TEXT,estoque INTEGER DEFAULT 0,entrega_link TEXT,entrega_desc TEXT)',
  'CREATE TABLE IF NOT EXISTS saldos(uid TEXT PRIMARY KEY,nick TEXT,saldo REAL DEFAULT 0)',
  'CREATE TABLE IF NOT EXISTS transacoes(id INTEGER PRIMARY KEY AUTOINCREMENT,uid TEXT,tipo TEXT,valor REAL,status TEXT,ref TEXT,pix TEXT,prod TEXT,data TEXT)',
  'CREATE TABLE IF NOT EXISTS logs(tipo TEXT PRIMARY KEY,cid TEXT)',
  'CREATE TABLE IF NOT EXISTS carrinho(uid TEXT,pid INTEGER,qtd INTEGER DEFAULT 1)']: db.execute(q)
db.commit()
g=lambda k,d=None: (lambda r:r[0] if r else d)(db.execute('SELECT v FROM cfg WHERE k=?',(k,)).fetchone())
s=lambda k,v: db.execute('INSERT OR REPLACE INTO cfg VALUES(?,?)',(k,v)); db.commit()
saldo=lambda u: (lambda r:r[0] if r else 0)(db.execute('SELECT saldo FROM saldos WHERE uid=?',(str(u),)).fetchone())
sets=lambda u,n,v: db.execute('INSERT OR REPLACE INTO saldos VALUES(?,?,?)',(str(u),n,v)); db.commit()
taxa_saque=lambda v: 0.5 if v<=5 else 1 if v<=20 else 2 if v<=50 else 4
HDR=lambda: {'access_token':g('asaas_k',ASAAS_KEY),'Content-Type':'application/json'}

async def pix_criar(v,ref):
  async with aiohttp.ClientSession() as s:
    r=await s.post(f'{ASAAS_URL}/payments',json={'customer':g('asaas_c',ASAAS_CLI),'billingType':'PIX','value':v,'dueDate':datetime.now().strftime('%Y-%m-%d'),'externalReference':ref,'description':ref},headers=HDR())
    d=await r.json(); return {'cc':d.get('pixPayload',{}).get('payload',''),'qr':d.get('pixPayload',{}).get('encodedImage',''),'id':d.get('id')}

async def pix_enviar(v,chave,nome):
  async with aiohttp.ClientSession() as s:
    r=await s.post(f'{ASAAS_URL}/pix/transfers',json={'value':v,'pixAddressKey':chave,'pixAddressKeyType':'CPF' if len(chave)==11 else 'TELEFONE','description':'MONARCH','scheduleDate':datetime.now().strftime('%Y-%m-%d')},headers=HDR())
    return await r.json()

def img_compra(nick,prod,valor):
  img=Image.new('RGB',(600,250),'#0a0618'); d=ImageDraw.Draw(img)
  try: f1=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',36); f2=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',22)
  except: f1=f2=ImageFont.load_default()
  d.rectangle([0,0,600,60],fill='#6D28D9')
  d.text((20,12),'✅ COMPRA REALIZADA',font=f1,fill='white')
  d.text((20,100),f'Usuário: {nick}',font=f2,fill='#C4B5FD')
  d.text((20,140),f'Produto: {prod}',font=f2,fill='white')
  d.text((20,180),f'Valor: R$ {valor:.2f}'.replace('.',','),font=f2,fill='#10B981')
  b=io.BytesIO(); img.save(b,'PNG'); b.seek(0); return File(b,'compra.png')

intents=discord.Intents.default(); intents.members=True
bot=discord.Client(intents=intents); tree=app_commands.CommandTree(bot)

class MProd(Modal,title='➕ Criar Produto'):
  n=TextInput(label='Nome',required=True); v=TextInput(label='Valor ex:19.90',required=True)
  d=TextInput(label='Descrição',style=discord.TextStyle.long,required=False)
  b=TextInput(label='Banner URL foto/video',required=False); e=TextInput(label='Estoque 0=ilimitado',default='0')
  async def on_submit(self,it):
    db.execute('INSERT INTO produtos(nome,valor,desc,banner,estoque)VALUES(?,?,?,?,?)',(self.n.value,float(self.v.value.replace(',','.')),self.d.value,self.b.value,int(self.e.value))); db.commit()
    await it.response.send_message(f'✅ Produto **{self.n.value}** criado',ephemeral=True)

class MEntrega(Modal,title='⚡ Entrega Automática'):
  l=TextInput(label='Link/ZIP/APK',required=True); d=TextInput(label='Descrição',style=discord.TextStyle.long,required=True)
  def __init__(self,pid): super().__init__(); self.pid=pid
  async def on_submit(self,it):
    db.execute('UPDATE produtos SET entrega_link=?,entrega_desc=? WHERE id=?',(self.l.value,self.d.value,self.pid)); db.commit()
    await it.response.send_message('✅ Entrega cadastrada',ephemeral=True)

class MValor(Modal):
  v=TextInput(label='Valor R$',required=True)
  def __init__(self,tit,mn,mx): super().__init__(title=tit); self.v.label=f'R$ {mn:.2f} até R$ {mx:.2f}'.replace('.',','); self.mn=mn; self.mx=mx
  async def on_submit(self,it):
    try: self.vv=float(self.v.value.replace(',','.'))
    except: return await it.response.send_message('❌ Valor inválido',ephemeral=True)
    if self.vv<self.mn or self.vv>self.mx: return await it.response.send_message('❌ Fora do limite',ephemeral=True)
    self.stop()

class MSaque(Modal,title='💸 Sacar'):
  p=TextInput(label='Chave PIX',required=True); n=TextInput(label='Nome Conta',required=True); v=TextInput(label='Valor min R$5',required=True)
  async def on_submit(self,it):
    try: v=float(self.v.value.replace(',','.'))
    except: return await it.response.send_message('❌ Valor inválido',ephemeral=True)
    if v<5: return await it.response.send_message('❌ Mínimo R$5',ephemeral=True)
    sd=saldo(it.user.id); tx=taxa_saque(v); tt=v+tx
    if sd<tt: return await it.response.send_message(f'❌ Saldo insuficiente. Precisa R${tt:.2f} c/ taxa'.replace('.',','),ephemeral=True)
    await pix_enviar(tx,PIX_TAXA,'Taxa'); r=await pix_enviar(v,self.p.value,self.n.value)
    if r.get('id'):
      sets(it.user.id,it.user.display_name,sd-tt)
      await it.response.send_message(f'✅ Saque enviado R${v:.2f} · Taxa R${tx:.2f}'.replace('.',','),ephemeral=True)
      lc=g('log_saque')
      if lc: await bot.get_channel(int(lc)).send(embed=Embed(title='💸 SAQUE',color=0xef4444,description=f'<@{it.user.id}>\nR${v:.2f} · Taxa R${tx:.2f}\nPIX: {self.p.value}'.replace('.',',')))
    else: await it.response.send_message(f'❌ Erro: {r.get("errors","")}',ephemeral=True)

class VPainel(View):
  def __init__(self): super().__init__(timeout=None)
  @Button(label='➕ Criar Produto',style=ButtonStyle.blurple)
  async def _(self,it,b): await it.response.send_modal(MProd())
  @Button(label='🗑️ Remover',style=ButtonStyle.red)
  async def _(self,it,b):
    ps=db.execute('SELECT id,nome FROM produtos').fetchall()
    if not ps: return await it.response.send_message('❌ Sem produtos',ephemeral=True)
    v=View(); sel=Select(options=[discord.SelectOption(label=f'{p[1]} #{p[0]}',value=str(p[0])) for p in ps])
    async def c(i): db.execute('DELETE FROM produtos WHERE id=?',(int(sel.values[0]),)); db.commit(); await i.response.edit_message(content='✅ Removido',view=None)
    sel.callback=c; v.add_item(sel); await it.response.send_message(view=v,ephemeral=True)
  @Button(label='⚡ Entrega Automática',style=ButtonStyle.green)
  async def _(self,it,b):
    ps=db.execute('SELECT id,nome FROM produtos').fetchall()
    if not ps: return await it.response.send_message('❌ Sem produtos',ephemeral=True)
    v=View(); sel=Select(options=[discord.SelectOption(label=f'{p[1]} #{p[0]}',value=str(p[0])) for p in ps])
    async def c(i): await i.response.send_modal(MEntrega(int(sel.values[0])))
    sel.callback=c; v.add_item(sel); await it.response.send_message(view=v,ephemeral=True)
  @Button(label='🚀 Criar Painel Loja',style=ButtonStyle.purple)
  async def _(self,it,b):
    cats=['VIP','BOTS','CONTAS','OUTROS']
    v=View(); sel=Select(options=[discord.SelectOption(label=c,value=c) for c in cats])
    async def c(i):
      ps=db.execute('SELECT * FROM produtos').fetchall()
      if not ps: return await i.response.send_message('❌ Sem produtos',ephemeral=True)
      await i.channel.send(embed=Embed(title=f'🛒 LOJA — {sel.values[0]}',color=0x8B5CF6,description='Escolha:'),view=VLoja(ps))
      await i.response.send_message('✅ Painel enviado',ephemeral=True)
    sel.callback=c; v.add_item(sel); await it.response.send_message(view=v,ephemeral=True)
  @Button(label='🔑 API Asaas',style=ButtonStyle.grey)
  async def _(self,it,b):
    m=Modal(title='🔑 API'); m.add_item(TextInput(label='Chave',required=True)); m.add_item(TextInput(label='Cliente cus_...',required=True))
    async def ss(i): s('asaas_k',m.children[0].value); s('asaas_c',m.children[1].value); await i.response.send_message('✅ Salvo',ephemeral=True)
    m.on_submit=ss; await it.response.send_modal(m)

class VLoja(View):
  def __init__(self,ps):
    super().__init__(timeout=None); self.ps=ps
    for p in ps[:25]: self.add_item(Button(label=f'R${p[2]:.2f} · {p[1]}'.replace('.',','),custom_id=f'b_{p[0]}',style=ButtonStyle.green))
    self.add_item(Button(label='🛒 Carrinho',custom_id='cart',style=ButtonStyle.blurple))
  async def interaction_check(self,it):
    c=it.data.get('custom_id','')
    if c=='cart':
      its=db.execute('SELECT p.nome,p.valor,c.qtd FROM carrinho c JOIN produtos p ON p.id=c.pid WHERE c.uid=?',(str(it.user.id),)).fetchall()
      if not its: return await it.response.send_message('🛒 Vazio',ephemeral=True)
      tot=sum(i[1]*i[2] for i in its)+1.0
      e=Embed(title='🛒 Carrinho',color=0x8B5CF6,description='\n'.join([f'• {i[2]}x {i[0]} R${i[1]*i[2]:.2f}'.replace('.',',') for i in its])+f'\n\n**Total c/ taxa R$1: R${tot:.2f}**'.replace('.',','))
      v=View()
      b1=Button(label='✅ Finalizar',style=ButtonStyle.green); b2=Button(label='🗑️ Limpar',style=ButtonStyle.red)
      async def f(ii):
        sd=saldo(ii.user.id)
        if sd<tot: return await ii.response.send_message(f'❌ Saldo R${sd:.2f}'.replace('.',','),ephemeral=True)
        sets(ii.user.id,ii.user.display_name,sd-tot); await pix_enviar(1.0,PIX_TAXA,'Taxa')
        for i in its:
          p=db.execute('SELECT entrega_link,entrega_desc,nome FROM produtos WHERE nome=?',(i[0],)).fetchone()
          await ii.user.send(f'✅ **{p[2]}**\n{p[1]}\n{p[0]}')
          lc=g('log_compra')
          if lc: await bot.get_channel(int(lc)).send(file=img_compra(ii.user.display_name,p[2],i[1]*i[2]),embed=Embed(title='🛒 COMPRA',color=0x10B981,description=f'<@{ii.user.id}>\n{i[0]} R${i[1]*i[2]:.2f}'.replace('.',',')))
        db.execute('DELETE FROM carrinho WHERE uid=?',(str(ii.user.id),)); db.commit()
        await ii.response.edit_message(content='✅ Feito! Entregue na DM',embed=None,view=None)
      async def l(ii): db.execute('DELETE FROM carrinho WHERE uid=?',(str(ii.user.id),)); db.commit(); await ii.response.edit_message(content='🗑️ Limpo',embed=None,view=None)
      b1.callback=f; b2.callback=l; v.add_item(b1); v.add_item(b2)
      await it.response.send_message(embed=e,view=v,ephemeral=True); return True
    if c.startswith('b_'):
      pid=int(c[2:]); p=db.execute('SELECT * FROM produtos WHERE id=?',(pid,)).fetchone()
      e=Embed(title=p[1],color=0x8B5CF6,description=p[3] or '').add_field(name='💰',value=f'R${p[2]:.2f}'.replace('.',',')).add_field(name='📦',value=str(p[5]) if p[5] else '∞')
      if p[4]: e.set_image(url=p[4])
      v=View()
      async def px(ii):
        m=MValor('💳 PIX',max(2.0,p[2]),2500); await ii.response.send_modal(m); await m.wait()
        if not hasattr(m,'vv'): return
        ref=f'V{pid}-{ii.user.id}-{int(datetime.now().timestamp())}'
        r=await pix_criar(m.vv,ref)
        db.execute('INSERT INTO transacoes(uid,tipo,valor,status,ref,pix,prod,data)VALUES(?,?,?,?,?,?,?,?)',(str(ii.user.id),'PIX',m.vv,'PENDENTE',ref,r['cc'],p[1],datetime.now().isoformat())); db.commit()
        ee=Embed(title='💳 PIX',color=0x10B981,description=f'**R${m.vv:.2f}**\n\n```\n{r["cc"]}\n```').replace('.',',')
        if r['qr']: ee.set_image(url=r['qr'])
        await ii.edit_original_response(embed=ee,view=None)
      async def sd(ii):
        s0=saldo(ii.user.id); tt=p[2]+1.0
        if s0<tt: return await ii.response.send_message(f'❌ Saldo R${s0:.2f} · Precisa R${tt:.2f}'.replace('.',','),ephemeral=True)
        sets(ii.user.id,ii.user.display_name,s0-tt); await pix_enviar(1.0,PIX_TAXA,'Taxa')
        if p[6]: await ii.user.send(f'✅ **{p[1]}**\n{p[7]}\n{p[6]}')
        lc=g('log_compra')
        if lc: await bot.get_channel(int(lc)).send(file=img_compra(ii.user.display_name,p[1],p[2]),embed=Embed(title='🛒 SALDO',color=0x10B981,description=f'<@{ii.user.id}>\n{p[1]} R${p[2]:.2f}'.replace('.',',')))
        await ii.response.edit_message(content='✅ Comprado! DM enviada',embed=None,view=None)
      async def cr(ii):
        db.execute('INSERT INTO carrinho VALUES(?,?,1) ON CONFLICT DO UPDATE SET qtd=qtd+1',(str(ii.user.id),pid)); db.commit()
        await ii.response.send_message('✅ + carrinho',ephemeral=True)
      b1=Button(label='💳 PIX',style=ButtonStyle.green); b1.callback=px
      b2=Button(label='💸 Saldo +R$1',style=ButtonStyle.blurple); b2.callback=sd
      b3=Button(label='🛒 + Carrinho',style=ButtonStyle.grey); b3.callback=cr
      v.add_item(b1); v.add_item(b2); v.add_item(b3)
      await it.response.send_message(embed=e,view=v,ephemeral=True); return True
    return True

class VSaldo(View):
  def __init__(self,u,n): super().__init__(); self.u=u; self.n=n
  @Button(label='📥 DEPOSITAR',style=ButtonStyle.green)
  async def _(self,it,b):
    m=MValor('📥 Depósito',2.0,2500); await it.response.send_modal(m); await m.wait()
    if not hasattr(m,'vv'): return
    ref=f'D{self.u}-{int(datetime.now().timestamp())}'; r=await pix_criar(m.vv,ref)
    db.execute('INSERT INTO transacoes(uid,tipo,valor,status,ref,pix,data)VALUES(?,?,?,?,?,?,?)',(str(self.u),'DEP',m.vv,'PENDENTE',ref,r['cc'],datetime.now().isoformat())); db.commit()
    e=Embed(title='📥 DEPÓSITO PIX',color=0x10B981,description=f'**R${m.vv:.2f}**\n\n```\n{r["cc"]}\n```').replace('.',',')
    if r['qr']: e.set_image(url=r['qr'])
    await it.edit_original_response(embed=e)
  @Button(label='📤 SACAR',style=ButtonStyle.red)
  async def _(self,it,b): await it.response.send_modal(MSaque())

@tree.command(name='painel',description='🛒 Painel loja')
@app_commands.checks.has_permissions(administrator=True)
async def _(it): await it.response.send_message('# 🛒 PAINEL VENDAS',view=VPainel(),ephemeral=True)

@tree.command(name='api',description='🔑 Cadastrar API Asaas')
@app_commands.checks.has_permissions(administrator=True)
async def _(it):
  m=Modal(title='🔑 API'); m.add_item(TextInput(label='Chave',required=True)); m.add_item(TextInput(label='Cliente cus_...',required=True))
  async def ss(i): s('asaas_k',m.children[0].value); s('asaas_c',m.children[1].value); await i.response.send_message('✅ Salvo',ephemeral=True)
  m.on_submit=ss; await it.response.send_modal(m)

@tree.command(name='saldo',description='💰 Saldo / Depositar / Sacar')
async def _(it):
  await it.response.send_message(embed=Embed(title='💰 SALDO',color=0x8B5CF6,description=f'{it.user.mention}\n**R${saldo(it.user.id):.2f}**'.replace('.',',')),view=VSaldo(it.user.id,it.user.display_name),ephemeral=True)

@tree.command(name='log',description='📋 Configurar canais logs')
@app_commands.checks.has_permissions(administrator=True)
async def _(it):
  v=View()
  for t in ['compra','saque','deposito']:
    sel=Select(placeholder=f'Canal {t}',options=[discord.SelectOption(label=c.name,value=str(c.id)) for c in it.guild.text_channels[:25]],custom_id=t)
    async def cb(i,tt=t): s(f'log_{tt}',i.data['values'][0]); await i.response.send_message(f'✅ Log {tt}',ephemeral=True)
    sel.callback=cb; v.add_item(sel)
  await it.response.send_message(view=v,ephemeral=True)

from aiohttp import web as aw
async def wh(r):
  try:
    d=await r.json(); ev=d.get('event',''); ref=d.get('payment',{}).get('externalReference','')
    if ev in('PAYMENT_RECEIVED','PAYMENT_CONFIRMED') and ref:
      t=db.execute('SELECT id,uid,tipo,valor FROM transacoes WHERE ref=? AND status=?',(ref,'PENDENTE')).fetchone()
      if t:
        db.execute('UPDATE transacoes SET status=? WHERE id=?',('CONFIRMADO',t[0]))
        if t[2]=='DEP':
          u=bot.get_user(int(t[1])); sets(t[1],u.display_name if u else '?',saldo(t[1])+t[3])
          if u: await u.send(f'📥 +R${t[3]:.2f}'.replace('.',','))
          lc=g('log_deposito')
          if lc: await bot.get_channel(int(lc)).send(embed=Embed(title='📥 DEPÓSITO',color=0x10B981,description=f'<@{t[1]}> R${t[3]:.2f}'.replace('.',',')))
        db.commit()
  except: pass
  return aw.Response()

@bot.event
async def on_ready():
  await tree.sync(); print(f'✅ BOT VENDAS: {bot.user}')
  ap=aw.Application(); ap.router.add_post('/wh/asaas',wh)
  asyncio.create_task(aw._run_app(ap,host='0.0.0.0',port=int(os.getenv('PORT','10001'))))

bot.run(TOKEN)
