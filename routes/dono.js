const express = require('express');
const router = express.Router();
const db = require('../db');
const crypto = require('crypto');

router.use((req, res, next) => {
  if(!req.session.user || req.session.user.is_dono_plataforma!==1) return res.redirect('/login?erro=403');
  next();
});

// Dashboard com SEU saldo da plataforma
router.get('/', (req, res) => {
  const p = db.plat();
  res.render('premium/dono-dashboard', {
    titulo:'👑 Painel Dono MONARCH',
    seu_saldo: p.saldo, total_taxas: p.total_taxas, total_vendas: p.total_vendas,
    clientes: db.totalUsuarios(), botsOn: db.botsOnline(), saquesPend: db.saquesPendentes(),
    ultimas: db.ultimasAtividades(12)
  });
});

// ========== CRUD PRODUTOS (você cadastra tudo aqui) ==========
router.get('/produtos', (req, res) => res.render('loja/dono-produtos', {
  titulo:'📦 Cadastrar / Editar Produtos',
  prods: db.db.prepare('SELECT * FROM produtos ORDER BY ordem').all()
}));
router.post('/produtos/salvar', (req, res) => {
  const b = req.body;
  db.db.prepare(`INSERT INTO produtos (id,nome,tipo_bot,nivel_api,preco,dias_validade,badge,cor,descricao,banner,logo,tem_carteira_interna,ordem,ativo)
    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,1)
    ON CONFLICT(id) DO UPDATE SET nome=excluded.nome,tipo_bot=excluded.tipo_bot,nivel_api=excluded.nivel_api,
    preco=excluded.preco,dias_validade=excluded.dias_validade,badge=excluded.badge,cor=excluded.cor,
    descricao=excluded.descricao,banner=excluded.banner,logo=excluded.logo,tem_carteira_interna=excluded.tem_carteira_interna,ordem=excluded.ordem`)
    .run(
      b.id.toUpperCase(), b.nome, b.tipo_bot.toUpperCase(), b.nivel_api.toUpperCase(),
      +b.preco, +b.dias_validade, b.badge?.toUpperCase()||'', b.cor||'roxo',
      b.descricao||'', b.banner||'', b.logo||'',
      // ✅ REGRA: Intermediário pra cima JÁ VEM com carteira interna automática
      ['INTERMEDIARIO','VIP','PREMIUM'].includes(b.tipo_bot.toUpperCase()) ? 1 : (b.tem_carteira_interna?1:0),
      +b.ordem||0
    );
  res.redirect('/dono/produtos');
});
router.get('/produtos/:id/off', (req, res) => {
  db.db.prepare('UPDATE produtos SET ativo=0 WHERE id=?').run(req.params.id);
  res.redirect('/dono/produtos');
});

// ========== CONFIG PLATAFORMA (sua chave Asaas + taxa 15% + limites) ==========
router.get('/config', (req, res) => res.render('loja/dono-config', {
  titulo:'⚙️ Configurações da Plataforma',
  c: db.cfg(), sua_carteira: db.plat()
}));
router.post('/config', (req, res) => {
  const b = req.body;
  db.db.prepare(`UPDATE config_plataforma SET taxa_saque_membros=?,saque_min=?,saque_max=?,deposito_min=?,deposito_max=?,chave_asaas_dono=? WHERE id=1`)
    .run(+b.taxa_saque_membros,+b.saque_min,+b.saque_max,+b.deposito_min,+b.deposito_max,b.chave_asaas_dono||'');
  res.redirect('/dono/config');
});

// ========== SUA CARTEIRA (DEPOSITA / SACA SEM TAXA NENHUMA) ==========
router.get('/carteira', (req, res) => res.render('loja/dono-carteira', {
  titulo:'💰 Minha Carteira (SEM TAXA)',
  c: db.plat(), cfg: db.cfg()
}));
router.post('/carteira/depositar', (req, res) => {
  const v = +req.body.valor;
  db.db.prepare('UPDATE carteira_plataforma SET saldo=saldo+? WHERE id=1').run(v);
  db.db.prepare('INSERT INTO transacoes (tipo,valor,liquido,destinatario,descricao) VALUES (?,?,?,?,?)')
    .run('DEPOSITO_DONO',v,v,'PLATAFORMA','Depósito dono plataforma SEM TAXA');
  res.redirect('/dono/carteira');
});
router.post('/carteira/sacar', (req, res) => {
  const v = +req.body.valor;
  const p = db.plat();
  if(v > p.saldo) return res.redirect('/dono/carteira?erro=saldo');
  db.db.prepare('UPDATE carteira_plataforma SET saldo=saldo-?,total_sacado=total_sacado+? WHERE id=1').run(v,v);
  db.db.prepare('INSERT INTO transacoes (tipo,valor,taxa,liquido,destinatario,descricao) VALUES (?,?,?,?,?,?)')
    .run('SAQUE_DONO',v,0,v,'PLATAFORMA','Saque dono plataforma SEM TAXA');
  res.redirect('/dono/carteira?ok=1');
});

// Outros
router.get('/clientes', (req,res)=>res.render('premium/dono-clientes',{titulo:'👥 Clientes'}));
router.get('/bots', (req,res)=>res.render('premium/dono-bots',{titulo:'🤖 Bots da Plataforma'}));
router.get('/licencas', (req,res)=>res.render('premium/dono-licencas',{titulo:'📜 Licenças'}));
router.get('/saques', (req,res)=>res.render('premium/dono-saques',{titulo:'💸 Saques Pendentes'}));
router.get('/seguranca', (req,res)=>res.render('premium/dono-seguranca',{titulo:'🛡️ Security Center',score:98}));
router.get('/analytics', (req,res)=>res.render('premium/dono-analytics',{titulo:'📊 Analytics'}));

// Gerar licença manual
router.post('/gerar-licenca', (req, res) => {
  const {usuarioId, produtoId} = req.body;
  const prod = db.db.prepare('SELECT * FROM produtos WHERE id=?').get(produtoId);
  const id = `MNC-${crypto.randomInt(100000,999999)}`;
  const chave = `mnc_live_${crypto.randomBytes(16).toString('hex')}`;
  db.criarLicenca({id, usuario_id:+usuarioId, produto_id:produtoId, chave_api:chave, validade:new Date(Date.now()+prod.dias_validade*86400000).toISOString()});
  // Cria bot automaticamente integrado com a licença
  db.db.prepare('INSERT INTO bots (licenca_id,usuario_id,nome_bot) VALUES (?,?,?)').run(id, +usuarioId, `MONARCH ${prod.tipo_bot}`);
  res.json({ok:true, licenca:id, chave});
});
module.exports = router;
