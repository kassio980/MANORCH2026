# ==================================================
# 🎙️ MONARCH VOICE™ — SISTEMA COMPLETO
# 🎧 Central de Voz | 🛡️ Anti-Link/Flood/Imagem | 📜 Logs | ⚙️ Config
# ==================================================
import os,re,sqlite3,time,asyncio
from datetime import datetime
from dotenv import load_dotenv
import discord
from discord import app_commands,Interaction,Embed,Color,ButtonStyle
from discord.ui import View,Button,Modal,TextInput,Select

load_dotenv()
TOKEN=os.getenv("TOKEN_VOICE")
ID_DONO=int(os.getenv("ID_DONO","0"))
GUILD=int(os.getenv("SERVIDOR_OFICIAL","0"))
EMPRESA=os.getenv("EMPRESA","MONARCH VOICE™")
COR=0x00BFFF

DB="dados/voice.db"
def db():c=sqlite3.connect(DB);c.row_factory=sqlite3.Row;return c
def init():
    with db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS cfg(chave TEXT PRIMARY KEY,valor TEXT);
        CREATE TABLE IF NOT EXISTS logs(id INTEGER PRIMARY KEY,tipo TEXT,user TEXT,canal TEXT,msg TEXT,data TEXT);
        CREATE TABLE IF NOT EXISTS bots_autorizados(id INTEGER PRIMARY KEY,nome TEXT,conectado INTEGER DEFAULT 0,canal INTEGER);
        CREATE TABLE IF NOT EXISTS warns(id INTEGER PRIMARY KEY,uid TEXT,nick TEXT,motivo TEXT,mod TEXT,data TEXT);
        """)
        padrao=[
            ("CANAL_VOZ","0"),("ANTI_LINK","1"),("ANTI_FLOOD","1"),("ANTI_IMAGEM","1"),
            ("FLOOD_MAX","5"),("FLOOD_TEMPO","10"),("TIMEOUT_FLOOD","5"),("CANAL_LOGS","0"),
            ("AUTO_RECON","1"),("PERM_ADMIN","manage_guild"),
        ]
        c.executemany("INSERT OR IGNORE INTO cfg VALUES(?,?)",padrao);c.commit()
init()

def cfg(k,d=None):r=db().execute("SELECT valor FROM cfg WHERE chave=?",(k,)).fetchone();return r[0] if r else d
def setc(k,v):db().execute("INSERT OR REPLACE INTO cfg VALUES(?,?)",(k,v));db().commit()
def log(t,u="",c="",m=""):db().execute("INSERT INTO logs VALUES(NULL,?,?,?,?,?)",(t,u,c,m,datetime.now().isoformat()));db().commit()
def emb(t="",d=""):e=Embed(title=t,description=d,color=COR,timestamp=datetime.now());e.set_footer(text=EMPRESA);return e
def tem_perm(i):return i.user.guild_permissions.manage_guild or i.user.id==ID_DONO

intents=discord.Intents.all()
bot=discord.Client(intents=intents);tree=app_commands.CommandTree(bot)

CACHE_FLOOD={}
URL_RE=re.compile(r'https?://\S+|www\.\S+|discord\.gg/\S+')
CONEXAO_DESDE={}

# ========== SISTEMA DE VOZ ==========
def bots_autorizados(g):return [m for m in g.members if m.bot and str(m.id) in [str(x['id']) for x in db().execute("SELECT id FROM bots_autorizados").fetchall()]]

@tree.command(name="conectar",description="🎧 Conectar todos BOTs autorizados num canal",guild=discord.Object(id=GUILD))
@app_commands.describe(canal="ID ou menção do canal")
async def cmd_conectar(i,canal:discord.VoiceChannel):
    if not tem_perm(i):return await i.response.send_message("❌ Sem permissão (Gerir Servidor)",ephemeral=True)
    bots=bots_autorizados(i.guild);conectados=0
    for b in bots:
        try:
            if b==i.guild.me:
                if not b.voice:await canal.connect(self_deaf=True)
                else:await b.voice.move_to(canal)
            else:
                await b.move_to(canal)
            db().execute("UPDATE bots_autorizados SET conectado=1,canal=? WHERE id=?",(canal.id,b.id));db().commit()
            conectados+=1
        except:pass
    CONEXAO_DESDE[canal.id]=time.time()
    log("CONECTAR",str(i.user),canal.name,f"{conectados} bots")
    await i.response.send_message(embed=emb("🎧 CONECTADO",f"✅ **{conectados}/{len(bots)}** BOTs em **{canal.name}**\n🔄 Reconexão automática ativada"))

@tree.command(name="desconectar",description="🔌 Desconectar todos BOTs",guild=discord.Object(id=GUILD))
async def cmd_desconectar(i):
    if not tem_perm(i):return
    bots=[m for m in i.guild.members if m.bot and m.voice];t=time.time()-CONEXAO_DESDE.get(i.guild.me.voice.channel.id,time.time()) if i.guild.me.voice else 0
    for b in bots:
        try:
            if b==i.guild.me:await b.voice.disconnect()
            else:await b.move_to(None)
            db().execute("UPDATE bots_autorizados SET conectado=0,canal=0 WHERE id=?",(b.id,));db().commit()
        except:pass
    log("DESCONECTAR",str(i.user),"",f"{len(bots)} bots")
    await i.response.send_message(embed=emb("🔌 DESCONECTADO",f"✅ **{len(bots)}** BOTs desconectados\n⏱️ Tempo conectado: **{int(t//60)}m {int(t%60)}s**"))

@tree.command(name="mover",description="➡️ Mover todos para outro canal",guild=discord.Object(id=GUILD))
async def cmd_mover(i,novo:discord.VoiceChannel):
    if not tem_perm(i):return
    bots=[m for m in i.guild.members if m.bot and m.voice];mov=0
    for b in bots:
        try:await b.move_to(novo);mov+=1
        except:pass
    log("MOVER",str(i.user),novo.name,f"{mov} bots")
    await i.response.send_message(f"➡️ **{mov}** BOTs movidos para **{novo.name}**")

@tree.command(name="status",description="📊 Status do sistema de voz",guild=discord.Object(id=GUILD))
async def cmd_status(i):
    g=i.guild;bots=bots_autorizados(g)
    on=sum(1 for b in bots if b.voice);off=len(bots)-on
    canal=g.me.voice.channel.name if g.me.voice else "❌ Nenhum"
    t=int((time.time()-CONEXAO_DESDE.get(g.me.voice.channel.id,time.time()))//60) if g.me.voice else 0
    await i.response.send_message(embed=emb("📊 STATUS SISTEMA DE VOZ",f"""
