const express = require('express');
const router = express.Router();
const db = require('../db');

router.use((req,res,next)=>{ if(!req.session.user) return res.redirect('/login'); next(); });

router.get('/', (req, res) => {
  res.render('premium/cliente-inicio', {
    titulo: '👤 Meu Painel',
    licencas: db.minhasLicencas(req.session.user.id),
    carteira: db.minhaCarteira(req.session.user.id) || {saldo:0,pendente:0,sacado:0,gasto:0},
    notifs: db.minhasNotificacoes(req.session.user.id)
  });
});
router.get('/bot', (req,res)=>res.render('premium/cliente-bot',{titulo:'🤖 Meu Bot'}));
router.get('/loja', (req,res)=>res.render('premium/cliente-loja',{titulo:'🛒 Minha Loja'}));
router.get('/carteira', (req,res)=>res.render('premium/cliente-carteira',{titulo:'💰 Carteira', c: db.minhaCarteira(req.session.user.id)||{saldo:0}}));
router.get('/vip', (req,res)=>res.render('premium/cliente-vip',{titulo:'⭐ VIP'}));
router.get('/api', (req,res)=>res.render('premium/cliente-api',{titulo:'🔑 Minhas APIs', l: db.minhasLicencas(req.session.user.id)}));
router.get('/tickets', (req,res)=>res.render('premium/cliente-tickets',{titulo:'🎫 Suporte'}));
module.exports = router;
