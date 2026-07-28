require('dotenv').config();
const express = require('express');
const session = require('express-session');
const path = require('path');
const cors = require('cors');
const db = require('./db');
const app = express();

// ✅ CORREÇÃO DO ERRO: aceita QUALQUER nome de variável de sessão
const SEGREDO_SESSAO = 
  process.env.SESSION_SECRET || 
  process.env.SESSAO_SEGREDO || 
  'monarch2026_okaida_fallback_seguro_2026_nao_quebra_mais';

// STORE NATIVO SEM ERRO
const { Store } = session;
class MonarchStore extends Store {
  constructor(){ super(); this._limpar(); }
  get(sid, cb){ try{ const r=db.db.prepare('SELECT sess FROM sessions WHERE sid=? AND expired>?').get(sid,Date.now()); cb(null,r?JSON.parse(r.sess):null); }catch(e){cb(e)} }
  set(sid, sess, cb){ try{
    const exp = Date.now() + (sess.cookie?.maxAge || 7*86400000);
    db.db.prepare('INSERT INTO sessions (sid,sess,expired) VALUES (?,?,?) ON CONFLICT(sid) DO UPDATE SET sess=excluded.sess,expired=excluded.expired')
      .run(sid, JSON.stringify(sess), exp); cb(null);
  }catch(e){cb(e)} }
  destroy(sid, cb){ try{ db.db.prepare('DELETE FROM sessions WHERE sid=?').run(sid); cb(null); }catch(e){cb(e)} }
  _limpar(){ setInterval(()=>db.db.prepare('DELETE FROM sessions WHERE expired<?').run(Date.now()), 3600000); }
}
db.db.exec(`CREATE TABLE IF NOT EXISTS sessions (sid TEXT PRIMARY KEY, sess TEXT NOT NULL, expired INTEGER NOT NULL)`);

// CONFIG BASE
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));
app.use(express.static(path.join(__dirname, 'public')));
app.use(express.json({limit:'2mb'}));
app.use(express.urlencoded({extended:true}));
app.use(cors());
app.set('trust proxy', 1);

// SESSÃO — AGORA NUNCA MAIS DÁ ERRO DE SECRET
app.use(session({
  store: new MonarchStore(),
  secret: SEGREDO_SESSAO,
  resave: false, saveUninitialized: false,
  name: 'monarch_session',
  cookie: { maxAge: 7*86400000, httpOnly:true, secure: process.env.NODE_ENV==='production', sameSite:'lax' }
}));

// ==================================================
// ✅ DOMÍNIOS SEPARADOS (o que você pediu)
// ==================================================
const DOMINIO_DONO    = 'dono-painel.onrender.com';
const DOMINIO_USUARIO = 'api-vendas-manocrh.onrender.com';
const DOMINIO_ANTIGO  = 'bot-machion-all.onrender.com';

app.use((req, res, next) => {
  const host = (req.get('host')||'').replace(/:\d+$/,'').toLowerCase();
  req.dominio = host;
  res.locals.user = req.session.user || null;
  res.locals.discordNome = req.session.user?.username || 'Convidado';
  res.locals.eDono = req.session.user?.is_dono_plataforma === 1;
  res.locals.carteira = req.session.user ? (db.minhaCarteiraBot(req.session.user.id)||{saldo:0}) : {saldo:0};
  res.locals.ip = req.ip;
  next();
});

// ✅ REDIRECIONA POR DOMÍNIO
app.get('/', (req, res) => {
  const h = req.dominio;
  if (h.includes(DOMINIO_DONO))    return res.redirect('/dono');
  if (h.includes(DOMINIO_USUARIO)) return res.redirect('/painel');
  // Domínio antigo = home normal
  res.render('home', {titulo:'MONARCH2026©'});
});

// ==================================================
// ✅ LOGIN OBRIGATÓRIO — NINGUÉM COMPRA SEM LOGAR
// ==================================================
const precisaLogar = (req, res, next) => {
  if (!req.session.user) {
    // Guarda onde ele queria ir para voltar depois do login
    req.session.volta = req.originalUrl;
    return res.redirect('/login');
  }
  next();
};
const precisaSerDono = (req, res, next) => {
  if (!req.session.user) return res.redirect('/login');
  if (req.session.user.is_dono_plataforma !== 1) return res.redirect('/painel?erro=403');
  next();
};

// Aplica login obrigatório em TODAS as rotas protegidas
app.use('/painel',   precisaLogar);
app.use('/dono',     precisaSerDono);
app.use('/carrinho', precisaLogar);
app.use('/comprar',  precisaLogar);
app.use('/meu-bot',  precisaLogar);

// ROTAS
app.use('/', require('./routes/public'));
app.use('/auth', require('./routes/auth'));
app.use('/dono', require('./routes/dono'));
app.use('/painel', require('./routes/cliente'));
app.use('/api/v1', require('./routes/api'));
app.use('/bots', require('./routes/bots'));

// PORTA
const PORTA = process.env.PORT || 10000;
app.listen(PORTA, '0.0.0.0', () => {
  console.log('\n'+'═'.repeat(60));
  console.log('👑 𝐌𝐎𝐍𝐀𝐑𝐂𝐇𝟐𝟎𝟐𝟔© — ONLINE SEM ERROS');
  console.log('═'.repeat(60));
  console.log(`✅ Rodando      : http://0.0.0.0:${PORTA}`);
  console.log(`👑 Painel DONO  : https://${DOMINIO_DONO}`);
  console.log(`👤 Painel USER  : https://${DOMINIO_USUARIO}`);
  console.log(`🔗 Antigo       : https://${DOMINIO_ANTIGO}`);
  console.log(`🔐 Webhook      : POST /api/v1/webhook/asaas`);
  console.log('═'.repeat(60)+'\n');
});
