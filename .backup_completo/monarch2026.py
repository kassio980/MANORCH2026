# ==================================================
# 👑 MONARCH2026© — SISTEMA PRINCIPAL COMPLETO
# 🔒 WHITELIST | 🎨 BRANDING | 🚫 SEM PAINEL WEB
# ==================================================
import os, sqlite3, datetime, discord
from discord import app_commands, Interaction, Embed, ButtonStyle
from discord.ui import View, Button, Modal, TextInput
from discord.ext import tasks
from dotenv import load_dotenv
from core.seguranca import servidor_valido, eh_dono, SERVIDOR_PERMITIDO
from core.brand import mk_embed, setar

load_dotenv()
TOKEN = os.getenv("TOKEN")
intents = discord.Intents.default()
intents.members = intents.voice_states = intents.message_content = intents.guilds = True
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

@bot.event
async def on_guild_join(g):
    if not servidor_valido(g.id):
        print(f"❌ Saindo de {g.id}")
        await g.leave()

@bot.event
async def on_voice_state_update(m,a,d):
    if not servidor_valido(m.guild.id) or not m.bot: return
    if a.channel and not d.channel:
        try: await a.channel.connect(self_deaf=True) if m==bot.user else await m.move_to(a.channel)
        except: pass

class ModalBranding(Modal):
    def __init__(self):
        super().__init__(title="🎨 CONFIGURAR BRANDING")
        b = mk_embed().to_dict()["author"]["name"]
        self.add_item(TextInput(label="Nome",default=b))
    async def on_submit(self,i):
        if not eh_dono(i.user.id): return
        setar(nome=self.children[0].value)
        await i.response.send_message(embed=mk_embed("✅ ATUALIZADO"),ephemeral=True)

class Painel(View):
    @discord.ui.button(label="🔌 CONECTAR TODOS",style=ButtonStyle.green)
    async def c(self,i,b):
        if not eh_dono(i.user.id): return
        canal = i.user.voice.channel if i.user.voice else None
        if not canal: return await i.response.send_message("❌ Sem canal",ephemeral=True)
        if not bot.user.voice: await canal.connect(self_deaf=True)
        for m in i.guild.members:
            if m.bot and m.voice: await m.move_to(canal)
        await i.response.send_message(embed=mk_embed("✅ CONECTADO"))
    @discord.ui.button(label="🎨 BRANDING",style=ButtonStyle.blurple)
    async def br(self,i,b):
        if not eh_dono(i.user.id): return await i.response.send_modal(ModalBranding())

@tree.command(name="painel",guild=discord.Object(id=SERVIDOR_PERMITIDO))
async def _(i): await i.response.send_message(embed=mk_embed("👑 PAINEL PRINCIPAL"),view=Painel())

@tasks.loop(seconds=15)
async def auto_rec():
    g = bot.get_guild(SERVIDOR_PERMITIDO)
    if g and not bot.user.voice:
        try: await g.channels[0].connect(self_deaf=True)
        except: pass

@bot.event
async def on_ready():
    await tree.sync(guild=discord.Object(id=SERVIDOR_PERMITIDO))
    auto_rec.start()
    print("👑 MONARCH2026© PRINCIPAL ONLINE")

bot.run(TOKEN)
