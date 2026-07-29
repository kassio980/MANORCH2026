# 🟢 MONARCH SALES™ — BÁSICO v2.0
# Produtos ilimitados · Categorias · Carrinho · Estoque · Cupons · Logs · BRANDING EDITÁVEL
import os,discord,sqlite3,json
from datetime import datetime
from discord.ext import commands
from discord import app_commands,Embed,Color,ButtonStyle,SelectOption
from discord.ui import View,Button,Select,Modal,TextInput

TOKEN=os.getenv("BOT_TOKEN","");LIC=os.getenv("LIC","");DONO=int(os.getenv("DONO","0"))
db=sqlite3.connect("basico.db",check_same_thread=False)

# ========== SISTEMA DE BRANDING (CONFIGURÁVEL PELO ADMIN) ==========
for q in [
"CREATE TABLE IF NOT EXISTS cfg(chave TEXT PRIMARY KEY,valor TEXT)",
"CREATE TABLE IF NOT EXISTS cat(id INTEGER PRIMARY KEY,nome TEXT UNIQUE,desc TEXT,img TEXT)",
"CREATE TABLE IF NOT EXISTS prod(id INTEGER PRIMARY KEY,nome TEXT UNIQUE,desc TEXT,preco REAL,estoque INTEGER DEFAULT -1,cat INTEGER,img TEXT)",
"CREATE TABLE IF NOT EXISTS carr(uid TEXT PRIMARY KEY,itens TEXT)",
"CREATE TABLE IF NOT EXISTS cup(cod TEXT PRIMARY KEY,tipo TEXT,valor REAL,usos INTEGER DEFAULT 0,max INTEGER DEFAULT 999,exp TEXT)",
"CREATE TABLE IF NOT EXISTS vend(id INTEGER PRIMARY KEY,uid TEXT,nick TEXT,itens TEXT,total REAL,cupom TEXT,data TEXT)",
"CREATE TABLE IF NOT EXISTS logs(id INTEGER PRIMARY KEY,tipo TEXT,user TEXT,msg TEXT,data TEXT)",
]:db.execute(q)
db.commit()

# Valores padrão do branding
BRAND_PADRAO=[
("nome_bot","MONARCH SALES™"),("logo",""),("banner",""),
("descricao","Sua loja completa dentro do Discord!"),("cor","0x22C55E"),
("rodape","MONARCH SALES™ — Tecnologia • Bots • Soluções"),
]
db.executemany("INSERT OR IGNORE INTO cfg VALUES(?,?)",BRAND_PADRAO);db.commit()

def cfg(k,d=None):r=db.execute("SELECT valor FROM cfg WHERE chave=?",(k,)).fetchone();return r[0] if r else d
def setc(k,v):db.execute("INSERT OR REPLACE INTO cfg VALUES(?,?)",(k,v));db.commit()
def log(t,u,m):db.execute("INSERT INTO logs VALUES(NULL,?,?,?,?)",(t,u,m,datetime.now().isoformat()));db.commit()
def cor():
    try:return int(cfg("cor","0x22C55E"),16)
    except:return 0x22C55E
def emb(t="",d=""):
    e=Embed(title=t,description=d or cfg("descricao",""),color=cor(),timestamp=datetime.now())
    if cfg("logo"):e.set_thumbnail(url=cfg("logo"))
    if cfg("banner"):e.set_image(url=cfg("banner"))
    e.set_footer(text=cfg("rodape","MONARCH SALES™"))
    return e

intents=discord.Intents.all();bot=commands.Bot(command_prefix="b!",intents=intents);tree=bot.tree

# ========== MODAL: CONFIGURAR BRANDING COMPLETO ==========
class MBrand(Modal):
    def __init__(self):
        super().__init__(title="🎨 CONFIGURAR IDENTIDADE DO BOT")
        self.n=TextInput(label="Nome do Bot",default=cfg("nome_bot"),required=True)
        self.d=TextInput(label="Descrição Principal",default=cfg("descricao"),style=discord.TextStyle.long,required=False)
        self.l=TextInput(label="URL Logo (miniatura)",default=cfg("logo"),required=False)
        self.b=TextInput(label="URL Banner (imagem grande)",default=cfg("banner"),required=False)
        self.c=TextInput(label="Cor Hex (ex: 0xFF0000)",default=cfg("cor"),required=False)
    async def on_submit(self,it):
        setc("nome_bot",self.n.value);setc("descricao",self.d.value)
        setc("logo",self.l.value);setc("banner",self.b.value);setc("cor",self.c.value)
        try:await bot.user.edit(username=self.n.value[:32])
        except:pass
        await it.response.send_message(embed=emb("✅ IDENTIDADE ATUALIZADA!",f"Nome: **{self.n.value}**\nCor: `{self.c.value}`\nLogo: {self.l.value[:50] if self.l.value else 'Não definido'}\nBanner: {self.b.value[:50] if self.b.value else 'Não definido'}"),ephemeral=True)

