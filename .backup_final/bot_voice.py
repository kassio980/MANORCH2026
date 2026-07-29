import os,discord,sqlite3
from discord.ext import commands
from discord import app_commands,Embed
TOKEN=os.getenv("TOKEN_VOZ","")
DONO=int(os.getenv("ID_DONO","0"))
SERVIDOR=int(os.getenv("SERVIDOR_OFICIAL","1531365460212322497"))
db=sqlite3.connect("limpeza.db",check_same_thread=False)
db.execute("CREATE TABLE IF NOT EXISTS cfg(chave TEXT PRIMARY KEY,valor TEXT)")
db.commit()

intents=discord.Intents.all()
bot=commands.Bot(command_prefix="v!",intents=intents)
tree=bot.tree

@bot.event
async def on_guild_join(g):
    if g.id != SERVIDOR:
        await g.leave()
        return

@tree.command(name="conectar_voz")
async def conectar(it,canal:discord.VoiceChannel):
    if it.user.id != DONO: return await it.response.send_message("❌ APENAS DONO",ephemeral=True)
    await canal.connect()
    await it.response.send_message(f"✅ CONECTADO EM: {canal.name}",ephemeral=True)

@tree.command(name="desconectar_voz")
async def desconectar(it):
    if it.user.id != DONO: return await it.response.send_message("❌ APENAS DONO",ephemeral=True)
    if bot.voice_clients: await bot.voice_clients[0].disconnect()
    await it.response.send_message("✅ DESCONECTADO",ephemeral=True)

$PADRAO_COMANDO

@bot.event
async def on_ready():
    print("🎙️ MONARCH VOICE TECH — ONLINE")
    await bot.tree.sync(guild=discord.Object(id=SERVIDOR))

bot.run(TOKEN)
