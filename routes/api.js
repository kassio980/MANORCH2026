const express = require('express');
const router = express.Router();
const axios = require('axios');
const db = require('../db');

// 🛡️ WEBHOOK ASAAS — CONFIGURADO NO /bot-machion-all.onrender.com
router.post('/webhook/asaas', async (req, res) => {
  try {
    const tok = req.headers['asaas-access-token'];
    if(tok !== process.env.BANCO_WEBHOOK_SEGREDO) return res.sendStatus(403);

    const evento = req.body.event;
    const p = req.body.payment || {};
    const ref = p.externalReference;
    console.log(`📩 ASAAS: ${evento} | ${p.id} | REF=${ref}`);

    if((evento==='PAYMENT_CONFIRMED'||evento==='PAYMENT_RECEIVED') && ref){
      db.db.prepare('UPDATE licencas SET status=? WHERE id=?').run('ATIVA', ref);
      db.db.prepare('UPDATE transacoes SET status=?, liquido=valor-taxa WHERE referencia=?').run('CONFIRMADO', ref);
      const dono = db.db.prepare('SELECT usuario_id FROM licencas WHERE id=?').get(ref);
      if(dono) db.db.prepare('INSERT INTO notificacoes (usuario_id,titulo,mensagem) VALUES (?,?,?)')
        .run(dono.usuario_id, '✅ Pagamento confirmado', `Sua licença ${ref} foi ativada`);
      db.log('ASAAS_WEBHOOK', `${evento} ${ref}`, req.ip);
    }
    if((evento==='PAYMENT_OVERDUE'||evento==='PAYMENT_REFUNDED') && ref){
      db.db.prepare('UPDATE licencas SET status=? WHERE id=?').run('BLOQUEADA', ref);
    }
    return res.sendStatus(200);
  } catch(e){ console.error('WEBHOOK ERRO:',e); return res.sendStatus(500); }
});

router.get('/licenca/:id', (req,res)=>res.json(db.getLicencaPorId(req.params.id.toUpperCase())||{erro:'nao_encontrado'}));
router.get('/health', (req,res)=>res.json({ok:true,ts:Date.now()}));
module.exports = router;
