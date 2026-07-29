import os
import discord
from discord.ext import commands
from discord import app_commands, Embed

TOKEN = os.getenv("TOKEN_API", "")
DONO = int(os.getenv("ID_DONO", "0"))
SERVIDOR = int(os.getenv("SERVIDOR_OFICIAL", "1531365460212322497"))

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="a!", intents=intents)
tree = bot.tree

# SAI DE QUALQUER SERVIDOR QUE NÃO SEJA O OFICIAL
@bot.event
async def on_guild_join(g):
    if g.id != SERVIDOR:
        await g.leave()
        return

@tree.command(name="loja", description="👑 Ver planos disponíveis")
async def loja(it):
    e = Embed(title="👑 MONARCH LOJA OFICIAL", color=0xFF8C00)
    e.add_field(name="BÁSICO", value="Comandos simples", inline=False)
    e.add_field(name="INTERMEDIÁRIO", value="Comandos + Tickets", inline=False)
    e.add_field(name="VIP", value="Carteira + Pagamentos", inline=False)
    e.add_field(name="PREMIUM", value="API + Hospedagem Automática", inline=False)
    await it.response.send_message(embed=e, ephemeral=True)

@tree.command(name="testar", description="✅ Verificar sistema")
async def testar(it):
    await it.response.send_message("✅ MONARCH API — SISTEMA 100% ONLINE", ephemeral=True)

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
    msg.add_field(name="PRINCIPAIS", value="/loja • /testar")
    msg.add_field(name="ADMIN", value="/configurar_tudo")
    await it.followup.send(embed=msg, ephemeral=True)
    print(f"✅ API: {len(total)} comandos atualizados")

@bot.event
async def on_ready():
    print("🔌 MONARCH API — ONLINE")
    await tree.sync(guild=discord.Object(id=SERVIDOR))

bot.run(TOKEN)
