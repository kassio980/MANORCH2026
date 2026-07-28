import os, sqlite3, random
from dotenv import load_dotenv
import discord
from discord import app_commands, ButtonStyle, Interaction, Embed, File
from discord.ui import View, Button, Modal, TextInput, Select

load_dotenv()
TOKEN = os.getenv('BOT_GERADOR_TOKEN', '')

db = sqlite3.connect('gerador.db', check_same_thread=False)
for q in [
  'CREATE TABLE IF NOT EXISTS cfg(k TEXT PRIMARY KEY, v TEXT)',
  'CREATE TABLE IF NOT EXISTS tipos(id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT UNIQUE, banner TEXT, cor TEXT DEFAULT "#8B5CF6")',
  'CREATE TABLE IF NOT EXISTS contas(id INTEGER PRIMARY KEY, tipo TEXT, usuario TEXT, senha TEXT, extra TEXT, usada INTEGER DEFAULT 0, user_id TEXT, data TEXT)']:
  db.execute(q)
db.commit()

# Tipos padrão que você pediu
TIPOS_PADRAO = [
  ('Discord Nitro', 'https://i.imgur.com/9Z7X7yY.png', '#5865F2'),
  ('Spotify Premium', 'https://i.imgur.com/3kL8zXq.png', '#1DB954'),
  ('Netflix', 'https://i.imgur.com/7R4d2Qx.png', '#E50914'),
  ('Disney+', 'https://i.imgur.com/2W8n9Kp.png', '#113CCF'),
  ('HBO Max', 'https://i.imgur.com/5P6sL0v.png', '#663399'),
  ('Crunchyroll', 'https://i.imgur.com/8M2wQ4z.png', '#F47521'),
  ('TikTok Premium', 'https://i.imgur.com/1N3pK9L.png', '#000000'),
  ('Instagram+', 'https://i.imgur.com/4T7xZ2n.png', '#E1306C'),
  ('YouTube Premium', 'https://i.imgur.com/6K1wR8t.png', '#FF0000'),
  ('Prime Video', 'https://i.imgur.com/0F9jH3d.png', '#00A8E1')
]
for t in TIPOS_PADRAO:
  db.execute('INSERT OR IGNORE INTO tipos(nome,banner,cor) VALUES(?,?,?)', t)
db.commit()

g = lambda k, d=None: (lambda r: r[0] if r else d)(db.execute('SELECT v FROM cfg WHERE k=?', (k,)).fetchone())
s = lambda k, v: db.execute('INSERT OR REPLACE INTO cfg VALUES(?,?)', (k, v)); db.commit()
tipos = lambda: db.execute('SELECT id,nome,banner,cor FROM tipos ORDER BY id').fetchall()
estoque = lambda t: db.execute('SELECT COUNT(*) FROM contas WHERE tipo=? AND usada=0', (t,)).fetchone()[0]

intents = discord.Intents.default(); intents.members = True
bot = discord.Client(intents=intents); tree = app_commands.CommandTree(bot)

# ============== MODAIS ==============
class MCfg(Modal, title='🎰 CONFIGURAR PAINEL GERADOR'):
    def __init__(self):
        super().__init__()
        self.add_item(TextInput(label='Nome do Painel', default=g('nome', '🎰 GERADOR MONARCH'), required=True))
        self.add_item(TextInput(label='Canal onde aparece (ID)', default=g('canal', ''), required=True))
        self.add_item(TextInput(label='Banner URL (foto/vídeo)', default=g('banner', ''), required=False))
        self.add_item(TextInput(label='Descrição', style=discord.TextStyle.long, default=g('desc', 'Escolha abaixo e receba sua conta INSTANTANEAMENTE no privado!'), required=True))
    async def on_submit(self, it):
        s('nome', self.children[0].value); s('canal', self.children[1].value)
        s('banner', self.children[2].value); s('desc', self.children[3].value)
        await it.response.send_message('✅ Config salvo! Use **/enviargerador**', ephemeral=True)

class MAddConta(Modal, title='📦 ADICIONAR CONTA'):
    def __init__(self):
        super().__init__()
        self.add_item(Select(placeholder='Escolha o tipo', options=[
            discord.SelectOption(label=f'{t[1]} ({estoque(t[1])} disp)', value=t[1]) for t in tipos()
        ], row=0))
        self.add_item(TextInput(label='Usuário / Email / Chave', required=True, row=1))
        self.add_item(TextInput(label='Senha', required=False, row=2))
        self.add_item(TextInput(label='Extra (link, PIN etc)', required=False, row=3))
    async def on_submit(self, it):
        tp = self.children[0].values[0]
        db.execute('INSERT INTO contas(tipo,usuario,senha,extra) VALUES(?,?,?,?)',
                   (tp, self.children[1].value, self.children[2].value, self.children[3].value))
        db.commit()
        await it.response.send_message(f'✅ +1 conta **{tp}** adicionada · Estoque: **{estoque(tp)}**', ephemeral=True)

