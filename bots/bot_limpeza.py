import os, sqlite3, asyncio
from dotenv import load_dotenv
import discord
from discord import app_commands, ButtonStyle, Interaction, Embed
from discord.ui import View, Button, Modal, TextInput, Select

load_dotenv()
TOKEN = os.getenv('BOT_LIMPEZA_TOKEN', '')

# Banco próprio
db = sqlite3.connect('limpeza.db', check_same_thread=False)
db.execute('CREATE TABLE IF NOT EXISTS cfg(k TEXT PRIMARY KEY, v TEXT)')
db.commit()
g = lambda k, d=None: (lambda r: r[0] if r else d)(db.execute('SELECT v FROM cfg WHERE k=?', (k,)).fetchone())
s = lambda k, v: db.execute('INSERT OR REPLACE INTO cfg VALUES(?,?)', (k, v)); db.commit()

LOOPS = {}  # Canais com limpeza automática rodando

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.voice_states = True
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

# ============== LIMPEZA LOOP ==============
async def loop_limpeza(cid: int, minutos: int, qtd: int):
    while str(cid) in LOOPS:
        try:
            ch = bot.get_channel(cid)
            if ch and hasattr(ch, 'purge'):
                await ch.purge(limit=qtd, bulk=True, reason='Limpeza automática MONARCH')
        except: pass
        await asyncio.sleep(max(60, minutos * 60))

# ============== MODAIS ==============
class MLimp(Modal, title='🧹 LIMPEZA AUTOMÁTICA'):
    def __init__(self):
        super().__init__()
        self.add_item(TextInput(label='Canal ID (onde vai limpar)', default=g('canal', ''), required=True))
        self.add_item(TextInput(label='A cada quantos MINUTOS', default=g('min', '30'), required=True))
        self.add_item(TextInput(label='Quantas MENSAGENS apagar', default=g('qtd', '50'), required=True))
    async def on_submit(self, it: Interaction):
        cid = int(self.children[0].value); mn = int(self.children[1].value); qtd = int(self.children[2].value)
        s('canal', str(cid)); s('min', str(mn)); s('qtd', str(qtd))
        LOOPS[str(cid)] = True
        asyncio.create_task(loop_limpeza(cid, mn, qtd))
        await it.response.send_message(f'✅ ATIVADO\n🧹 A cada **{mn}min** apaga **{qtd}** msgs em <#{cid}>', ephemeral=True)

class MVoz(Modal, title='🔊 CONECTAR CANAL DE VOZ'):
    def __init__(self):
        super().__init__()
        self.add_item(TextInput(label='ID DO CANAL DE VOZ', required=True, placeholder='Ex: 123456789012345678'))
    async def on_submit(self, it: Interaction):
        cid = int(self.children[0].value)
        vc = it.guild.get_channel(cid)
        if not vc or not isinstance(vc, discord.VoiceChannel):
            return await it.response.send_message('❌ Canal de voz inválido', ephemeral=True)
        try:
            if vc.guild.voice_client: await vc.guild.voice_client.disconnect()
            await vc.connect(self_deaf=True, self_mute=True)
            await it.response.send_message(f'🔊 Conectado em **{vc.name}**\n\n✅ Para conectar OUTROS bots aqui, basta usar o mesmo ID nos outros bots', ephemeral=True)
        except Exception as e:
            await it.response.send_message(f'❌ Erro: {e}', ephemeral=True)

# ============== VIEW PRINCIPAL ==============
class VLimpeza(View):
    def __init__(self): super().__init__(timeout=None)

    @Button(label='⚙️ CONFIGURAR LIMPEZA', style=ButtonStyle.blurple, row=0)
    async def _(self, it, b): await it.response.send_modal(MLimp())

    @Button(label='🧹 LIMPAR AGORA 100 MSGS', style=ButtonStyle.green, row=0)
    async def _(self, it, b):
        await it.response.defer(ephemeral=True)
        q = await it.channel.purge(limit=100, bulk=True)
        await it.followup.send(f'🧹 **{len(q)}** mensagens apagadas', ephemeral=True)

    @Button(label='⏹️ PARAR LIMPEZA', style=ButtonStyle.red, row=0)
    async def _(self, it, b):
        cid = g('canal')
        if cid: LOOPS.pop(cid, None)
        await it.response.send_message('⏹️ Limpeza automática parada', ephemeral=True)

    @Button(label='🔊 CONECTAR EM CANAL DE VOZ', style=ButtonStyle.purple, row=1)
    async def _(self, it, b): await it.response.send_modal(MVoz())

    @Button(label='🔇 DESCONECTAR VOZ', style=ButtonStyle.grey, row=1)
    async def _(self, it, b):
        if it.guild.voice_client:
            await it.guild.voice_client.disconnect()
            await it.response.send_message('🔇 Desconectado', ephemeral=True)
        else:
            await it.response.send_message('❌ Não estou em nenhum canal', ephemeral=True)

# ============== COMANDO ==============
@tree.command(name='limpeza', description='🧹 Painel limpeza + voz')
@app_commands.checks.has_permissions(administrator=True)
async def cmd_limpeza(it: Interaction):
    e = Embed(title='🧹 LIMPEZA + VOZ MONARCH', color=0x8B5CF6,
              description='Configure limpeza automática e conecte o bot em qualquer canal de voz.')
    e.add_field(name='⏱️ Config atual', value=f"Canal: <#{g('canal','0')}>\nA cada: `{g('min','30')}min`\nQuantidade: `{g('qtd','50')}` msgs")
    await it.response.send_message(embed=e, view=VLimpeza(), ephemeral=True)

@bot.event
async def on_ready():
    await tree.sync()
    # Retoma limpeza se tiver configurada
    cid = g('canal'); mn = g('min'); qtd = g('qtd')
    if cid and mn and qtd and cid.isdigit():
        LOOPS[cid] = True
        asyncio.create_task(loop_limpeza(int(cid), int(mn), int(qtd)))
    print(f'✅ BOT LIMPEZA+VOZ: {bot.user}')

bot.run(TOKEN)
