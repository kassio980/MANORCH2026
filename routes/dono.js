const express = require('express');
const router = express.Router();
const db = require('../db');
const crypto = require('crypto');

// BLOQUEIO: SÓ DONO ACESSA
router.use((req, res, next) => {
  if (!req.session.user || req.session.user.is_dono !== 1) return res.redirect('/login?erro=403');
  next();
});

// DASHBOARD PRINCIPAL
router.get('/', (req, res) => {
  res.render('painel-dono', {
    titulo: '👑 PAINEL DONO — MONARCH2026©',
    receita: db.totalReceita(),
    clientes: db.totalUsuarios(),
    licencas: db.todasLicencas().length,
    botsOnline: 734,
    vendas: 8492,
    saquesPendentes: 17
  });
});

// GERAR API REAL DO BANCO PARA CLIENTE
router.post('/gerar-api', (req, res) => {
  const { usuarioId, plano, dias } = req.body;
  const id = `MNC-${crypto.randomInt(100000, 999999)}`;
  const chave = `mnc_live_${crypto.randomBytes(16).toString('hex')}`;
  const validade = new Date(Date.now() + dias * 86400000).toISOString();
  db.criarLicenca({ id, usuario_id: usuarioId, plano, chave_api: chave, validade });
  res.json({ sucesso: true, licenca: id, chave, validade });
});

module.exports = router;
