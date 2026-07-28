const Database = require('better-sqlite3');
const db = new Database('./db/monarch2026.db', { fileMustExist:false });
db.pragma('journal_mode = WAL');
db.pragma('foreign_keys = ON');

db.exec(`
CREATE TABLE IF NOT EXISTS usuarios (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  discord_id TEXT UNIQUE NOT NULL,
  username TEXT NOT NULL,
  avatar TEXT,
  email TEXT,
  is_dono INTEGER DEFAULT 0,
  nivel TEXT DEFAULT 'NOVO',
  reputacao INTEGER DEFAULT 50,
  criado_em DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS licencas (
  id TEXT PRIMARY KEY,
  usuario_id INTEGER NOT NULL,
  plano TEXT NOT NULL,
  chave_api TEXT UNIQUE NOT NULL,
  validade DATETIME NOT NULL,
  status TEXT DEFAULT 'ATIVA',
  criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
);
CREATE TABLE IF NOT EXISTS bots (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  licenca_id TEXT NOT NULL,
  nome TEXT DEFAULT 'MONARCH BOT',
  token TEXT, servidor_id TEXT,
  status TEXT DEFAULT 'OFFLINE',
  cpu REAL DEFAULT 0, ram REAL DEFAULT 0,
  uptime TEXT DEFAULT '0s',
  FOREIGN KEY(licenca_id) REFERENCES licencas(id)
);
CREATE TABLE IF NOT EXISTS transacoes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  usuario_id INTEGER NOT NULL,
  tipo TEXT NOT NULL,
  valor REAL NOT NULL,
  taxa REAL DEFAULT 0,
  liquido REAL DEFAULT 0,
  referencia TEXT,
  status TEXT DEFAULT 'PENDENTE',
  descricao TEXT,
  criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
);
CREATE TABLE IF NOT EXISTS carteiras (
  usuario_id INTEGER PRIMARY KEY,
  saldo REAL DEFAULT 0,
  pendente REAL DEFAULT 0,
  sacado REAL DEFAULT 0,
  gasto REAL DEFAULT 0,
  FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
);
CREATE TABLE IF NOT EXISTS planos (
  id TEXT PRIMARY KEY,
  nome TEXT NOT NULL, preco REAL NOT NULL, dias INTEGER NOT NULL,
  api INTEGER DEFAULT 1, bot INTEGER DEFAULT 1, host INTEGER DEFAULT 1, vip INTEGER DEFAULT 1,
  limite_servidores INTEGER DEFAULT 1
);
CREATE TABLE IF NOT EXISTS logs_auditoria (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  usuario TEXT, acao TEXT, ip TEXT,
  resultado TEXT DEFAULT 'SUCCESS',
  criado_em DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS notificacoes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  usuario_id INTEGER,
  titulo TEXT, mensagem TEXT,
  lida INTEGER DEFAULT 0,
  criado_em DATETIME DEFAULT CURRENT_TIMESTAMP
);
`);

// Cria carteira automaticamente
db.function('criar_carteira', (uid) => {
  db.prepare('INSERT OR IGNORE INTO carteiras (usuario_id) VALUES (?)').run(uid); return null;
});

module.exports = {
  db,
  salvarUsuario: (u) => {
    const ex = db.prepare('SELECT * FROM usuarios WHERE discord_id = ?').get(u.discordId);
    if (ex) { db.prepare('SELECT criar_carteira(?)').get(ex.id); return ex; }
    const info = db.prepare('INSERT INTO usuarios (discord_id,username,avatar,email,is_dono) VALUES (?,?,?,?,?)')
      .run(u.discordId, u.username, u.avatar, u.email, u.isDono?1:0);
    const novo = db.prepare('SELECT * FROM usuarios WHERE id = ?').get(info.lastInsertRowid);
    db.prepare('SELECT criar_carteira(?)').get(novo.id);
    return novo;
  },
  getLicencaPorId: (id) => db.prepare('SELECT * FROM licencas WHERE id = ?').get(id),
  criarLicenca: (l) => db.prepare('INSERT INTO licencas (id,usuario_id,plano,chave_api,validade) VALUES (?,?,?,?,?)').run(l.id,l.usuario_id,l.plano,l.chave_api,l.validade),
  totalUsuarios: () => db.prepare('SELECT COUNT(*) c FROM usuarios WHERE is_dono=0').get().c,
  totalReceita: () => db.prepare('SELECT COALESCE(SUM(liquido),0) v FROM transacoes WHERE status=?').get('CONFIRMADO').v,
  totalVendas: () => db.prepare('SELECT COUNT(*) c FROM transacoes WHERE tipo=? AND status=?').get('VENDA','CONFIRMADO').c,
  botsOnline: () => db.prepare('SELECT COUNT(*) c FROM bots WHERE status=?').get('ONLINE').c,
  saquesPendentes: () => db.prepare('SELECT COUNT(*) c FROM transacoes WHERE tipo=? AND status=?').get('SAQUE','PENDENTE').c,
  ultimasAtividades: (n=10) => db.prepare('SELECT * FROM transacoes ORDER BY criado_em DESC LIMIT ?').all(n),
  minhasLicencas: (uid) => db.prepare('SELECT * FROM licencas WHERE usuario_id = ? ORDER BY criado_em DESC').all(uid),
  minhaCarteira: (uid) => db.prepare('SELECT * FROM carteiras WHERE usuario_id = ?').get(uid),
  notificacoesNaoLidas: (uid) => db.prepare('SELECT COUNT(*) c FROM notificacoes WHERE usuario_id=? AND lida=0').get(uid).c,
  minhasNotificacoes: (uid) => db.prepare('SELECT * FROM notificacoes WHERE usuario_id=? ORDER BY criado_em DESC LIMIT 20').all(uid),
  buscarGlobal: (q) => {
    const like = `%${q}%`;
    return {
      licencas: db.prepare('SELECT * FROM licencas WHERE id LIKE ? OR plano LIKE ? LIMIT 5').all(like,like),
      usuarios: db.prepare('SELECT * FROM usuarios WHERE username LIKE ? OR discord_id LIKE ? LIMIT 5').all(like,like),
      transacoes: db.prepare('SELECT * FROM transacoes WHERE referencia LIKE ? OR descricao LIKE ? LIMIT 5').all(like,like)
    };
  },
  log: (u,a,ip,r='SUCCESS') => db.prepare('INSERT INTO logs_auditoria (usuario,acao,ip,resultado) VALUES (?,?,?,?)').run(u,a,ip,r)
};
