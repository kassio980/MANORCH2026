const express = require('express');
const router = express.Router();
router.get('/status/:id', (req, res) => res.json({ bot: req.params.id, status: 'ONLINE', cpu: '8%', ram: '192MB' }));
module.exports = router;
