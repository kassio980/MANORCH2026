const express = require('express');
const router = express.Router();
const db = require('../db');

router.get('/', (req, res) => res.render('home', {titulo:'𝐌𝐎𝐍𝐀𝐑𝐂𝐇𝟐𝟎𝟐𝟔© — PLATAFORMA OFICIAL'}));
router.get('/login', (req, res) => {
  if(req.session.user) return res.redirect(req.session.user.is_dono?'/dono':'/painel');
  res.render('login', {titulo:'Entrar — MONARCH2026©'});
});
router.get('/status', (req, res) => res.render('status', {titulo:'Status da Plataforma'}));
router.get('/docs', (req, res) => res.render('docs', {titulo:'Documentação'}));
router.get('/verificar', (req, res) => res.render('verificar', {licenca:null}));
router.post('/verificar', (req, res) => {
  const l = db.getLicencaPorId((req.body.id||'').toUpperCase());
  res.render('verificar', {licenca: l || {invalida:true, id:req.body.id}});
});
router.get('/tema/:t', (req, res) => { req.session.tema = ['dark','light'].includes(req.params.t)?req.params.t:'dark'; res.redirect('back'); });
router.post('/buscar', (req, res) => res.json(db.buscarGlobal(req.body.q||'')));
module.exports = router;