# ============== VIEW PAINEL PÚBLICO ==============
class VGerador(View):
    def __init__(self):
        super().__init__(timeout=None)
        for t in tipos()[:25]:
            self.add_item(Button(
                label=f'{t[1]} · {estoque(t[1])}',
                custom_id=f'g_{t[0]}',
                style=ButtonStyle.green,
                row=min(len(self.children)//5, 4)
            ))
    async def interaction_check(self, it):
        c = it.data.get('custom_id', '')
        if not c.startswith('g_'): return True
        tid = int(c[2:])
        tp = db.execute('SELECT nome,cor FROM tipos WHERE id=?', (tid,)).fetchone()
        if not tp: return await it.response.send_message('❌ Tipo inválido', ephemeral=True)
        nome, cor = tp
        q = db.execute('SELECT id,usuario,senha,extra FROM contas WHERE tipo=? AND usada=0 ORDER BY RANDOM() LIMIT 1', (nome,)).fetchone()
        if not q: return await it.response.send_message(f'❌ **{nome}** sem estoque no momento', ephemeral=True)
        from datetime import datetime
        db.execute('UPDATE contas SET usada=1, user_id=?, data=? WHERE id=?', (str(it.user.id), datetime.now().isoformat(), q[0]))
        db.commit()
        # Envia na DM
        e = Embed(title=f'✅ SUA CONTA: {nome}', color=int(cor.replace('#',''),16), timestamp=datetime.now())
        e.add_field(name='👤 Usuário', value=f'`{q[1]}`', inline=False)
        if q[2]: e.add_field(name='🔑 Senha', value=f'||{q[2]}||', inline=False)
        if q[3]: e.add_field(name='📎 Extra', value=q[3], inline=False)
        e.set_footer(text=f'Gerado por {it.user.display_name}')
        try:
            await it.user.send(embed=e)
            await it.response.send_message(f'✅ **{nome}** enviado na sua **DM** 📩', ephemeral=True)
        except:
            await it.response.send_message(embed=e, ephemeral=True)
        # Atualiza botão
        for btn in self.children:
            if btn.custom_id == c:
                btn.label = f'{nome} · {estoque(nome)}'
        return True

# ============== VIEW ADMIN ==============
class VAdmin(View):
    def __init__(self):
        super().__init__(timeout=None)
    @Button(label='⚙️ CONFIG PAINEL', style=ButtonStyle.blurple)
    async def _(self, it, b): await it.response.send_modal(MCfg())
    @Button(label='📦 + ADICIONAR CONTA', style=ButtonStyle.green)
    async def _(self, it, b): await it.response.send_modal(MAddConta())
    @Button(label='🚀 ENVIAR PAINEL NO CANAL', style=ButtonStyle.purple)
    async def _(self, it, b):
        cid = g('canal')
        if not cid or not cid.isdigit(): return await it.response.send_message('❌ Canal não configurado', ephemeral=True)
        ch = bot.get_channel(int(cid))
        if not ch: return await it.response.send_message('❌ Canal inválido', ephemeral=True)
        e = Embed(title=g('nome','🎰 GERADOR'), color=0x8B5CF6, description=g('desc',''))
        bn = g('banner')
        if bn:
            if any(bn.lower().endswith(x) for x in ('.mp4','.webm','.mov')):
                e.description += f'\n\n[📹 VER VÍDEO]({bn})'
            else: e.set_image(url=bn)
        e.add_field(name='📊 Estoque', value='\n'.join([f'• **{t[1]}**: `{estoque(t[1])}`' for t in tipos()]))
        await ch.send(embed=e, view=VGerador())
        await it.response.send_message(f'✅ Painel enviado em {ch.mention}', ephemeral=True)

# ============== COMANDO ==============
@tree.command(name='gerador', description='🎰 Configurar gerador de contas')
@app_commands.checks.has_permissions(administrator=True)
async def cmd_gerador(it):
    e = Embed(title='🎰 ADMIN · GERADOR', color=0x8B5CF6,
              description='Configure, adicione contas e envie o painel para o canal público.')
    e.add_field(name='📦 Tipos cadastrados', value=str(len(tipos())) + ' categorias')
    e.add_field(name='💾 Total contas', value=str(db.execute('SELECT COUNT(*) FROM contas').fetchone()[0]))
    await it.response.send_message(embed=e, view=VAdmin(), ephemeral=True)

@bot.event
async def on_ready():
    await tree.sync()
    print(f'✅ BOT GERADOR: {bot.user} · {len(tipos())} categorias')

bot.run(TOKEN)
