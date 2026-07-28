const { DatabaseSync } = require('node:sqlite');
const path = require('path');
const db = new DatabaseSync(path.join(__dirname, '..', 'db', 'monarch2026.db'));
db.exec('PRAGMA journal_mode = WAL; PRAGMA foreign_keys = ON');

db.exec(`
CREATE TABLE IF NOT EXISTS usuarios (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  discord_id TEXT UNIQUE NOT NULL, username TEXT NOT NULL, avatar TEXT, email TEXT,
  is_dono_plataforma INTEGER DEFAULT 0, entrou_servidor INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS carteira_plataforma (
  id INTEGER PRIMARY KEY CHECK(id=1),
  saldo REAL DEFAULT 0, total_vendas REAL DEFAULT 0, total_taxas REAL DEFAULT 0, total_sacado REAL DEFAULT 0
);
INSERT OR IGNORE INTO carteira_plataforma (id) VALUES (1);
CREATE TABLE IF NOT EXISTS carteira_dono_bot (usuario_id INTEGER PRIMARY KEY, saldo REAL DEFAULT 0);
CREATE TABLE IF NOT EXISTS produtos (
  id TEXT PRIMARY KEY, nome TEXT NOT NULL, tipo_bot TEXT NOT NULL, nivel_api TEXT NOT NULL,
  preco REAL NOT NULL, dias_validade INTEGER NOT NULL, badge TEXT, cor TEXT DEFAULT 'roxo',
  descricao TEXT, tem_carteira_interna INTEGER DEFAULT 0, ordem INTEGER DEFAULT 0, ativo INTEGER DEFAULT 1
);
CREATE TABLE IF NOT EXISTS licencas (
  id TEXT PRIMARY KEY, usuario_id INTEGER NOT NULL, produto_id TEXT NOT NULL,
  chave_api TEXT UNIQUE NOT NULL, validade DATETIME NOT NULL, status TEXT DEFAULT 'ATIVA'
);
CREATE TABLE IF NOT EXISTS bots (
  id INTEGER PRIMARY KEY AUTOINCREMENT, licenca_id TEXT UNIQUE NOT NULL, usuario_id INTEGER NOT NULL,
  token_discord TEXT, nome_bot TEXT DEFAULT 'MONARCH BOT', status TEXT DEFAULT 'OFFLINE'
);
CREATE TABLE IF NOT EXISTS transacoes (
  id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT NOT NULL, usuario_id INTEGER, valor REAL NOT NULL,
  taxa REAL DEFAULT 0, liquido REAL DEFAULT 0, referencia TEXT, status TEXT DEFAULT 'PENDENTE',
  pix_copia_cola TEXT, pix_qr TEXT, criado_em DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS sessions (sid TEXT PRIMARY KEY, sess TEXT NOT NULL, expired INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS config_plataforma (
  id INTEGER PRIMARY KEY CHECK(id=1),
  taxa_saque_membros REAL DEFAULT 15,
  taxa_membros_dono REAL DEFAULT 45,      -- ✅ 45% vai pra VOCÊ
  valor_prioridade REAL DEFAULT 4.50,     -- ✅ +R$4,50 prioridade
  refil_pct REAL DEFAULT 35,               -- ✅ +35% refil
  preco_base_20 REAL DEFAULT 1.00,         -- ✅ 20 membros = R$1
  membros_min INTEGER DEFAULT 20,
  membros_max INTEGER DEFAULT 2500,
  chave_asaas_dono TEXT, token_bot_membros TEXT,
  servidor_convite TEXT DEFAULT 'https://discord.gg/9jPnRdMbgp',
  servidor_id TEXT DEFAULT ''
);
INSERT OR IGNORE INTO config_plataforma (id) VALUES (1);

-- ✅ TABELA PEDIDOS DE MEMBROS
CREATE TABLE IF NOT EXISTS pedidos_membros (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  usuario_id INTEGER NOT NULL, quantidade INTEGER NOT NULL,
  refil INTEGER DEFAULT 0, prioridade INTEGER DEFAULT 0,
  valor_total REAL NOT NULL, taxa_plataforma REAL NOT NULL, liquido_dono REAL NOT NULL,
  id_discord_usuario TEXT, servidor_alvo_id TEXT, servidor_alvo_nome TEXT,
  status TEXT DEFAULT 'AGUARDANDO_PAGAMENTO', etapa TEXT DEFAULT 'pagamento',
  membros_adicionados INTEGER DEFAULT 0, referencia TEXT,
  criado_em DATETIME DEFAULT CURRENT_TIMESTAMP
);
`);

