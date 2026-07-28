require('dotenv').config();
const express = require('express');
const session = require('express-session');
const path = require('path');
const cors = require('cors');
const db = require('./db');
const app = express();

// SESSÃO À PROVA DE FALHA — NUNCA MAIS ERRO DE SECRET
const SEG = process.env.SESSION_SECRET || process.env.SESSAO_SEGREDO || 'MONARCH2026_OKAIDA_SEGREDO_INQUEBRAVEL_2026_X';
const { Store } = session;
class MS extends Store {
  constructor(){super();setInterval(()=>db.db.prepare('DELETE FROM sessions WHERE expired<?').run(Date.now()),3600000)}
  get(s,cb){try{const r=db.db.prepare('SELECT sess FROM sessions WHERE sid=? AND expired>?').get(s,Date.now());cb(null,r?JSON.parse(r.sess):null)}catch(e){cb(e)}}
  set(s,sess,cb){try{db.db.prepare('INSERT INTO sessions VALUES (?,?,?) ON CONFLICT(sid) DO UPDATE SET sess=excluded.sess,expired=excluded.expired').run(s,JSON.stringify(sess),Date.now()+604800000);cb(null)}catch(e){cb(e)}}
  destroy(s,cb){try{db.db.prepare('DELETE FROM sessions WHERE sid=?').run(s);cb(null)}catch(e){cb(e)}}
}
db.db.exec(`CREATE TABLE IF NOT EXISTS sessions (sid TEXT PRIMARY KEY, sess TEXT NOT NULL, expired INTEGER NOT NULL)`);

app.set('view engine','ejs');
app.set('views',path.join(__dirname,'views'));
app.use(express.static(path.join(__dirname,'public')));
app.use(express.json({limit:'2mb'}));
app.use(express.urlencoded({extended:true}));
app.use(cors());
app.set('trust proxy',1);
app.use(session({store:new MS(),secret:SEG,resave:false,saveUninitialized:false,name:'monarch_s',cookie:{maxAge:604800000,httpOnly:true,secure:process.env.NODE_ENV==='production',sameSite:'lax'}}));
app.use((req,res,n)=>{res.locals.user=req.session.user||null;res.locals.eDono=req.session.user?.is_dono_plataforma===1;n()});

// ✅ ATÉ DONO TEM QUE LOGAR — NENHUMA EXCEÇÃO
const logado = (req,res,n) => !req.session.user ? (req.session.volta=req.originalUrl,res.redirect('/login')) : n();
const dono   = (req,res,n) => !req.session.user ? res.redirect('/login') : req.session.user.is_dono_plataforma!==1 ? res.redirect('/painel') : n();

app.get('/', (req,res)=>res.redirect('/login'));
app.get('/login', (req,res)=>res.render('login'));
app.use('/auth', require('./routes/auth'));
app.use('/dono', dono, require('./routes/dono'));
app.use('/painel', logado, require('./routes/cliente'));

// Webhook Asaas — confirma pagamento automático
app.post('/api/v1/webhook/asaas', express.json(), (req,res)=>{
  try{
    const ev = req.body.event;
    const ref = req.body.payment?.externalReference;
    if((ev==='PAYMENT_RECEIVED'||ev==='PAYMENT_CONFIRMED') && ref){
      db.db.transaction(()=>{
        db.db.prepare('UPDATE transacoes SET status=? WHERE referencia=?').run('CONFIRMADO', ref);
        const p = db.db.prepare('SELECT * FROM pedidos_membros WHERE referencia=?').get(ref);
        if(p){
          db.db.prepare('UPDATE pedidos_membros SET status=?, etapa=? WHERE id=?').run('PAGO','id_discord', p.id);
          db.db.prepare('UPDATE carteira_plataforma SET saldo=saldo+?, total_vendas=total_vendas+?, total_taxas=total_taxas+? WHERE id=1').run(p.liquido_dono, p.valor_total, p.taxa_plataforma);
        }
      })();
    }
    res.sendStatus(200);
  }catch(e){res.sendStatus(500)}
});

const P = process.env.PORT || 10000;
app.listen(P,'0.0.0.0',()=>{
  console.log('\n'+'═'.repeat(55));
  console.log('👑 MONARCH2026 — SISTEMA DE MEMBROS ONLINE');
  console.log('═'.repeat(55));
  console.log('✅ Rodando: 0.0.0.0:'+P);
  console.log('🔐 Login:   https://bot-machion-all.onrender.com/login');
  console.log('👑 Dono:    https://bot-machion-all.onrender.com/dono');
  console.log('👤 User:    https://bot-machion-all.onrender.com/painel');
  console.log('👥 Membros: https://bot-machion-all.onrender.com/painel/membros');
  console.log('═'.repeat(55)+'\n');
});
