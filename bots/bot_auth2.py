import os, sqlite3, asyncio, aiohttp, secrets, urllib.parse, smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
import discord
from discord import app_commands, ButtonStyle, Interaction, Embed
from discord.ui import View, Button, Modal, TextInput

load_dotenv()

# ==============================
# 🔐 SÓ AUTH2 DISCORD — /cb3
# ==============================
TOKEN = os.getenv('BOT_AUTH2_TOKEN', '')
DC_ID = os.getenv('DISCORD_CLIENT_ID', '')
DC_SEC = os.getenv('DISCORD_CLIENT_SECRET', '')
CB = 'https://auth2-monarch.orender.com/calback/cb3'  # 🔒 SÓ ESSE EXISTE AGORA
SCOPES = 'identify%20email%20guilds%20guilds.join%20openid'
PORTA = int(os.getenv('PORT_AUTH2', '10003'))
EMPRESA = 'MONARCH FINANCE LTDA'
COR = 0x6D28D9
IMG = 'https://p-dola-image-sign-sgnontt.byteintl.net/tos-mya-i-uo7y4d541q/rc_vlm/ac1a11ab6a9f46249be6fdc75624a3ac.jpg~tplv-0es2k971ck-24-95-exif:960:960.image?rcl=20260729033321A4A74190F0A249108842&rk3s=8e244e95&rrcfp=5e034a21&x-orig-authkey=dolaorigin&x-orig-expires=1785353605&x-orig-sign=lwZQL0jCDWJMR%2BqnFV%2B5VSkVtRE%3D'

# EMAIL OFICIAL
EMAIL_U = 'monarchtech.oficial@gmail.com'
EMAIL_S = os.getenv('EMAIL_SENHA_APP', '')

db = sqlite3.connect('auth2_discord.db', check_same_thread=False)
for q in [
    'CREATE TABLE IF NOT EXISTS srv(gid TEXT PRIMARY KEY, canal TEXT, banner TEXT, bt TEXT DEFAULT "✅ SE VERIFICAR", cargo TEXT)',
    'CREATE TABLE IF NOT EXISTS pen(state TEXT PRIMARY KEY, gid TEXT, uid TEXT, nick TEXT, data TEXT)',
    'CREATE TABLE IF NOT EXISTS ver(gid TEXT, uid TEXT, nick TEXT, email TEXT, data TEXT, PRIMARY KEY(gid,uid))',
    'CREATE TABLE IF NOT EXISTS tok(uid TEXT PRIMARY KEY, at TEXT, rt TEXT)',
    'CREATE TABLE IF NOT EXISTS pux(g1 TEXT, g2 TEXT, uid TEXT, nick TEXT, data TEXT, PRIMARY KEY(g1,g2,uid))']: db.execute(q)
db.commit()

g_ = lambda i,k,d=None: (lambda r:r[0] if r else d)(db.execute(f'SELECT {k} FROM srv WHERE gid=?',(str(i),)).fetchone())
s_ = lambda i,**kv: db.execute(f'INSERT INTO srv(gid,{",".join(kv)}) VALUES(?{",?"*len(kv)}) ON CONFLICT DO UPDATE SET {",".join(f"{k}=excluded.{k}" for k in kv)}',(str(i),*kv.values())) or db.commit()

