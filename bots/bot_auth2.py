import os, sqlite3, asyncio, aiohttp
from dotenv import load_dotenv
import discord
from discord import app_commands, ButtonStyle, Interaction, Embed
from discord.ui import View, Button, Modal, TextInput, Select

load_dotenv()
TOKEN=os.getenv('BOT_AUTH2_TOKEN')
DC_ID=os.getenv('DISCORD_CLIENT_ID',''); DC_SEC=os.getenv('DISCORD_CLIENT_SECRET','')
HOST=os.getenv('AUTH_HOST','https://bot-machion-all.onrender.com')

db=sqlite3.connect('bots/auth2.db',check_same_thread=False)
for q in ['CREATE TABLE IF NOT EXISTS cfg(k TEXT PRIMARY KEY,v TEXT)',
  'CREATE TABLE IF NOT EXISTS pending(uid TEXT PRIMARY KEY,state TEXT,gu TEXT)']: db.execute(q)
db.commit()
g=lambda k,d=None: (lambda r:r[0] if r else d)(db.execute('SELECT v FROM cfg WHERE k=?',(k,)).fetchone())
s=lambda k,v: db.execute('INSERT OR REPLACE INTO cfg VALUES(?,?)',(k,v)); db.commit()

intents=discord.Intents.default(); intents.members=True
bot=discord.Client(intents=intents); tree=app_commands.CommandTree(bot)

class MCfg(Modal,title='🔐 AUTH2 Verificação'):
  def __init__(self):
    super().__init__()
    self.add_item(TextInput(label='Canal Painel ID',default=g('cp','')))
    self.add_item(TextInput(label='Cargo Verificado ID',default=g('cv','')))
    self.add_item(TextInput(label='Msg Painel',style=discord.TextStyle.long,default=g('mp','Clique abaixo para se verificar')))
    self.add_item(TextInput(label='Banner URL',default=g('bn','')))
    self.add_item(TextInput(label='Botão Texto',default=g('bt','✅ SE VERIFICAR')))
  async def on_submit(self,it):
    s('cp',self.children[0].value); s('cv',self.children[1].value); s('mp',self.children[2].value); s('bn',self.children[3].value); s('bt',self.children[4].value)
    await it.response.send_message('✅ Config salvo. Use /enviarauth',ephemeral=True)

class MPuxa(Modal,title='⬇️ Puxar Membros'):
  def __init__(self):
    super().__init__()
    self.add_item(TextInput(label='Convite Servidor Origem',required=True))
    self.add_item(TextInput(label='ID Servidor Alvo',required=True))
    self.add_item(TextInput(label='Quantidade',default='100'))
  async def on_submit(self,it):
    await it.response.send_message(f'⬇️ Iniciando puxada de {self.children[2].value} membros...',ephemeral=True)
    await asyncio.sleep(1)
    await it.followup.send('✅ Puxada simulada finalizada (integre API real aqui)',ephemeral=True)

class VPainel(View):
  def __init__(self):
    super().__init__(timeout=None)
  @Button(label='🔐 VERIFICAR',style=ButtonStyle.green,custom_id='auth')
  async def _(self,it,b):
    import uuid; st=str(uuid.uuid4())
    db.execute('INSERT OR REPLACE INTO pending VALUES(?,?,?)',(str(it.user.id),st,str(it.guild.id))); db.commit()
    url=f'https://discord.com/api/oauth2/authorize?client_id={DC_ID}&redirect_uri={HOST}/auth2/cb&response_type=code&scope=identify%20guilds%20email&state={st}'
    await it.response.send_message(f'🔐 [Clique aqui para verificar]({url})\n\nVocê será redirecionado ao Discord oficial, autorize e volte.',ephemeral=True)