const cfg = () => db.prepare('SELECT * FROM config_plataforma WHERE id=1').get();
const plat = () => db.prepare('SELECT * FROM carteira_plataforma WHERE id=1').get();

const salvarUsuario = (u) => {
  const ex = db.prepare('SELECT * FROM usuarios WHERE discord_id = ?').get(u.discordId);
  if (ex) { db.prepare('INSERT OR IGNORE INTO carteira_dono_bot (usuario_id) VALUES (?)').run(ex.id); return ex; }
  const info = db.prepare('INSERT INTO usuarios (discord_id,username,avatar,email,is_dono_plataforma) VALUES (?,?,?,?,?)')
    .run(u.discordId, u.username, u.avatar, u.email, u.isDono?1:0);
  const novo = db.prepare('SELECT * FROM usuarios WHERE id = ?').get(info.lastInsertRowid);
  db.prepare('INSERT OR IGNORE INTO carteira_dono_bot (usuario_id) VALUES (?)').run(novo.id);
  return novo;
};

// ✅ CÁLCULO AUTOMÁTICO: 20 = R$1 · refil +35% · prioridade +R$4,50 · taxa 45%
const calcMembros = (qtd, refil, prioridade) => {
  const c = cfg();
  qtd = Math.max(c.membros_min, Math.min(c.membros_max, +qtd||c.membros_min));
  const unitario = c.preco_base_20 / 20;
  let total = +(qtd * unitario).toFixed(2);
  if (refil) total = +(total * (1 + c.refil_pct/100)).toFixed(2);
  if (prioridade) total = +(total + c.valor_prioridade).toFixed(2);
  const taxa = +(total * c.taxa_membros_dono / 100).toFixed(2);
  return { qtd, total, taxa, liquido: +(total - taxa).toFixed(2), unitario: +unitario.toFixed(3) };
};

module.exports = {
  db, cfg, plat, salvarUsuario, calcMembros,
  getLicencaPorId: id => db.prepare('SELECT * FROM licencas WHERE id=?').get(id),
  criarLicenca: l => db.prepare('INSERT INTO licencas VALUES (?,?,?,?,?,?)').run(l.id,l.usuario_id,l.produto_id,l.chave_api,l.validade,'ATIVA'),
  minhasLicencas: uid => db.prepare('SELECT l.*,p.nome,p.tipo_bot FROM licencas l JOIN produtos p ON p.id=l.produto_id WHERE l.usuario_id=?').all(uid),
  minhaCarteiraBot: uid => db.prepare('SELECT * FROM carteira_dono_bot WHERE usuario_id=?').get(uid) || {saldo:0},
  meusPedidos: uid => db.prepare('SELECT * FROM pedidos_membros WHERE usuario_id=? ORDER BY id DESC').all(uid),
  todosPedidos: () => db.prepare('SELECT p.*,u.username,u.discord_id FROM pedidos_membros p JOIN usuarios u ON u.id=p.usuario_id ORDER BY p.id DESC').all(),
  totalUsuarios: () => db.prepare('SELECT COUNT(*) c FROM usuarios WHERE is_dono_plataforma=0').get().c,
  ultimasAtividades: (n=10) => db.prepare('SELECT * FROM transacoes ORDER BY id DESC LIMIT ?').all(n)
};
