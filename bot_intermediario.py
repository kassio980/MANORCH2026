import os,discord,sqlite3
from discord.ext import commands
from discord import app_commands,Embed
TOKEN=os.getenv("TOKEN_INTERMEDIARIO","")
DONO=int(os.getenv("ID_DONO","0"))
SERVIDOR=int(os.getenv("SERVIDOR_OFICIAL","1531365460212322497"))
db=sqlite3.connect("intermediario.db",check_same_thread=False)

intents=discord.Intents.all()
bot=commands.Bot(command_prefix="b!",intents=intents)
tree=bot.tree

@bot.event
async def on_guild_join(g):
    if g.id != SERVIDOR: await g.leave()

@tree.command(name="painel_intermediario")
async def painel(it):
    e=Embed(title=f"👑 MONARCH INTERMEDIARIO",description="Sistema completo ativado",color=0xFF8C00)
    await it.response.send_message(embed=e,ephemeral=True)


# ========== COMANDO EXCLUSIVO DO DONO ==========
@tree.command(name="configurar_tudo", description="👑 ATUALIZA TODOS OS COMANDOS DO SISTEMA")
@app_commands.guilds(discord.Object(id=1531365460212322497))
async def cmd_atualizar(it):
    if it.user.id != DONO:
        await it.response.send_message("❌ **SOMENTE O DONO PODE USAR ISSO!**", ephemeral=True)
        return
    await it.response.defer(ephemeral=True)
    total = await tree.sync(guild=discord.Object(id=1531365460212322497))
    msg = Embed(
        title="👑 SISTEMA CONFIGURADO COM SUCESSO!",
        description=f"✅ **TODOS OS COMANDOS CARREGADOS!**\n📦 Total: {len(total)}\n🖥️ Servidor: MONARCH2026©",
        color=0xFF8C00
    )
    msg.add_field(name="📂 PRINCIPAIS", value="/loja • /carteira • /premium • /config_branding")
    msg.add_field(name="⚙️ ADMIN", value="/admin • /conectar_voz • /criar_loja")
    msg.add_field(name="🔧 SISTEMA", value="/configurar_tudo")
    await it.followup.send(embed=msg, ephemeral=True)
    try: print(f"✅ COMANDOS: {len(total)}")
    except: pass


@bot.event
async def on_ready():
    print(f"👑 BOT INTERMEDIARIO — ONLINE")
    await bot.tree.sync(guild=discord.Object(id=SERVIDOR))

bot.run(TOKEN)