@tree.command(name='auth2',description='🔐 Configurar verificação')
@app_commands.checks.has_permissions(administrator=True)
async def _(it):
  v=View()
  b1=Button(label='⚙️ Configurar',style=ButtonStyle.blurple); b2=Button(label='⬇️ Puxar Membros',style=ButtonStyle.green)
  async def c1(ii): await ii.response.send_modal(MCfg())
  async def c2(ii): await ii.response.send_modal(MPuxa())
  b1.callback=c1; b2.callback=c2; v.add_item(b1); v.add_item(b2)
  await it.response.send_message(view=v,ephemeral=True)

@tree.command(name='enviarauth',description='🔐 Enviar painel verificação')
@app_commands.checks.has_permissions(administrator=True)
async def _(it):
  cp=g('cp'); bn=g('bn'); mp=g('mp'); bt=g('bt')
  if not cp: return await it.response.send_message('❌ Canal não configurado',ephemeral=True)
  ch=bot.get_channel(int(cp))
  e=Embed(title='🔐 VERIFICAÇÃO',color=0x10B981,description=mp)
  if bn: e.set_image(url=bn)
  v=VPainel(); v.children[0].label=bt
  await ch.send(embed=e,view=v); await it.response.send_message('✅ Enviado',ephemeral=True)

# Webhook callback
from aiohttp import web as aw
async def cb(r):
  code=r.query.get('code'); st=r.query.get('state')
  if not code or not st: return aw.Response(text='❌ inválido')
  row=db.execute('SELECT uid,gu FROM pending WHERE state=?',(st,)).fetchone()
  if not row: return aw.Response(text='❌ sessão')
  uid,gu=row
  try:
    tok=await (await aiohttp.ClientSession().post('https://discord.com/api/oauth2/token',data={'client_id':DC_ID,'client_secret':DC_SEC,'grant_type':'authorization_code','code':code,'redirect_uri':f'{HOST}/auth2/cb'})).json()
    me=await (await aiohttp.ClientSession().get('https://discord.com/api/users/@me',headers={'Authorization':f'Bearer {tok["access_token"]}'})).json()
    guild=bot.get_guild(int(gu)); cv=g('cv')
    if guild and cv:
      m=guild.get_member(int(uid)) or await guild.fetch_member(int(uid))
      if m: await m.add_roles(guild.get_role(int(cv)))
    db.execute('DELETE FROM pending WHERE state=?',(st,)); db.commit()
    html='''<html><head><meta charset=utf-8><title>Verificado</title><style>
      body{margin:0;background:#0a0618;color:#fff;font-family:Arial;display:flex;align-items:center;justify-content:center;min-height:100vh}
      .c{text-align:center;padding:40px;background:#120a28;border-radius:20px;border:1px solid #8B5CF6}
      .bar{width:300px;height:14px;background:#1e1b2e;border-radius:999px;overflow:hidden;margin:20px auto}
      .f{height:100%;background:linear-gradient(90deg,#10B981,#34D399);animation:g 2.5s forwards}
      @keyframes g{0%{width:0}40%{width:60%}100%{width:100%}}
      a{display:inline-block;margin-top:20px;padding:12px 24px;background:#8B5CF6;color:#fff;border-radius:10px;text-decoration:none;font-weight:700}
      </style></head><body><div class=c><h1 id=t>Carregando...</h1><div class=bar><div class=f></div></div><p id=s>Verificando seus dados...</p><a href='discord://-/channels/@me'>← Voltar pro Discord</a>
      <script>setTimeout(()=>{document.getElementById('t').textContent='✅ VERIFICADO';document.getElementById('s').textContent='Você já recebeu seu cargo, pode voltar!'},2600)</script></div></body></html>'''
    return aw.Response(text=html,content_type='text/html')
  except Exception as e: return aw.Response(text=f'❌ {e}')

@bot.event
async def on_ready():
  await tree.sync(); print(f'✅ BOT AUTH2: {bot.user}')
  ap=aw.Application(); ap.router.add_get('/auth2/cb',cb)
  asyncio.create_task(aw._run_app(ap,host='0.0.0.0',port=int(os.getenv('PORT','10003'))))

bot.run(TOKEN)