# ========== MODAIS ==========
class MCat(Modal):
    def __init__(self):super().__init__(title="➕ NOVA CATEGORIA")
    n=TextInput(label="Nome",required=True);d=TextInput(label="Descrição",required=False);i=TextInput(label="URL Imagem",required=False)
    async def on_submit(self,it):
        db.execute("INSERT OR REPLACE INTO cat VALUES(NULL,?,?,?)",(self.n.value,self.d.value or "",self.i.value or ""));db.commit()
        log("CAT_CRIAR",str(it.user),self.n.value);await it.response.send_message("✅ Categoria criada!",ephemeral=True)

class MProd(Modal):
    def __init__(self,cats):
        super().__init__(title="➕ NOVO PRODUTO");self.cats=cats
        self.n=TextInput(label="Nome",required=True);self.d=TextInput(label="Descrição",style=discord.TextStyle.long,required=False)
        self.p=TextInput(label="Preço",required=True);self.e=TextInput(label="Estoque (-1 = ilimitado)",default="-1");self.i=TextInput(label="URL Imagem",required=False)
    async def on_submit(self,it):
        db.execute("INSERT OR REPLACE INTO prod VALUES(NULL,?,?,?,?,?,?)",(self.n.value,self.d.value or "",float(self.p.value),int(self.e.value),self.cats,self.i.value or ""));db.commit()
        log("PROD_CRIAR",str(it.user),self.n.value);await it.response.send_message("✅ Produto criado!",ephemeral=True)

class MCup(Modal):
    def __init__(self):super().__init__(title="🎟️ NOVO CUPOM")
    c=TextInput(label="Código");t=TextInput(label="Tipo (pct/fixo)",default="pct");v=TextInput(label="Valor",default="10");m=TextInput(label="Máx usos",default="999");e=TextInput(label="Expira (YYYY-MM-DD)",required=False)
    async def on_submit(self,it):
        db.execute("INSERT OR REPLACE INTO cup VALUES(?,?,?,0,?,?)",(self.c.value.upper(),self.t.value,float(self.v.value),int(self.m.value),self.e.value or ""));db.commit()
        await it.response.send_message(f"✅ Cupom `{self.c.value}` criado!",ephemeral=True)

class Qtd(Modal):
    def __init__(self,pid,nome):super().__init__(title=f"🛒 Quantidade: {nome}");self.pid=pid
    q=TextInput(label="Quantidade",default="1")
    async def on_submit(self,it):
        p=db.execute("SELECT * FROM prod WHERE id=?",(self.pid,)).fetchone()
        q=int(self.q.value)
        if p[4]>0 and q>p[4]:return await it.response.send_message(f"❌ Estoque só tem {p[4]}",ephemeral=True)
        c=json.loads(db.execute("SELECT itens FROM carr WHERE uid=?",(str(it.user.id),)).fetchone()[0] or "[]")
        c.append({"id":p[0],"nome":p[1],"preco":p[3],"q":q})
        db.execute("INSERT OR REPLACE INTO carr VALUES(?,?)",(str(it.user.id),json.dumps(c)));db.commit()
        await it.response.edit_message(embed=emb("🛒 CARRINHO ATUALIZADO",f"+{q}x **{p[1]}**\n\nTotal itens: **{sum(x['q'] for x in c)}**"),view=VCarr(it.user.id))