def enviar_email(email_destino, nome, tipo='DISCORD'):
    if not EMAIL_S or '@' not in str(email_destino): return False
    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = f'MONARCH TECH <{EMAIL_U}>'
        msg['To'] = f'{nome} <{email_destino}>'
        msg['Subject'] = '✅ Verificacao AUTH2 Concluida com Sucesso'
        HTML = f'''<html><body style="margin:0;padding:25px;background:#05020D;font-family:Arial;color:#E5E7EB">
<div style="max-width:620px;margin:auto;background:#0A0618;border:1px solid #7C3AED;border-radius:18px;overflow:hidden">
  <div style="background:linear-gradient(135deg,#5B21B6,#7C3AED);padding:24px;text-align:center;color:#fff">
    <div style="font-size:20px;font-weight:900">MONARCH TECH™</div>
    <div style="font-size:10px;letter-spacing:3px">Technology • APIs • Bots • Solutions</div>
  </div>
  <div style="padding:26px;line-height:1.7;font-size:14px">
    <div style="font-size:17px;font-weight:800;color:#C4B5FD">Sua verificacao foi concluida.</div>
    <p>Ola, <strong>{nome}</strong>!</p>
    <p>Este e um comunicado automatico da <strong>MONARCH TECH™</strong>. Sua autenticacao AUTH2 foi concluida com sucesso.</p>
    <div style="margin:18px 0;padding:16px;background:rgba(124,58,237,.12);border-radius:10px">
      🟢 Verificacao: <strong style="color:#10B981">APROVADA</strong><br>
      🟢 Conta: <strong style="color:#10B981">VALIDADA</strong><br>
      🟢 Cargo Discord: <strong style="color:#10B981">CONCEDIDO</strong><br>
      🟢 Permissoes: <strong style="color:#10B981">LIBERADAS</strong>
    </div>
    <p style="color:#10B981;font-weight:800">Seu acesso ja esta disponivel.</p>
    <p style="color:#9CA3AF;font-size:12px">Caso o cargo nao apareca, aguarde alguns segundos e atualize o Discord.</p>
    <div style="margin-top:18px;padding-top:14px;border-top:1px dashed rgba(167,139,250,.3);color:#9CA3AF;font-size:12px">
      <strong style="color:#F59E0B">Informacoes de Seguranca</strong><br>
      Comunicacao automatica. Nao responda.
    </div>
  </div>
  <div style="background:#070410;padding:18px;text-align:center;color:#8B5CF6;font-size:12px;border-top:1px solid rgba(124,58,237,.4)">
    <strong style="color:#C4B5FD">MONARCH TECH™</strong><br>
    SALES & DIGITAL SYSTEMS<br>
    monarchtech.oficial@gmail.com<br>
    © 2026 — MONARCH TECH™. Todos os direitos reservados.
  </div>
</div></body></html>'''
        msg.attach(MIMEText(HTML, 'html', 'utf-8'))
        with smtplib.SMTP('smtp.gmail.com', 587, timeout=12) as sm:
            sm.starttls(); sm.login(EMAIL_U, EMAIL_S); sm.sendmail(EMAIL_U, email_destino, msg.as_string())
        print(f'📧 AUTH2 EMAIL → {email_destino}')
        return True
    except Exception as ex: print(f'❌ EMAIL: {ex}'); return False

PAG = '''<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AUTH2 · MONARCH</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{min-height:100vh;background:#000 url('IMG') center/cover no-repeat fixed;font-family:Arial;color:#fff;display:flex;align-items:center;justify-content:center;padding:20px}
.card{max-width:520px;width:100%;background:rgba(10,6,24,.88);backdrop-filter:blur(14px);border:1px solid #8B5CF6;border-radius:22px;padding:28px;text-align:center;box-shadow:0 0 60px rgba(139,92,246,.35)}
h1{font-size:26px;font-weight:800;background:linear-gradient(90deg,#C4B5FD,#FDE68A,#C4B5FD);-webkit-background-clip:text;background-clip:text;color:transparent;margin-bottom:6px}
.sub{color:#A78BFA;font-size:12px;margin-bottom:18px;letter-spacing:3px;text-transform:uppercase}
.etapas{display:flex;justify-content:space-between;margin:14px 0}
.etapa{flex:1;text-align:center;font-size:10px;color:#64748B;font-weight:700}
.etapa.ativa{color:#C4B5FD;text-shadow:0 0 8px #A78BFA}
.etapa.ok{color:#10B981}
.ic{width:28px;height:28px;margin:0 auto 4px;border-radius:50%;border:2px solid #334155;display:flex;align-items:center;justify-content:center;font-size:11px}
.etapa.ativa .ic{border-color:#A78BFA;animation:p 1.2s infinite}
.etapa.ok .ic{border-color:#10B981;background:#10B981;color:#000}
@keyframes p{50%{transform:scale(1.08)}}
.bar{width:100%;height:12px;background:#1E1B2E;border-radius:999px;overflow:hidden;margin:14px 0;border:1px solid #312E4A}
.pr{height:100%;width:0%;background:linear-gradient(90deg,#7C3AED,#A78BFA,#FDE68A,#A78BFA,#7C3AED);background-size:300% 100%;animation:b 2s linear infinite;transition:width .45s}
@keyframes b{to{background-position:300% 50%}}
.st{font-size:12px;color:#C4B5FD;min-height:18px;margin-bottom:10px}
.bt{display:inline-flex;align-items:center;gap:8px;padding:12px 24px;border-radius:14px;background:linear-gradient(135deg,#7C3AED,#5B21B6);color:#fff;font-weight:800;text-decoration:none;border:1px solid #A78BFA;opacity:0;transform:translateY(10px);transition:.5s;pointer-events:none}
.bt.show{opacity:1;transform:translateY(0);pointer-events:auto}
</style></head><body>
<div class="card">
  <h1>VERIFICACAO STEMY</h1>
  <div class="sub">DISCORD · MONARCH</div>
  <div class="etapas">
    <div class="etapa ativa"><div class="ic">◉</div>CARREGANDO</div>
    <div class="etapa"><div class="ic">◎</div>VERIFICANDO</div>
    <div class="etapa"><div class="ic">✓</div>VERIFICADO</div>
    <div class="etapa"><div class="ic">✓</div>CONCLUIDO</div>
  </div>
  <div class="bar"><div class="pr"></div></div>
  <div class="st">Iniciando...</div>
  <a class="bt" href="discord://-/channels/@me">🐸 VOLTA PRO DISCORD</a>
</div>
<script>
const E=[{p:25,t:'Autorizando...'},{p:55,t:'Coletando dados...'},{p:80,t:'Aplicando cargo...'},{p:100,t:'✅ CONCLUIDO'}];
const p=document.querySelector('.pr'),s=document.querySelector('.st'),b=document.querySelector('.bt');
async function R(){
  for(let i=0;i<E.length;i++){
    document.querySelectorAll('.etapa').forEach((e,k)=>{e.classList.remove('ativa','ok');if(k<i)e.classList.add('ok');if(k===i)e.classList.add('ativa');if(k===3)e.classList.add('ok')});
    p.style.width=E[i].p+'%';s.textContent=E[i].t;await new Promise(r=>setTimeout(r,900));
  }
  b.classList.add('show');
}
R();
</script></body></html>'''.replace('IMG', IMG)

