const express = require('express');
const router = express.Router();
const axios = require('axios');
const db = require('../db');
const crypto = require('crypto');
const ASAAS = 'https://www.asaas.com/api/v3';
const AKEY = () => process.env.ASAAS_CHAVE_MESTRE || db.cfg().chave_asaas_dono;
const BOT_TOKEN = () => process.env.DISCORD_BOT_TOKEN || db.cfg().token_bot_membros;
const DC_APP_ID = () => process.env.DISCORD_CLIENT_ID;

router.get('/', (req, res) => res.render('loja/cliente-loja', {
  titulo:'🏠 Loja',
  prods: db.db.prepare('SELECT * FROM produtos WHERE ativo=1 ORDER BY ordem').all(),
  carteira: db.minhaCarteiraBot(req.session.user.id),
  licencas: db.minhasLicencas(req.session.user.id),
  pedidos: db.meusPedidos(req.session.user.id).slice(0,5)
}));

router.get('/membros/calc', (req, res) => {
  res.json(db.calcMembros(+req.query.q, req.query.r==='1', req.query.p==='1'));
});

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

router.post('/membros/comprar', async (req, res) => {
  const uid = req.session.user.id;
  const c = db.cfg();
  const qtd = Math.max(c.membros_min, Math.min(c.membros_max, +req.body.qtd||20));
  const refil = req.body.refil==='1'?1:0, prio = req.body.prio==='1'?1:0;
  const calc = db.calcMembros(qtd, refil, prio);
  const ref = `MEM-${Date.now()}-${crypto.randomBytes(2).toString('hex').toUpperCase()}`;

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

// ==================================================
// ✅ AQUI É A PARTE QUE VOCÊ PEDIU:
//    PEGA O ID DIGITADO → ABRE DM → MANDA TUDO LÁ
// ==================================================
router.post('/membros/pedido/:id/id', async (req, res) => {
  const uid = req.session.user.id;
  const DID = req.body.discord_id?.trim().replace(/\D/g,''); // limpa o ID
  if(!DID || DID.length < 15) return res.redirect('back?erro=id');

  // Salva o ID no pedido
  db.db.prepare('UPDATE pedidos_membros SET id_discord_usuario=?, etapa=? WHERE id=? AND usuario_id=?')
    .run(DID, 'bot_dm', +req.params.id, uid);
  const p = db.db.prepare('SELECT * FROM pedidos_membros WHERE id=?').get(+req.params.id);
  const BT = BOT_TOKEN();
  const APP = DC_APP_ID();

  // ✅ Tenta enviar DIRETO NA DM DA PESSOA PELO ID
  let enviou = false, erroDm = '';
  if(BT && APP){
    try {
      // 1) Abre DM com o usuário pelo ID
      const dm = await axios.post('https://discord.com/api/v10/users/@me/channels',
        { recipient_id: DID },
        { headers: { Authorization: `Bot ${BT}`, 'Content-Type':'application/json' } }
      );
      const DM_ID = dm.data.id;

      // 2) Link do BOT com permissões: GERENCIAR MEMBROS + CARGOS + ADMINISTRADOR
      const INV_BOT = `https://discord.com/api/oauth2/authorize?client_id=${APP}&permissions=268435457&scope=bot%20applications.commands&guild_id=`;

      // 3) MENSAGEM 1: Dados do pedido + botão "Me adicionar no servidor"
      await axios.post(`https://discord.com/api/v10/channels/${DM_ID}/messages`, {
        content: `✅ **SEU PEDIDO FOI APROVADO!**\n\n📦 **Pedido #${p.id}**\n👥 **Quantidade:** ${p.quantidade} membros\n💰 **Valor pago:** R$ ${p.valor_total.toFixed(2).replace('.',',')}\n⏰ **Horário:** ${new Date().toLocaleString('pt-BR')}\n${p.refil?'🔁 **Refil automático ativado**\n':''}${p.prioridade?'⚡ **Prioridade ativada — entrega instantânea**\n':''}\n\n👇 Clique abaixo para adicionar o BOT no seu servidor:`,
        components: [{
          type: 1,
          components: [{
            type: 2, style: 5, label: '🤖 Me adicionar no servidor',
            url: INV_BOT
          }]
        }]
      }, { headers: { Authorization: `Bot ${BT}` } });

      // 4) MENSAGEM 2: Confirmação do servidor (o bot detecta o invite e responde sozinho depois)
      await axios.post(`https://discord.com/api/v10/channels/${DM_ID}/messages`, {
        content: `💡 **Assim que adicionar o BOT:**\n\nEle vai te perguntar aqui na DM:\n> 🤖 *Quer adicionar esses ${p.quantidade} membros nesse servidor?*\n> 📍 Nome do Servidor · ID: 123456789\n\n✅ Aí é só clicar em **CONFIRMAR** que ele já começa a puxar!\n\n🫂 _Obrigado pela compra, volte sempre!_`
      }, { headers: { Authorization: `Bot ${BT}` } });

      enviou = true;
      db.db.prepare('UPDATE pedidos_membros SET etapa=? WHERE id=?').run('dm_enviada', p.id);
    } catch(e){
      erroDm = e.response?.data?.message || e.message;
      console.log('ERRO DM DISCORD:', erroDm);
      // Se não conseguiu abrir DM (bot bloqueado / usuário não existe)
      db.db.prepare('UPDATE pedidos_membros SET etapa=?, status=? WHERE id=?')
        .run('erro_dm', 'FALHA_DM', p.id);
    }
  }

  // Redireciona de volta com status
  res.redirect(`/painel/membros/pedido/${p.id}?dm=${enviou?'ok':'falha'}`);
});

router.get('/api', (req,res)=>res.render('loja/cliente-api',{titulo:'🔑 APIs', l:db.minhasLicencas(req.session.user.id)}));
router.get('/carteira', (req,res)=>res.render('loja/cliente-carteira',{titulo:'💰 Carteira', c:db.minhaCarteiraBot(req.session.user.id), cfg:db.cfg()}));
module.exports = router;
