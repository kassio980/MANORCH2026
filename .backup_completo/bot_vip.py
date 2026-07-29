# 🟣 MONARCH SALES™ — VIP v2.0
import os,discord,sqlite3,json,shutil,random,string
from datetime import datetime,timedelta
from discord.ext import commands
from discord import app_commands,Embed,Color,ButtonStyle,SelectOption
from discord.ui import View,Button,Select,Modal,TextInput

TOKEN=os.getenv("BOT_TOKEN","")
LIC=os.getenv("LIC","")
DONO=int(os.getenv("DONO","0"))
db=sqlite3.connect("vip.db",check_same_thread=False)

for q in [
"CREATE TABLE IF NOT EXISTS cfg(chave TEXT PRIMARY KEY,valor TEXT)",
"CREATE TABLE IF NOT EXISTS users(uid TEXT PRIMARY KEY,nick TEXT,saldo REAL DEFAULT 0,senha TEXT,afiliado TEXT,comissao REAL DEFAULT 0)",
"CREATE TABLE IF NOT EXISTS trans(id INTEGER PRIMARY KEY,uid TEXT,tipo TEXT,valor REAL,taxa REAL,data TEXT,ref TEXT,status TEXT)",
"CREATE TABLE IF NOT EXISTS afiliados(cod TEXT PRIMARY KEY,uid TEXT,ganhos REAL DEFAULT 0,vendas INTEGER DEFAULT 0)",
"CREATE TABLE IF NOT EXISTS revendedores(uid TEXT PRIMARY KEY,nick TEXT,nivel INTEGER DEFAULT 1,desconto REAL DEFAULT 5)",
"CREATE TABLE IF NOT EXISTS tickets(id INTEGER PRIMARY KEY,uid TEXT,nick TEXT,assunto TEXT,status TEXT DEFAULT 'aberto',data TEXT)",
"CREATE TABLE IF NOT EXISTS msgs_ticket(id INTEGER PRIMARY KEY,tid INTEGER,uid TEXT,msg TEXT,data TEXT)",
"CREATE TABLE IF NOT EXISTS backup(id INTEGER PRIMARY KEY,data TEXT,arquivo TEXT)",
]:db.execute(q)
db.commit()

BRAND=[
("nome_bot","MONARCH SALES™ VIP"),("logo",""),("banner",""),
("descricao","Carteira virtual completa"),("cor","0x8B5CF6"),
("rodape","MONARCH SALES™ VIP"),("pix_dono",""),
]
db.executemany("INSERT OR IGNORE INTO cfg VALUES(?,?)",BRAND);db.commit()

def cfg(k,d=None):
    r=db.execute("SELECT valor FROM cfg WHERE chave=?",(k,)).fetchone()
    return r[0] if r else d
def setc(k,v):
    db.execute("INSERT OR REPLACE INTO cfg VALUES(?,?)",(k,v));db.commit()
def u(user):
    db.execute("INSERT OR IGNORE INTO users VALUES(?,?,0,NULL,NULL,0)",(str(user.id),user.display_name));db.commit()
    return str(user.id)
def saldo(uid):
    return float(db.execute("SELECT saldo FROM users WHERE uid=?",(str(uid),)).fetchone()[0] or 0)
def COR():
    try:return int(cfg("cor","0x8B5CF6"),16)
    except:return 0x8B5CF6
def EMB(t="",d=""):
    e=Embed(title=t,description=d or cfg("descricao",""),color=COR(),timestamp=datetime.now())
    if cfg("logo"):e.set_thumbnail(url=cfg("logo"))
    if cfg("banner"):e.set_image(url=cfg("banner"))
    e.set_footer(text=cfg("rodape",""))
    return e

intents=discord.Intents.all()
bot=commands.Bot(command_prefix="v!",intents=intents)
tree=bot.tree

class MBrand(Modal):
    def __init__(self):
        super().__init__(title="CONFIGURAR IDENTIDADE")
        self.n=TextInput(label="Nome",default=cfg("nome_bot"),max_length=32)
        self.d=TextInput(label="Descricao",default=cfg("descricao"),style=discord.TextStyle.long,required=False)
        self.l=TextInput(label="Logo URL",default=cfg("logo"),required=False)
        self.b=TextInput(label="Banner URL",default=cfg("banner"),required=False)
        self.c=TextInput(label="Cor Hex",default=cfg("cor"))
    async def on_submit(self,it):
        setc("nome_bot",self.n.value);setc("descricao",self.d.value)
        setc("logo",self.l.value);setc("banner",self.b.value);setc("cor",self.c.value)
        try:await bot.user.edit(username=self.n.value[:32])
        except:pass
        await it.response.send_message(embed=EMB("✅ OK"),ephemeral=True)

