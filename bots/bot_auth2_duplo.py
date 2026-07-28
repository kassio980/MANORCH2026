import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os, sqlite3, asyncio, aiohttp, secrets, urllib.parse, json
from datetime import datetime
from dotenv import load_dotenv
import discord
from discord import app_commands, ButtonStyle, Interaction, Embed
from discord.ui import View, Button, Modal, TextInput

load_dotenv()
EMPRESA = 'MONARCH FINANCE LTDA'

# EMAIL OFICIAL — MONARCH TECH
EMAIL_USUARIO = os.getenv('EMAIL_OFICIAL','monarchtech.oficial@gmail.com')
EMAIL_SENHA   = os.getenv('EMAIL_SENHA_APP','')
EMAIL_SMTP    = 'smtp.gmail.com'
EMAIL_PORTA   = 587
EMAIL_REMETENTE = 'MONARCH TECH <monarchtech.oficial@gmail.com>'

COR = 0x6D28D9
IMG_FUNDACAO = 'https://p-dola-image-sign-sgnontt.byteintl.net/tos-mya-i-uo7y4d541q/rc_vlm/ac1a11ab6a9f46249be6fdc75624a3ac.jpg~tplv-0es2k971ck-24-95-exif:960:960.image?rcl=20260729033321A4A74190F0A249108842&rk3s=8e244e95&rrcfp=5e034a21&x-orig-authkey=dolaorigin&x-orig-expires=1785353605&x-orig-sign=lwZQL0jCDWJMR%2BqnFV%2B5VSkVtRE%3D'

# ==========================================================================
# 🔐 AUTH 1 — DISCORD MEMBROS  ·  URL: https://auth2-monarch.orender.com/calback/cb3
# ==========================================================================
T1  = os.getenv('AUTH1_TOKEN','')
ID1 = os.getenv('AUTH1_CLIENT_ID','')
SC1 = os.getenv('AUTH1_CLIENT_SECRET','')
CB1 = 'https://auth2-monarch.orender.com/calback/cb3'
P1  = int(os.getenv('AUTH1_PORTA','10003'))
S1  = 'identify%20email%20guilds%20guilds.join%20openid'

db1 = sqlite3.connect('auth_discord.db', check_same_thread=False)
for q in [
  'CREATE TABLE IF NOT EXISTS srv(gid TEXT PRIMARY KEY, canal TEXT, banner TEXT, bt TEXT DEFAULT "✅ SE VERIFICAR", cargo TEXT)',
  'CREATE TABLE IF NOT EXISTS pen(state TEXT PRIMARY KEY, gid TEXT, uid TEXT, nick TEXT, data TEXT)',
  'CREATE TABLE IF NOT EXISTS ver(gid TEXT, uid TEXT, nick TEXT, email TEXT, data TEXT, PRIMARY KEY(gid,uid))',
  'CREATE TABLE IF NOT EXISTS tok(uid TEXT PRIMARY KEY, at TEXT, rt TEXT)',
  'CREATE TABLE IF NOT EXISTS pux(g1 TEXT, g2 TEXT, uid TEXT, nick TEXT, data TEXT, PRIMARY KEY(g1,g2,uid))']: db1.execute(q)
db1.commit()
g1 = lambda i,k,d=None: (lambda r:r[0] if r else d)(db1.execute(f'SELECT {k} FROM srv WHERE gid=?',(str(i),)).fetchone())
s1 = lambda i,**kv: db1.execute(f'INSERT INTO srv(gid,{",".join(kv)}) VALUES(?{",?"*len(kv)}) ON CONFLICT DO UPDATE SET {",".join(f"{k}=excluded.{k}" for k in kv)}',(str(i),*kv.values())) or db1.commit()

# ==========================================================================
# 💰 AUTH 2 — PAINEL VENDAS  ·  URL: https://auth2-monarch.orender.com/calback/cb4
# ==========================================================================
T2  = os.getenv('AUTH2_TOKEN','')
ID2 = os.getenv('AUTH2_CLIENT_ID','')
SC2 = os.getenv('AUTH2_CLIENT_SECRET','')
CB2 = 'https://auth2-monarch.orender.com/calback/cb4'
P2  = int(os.getenv('AUTH2_PORTA','10004'))
S2  = 'identify%20email%20guilds%20openid'
ID_DONO = int(os.getenv('ID_DONO_DISCORD','0'))
SERVIDOR_MEMBROS = int(os.getenv('SERVIDOR_MEMBROS_ID','0'))

