const express = require('express');
const router = express.Router();
const db = require('../db');

// HOME PRINCIPAL
router.get('/', (req, res) => res.render('home', { titulo: '𝐌𝐎𝐍𝐀𝐑𝐂𝐇𝟐𝟎𝟐𝟔© — OFICIAL' }));

// LOGIN
router.get('/login', (req, res) => {
  if (req.session.user) return res.redirect(req.session.user.is_dono ? '/dono' : '/painel');
  res.render('login', { titulo: 'Entrar — MONARCH2026©' });
});

// VERIFICAR LICENÇA
router.get('/verificar', (req, res) => res.render('verificar', { licenca: null }));
router.post('/verificar', (req, res) => {
  const l = db.getLicencaPorId(req.body.id.toUpperCase());
  res.render('verificar', { licenca: l || { invalida: true, id: req.body.id } });
});

// DOCS E STATUS
router.get('/docs', (req, res) => res.render('docs'));
router.get('/status', (req, res) => res.render('status'));

module.exports = router;
