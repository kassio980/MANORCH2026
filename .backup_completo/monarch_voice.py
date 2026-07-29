# ==================================================
# 🎙️ MONARCH VOICE TECH — INTEGRADO
# ==================================================
import os, discord
from discord.ext import commands
from dotenv import load_dotenv
from core.seguranca import SERVIDOR_PERMITIDO
load_dotenv()
bot = commands.Bot(command_prefix="v!",intents=discord.Intents.all())
@bot.event
async def on_guild_join(g):
    if g.id != SERVIDOR_PERMITIDO: await g.leave()
@bot.event
async def on_ready(): print("🎙️ MONARCH VOICE ONLINE")
bot.run(os.getenv("TOKEN_VOICE"))