ERR = '<html><body style="background:#000;color:#fff;text-align:center;padding:80px"><h1 style="color:#EF4444">❌ FALHA</h1><a href="discord://-/channels/@me" style="color:#A78BFA">← Voltar</a></body></html>'

intents = discord.Intents.default(); intents.members = True
bot = discord.Client(intents=intents); tree = app_commands.CommandTree(bot)

class MCfg(Modal, title='⚙️ CONFIG AUTH2 DISCORD'):
    def __init__(self,g): super().__init__(); self.g=str(g)
    self.add_item(TextInput(label='ID CANAL PAINEL', default=g_(g,'canal','')))
    self.add_item(TextInput(label='BANNER URL', default=g_(g,'banner',''), required=False))
    self.add_item(TextInput(label='TEXTO BOTAO', default=g_(g,'bt','✅ SE VERIFICAR')))
    self.add_item(TextInput(label='ID CARGO VERIFICADO', default=g_(g,'cargo',''), required=False))
    async def on_submit(self,it):
        s_(self.g, canal=self.children[0].value, banner=self.children[1].value, bt=self.children[2].value, cargo=self.children[3].value)
        await it.response.send_message('✅ Salvo — use /enviarauth', ephemeral=True)

class MPuxa(Modal, title='⬇️ PUXAR MEMBROS VERIFICADOS'):
    def __init__(self): super().__init__()
    self.add_item(TextInput(label='ID SERVIDOR ORIGEM'))
    self.add_item(TextInput(label='LINK CONVITE DESTINO'))
    self.add_item(TextInput(label='QUANTIDADE', default='50'))
    async def on_submit(self,it):
        gO=self.children[0].value; conv=self.children[1].value
        try: q=max(1,min(500,int(self.children[2].value)))
        except: return await it.response.send_message('❌ Qtd invalida', ephemeral=True)
        go=bot.get_guild(int(gO)) if gO.isdigit() else None
        if not go: return await it.response.send_message('❌ Bot nao esta no servidor origem (ADM + Gerenciar Membros)', ephemeral=True)
        cr=go.get_role(int(g_(gO,'cargo','0'))) if g_(gO,'cargo','0').isdigit() else None
        if not cr: return await it.response.send_message('❌ Cargo nao configurado na origem', ephemeral=True)
        await it.response.defer(ephemeral=True, thinking=True)
        ja={r[0] for r in db.execute('SELECT uid FROM pux WHERE g1=? AND g2=?',(gO,str(it.guild.id))).fetchall()}
        alvos=[m for m in go.members if cr in m.roles and not m.bot and str(m.id) not in ja][:q]
        ok=0
        for m in alvos:
            try:
                cid=g_(str(it.guild.id),'cargo')
                if cid and cid.isdigit():
                    rl=it.guild.get_role(int(cid))
                    if rl and it.guild.get_member(m.id): await it.guild.get_member(m.id).add_roles(rl)
                ok+=1; db.execute('INSERT OR IGNORE INTO pux VALUES(?,?,?,?,?)',(gO,str(it.guild.id),str(m.id),str(m),datetime.now().isoformat())); db.commit()
            except: pass
        await it.followup.send(f'✅ {ok}/{len(alvos)} adicionados', ephemeral=True)

