const express = require('express');
const router = express.Router();
const db = require('../db');
const crypto = require('crypto');

router.use((req,res,next)=>{ if(!req.session.user) return res.redirect('/login'); next(); });

// Home = Loja + SEU saldo de dono de bot
router.get('/', (req, res) => {
  const uid = req.session.user.id;
  res.render('loja/cliente-loja', {
    titulo:'🏠 MONARCH STORE',
    prods: db.db.prepare('SELECT * FROM produtos WHERE ativo=1 ORDER BY ordem').all(),
    minha_carteira: db.minhaCarteiraBot(uid) || {saldo:0},
    minhas_licencas: db.minhasLicencas(uid),
    cfg: db.cfg()
  });
});

// ========== COMPRAR PRODUTO (regras de dinheiro automáticas) ==========
router.post('/comprar/:produtoId', (req, res) => {
  const uid = req.session.user.id;
  const prod = db.db.prepare('SELECT * FROM produtos WHERE id=? AND ativo=1').get(req.params.produtoId);
  if(!prod) return res.redirect('/painel?erro=produto');
  const cart = db.minhaCarteiraBot(uid) || {saldo:0};

  // 1. Venda do produto → 100% vai pra VOCÊ (dono plataforma), SEM TAXA
  if(cart.saldo < prod.preco) return res.redirect('/painel?erro=saldo');
  db.db.prepare('UPDATE carteira_dono_bot SET saldo=saldo-? WHERE usuario_id=?').run(prod.preco, uid);
  db.movimentar({
    tipo:'VENDA_PRODUTO', usuario_id:uid, valor:prod.preco, taxa_pct:0,
    destinatario:'PLATAFORMA', referencia:prod.id,
    descricao:`${req.session.user.username} comprou ${prod.nome}`
  });

  // 2. Cria licença + BOT JÁ INTEGRADO com a API comprada
  const lid = `MNC-${crypto.randomInt(100000,999999)}`;
  const chave = `mnc_live_${crypto.randomBytes(16).toString('hex')}`;
  db.criarLicenca({id:lid, usuario_id:uid, produto_id:prod.id, chave_api:chave, validade:new Date(Date.now()+prod.dias_validade*86400000).toISOString()});
  const botId = db.db.prepare('INSERT INTO bots (licenca_id,usuario_id,nome_bot,descricao) VALUES (?,?,?,?)')
    .run(lid, uid, `MONARCH ${prod.tipo_bot}`, prod.descricao||'').lastInsertRowid;

  // 3. Convite do bot automático
  const invite = `https://discord.com/api/oauth2/authorize?client_id=SEU_CLIENT_ID&permissions=8&scope=bot%20applications.commands&guild_id=`;
  db.db.prepare('UPDATE bots SET invite_link=? WHERE id=?').run(invite, botId);
  res.redirect(`/painel/meu-bot/${botId}?nova=1`);
});

// ========== MEU BOT (configura nome, banner, logo, descrição, convidar pro servidor) ==========
router.get('/meu-bot/:id', (req, res) => {
  const uid = req.session.user.id;
  const bot = db.db.prepare('SELECT b.*,l.chave_api,l.status,p.tipo_bot,p.nivel_api,p.tem_carteira_interna FROM bots b JOIN licencas l ON l.id=b.licenca_id JOIN produtos p ON p.id=l.produto_id WHERE b.id=? AND b.usuario_id=?').get(+req.params.id, uid);
  if(!bot) return res.redirect('/painel/api');
  res.render('loja/cliente-bot', {titulo:`🤖 ${bot.nome_bot}`, bot});
});
router.post('/meu-bot/:id/salvar', (req, res) => {
  const b = req.body;
  db.db.prepare('UPDATE bots SET nome_bot=?,banner=?,logo=?,descricao=?,token_discord=? WHERE id=? AND usuario_id=?')
    .run(b.nome_bot,b.banner||'',b.logo||'',b.descricao||'',b.token_discord||'',+req.params.id,req.session.user.id);
  res.redirect('back');
});