class MPix(Modal):
    def __init__(self):super().__init__(title="CONFIGURAR PIX")
    self.p=TextInput(label="Chave Pix",default=cfg("pix_dono"))
    async def on_submit(self,it):
        setc("pix_dono",self.p.value)
        await it.response.send_message(embed=EMB("✅ PIX OK"),ephemeral=True)

class MDep(Modal):
    def __init__(self):super().__init__(title="DEPOSITAR")
    self.v=TextInput(label="Valor R$ (5-2500)",default="50")
    async def on_submit(self,it):
        v=float(self.v.value.replace(",","."))
        if v<5 or v>2500:return await it.response.send_message("❌ 5-2500",ephemeral=True)
        if not cfg("pix_dono"):return await it.response.send_message("❌ PIX NAO CONFIG",ephemeral=True)
        ref=f"DEP-{it.user.id}-{int(datetime.now().timestamp())}"
        db.execute("INSERT INTO trans VALUES(NULL,?,'DEP',?,0,?,?,?)",(u(it.user),v,datetime.now().isoformat(),ref,"pendente"));db.commit()
        await it.response.send_message(embed=EMB(f"💰 DEP R${v:.2f}",f"PIX: `{cfg('pix_dono')}`\nRef: `{ref}`"),ephemeral=True)

class MSenha(Modal):
    def __init__(self):super().__init__(title="CRIAR SENHA 6 DIGITOS")
    s1=TextInput(label="Senha 6 numeros",max_length=6,min_length=6)
    s2=TextInput(label="Repetir",max_length=6,min_length=6)
    async def on_submit(self,it):
        if self.s1.value!=self.s2.value:return await it.response.send_message("❌ Diferente",ephemeral=True)
        if not self.s1.value.isdigit():return await it.response.send_message("❌ So numeros",ephemeral=True)
        f=["123456","000000","111111","222222","333333","444444","555555","666666","777777","888888","999999","121212","123123","654321"]
        if self.s1.value in f:return await it.response.send_message("❌ Fraca",ephemeral=True)
        db.execute("UPDATE users SET senha=? WHERE uid=?",(self.s1.value,u(it.user)));db.commit()
        await it.response.send_message(embed=EMB("✅ SENHA CRIADA"),ephemeral=True)

class MSaq(Modal):
    def __init__(self):super().__init__(title="SACAR")
    self.v=TextInput(label="Valor R$",required=True)
    self.p=TextInput(label="Chave Pix",required=True)
    self.n=TextInput(label="Nome",required=True)
    self.s=TextInput(label="Senha 6 dig",required=True,max_length=6)
    async def on_submit(self,it):
        us=db.execute("SELECT * FROM users WHERE uid=?",(u(it.user),)).fetchone()
        if not us[3] or us[3]!=self.s.value:return await it.response.send_message("❌ Senha errada",ephemeral=True)
        v=float(self.v.value.replace(",","."))
        if v<5 or v>2500:return await it.response.send_message("❌ 5-2500",ephemeral=True)
        if saldo(it.user.id)<v:return await it.response.send_message("❌ Saldo insuficiente",ephemeral=True)
        tx=round(v*0.15,2);lq=round(v-tx,2)
        db.execute("UPDATE users SET saldo=saldo-? WHERE uid=?",(v,u(it.user)))
        ref=f"SAQ-{int(datetime.now().timestamp())}"
        db.execute("INSERT INTO trans VALUES(NULL,?,'SAQ',?,?,?,?,?)",(u(it.user),lq,tx,datetime.now().isoformat(),ref,"processando"));db.commit()
        await it.response.send_message(embed=EMB("💸 SAQUE OK",f"Bruto R${v:.2f}\nTaxa R${tx:.2f}\nLiquido R${lq:.2f}\nPix `{self.p.value}`"),ephemeral=True)

class MAfil(Modal):
    def __init__(self):super().__init__(title="AFILIADO")
    c=TextInput(label="Cod indicacao (opcional)",required=False)
    async def on_submit(self,it):
        cod=''.join(random.choices(string.ascii_uppercase+string.digits,k=8))
        db.execute("INSERT OR IGNORE INTO afiliados VALUES(?,?,0,0)",(cod,u(it.user)));db.commit()
        await it.response.send_message(embed=EMB("✅ AFILIADO",f"Cod: `{cod}`"),ephemeral=True)

class MTicket(Modal):
    def __init__(self):super().__init__(title="TICKET")
    a=TextInput(label="Assunto",required=True)
    m=TextInput(label="Mensagem",style=discord.TextStyle.long,required=True)
    async def on_submit(self,it):
        db.execute("INSERT INTO tickets VALUES(NULL,?,?,?,'aberto',?)",(u(it.user),it.user.display_name,self.a.value,datetime.now().isoformat()))
        tid=db.execute("SELECT last_insert_rowid()").fetchone()[0]
        db.execute("INSERT INTO msgs_ticket VALUES(NULL,?,?,?,?)",(tid,u(it.user),self.m.value,datetime.now().isoformat()));db.commit()
        await it.response.send_message(f"✅ Ticket #{tid}",ephemeral=True)