db2 = sqlite3.connect('auth_vendas.db', check_same_thread=False)
for q in [
  'CREATE TABLE IF NOT EXISTS sess(state TEXT PRIMARY KEY, tipo TEXT, data TEXT)',
  'CREATE TABLE IF NOT EXISTS users(uid TEXT PRIMARY KEY, nick TEXT, email TEXT, avatar TEXT, nivel TEXT DEFAULT "cliente", at TEXT, rt TEXT, data TEXT)',
  'CREATE TABLE IF NOT EXISTS logs(uid TEXT, acao TEXT, data TEXT)']: db2.execute(q)
db2.commit()

# ==========================================================================
# 🎨 PÁGINA DE VERIFICAÇÃO (USADA PELOS DOIS)
# ==========================================================================
def pagina(titulo='VERIFICAÇÃO STEMY', subtitulo='FUNDAÇÃO BOT'):
  return '''<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>'''+titulo+''' · MONARCH</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{min-height:100vh;background:#000 url('IMG') center/cover no-repeat fixed;
  font-family:'Segoe UI',Arial,sans-serif;color:#fff;display:flex;align-items:center;justify-content:center;padding:20px}
.card{width:100%;max-width:520px;background:rgba(10,6,24,.88);backdrop-filter:blur(14px);
  border:1px solid #8B5CF6;border-radius:22px;padding:28px;box-shadow:0 0 60px rgba(139,92,246,.35);text-align:center}
h1{font-size:26px;font-weight:800;background:linear-gradient(90deg,#C4B5FD,#FDE68A,#C4B5FD);-webkit-background-clip:text;background-clip:text;color:transparent;margin-bottom:6px;letter-spacing:1px}
.sub{color:#A78BFA;font-size:12px;margin-bottom:22px;letter-spacing:3px;text-transform:uppercase}
.etapas{display:flex;justify-content:space-between;align-items:center;margin:14px 0 10px}
.etapa{flex:1;text-align:center;font-size:10px;color:#64748B;font-weight:700;letter-spacing:.5px;transition:.4s}
.etapa.ativa{color:#C4B5FD;text-shadow:0 0 8px #A78BFA}
.etapa.ok{color:#10B981}
.ic{width:30px;height:30px;margin:0 auto 6px;border-radius:50%;border:2px solid #334155;display:flex;align-items:center;justify-content:center;font-size:12px;transition:.4s}
.etapa.ativa .ic{border-color:#A78BFA;box-shadow:0 0 16px #8B5CF6;animation:p 1.2s infinite}
.etapa.ok .ic{border-color:#10B981;background:#10B981;color:#000}
@keyframes p{0%,100%{transform:scale(1)}50%{transform:scale(1.08)}}
.bar{width:100%;height:12px;background:#1E1B2E;border-radius:999px;overflow:hidden;margin:16px 0 8px;border:1px solid #312E4A}
.pr{height:100%;width:0%;background:linear-gradient(90deg,#7C3AED,#A78BFA,#FDE68A,#A78BFA,#7C3AED);
  background-size:300% 100%;border-radius:999px;animation:b 2s linear infinite;transition:width .45s ease}
@keyframes b{0%{background-position:0% 50%}100%{background-position:300% 50%}}
.st{font-size:12px;color:#C4B5FD;min-height:18px;margin-bottom:14px;letter-spacing:1px}
.bt{display:inline-flex;align-items:center;gap:10px;padding:13px 26px;border-radius:14px;
  background:linear-gradient(135deg,#7C3AED,#5B21B6);color:#fff;font-weight:800;font-size:14px;
  text-decoration:none;border:1px solid #A78BFA;box-shadow:0 8px 30px rgba(124,58,237,.45);
  opacity:0;transform:translateY(10px);transition:.5s;pointer-events:none}
.bt.show{opacity:1;transform:translateY(0);pointer-events:auto}
.bt:hover{transform:translateY(-2px)}
.r{margin-top:16px;font-size:10px;color:#64748B}
</style></head><body>
<div class="card">
  <h1>'''+titulo+'''</h1>
  <div class="sub">'''+subtitulo+'''</div>
  <div class="etapas">
    <div class="etapa ativa"><div class="ic">◉</div>CARREGANDO</div>
    <div class="etapa"><div class="ic">◎</div>VERIFICANDO</div>
    <div class="etapa"><div class="ic">✓</div>VERIFICADO</div>
    <div class="etapa"><div class="ic">✓</div>CONCLUIDO</div>
  </div>
  <div class="bar"><div class="pr"></div></div>
  <div class="st">Iniciando verificação segura...</div>
  <a class="bt" href="discord://-/channels/@me">
    <svg width="16" viewBox="0 0 24 24" fill="currentColor"><path d="M20.3 4.4A18 18 0 0 0 16 3l-.2.4a14 14 0 0 0-7.6 0L8 3a18 18 0 0 0-4.3 1.4A19 19 0 0 0 .4 17a18 18 0 0 0 5.5 2.8l.5-.7a12 12 0 0 1-1.8-.9l.4-.3a13 13 0 0 0 11 0l.4.3c-.6.4-1.2.7-1.8.9l.5.7a18 18 0 0 0 5.5-2.8 19 19 0 0 0-3.3-12.6zM8.5 14.7c-1 0-1.9-.9-1.9-2s.8-2 1.9-2 1.9.9 1.9 2-.8 2-1.9 2zm7 0c-1 0-1.9-.9-1.9-2s.8-2 1.9-2 1.9.9 1.9 2-.8 2-1.9 2z"/></svg>
    VOLTA PRO DISCORD
  </a>
  <div class="r">'''+EMPRESA+'''</div>
</div>
<script>
const E=[{p:25,t:'Autorizando...'},{p:55,t:'Coletando dados...'},{p:80,t:'Validando...'},{p:100,t:'✅ CONCLUÍDO'}];
const p=document.querySelector('.pr'),s=document.querySelector('.st'),b=document.querySelector('.bt');
async function R(){
  for(let i=0;i<E.length;i++){
    document.querySelectorAll('.etapa').forEach((e,k)=>{e.classList.remove('ativa','ok');if(k<i)e.classList.add('ok');if(k===i)e.classList.add('ativa');if(k===3)e.classList.add('ok')});
    p.style.width=E[i].p+'%';s.textContent=E[i].t;await new Promise(r=>setTimeout(r,900));
  }
  b.classList.add('show');
}
fetch('/_ok').catch(()=>{}); R();
</script></body></html>'''.replace('IMG', IMG_FUNDACAO)

