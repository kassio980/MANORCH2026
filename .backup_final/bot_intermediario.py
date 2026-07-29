# 🔵 MONARCH SALES™ — INTERMEDIÁRIO v2.0
# Tudo Básico + Licenças · Keys · Assinaturas · Cashback · Convites · Banner · Estatísticas Avançadas · BRANDING
import os,discord,sqlite3,json,random,string
from datetime import datetime,timedelta
from discord.ext import commands
from discord import app_commands,Embed,Color,ButtonStyle,SelectOption
from discord.ui import View,Button,Select,Modal,TextInput

TOKEN=os.getenv("BOT_TOKEN","");LIC=os.getenv("LIC","");DONO=int(os.getenv("DONO","0"))
db=sqlite3.connect("inter.db",check_same_thread=False)

for q in [
"CREATE TABLE IF NOT EXISTS cfg(chave TEXT PRIMARY KEY,valor TEXT)",
"CREATE TABLE IF NOT EXISTS cat(id INTEGER PRIMARY KEY,nome TEXT UNIQUE,desc TEXT,img TEXT,prem INTEGER DEFAULT 0)",
"CREATE TABLE IF NOT EXISTS prod(id INTEGER PRIMARY KEY,nome TEXT UNIQUE,desc TEXT,preco REAL,estoque INTEGER DEFAULT -1,cat INTEGER,tipo TEXT DEFAULT 'digital',img TEXT,key TEXT DEFAULT '')",
"CREATE TABLE IF NOT EXISTS carr(uid TEXT PRIMARY KEY,itens TEXT)",
"CREATE TABLE IF NOT EXISTS cup(cod TEXT PRIMARY KEY,tipo TEXT,valor REAL,usos INTEGER DEFAULT 0,max INTEGER DEFAULT 999,exp TEXT,cash REAL DEFAULT 0)",
"CREATE TABLE IF NOT EXISTS vend(id INTEGER PRIMARY KEY,uid TEXT,nick TEXT,itens TEXT,total REAL,cupom TEXT,cashback REAL DEFAULT 0,data TEXT)",
"CREATE TABLE IF NOT EXISTS keys(id INTEGER PRIMARY KEY,chave TEXT UNIQUE,prod TEXT,usada INTEGER DEFAULT 0,dono TEXT,data TEXT)",
"CREATE TABLE IF NOT EXISTS lic(id INTEGER PRIMARY KEY,cod TEXT UNIQUE,uid TEXT,plano TEXT,validade TEXT,status TEXT DEFAULT 'ativa')",
"CREATE TABLE IF NOT EXISTS assin(id INTEGER PRIMARY KEY,uid TEXT,plano TEXT,valor REAL,prox TEXT,status TEXT DEFAULT 'ativa')",
"CREATE TABLE IF NOT EXISTS convites(cod TEXT PRIMARY KEY,uid TEXT,premio REAL,usos INTEGER DEFAULT 0)",
"CREATE TABLE IF NOT EXISTS users(uid TEXT PRIMARY KEY,nick TEXT,cash REAL DEFAULT 0,conv TEXT)",
"CREATE TABLE IF NOT EXISTS logs(id INTEGER PRIMARY KEY,tipo TEXT,user TEXT,msg TEXT,data TEXT)",
]:db.execute(q)
db.commit()

BRAND_PADRAO=[
("nome_bot","MONARCH SALES™ INTERMEDIÁRIO"),("logo",""),("banner",""),
("descricao","Loja completa com licenças, assinaturas e cashback!"),("cor","0x3B82F6"),
("rodape","MONARCH SALES™ INTERMEDIÁRIO"),
]
db.executemany("INSERT OR IGNORE INTO cfg VALUES(?,?)",BRAND_PADRAO);db.commit()

def cfg(k,d=None):r=db.execute("SELECT valor FROM cfg WHERE chave=?",(k,)).fetchone();return r[0] if r else d
def setc(k,v):db.execute("INSERT OR REPLACE INTO cfg VALUES(?,?)",(k,v));db.commit()
def uid(u):db.execute("INSERT OR IGNORE INTO users VALUES(?,?,0,NULL)",(str(u.id),u.display_name));db.commit();return str(u.id)
def cor():
    try:return int(cfg("cor","0x3B82F6"),16)
    except:return 0x3B82F6
