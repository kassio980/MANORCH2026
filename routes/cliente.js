const express = require('express');
const router = express.Router();
const db = require('../db');

// BLOQUEIO: SÓ USUÁRIO LOGADO
router.use((req, res, next) => {
  if (!req.session.user) return res.redirect('/login');
  next();
});

router.get('/', (req, res) => {
  const minhas = db.prepare('SELECT * FROM licencas WHERE usuario_id = ?').all(req.session.user.id);
  res.render('painel-cliente', {
    titulo: '👤 MEU PAINEL — MONARCH2026©',
    licencas: minhas
  });
});

router.get('/carteira', (req, res) => res.render('carteira'));
router.get('/bot', (req, res) => res.render('gerenciar-bot'));
router.get('/loja', (req, res) => res.render('minha-loja'));

module.exports = router;