ERR = '<html><body style="background:#000;color:#fff;text-align:center;padding:80px;font-family:Arial"><h1 style="color:#EF4444">❌ FALHA</h1><a href="discord://-/channels/@me" style="color:#A78BFA">← Voltar</a></body></html>'

# ==========================================================================
# 🤖 BOT 1 — DISCORD /auth  ·  /enviarauth  ·  PUXA MEMBROS
# ==========================================================================
int1 = discord.Intents.default(); int1.members=True; int1.guilds=True
bot1 = discord.Client(intents=int1, shard_id=0, shard_count=2); t1 = app_commands.CommandTree(bot1)

class MC1(Modal, title='⚙️ AUTH1 — CONFIG PAINEL DISCORD'):
  def __init__(self,g): super().__init__(); self.g=str(g)
  self.add_item(TextInput(label='📢 ID CANAL PAINEL', default=g1(g,'canal','')))
  self.add_item(TextInput(label='🖼️ BANNER URL', default=g1(g,'banner',''), required=False))
  self.add_item(TextInput(label='🔘 TEXTO BOTÃO', default=g1(g,'bt','✅ SE VERIFICAR')))
  self.add_item(TextInput(label='👑 ID CARGO VERIFICADO', default=g1(g,'cargo',''), required=False))
  async def on_submit(self,it):
    s1(self.g, canal=self.children[0].value, banner=self.children[1].value, bt=self.children[2].value, cargo=self.children[3].value)
    await it.response.send_message('✅ Salvo — use **/enviarauth**', ephemeral=True)