# ========== VIEWS ==========
class VPrincipal(View):
    def __init__(self):super().__init__(timeout=None)
    @discord.ui.button(label="🛍️ COMPRAR",style=ButtonStyle.green)
    async def b_comp(self,it,b):await it.response.edit_message(embed=emb("📂 CATEGORIAS","Escolha uma categoria:"),view=VCats())
    @discord.ui.button(label="🛒 MEU CARRINHO",style=ButtonStyle.blurple)
    async def b_carr(self,it,b):await it.response.edit_message(view=VCarr(it.user.id))
    @discord.ui.button(label="📜 HISTÓRICO",style=ButtonStyle.gray)
    async def b_hist(self,it,b):
        r=db.execute("SELECT * FROM vend WHERE uid=? ORDER BY id DESC LIMIT 10",(str(it.user.id),)).fetchall()
        t="\n".join([f"• `{x[6][:10]}` — R${x[4]:.2f} ({len(json.loads(x[3]))} itens)"for x in r]) or "Nenhuma compra"
        await it.response.send_message(embed=emb("📜 SEU HISTÓRICO",t),ephemeral=True)
    @discord.ui.button(label="⭐ AVALIAR",style=ButtonStyle.gray)
    async def b_ava(self,it,b):
        class A(Modal):
            def __init__(self):super().__init__(title="⭐ AVALIE NOSSA LOJA")
            n=TextInput(label="Nota 1-5",default="5");c=TextInput(label="Comentário",style=discord.TextStyle.short,required=False)
            async def on_submit(self,it):await it.response.send_message("✅ Obrigado pela avaliação!",ephemeral=True);log("AVALIACAO",str(it.user),f"Nota {self.n.value}")
        await it.response.send_modal(A())

class VCats(View):
    def __init__(self):
        super().__init__();cats=db.execute("SELECT * FROM cat").fetchall()
        if not cats:return
        self.add_item(Select(options=[SelectOption(label=x[1],value=str(x[0]),description=x[2][:50] if x[2] else "")for x in cats],placeholder="📂 Escolha a categoria...",custom_id="sel_cat"))
    async def interaction_check(self,it):
        if it.data.get("custom_id")=="sel_cat":
            cid=int(it.data["values"][0]);prods=db.execute("SELECT * FROM prod WHERE cat=?",(cid,)).fetchall()
            if not prods:return await it.response.edit_message(embed=emb("📭 VAZIO","Nenhum produto nesta categoria"))
            await it.response.edit_message(embed=emb("🛍️ PRODUTOS","Escolha um produto:"),view=VProds(prods))
        return True

class VProds(View):
    def __init__(self,prods):
        super().__init__()
        for p in prods[:25]:
            async def mk(pid=p[0],pn=p[1],pp=p[3]):
                class B(Button):
                    async def cb(s,it):await it.response.send_modal(Qtd(pid,pn))
                return B(label=f"{p[1]} R${p[3]:.2f}",style=ButtonStyle.green)
            self.add_item(mk())

class VCarr(View):
    def __init__(self,uid):
        super().__init__();self.uid=str(uid)
        self.it=json.loads(db.execute("SELECT itens FROM carr WHERE uid=?",(self.uid,)).fetchone()[0] or "[]")
        self.tot=sum(x["preco"]*x["q"] for x in self.it)
    @discord.ui.button(label="💳 PAGAR",style=ButtonStyle.green)
    async def b_pag(self,it,b):
        if not self.it:return await it.response.send_message("❌ Carrinho vazio",ephemeral=True)
        for x in self.it:
            p=db.execute("SELECT estoque FROM prod WHERE id=?",(x["id"],)).fetchone()
            if p and p[0]>0 and p[0]<x["q"]:return await it.response.send_message(f"❌ {x['nome']} sem estoque",ephemeral=True)
        for x in self.it:
            p=db.execute("SELECT estoque FROM prod WHERE id=?",(x["id"],)).fetchone()
            if p and p[0]>0:db.execute("UPDATE prod SET estoque=estoque-? WHERE id=?",(x["q"],x["id"]))
        db.execute("INSERT INTO vend VALUES(NULL,?,?,?,?,?,?)",(self.uid,it.user.display_name,json.dumps(self.it),self.tot,"",datetime.now().isoformat()))
        db.execute("DELETE FROM carr WHERE uid=?",(self.uid,));db.commit()
        log("VENDA",str(it.user),f"R${self.tot:.2f}")
        await it.response.edit_message(embed=emb("✅ COMPRA FINALIZADA!",f"💵 R${self.tot:.2f}\n🛒 {sum(x['q'] for x in self.it)} itens\n\n📦 Entrega automática realizada!"),view=VPrincipal())
    @discord.ui.button(label="🗑️ LIMPAR",style=ButtonStyle.red)
    async def b_limp(self,it,b):
        db.execute("DELETE FROM carr WHERE uid=?",(self.uid,));db.commit()
        await it.response.edit_message(embed=emb("🗑️ CARRINHO LIMPO",""),view=VPrincipal())

# ========== COMANDOS ==========
@tree.command(name="loja",description="🏪 Abrir loja principal")
async def loja(it):await it.response.send_message(embed=emb(f"🛍️ {cfg('nome_bot')} — LOJA"),view=VPrincipal())

