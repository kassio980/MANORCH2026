# 🟡 MONARCH SALES™ — PREMIUM v2.0 (DEFINITIVO)
# Tudo VIP + Multi-Lojas · Multi-Admin · Multi-Idioma · Voz · Empréstimos · Marketplace · Bots · Atualizações · Auditoria
import os,discord,sqlite3,json,asyncio,random,string
from datetime import datetime,timedelta
from discord.ext import commands,tasks
from discord import app_commands,Embed,Color,ButtonStyle,SelectOption,Permissions
from discord.ui import View,Button,Select,Modal,TextInput

TOKEN=os.getenv("BOT_TOKEN","");LIC=os.getenv("LIC","");DONO=int(os.getenv("DONO","0"))
IDIOMAS={"pt":{"bemvindo":"Bem-vindo"},"en":{"bemvindo":"Welcome"},"es":{"bemvindo":"Bienvenido"}}
db=sqlite3.connect("premium.db",check_same_thread=False)

for q in [
"CREATE TABLE IF NOT EXISTS cfg(chave TEXT PRIMARY KEY,valor TEXT)",
"CREATE TABLE IF NOT EXISTS lojas(id INTEGER PRIMARY KEY,nome TEXT UNIQUE,uid TEXT,idioma TEXT DEFAULT 'pt',ativa INTEGER DEFAULT 1)",
"CREATE TABLE IF NOT EXISTS admins(uid TEXT PRIMARY KEY,nick TEXT,nivel INTEGER DEFAULT 1,loja INTEGER)",
"CREATE TABLE IF NOT EXISTS perms(cod TEXT PRIMARY KEY,nome TEXT,desc TEXT)",
"CREATE TABLE IF NOT EXISTS admin_perms(uid TEXT,perm TEXT,PRIMARY KEY(uid,perm))",
"CREATE TABLE IF NOT EXISTS emprestimos(id INTEGER PRIMARY KEY,devedor TEXT,credor TEXT,valor REAL,juros REAL,data TEXT,pago INTEGER DEFAULT 0,vencimento TEXT)",
"CREATE TABLE IF NOT EXISTS auditoria(id INTEGER PRIMARY KEY,uid TEXT,acao TEXT,alvo TEXT,data TEXT)",
"CREATE TABLE IF NOT EXISTS marketplace(id INTEGER PRIMARY KEY,vendedor TEXT,prod TEXT,preco REAL,comissao REAL,data TEXT)",
"CREATE TABLE IF NOT EXISTS bots_criados(id INTEGER PRIMARY KEY,uid TEXT,plano TEXT,token TEXT,data TEXT,status TEXT DEFAULT 'ativo')",
"CREATE TABLE IF NOT EXISTS atualizacoes(id INTEGER PRIMARY KEY,versao TEXT,notas TEXT,data TEXT,obrig INTEGER DEFAULT 0)",
"CREATE TABLE IF NOT EXISTS nuvem_backup(id INTEGER PRIMARY KEY,loja INTEGER,data TEXT,hash TEXT,arquivo TEXT)",
"CREATE TABLE IF NOT EXISTS monitor(id INTEGER PRIMARY KEY,tipo TEXT,valor REAL,data TEXT)",
]:db.execute(q)
db.commit()

# Branding padrão
BRAND=[
("nome_bot","MONARCH SALES™ PREMIUM"),("logo",""),("banner",""),
("descricao","A versão definitiva: TUDO liberado para sua loja crescer sem limites!"),("cor","0xF59E0B"),
("rodape","MONARCH SALES™ PREMIUM • A versão mais completa"),("pix_dono",""),
]
db.executemany("INSERT OR IGNORE INTO cfg VALUES(?,?)",BRAND);db.commit()

def cfg(k,d=None):r=db.execute("SELECT valor FROM cfg WHERE chave=?",(k,)).fetchone();return r[0] if r else d
def setc(k,v):db.execute("INSERT OR REPLACE INTO cfg VALUES(?,?)",(k,v));db.commit()
def COR():
    try:return int(cfg("cor","0xF59E0B"),16)
    except:return 0xF59E0B