class MP1(Modal, title='⬇️ AUTH1 — PUXAR MEMBROS VERIFICADOS'):
  def __init__(self): super().__init__()
  self.add_item(TextInput(label='🆔 ID SERVIDOR ORIGEM', required=True))
  self.add_item(TextInput(label='🔗 CONVITE DESTINO', required=True))
  self.add_item(TextInput(label='🔢 QUANTIDADE', default='50'))
  async def on_submit(self,it):
    gO=self.children[0].value; conv=self.children[1].value
    try: q=max(1,min(500,int(self.children[2].value)))
    except: return await it.response.send_message('❌ Qtd inválida', ephemeral=True)
    go=bot1.get_guild(int(gO)) if gO.isdigit() else None
    if not go: return await it.response.send_message('❌ Bot não está no servidor ORIGEM (precisa de ADM + Gerenciar Membros)', ephemeral=True)
    cr=gO.get_role(int(g1(gO,'cargo','0'))) if g1(gO,'cargo','0').isdigit() else None
    if not cr: return await it.response.send_message('❌ Cargo de verificação não configurado na origem', ephemeral=True)
    await it.response.defer(ephemeral=True, thinking=True)
    ja={r[0] for r in db1.execute('SELECT uid FROM pux WHERE g1=? AND g2=?',(gO,str(it.guild.id))).fetchall()}
    alvos=[m for m in go.members if cr in m.roles and not m.bot and str(m.id) not in ja][:q]
    ok=0
    H={'Authorization':f'Bot {T1}','Content-Type':'application/json'}
    async with aiohttp.ClientSession() as ss:
      for m in alvos:
        try:
          tk=db1.execute('SELECT at FROM tok WHERE uid=?',(str(m.id),)).fetchone()
          pl={'nick':m.display_name}
          if tk: pl['access_token']=tk[0]
          r=await ss.put(f'https://discord.com/api/v10/guilds/{it.guild.id}/members/{m.id}',json=pl,headers=H)
          if r.status in(201,204):
            ok+=1; db1.execute('INSERT OR IGNORE INTO pux VALUES(?,?,?,?,?)',(gO,str(it.guild.id),str(m.id),str(m),datetime.now().isoformat())); db1.commit()
        except: pass
    await it.followup.send(f'✅ **{ok}/{len(alvos)}** adicionados', ephemeral=True)

class VPub1(View):
  def __init__(self,g): super().__init__(timeout=None); self.g=str(g)
  @Button(label='VERIFICAR',style=ButtonStyle.green,custom_id='v1')
  async def _(self,it,b):
    st=secrets.token_urlsafe(24)
    db1.execute('INSERT OR REPLACE INTO pen VALUES(?,?,?,?,?)',(st,self.g,str(it.user.id),str(it.user),datetime.now().isoformat())); db1.commit()
    u=f'https://discord.com/api/oauth2/authorize?client_id={ID1}&redirect_uri={urllib.parse.quote(CB1,safe="")}&response_type=code&scope={S1}&state={st}&prompt=consent&guild_id={self.g}'
    await it.response.send_message(f'🔐 [CLIQUE AQUI PARA SE VERIFICAR]({u})\n\n✅ Será pedido: ID · Nick · Email · Servidores', ephemeral=True)

class VAdm1(View):
  def __init__(self): super().__init__(timeout=None)
  @Button(label='⚙️ CONFIG PAINEL',style=ButtonStyle.blurple)
  async def _(self,it,b): await it.response.send_modal(MC1(it.guild.id))
  @Button(label='⬇️ PUXAR MEMBROS',style=ButtonStyle.green)
  async def _(self,it,b): await it.response.send_modal(MP1())
  @Button(label='🚀 ENVIAR PAINEL',style=ButtonStyle.purple)
  async def _(self,it,b):
    g=str(it.guild.id); ch=bot1.get_channel(int(g1(g,'canal','0')))
    if not ch: return await it.response.send_message('❌ Canal não configurado', ephemeral=True)
    e=Embed(title='🔐 VERIFICAÇÃO OBRIGATÓRIA',color=COR,description='Clique abaixo para liberar acesso completo.')
    bn=g1(g,'banner')
    if bn and not any(bn.lower().endswith(x) for x in('.mp4','.webm')): e.set_image(url=bn)
    v=VPub1(g); v.children[0].label=g1(g,'bt','✅ SE VERIFICAR')
    await ch.send(embed=e,view=v); await it.response.send_message(f'✅ Enviado em {ch.mention}', ephemeral=True)