🟢 **Online:** {on}
🔴 **Offline:** {off}
🎧 **Canal:** {canal}
⏱️ **Tempo:** {t}min
🤖 **Total autorizados:** {len(bots)}"""))

@tree.command(name="reconnect",description="🔄 Reconectar BOTs desconectados",guild=discord.Object(id=GUILD))
async def cmd_recon(i):
    if not tem_perm(i):return
    canal=i.guild.me.voice.channel
    if not canal:return await i.response.send_message("❌ Conecte primeiro",ephemeral=True)
    rec=0
    for b in bots_autorizados(i.guild):
        if not b.voice:
            try:await b.move_to(canal);rec+=1
            except:pass
    log("RECON",str(i.user),canal.name,f"{rec} bots")
    await i.response.send_message(f"🔄 **{rec}** BOTs reconectados")

# ========== RECONEXÃO AUTOMÁTICA ==========
@bot.event
async def on_voice_state_update(m,ant,dps):
    if not cfg("AUTO_RECON")=="1":return
    if m.bot and str(m.id) in [str(x['id']) for x in db().execute("SELECT id FROM bots_autorizados").fetchall()]:
        if ant.channel and not dps.channel:
            await asyncio.sleep(2)
            try:
                if m==bot.user:await ant.channel.connect(self_deaf=True)
                else:await m.move_to(ant.channel)
                log("AUTO_RECON",str(m),ant.channel.name,"")
            except:pass

# ========== ANTI-LINK ==========
@bot.event
async def on_message(msg):
    if msg.author.bot or not msg.guild:return
    if msg.author.guild_permissions.manage_guild:return
    # ANTI-LINK
    if cfg("ANTI_LINK")=="1" and URL_RE.search(msg.content):
        try:await msg.delete()
        except:pass
        await msg.channel.send(f"🔗 {msg.author.mention} **Links proibidos!**",delete_after=5)
        log("ANTI-LINK",str(msg.author),msg.channel.name,msg.content[:100])
        if cfg("TIMEOUT_FLOOD"):
            try:await msg.author.timeout(discord.utils.utcnow()+discord.timedelta(minutes=int(cfg("TIMEOUT_FLOOD"))),reason="ANTI-LINK")
            except:pass
        return
    # ANTI-FLOOD
    if cfg("ANTI_FLOOD")=="1":
        u=str(msg.author.id);agora=time.time()
        CACHE_FLOOD[u]=[t for t in CACHE_FLOOD.get(u,[]) if agora-t<int(cfg("FLOOD_TEMPO","10"))]
        CACHE_FLOOD[u].append(agora)
        if len(CACHE_FLOOD[u])>int(cfg("FLOOD_MAX","5")):
            try:await msg.delete()
            except:pass
            await msg.channel.send(f"💬 {msg.author.mention} mutado {cfg('TIMEOUT_FLOOD')}min por flood",delete_after=5)
            try:await msg.author.timeout(discord.utils.utcnow()+discord.timedelta(minutes=int(cfg("TIMEOUT_FLOOD"))),reason="ANTI-FLOOD")
            except:pass
            log("ANTI-FLOOD",str(msg.author),msg.channel.name,f"{len(CACHE_FLOOD[u])} msgs")
            return
    # ANTI-IMAGEM
    if cfg("ANTI_IMAGEM")=="1" and msg.attachments:
        try:await msg.delete()
        except:pass
        await msg.channel.send(f"🖼️ {msg.author.mention} **Imagens/vídeos/arquivos proibidos!**",delete_after=5)
        log("ANTI-IMAGEM",str(msg.author),msg.channel.name,f"{len(msg.attachments)} arquivos")

# ========== CONFIGS ==========
class CfgModal(Modal):
    def __init__(self,k,v,t):super().__init__(title=f"⚙️ CONFIG: {t}");self.k=k
        self.t=TextInput(label="Novo valor",default=v,required=True)
    async def on_submit(self,i):
        setc(self.k,self.t.value);log("CONFIG",str(i.user),"",f"{self.k}={self.t.value}")
        await i.response.send_message(f"✅ **{self.k}** → `{self.t.value}`",ephemeral=True)

@tree.command(name="config",description="⚙️ Configurar sistema",guild=discord.Object(id=GUILD))
@app_commands.choices(opcao=[
    app_commands.Choice(name="🎧 Canal de Voz Padrão",value="CANAL_VOZ"),
    app_commands.Choice(name="🛡️ Anti-Link (1=ligado/0=desligado)",value="ANTI_LINK"),
    app_commands.Choice(name="🚫 Anti-Flood (1/0)",value="ANTI_FLOOD"),
    app_commands.Choice(name="🖼️ Anti-Imagem (1/0)",value="ANTI_IMAGEM"),
    app_commands.Choice(name="📜 Canal de Logs (ID)",value="CANAL_LOGS"),
    app_commands.Choice(name="🔄 Auto Reconexão (1/0)",value="AUTO_RECON"),
    app_commands.Choice(name="💬 Flood: max mensagens",value="FLOOD_MAX"),
    app_commands.Choice(name="⏱️ Flood: tempo segundos",value="FLOOD_TEMPO"),
    app_commands.Choice(name="⏳ Timeout flood (minutos)",value="TIMEOUT_FLOOD"),
])
async def cmd_cfg(i,opcao:str):
    if not tem_perm(i):return
    nomes={"CANAL_VOZ":"Canal Voz","ANTI_LINK":"Anti-Link","ANTI_FLOOD":"Anti-Flood","ANTI_IMAGEM":"Anti-Imagem","CANAL_LOGS":"Canal Logs","AUTO_RECON":"Auto Recon","FLOOD_MAX":"Max Msg Flood","FLOOD_TEMPO":"Tempo Flood","TIMEOUT_FLOOD":"Timeout Flood"}
    await i.response.send_modal(CfgModal(opcao,cfg(opcao,""),nomes[opcao]))

@tree.command(name="logs",description="📜 Ver últimos logs",guild=discord.Object(id=GUILD))
@app_commands.describe(limite="Quantidade (max 50)")
async def cmd_logs(i,limite:int=20):
    if not tem_perm(i):return
    r=db().execute("SELECT * FROM logs ORDER BY id DESC LIMIT ?",(min(limite,50),)).fetchall()
    t="\n".join([f"• `{x['data'][11:19]}` **{x['tipo']}** — {x['user']} — {x['msg'][:60]}" for x in r]) or "Sem logs"
    await i.response.send_message(embed=emb(f"📜 ÚLTIMOS {len(r)} LOGS",t),ephemeral=True)

@tree.command(name="autorizar_bot",description="🤖 ADICIONAR BOT na lista autorizada",guild=discord.Object(id=GUILD))
async def cmd_autbot(i,bot_id:str,nome:str):
    if not tem_perm(i):return
    db().execute("INSERT OR REPLACE INTO bots_autorizados VALUES(?,?,0,0)",(int(bot_id),nome));db().commit()
    log("AUT_BOT",str(i.user),"",f"{nome} ({bot_id})")
    await i.response.send_message(f"✅ **{nome}** autorizado!",ephemeral=True)

@tree.command(name="painel",description="📈 Painel completo do Voice",guild=discord.Object(id=GUILD))
async def cmd_painel(i):
    g=i.guild;bots=bots_autorizados(g);on=sum(1 for b in bots if b.voice)
    await i.response.send_message(embed=emb(f"🎙️ {EMPRESA} — PAINEL",f"""
🤖 **Bots autorizados:** {len(bots)}
🟢 **Conectados:** {on}
🔴 **Desconectados:** {len(bots)-on}
🎧 **Canal atual:** {g.me.voice.channel.name if g.me.voice else 'Nenhum'}

🛡️ **Proteções:**
   • Anti-Link: {'✅'if cfg('ANTI_LINK')=='1'else'❌'}
   • Anti-Flood: {'✅'if cfg('ANTI_FLOOD')=='1'else'❌'}
   • Anti-Imagem: {'✅'if cfg('ANTI_IMAGEM')=='1'else'❌'}
   • Auto-Recon: {'✅'if cfg('AUTO_RECON')=='1'else'❌'}"""))

@bot.event
async def on_ready():
    await tree.sync(guild=discord.Object(id=GUILD))
    print(f"🎙️ {EMPRESA} ONLINE — {bot.user}")

bot.run(TOKEN)
