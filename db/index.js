const Database = require('better-sqlite3');
const db = new Database('./db/monarch2026.db');

// CRIA TABELAS SE NÃO EXISTIREM
db.exec(`
CREATE TABLE IF NOT EXISTS usuarios (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  discord_id TEXT UNIQUE NOT NULL,
  username TEXT NOT NULL,
  avatar TEXT,
  email TEXT,
  is_dono INTEGER DEFAULT 0,
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
  token TEXT,
  servidor_id TEXT,
  status TEXT DEFAULT 'OFFLINE',
  FOREIGN KEY(licenca_id) REFERENCES licencas(id)
);

CREATE TABLE IF NOT EXISTS transacoes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  usuario_id INTEGER NOT NULL,
  tipo TEXT NOT NULL,
  valor REAL NOT NULL,
  status TEXT DEFAULT 'PENDENTE',
  criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
);
`);

// FUNÇÕES PRONTAS
module.exports = {
  salvarUsuario: (u) => {
    const existe = db.prepare('SELECT * FROM usuarios WHERE discord_id = ?').get(u.discordId);
    if (existe) return existe;
    const info = db.prepare('INSERT INTO usuarios (discord_id, username, avatar, email, is_dono) VALUES (?,?,?,?,?)')
      .run(u.discordId, u.username, u.avatar, u.email, u.isDono ? 1 : 0);
    return db.prepare('SELECT * FROM usuarios WHERE id = ?').get(info.lastInsertRowid);
  },
  getLicencaPorId: (id) => db.prepare('SELECT * FROM licencas WHERE id = ?').get(id),
  criarLicenca: (l) => db.prepare('INSERT INTO licencas (id, usuario_id, plano, chave_api, validade) VALUES (?,?,?,?,?)')
    .run(l.id, l.usuario_id, l.plano, l.chave_api, l.validade),
  todasLicencas: () => db.prepare('SELECT * FROM licencas ORDER BY criado_em DESC').all(),
  totalUsuarios: () => db.prepare('SELECT COUNT(*) as total FROM usuarios').get().total,
  totalReceita: () => db.prepare('SELECT COALESCE(SUM(valor),0) as total FROM transacoes WHERE status = ?').get('CONFIRMADO').total
};