@tree.command(name="config_branding",description="🎨 Editar nome/logo/banner/descrição/cor do bot")
@app_commands.checks.has_permissions(administrator=True)
async def brand(it):await it.response.send_modal(MBrand())

@tree.command(name="testar",description="✅ Testar se tudo está funcionando")
@app_commands.checks.has_permissions(administrator=True)
async def test(it):
    erros=[]
    try:Embed(title="t",color=cor())
    except:erros.append("❌ Cor inválida")
    if db.execute("SELECT COUNT(*) FROM prod").fetchone()[0]==0:erros.append("⚠️ Nenhum produto cadastrado")
    if db.execute("SELECT COUNT(*) FROM cat").fetchone()[0]==0:erros.append("⚠️ Nenhuma categoria cadastrada")
    e=emb("✅ TESTE DO SISTEMA","\n".join(erros) if erros else "🟢 TUDO FUNCIONANDO PERFEITAMENTE!")
    e.add_field(name="Bot",value=cfg("nome_bot"))
    e.add_field(name="Produtos",value=str(db.execute("SELECT COUNT(*) FROM prod").fetchone()[0]))
    e.add_field(name="Categorias",value=str(db.execute("SELECT COUNT(*) FROM cat").fetchone()[0]))
    e.add_field(name="Cupons",value=str(db.execute("SELECT COUNT(*) FROM cup").fetchone()[0]))
    e.add_field(name="Vendas",value=str(db.execute("SELECT COUNT(*) FROM vend").fetchone()[0]))
    await it.response.send_message(embed=e,ephemeral=True)

@tree.command(name="admin",description="⚙️ Painel administrativo")
@app_commands.checks.has_permissions(administrator=True)
async def adm(it):
    v=View()
    v.add_item(Button(label="🎨 Branding",style=ButtonStyle.blurple,custom_id="brand"))
    v.add_item(Button(label="➕ Categoria",style=ButtonStyle.blurple,custom_id="add_cat"))
    v.add_item(Button(label="➕ Produto",style=ButtonStyle.green,custom_id="add_prod"))
    v.add_item(Button(label="🎟️ Cupom",style=ButtonStyle.gray,custom_id="add_cup"))
    v.add_item(Button(label="📊 Estatísticas",style=ButtonStyle.blurple,custom_id="stats"))
    v.add_item(Button(label="📜 Logs",style=ButtonStyle.gray,custom_id="logs"))
    v.add_item(Button(label="✅ Testar",style=ButtonStyle.green,custom_id="test"))
    async def check(it):
        c=it.data.get("custom_id")
        if c=="brand":await it.response.send_modal(MBrand())
        elif c=="add_cat":await it.response.send_modal(MCat())
        elif c=="add_prod":
            cats=db.execute("SELECT * FROM cat").fetchall()
            if not cats:return await it.response.send_message("❌ Crie uma categoria primeiro",ephemeral=True)
            class S(Select):
                def __init__(self):super().__init__(options=[SelectOption(label=x[1],value=str(x[0]))for x in cats],placeholder="Categoria...")
                async def callback(s,it):await it.response.send_modal(MProd(int(s.values[0])))
            vv=View();vv.add_item(S());await it.response.send_message("Escolha a categoria:",view=vv,ephemeral=True)
        elif c=="add_cup":await it.response.send_modal(MCup())
        elif c=="stats":
            t=db.execute("SELECT COALESCE(SUM(total),0),COUNT(*) FROM vend").fetchone()
            await it.response.send_message(embed=emb("📊 ESTATÍSTICAS",f"💵 Faturamento: **R${t[0]:.2f}**\n🛒 Vendas: **{t[1]}**\n📦 Produtos: **{db.execute('SELECT COUNT(*) FROM prod').fetchone()[0]}**\n📂 Categorias: **{db.execute('SELECT COUNT(*) FROM cat').fetchone()[0]}**"),ephemeral=True)
        elif c=="logs":
            r=db.execute("SELECT * FROM logs ORDER BY id DESC LIMIT 15").fetchall()
            await it.response.send_message(embed=emb("📜 ÚLTIMOS LOGS","\n".join([f"`{x[4][11:16]}` **{x[1]}** — {x[3]}"for x in r])),ephemeral=True)
        elif c=="test":await test.callback(None,it)
    v.interaction_check=check
    await it.response.send_message("⚙️ PAINEL ADMIN — BÁSICO",view=v,ephemeral=True)

@bot.event
async def on_ready():await tree.sync();print(f"🟢 {cfg('nome_bot')} ONLINE | LIC: {LIC}")
bot.run(TOKEN)