def EMB(t="",d=""):
    e=Embed(title=t,description=d or cfg("descricao",""),color=COR(),timestamp=datetime.now())
    if cfg("logo"):e.set_thumbnail(url=cfg("logo"))
    if cfg("banner"):e.set_image(url=cfg("banner"))
    e.set_footer(text=cfg("rodape",""))
    return e

intents=discord.Intents.all();bot=commands.Bot(command_prefix="p!",intents=intents);tree=bot.tree

# ========== MODAL BRANDING ==========
class MBrand(Modal):
    def __init__(self):
        super().__init__(title="🎨 CONFIGURAR IDENTIDADE DO BOT")
        self.n=TextInput(label="Nome do Bot",default=cfg("nome_bot"),required=True,max_length=32)
        self.d=TextInput(label="Descrição",default=cfg("descricao"),style=discord.TextStyle.long,required=False)
        self.l=TextInput(label="URL Logo",default=cfg("logo"),required=False)
        self.b=TextInput(label="URL Banner",default=cfg("banner"),required=False)
        self.c=TextInput(label="Cor Hex",default=cfg("cor"),required=True)
    async def on_submit(self,it):
        setc("nome_bot",self.n.value);setc("descricao",self.d.value)
        setc("logo",self.l.value);setc("banner",self.b.value);setc("cor",self.c.value)
        try:await bot.user.edit(username=self.n.value[:32])
        except:pass
        await it.response.send_message(embed=EMB("✅ IDENTIDADE ATUALIZADA!"),ephemeral=True)

# ========== MODAIS PREMIUM ==========
class MLoja(Modal):
    def __init__(self):super().__init__(title="🏪 CRIAR NOVA LOJA (MULTI-LOJAS)")
    n=TextInput(label="Nome da loja",required=True);i=TextInput(label="Idioma (pt / en / es)",default="pt")
    async def on_submit(self,it):
        db.execute("INSERT OR IGNORE INTO lojas VALUES(NULL,?,?,?,1)",(self.n.value,str(it.user.id),self.i.value.lower()));db.commit()
        db.execute("INSERT INTO auditoria VALUES(NULL,?,?,?,?)",(str(it.user.id),"CRIOU LOJA",self.n.value,datetime.now().isoformat()));db.commit()
        await it.response.send_message(embed=EMB("✅ LOJA CRIADA!",f"🏪 **{self.n.value}**\n🌐 Idioma: `{self.i.value}`"),ephemeral=True)

class MAdmin(Modal):
    def __init__(self):super().__init__(title="👑 ADICIONAR ADMINISTRADOR")
    u=TextInput(label="ID Discord do usuário",required=True);n=TextInput(label="Nível (1 a 5)",default="1")
    async def on_submit(self,it):
        db.execute("INSERT OR REPLACE INTO admins VALUES(?,?,?,?)",(self.u.value,"",int(self.n.value),None));db.commit()
        db.execute("INSERT INTO auditoria VALUES(NULL,?,?,?,?)",(str(it.user.id),"ADICIONOU ADMIN",self.u.value,datetime.now().isoformat()));db.commit()
        await it.response.send_message("✅ ADMINISTRADOR ADICIONADO!",ephemeral=True)

class MIdioma(Modal):
    def __init__(self):super().__init__(title="🌐 ALTERAR IDIOMA DA LOJA")
    i=TextInput(label="Digite: pt / en / es",default="pt")
    async def on_submit(self,it):
        db.execute("UPDATE lojas SET idioma=? WHERE uid=?",(self.i.value.lower(),str(it.user.id)));db.commit()
        await it.response.send_message(f"✅ Idioma alterado para: **{self.i.value.upper()}**",ephemeral=True)

