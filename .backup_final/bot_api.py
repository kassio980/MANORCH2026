import os,discord,sqlite3
from discord.ext import commands
from discord import app_commands,Embed
TOKEN=os.getenv("TOKEN_API","")
DONO=int(os.getenv("ID_DONO","0"))
SERVIDOR=int(os.getenv("SERVIDOR_OFICIAL","1531365460212322497"))
db=sqlite3.connect("monarch_api_v8.db",check_same_thread=False)

intents=discord.Intents.all()
bot=commands.Bot(command_prefix="a!",intents=intents)
tree=bot.tree

@bot.event
async def on_guild_join(g):
    if g.id != SERVIDOR: await g.leave()

@tree.command(name="loja")
async def loja(it):
    e=Embed(title="👑 MONARCH LOJA",description="Escolha seu plano",color=0xFF8C00)
    e.add_field(name="BÁSICO",value="Criação de comandos simples",inline=False)
    e.add_field(name="INTERMEDIÁRIO",value="Sistema completo + tickets",inline=False)
    e.add_field(name="VIP",value="Carteira + pagamentos",inline=False)
    e.add_field(name="PREMIUM",value="API + hospedagem automática",inline=False)
    await it.response.send_message(embed=e,ephemeral=True)

@tree.command(name="testar")
async def testar(it):
    await it.response.send_message("✅ SISTEMA API — 100% FUNCIONAL",ephemeral=True)

$PADRAO_COMANDO

@bot.event
async def on_ready():
    print("🔌 MONARCH API — ONLINE")
    await bot.tree.sync(guild=discord.Object(id=SERVIDOR))

bot.run(TOKEN)
