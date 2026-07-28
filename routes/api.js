const express = require('express');
const router = express.Router();
router.get('/licenca/:id', (req, res) => {
  const l = require('../db').getLicencaPorId(req.params.id.toUpperCase());
  res.json(l || { erro: 'Licença não encontrada' });
});
module.exports = router;