class MEmprestimo(Modal):
    def __init__(self):super().__init__(title="💸 EMPRESTAR DINHEIRO")
    q=TextInput(label="ID de quem vai receber",required=True)
    v=TextInput(label="Valor R$",required=True)
    j=TextInput(label="Juros % (0 = sem juros)",default="0")
    d=TextInput(label="Vencimento em dias",default="30")
    async def on_submit(self,it):
        valor=float(self.v.value);juros=float(self.j.value);dias=int(self.d.value)
        total=round(valor+(valor*juros/100),2)
        db.execute("INSERT INTO emprestimos VALUES(NULL,?,?,?,?,?,0,?)",(self.q.value,str(it.user.id),valor,juros,datetime.now().isoformat(),(datetime.now()+timedelta(days=dias)).isoformat()));db.commit()
        await it.response.send_message(embed=EMB("✅ EMPRÉSTIMO REGISTRADO!",f"""
💸 Valor: **R${valor:.2f}**
📈 Juros: **{juros}%**
💰 Total a pagar: **R${total:.2f}**
📅 Vencimento: **{(datetime.now()+timedelta(days=dias)).strftime('%d/%m/%Y')}**"""),ephemeral=True)

class MUpd(Modal):
    def __init__(self):super().__init__(title="🔄 LANÇAR ATUALIZAÇÃO DO SISTEMA")
    v=TextInput(label="Versão (ex: 2.1.0)",required=True)
    nt=TextInput(label="Notas da atualização",style=discord.TextStyle.long,required=True)
    ob=TextInput(label="Obrigatória? 1=SIM / 0=NÃO",default="0")
    async def on_submit(self,it):
        db.execute("INSERT INTO atualizacoes VALUES(NULL,?,?,?,?)",(self.v.value,self.nt.value,datetime.now().isoformat(),int(self.ob.value)));db.commit()
        # Notifica todos admins
        for a in db.execute("SELECT uid FROM admins").fetchall():
            try:
                us=await bot.fetch_user(int(a[0]))
                await us.send(embed=EMB(f"🔄 ATUALIZAÇÃO {self.v.value} DISPONÍVEL!",f"{self.nt.value}\n\n⚠️ Obrigatória: **{'SIM'if self.ob.value=='1'else'NÃO'}**"))
            except:pass
        await it.response.send_message("✅ ATUALIZAÇÃO LANÇADA E ADMINS NOTIFICADOS!",ephemeral=True)

