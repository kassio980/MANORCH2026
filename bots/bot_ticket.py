import os, sqlite3
from dotenv import load_dotenv
import discord
from discord import app_commands, ButtonStyle, Interaction, Embed
from discord.ui import View, Button, Modal, TextInput, Select

load_dotenv()
TOKEN = os.getenv('BOT_TICKET_TOKEN', '')

db = sqlite3.connect('ticket.db', check_same_thread=False)
for q in [
  'CREATE TABLE IF NOT EXISTS cfg(k TEXT PRIMARY KEY, v TEXT)',
  'CREATE TABLE IF NOT EXISTS tickets(id INTEGER PRIMARY KEY AUTOINCREMENT, uid TEXT, cid TEXT UNIQUE, cat TEXT, st TEXT DEFAULT ABERTO, num INTEGER)']:
  db.execute(q)
db.commit()
g = lambda k, d=None: (lambda r: r[0] if r else d)(db.execute('SELECT v FROM cfg WHERE k=?', (k,)).fetchone())
s = lambda k, v: db.execute('INSERT OR REPLACE INTO cfg VALUES(?,?)', (k, v)); db.commit()

intents = discord.Intents.default(); intents.members = True
bot = discord.Client(intents=intents); tree = app_commands.CommandTree(bot)

# ============== MODAL CONFIG COMPLETO ==============
class MCfg(Modal, title='🎫 CONFIGURAR TICKET'):
    def __init__(self):
        super().__init__()
        self.add_item(TextInput(label='Nome do Painel', default=g('nome','🎫 CENTRAL DE ATENDIMENTO'), required=True))
        self.add_item(TextInput(label='Canal do PAINEL (ID)', default=g('canal_painel',''), required=True))
        self.add_item(TextInput(label='Cargo Suporte (ID)', default=g('cargo',''), required=True))
        self.add_item(TextInput(label='Banner (foto OU vídeo URL)', default=g('banner',''), required=False))
        self.add_item(TextInput(label='Descrição do painel', style=discord.TextStyle.long,
            default=g('desc','Selecione uma categoria abaixo para abrir seu atendimento privado.'), required=True))
    async def on_submit(self, it):
        s('nome',self.children[0].value); s('canal_painel',self.children[1].value)
        s('cargo',self.children[2].value); s('banner',self.children[3].value); s('desc',self.children[4].value)
        await it.response.send_message('✅ Config salvo!\n\nAgora use **/categorias** para definir as opções e **/enviarticket** para lançar o painel.', ephemeral=True)

class MCats(Modal, title='📂 CATEGORIAS DE TICKET'):
    def __init__(self):
        super().__init__()
        self.add_item(TextInput(label='Categorias (separadas por vírgula)',
            default=g('cats','Suporte Financeiro, Compra, Denúncia, Dúvida, Parceria'), required=True))
        self.add_item(TextInput(label='Prefixo do canal (ex: ticket)', default=g('prefixo','ticket'), required=True))
        self.add_item(TextInput(label='Máx tickets abertos por pessoa', default=g('max','3'), required=True))
    async def on_submit(self, it):
        s('cats',self.children[0].value); s('prefixo',self.children[1].value); s('max',self.children[2].value)
        await it.response.send_message(f'✅ Categorias salvas: {self.children[0].value}', ephemeral=True)