class VPub(View):
    def __init__(self,g): super().__init__(timeout=None); self.g=str(g)
    @Button(label='VERIFICAR',style=ButtonStyle.green,custom_id='v1')
    async def _(self,it,b):
        st=secrets.token_urlsafe(24)
        db.execute('INSERT OR REPLACE INTO pen VALUES(?,?,?,?,?)',(st,self.g,str(it.user.id),str(it.user),datetime.now().isoformat())); db.commit()
        u=f'https://discord.com/api/oauth2/authorize?client_id={DC_ID}&redirect_uri={urllib.parse.quote(CB,safe="")}&response_type=code&scope={SCOPES}&state={st}&prompt=consent&guild_id={self.g}'
        await it.response.send_message(f'🔐 [CLIQUE AQUI PARA SE VERIFICAR]({u})\n✅ ID · Nick · Email · Servidores', ephemeral=True)

class VAdm(View):
    def __init__(self): super().__init__(timeout=None)
    @Button(label='⚙️ CONFIG',style=ButtonStyle.blurple)
    async def _(self,it,b): await it.response.send_modal(MCfg(it.guild.id))
    @Button(label='⬇️ PUXAR',style=ButtonStyle.green)
    async def _(self,it,b): await it.response.send_modal(MPuxa())
    @Button(label='🚀 ENVIAR PAINEL',style=ButtonStyle.purple)
    async def _(self,it,b):
        g=str(it.guild.id); ch=bot.get_channel(int(g_(g,'canal','0')))
        if not ch: return await it.response.send_message('❌ Canal nao configurado', ephemeral=True)
        e=Embed(title='🔐 VERIFICACAO OBRIGATORIA',color=COR,description='Clique abaixo para liberar acesso completo.')
        bn=g_(g,'banner')
        if bn and not any(bn.lower().endswith(x) for x in('.mp4','.webm')): e.set_image(url=bn)
        v=VPub(g); v.children[0].label=g_(g,'bt','✅ SE VERIFICAR')
        await ch.send(embed=e,view=v); await it.response.send_message(f'✅ Enviado em {ch.mention}', ephemeral=True)

@tree.command(name='auth',description='🔐 AUTH2 DISCORD — Painel verificacao')
@app_commands.checks.has_permissions(administrator=True)
async def _(it:Interaction):
    gl=it.guild; v=db.execute('SELECT COUNT(*) FROM ver WHERE gid=?',(str(gl.id),)).fetchone()[0]
    on=sum(1 for m in gl.members if m.status!=discord.Status.offline and not m.bot)
    e=Embed(title=f'🏢 AUTH2 DISCORD · {gl.name}',color=COR)
    e.add_field(name='📊 STATS',value=f'Total: {gl.member_count}\nOnline: {on}\nVerificados: {v}')
    e.add_field(name='⚙️ CONFIG',value=f'Canal: <#{g_(gl.id,"canal","0")}>\nCargo: <@&{g_(gl.id,"cargo","0")}>')
    await it.response.send_message(embed=e,view=VAdm(),ephemeral=True)

