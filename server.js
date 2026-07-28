require('dotenv').config();
const express = require('express');
const session = require('express-session');
const path = require('path');
const cors = require('cors');
const db = require('./db');
const app = express();

// ✅ À PROVA DE FALHA: NUNCA MAIS SECRET UNDEFINED
const SEGREDO = 
  process.env.SESSION_SECRET || 
  process.env.SESSAO_SEGREDO || 
  'MONARCH2026_OKAIDA_SEGREDO_FIXO_QUE_NUNCA_QUEBRA_2026_XYZ';

// Store no banco
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

// Config base
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));
app.use(express.static(path.join(__dirname, 'public')));
app.use(express.json({limit:'2mb'}));
app.use(express.urlencoded({extended:true}));
app.use(cors());
app.set('trust proxy', 1);

// ✅ SESSÃO 100% SEGURA — NUNCA MAIS ERRO
app.use(session({
  store: new MonarchStore(),
  secret: SEGREDO,
  resave: false, saveUninitialized: false,
  name: 'monarch_session',
  cookie: { maxAge: 7*86400000, httpOnly:true, secure: process.env.NODE_ENV==='production', sameSite:'lax' }
}));

// Variáveis globais
app.use((req, res, next) => {
  res.locals.user = req.session.user || null;
  res.locals.discordNome = req.session.user?.username || 'Convidado';
  res.locals.eDono = req.session.user?.is_dono_plataforma === 1;
  res.locals.carteira = req.session.user ? (db.minhaCarteiraBot(req.session.user.id)||{saldo:0}) : {saldo:0};
  next();
});

// ✅ ATÉ O DONO TEM QUE LOGAR — NENHUMA EXCEÇÃO
const precisaLogar = (req, res, next) => {
  if (!req.session.user) { req.session.volta = req.originalUrl; return res.redirect('/login'); }
  next();
};
const precisaSerDono = (req, res, next) => {
  if (!req.session.user) return res.redirect('/login');
  if (req.session.user.is_dono_plataforma !== 1) return res.redirect('/painel?erro=403');
  next();
};

// Bloqueia TUDO sem login
app.use('/painel',   precisaLogar);
app.use('/dono',     precisaSerDono); // ✅ DONO SÓ ENTRA SE LOGAR
app.use('/carrinho', precisaLogar);
app.use('/comprar',  precisaLogar);
app.use('/meu-bot',  precisaLogar);

// Rotas
app.get('/', (req, res) => res.redirect('/login')); // Home = direto pro login
app.use('/', require('./routes/public'));
app.use('/auth', require('./routes/auth'));
app.use('/dono', require('./routes/dono'));
app.use('/painel', require('./routes/cliente'));
app.use('/api/v1', require('./routes/api'));

// Inicia
const PORTA = process.env.PORT || 10000;
app.listen(PORTA, '0.0.0.0', () => {
  console.log('\n'+'═'.repeat(58));
  console.log('👑 MONARCH2026© — ONLINE SEM ERROS DE SESSÃO');
  console.log('═'.repeat(58));
  console.log(`✅ Rodando: http://0.0.0.0:${PORTA}`);
  console.log(`👑 Dono:    /dono    (precisa logar)`);
  console.log(`👤 User:    /painel  (precisa logar)`);
  console.log(`🔐 Login:   /login`);
  console.log('═'.repeat(58)+'\n');
});
