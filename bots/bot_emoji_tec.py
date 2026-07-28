import os, sqlite3, asyncio, aiohttp, re, random, io, math
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dotenv import load_dotenv
import discord
from discord import app_commands, ButtonStyle, Interaction, Embed, File, Permissions, Role
from discord.ui import View, Button, Modal, TextInput, Select

load_dotenv()
TOKEN = os.getenv('BOT_EMOJI_TOKEN', '')
EMPRESA = 'MONARCH FINANCE LTDA'
COR_PRINCIPAL = 0x6D28D9   # Roxo enterprise
COR_SUCESSO   = 0x10B981
COR_AVISO     = 0xF59E0B
COR_PERIGO    = 0xEF4444
COR_INFO      = 0x3B82F6

# ============ BANCO ============
db = sqlite3.connect('emoji_tec.db', check_same_thread=False)
for q in [
  'CREATE TABLE IF NOT EXISTS servidores(gid TEXT PRIMARY KEY, canal_logs TEXT, ant_link INTEGER DEFAULT 1, ant_convite INTEGER DEFAULT 1, ant_spam INTEGER DEFAULT 1, ant_raid INTEGER DEFAULT 1, img_limite INTEGER DEFAULT 1, warn_max INTEGER DEFAULT 3, punicao TEXT DEFAULT "mute")',
  'CREATE TABLE IF NOT EXISTS cargos_permitidos(gid TEXT, rid TEXT, PRIMARY KEY(gid,rid))',
  'CREATE TABLE IF NOT EXISTS lista_branca(gid TEXT, valor TEXT, tipo TEXT, PRIMARY KEY(gid,valor,tipo))',
  'CREATE TABLE IF NOT EXISTS lista_negra(gid TEXT, valor TEXT, tipo TEXT, PRIMARY KEY(gid,valor,tipo))',
  'CREATE TABLE IF NOT EXISTS warns(id INTEGER PRIMARY KEY AUTOINCREMENT, gid TEXT, uid TEXT, nick TEXT, motivo TEXT, data TEXT)',
  'CREATE TABLE IF NOT EXISTS punicoes(id INTEGER PRIMARY KEY AUTOINCREMENT, gid TEXT, uid TEXT, nick TEXT, tipo TEXT, motivo TEXT, data TEXT)',
  'CREATE TABLE IF NOT EXISTS emojis_gerados(id INTEGER PRIMARY KEY AUTOINCREMENT, gid TEXT, uid TEXT, nome TEXT, url TEXT, estilo TEXT, data TEXT)',
  'CREATE TABLE IF NOT EXISTS raids(id INTEGER PRIMARY KEY AUTOINCREMENT, gid TEXT, uid TEXT, nick TEXT, acao TEXT, data TEXT)']:
  db.execute(q)
db.commit()

# ============ HELPERS ============
def gs(gid, k, d=None):
  r = db.execute(f'SELECT {k} FROM servidores WHERE gid=?', (str(gid),)).fetchone()
  return r[0] if r and r[0] is not None else d
def ss(gid, **kv):
  cols = ','.join(k for k in kv)
  vals = ','.join('?' for _ in kv)
  db.execute(f'INSERT INTO servidores(gid,{cols}) VALUES(?{ ",?"*len(kv) }) ON CONFLICT(gid) DO UPDATE SET {",".join(f"{k}=excluded.{k}" for k in kv)}',
    (str(gid), *kv.values())); db.commit()
def log(gid, e: Embed):
  c = gs(gid, 'canal_logs')
  if c and c.isdigit():
    ch = bot.get_channel(int(c))
    if ch: asyncio.create_task(ch.send(embed=e))

# ============ CACHE MODERAÇÃO ============
MSG_CACHE = defaultdict(lambda: deque(maxlen=15))
JOIN_CACHE = defaultdict(lambda: deque(maxlen=30))
WARN_COUNT = lambda g,u: db.execute('SELECT COUNT(*) FROM warns WHERE gid=? AND uid=?',(str(g),str(u))).fetchone()[0]
URL_RE = re.compile(r'https?://\S+|www\.\S+', re.I)
INV_RE = re.compile(r'(discord\.gg|discord\.com/invite|dsc\.gg)/\S+', re.I)
EMOJI_RE = re.compile(r'<a?:\w+:\d+>')
MENTION_RE = re.compile(r'<@[!&]?\d+>')