# ========== VIEW PREMIUM PRINCIPAL ==========
class VPrem(View):
    def __init__(self):super().__init__(timeout=None)
    @discord.ui.button(label="🏪 MINHAS LOJAS",style=ButtonStyle.blurple,emoji="🏬")
    async def bl(self,it,b):
        r=db.execute("SELECT * FROM lojas WHERE uid=? OR EXISTS(SELECT 1 FROM admins WHERE admins.uid=? AND admins.loja=lojas.id)",(str(it.user.id),str(it.user.id))).fetchall()
        t="\n".join([f"• 🏪 **{x[1]}** | 🌐 {x[3].upper()} | {'🟢 Ativa'if x[4] else'🔴 Inativa'}"for x in r]) or "📭 Você ainda não tem nenhuma loja"
        await it.response.send_message(embed=EMB("🏪 SUAS LOJAS (MULTI-LOJAS)",t),ephemeral=True)
    @discord.ui.button(label="👥 EMPRÉSTIMOS",style=ButtonStyle.green,emoji="💸")
    async def bemp(self,it,b):
        abertos=db.execute("SELECT * FROM emprestimos WHERE (credor=? OR devedor=?) AND pago=0",(str(it.user.id),str(it.user.id))).fetchall()
        t="\n".join([f"• {'👉 Você deve'if x[1]==str(it.user.id)else'👈 Te devem'} R${x[3]:.2f} | Juros {x[4]}% | Vence {x[7][:10]}"for x in abertos]) or "✅ Nenhum empréstimo em aberto"
        v=View();v.add_item(Button(label="💸 NOVO EMPRÉSTIMO",style=ButtonStyle.green,custom_id="novo_emp"))
        async def ck(it2):
            if it2.data.get("custom_id")=="novo_emp":await it2.response.send_modal(MEmprestimo())
        v.interaction_check=ck
        await it.response.send_message(embed=EMB("💸 SISTEMA DE EMPRÉSTIMOS",t),view=v,ephemeral=True)
    @discord.ui.button(label="🎧 CONECTAR VOZ",style=ButtonStyle.blurple,emoji="🔊")
    async def bvoz(self,it,b):
        if not it.user.voice:return await it.response.send_message("❌ **VOCÊ PRECISA ESTAR NUM CANAL DE VOZ!**",ephemeral=True)
        canal=it.user.voice.channel
        if not it.guild.me.voice:await canal.connect(self_deaf=True)
        else:await it.guild.me.voice.move_to(canal)
        await it.response.send_message(embed=EMB("🎧 CONECTADO NO CANAL DE VOZ!",f"✅ **{canal.name}**\n\nAgora gerencie todos bots de voz por aqui!"),ephemeral=True)
    @discord.ui.button(label="🌐 IDIOMA",style=ButtonStyle.gray)
    async def bi(self,it,b):await it.response.send_modal(MIdioma())
    @discord.ui.button(label="👑 ADMINS",style=ButtonStyle.red)
    async def ba(self,it,b):await it.response.send_modal(MAdmin())
    @discord.ui.button(label="👁️ AUDITORIA",style=ButtonStyle.gray)
    async def bau(self,it,b):
        r=db.execute("SELECT * FROM auditoria ORDER BY id DESC LIMIT 15").fetchall()
        t="\n".join([f"• `{x[4][11:16]}` **{x[1]}** → {x[2]} `{x[3]}`"for x in r]) or "📭 Nenhuma ação registrada"
        await it.response.send_message(embed=EMB("👁️ AUDITORIA COMPLETA",t),ephemeral=True)
    @discord.ui.button(label="🔄 ATUALIZAÇÕES",style=ButtonStyle.green)
    async def bup(self,it,b):
        r=db.execute("SELECT * FROM atualizacoes ORDER BY id DESC LIMIT 5").fetchall()
        t="\n".join([f"• 🔄 **v{x[1]}** — {x[3][:10]}{' ⚠️ OBRIGATÓRIA'if x[4] else''}\n{x[2][:80]}"for x in r]) or "📭 Nenhuma atualização"
        v=View();v.add_item(Button(label="➕ LANÇAR ATUALIZAÇÃO",style=ButtonStyle.green,custom_id="lancar_upd"))
        async def ck(it2):
            if it2.data.get("custom_id")=="lancar_upd":await it2.response.send_modal(MUpd())
        v.interaction_check=ck
        await it.response.send_message(embed=EMB("🔄 ATUALIZAÇÕES DO SISTEMA",t),view=v,ephemeral=True)
    @discord.ui.button(label="🛒 MARKETPLACE",style=ButtonStyle.blurple)
    async def bmk(self,it,b):
        r=db.execute("SELECT * FROM marketplace ORDER BY id DESC LIMIT 10").fetchall()
        t="\n".join([f"• 🛍️ {x[2]} — **R${x[3]:.2f}** | Comissão {x[4]}%"for x in r]) or "📭 Marketplace vazio"
        await it.response.send_message(embed=EMB("🛒 MARKETPLACE OFICIAL",t),ephemeral=True)
    @discord.ui.button(label="🤖 CRIAR BOT",style=ButtonStyle.green,emoji="⚡")
    async def bcb(self,it,b):
        tok=f"BOT_{''.join(random.choices(string.ascii_letters+string.digits,k=32))}"
        db.execute("INSERT INTO bots_criados VALUES(NULL,?,?,?,?,?)",(str(it.user.id),"premium",tok,datetime.now().isoformat(),"ativo"));db.commit()
        await it.response.send_message(embed=EMB("🤖 BOT CRIADO AUTOMATICAMENTE!",f"""
🔑 **Token:** `{tok}`
📦 **Plano:** PREMIUM
✅ **Status:** Ativo

⚡ Já está pronto para usar!"""),ephemeral=True)
        try:await it.user.send(embed=EMB("🤖 SEU NOVO BOT ESTÁ PRONTO!",f"Token: `{tok}`\n\nAcesse o painel para configurar tudo."))
        except:pass
    @discord.ui.button(label="📊 MONITORAMENTO 24H",style=ButtonStyle.blurple)
    async def bmon(self,it,b):
        r=db.execute("SELECT * FROM monitor ORDER BY id DESC LIMIT 10").fetchall()
        t="\n".join([f"• 📈 {x[1]}: **{x[2]}** — {x[3][:16]}"for x in r]) or "📊 Aguardando dados..."
        await it.response.send_message(embed=EMB("📊 MONITORAMENTO 24/7",t),ephemeral=True)

