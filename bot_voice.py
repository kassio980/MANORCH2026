import os
import discord
from discord.ext import commands
from discord import app_commands, Embed

TOKEN = os.getenv("TOKEN_VOZ", "")
DONO = int(os.getenv("ID_DONO", "0"))
SERVIDOR = int(os.getenv("SERVIDOR_OFICIAL", "1531365460212322497"))

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="v!", intents=intents)
tree = bot.tree

# SAI DE QUALQUER SERVIDOR QUE NÃO SEJA O OFICIAL
@bot.event
async def on_guild_join(g):
    if g.id != SERVIDOR:
        await g.leave()
        return

@tree.command(name="conectar_voz", description="🎙️ Conectar em canal de voz")
@app_commands.guilds(discord.Object(id=SERVIDOR))
async def conectar(it, canal: discord.VoiceChannel):
    if it.user.id != DONO:
        await it.response.send_message("❌ SOMENTE O DONO", ephemeral=True)
        return
    await canal.connect()
    await it.response.send_message(f"✅ CONECTADO EM: {canal.name}", ephemeral=True)

@tree.command(name="desconectar_voz", description="🎙️ Desconectar")
@app_commands.guilds(discord.Object(id=SERVIDOR))
async def desconectar(it):
    if it.user.id != DONO:
        await it.response.send_message("❌ SOMENTE O DONO", ephemeral=True)
        return
    if bot.voice_clients:
        await bot.voice_clients[0].disconnect()
    await it.response.send_message("✅ DESCONECTADO", ephemeral=True)

# ========== COMANDO EXCLUSIVO DO DONO ==========
@tree.command(name="configurar_tudo", description="👑 ATUALIZA TODOS OS COMANDOS")
@app_commands.guilds(discord.Object(id=SERVIDOR))
async def cmd_atualizar(it):
    if it.user.id != DONO:
        await it.response.send_message("❌ SOMENTE O DONO PODE USAR ISSO!", ephemeral=True)
        return
    await it.response.defer(ephemeral=True)
    total = await tree.sync(guild=discord.Object(id=SERVIDOR))
    msg = Embed(
        title="👑 SISTEMA CONFIGURADO!",
        description=f"✅ {len(total)} COMANDOS CARREGADOS\n🖥️ Servidor: MONARCH2026©",
        color=0xFF8C00
    )
    msg.add_field(name="VOZ", value="/conectar_voz • /desconectar_voz")
    msg.add_field(name="ADMIN", value="/configurar_tudo")
    await it.followup.send(embed=msg, ephemeral=True)
    print(f"✅ VOZ: {len(total)} comandos atualizados")

@bot.event
async def on_ready():
    print("🎙️ MONARCH VOICE TECH — ONLINE")
    await tree.sync(guild=discord.Object(id=SERVIDOR))

bot.run(TOKEN)
