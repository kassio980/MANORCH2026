const { DatabaseSync } = require('node:sqlite'); // ✅ NATIVO, NUNCA MAIS ERRO
const path = require('path');
const db = new DatabaseSync(path.join(__dirname, '..', 'db', 'monarch2026.db'));
db.exec('PRAGMA journal_mode = WAL; PRAGMA foreign_keys = ON');

// ==================================================
// TABELAS (com todas as regras que você pediu)
// ==================================================
db.exec(`
-- 1. Usuários (você = dono plataforma + clientes donos de bot)
CREATE TABLE IF NOT EXISTS usuarios (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  discord_id TEXT UNIQUE NOT NULL, username TEXT NOT NULL, avatar TEXT, email TEXT,
  is_dono_plataforma INTEGER DEFAULT 0, -- 1 = VOCÊ (dono MONARCH)
  chave_asaas TEXT, -- cada dono de bot pode colocar a SUA chave Asaas
  criado_em DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 2. Carteira GLOBAL DA PLATAFORMA (seu saldo)
CREATE TABLE IF NOT EXISTS carteira_plataforma (
  id INTEGER PRIMARY KEY CHECK(id=1),
  saldo REAL DEFAULT 0,
  total_vendas REAL DEFAULT 0,
  total_taxas REAL DEFAULT 0,
  total_sacado REAL DEFAULT 0
);
INSERT OR IGNORE INTO carteira_plataforma (id) VALUES (1);

-- 3. Carteira de CADA DONO DE BOT (recebe vendas do seu bot)
CREATE TABLE IF NOT EXISTS carteira_dono_bot (
  usuario_id INTEGER PRIMARY KEY,
  saldo REAL DEFAULT 0, pendente REAL DEFAULT 0, sacado REAL DEFAULT 0,
  FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
);

-- 4. Carteira DOS MEMBROS dentro de CADA BOT (dono do bot NÃO PODE MEXER)
CREATE TABLE IF NOT EXISTS carteira_membro (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  bot_id INTEGER NOT NULL,
  discord_usuario_id TEXT NOT NULL,
  nome TEXT NOT NULL,
  saldo REAL DEFAULT 0,
  UNIQUE(bot_id, discord_usuario_id),
  FOREIGN KEY(bot_id) REFERENCES bots(id)
);

-- 5. Produtos (VOCÊ cadastra no painel dono)
CREATE TABLE IF NOT EXISTS produtos (
  id TEXT PRIMARY KEY,
  nome TEXT NOT NULL,
  tipo_bot TEXT NOT NULL, -- BASICO / INTERMEDIARIO / VIP / PREMIUM
  nivel_api TEXT NOT NULL, -- BASICA / AVANCADA / COMPLETA / ILIMITADA
  preco REAL NOT NULL,
  dias_validade INTEGER NOT NULL,
  badge TEXT, -- MAIS VENDIDO / POPULAR / COMPLETO
  cor TEXT DEFAULT 'roxo',
  descricao TEXT,
  banner TEXT,
  logo TEXT,
  tem_carteira_interna INTEGER DEFAULT 0, -- 1 a partir de INTERMEDIARIO
  ordem INTEGER DEFAULT 0, ativo INTEGER DEFAULT 1
);

-- 6. Licenças compradas pelos clientes
CREATE TABLE IF NOT EXISTS licencas (
  id TEXT PRIMARY KEY,
  usuario_id INTEGER NOT NULL,
  produto_id TEXT NOT NULL,
  chave_api TEXT UNIQUE NOT NULL,
  validade DATETIME NOT NULL,
  status TEXT DEFAULT 'ATIVA',
  criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(usuario_id) REFERENCES usuarios(id),
  FOREIGN KEY(produto_id) REFERENCES produtos(id)
);

-- 7. Bots (1 por licença, integrado com a API comprada)
CREATE TABLE IF NOT EXISTS bots (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  licenca_id TEXT UNIQUE NOT NULL,
  usuario_id INTEGER NOT NULL,
  token_discord TEXT,
  nome_bot TEXT DEFAULT 'MONARCH BOT',
  banner TEXT, logo TEXT, descricao TEXT,
  invite_link TEXT,
  status TEXT DEFAULT 'OFFLINE',
  FOREIGN KEY(licenca_id) REFERENCES licencas(id),
  FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
);

-- 8. Transações GLOBAIS (tudo que passa de dinheiro)
CREATE TABLE IF NOT EXISTS transacoes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tipo TEXT NOT NULL, -- VENDA_PRODUTO / DEPOSITO / SAQUE / TAXA / TRANSFERENCIA
  usuario_id INTEGER, -- quem movimentou
  bot_id INTEGER, -- se foi dentro de um bot
  valor REAL NOT NULL,
  taxa REAL DEFAULT 0, -- 15% vai pra VOCÊ
  liquido REAL DEFAULT 0, -- quem recebe
  destinatario TEXT, -- pra quem foi o dinheiro
  referencia TEXT,
  status TEXT DEFAULT 'CONFIRMADO',
  descricao TEXT,
  criado_em DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 9. Sessões (mantido, sem erro)
CREATE TABLE IF NOT EXISTS sessions (
  sid TEXT PRIMARY KEY, sess TEXT NOT NULL, expired INTEGER NOT NULL
);

-- 10. Configurações GERAIS DA PLATAFORMA (você altera no painel)
CREATE TABLE IF NOT EXISTS config_plataforma (
  id INTEGER PRIMARY KEY CHECK(id=1),
  taxa_saque_membros REAL DEFAULT 15, -- 15% padrão que VOCÊ recebe
  saque_min REAL DEFAULT 5, saque_max REAL DEFAULT 2500,
  deposito_min REAL DEFAULT 5, deposito_max REAL DEFAULT 10000,
  chave_asaas_dono TEXT -- SUA chave Asaas da plataforma
);
INSERT OR IGNORE INTO config_plataforma (id) VALUES (1);
`);

