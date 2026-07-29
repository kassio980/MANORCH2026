# 🟢 BOT BÁSICO — MONARCH2026©
import os, discord
from dotenv import load_dotenv
load_dotenv()
bot = discord.Client(intents=discord.Intents.default())
@bot.event
async def on_ready(): print("🟢 BOT BÁSICO ONLINE")
bot.run(os.getenv("TOKEN_BOT_BASICO",""))
