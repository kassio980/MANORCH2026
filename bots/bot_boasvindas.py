import os, sqlite3, io
from dotenv import load_dotenv
import discord
from discord import app_commands, ButtonStyle, Interaction, Embed, File
from discord.ui import View, Button, Modal, TextInput, Select
from PIL import Image, ImageDraw, ImageFont, ImageOps

load_dotenv()
TOKEN=os.getenv('BOT_BV_TOKEN')
db=sqlite3.connect('bots/bv.db',check_same_thread=False)
for q in ['CREATE TABLE IF NOT EXISTS cfg(k TEXT PRIMARY KEY,v TEXT)']: db.execute(q)
db.commit()
g=lambda k,d=None: (lambda r:r[0] if r else d)(db.execute('SELECT v FROM cfg WHERE k=?',(k,)).fetchone())
s=lambda k,v: db.execute('INSERT OR REPLACE INTO cfg VALUES(?,?)',(k,v)); db.commit()

def img_bv(avatar_url,nome,texto='BEM VINDOS💲🚀'):
  try:
    import aiohttp; import asyncio
    async def _d():
      async with aiohttp.ClientSession() as ss:
        r=await ss.get(str(avatar_url).replace('webp','png')); return await r.read()
    d=asyncio.run(_d())
    av=Image.open(io.BytesIO(d)).convert('RGBA').resize((180,180))
  except: av=Image.new('RGBA',(180,180),'#6D28D9')
  m=Image.new('L',av.size,0); ImageDraw.Draw(m).ellipse((0,0,180,180),fill=255)
  av=ImageOps.fit(av,m.size,centering=(0.5,0.5)); av.putalpha(m)
  img=Image.new('RGB',(900,300),'#0a0618'); d=ImageDraw.Draw(img)
  g2=ImageDraw.Draw(img).linear_gradient((0,0,900,300)); g2.__setstate__({'colors':[(0,'#6D28D9'),(1,'#8B5CF6')]})
  img.paste(g2,(0,0),Image.new('L',(900,300),80))
  try: f1=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',56); f2=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',32)
  except: f1=f2=ImageFont.load_default()
  d.ellipse((54,54,246,246),fill='#fff',width=6,outline='#C4B5FD')
  img.paste(av,(60,60),av)
  d.text((280,80),texto,font=f1,fill='white')
  d.text((280,160),nome,font=f2,fill='#C4B5FD')
  b=io.BytesIO(); img.save(b,'PNG'); b.seek(0); return File(b,'bv.png')

intents=discord.Intents.default(); intents.members=True
bot=discord.Client(intents=intents); tree=app_commands.CommandTree(bot)

class MCfg(Modal,title='👋 Boas Vindas'):
  def __init__(self):
    super().__init__()
    self.add_item(TextInput(label='Canal Entrada ID',default=g('ce','')))
    self.add_item(TextInput(label='Msg Entrada {user} {server}',style=discord.TextStyle.long,default=g('me','🎉 {user.mention} bem-vindo ao **{server.name}**!')))
    self.add_item(TextInput(label='Canal Saída ID',default=g('cs','')))
    self.add_item(TextInput(label='Msg Saída {user}',style=discord.TextStyle.long,default=g('ms','👋 {user} saiu do servidor.')))
    self.add_item(TextInput(label='Texto Imagem',default=g('ti','BEM VINDOS💲🚀')))
  async def on_submit(self,it):
    s('ce',self.children[0].value); s('me',self.children[1].value)
    s('cs',self.children[2].value); s('ms',self.children[3].value); s('ti',self.children[4].value)
    await it.response.send_message('✅ Config salvo',ephemeral=True)

@tree.command(name='boasvindas',description='👋 Configurar entrada/saída')
@app_commands.checks.has_permissions(administrator=True)
async def _(it): await it.response.send_modal(MCfg())

@bot.event
async def on_member_join(m):
  ce=g('ce'); me=g('me'); ti=g('ti','BEM VINDOS💲🚀')
  if not ce: return
  ch=bot.get_channel(int(ce))
  if ch:
    try: f=img_bv(m.display_avatar.url,m.display_name,ti)
    except: f=None
    txt=me.replace('{user.mention}',m.mention).replace('{user}',str(m)).replace('{server.name}',m.guild.name)
    await ch.send(content=txt,file=f)

@bot.event
async def on_member_remove(m):
  cs=g('cs'); ms=g('ms')
  if not cs: return
  ch=bot.get_channel(int(cs))
  if ch: await ch.send(ms.replace('{user.mention}',m.mention).replace('{user}',str(m)))

@bot.event
async def on_ready(): await tree.sync(); print(f'✅ BOT BOAS VINDAS: {bot.user}')
bot.run(TOKEN)