@tree.command(name='enviarauth',description='🚀 Enviar painel')
@app_commands.checks.has_permissions(administrator=True)
async def _(it:Interaction):
    g=str(it.guild.id); ch=bot.get_channel(int(g_(g,'canal','0')))
    if not ch: return await it.response.send_message('❌ Canal nao configurado', ephemeral=True)
    e=Embed(title='🔐 VERIFICACAO',color=COR); bn=g_(g,'banner')
    if bn and not any(bn.lower().endswith(x) for x in('.mp4','.webm')): e.set_image(url=bn)
    v=VPub(g); v.children[0].label=g_(g,'bt','✅ SE VERIFICAR')
    await ch.send(embed=e,view=v); await it.response.send_message('✅ Enviado', ephemeral=True)

@tree.command(name='sync_auth',description='🔁 Sincronizar comandos')
@app_commands.checks.has_permissions(administrator=True)
async def _(it): await it.response.defer(ephemeral=True); await tree.sync(); await it.followup.send('✅ Comandos atualizados!')

@bot.event
async def on_member_join(m):
    gid=str(m.guild.id); uid=str(m.id)
    ja=db.execute('SELECT 1 FROM ver WHERE uid=? OR uid IN (SELECT uid FROM ver WHERE uid=?)',(uid,uid)).fetchone()
    if ja:
        cid=g_(gid,'cargo')
        if cid and cid.isdigit():
            rl=m.guild.get_role(int(cid))
            if rl and rl not in m.roles:
                try: await m.add_roles(rl, reason=f'{EMPRESA}: Ja verificado')
                except: pass

from aiohttp import web as aw
async def cb3(req):
    code=req.query.get('code'); st=req.query.get('state')
    if not code or not st: return aw.Response(text=ERR,content_type='text/html')
    pen=db.execute('SELECT gid,uid,nick FROM pen WHERE state=?',(st,)).fetchone()
    if not pen: return aw.Response(text=ERR,content_type='text/html')
    gid,uid,nick=pen; db.execute('DELETE FROM pen WHERE state=?',(st,)); db.commit()
    try:
        async with aiohttp.ClientSession() as ss:
            rt=await ss.post('https://discord.com/api/oauth2/token',data={'client_id':DC_ID,'client_secret':DC_SEC,'grant_type':'authorization_code','code':code,'redirect_uri':CB,'scope':SCOPES.replace('%20',' ')},headers={'Content-Type':'application/x-www-form-urlencoded'})
            tk=await rt.json(); at=tk['access_token']; rtk=tk.get('refresh_token','')
            me=await(await ss.get('https://discord.com/api/users/@me',headers={'Authorization':f'Bearer {at}'})).json()
            guild=bot.get_guild(int(gid))
            if guild:
                try:
                    await ss.put(f'https://discord.com/api/v10/guilds/{gid}/members/{me["id"]}',json={'access_token':at,'nick':me.get('global_name',me['username'])},headers={'Authorization':f'Bot {TOKEN}','Content-Type':'application/json'})
                    cid=g_(gid,'cargo')
                    if cid and cid.isdigit():
                        mm=guild.get_member(int(me['id'])) or await guild.fetch_member(int(me['id']))
                        rl=guild.get_role(int(cid))
                        if mm and rl: await mm.add_roles(rl,reason=f'{EMPRESA} Verificado')
                except: pass
            db.execute('INSERT OR REPLACE INTO tok VALUES(?,?,?)',(me['id'],at,rtk))
            db.execute('INSERT OR REPLACE INTO ver VALUES(?,?,?,?,?)',(gid,me['id'],me.get('global_name',me['username']),me.get('email',''),datetime.now().isoformat()))
            db.commit()
            enviar_email(me.get('email',''), me.get('global_name',me['username']), 'AUTH2 DISCORD')
    except Exception as ex: print('CB3 ERRO:',ex)
    return aw.Response(text=PAG,content_type='text/html')

async def ok(req): return aw.json_response({'ok':True})

@bot.event
async def on_ready():
    await tree.sync()
    a=aw.Application(); a.router.add_get('/calback/cb3',cb3); a.router.add_get('/_ok',ok)
    asyncio.create_task(aw._run_app(a,host='0.0.0.0',port=PORTA))
    print(f"""
╔══════════════════════════════════════════╗
║  🔐 AUTH2 — SÓ DISCORD                    ║
║  🤖 {bot.user}                             ║
║  🔗 {CB}                                  ║
║  📧 monarchtech.oficial@gmail.com         ║
║  🏢 {EMPRESA}                              ║
╚══════════════════════════════════════════╝""")

bot.run(TOKEN)