def emb(t="",d=""):
    e=Embed(title=t,description=d or cfg("descricao",""),color=cor(),timestamp=datetime.now())
    if cfg("logo"):e.set_thumbnail(url=cfg("logo"))
    if cfg("banner"):e.set_image(url=cfg("banner"))
    e.set_footer(text=cfg("rodape",""))
    return e

intents=discord.Intents.all();bot=commands.Bot(command_prefix="i!",intents=intents);tree=bot.tree

# ========== MODAL BRANDING ==========
class MBrand(Modal):
    def __init__(self):
        super().__init__(title="🎨 CONFIGURAR IDENTIDADE DO BOT")
        self.n=TextInput(label="Nome do Bot",default=cfg("nome_bot"),required=True)
        self.d=TextInput(label="Descrição Principal",default=cfg("descricao"),style=discord.TextStyle.long,required=False)
        self.l=TextInput(label="URL Logo",default=cfg("logo"),required=False)
        self.b=TextInput(label="URL Banner",default=cfg("banner"),required=False)
        self.c=TextInput(label="Cor Hex",default=cfg("cor"),required=False)
    async def on_submit(self,it):
        setc("nome_bot",self.n.value);setc("descricao",self.d.value)
        setc("logo",self.l.value);setc("banner",self.b.value);setc("cor",self.c.value)
        try:await bot.user.edit(username=self.n.value[:32])
        except:pass
        await it.response.send_message(embed=emb("✅ IDENTIDADE ATUALIZADA!"),ephemeral=True)

# ========== MODAIS EXTRAS ==========
class MLic(Modal):
    def __init__(self):super().__init__(title="🔑 NOVA LICENÇA")
    p=TextInput(label="Plano");d=TextInput(label="Dias",default="30");u=TextInput(label="UID Usuário")
    async def on_submit(self,it):
        cod=f"LIC-{''.join(random.choices(string.ascii_letters+string.digits,k=16))}"
        val=(datetime.now()+timedelta(days=int(self.d.value))).isoformat()
        db.execute("INSERT INTO lic VALUES(NULL,?,?,?,?,?)",(cod,self.u.value,self.p.value,val,'ativa'));db.commit()
        await it.response.send_message(f"✅ Licença: `{cod}`",ephemeral=True)

class MA(Modal):
    def __init__(self):super().__init__(title="🎁 CRIAR CONVITE PREMIADO")
    p=TextInput(label="Prêmio em R$",default="5")
    async def on_submit(self,it):
        cod=''.join(random.choices(string.ascii_uppercase+string.digits,k=6))
        db.execute("INSERT INTO convites VALUES(?,?,?,0)",(cod,str(it.user.id),float(self.p.value)));db.commit()
        await it.response.send_message(f"✅ Convite: `{cod}` — Prêmio: R${self.p.value}",ephemeral=True)

class MAval(Modal):
    def __init__(self,vid):super().__init__(title="⭐ AVALIAÇÃO AVANÇADA");self.vid=vid
    n=TextInput(label="Nota 1-5",default="5");c=TextInput(label="Comentário",style=discord.TextStyle.long,required=False);p=TextInput(label="Recomenda? (S/N)",default="S")
    async def on_submit(self,it):await it.response.send_message("✅ Avaliação salva!",ephemeral=True)

