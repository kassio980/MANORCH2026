const express = require('express');
const router = express.Router();
const axios = require('axios');
const db = require('../db');
const crypto = require('crypto');
const ASAAS = 'https://www.asaas.com/api/v3';
const AKEY = () => process.env.ASAAS_CHAVE_MESTRE || db.cfg().chave_asaas_dono;

router.get('/', (req, res) => res.render('loja/cliente-loja', {
  titulo:'🏠 Loja',
  prods: db.db.prepare('SELECT * FROM produtos WHERE ativo=1 ORDER BY ordem').all(),
  carteira: db.minhaCarteiraBot(req.session.user.id),
  licencas: db.minhasLicencas(req.session.user.id),
  pedidos: db.meusPedidos(req.session.user.id).slice(0,5)
}));

// ✅ CALCULA EM TEMPO REAL (AJAX) — mexeu no slider já atualiza
router.get('/membros/calc', (req, res) => {
  res.json(db.calcMembros(+req.query.q, req.query.r==='1', req.query.p==='1'));
});

// ✅ TELA COMPRA MEMBROS COM SLIDER
router.get('/membros', (req, res) => {
  const c = db.cfg();
  const qtd = Math.max(c.membros_min, Math.min(c.membros_max, +(req.query.qtd||20)));
  const refil = req.query.refil==='1', prio = req.query.prio==='1';
  res.render('loja/cliente-membros', {
    titulo:'👥 Comprar Membros', c, qtd, refil, prio,
    calc: db.calcMembros(qtd, refil, prio),
    entrou: req.session.user.entrou_servidor===1,
    convite: c.servidor_convite
  });
});

// ✅ CRIA PEDIDO E GERA PIX
router.post('/membros/comprar', async (req, res) => {
  const uid = req.session.user.id;
  const c = db.cfg();
  const qtd = Math.max(c.membros_min, Math.min(c.membros_max, +req.body.qtd||20));
  const refil = req.body.refil==='1'?1:0, prio = req.body.prio==='1'?1:0;
  const calc = db.calcMembros(qtd, refil, prio);
  const ref = `MEM-${Date.now()}-${crypto.randomBytes(2).toString('hex').toUpperCase()}`;

  // Gera Pix Asaas
  let pix = { cc:'', qr:'' };
  try {
    const r = await axios.post(`${ASAAS}/payments`, {
      customer: process.env.ASAAS_CLIENTE_ID || 'cus_000000000',
      billingType:'PIX', value: calc.total,
      dueDate: new Date(Date.now()+86400000).toISOString().slice(0,10),
      externalReference: ref, description: `${qtd} membros MONARCH`
    }, {headers:{ access_token: AKEY() }});
    pix = { cc: r.data.pixPayload?.payload||'', qr: r.data.pixPayload?.encodedImage||'' };
  } catch(e){ console.log('ASAAS:',e.response?.data||''); }

  const tid = db.db.prepare(`INSERT INTO transacoes
    (tipo,usuario_id,valor,taxa,liquido,referencia,status,pix_copia_cola,pix_qr)
    VALUES ('MEMBROS',?,?,?,?,?,?,?,?)`)
    .run(uid, calc.total, calc.taxa, calc.liquido, ref, 'PENDENTE', pix.cc, pix.qr).lastInsertRowid;
  const pid = db.db.prepare(`INSERT INTO pedidos_membros
    (usuario_id,quantidade,refil,prioridade,valor_total,taxa_plataforma,liquido_dono,referencia,etapa,status)
    VALUES (?,?,?,?,?,?,?,?,'pagamento','AGUARDANDO_PAGAMENTO')`)
    .run(uid, qtd, refil, prio, calc.total, calc.taxa, calc.liquido, ref).lastInsertRowid;
  db.db.prepare('UPDATE pedidos_membros SET transacao_id=? WHERE id=?').run(tid, pid);
  res.redirect(`/painel/membros/pedido/${pid}`);
});

// ✅ TELA DO PEDIDO (JANELA FLUTUANTE PEDINDO ID)
router.get('/membros/pedido/:id', (req, res) => {
  const p = db.db.prepare(`SELECT p.*,t.pix_copia_cola,t.pix_qr,t.status AS status_pag
    FROM pedidos_membros p LEFT JOIN transacoes t ON t.referencia=p.referencia
    WHERE p.id=? AND p.usuario_id=?`).get(+req.params.id, req.session.user.id);
  if(!p) return res.redirect('/painel/membros');
  res.render('loja/cliente-membros-pedido', {
    titulo:`Pedido #${p.id}`, p, c: db.cfg(),
    entrou: req.session.user.entrou_servidor===1
  });
});

// ✅ SALVA ID DISCORD E DISPARA MENSAGEM NO BOT
router.post('/membros/pedido/:id/id', async (req, res) => {
  const uid = req.session.user.id;
  const did = req.body.discord_id?.trim();
  if(!did) return res.redirect('back');
  db.db.prepare('UPDATE pedidos_membros SET id_discord_usuario=?, etapa=? WHERE id=? AND usuario_id=?')
    .run(did, 'bot', +req.params.id, uid);
  // Mensagem bot
  try {
    const BOT = process.env.DISCORD_BOT_TOKEN;
    const INV = `https://discord.com/api/oauth2/authorize?client_id=${process.env.DISCORD_CLIENT_ID}&permissions=268435456&scope=bot%20applications.commands&guild_id=`;
    if(BOT && process.env.CANAL_LOGS_ID){
      const p = db.db.prepare('SELECT * FROM pedidos_membros WHERE id=?').get(+req.params.id);
      await axios.post(`https://discord.com/api/channels/${process.env.CANAL_LOGS_ID}/messages`, {
        content: `✅ **NOVO PEDIDO #${p.id}**\n👤 <@${did}>\n📦 **${p.quantidade} membros**\n💰 R$ ${p.valor_total.toFixed(2).replace('.',',')}\n⏰ ${new Date().toLocaleString('pt-BR')}\n${p.prioridade?'⚡ Prioridade':''} ${p.refil?'🔁 Refil':''}`,
        components: [{type:1,components:[{type:2,style:5,label:'🤖 Me adicionar no servidor',url:INV}]}]
      }, {headers:{Authorization:`Bot ${BOT}`}});
    }
  } catch(e){}
  res.redirect('back');
});

router.get('/api', (req,res)=>res.render('loja/cliente-api',{titulo:'🔑 APIs', l:db.minhasLicencas(req.session.user.id)}));
router.get('/carteira', (req,res)=>res.render('loja/cliente-carteira',{titulo:'💰 Carteira', c:db.minhaCarteiraBot(req.session.user.id), cfg:db.cfg()}));
module.exports = router;