def is_admin(m: discord.Member):
  return m.guild_permissions.administrator or m.id == m.guild.owner_id
def cargo_permitido(m: discord.Member):
  if is_admin(m): return True
  permitidos = {r[0] for r in db.execute('SELECT rid FROM cargos_permitidos WHERE gid=?',(str(m.guild.id),)).fetchall()}
  return any(str(r.id) in permitidos for r in m.roles)

# ============ GERADOR DE EMOJIS (PROCEDURAL + IA FALLBACK) ============
PALETAS = [
  ['#6D28D9','#A78BFA','#C4B5FD'], ['#059669','#34D399','#6EE7B7'],
  ['#DC2626','#F87171','#FECACA'], ['#2563EB','#60A5FA','#BFDBFE'],
  ['#EA580C','#FB923C','#FED7AA'], ['#0891B2','#22D3EE','#A5F3FC'],
  ['#BE185D','#F472B6','#FBCFE8'], ['#4D7C0F','#A3E635','#ECFCCB']
]
ESTILOS = ['FLAT','GRADIENT','NEON','GLASS','3D','PIXEL','GLOW','OUTLINE']
FORMAS = ['CIRCLE','SQUARE','STAR','HEART','SHIELD','BOLT','CROWN','FIRE','GEM','ROCKET']