class VCarteira(View):
    def __init__(self,uid):super().__init__(timeout=None);self.uid=uid
    @discord.ui.button(label="💰 DEP",style=ButtonStyle.green)
    async def bd(self,it,b):await it.response.send_modal(MDep())
    @discord.ui.button(label="💸 SAQ",style=ButtonStyle.red)
    async def bs(self,it,b):
        us=db.execute("SELECT senha FROM users WHERE uid=?",(self.uid,)).fetchone()
        if not us or not us[0]:return await it.response.send_modal(MSenha())
        await it.response.send_modal(MSaq())
    @discord.ui.button(label="🔐 SENHA",style=ButtonStyle.gray)
    async def bsen(self,it,b):await it.response.send_modal(MSenha())
    @discord.ui.button(label="📜 EXTRATO",style=ButtonStyle.blurple)
    async def bex(self,it,b):
        r=db.execute("SELECT * FROM trans WHERE uid=? ORDER BY id DESC LIMIT 10",(self.uid,)).fetchall()
        t="\n".join([f"{x[2]} R${x[3]:.2f} {x[5][:10]}"for x in r]) or "Vazio"
        await it.response.send_message(embed=EMB(f"EXTRATO Saldo R${saldo(self.uid):.2f}",t),ephemeral=True)
    @discord.ui.button(label="🤝 AFILIADO",style=ButtonStyle.green)
    async def baf(self,it,b):await it.response.send_modal(MAfil())
    @discord.ui.button(label="🎫 TICKET",style=ButtonStyle.gray)
    async def btk(self,it,b):await it.response.send_modal(MTicket())

class VAdmin(View):
    def __init__(self):super().__init__(timeout=None)
    @discord.ui.button(label="🎨 BRANDING",style=ButtonStyle.blurple)
    async def bb(self,it,b):await it.response.send_modal(MBrand())
    @discord.ui.button(label="💰 PIX",style=ButtonStyle.green)
    async def bp(self,it,b):await it.response.send_modal(MPix())
    @discord.ui.button(label="💾 BACKUP",style=ButtonStyle.gray)
    async def bk(self,it,b):
        arq=f"/tmp/bkp_{int(datetime.now().timestamp())}.db"
        shutil.copy("vip.db",arq)
        await it.response.send_message("OK",file=discord.File(arq),ephemeral=True)
    @discord.ui.button(label="📊 RELATORIO",style=ButtonStyle.blurple)
    async def br(self,it,b):
        t=db.execute("SELECT COALESCE(SUM(CASE tipo WHEN 'DEP' THEN valor END),0),COALESCE(SUM(CASE tipo WHEN 'SAQ' THEN valor END),0),COALESCE(SUM(CASE tipo WHEN 'SAQ' THEN taxa END),0) FROM trans").fetchone()
        await it.response.send_message(embed=EMB("RELATORIO",f"DEP R${t[0]:.2f}\nSAQ R${t[1]:.2f}\nLUCRO R${t[2]:.2f}"),ephemeral=True)
    @discord.ui.button(label="✅ TESTAR",style=ButtonStyle.green)
    async def bt(self,it,b):
        e=EMB("TESTE VIP","🟢 OK")
        e.add_field(name="Users",value=str(db.execute("SELECT COUNT(*) FROM users").fetchone()[0]))
        e.add_field(name="Trans",value=str(db.execute("SELECT COUNT(*) FROM trans").fetchone()[0]))
        await it.response.send_message(embed=e,ephemeral=True)

@tree.command(name="carteira")
async def cart(it):
    uu=u(it.user)
    await it.response.send_message(embed=EMB(f"CARTEIRA R${saldo(uu):.2f}"),view=VCarteira(uu),ephemeral=True)

@tree.command(name="config_branding")
@app_commands.checks.has_permissions(administrator=True)
async def brand(it):await it.response.send_modal(MBrand())

@tree.command(name="testar")
@app_commands.checks.has_permissions(administrator=True)
async def test(it):
    e=EMB("TESTE VIP","🟢 TUDO OK")
    e.add_field(name="Bot",value=cfg("nome_bot"))
    await it.response.send_message(embed=e,ephemeral=True)

@tree.command(name="admin_vip")
@app_commands.checks.has_permissions(administrator=True)
async def adm(it):await it.response.send_message("ADMIN VIP",view=VAdmin(),ephemeral=True)

@bot.event
async def on_ready():
    await tree.sync()
    print(f"🟣 VIP OK: {cfg('nome_bot')}")

bot.run(TOKEN)