@t1.command(name='auth',description='🔐 AUTH1 — Painel verificação MEMBROS DISCORD')
@app_commands.checks.has_permissions(administrator=True)
async def _(it:Interaction):
  gl=it.guild; v=db1.execute('SELECT COUNT(*) FROM ver WHERE gid=?',(str(gl.id),)).fetchone()[0]
  on=sum(1 for m in gl.members if m.status!=discord.Status.offline and not m.bot)
  e=Embed(title=f'🏢 AUTH1 · DISCORD · {gl.name}',color=COR)
  e.add_field(name='📊 STATS',value=f'Total: {gl.member_count}\nOnline: {on}\nVerificados: {v}')
  e.add_field(name='⚙️ CONFIG',value=f'Canal: <#{g1(gl.id,"canal","0")}>\nCargo: <@&{g1(gl.id,"cargo","0")}>')
  e.set_footer(text=EMPRESA)
  await it.response.send_message(embed=e,view=VAdm1(),ephemeral=True)

@t1.command(name='enviarauth',description='🚀 Enviar painel verificação')
@app_commands.checks.has_permissions(administrator=True)
async def _(it:Interaction):
  g=str(it.guild.id); ch=bot1.get_channel(int(g1(g,'canal','0')))
  if not ch: return await it.response.send_message('❌ Canal não configurado', ephemeral=True)
  e=Embed(title='🔐 VERIFICAÇÃO',color=COR); bn=g1(g,'banner')
  if bn and not any(bn.lower().endswith(x) for x in('.mp4','.webm')): e.set_image(url=bn)
  v=VPub1(g); v.children[0].label=g1(g,'bt','✅ SE VERIFICAR')
  await ch.send(embed=e,view=v); await it.response.send_message('✅ Enviado', ephemeral=True)

# ==========================================================================
# 🤖 BOT 2 — PAINEL VENDAS  ·  /auth_vendas  ·  LOGIN NO SITE
# ==========================================================================
int2 = discord.Intents.default(); int2.members=True
bot2 = discord.Client(intents=int2, shard_id=1, shard_count=2); t2 = app_commands.CommandTree(bot2)

class VAdm2(View):
  def __init__(self): super().__init__(timeout=None)
  @Button(label='🔗 GERAR LINK LOGIN PAINEL',style=ButtonStyle.green)
  async def _(self,it,b):
    st=secrets.token_urlsafe(24)
    db2.execute('INSERT OR REPLACE INTO sess VALUES(?,?,?)',(st,'LOGIN_VENDAS',datetime.now().isoformat())); db2.commit()
    u=f'https://discord.com/api/oauth2/authorize?client_id={ID2}&redirect_uri={urllib.parse.quote(CB2,safe="")}&response_type=code&scope={S2}&state={st}&prompt=consent'
    await it.response.send_message(f'🔐 **LINK LOGIN PAINEL VENDAS:**\n{u}\n\n*(válido 10min)*', ephemeral=True)
  @Button(label='👑 PROMOVER DONO',style=ButtonStyle.red)
  async def _(self,it,b):
    db2.execute('UPDATE users SET nivel="dono" WHERE uid=?',(str(it.user.id),)); db2.commit()
    await it.response.send_message('✅ Você é **DONO** no painel de vendas', ephemeral=True)
  @Button(label='📊 VER USUÁRIOS',style=ButtonStyle.blurple)
  async def _(self,it,b):
    r=db2.execute('SELECT nick,nivel,data FROM users ORDER BY data DESC LIMIT 10').fetchall()
    txt='\n'.join([f'• **{x[0]}** · {x[1]}' for x in r]) or 'Nenhum'
    await it.response.send_message(embed=Embed(title='📊 LOGINS PAINEL',color=COR,description=txt), ephemeral=True)

@t2.command(name='auth_vendas',description='💰 AUTH2 — Controle LOGIN PAINEL DE VENDAS')
@app_commands.checks.has_permissions(administrator=True)
async def _(it:Interaction):
  total=db2.execute('SELECT COUNT(*) FROM users').fetchone()[0]
  donos=db2.execute('SELECT COUNT(*) FROM users WHERE nivel="dono"').fetchone()[0]
  e=Embed(title=f'💰 AUTH2 · PAINEL VENDAS · {it.guild.name}',color=COR)
  e.add_field(name='📊 DADOS',value=f'Contas cadastradas: {total}\nDonos: {donos}')
  e.add_field(name='🔗 URL CALLBACK',value=f'`{CB2}`',inline=False)
  e.set_footer(text=EMPRESA)
  await it.response.send_message(embed=e,view=VAdm2(),ephemeral=True)

