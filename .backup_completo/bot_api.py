# ==================================================
# 👑 BOT API MONARCH TECH™ — SISTEMA COMPLETO
# 📦 4 BOTS ARMAZENADOS | LOJA | SALDO | PIX | LICENÇAS
# ==================================================
import os,re,json,sqlite3,asyncio,random,string
from datetime import datetime,timedelta
from dotenv import load_dotenv
import discord
from discord import app_commands,Interaction,Embed,Color,ButtonStyle,SelectOption
from discord.ui import View,Button,Select,Modal,TextInput

load_dotenv()
TOKEN = os.getenv("TOKEN_API")
ID_DONO = int(os.getenv("ID_DONO","0"))
GUILD = int(os.getenv("SERVIDOR_OFICIAL","0"))
EMPRESA = os.getenv("EMPRESA","MONARCH TECH™")
COR = int(os.getenv("COR","0xFF8C00"),16)
PIX_DONO = os.getenv("CHAVE_PIX","")

DB = "dados/api_principal.db"
def db():
    c=sqlite3.connect(DB);c.row_factory=sqlite3.Row;return c
def init_db():
    with db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS planos(id TEXT PRIMARY KEY,nome TEXT,preco REAL,desc TEXT,arquivo TEXT,logo TEXT,banner TEXT,video TEXT,ativo INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS usuarios(uid TEXT PRIMARY KEY,nick TEXT,id_discord TEXT UNIQUE,saldo REAL DEFAULT 0,senha_saque TEXT,cadastrado INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS licencas(id TEXT PRIMARY KEY,uid TEXT,plano TEXT,api_key TEXT UNIQUE,bot_token TEXT,dono_bot INTEGER,validade TEXT,status TEXT DEFAULT 'ativa',servidor_id INTEGER,servidor_nome TEXT);
        CREATE TABLE IF NOT EXISTS carrinhos(uid TEXT PRIMARY KEY,itens TEXT);
        CREATE TABLE IF NOT EXISTS transacoes(id INTEGER PRIMARY KEY,uid TEXT,tipo TEXT,valor REAL,taxa REAL,data TEXT,ref TEXT,status TEXT);
        CREATE TABLE IF NOT EXISTS configs(chave TEXT PRIMARY KEY,valor TEXT);
        CREATE TABLE IF NOT EXISTS pagamentos_pix(ref TEXT PRIMARY KEY,uid TEXT,valor REAL,status TEXT DEFAULT 'pendente',tipo TEXT);
        """)
        # Insere planos padrão
        planos=[
            ("basico","🟢 API BÁSICA",29.90,"Sistema de vendas básico: cadastrar/remover produtos, estoque infinito","bot_basico.py","","","",1),
            ("intermediario","🔵 API INTERMEDIÁRIA",59.90,"Tudo do básico + cupons, carrinho completo, relatórios","bot_intermediario.py","","","",1),
            ("vip","🟣 API VIP",99.90,"Tudo do intermediário + depósito/saque Pix para membros, saldo individual","bot_vip.py","","","",1),
            ("premium","🟠 API PREMIUM",199.90,"TUDO + sistema de voz, empréstimos entre membros, mais organizado","bot_premium.py","","","",1),
        ]
        c.executemany("INSERT OR IGNORE INTO planos VALUES(?,?,?,?,?,?,?,?,?)",planos)
        c.commit()
init_db()

# ========== FUNÇÕES AUXILIARES ==========
def cfg(k,d=None):
    r=db().execute("SELECT valor FROM configs WHERE chave=?",(k,)).fetchone()
    return r[0] if r else d
def set_cfg(k,v):
    db().execute("INSERT OR REPLACE INTO configs VALUES(?,?)",(k,v));db().commit()
def gerar_id(tam=12):return ''.join(random.choices(string.ascii_letters+string.digits,k=tam))
def saldo(u):return float(db().execute("SELECT saldo FROM usuarios WHERE uid=?",(str(u),)).fetchone()[0] or 0)
def add_saldo(u,v,n=""):
    db().execute("INSERT OR REPLACE INTO usuarios VALUES(?,?,COALESCE((SELECT saldo FROM usuarios WHERE uid=?),0)+?,COALESCE((SELECT senha_saque FROM usuarios WHERE uid=?),NULL),1)",
        (str(u),n or str(u),str(u),float(v),str(u)));db().commit()
def sub_saldo(u,v):db().execute("UPDATE usuarios SET saldo=saldo-? WHERE uid=?",(float(v),str(u)));db().commit()
def emb(t="",d=""):
    e=Embed(title=t,description=d,color=COR,timestamp=datetime.now())
    e.set_footer(text=f"{EMPRESA} — Tecnologia • APIs • Bots")
    return e

# ========== INICIALIZA BOT ==========
intents=discord.Intents.default();intents.message_content=intents.members=True
bot=discord.Client(intents=intents);tree=app_commands.CommandTree(bot)

# ========== MODAIS ==========
class ModalCadID(Modal,title="🆔 CADASTRAR ID DO DISCORD"):
    idd=TextInput(label="Seu ID do Discord",placeholder="Cole seu ID aqui de 18 dígitos",required=True,min_length=10,max_length=25)
    async def on_submit(self,i):
        if not self.idd.value.isdigit():return await i.response.send_message("❌ ID inválido — só números",ephemeral=True)
        db().execute("INSERT OR REPLACE INTO usuarios VALUES(?,?,COALESCE((SELECT saldo FROM usuarios WHERE uid=?),0),COALESCE((SELECT senha_saque FROM usuarios WHERE uid=?),NULL),1)",
            (str(i.user.id),i.user.display_name,str(i.user.id),str(i.user.id)));db().commit()
        set_cfg(f"id_cadastrado_{i.user.id}",self.idd.value)
        await i.response.send_message("✅ ID CADASTRADO COM SUCESSO!\n\nAgora você pode resgatar seu BOT normalmente.",ephemeral=True)

class ModalSenha(Modal,title="🔐 CRIAR SENHA DE SAQUE (6 DÍGITOS)"):
    s1=TextInput(label="Senha (6 números)",max_length=6,min_length=6,required=True)
    s2=TextInput(label="Repita a senha",max_length=6,min_length=6,required=True)
    async def on_submit(self,i):
        if self.s1.value!=self.s2.value:return await i.response.send_message("❌ Senhas não conferem",ephemeral=True)
        if not self.s1.value.isdigit():return await i.response.send_message("❌ Apenas números",ephemeral=True)
        fracas=["123456","000000","111111","222222","333333","444444","555555","666666","777777","888888","999999","121212","123123","654321"]
        if self.s1.value in fracas:return await i.response.send_message("❌ Senha muito fraca — crie uma melhor",ephemeral=True)
        db().execute("UPDATE usuarios SET senha_saque=? WHERE uid=?",(self.s1.value,str(i.user.id)));db().commit()
        await i.response.send_message("✅ SENHA CRIADA!\n\nAgora você pode sacar normalmente.",ephemeral=True)

# ========== VIEWS / BOTÕES ==========
class ViewEntrega(View):
    def __init__(self,lic_id):
        super().__init__(timeout=None);self.lic=lic_id
    @discord.ui.button(label="🔑 RESGATAR BOT",style=ButtonStyle.green)
    async def b_resgatar(self,i,b):
        lic=db().execute("SELECT * FROM licencas WHERE id=?",(self.lic,)).fetchone()
        if not lic:return await i.response.send_message("❌ Licença não encontrada",ephemeral=True)
        if not cfg(f"id_cadastrado_{i.user.id}"):
            msg="""🆔 CADASTRO DO ID DO DISCORD

Olá! 👋

Antes de continuar com o registro do seu BOT, é necessário realizar o cadastro do seu ID do Discord.

Essa etapa é obrigatória e garante que o sistema da MONARCH TECH™ identifique você como o proprietário oficial do BOT.

✅ Por que cadastrar o ID?

- Vincula o BOT à sua conta do Discord.
- Confirma a propriedade do BOT.
- Libera o registro e a ativação do sistema.
- Habilita todas as funcionalidades e recursos disponíveis.
- Aumenta a segurança contra registros não autorizados.

📋 Como continuar

1️⃣ Copie o seu ID do Discord.
2️⃣ Informe o ID no campo de cadastro.
3️⃣ Aguarde a confirmação automática do sistema.
4️⃣ Após a confirmação, registre o seu BOT normalmente.

«⚠️ Importante: Sem o cadastro do ID do Discord, o sistema não permitirá a conclusão do registro do BOT.»

Obrigado por utilizar a MONARCH TECH™.

🚀 MONARCH TECH™ — Tecnologia • APIs • Bots • Soluções Digitais"""
            return await i.response.send_message(embed=emb("🆔 CADASTRO OBRIGATÓRIO",msg),view=View().add_item(Button(label="📝 CADASTRAR ID",style=ButtonStyle.blurple,custom_id=f"cadid_{i.user.id}")),ephemeral=True)
        # Gera link OAuth
        l=db().execute("SELECT * FROM licencas WHERE id=?",(self.lic,)).fetchone()
        url=f"https://discord.com/oauth2/authorize?client_id={l['bot_token'].split('.')[0]}&permissions=8&scope=bot%20applications.commands"
        await i.response.send_message(f"🔑 **RESGATE SEU BOT**\n\nClique abaixo para adicionar no seu servidor:\n\n{url}\n\n✅ Assim que entrar, envio a confirmação automaticamente.",ephemeral=True)
    @discord.ui.button(label="📝 CADASTRAR ID",style=ButtonStyle.blurple)
    async def b_cad(self,i,b):await i.response.send_modal(ModalCadID())
    @discord.ui.button(label="📜 POLÍTICA DE PRIVACIDADE",style=ButtonStyle.gray)
    async def b_pol(self,i,b):
        pol="""🔒 POLÍTICA DE PRIVACIDADE — MONARCH TECH™

Última atualização: 29 de julho de 2026

A MONARCH TECH™ valoriza a privacidade e a segurança dos dados de seus usuários. Esta Política de Privacidade explica como coletamos, utilizamos, armazenamos e protegemos as informações fornecidas durante o uso de nossos Bots, APIs, Painéis Web e demais serviços.

1. Coleta de Informações

Podemos coletar as seguintes informações quando você utiliza nossos serviços:

- ID do Discord.
- Nome de usuário e avatar do Discord.
- Endereço de e-mail (quando necessário).
- Informações de licenças e produtos adquiridos.
- Registros de acesso e atividades do sistema.
- Dados técnicos necessários para o funcionamento dos serviços.

2. Finalidade da Coleta

As informações são utilizadas para:

- Identificar o proprietário do BOT.
- Gerenciar licenças e ativações.
- Garantir a segurança da plataforma.
- Prevenir fraudes e acessos não autorizados.
- Melhorar nossos serviços e recursos.
- Fornecer suporte técnico quando solicitado.

3. Armazenamento dos Dados

Os dados são armazenados em servidores protegidos com medidas de segurança destinadas a reduzir riscos de acesso não autorizado, alteração ou perda de informações.

4. Compartilhamento de Dados

A MONARCH TECH™ não vende informações pessoais dos usuários.

Os dados poderão ser compartilhados apenas quando:

- Houver obrigação legal.
- For necessário para proteger a segurança da plataforma.
- O usuário autorizar expressamente.

5. Segurança

Empregamos medidas técnicas e administrativas para proteger as informações armazenadas. Apesar disso, nenhum sistema é totalmente imune a riscos, e não é possível garantir segurança absoluta.

6. Responsabilidades do Usuário

O usuário é responsável por:

- Manter sua conta do Discord protegida.
- Não compartilhar tokens, senhas ou chaves de acesso.
- Utilizar nossos serviços de acordo com os Termos de Uso.

7. Direitos do Usuário

O usuário poderá solicitar, quando aplicável:

- Acesso aos seus dados cadastrados.
- Correção de informações incorretas.
- Exclusão de dados, quando possível e compatível com obrigações legais ou operacionais.

8. Alterações desta Política

A MONARCH TECH™ poderá atualizar esta Política de Privacidade a qualquer momento. A versão mais recente será disponibilizada em nossos canais oficiais.

9. Contato

Em caso de dúvidas sobre esta Política de Privacidade, entre em contato pelos canais oficiais da MONARCH TECH™.

---

MONARCH TECH™
Tecnologia • APIs • Bots • Soluções Digitais

© 2026 MONARCH TECH™. Todos os direitos reservados."""
        await i.response.send_message(embed=emb("🔒 POLÍTICA DE PRIVACIDADE",pol),ephemeral=True)

class ViewCarrinho(View):
    def __init__(self,uid):
        super().__init__();self.uid=str(uid)
    def calc(self):
        it=json.loads(db().execute("SELECT itens FROM carrinhos WHERE uid=?",(self.uid,)).fetchone()[0] or "[]")
        meses=sum(x['qtd'] for x in it)
        if meses>12:return None,None,None,meses
        total=sum(x['preco']*x['qtd'] for x in it)
        if total>=100:total*=0.95
        # Melhor plano
        ordem={"premium":4,"vip":3,"intermediario":2,"basico":1}
        melhor=max(it,key=lambda x:ordem.get(x['plano'],0))['plano'] if it else None
        return total,meses,melhor,meses
    @discord.ui.select(options=[
        SelectOption(label="🟢 BÁSICA R$29,90/mês",value="basico",description="Sistema de vendas"),
        SelectOption(label="🔵 INTERMEDIÁRIA R$59,90/mês",value="intermediario",description="+ Cupons + Carrinho"),
        SelectOption(label="🟣 VIP R$99,90/mês",value="vip",description="+ Depósito/Saque Pix"),
        SelectOption(label="🟠 PREMIUM R$199,90/mês",value="premium",description="+ Voz + Empréstimos"),
    ])
    async def sel(self,i,s):
        p=db().execute("SELECT * FROM planos WHERE id=?",(s.values[0],)).fetchone()
        it=json.loads(db().execute("SELECT itens FROM carrinhos WHERE uid=?",(self.uid,)).fetchone()[0] or "[]")
        it.append({"plano":p['id'],"nome":p['nome'],"preco":p['preco'],"qtd":1})
        db().execute("INSERT OR REPLACE INTO carrinhos VALUES(?,?)",(self.uid,json.dumps(it)));db().commit()
        t,m,ml,mm=self.calc()
        if mm>12:return await i.response.send_message("❌ LIMITE DE 1 ANO (12 MESES) ATINGIDO\n\nCarrinho cancelado automaticamente.",ephemeral=True)
        await i.response.edit_message(embed=emb(f"🛒 CARRINHO — {m} MÊS(ES)",f"Plano final: **{ml.upper()}**\n\nTotal: **R${t:.2f}**{' (5% OFF aplicado)'if t*1.05>=100 else ''}"),view=self)
    @discord.ui.button(label="➕ +1 MÊS",style=ButtonStyle.green)
    async def b_mais(self,i,b):
        it=json.loads(db().execute("SELECT itens FROM carrinhos WHERE uid=?",(self.uid,)).fetchone()[0] or "[]")
        if not it:return await i.response.send_message("❌ Escolha um plano primeiro",ephemeral=True)
        it[-1]['qtd']+=1
        db().execute("INSERT OR REPLACE INTO carrinhos VALUES(?,?)",(self.uid,json.dumps(it)));db().commit()
        t,m,ml,mm=self.calc()
        if mm>12:return await i.response.send_message("❌ LIMITE DE 1 ANO (12 MESES)",ephemeral=True)
        await i.response.edit_message(embed=emb(f"🛒 CARRINHO — {m} MÊS(ES)",f"Plano: **{ml.upper()}**\nTotal: **R${t:.2f}**"),view=self)
    @discord.ui.button(label="➖ -1 MÊS",style=ButtonStyle.red)
    async def b_menos(self,i,b):
        it=json.loads(db().execute("SELECT itens FROM carrinhos WHERE uid=?",(self.uid,)).fetchone()[0] or "[]")
        if not it:return
        it[-1]['qtd']=max(1,it[-1]['qtd']-1)
        db().execute("INSERT OR REPLACE INTO carrinhos VALUES(?,?)",(self.uid,json.dumps(it)));db().commit()
        t,m,ml,_=self.calc()
        await i.response.edit_message(embed=emb(f"🛒 CARRINHO — {m} MÊS(ES)",f"Plano: **{ml.upper()}**\nTotal: **R${t:.2f}**"),view=self)
    @discord.ui.button(label="💳 PAGAR COM PIX",style=ButtonStyle.blurple)
    async def b_pix(self,i,b):
        t,m,plano,_=self.calc()
        if not t:return await i.response.send_message("❌ Carrinho vazio",ephemeral=True)
        ref=f"PIX-{i.user.id}-{int(datetime.now().timestamp())}"
        db().execute("INSERT INTO pagamentos_pix VALUES(?,?,?,'pendente','compra')",(ref,str(i.user.id),t));db().commit()
        await i.response.send_message(embed=emb(f"💳 PAGAMENTO PIX — R${t:.2f}",f"Plano: **{plano.upper()}** | {m} mês(es)\n\n**PIX:** `{PIX_DONO}`\n**Ref:** `{ref}`\n\n✅ Após o pagamento, seu BOT + API são gerados automaticamente e enviados na DM."),ephemeral=True)
    @discord.ui.button(label="💰 PAGAR COM SALDO",style=ButtonStyle.green)
    async def b_saldo(self,i,b):
        t,m,plano,_=self.calc()
        if not t:return await i.response.send_message("❌ Vazio",ephemeral=True)
        if saldo(i.user.id)<t:return await i.response.send_message(f"❌ Saldo insuficiente (R${saldo(i.user.id):.2f})",ephemeral=True)
        sub_saldo(i.user.id,t)
        add_saldo(ID_DONO,t,"CAIXA")
        lic=await gerar_licenca(i.user,plano,m)
        db().execute("INSERT INTO transacoes VALUES(NULL,?,'COMPRA_SALDO',?,0,?,?,?)",(str(i.user.id),t,datetime.now().isoformat(),f"SALDO-{gerar_id()}",'pago'));db().commit()
        db().execute("DELETE FROM carrinhos WHERE uid=?",(self.uid,));db().commit()
        await enviar_entrega(i.user,lic)
        await i.response.send_message("✅ PAGO COM SALDO! Verifique sua DM.",ephemeral=True)

class ViewRenovar(View):
    def __init__(self,lic):
        super().__init__();self.lic=lic
    @discord.ui.button(label="🔄 RENOVAR LICENÇA",style=ButtonStyle.green)
    async def b_ren(self,i,b):
        l=db().execute("SELECT * FROM licencas WHERE id=?",(self.lic,)).fetchone()
        p=db().execute("SELECT preco FROM planos WHERE id=?",(l['plano'],)).fetchone()
        ref=f"REN-{i.user.id}-{int(datetime.now().timestamp())}"
        db().execute("INSERT INTO pagamentos_pix VALUES(?,?,?,'pendente','renovacao')",(ref,str(i.user.id),p[0]));db().commit()
        await i.response.send_message(embed=emb(f"🔄 RENOVAÇÃO — R${p[0]:.2f}",f"**PIX:** `{PIX_DONO}`\n**Ref:** `{ref}`\n\n✅ Ao pagar, licença +1 mês automaticamente."),ephemeral=True)

# ========== GERA LICENÇA + BOT + API ==========
async def gerar_licenca(user,plano,meses):
    lid=gerar_id();api_key=f"mk-{gerar_id(24)}";bot_tok=f"{gerar_id(18)}.{gerar_id(6)}.{gerar_id(27)}"
    val=(datetime.now()+timedelta(days=30*meses)).isoformat()
    arq=db().execute("SELECT arquivo FROM planos WHERE id=?",(plano,)).fetchone()[0]
    # Copia template (NUNCA ALTERA O ORIGINAL)
    with open(f"templates/{arq}") as f:codigo=f.read()
    codigo=f"# LICENÇA: {lid} | API: {api_key} | DONO: {user.id} | VALIDADE: {val}\n"+codigo
    os.makedirs("api_gerados",exist_ok=True)
    with open(f"api_gerados/bot_{lid}.py","w") as f:f.write(codigo)
    db().execute("INSERT INTO licencas VALUES(?,?,?,?,?,?,?,'ativa',NULL,NULL)",
        (lid,str(user.id),plano,api_key,bot_tok,user.id,val));db().commit()
    return lid

async def enviar_entrega(user,lid):
    l=db().execute("SELECT * FROM licencas WHERE id=?",(lid,)).fetchone()
    p=db().execute("SELECT * FROM planos WHERE id=?",(l['plano'],)).fetchone()
    val=l['validade'][:10]
    msg=f"""🤖 {EMPRESA} • NOTIFICAÇÃO OFICIAL DO SISTEMA

Olá! 👋

Temos o prazer de informar que o processo de criação foi concluído com sucesso.

✅ Seu BOT foi gerado.
✅ Sua API foi configurada.
✅ Todos os arquivos essenciais já estão preparados para utilização.

📦 Logo abaixo desta mensagem você encontrará o seu BOT.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ ETAPA OBRIGATÓRIA

Antes de registrar o BOT, é necessário cadastrar o seu ID do Discord.

Esse procedimento é obrigatório e faz parte do sistema de segurança da {EMPRESA}.

Ao cadastrar seu ID, nossa plataforma poderá:

🔹 Reconhecer você como proprietário oficial do BOT.
🔹 Vincular permanentemente a licença ao seu Discord.
🔹 Liberar todos os recursos e funcionalidades exclusivas.
🔹 Impedir que terceiros registrem ou utilizem o seu BOT sem autorização.
🔹 Garantir maior segurança e autenticidade durante o uso da plataforma.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 COMO CONTINUAR

1️⃣ Cadastre o seu ID do Discord.
2️⃣ Aguarde a confirmação automática do sistema.
3️⃣ Registre o seu BOT normalmente.
4️⃣ Comece a utilizar todas as funcionalidades disponíveis.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📢 IMPORTANTE

O registro do BOT somente poderá ser concluído após a confirmação do ID do Discord.

Caso tente registrar o BOT sem realizar essa etapa, o sistema poderá bloquear temporariamente o processo até que a verificação seja concluída.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📦 DADOS DA SUA LICENÇA

🆔 Licença: `{lid}`
🔑 API Key: `{l['api_key']}`
🤖 Token do BOT: `{l['bot_token']}`
📅 Validade: **{val}**
📦 Plano: **{p['nome']}**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

STATUS DO SISTEMA

🟢 BOT: Criado com sucesso.
🟢 API: Ativada.
🟢 Arquivos: Prontos.
🟡 Registro: Aguardando cadastro do ID do Discord.

Obrigado por escolher a {EMPRESA}.

Agradecemos a sua confiança em nossa plataforma e desejamos uma excelente experiência com nossos sistemas e soluções tecnológicas.

🚀 {EMPRESA} — Tecnologia, APIs, Bots e Soluções Digitais."""
    await user.send(embed=emb("✅ SEU NOVO BOT ESTÁ PRONTO!",msg),view=ViewEntrega(lid))

# ========== EVENTOS ==========
@bot.event
async def on_guild_join(g):
    # Verifica se é um bot nosso que entrou
    for l in db().execute("SELECT * FROM licencas WHERE bot_token LIKE ?",(f"{g.me.id}%",)).fetchall():
        db().execute("UPDATE licencas SET servidor_id=?,servidor_nome=? WHERE id=?",(g.id,g.name,l['id']));db().commit()
        dono=bot.get_user(l['dono_bot']) or await bot.fetch_user(l['dono_bot'])
        msg=f"""✅ BOT ATIVADO COM SUCESSO!

Olá! 👋

Temos uma ótima notícia!

Seu BOT foi adicionado ao servidor e já está online e em pleno funcionamento.

🎉 O processo de implantação foi concluído com sucesso.

📋 Status da Implantação

🟢 BOT conectado ao servidor.
🟢 Sistema inicializado com sucesso.
🟢 Comandos carregados.
🟢 Recursos ativados.
🟢 API conectada e operacional.
🟢 BOT pronto para uso.

Agora você já pode utilizar todas as funcionalidades disponíveis e começar a configurar o BOT de acordo com as necessidades do seu servidor.

---

💙 Obrigado por escolher a {EMPRESA}

Agradecemos pela confiança em nossa plataforma.

Nosso objetivo é oferecer Bots modernos, seguros, rápidos e com alta disponibilidade para proporcionar a melhor experiência possível.

Esperamos que seu BOT contribua para o crescimento e a organização da sua comunidade.

---

📢 Importante

Caso adicione novos módulos ou altere configurações, algumas funções poderão ser atualizadas automaticamente pelo sistema para garantir o melhor desempenho.

---

STATUS FINAL

✅ BOT: Online
✅ Servidor: **{g.name}**
✅ API: Operacional
✅ Comandos: Ativos
✅ Sistema: Funcionando normalmente

🚀 Seu BOT já está pronto para uso. Desejamos uma excelente experiência com a {EMPRESA}!"""
        await dono.send(embed=emb("✅ BOT ATIVADO NO SEU SERVIDOR",msg))

@bot.event
async def on_ready():
    await tree.sync(guild=discord.Object(id=GUILD))
    print(f"👑 BOT API ONLINE — {bot.user}")
    # Loop de verificação de licenças
    bot.loop.create_task(loop_licencas())

async def loop_licencas():
    while True:
        agora=datetime.now().isoformat()
        for l in db().execute("SELECT * FROM licencas WHERE status='ativa' AND validade<?",(agora,)).fetchall():
            db().execute("UPDATE licencas SET status='expirada' WHERE id=?",(l['id'],));db().commit()
            dono=bot.get_user(l['dono_bot']) or await bot.fetch_user(l['dono_bot'])
            msg=f"""⚠️ LICENÇA EXPIRADA

Olá! 👋

Informamos que a licença do seu BOT expirou.

Devido ao término da validade, o BOT foi desativado automaticamente e não poderá ser utilizado até que a licença seja renovada.

📋 Status do Sistema

🔴 Licença: Expirada
🔴 BOT: Offline
🔴 API: Desativada
🔴 Serviços: Suspensos

❗ O que aconteceu?

Assim que a validade da licença é encerrada, o sistema da {EMPRESA} desativa automaticamente o BOT para proteger a integridade da licença e garantir que apenas assinaturas ativas utilizem os serviços.

🔄 Como reativar

Para voltar a utilizar o seu BOT, basta realizar a renovação da licença.

Após a confirmação da renovação, o sistema irá automaticamente:

✅ Reativar a licença.
✅ Colocar o BOT novamente online.
✅ Restaurar todas as funcionalidades.
✅ Reativar a API e os serviços vinculados.
✅ Permitir que o BOT volte a operar normalmente no seu servidor.

«⚠️ Importante: Enquanto a licença permanecer expirada, o BOT continuará offline e todas as suas funcionalidades permanecerão indisponíveis.»

Agradecemos por utilizar os serviços da {EMPRESA}.

🚀 {EMPRESA} — Tecnologia • APIs • Bots • Soluções Digitais"""
            await dono.send(embed=emb("⚠️ LICENÇA EXPIRADA",msg),view=ViewRenovar(l['id']))
        await asyncio.sleep(3600)

# ========== COMANDOS ==========
@tree.command(name="gapi",description="🛒 MONTA LOJA DE APIs AUTOMATICAMENTE",guild=discord.Object(id=GUILD))
async def gapi(i):
    if i.user.id!=ID_DONO:return await i.response.send_message("❌ Apenas dono",ephemeral=True)
    v=ViewCarrinho(i.user.id)
    await i.channel.send(embed=emb("🏪 LOJA OFICIAL DE APIs","Escolha seu plano abaixo, adicione meses e pague com Pix ou Saldo!\n\n💎 Acima de R$100 ganha **5% OFF**\n📅 Máximo 12 meses (1 ano)"),view=v)
    await i.response.send_message("✅ LOJA CRIADA COM SUCESSO!",ephemeral=True)

@tree.command(name="configurar_api",description="⚙️ ADMIN: Configurar chaves do sistema",guild=discord.Object(id=GUILD))
@app_commands.describe(chave_pix="Sua chave Pix",asaas_key="Chave Asaas")
async def cfg_api(i,chave_pix:str,asaas_key:str):
    if i.user.id!=ID_DONO:return
    set_cfg("PIX_DONO",chave_pix);set_cfg("ASAAS_KEY",asaas_key)
    global PIX_DONO;PIX_DONO=chave_pix
    await i.response.send_message("✅ SISTEMA CONFIGURADO!\n\nPagamentos automáticos ativados.",ephemeral=True)

@tree.command(name="confirmar_pagamento",description="✅ ADMIN: Confirma pagamento Pix",guild=discord.Object(id=GUILD))
@app_commands.describe(ref="Referência do pagamento")
async def conf_pag(i,ref:str):
    if i.user.id!=ID_DONO:return
    pg=db().execute("SELECT * FROM pagamentos_pix WHERE ref=?",(ref,)).fetchone()
    if not pg:return await i.response.send_message("❌ Não encontrado",ephemeral=True)
    db().execute("UPDATE pagamentos_pix SET status='pago' WHERE ref=?",(ref,));db().commit()
    user=bot.get_user(int(pg['uid'])) or await bot.fetch_user(int(pg['uid']))
    if pg['tipo']=='compra':
        it=json.loads(db().execute("SELECT itens FROM carrinhos WHERE uid=?",(pg['uid'],)).fetchone()[0] or "[]")
        meses=sum(x['qtd'] for x in it)
        ordem={"premium":4,"vip":3,"intermediario":2,"basico":1}
        plano=max(it,key=lambda x:ordem.get(x['plano'],0))['plano']
        lid=await gerar_licenca(user,plano,meses)
        db().execute("DELETE FROM carrinhos WHERE uid=?",(pg['uid'],));db().commit()
        await enviar_entrega(user,lid)
    elif pg['tipo']=='renovacao':
        l=db().execute("SELECT * FROM licencas WHERE uid=? ORDER BY rowid DESC LIMIT 1",(pg['uid'],)).fetchone()
        nv=(datetime.fromisoformat(l['validade'])+timedelta(days=30)).isoformat()
        db().execute("UPDATE licencas SET validade=?,status='ativa' WHERE id=?",(nv,l['id']));db().commit()
        await user.send(embed=emb("✅ LICENÇA RENOVADA!",f"+30 dias | Nova validade: {nv[:10]}"))
    elif pg['tipo']=='deposito':
        add_saldo(int(pg['uid']),pg['valor'],user.display_name)
        await user.send(embed=emb("💰 DEPÓSITO CONFIRMADO",f"R${pg['valor']:.2f} adicionado ao seu saldo!"))
    add_saldo(ID_DONO,pg['valor'],"CAIXA")
    await i.response.send_message(f"✅ PAGAMENTO CONFIRMADO\n\nRef: `{ref}`\nValor: R${pg['valor']:.2f}",ephemeral=True)

@tree.command(name="saldo",description="💰 Ver seu saldo",guild=discord.Object(id=GUILD))
async def cmd_saldo(i):
    await i.response.send_message(f"💰 **Seu saldo:** R${saldo(i.user.id):.2f}",ephemeral=True)

@tree.command(name="depositar",description="💰 Gerar Pix para depositar no saldo",guild=discord.Object(id=GUILD))
@app_commands.describe(valor="Valor entre R$5 e R$2500")
async def cmd_dep(i,valor:float):
    if valor<5 or valor>2500:return await i.response.send_message("❌ Min R$5 / Máx R$2500",ephemeral=True)
    ref=f"DEP-{i.user.id}-{int(datetime.now().timestamp())}"
    db().execute("INSERT INTO pagamentos_pix VALUES(?,?,?,'pendente','deposito')",(ref,str(i.user.id),valor));db().commit()
    await i.response.send_message(embed=emb(f"💰 DEPÓSITO — R${valor:.2f}",f"**PIX:** `{PIX_DONO}`\n**Ref:** `{ref}`\n\n✅ Ao pagar, saldo cai automaticamente."),ephemeral=True)

@tree.command(name="criar_senha_saque",description="🔐 Cria senha de 6 dígitos para sacar",guild=discord.Object(id=GUILD))
async def cmd_senha(i):await i.response.send_modal(ModalSenha())

@tree.command(name="sacar",description="💸 Sacar saldo via Pix",guild=discord.Object(id=GUILD))
@app_commands.describe(valor="R$5 até R$2500",chave_pix="Sua chave Pix",nome_conta="Nome da conta",senha="Sua senha de 6 dígitos")
async def cmd_sacar(i,valor:float,chave_pix:str,nome_conta:str,senha:str):
    if valor<5 or valor>2500:return await i.response.send_message("❌ Min R$5 / Máx R$2500",ephemeral=True)
    us=db().execute("SELECT * FROM usuarios WHERE uid=?",(str(i.user.id),)).fetchone()
    if not us or not us['senha_saque']:return await i.response.send_message("❌ Crie uma senha primeiro: /criar_senha_saque",ephemeral=True)
    if us['senha_saque']!=senha:return await i.response.send_message("❌ Senha incorreta",ephemeral=True)
    taxa=round(valor*0.15,2);liquido=round(valor-taxa,2)
    if saldo(i.user.id)<valor:return await i.response.send_message(f"❌ Saldo insuficiente (R${saldo(i.user.id):.2f})",ephemeral=True)
    sub_saldo(i.user.id,valor)
    ref=f"SAQ-{i.user.id}-{int(datetime.now().timestamp())}"
    db().execute("INSERT INTO transacoes VALUES(NULL,?,'SAQUE',?,?,?,?,?)",(str(i.user.id),liquido,taxa,datetime.now().isoformat(),ref,'processando'));db().commit()
    await i.response.send_message(embed=emb("💸 SAQUE SOLICITADO",f"""
Valor bruto: R${valor:.2f}
Taxa 15%: R${taxa:.2f}
✅ Você recebe: **R${liquido:.2f}**

Pix: `{chave_pix}`
Nome: `{nome_conta}`
Ref: `{ref}`

⏳ Processando — cai em até 24h."""),ephemeral=True)
    # Avisa dono
    dono=bot.get_user(ID_DONO)
    await dono.send(f"💸 NOVO SAQUE\n\nDe: {i.user.mention}\nValor: R${liquido:.2f}\nPix: `{chave_pix}`\nNome: {nome_conta}\nRef: `{ref}`")

bot.run(TOKEN)
