const express = require('express');
const router = express.Router();
const db = require('../db');

router.get('/', (req, res) => {
  const p = db.plat();
  res.render('premium/dono-dashboard', {
    titulo:'👑 Painel Dono', seu_saldo:p.saldo, total_taxas:p.total_taxas, total_vendas:p.total_vendas,
    clientes:db.totalUsuarios(), ultimas:db.ultimasAtividades(10),
    pedidos: db.db.prepare('SELECT COUNT(*) c FROM pedidos_membros WHERE DATE(criado_em)=DATE()').get().c,
    membros: db.db.prepare('SELECT COALESCE(SUM(quantidade),0) c FROM pedidos_membros WHERE DATE(criado_em)=DATE()').get().c
  });
});

// ✅ DONO GERENCIA TODOS OS PEDIDOS
router.get('/membros', (req, res) => res.render('loja/dono-membros', {
  titulo:'👥 Gerenciar Membros', pedidos: db.todosPedidos(), cfg: db.cfg()
}));
router.get('/membros/:id/confirmar', (req, res) => {
  const p = db.db.prepare('SELECT * FROM pedidos_membros WHERE id=?').get(+req.params.id);
  if(!p) return res.redirect('back');
  db.db.transaction(()=>{
    db.db.prepare('UPDATE pedidos_membros SET status=?, etapa=? WHERE id=?').run('PAGO','id_discord', p.id);
    db.db.prepare('UPDATE transacoes SET status=? WHERE referencia=?').run('CONFIRMADO', p.referencia);
    db.db.prepare('UPDATE carteira_plataforma SET saldo=saldo+?, total_vendas=total_vendas+?, total_taxas=total_taxas+? WHERE id=1')
      .run(p.liquido_dono, p.valor_total, p.taxa_plataforma);
  })();
  res.redirect('back');
});

router.get('/produtos', (req,res)=>res.render('loja/dono-produtos',{titulo:'📦 Produtos',prods:db.db.prepare('SELECT * FROM produtos ORDER BY ordem').all()}));
router.post('/produtos/salvar', (req,res)=>{
  const b=req.body;
  db.db.prepare(`INSERT INTO produtos (id,nome,tipo_bot,nivel_api,preco,dias_validade,badge,cor,descricao,tem_carteira_interna,ordem,ativo)
    VALUES (?,?,?,?,?,?,?,?,?,?,?,1) ON CONFLICT(id) DO UPDATE SET nome=excluded.nome,tipo_bot=excluded.tipo_bot,nivel_api=excluded.nivel_api,
    preco=excluded.preco,dias_validade=excluded.dias_validade,badge=excluded.badge,cor=excluded.cor,descricao=excluded.descricao,
    tem_carteira_interna=excluded.tem_carteira_interna,ordem=excluded.ordem`)
    .run(b.id.toUpperCase(),b.nome,b.tipo_bot.toUpperCase(),b.nivel_api.toUpperCase(),+b.preco,+b.dias_validade,
      b.badge||'',b.cor||'roxo',b.descricao||'',['INTERMEDIARIO','VIP','PREMIUM'].includes(b.tipo_bot.toUpperCase())?1:(b.tem_carteira_interna?1:0),+b.ordem||0);
  res.redirect('/dono/produtos');
});
router.get('/config', (req,res)=>res.render('loja/dono-config',{titulo:'⚙️ Config',c:db.cfg()}));
router.post('/config', (req,res)=>{
  const b=req.body;
  db.db.prepare(`UPDATE config_plataforma SET taxa_saque_membros=?,taxa_membros_dono=?,valor_prioridade=?,refil_pct=?,preco_base_20=?,
    membros_min=?,membros_max=?,chave_asaas_dono=?,token_bot_membros=?,servidor_convite=?,servidor_id=? WHERE id=1`)
    .run(+b.taxa_saque_membros,+b.taxa_membros_dono,+b.valor_prioridade,+b.refil_pct,+b.preco_base_20,
      +b.membros_min,+b.membros_max,b.chave_asaas_dono||'',b.token_bot_membros||'',
      b.servidor_convite||'https://discord.gg/9jPnRdMbgp',b.servidor_id||'');
  res.redirect('/dono/config');
});
router.get('/carteira', (req,res)=>res.render('loja/dono-carteira',{titulo:'💰 Carteira',c:db.plat(),cfg:db.cfg()}));
router.post('/carteira/depositar', (req,res)=>{db.db.prepare('UPDATE carteira_plataforma SET saldo=saldo+? WHERE id=1').run(+req.body.valor);res.redirect('/dono/carteira');});
router.post('/carteira/sacar', (req,res)=>{
  const v=+req.body.valor; const p=db.plat();
  if(v>p.saldo) return res.redirect('/dono/carteira?erro=saldo');
  db.db.prepare('UPDATE carteira_plataforma SET saldo=saldo-?,total_sacado=total_sacado+? WHERE id=1').run(v,v);
  res.redirect('/dono/carteira?ok=1');
});
module.exports = router;
