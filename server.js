require('dotenv').config();
const express = require('express');
const session = require('express-session');
const path = require('path');
const cors = require('cors');
const db = require('./db');
const app = express();

// STORE DE SESSÃO NATIVO — ACABA COM O ERRO DO RENDER
const { Store } = session;
class MonarchSessionStore extends Store {
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

// CONFIG
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));
app.use(express.static(path.join(__dirname, 'public')));
app.use(express.json({limit:'2mb'}));
app.use(express.urlencoded({extended:true}));
app.use(cors());
app.set('trust proxy', 1);

// SESSÃO SEGURA
app.use(session({
  store: new MonarchSessionStore(),
  secret: process.env.SESSAO_SEGREDO,
  resave: false, saveUninitialized: false,
  name: 'monarch_session',
  cookie: { maxAge: 7*86400000, httpOnly:true, secure: process.env.AMBIENTE==='producao', sameSite:'lax' }
}));

// DADOS GLOBAIS EM TODAS AS TELAS
app.use((req, res, next) => {
  res.locals.user = req.session.user || null;
  res.locals.discordNome = req.session.user?.username || 'Convidado';
  res.locals.eDono = req.session.user?.is_dono === 1;
  res.locals.tema = req.session.tema || 'dark';
  res.locals.notifCount = req.session.user ? db.notificacoesNaoLidas(req.session.user.id) : 0;
  res.locals.ip = req.ip;
  next();
});

// ROTAS
app.use('/', require('./routes/public'));
app.use('/auth', require('./routes/auth'));
app.use('/dono', require('./routes/dono'));
app.use('/painel', require('./routes/cliente'));
app.use('/api/v1', require('./routes/api'));
app.use('/bots', require('./routes/bots'));

// PORTA OBRIGATÓRIA DO RENDER
const PORTA = process.env.PORT || process.env.PORTA || 3000;
app.listen(PORTA, '0.0.0.0', () => {
  console.log('\n'+'═'.repeat(62));
  console.log('👑 𝐌𝐎𝐍𝐀𝐑𝐂𝐇𝟐𝟎𝟐𝟔© — VERSÃO PREMIUM SAAS');
  console.log('═'.repeat(62));
  console.log(`✅ Rodando em : http://0.0.0.0:${PORTA}`);
  console.log(`👑 Dono       : /dono`);
  console.log(`👤 Cliente    : /painel`);
  console.log(`🔐 Webhook    : /api/v1/webhook/asaas`);
  console.log(`🛡️ Verificar  : /verificar`);
  console.log('═'.repeat(62)+'\n');
});