# ==========================================================================
# 🌐 SERVIDOR WEB 1 — /calback/cb3  (DISCORD)
# ==========================================================================
from aiohttp import web as aw

async def cb3(req):
  code=req.query.get('code'); st=req.query.get('state')
  if not code or not st: return aw.Response(text=ERR,content_type='text/html')
  pen=db1.execute('SELECT gid,uid,nick FROM pen WHERE state=?',(st,)).fetchone()
  if not pen: return aw.Response(text=ERR,content_type='text/html')
  gid,uid,nick=pen; db1.execute('DELETE FROM pen WHERE state=?',(st,)); db1.commit()
  try:
    async with aiohttp.ClientSession() as ss:
      rt=await ss.post('https://discord.com/api/oauth2/token',data={'client_id':ID1,'client_secret':SC1,'grant_type':'authorization_code','code':code,'redirect_uri':CB1,'scope':S1.replace('%20',' ')},headers={'Content-Type':'application/x-www-form-urlencoded'})
      tk=await rt.json(); at=tk['access_token']; rtk=tk.get('refresh_token','')
      me=await(await ss.get('https://discord.com/api/users/@me',headers={'Authorization':f'Bearer {at}'})).json()
      guild=bot1.get_guild(int(gid))
      if guild:
        try:
          await ss.put(f'https://discord.com/api/v10/guilds/{gid}/members/{me["id"]}',json={'access_token':at,'nick':me.get('global_name',me['username'])},headers={'Authorization':f'Bot {T1}','Content-Type':'application/json'})
          cid=g1(gid,'cargo')
          if cid and cid.isdigit():
            m=guild.get_member(int(me['id'])) or await guild.fetch_member(int(me['id']))
            rl=guild.get_role(int(cid))
            if m and rl: await m.add_roles(rl,reason=f'{EMPRESA} Verificado')
        except: pass
      db1.execute('INSERT OR REPLACE INTO tok VALUES(?,?,?)',(me['id'],at,rtk))
      db1.execute('INSERT OR REPLACE INTO ver VALUES(?,?,?,?,?)',(gid,me['id'],me.get('global_name',me['username']),me.get('email',''),datetime.now().isoformat()))
      enviar_email_verificacao(me.get('email',''), me.get('global_name',me['username']), 'AUTH2 /cb3 DISCORD')
      db1.commit()
  except Exception as ex: print('CB3 ERRO:',ex)
  return aw.Response(text=pagina('VERIFICAÇÃO STEMY','DISCORD · ACESSO LIBERADO'),content_type='text/html')

# ==========================================================================
# 🌐 SERVIDOR WEB 2 — /calback/cb4  (PAINEL VENDAS)
# ==========================================================================
async def cb4(req):
  code=req.query.get('code'); st=req.query.get('state')
  if not code or not st: return aw.Response(text=ERR,content_type='text/html')
  try:
    async with aiohttp.ClientSession() as ss:
      rt=await ss.post('https://discord.com/api/oauth2/token',data={'client_id':ID2,'client_secret':SC2,'grant_type':'authorization_code','code':code,'redirect_uri':CB2,'scope':S2.replace('%20',' ')},headers={'Content-Type':'application/x-www-form-urlencoded'})
      tk=await rt.json(); at=tk['access_token']; rtk=tk.get('refresh_token','')
      me=await(await ss.get('https://discord.com/api/users/@me',headers={'Authorization':f'Bearer {at}'})).json()
      uid=me['id']; nick=me.get('global_name',me['username']); email=me.get('email','')
      avatar=f'https://cdn.discordapp.com/avatars/{uid}/{me.get("avatar","")}.png' if me.get('avatar') else ''
      nivel='dono' if int(uid)==ID_DONO else 'cliente'
      # Verifica se está no servidor de membros
      if SERVIDOR_MEMBROS:
        try:
          gv=await(await ss.get(f'https://discord.com/api/users/@me/guilds/{SERVIDOR_MEMBROS}',headers={'Authorization':f'Bearer {at}'})).json()
          if not gv.get('id'): nivel='bloqueado'
        except: pass
      db2.execute('INSERT OR REPLACE INTO users VALUES(?,?,?,?,?,?,?,?)',(uid,nick,email,avatar,nivel,at,rtk,datetime.now().isoformat()))
      db2.execute('INSERT INTO logs VALUES(?,?,?)',(uid,'LOGIN_PAINEL',datetime.now().isoformat()))
      enviar_email_verificacao(email, nick, 'AUTH2 /cb4 PAINEL VENDAS')
      db2.commit()
      # Envia aviso pro dono
      try:
        dono=await bot2.fetch_user(ID_DONO)
        await dono.send(f'💰 **LOGIN PAINEL VENDAS**\n👤 {nick}\n📧 {email}\n🎖️ Nível: {nivel}')
      except: pass
  except Exception as ex: print('CB4 ERRO:',ex)
  return aw.Response(text=pagina('ACESSO PAINEL','VENDAS · AUTENTICADO'),content_type='text/html')

