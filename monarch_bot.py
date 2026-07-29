import os
import discord
from discord import app_commands, Interaction, ButtonStyle
from discord.ui import View, Button, Modal, TextInput
from discord.ext import tasks
from dotenv import load_dotenv
from core.seguranca import servidor_valido, eh_dono, SERVIDOR_PERMITIDO
from core.brand import mk_embed, set_brand, get_brand

load_dotenv()
TOKEN = os.getenv("TOKEN_BOT")

intents = discord.Intents.default()
intents.members = True
intents.voice_states = True
intents.message_content = True
intents.guilds = True

bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

# 🔒 SAI DE SERVIDOR NÃO AUTORIZADO
@bot.event
async def on_guild_join(g):
    if not servidor_valido(g.id):
        print(f"❌ Servidor {g.id} — SAINDO")
        await g.leave()

# 🛡️ ANTI-SAIDA
@bot.event
async def on_voice_state_update(m, ant, dps):
    if not servidor_valido(m.guild.id) or not m.bot: return
    if ant.channel and not dps.channel:
        try: await ant.channel.connect(self_deaf=True) if m == bot.user else await m.move_to(ant.channel)
        except: pass

# 🎨 MODAL BRANDING
class ModalBrand(Modal, title="🎨 CONFIGURAR BRANDING"):
    def __init__(self):
        super().__init__()
        b = get_brand()
        self.add_item(TextInput(label="Nome", default=b[1], required=False))
        self.add_item(TextInput(label="Slogan", default=b[2], required=False))
        self.add_item(TextInput(label="Logo URL", default=b[3], required=False))
        self.add_item(TextInput(label="Banner URL", default=b[4], required=False))
        self.add_item(TextInput(label="Vídeo URL", default=b[5], required=False))
        self.add_item(TextInput(label="Cor HEX", default=b[6], required=False))

    async def on_submit(self, i:Interaction):
        if not eh_dono(i.user.id): return
        set_brand(nome=self.children[0].value, slogan=self.children[1].value,
                  logo=self.children[2].value, banner=self.children[3].value,
                  video=self.children[4].value, cor=self.children[5].value)
        await i.response.send_message(embed=mk_embed("✅ BRANDING ATUALIZADO"), ephemeral=True)

# 🎛️ PAINEL
class Painel(View):
    @discord.ui.button(label="🔌 CONECTAR TODOS", style=ButtonStyle.green)
    async def c(self,i,b):
        if not eh_dono(i.user.id): return
        canal = i.user.voice.channel if i.user.voice else None
        if not canal: return await i.response.send_message("❌ Entre em canal primeiro", ephemeral=True)
        for m in i.guild.members:
            if m.bot and m.voice and m.voice.channel != canal:
                try: await m.move_to(canal)
                except: pass
        if not bot.user.voice: await canal.connect(self_deaf=True)
        await i.response.send_message(embed=mk_embed("✅ CONECTADO", f"Todos em {canal.mention}"))

    @discord.ui.button(label="⏏️ DESCONECTAR", style=ButtonStyle.red)
    async def d(self,i,b):
        if not eh_dono(i.user.id): return
        for m in i.guild.members:
            if m.bot and m.voice:
                try: await m.move_to(None)
                except: pass
        if bot.user.voice: await bot.user.voice.disconnect()
        await i.response.send_message(embed=mk_embed("⏏️ DESCONECTADO"))

    @discord.ui.button(label="🎨 BRANDING", style=ButtonStyle.blurple)
    async def br(self,i,b):
        if not eh_dono(i.user.id): return await i.response.send_modal(ModalBrand())

@tree.command(name="painel", description="👑 Controle", guild=discord.Object(id=SERVIDOR_PERMITIDO))
async def _painel(i:Interaction):
    await i.response.send_message(embed=mk_embed("👑 PAINEL PRINCIPAL"), view=Painel())

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
    print(f"👑 MONARCH2026© ONLINE | SÓ NO SERVIDOR: {SERVIDOR_PERMITIDO}")

bot.run(TOKEN)