# ============== VIEW PAINEL PÚBLICO ==============
class VPainel(View):
    def __init__(self, cats):
        super().__init__(timeout=None)
        emojis = ['🎫','💰','🚨','❓','🤝','🛒','⚙️','🔒']
        for i, c in enumerate(cats[:8]):
            self.add_item(Button(label=c.strip(), emoji=emojis[i%8],
                custom_id=f't_{c.strip()}', style=ButtonStyle.blurple, row=i//4))
    async def interaction_check(self, it):
        cid = it.data.get('custom_id','')
        if not cid.startswith('t_'): return True
        cat = cid[2:]; uid = str(it.user.id)
        mx = int(g('max','3'))
        ab = db.execute('SELECT COUNT(*) FROM tickets WHERE uid=? AND st=?',(uid,'ABERTO')).fetchone()[0]
        if ab >= mx: return await it.response.send_message(f'❌ Máximo {mx} tickets abertos', ephemeral=True)
        num = (db.execute('SELECT COALESCE(MAX(num),0)+1 FROM tickets').fetchone()[0])
        # CRIA NA MESMA CATEGORIA ONDE O PAINEL ESTÁ
        gu = it.guild
        cat_pai = it.channel.category
        crg = g('cargo')
        ow = {
            gu.default_role: discord.PermissionOverwrite(view_channel=False),
            it.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True, read_message_history=True)
        }
        if crg and crg.isdigit():
            try: ow[gu.get_role(int(crg))] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
            except: pass
        prefixo = g('prefixo','ticket')
        ch = await gu.create_text_channel(f'{prefixo}-{cat[:6].lower()}-{num:04d}', category=cat_pai, overwrites=ow)
        db.execute('INSERT INTO tickets(uid,cid,cat,num) VALUES(?,?,?,?)',(uid,str(ch.id),cat,num)); db.commit()
        e = Embed(title=f'🎫 Ticket #{num:04d} · {cat}', color=0x8B5CF6,
                  description=f'Olá {it.user.mention}, explique seu problema que um atendente já vem!\n\n' + (f'**Suporte:** <@&{crg}>' if crg else ''))
        e.set_footer(text=f'ID: {num} | Usuário: {it.user.id}')
        v = View()
        bf = Button(label='🔒 FECHAR', style=ButtonStyle.red)
        ba = Button(label='➕ ADICIONAR MEMBRO', style=ButtonStyle.blurple)
        bt = Button(label='📝 TRANSCRIVER', style=ButtonStyle.grey)
        async def f(ii):
            await ii.channel.send('🔒 Fechando em 5s...'); await asyncio.sleep(5)
            await ii.channel.delete(); db.execute('UPDATE tickets SET st=? WHERE cid=?',('FECHADO',str(ii.channel.id))); db.commit()
        async def a(ii):
            m = Modal(title='➕ Add'); m.add_item(TextInput(label='ID Usuário', required=True))
            async def ss(iii):
                try: u = await bot.fetch_user(int(m.children[0].value)); await ii.channel.set_permissions(u, view_channel=True); await iii.response.send_message(f'✅ {u.mention}', ephemeral=True)
                except: await iii.response.send_message('❌ ID inválido', ephemeral=True)
            m.on_submit = ss; await ii.response.send_modal(m)
        async def tr(ii):
            ms = []
            async for x in ii.channel.history(limit=500, oldest_first=True):
                if not x.author.bot: ms.append(f'[{x.created_at.strftime("%H:%M")}] {x.author}: {x.content}')
            open('/tmp/ticket.txt','w').write('\n'.join(ms))
            await ii.response.send_message(file=discord.File('/tmp/ticket.txt'), ephemeral=True)
        bf.callback=f; ba.callback=a; bt.callback=tr; v.add_item(bf); v.add_item(ba); v.add_item(bt)
        await ch.send(content=f'{it.user.mention}' + (f' <@&{crg}>' if crg else ''), embed=e, view=v)
        await it.response.send_message(f'✅ Ticket criado: {ch.mention}', ephemeral=True)
        return True

# ============== VIEW ADMIN ==============
class VAdmin(View):
    def __init__(self): super().__init__(timeout=None)
    @Button(label='⚙️ CONFIG GERAL', style=ButtonStyle.blurple)
    async def _(self,it,b): await it.response.send_modal(MCfg())
    @Button(label='📂 CATEGORIAS', style=ButtonStyle.green)
    async def _(self,it,b): await it.response.send_modal(MCats())
    @Button(label='🚀 ENVIAR PAINEL', style=ButtonStyle.purple)
    async def _(self,it,b):
        cp = g('canal_painel')
        if not cp or not cp.isdigit(): return await it.response.send_message('❌ Canal do painel não configurado', ephemeral=True)
        ch = bot.get_channel(int(cp))
        if not ch: return await it.response.send_message('❌ Canal inválido', ephemeral=True)
        cats = [x.strip() for x in g('cats','Suporte').split(',') if x.strip()]
        e = Embed(title=g('nome','🎫 ATENDIMENTO'), color=0x8B5CF6, description=g('desc',''))
        bn = g('banner')
        if bn:
            if any(bn.lower().endswith(x) for x in ('.mp4','.webm','.mov')):
                e.description += f'\n\n[📹 ASSISTA AO VÍDEO]({bn})'
            else: e.set_image(url=bn)
        e.add_field(name='📋 Categorias', value='\n'.join([f'• **{c}**' for c in cats]))
        e.add_field(name='👥 Suporte', value=(f'<@&{g("cargo")}>' if g('cargo') else 'Não configurado'))
        await ch.send(embed=e, view=VPainel(cats))
        await it.response.send_message(f'✅ Painel enviado em {ch.mention}\n\n💡 Os tickets serão criados **ABAIXO**, na mesma categoria do painel.', ephemeral=True)

# ============== COMANDOS ==============
@tree.command(name='ticket', description='🎫 Painel admin completo')
@app_commands.checks.has_permissions(administrator=True)
async def cmd_ticket(it):
    e = Embed(title='🎫 ADMIN · TICKET MONARCH', color=0x8B5CF6,
              description='Configure tudo em 3 passos:\n1️⃣ Config geral\n2️⃣ Categorias\n3️⃣ Enviar painel')
    e.add_field(name='⚙️ Atual', value=f"Canal: <#{g('canal_painel','0')}>\nCargo: <@&{g('cargo','0')}>\nCats: `{g('cats','-')}`")
    await it.response.send_message(embed=e, view=VAdmin(), ephemeral=True)

@tree.command(name='categorias', description='📂 Editar categorias')
@app_commands.checks.has_permissions(administrator=True)
async def cmd_cats(it): await it.response.send_modal(MCats())

@tree.command(name='enviarticket', description='🚀 Enviar painel público')
@app_commands.checks.has_permissions(administrator=True)
async def cmd_env(it):
    cp = g('canal_painel')
    if not cp or not cp.isdigit(): return await it.response.send_message('❌ Canal não configurado', ephemeral=True)
    ch = bot.get_channel(int(cp))
    cats = [x.strip() for x in g('cats','Suporte').split(',') if x.strip()]
    e = Embed(title=g('nome','🎫 ATENDIMENTO'), color=0x8B5CF6, description=g('desc',''))
    if g('banner') and not any(g('banner').lower().endswith(x) for x in ('.mp4','.webm')): e.set_image(url=g('banner'))
    e.add_field(name='📋 Categorias', value='\n'.join([f'• **{c}**' for c in cats]))
    await ch.send(embed=e, view=VPainel(cats))
    await it.response.send_message('✅ Enviado', ephemeral=True)

@bot.event
async def on_ready():
    await tree.sync()
    print(f'✅ BOT TICKET V2: {bot.user}')

bot.run(TOKEN)