async def ok(req): return aw.json_response({'ok':True})

# ==========================================================================
# 🚀 INICIA TUDO JUNTO
# ==========================================================================
async def main():
  await asyncio.gather(
    bot1.start(T1),
    bot2.start(T2)
  )

async def web_servers():
  await bot1.wait_until_ready(); await bot2.wait_until_ready()
  await t1.sync(); await t2.sync()
  a1=aw.Application(); a1.router.add_get('/calback/cb3',cb3); a1.router.add_get('/_ok',ok)
  a2=aw.Application(); a2.router.add_get('/calback/cb4',cb4); a2.router.add_get('/_ok',ok)
  await asyncio.gather(
    aw._run_app(a1,host='0.0.0.0',port=P1),
    aw._run_app(a2,host='0.0.0.0',port=P2)
  )

async def tudo():
  await asyncio.gather(main(), web_servers())


@t1.command(name="sync", description="🔁 Atualiza comandos AUTH1 no Discord")
@app_commands.checks.has_permissions(administrator=True)
async def sync1_comando(it: Interaction):
    await it.response.defer(ephemeral=True, thinking=True)
    try:
        await t1.sync()
        await it.followup.send("✅ **AUTH1 DISCORD**: Todos os comandos atualizados com sucesso!", ephemeral=True)
    except Exception as e:
        await it.followup.send(f"❌ Erro: {str(e)}", ephemeral=True)

# Comando para AUTH2 (Painel Vendas)
@t2.command(name="sync_vendas", description="🔁 Atualiza comandos AUTH2 Vendas")
@app_commands.checks.has_permissions(administrator=True)
async def sync2_comando(it: Interaction):
    await it.response.defer(ephemeral=True, thinking=True)
    try:
        await t2.sync()
        await it.followup.send("✅ **AUTH2 VENDAS**: Todos os comandos atualizados com sucesso!", ephemeral=True)
    except Exception as e:
        await it.followup.send(f"❌ Erro: {str(e)}", ephemeral=True)

if __name__=='__main__':
  print(f'''
╔══════════════════════════════════════════════════╗
║   🏢 {EMPRESA}                               ║
║                                                  ║
║   🔐 AUTH1  DISCORD  →  /calback/cb3  :{str(P1):<5} ║
║   💰 AUTH2  VENDAS   →  /calback/cb4  :{str(P2):<5} ║
╚══════════════════════════════════════════════════╝
  ''')
  asyncio.run(tudo())

# ==== SINCRONIZAÇÃO AUTOMÁTICA QUANDO ENTRA NO SERVIDOR ====
@bot1.event
async def on_member_join(membro):
    gid = str(membro.guild.id)
    uid = str(membro.id)
    # Se já foi verificado em QUALQUER bot, já ganha o cargo
    ja_verif = db1.execute('SELECT uid FROM ver WHERE uid=? OR uid IN (SELECT uid FROM users WHERE uid=?)',(uid,uid)).fetchone()
    if ja_verif:
        cargo_id = g1(gid,'cargo')
        if cargo_id and cargo_id.isdigit():
            cargo = membro.guild.get_role(int(cargo_id))
            if cargo and cargo not in membro.roles:
                await membro.add_roles(cargo, reason=f'{EMPRESA}: Já verificado em outro sistema')
                print(f'✅ SINCRONIZADO: {membro} já era verificado — cargo adicionado')