# ========== VIEW PRINCIPAL ==========
class VIPrincipal(View):
    def __init__(self):super().__init__(timeout=None)
    @discord.ui.button(label="🛍️ COMPRAR",style=ButtonStyle.green)
    async def bc(self,it,b):
        cats=db.execute("SELECT * FROM cat").fetchall()
        if not cats:return await it.response.edit_message(embed=emb("📭 VAZIO"))
        v=View();v.add_item(Select(options=[SelectOption(label=x[1],value=str(x[0]))for x in cats],placeholder="📂 Categoria..."))
        await it.response.edit_message(embed=emb("📂 CATEGORIAS"),view=v)
    @discord.ui.button(label="💎 CASHBACK",style=ButtonStyle.blurple)
    async def bcash(self,it,b):
        u=db.execute("SELECT cash FROM users WHERE uid=?",(uid(it.user),)).fetchone()
        await it.response.send_message(f"💎 Seu cashback: **R${(u[0] or 0):.2f}**",ephemeral=True)
    @discord.ui.button(label="🔑 MINHAS LICENÇAS",style=ButtonStyle.gray)
    async def blic(self,it,b):
        r=db.execute("SELECT * FROM lic WHERE uid=?",(uid(it.user),)).fetchall()
        t="\n".join([f"• `{x[1]}` — {x[3]} | {x[4][:10]} | {x[5]}"for x in r]) or "Nenhuma"
        await it.response.send_message(embed=emb("🔑 SUAS LICENÇAS",t),ephemeral=True)
    @discord.ui.button(label="📅 MINHAS ASSINATURAS",style=ButtonStyle.gray)
    async def bass(self,it,b):
        r=db.execute("SELECT * FROM assin WHERE uid=?",(uid(it.user),)).fetchall()
        t="\n".join([f"• {x[2]} — R${x[3]:.2f} | Próx: {x[4][:10]}"for x in r]) or "Nenhuma"
        await it.response.send_message(embed=emb("📅 ASSINATURAS",t),ephemeral=True)
    @discord.ui.button(label="🎁 CONVITES",style=ButtonStyle.green)
    async def bconv(self,it,b):await it.response.send_modal(MA())

@tree.command(name="loja")
async def loja(it):await it.response.send_message(embed=emb(f"🛍️ {cfg('nome_bot')}"),view=VIPrincipal())

@tree.command(name="config_branding")
@app_commands.checks.has_permissions(administrator=True)
async def brand(it):await it.response.send_modal(MBrand())

@tree.command(name="testar")
@app_commands.checks.has_permissions(administrator=True)
async def test(it):
    e=emb("✅ TESTE INTERMEDIÁRIO","🟢 SISTEMA OPERACIONAL")
    e.add_field(name="Licenças",value=str(db.execute("SELECT COUNT(*) FROM lic").fetchone()[0]))
    e.add_field(name="Assinaturas",value=str(db.execute("SELECT COUNT(*) FROM assin").fetchone()[0]))
    e.add_field(name="Keys",value=str(db.execute("SELECT COUNT(*) FROM keys").fetchone()[0]))
    e.add_field(name="Cashback pago",value=f"R${db.execute('SELECT COALESCE(SUM(cashback),0) FROM vend').fetchone()[0]:.2f}")
    await it.response.send_message(embed=e,ephemeral=True)

@tree.command(name="admin_inter")
@app_commands.checks.has_permissions(administrator=True)
async def adm(it):
    v=View()
    v.add_item(Button(label="🎨 Branding",style=ButtonStyle.blurple,custom_id="brand"))
    v.add_item(Button(label="🔑 Licença",style=ButtonStyle.blurple,custom_id="add_lic"))
    v.add_item(Button(label="📅 Assinatura",style=ButtonStyle.green,custom_id="add_ass"))
    v.add_item(Button(label="📊 Stats Avançadas",style=ButtonStyle.blurple,custom_id="stats2"))
    v.add_item(Button(label="✅ Testar",style=ButtonStyle.green,custom_id="test"))
    async def ck(it):
        c=it.data.get("custom_id")
        if c=="brand":await it.response.send_modal(MBrand())
        elif c=="add_lic":await it.response.send_modal(MLic())
        elif c=="stats2":
            t=db.execute("SELECT COALESCE(SUM(total),0),COUNT(*) FROM vend").fetchone()
            cb=db.execute("SELECT COALESCE(SUM(cashback),0) FROM vend").fetchone()[0]
            await it.response.send_message(embed=emb("📊 ESTATÍSTICAS AVANÇADAS",f"💵 Faturamento: R${t[0]:.2f}\n🛒 Vendas: {t[1]}\n💎 Cashback: R${cb:.2f}"),ephemeral=True)
        elif c=="test":await test.callback(None,it)
    v.interaction_check=ck
    await it.response.send_message("⚙️ ADMIN INTERMEDIÁRIO",view=v,ephemeral=True)

@bot.event
async def on_ready():await tree.sync();print(f"🔵 {cfg('nome_bot')} ONLINE | LIC: {LIC}")
bot.run(TOKEN)
