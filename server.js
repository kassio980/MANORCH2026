require('dotenv').config();
const express = require('express');
const session = require('express-session');
const SQLiteStore = require('connect-sqlite3')(session);
const path = require('path');
const cors = require('cors');
const app = express();

// CONFIG BASE
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));
app.use(express.static(path.join(__dirname, 'public')));
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(cors());

// SESSÃO SEGURA
app.use(session({
  store: new SQLiteStore({ db: 'sessions.db', dir: './db' }),
  secret: process.env.SESSAO_SEGREDO,
  resave: false,
  saveUninitialized: false,
  cookie: { maxAge: 7*24*60*60*1000, httpOnly: true, secure: process.env.AMBIENTE === 'producao' }
}));

// DADOS DINÂMICOS DO DISCORD EM TODAS AS TELAS
app.use((req, res, next) => {
  res.locals.user = req.session.user || null;
  res.locals.discordNome = req.session.user?.username || 'Convidado';
  res.locals.eDono = req.session.user?.is_dono === 1;
  next();
});

// ROTAS
app.use('/', require('./routes/public'));
app.use('/auth', require('./routes/auth'));
app.use('/dono', require('./routes/dono'));
app.use('/painel', require('./routes/cliente'));
app.use('/api/v1', require('./routes/api'));
app.use('/bots', require('./routes/bots'));

// INICIA
const PORTA = process.env.PORTA || 3000;
app.listen(PORTA, () => {
  console.log('\n' + '='.repeat(60));
  console.log('👑 𝐌𝐎𝐍𝐀𝐑𝐂𝐇𝟐𝟎𝟐𝟔© — RODANDO COM SUCESSO');
  console.log('='.repeat(60));
  console.log(`🌐 Servidor: http://localhost:${PORTA}`);
  console.log(`👑 Painel Dono: http://localhost:${PORTA}/dono`);
  console.log(`👤 Painel Cliente: http://localhost:${PORTA}/painel`);
  console.log(`🔗 Domínio Público: ${process.env.DOMINIO_PUBLICO}`);
  console.log(`🔙 Backend Protegido: ${process.env.DOMINIO_BACKEND}`);
  console.log('='.repeat(60) + '\n');
});