// ==================================================
// FUNÇÕES AUXILIARES
// ==================================================
const cfg = () => db.prepare('SELECT * FROM config_plataforma WHERE id=1').get();
const plat = () => db.prepare('SELECT * FROM carteira_plataforma WHERE id=1').get();

const salvarUsuario = (u) => {
  const ex = db.prepare('SELECT * FROM usuarios WHERE discord_id = ?').get(u.discordId);
  if (ex) {
    db.prepare('INSERT OR IGNORE INTO carteira_dono_bot (usuario_id) VALUES (?)').run(ex.id);
    return ex;
  }
  const info = db.prepare('INSERT INTO usuarios (discord_id,username,avatar,email,is_dono_plataforma) VALUES (?,?,?,?,?)')
    .run(u.discordId, u.username, u.avatar, u.email, u.isDono?1:0);
  const novo = db.prepare('SELECT * FROM usuarios WHERE id = ?').get(info.lastInsertRowid);
  db.prepare('INSERT OR IGNORE INTO carteira_dono_bot (usuario_id) VALUES (?)').run(novo.id);
  return novo;
};

// ✅ FUNÇÃO PRINCIPAL: REGRAS DE DINHEIRO AUTOMÁTICAS
const movimentar = ({ tipo, usuario_id, bot_id, valor, taxa_pct, destinatario, referencia, descricao }) => {
  const tx = db.transaction(() => {
    taxa_pct = taxa_pct ?? cfg().taxa_saque_membros;
    const taxa = +(valor * taxa_pct / 100).toFixed(2);
    const liquido = +(valor - taxa).toFixed(2);

    // 1. TAXA SEMPRE VAI PRO SEU SALDO (PLATAFORMA)
    if (taxa > 0) {
      db.prepare('UPDATE carteira_plataforma SET saldo=saldo+?, total_taxas=total_taxas+? WHERE id=1').run(taxa, taxa);
      db.prepare('INSERT INTO transacoes (tipo,valor,liquido,referencia,descricao) VALUES (?,?,?,?,?)')
        .run('TAXA_PLATAFORMA', taxa, taxa, referencia, `Taxa ${taxa_pct}% → MONARCH`);
    }

    // 2. LÍQUIDO VAI PRO DESTINATÁRIO
    if (destinatario === 'PLATAFORMA') {
      db.prepare('UPDATE carteira_plataforma SET saldo=saldo+?, total_vendas=total_vendas+? WHERE id=1').run(liquido, liquido);
    } else if (destinatario?.startsWith('DONO_BOT:')) {
      const uid = +destinatario.split(':')[1];
      db.prepare('UPDATE carteira_dono_bot SET saldo=saldo+? WHERE usuario_id=?').run(liquido, uid);
    } else if (destinatario?.startsWith('MEMBRO:')) {
      const [, bid, did] = destinatario.split(':');
      db.prepare('INSERT INTO carteira_membro (bot_id,discord_usuario_id,nome,saldo) VALUES (?,?,?,?) ON CONFLICT DO UPDATE SET saldo=saldo+excluded.saldo')
        .run(+bid, did, 'Membro', liquido);
    }

    // 3. Registra transação principal
    return db.prepare('INSERT INTO transacoes (tipo,usuario_id,bot_id,valor,taxa,liquido,destinatario,referencia,descricao) VALUES (?,?,?,?,?,?,?,?,?)')
      .run(tipo, usuario_id||null, bot_id||null, valor, taxa, liquido, destinatario||null, referencia||null, descricao||null);
  });
  return tx();
};

