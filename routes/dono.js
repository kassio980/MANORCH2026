const express = require('express');
const router = express.Router();
const db = require('../db');
const crypto = require('crypto');

router.use((req, res, next) => {
  if(!req.session.user || req.session.user.is_dono!==1) return res.redirect('/login?erro=403');
  next();
});

router.get('/', (req, res) => {
  res.render('premium/dono-dashboard', {
    titulo: '👑 Visão Geral',
    receita: db.totalReceita(),
    vendas: db.totalVendas(),
    clientes: db.totalUsuarios(),
    botsOn: db.botsOnline(),
    saquesPend: db.saquesPendentes(),
    cresc: +(Math.random()*12+10).toFixed(1),
    ultimas: db.ultimasAtividades(10)
  });
});

router.get('/clientes', (req,res)=>res.render('premium/dono-clientes',{titulo:'👥 Clientes'}));
router.get('/planos', (req,res)=>res.render('premium/dono-planos',{titulo:'📦 Planos'}));
router.get('/apis', (req,res)=>res.render('premium/dono-apis',{titulo:'🔑 APIs'}));
router.get('/bots', (req,res)=>res.render('premium/dono-bots',{titulo:'🤖 Bots'}));
router.get('/licencas', (req,res)=>res.render('premium/dono-licencas',{titulo:'📜 Licenças'}));
router.get('/hosting', (req,res)=>res.render('premium/dono-hosting',{titulo:'☁️ Hosting'}));
router.get('/saques', (req,res)=>res.render('premium/dono-saques',{titulo:'💸 Saques Pendentes'}));
router.get('/seguranca', (req,res)=>res.render('premium/dono-seguranca',{titulo:'🛡️ Security Center', score:98}));
router.get('/analytics', (req,res)=>res.render('premium/dono-analytics',{titulo:'📊 Analytics'}));
router.get('/suporte', (req,res)=>res.render('premium/dono-suporte',{titulo:'🎫 Suporte'}));
router.get('/configuracoes', (req,res)=>res.render('premium/dono-config',{titulo:'⚙️ Configurações'}));

router.post('/gerar-api', (req, res) => {
  const {usuarioId, plano, dias} = req.body;
  const id = `MNC-${crypto.randomInt(100000,999999)}`;
  const chave = `mnc_live_${crypto.randomBytes(16).toString('hex')}`;
  const validade = new Date(Date.now()+dias*86400000).toISOString();
  db.criarLicenca({id, usuario_id:usuarioId, plano, chave_api:chave, validade});
  db.log(req.session.user.username, `GERAR_API ${id}`, req.ip);
  res.json({ok:true, licenca:id, chave, validade});
});
module.exports = router;