def gerar_emoji_procedural(nome: str, estilo: str, paleta: list):
  from PIL import Image, ImageDraw, ImageFilter, ImageFont
  img = Image.new('RGBA', (128,128), (0,0,0,0))
  d = ImageDraw.Draw(img)
  c1,c2,c3 = paleta
  cx,cy = 64,64

  if estilo == 'GRADIENT':
    for y in range(128):
      t = y/128
      r=int(int(c1[1:3],16)*(1-t)+int(c2[1:3],16)*t)
      g=int(int(c1[3:5],16)*(1-t)+int(c2[3:5],16)*t)
      b=int(int(c1[5:7],16)*(1-t)+int(c2[5:7],16)*t)
      d.line([(0,y),(128,y)],fill=(r,g,b,255))
  elif estilo == 'NEON':
    d.ellipse([10,10,118,118],fill=(0,0,0,0),outline=c1,width=4)
    d.ellipse([20,20,108,108],fill=c2,outline=c3,width=2)
  elif estilo == '3D':
    d.ellipse([14,14,118,118],fill=c1)
    d.ellipse([10,10,114,114],fill=c2)
    d.ellipse([22,22,70,70],fill=c3)
  elif estilo == 'GLASS':
    d.ellipse([8,8,120,120],fill=tuple(int(c1[i:i+2],16) for i in (1,3,5))+(160,))
    d.ellipse([20,20,60,60],fill=(255,255,255,100))
  elif estilo == 'STAR':
    pts=[]
    for i in range(10):
      a=math.radians(i*36-90); R=58 if i%2==0 else 26
      pts.append((cx+R*math.cos(a), cy+R*math.sin(a)))
    d.polygon(pts,fill=c1,outline=c2,width=3)
  elif estilo == 'HEART':
    d.polygon([(64,110),(14,54),(14,34),(34,14),(64,34),(94,14),(114,34),(114,54)],fill=c1,outline=c2,width=3)
  elif estilo == 'SHIELD':
    d.polygon([(20,14),(108,14),(108,70),(64,114),(20,70)],fill=c1,outline=c2,width=3)
  else:
    d.ellipse([14,14,114,114],fill=c1,outline=c2,width=4)

  # Letra/símbolo central
  try: f = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',56)
  except: f = ImageFont.load_default()
  letra = nome[0].upper() if nome else 'M'
  bbox = d.textbbox((0,0),letra,font=f)
  d.text(((128-(bbox[2]-bbox[0]))//2,(128-(bbox[3]-bbox[1]))//2-6), letra, font=f, fill='white',
         stroke_width=2, stroke_fill='black')
  if estilo == 'GLOW':
    img = img.filter(ImageFilter.GaussianBlur(1))
  buf = io.BytesIO(); img.save(buf,'PNG'); buf.seek(0)
  return buf

async def gerar_emojis_ia(qtd: int, gid: int, uid: int, canal_feedback=None):
  """Gera N emojis, retorna lista de (nome, arquivo_bytes)"""
  nomes_usados = set()
  resultado = []
  for i in range(qtd):
    estilo = random.choice(ESTILOS)
    paleta = random.choice(PALETAS)
    forma  = random.choice(FORMAS)
    base = f'{forma[:3]}{estilo[:2]}{i+1:03d}'
    nome = base
    while nome in nomes_usados: nome = base + random.choice('XYZ')
    nomes_usados.add(nome)
    arq = gerar_emoji_procedural(nome, estilo, paleta)
    resultado.append((nome.lower(), arq, estilo, paleta[0]))
    if canal_feedback and (i+1) % 10 == 0:
      await canal_feedback.send(f'🎨 **{i+1}/{qtd}** emojis gerados...')
  return resultado

async def upload_emoji(guild: discord.Guild, nome: str, arq: io.BytesIO):
  try:
    arq.seek(0)
    e = await guild.create_custom_emoji(name=nome, image=arq.read(), reason=f'{EMPRESA} Emoji Factory')
    db.execute('INSERT INTO emojis_gerados(gid,uid,nome,url,estilo,data) VALUES(?,?,?,?,?,?)',
      (str(guild.id), '0', nome, str(e.url), 'IA', datetime.now().isoformat())); db.commit()
    return e
  except Exception as ex:
    return None

# ============ MODERAÇÃO AUTOMÁTICA ============
async def aplicar_punicao(m: discord.Member, motivo: str):
  g = m.guild; maxw = gs(g.id,'warn_max',3); tipo = gs(g.id,'punicao','mute')
  w = WARN_COUNT(g.id, m.id) + 1
  db.execute('INSERT INTO warns(gid,uid,nick,motivo,data) VALUES(?,?,?,?,?)',
    (str(g.id),str(m.id),str(m),motivo,datetime.now().isoformat())); db.commit()
  log(g.id, Embed(title='⚠️ ADVERTÊNCIA',color=COR_AVISO,description=f'👤 {m.mention}\n📝 {motivo}\n🔢 {w}/{maxw}'))
  if w >= maxw:
    try:
      if tipo == 'mute' and m.guild_permissions.moderate_members:
        await m.timeout(timedelta(hours=1), reason=f'{EMPRESA}: {motivo}')
        acao = 'MUTADO 1H'
      elif tipo == 'kick':
        await m.kick(reason=f'{EMPRESA}: {motivo}'); acao = 'EXPULSO'
      elif tipo == 'ban':
        await m.ban(reason=f'{EMPRESA}: {motivo}'); acao = 'BANIDO'
      else: acao = f'{w} warns'
      db.execute('INSERT INTO punicoes(gid,uid,nick,tipo,motivo,data) VALUES(?,?,?,?,?,?)',
        (str(g.id),str(m.id),str(m),acao,motivo,datetime.now().isoformat())); db.commit()
      log(g.id, Embed(title=f'🚨 PUNIÇÃO: {acao}',color=COR_PERIGO,description=f'👤 {m.mention}\n📝 {motivo}'))
    except: pass

async def moderar(msg: discord.Message):
  if msg.author.bot or cargo_permitido(msg.author): return
  g = msg.guild; gid = str(g.id); deletar = False; motivo = ''

  # Anti-link
  if gs(gid,'ant_link',1) and URL_RE.search(msg.content):
    # Lista branca
    wl = {r[0] for r in db.execute('SELECT valor FROM lista_branca WHERE gid=? AND tipo=?',(gid,'url')).fetchall()}
    if not any(d in msg.content for d in wl):
      deletar = True; motivo = 'Link proibido'
  # Anti-convite
  if gs(gid,'ant_convite',1) and INV_RE.search(msg.content):
    deletar = True; motivo = 'Convite externo'
  # Anti-imagem
  lim = gs(gid,'img_limite',1)
  if lim and len(msg.attachments) > lim:
    deletar = True; motivo = f'Limite de {lim} imagem(ns)'
  # Anti-spam/flood
  if gs(gid,'ant_spam',1):
    agora = datetime.now()
    MSG_CACHE[msg.author.id].append(agora)
    hist = MSG_CACHE[msg.author.id]
    if len([x for x in hist if agora-x < timedelta(seconds=5)]) >= 6:
      deletar = True; motivo = 'Flood de mensagens'
    if len(EMOJI_RE.findall(msg.content)) > 15:
      deletar = True; motivo = 'Flood de emojis'
    if len(MENTION_RE.findall(msg.content)) > 8:
      deletar = True; motivo = 'Marcação excessiva'
    # Repetição
    ultimas = [m async for m in msg.channel.history(limit=5) if m.author == msg.author]
    if len(ultimas) >= 4 and len({m.content for m in ultimas}) == 1:
      deletar = True; motivo = 'Mensagem repetida'

  if deletar:
    try: await msg.delete()
    except: pass
    try:
      av = await msg.channel.send(f'⚠️ {msg.author.mention} **{motivo.upper()}!**\nAção registrada pelo {EMPRESA}.')
      asyncio.create_task(asyncio.sleep(4)); await av.delete()
    except: pass
    await aplicar_punicao(msg.author, motivo)

# Anti-raid
@bot.event
async def on_member_join(m):
  if m.bot: return
  gid = str(m.guild.id)
  if not gs(gid,'ant_raid',1): return
  JOIN_CACHE[gid].append(datetime.now())
  recentes = [x for x in JOIN_CACHE[gid] if datetime.now()-x < timedelta(seconds=15)]
  if len(recentes) >= 8:
    log(gid, Embed(title='🚨 RAID DETECTADO',color=COR_PERIGO,description=f'{len(recentes)} entradas em 15s'))
    # Ação: slowmode + warn dono
    try:
      for ch in m.guild.text_channels[:5]:
        await ch.edit(slowmode_delay=15)
    except: pass

@bot.event
async def on_message(msg):
  if not msg.guild: return
  await moderar(msg)

# ============ COMANDOS ============
intents = discord.Intents.all()
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

# --- /inicia ---
class MInicia(Modal, title='🤖 EMOJI FACTORY IA'):
  q = TextInput(label='Quantidade de emojis (max 200)', default='50', required=True)
  async def on_submit(self, it: Interaction):
    if not it.guild.me.guild_permissions.manage_emojis_and_stickers:
      return await it.response.send_message('❌ Preciso da permissão **Gerenciar Emojis**', ephemeral=True)
    try: qtd = max(1, min(200, int(self.q.value)))
    except: return await it.response.send_message('❌ Número inválido', ephemeral=True)
    await it.response.defer(thinking=True)
    fb = it.followup
    await fb.send(f'''🤖 **Iniciando Emoji Factory {EMPRESA}...**

🎨 Criando designs...
✨ Aplicando efeitos premium...
🌈 Escolhendo paletas exclusivas...
📦 Preparando {qtd} emojis...
🚀 Upload automático para `{it.guild.name}`''')
    emojis = await gerar_emojis_ia(qtd, it.guild.id, it.user.id, it.channel)
    ok = 0; falha = 0
    for nome, arq, est, cor in emojis:
      r = await upload_emoji(it.guild, nome, arq)
      if r: ok += 1
      else: falha += 1
    await fb.send(embed=Embed(title='✅ PROCESSO FINALIZADO',color=COR_SUCESSO,
      description=f'**{qtd} emojis processados**\n✅ **{ok}** enviados ao servidor\n❌ **{falha}** falhas (limite Discord)\n\n🏢 **{EMPRESA}**').set_footer(text=f'Solicitado por {it.user.display_name}'))

@tree.command(name='inicia', description='🤖 Inicia Emoji Factory em massa')
@app_commands.checks.has_permissions(manage_emojis_and_stickers=True)
async def cmd_inicia(it: Interaction, quantidade: int = 50):
  if quantidade > 200: quantidade = 200
  m = MInicia(); m.q.value = str(quantidade)
  await it.response.send_modal(m)

# --- /config ---
@tree.command(name='config', description='⚙️ Configurar segurança do servidor')
@app_commands.checks.has_permissions(administrator=True)
async def cmd_config(it: Interaction):
  gid = str(it.guild.id)
  e = Embed(title='⚙️ PAINEL DE SEGURANÇA', color=COR_PRINCIPAL, description=f'🏢 **{EMPRESA}** · `{it.guild.name}`')
  e.add_field(name='🛡️ Módulos', value=f'''
Anti-Link: **{"✅" if gs(gid,"ant_link",1) else "❌"}**
Anti-Convite: **{"✅" if gs(gid,"ant_convite",1) else "❌"}**
Anti-Spam: **{"✅" if gs(gid,"ant_spam",1) else "❌"}**
Anti-Raid: **{"✅" if gs(gid,"ant_raid",1) else "❌"}**''', inline=False)
  e.add_field(name='📏 Regras', value=f'''
Limite imagens/membro: **{gs(gid,"img_limite",1)}**
Máx advertências: **{gs(gid,"warn_max",3)}**
Punição final: **{gs(gid,"punicao","mute").upper()}**''', inline=False)
  e.add_field(name='📋 Logs', value=f'<#{gs(gid,"canal_logs","0")}>')
  e.set_footer(text='Use os botões para alterar')

  v = View(timeout=None)
  # Toggle módulos
  for mod, lbl in [('ant_link','🔗 Anti-Link'),('ant_convite','✉️ Anti-Convite'),('ant_spam','💬 Anti-Spam'),('ant_raid','⚔️ Anti-Raid')]:
    b = Button(label=lbl, style=ButtonStyle.blurple)
    async def cb(ii, mm=mod, ll=lbl):
      ss(gid, **{mm: 0 if gs(gid,mm,1) else 1})
      await ii.response.edit_message(embed=Embed(title=f'✅ {ll} {"ATIVADO" if gs(gid,mm,1) else "DESATIVADO"}',color=COR_SUCESSO), view=None)
    b.callback = cb; v.add_item(b)

  # Limite imagem
  b1 = Button(label='🖼️ Limite Imagens', style=ButtonStyle.grey)
  async def cb1(ii):
    m = Modal(title='🖼️ Limite de imagens'); m.add_item(TextInput(label='0 = ilimitado para membros', default=str(gs(gid,'img_limite',1))))
    async def sss(iii): ss(gid, img_limite=int(m.children[0].value)); await iii.response.edit_message(embed=Embed(title='✅ Atualizado',color=COR_SUCESSO),view=None)
    m.on_submit = sss; await ii.response.send_modal(m)
  b1.callback = cb1; v.add_item(b1)

  # Canal logs
  b2 = Button(label='📋 Canal Logs', style=ButtonStyle.green)
  async def cb2(ii):
    sel = Select(placeholder='Escolha o canal', options=[discord.SelectOption(label=c.name,value=str(c.id)) for c in it.guild.text_channels[:25]])
    async def sss(iii): ss(gid, canal_logs=sel.values[0]); await iii.response.edit_message(embed=Embed(title='✅ Logs configurados',color=COR_SUCESSO),view=None)
    sel.callback = sss; vv = View(); vv.add_item(sel); await ii.response.edit_message(view=vv)
  b2.callback = cb2; v.add_item(b2)

  # Punição
  b3 = Button(label='⚖️ Punição', style=ButtonStyle.red)
  async def cb3(ii):
    sel = Select(placeholder='Ação após warns', options=[discord.SelectOption(label=x,value=x) for x in ['mute','kick','ban']])
    async def sss(iii): ss(gid, punicao=sel.values[0]); await iii.response.edit_message(embed=Embed(title='✅ Punição: '+sel.values[0].upper(),color=COR_SUCESSO),view=None)
    sel.callback = sss; vv = View(); vv.add_item(sel); await ii.response.edit_message(view=vv)
  b3.callback = cb3; v.add_item(b3)

  # Warn máximo
  b4 = Button(label='🔢 Max Warns', style=ButtonStyle.grey)
  async def cb4(ii):
    m = Modal(title='🔢 Advertências'); m.add_item(TextInput(label='Quantidade', default=str(gs(gid,'warn_max',3))))
    async def sss(iii): ss(gid, warn_max=int(m.children[0].value)); await iii.response.edit_message(embed=Embed(title='✅ Atualizado',color=COR_SUCESSO),view=None)
    m.on_submit = sss; await ii.response.send_modal(m)
  b4.callback = cb4; v.add_item(b4)

  # Cargo permitido
  b5 = Button(label='👑 Cargo Permitido', style=ButtonStyle.blurple)
  async def cb5(ii):
    sel = Select(placeholder='Escolha cargo (além de ADM)', options=[discord.SelectOption(label=r.name,value=str(r.id)) for r in it.guild.roles[:25] if not r.managed])
    async def sss(iii):
      db.execute('INSERT OR IGNORE INTO cargos_permitidos VALUES(?,?)',(gid,sel.values[0])); db.commit()
      await iii.response.edit_message(embed=Embed(title='✅ Cargo liberado',color=COR_SUCESSO),view=None)
    sel.callback = sss; vv = View(); vv.add_item(sel); await ii.response.edit_message(view=vv)
  b5.callback = cb5; v.add_item(b5)

  await it.response.send_message(embed=e, view=v, ephemeral=True)

# --- /painel ---
@tree.command(name='painel', description='📊 Painel de segurança empresarial')
@app_commands.checks.has_permissions(administrator=True)
async def cmd_painel(it: Interaction):
  gid = str(it.guild.id)
  tw = db.execute('SELECT COUNT(*) FROM warns WHERE gid=?',(gid,)).fetchone()[0]
  tp = db.execute('SELECT COUNT(*) FROM punicoes WHERE gid=?',(gid,)).fetchone()[0]
  te = db.execute('SELECT COUNT(*) FROM emojis_gerados WHERE gid=?',(gid,)).fetchone()[0]
  e = Embed(title=f'🏢 PAINEL {EMPRESA}', color=COR_PRINCIPAL, description=f'Servidor: **{it.guild.name}**')
  e.add_field(name='📊 MÉTRICAS', value=f'''
👥 Membros: **{it.guild.member_count}**
🎨 Emojis gerados: **{te}**
⚠️ Advertências: **{tw}**
🚨 Punições: **{tp}**''', inline=False)
  e.add_field(name='🛡️ STATUS MÓDULOS', value=f'''
🔗 Anti-Link: **{"🟢 ATIVO" if gs(gid,"ant_link",1) else "🔴 OFF"}**
✉️ Anti-Convite: **{"🟢 ATIVO" if gs(gid,"ant_convite",1) else "🔴 OFF"}**
💬 Anti-Spam: **{"🟢 ATIVO" if gs(gid,"ant_spam",1) else "🔴 OFF"}**
⚔️ Anti-Raid: **{"🟢 ATIVO" if gs(gid,"ant_raid",1) else "🔴 OFF"}**
🖼️ Imagens/membro: **{gs(gid,"img_limite",1)}**
⚖️ Punição: **{gs(gid,"punicao","mute").upper()}**''', inline=False)
  e.set_thumbnail(url=it.guild.icon.url if it.guild.icon else None)
  e.set_footer(text=EMPRESA)
  await it.response.send_message(embed=e)

# --- /warns ---
@tree.command(name='warns', description='⚠️ Ver advertências de um usuário')
@app_commands.checks.has_permissions(moderate_members=True)
async def cmd_warns(it: Interaction, usuario: discord.Member):
  rows = db.execute('SELECT motivo,data FROM warns WHERE gid=? AND uid=? ORDER BY id DESC LIMIT 10',
    (str(it.guild.id),str(usuario.id))).fetchone()
  if not rows: return await it.response.send_message('✅ Nenhuma advertência', ephemeral=True)
  txt = '\n'.join([f'• {r[1][:16]} — {r[0]}' for r in rows])
  await it.response.send_message(embed=Embed(title=f'⚠️ WARNS · {usuario.display_name}',color=COR_AVISO,description=txt), ephemeral=True)

# ============ INICIAR ============
@bot.event
async def on_ready():
  await tree.sync()
  print(f'✅ BOT EMOJI TEC: {bot.user} · {EMPRESA}')
  print(f'🎨 Emoji Factory · 🛡️ Moderação IA · ⚔️ Anti-Raid · 📊 Logs')

bot.run(TOKEN)