module.exports = {
  db, cfg, plat, salvarUsuario, movimentar,
  getLicencaPorId: (id) => db.prepare('SELECT * FROM licencas WHERE id = ?').get(id),
  criarLicenca: (l) => db.prepare('INSERT INTO licencas (id,usuario_id,produto_id,chave_api,validade) VALUES (?,?,?,?,?)').run(l.id,l.usuario_id,l.produto_id,l.chave_api,l.validade),
  minhasLicencas: (uid) => db.prepare('SELECT l.*,p.nome,p.tipo_bot,p.nivel_api,p.tem_carteira_interna FROM licencas l JOIN produtos p ON p.id=l.produto_id WHERE l.usuario_id=? ORDER BY l.criado_em DESC').all(uid),
  minhaCarteiraBot: (uid) => db.prepare('SELECT * FROM carteira_dono_bot WHERE usuario_id=?').get(uid),
  carteiraMembro: (bid, did) => db.prepare('SELECT * FROM carteira_membro WHERE bot_id=? AND discord_usuario_id=?').get(bid, did),
  totalUsuarios: () => db.prepare('SELECT COUNT(*) c FROM usuarios WHERE is_dono_plataforma=0').get().c,
  totalReceita: () => plat().total_vendas + plat().total_taxas,
  totalVendas: () => db.prepare('SELECT COUNT(*) c FROM transacoes WHERE tipo=?').get('VENDA_PRODUTO').c,
  botsOnline: () => db.prepare('SELECT COUNT(*) c FROM bots WHERE status=?').get('ONLINE').c,
  saquesPendentes: () => db.prepare('SELECT COUNT(*) c FROM transacoes WHERE tipo=? AND status=?').get('SAQUE','PENDENTE').c,
  ultimasAtividades: (n=10) => db.prepare('SELECT * FROM transacoes ORDER BY criado_em DESC LIMIT ?').all(n),
  buscarGlobal: (q) => {
    const like = `%${q}%`;
    return {
      licencas: db.prepare('SELECT * FROM licencas WHERE id LIKE ? LIMIT 5').all(like),
      usuarios: db.prepare('SELECT * FROM usuarios WHERE username LIKE ? OR discord_id LIKE ? LIMIT 5').all(like,like),
      transacoes: db.prepare('SELECT * FROM transacoes WHERE referencia LIKE ? OR descricao LIKE ? LIMIT 5').all(like,like)
    };
  },
  log: (u,a,ip,r='SUCCESS') => {}
};