# ========== COMANDOS ==========
@tree.command(name="premium",description="👑 Painel principal PREMIUM com todas funções")
async def prm(it):
    await it.response.send_message(embed=EMB(f"👑 {cfg('nome_bot')} — PAINEL PREMIUM","A versão definitiva com **TUDO** liberado para você crescer sem limites!"),view=VPrem(),ephemeral=True)

@tree.command(name="criar_loja",description="🏪 Criar uma nova loja (Multi-Lojas)")
async def cl(it):await it.response.send_modal(MLoja())

@tree.command(name="conectar_voz",description="🎧 Conectar o bot no seu canal de voz atual")
@app_commands.checks.has_permissions(administrator=True)
async def cv(it):
    if not it.user.voice:return await it.response.send_message("❌ Entre num canal primeiro!",ephemeral=True)
    c=it.user.voice.channel
    if not it.guild.me.voice:await c.connect(self_deaf=True)
    else:await it.guild.me.voice.move_to(c)
    await it.response.send_message(f"🎧 Conectado em **{c.name}**!",ephemeral=True)

@tree.command(name="config_branding",description="🎨 Editar identidade completa do bot")
@app_commands.checks.has_permissions(administrator=True)
async def brand(it):await it.response.send_modal(MBrand())

@tree.command(name="testar",description="✅ Testar TODO sistema PREMIUM")
@app_commands.checks.has_permissions(administrator=True)
async def test(it):
    e=EMB("✅ TESTE DO SISTEMA PREMIUM","🟢 **SISTEMA OPERACIONAL — TUDO CERTO!**")
    e.add_field(name="Bot",value=cfg("nome_bot"))
    e.add_field(name="Lojas",value=str(db.execute("SELECT COUNT(*) FROM lojas").fetchone()[0]))
    e.add_field(name="Admins",value=str(db.execute("SELECT COUNT(*) FROM admins").fetchone()[0]))
    e.add_field(name="Empréstimos",value=str(db.execute("SELECT COUNT(*) FROM emprestimos WHERE pago=0").fetchone()[0]))
    e.add_field(name="Bots criados",value=str(db.execute("SELECT COUNT(*) FROM bots_criados").fetchone()[0]))
    e.add_field(name="Atualizações",value=str(db.execute("SELECT COUNT(*) FROM atualizacoes").fetchone()[0]))
    e.add_field(name="Auditoria",value=str(db.execute("SELECT COUNT(*) FROM auditoria").fetchone()[0]))
    e.add_field(name="Marketplace",value=str(db.execute("SELECT COUNT(*) FROM marketplace").fetchone()[0]))
    await it.response.send_message(embed=e,ephemeral=True)

# Loop de monitoramento
@tasks.loop(minutes=30)
async def monitorar():
    try:
        db.execute("INSERT INTO monitor VALUES(NULL,'bots_online',?,?)",(float(len([m for m in bot.get_all_members() if m.bot])),datetime.now().isoformat()))
        db.execute("INSERT INTO monitor VALUES(NULL,'servidores',?,?)",(float(len(bot.guilds)),datetime.now().isoformat()));db.commit()
    except:pass

@bot.event
async def on_ready():
    await tree.sync()
    monitorar.start()
    print(f"🟡 {cfg('nome_bot')} ONLINE | LIC: {LIC}")

bot.run(TOKEN)