// ========== CARTEIRA DO DONO DE BOT (recebe vendas dos membros no bot dele) ==========
router.get('/carteira', (req, res) => res.render('loja/cliente-carteira', {
  titulo:'💰 Minha Carteira de Bot',
  c: db.minhaCarteiraBot(req.session.user.id)||{saldo:0}, cfg: db.cfg()
}));
router.post('/carteira/depositar', (req, res) => {
  const v=+req.body.valor, uid=req.session.user.id;
  db.db.prepare('UPDATE carteira_dono_bot SET saldo=saldo+? WHERE usuario_id=?').run(v, uid);
  res.redirect('/painel/carteira');
});
// ✅ SAQUE DONO DE BOT: COBRA TAXA 15% QUE VAI PRA VOCÊ
router.post('/carteira/sacar', (req, res) => {
  const v=+req.body.valor, uid=req.session.user.id, cfg=db.cfg();
  const cart = db.minhaCarteiraBot(uid);
  if(v<cfg.saque_min||v>cfg.saque_max) return res.redirect('/painel/carteira?erro=limite');
  if(!cart || cart.saldo<v) return res.redirect('/painel/carteira?erro=saldo');
  // Aplica regra: desconta do cliente, 15% vai pra plataforma, resto recebe
  db.db.prepare('UPDATE carteira_dono_bot SET saldo=saldo-?,sacado=sacado+? WHERE usuario_id=?').run(v, +(v*(1-cfg.taxa_saque_membros/100)).toFixed(2), uid);
  db.movimentar({
    tipo:'SAQUE_DONO_BOT', usuario_id:uid, valor:v, taxa_pct:cfg.taxa_saque_membros,
    destinatario:`DONO_BOT:${uid}`, descricao:`Saque dono bot - taxa ${cfg.taxa_saque_membros}% MONARCH`
  });
  res.redirect('/painel/carteira?ok=1');
});

// ========== ENDPOINTS INTERNOS DO BOT (carteira dos membros) ==========
// ✅ REGRA: DONO DO BOT NUNCA MECHE NO SALDO DO MEMBRO — só o sistema
router.post('/bot/:botId/membro/:discordId/depositar', (req, res) => {
  const {valor} = req.body;
  const bot = db.db.prepare('SELECT * FROM bots WHERE id=?').get(+req.params.botId);
  if(!bot) return res.json({ok:false,erro:'bot'});
  // Membro deposita → aumenta saldo DELE APENAS
  db.db.prepare('INSERT INTO carteira_membro (bot_id,discord_usuario_id,nome,saldo) VALUES (?,?,?,?) ON CONFLICT DO UPDATE SET saldo=saldo+excluded.saldo')
    .run(bot.id, req.params.discordId, req.body.nome||'Membro', +valor);
  res.json({ok:true});
});
// Membro compra algo NO BOT → desconta DELE, líquido vai pro DONO DO BOT, 15% pra VOCÊ
router.post('/bot/:botId/membro/:discordId/comprar', (req, res) => {
  const {valor, descricao} = req.body;
  const bot = db.db.prepare('SELECT * FROM bots WHERE id=?').get(+req.params.botId);
  const m = db.carteiraMembro(bot.id, req.params.discordId);
  if(!m || m.saldo < +valor) return res.json({ok:false,erro:'saldo'});
  // 1. Desconta do membro
  db.db.prepare('UPDATE carteira_membro SET saldo=saldo-? WHERE id=?').run(+valor, m.id);
  // 2. Aplica regra: 15% pra VOCÊ, resto pro dono do bot
  db.movimentar({
    tipo:'VENDA_BOT_INTERNO', bot_id:bot.id, valor:+valor,
    destinatario:`DONO_BOT:${bot.usuario_id}`, referencia:`BOT-${bot.id}`,
    descricao: descricao||'Compra interna no bot'
  });
  res.json({ok:true});
});

// Outros
router.get('/api', (req,res)=>res.render('loja/cliente-api',{titulo:'🔑 Minhas APIs', l:db.minhasLicencas(req.session.user.id)}));
router.get('/plano', (req,res)=>res.render('loja/cliente-plano',{titulo:'📅 Meus Planos', l:db.minhasLicencas(req.session.user.id)}));
router.get('/config', (req,res)=>res.render('loja/cliente-config',{titulo:'⚙️ Minhas Configs', u:db.db.prepare('SELECT * FROM usuarios WHERE id=?').get(req.session.user.id)}));
router.post('/config/salvar-asaas', (req,res)=>{db.db.prepare('UPDATE usuarios SET chave_asaas=? WHERE id=?').run(req.body.chave_asaas||'',req.session.user.id);res.redirect('back');});
router.get('/perfil', (req,res)=>res.render('loja/cliente-perfil',{titulo:'👤 Meu Perfil'}));
router.get('/produtos', (req,res)=>res.redirect('/painel'));
module.exports = router;
