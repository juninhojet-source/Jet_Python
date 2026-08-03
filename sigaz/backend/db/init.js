/**
 * Script de inicialização do banco de dados
 * Cria todas as tabelas e popula dados iniciais
 *
 * Uso: node backend/db/init.js
 */
const fs = require('fs');
const path = require('path');
const bcrypt = require('bcryptjs');
const QRCode = require('qrcode');
const db = require('./connection');

console.log('==========================================');
console.log('  SIGAZ - Inicialização do Banco de Dados');
console.log('  Prefeitura Municipal de Barão de Cocais');
console.log('==========================================\n');

// 1. Executar schema
const schemaPath = path.join(__dirname, 'schema.sql');
const schema = fs.readFileSync(schemaPath, 'utf8');
db.exec(schema);
console.log('✓ Schema criado/atualizado');

// 1b. Migração — adicionar coluna username se não existir (bancos antigos)
try {
  const cols = db.prepare('PRAGMA table_info(usuarios)').all();
  const temUsername = cols.some(c => c.name === 'username');
  if (!temUsername) {
    db.exec('ALTER TABLE usuarios ADD COLUMN username TEXT');
    db.exec('CREATE UNIQUE INDEX IF NOT EXISTS idx_usuarios_username ON usuarios(username) WHERE username IS NOT NULL');
    console.log('✓ Coluna username adicionada (migração)');
  }
  // Migração das novas colunas de segurança
  const colNames = cols.map(c => c.name);
  const novas = [
    ['cpf', 'TEXT'],
    ['telefone', 'TEXT'],
    ['deve_trocar_senha', 'INTEGER NOT NULL DEFAULT 0'],
    ['tentativas_falhas', 'INTEGER NOT NULL DEFAULT 0'],
    ['bloqueado_ate', 'DATETIME'],
    ['ultimo_login', 'DATETIME']
  ];
  for (const [nome, tipo] of novas) {
    if (!colNames.includes(nome)) {
      db.exec(`ALTER TABLE usuarios ADD COLUMN ${nome} ${tipo}`);
      console.log(`✓ Coluna ${nome} adicionada (migração de segurança)`);
    }
  }
} catch (err) {
  console.warn('Migração:', err.message);
}

// 1c. Configurações padrão do sistema
const configsPadrao = [
  ['senha_min_caracteres', '8', 'Tamanho mínimo da senha'],
  ['senha_exige_maiuscula', '1', 'Senha deve conter letra maiúscula'],
  ['senha_exige_numero', '1', 'Senha deve conter número'],
  ['senha_exige_especial', '0', 'Senha deve conter caractere especial'],
  ['max_tentativas_login', '5', 'Tentativas antes de bloquear o usuário'],
  ['minutos_bloqueio', '15', 'Minutos de bloqueio após exceder tentativas'],
  ['backup_automatico', '1', 'Habilitar backup automático diário'],
  ['backup_hora', '23', 'Hora do dia para rodar o backup (0-23)'],
  ['backup_retencao_dias', '30', 'Dias de retenção dos backups'],
  ['municipio_nome', 'Barão de Cocais', 'Nome do município'],
  ['municipio_uf', 'MG', 'UF do município'],
  ['orgao_nome', 'Secretaria Municipal de Saúde', 'Nome do órgão responsável'],
  ['ti_telefone', '(31) 3837-7661', 'Telefone do Departamento de TI'],
  ['ti_nome', 'Departamento de Informática e Tecnologia', 'Nome do Departamento de TI']
];
const upsertConfig = db.prepare(`
  INSERT INTO configuracoes (chave, valor, descricao) VALUES (?, ?, ?)
  ON CONFLICT(chave) DO NOTHING
`);
for (const [k, v, d] of configsPadrao) {
  upsertConfig.run(k, v, d);
}

// 1d. Bairros oficiais de Barão de Cocais (fornecidos pela PMBC)
const bairrosOficiais = [
  // [nome, eh_distrito]
  ['Água Limpa', 1],
  ['Bananal', 1],
  ['Boa Esperança', 0],
  ['Boa Vista', 1],
  ['Braz Molina', 0],
  ['Brumadinho', 1],
  ['Campo Grande', 1],
  ['Cantinho do Céu', 0],
  ['Capim Cheiroso', 0],
  ['Carapuça I', 1],
  ['Carapuça II', 1],
  ['Castro', 0],
  ['Centro', 0],
  ['Chacará I', 0],
  ['Chacará II', 0],
  ['Chacará III', 0],
  ['Cidade Nova', 0],
  ['Cocais', 1],
  ['Córrego da Onça', 1],
  ['Dois Irmãos', 0],
  ['Égas', 1],
  ['Garcia I', 0],
  ['Garcia II', 0],
  ['Gongo', 1],
  ['Irmãos Aleme', 0],
  ['Itajuru "Henrique Roque"', 1],
  ['João Paulo', 0],
  ['Lagoa', 0],
  ['Leão XIII', 0],
  ['Nacional', 0],
  ['Padre Trombet', 0],
  ['Ponte Paixão', 0],
  ['Progresso', 0],
  ['Rezende', 0],
  ['Sagrada Família', 0],
  ['Santa Cruz', 0],
  ['Santo Antônio', 0],
  ['São Benedito', 0],
  ['São Gonçalo do Rio Acima', 1],
  ['São João Batista', 0],
  ['São José', 0],
  ['São Judas Tadeu', 0],
  ['São Luiz', 0],
  ['São Miguel', 0],
  ['Socorro', 0],            // comunidade
  ['Tambor', 1],
  ['Três Cachoeiras', 1],
  ['Três Moinhos', 0],
  ['Varginha I', 0],
  ['Varginha II', 0],
  ['Vila Brandão', 0],
  ['Vila da Sempre', 0],
  ['Vila São Geraldo', 0],
  ['Viúva', 0]
];
const insertBairro = db.prepare(`
  INSERT INTO bairros (nome, eh_distrito, ordem) VALUES (?, ?, ?)
  ON CONFLICT(nome) DO NOTHING
`);
bairrosOficiais.forEach((b, i) => insertBairro.run(b[0], b[1], i));
const totalBairros = db.prepare('SELECT COUNT(*) AS t FROM bairros').get().t;
console.log(`✓ Bairros oficiais (${totalBairros} cadastrados)`);

// 1e. Migração: adicionar lat/lng/geocoded_em em bancos antigos
try {
  const colsBairros = db.prepare('PRAGMA table_info(bairros)').all().map(c => c.name);
  if (!colsBairros.includes('latitude')) {
    db.exec('ALTER TABLE bairros ADD COLUMN latitude REAL');
    console.log('✓ Coluna bairros.latitude adicionada');
  }
  if (!colsBairros.includes('longitude')) {
    db.exec('ALTER TABLE bairros ADD COLUMN longitude REAL');
    console.log('✓ Coluna bairros.longitude adicionada');
  }
  if (!colsBairros.includes('geocoded_em')) {
    db.exec('ALTER TABLE bairros ADD COLUMN geocoded_em DATETIME');
    console.log('✓ Coluna bairros.geocoded_em adicionada');
  }
} catch (err) {
  console.warn('Migração bairros:', err.message);
}

// 1f. Seed de coordenadas iniciais (bairros que já mapeamos manualmente)
const coordsConhecidas = {
  'Centro':                  { lat: -19.9444, lng: -43.4912 },
  'São José':                { lat: -19.9398, lng: -43.4863 },
  'Cocais':                  { lat: -19.9472, lng: -43.5012 },
  'São Bento':               { lat: -19.9358, lng: -43.4955 },
  'Cantinho do Céu':         { lat: -19.9430, lng: -43.4885 },
  'Cidade Nova':             { lat: -19.9415, lng: -43.4815 },
  'Sagrada Família':         { lat: -19.9528, lng: -43.4965 },
  'Lagoa':                   { lat: -19.9501, lng: -43.5050 },
  'Santo Antônio':           { lat: -19.9602, lng: -43.4878 },
  'Rezende':                 { lat: -19.9485, lng: -43.4920 },
  'Progresso':               { lat: -19.9410, lng: -43.5005 },
  'Nacional':                { lat: -19.9460, lng: -43.5078 }
};
const updCoord = db.prepare(`
  UPDATE bairros SET latitude = ?, longitude = ?, geocoded_em = CURRENT_TIMESTAMP
  WHERE nome = ? AND (latitude IS NULL OR longitude IS NULL)
`);
let cAplic = 0;
for (const [nome, c] of Object.entries(coordsConhecidas)) {
  const r = updCoord.run(c.lat, c.lng, nome);
  if (r.changes > 0) cAplic++;
}
if (cAplic > 0) console.log(`✓ Coordenadas iniciais aplicadas em ${cAplic} bairros`);

// 1g. Migração: remover CHECK constraint antigo da tabela estoque_itens
// (versões anteriores limitavam as categorias a 6 valores fixos)
try {
  const ddl = db.prepare("SELECT sql FROM sqlite_master WHERE name = 'estoque_itens'").get();
  if (ddl && ddl.sql && ddl.sql.includes("CHECK") && ddl.sql.includes("categoria")) {
    db.exec(`
      BEGIN;
      CREATE TABLE estoque_itens_new (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        nome            TEXT NOT NULL,
        categoria       TEXT,
        unidade         TEXT DEFAULT 'unidade',
        estoque_minimo  INTEGER DEFAULT 0,
        observacoes     TEXT,
        ativo           INTEGER DEFAULT 1,
        criado_em       DATETIME DEFAULT CURRENT_TIMESTAMP
      );
      INSERT INTO estoque_itens_new (id, nome, categoria, unidade, estoque_minimo, observacoes, ativo, criado_em)
        SELECT id, nome, categoria, unidade, estoque_minimo, observacoes, ativo, criado_em FROM estoque_itens;
      DROP TABLE estoque_itens;
      ALTER TABLE estoque_itens_new RENAME TO estoque_itens;
      COMMIT;
    `);
    console.log('✓ Migração de estoque_itens: CHECK constraint removido');
  }
} catch (err) {
  try { db.exec('ROLLBACK'); } catch(_){}
  console.warn('Migração estoque_itens:', err.message);
}

// 1h. Migração: remover CHECK constraints de status_reprodutivo e habitacao na tabela animais.
// Versões anteriores limitavam os valores; agora precisam aceitar novos itens
// (ex.: "Ovário remanescente" no status reprodutivo, "Colônia" na habitação).
try {
  const ddl = db.prepare("SELECT sql FROM sqlite_master WHERE name = 'animais'").get();
  if (ddl && ddl.sql && ddl.sql.includes("status_reprodutivo  TEXT CHECK")) {
    db.exec('BEGIN');
    db.exec(`
      CREATE TABLE animais_new (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo              TEXT    NOT NULL UNIQUE,
        nome                TEXT    NOT NULL,
        especie             TEXT    NOT NULL,
        raca                TEXT,
        sexo                TEXT,
        data_nascimento     DATE,
        idade_aproximada    TEXT,
        pelagem             TEXT,
        porte               TEXT,
        peso_kg             REAL,
        status_reprodutivo  TEXT,
        habitacao           TEXT,
        microchip           TEXT,
        numero_identificacao TEXT,
        foto                TEXT,
        qrcode              TEXT,
        responsavel_id      INTEGER,
        observacoes         TEXT,
        ativo               INTEGER NOT NULL DEFAULT 1,
        criado_em           DATETIME DEFAULT CURRENT_TIMESTAMP,
        atualizado_em       DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (responsavel_id) REFERENCES responsaveis(id) ON DELETE SET NULL
      );
      INSERT INTO animais_new SELECT
        id, codigo, nome, especie, raca, sexo, data_nascimento, idade_aproximada,
        pelagem, porte, peso_kg, status_reprodutivo, habitacao, microchip,
        numero_identificacao, foto, qrcode, responsavel_id, observacoes, ativo,
        criado_em, atualizado_em
      FROM animais;
      DROP TABLE animais;
      ALTER TABLE animais_new RENAME TO animais;
      CREATE INDEX IF NOT EXISTS idx_animais_codigo ON animais(codigo);
      CREATE INDEX IF NOT EXISTS idx_animais_responsavel ON animais(responsavel_id);
      CREATE INDEX IF NOT EXISTS idx_animais_especie ON animais(especie);
    `);
    db.exec('COMMIT');
    console.log('✓ Migração de animais: CHECKs de status_reprodutivo e habitacao removidos');
  }
} catch (err) {
  try { db.exec('ROLLBACK'); } catch(_){}
  console.warn('Migração animais:', err.message);
}

// 1i. Migração: adicionar coluna 'fabricante' em vermifugacoes e ectoparasitarios
// (necessário para a importação que traz fabricante de cada ação sanitária)
try {
  const colsVerm = db.prepare("PRAGMA table_info(vermifugacoes)").all();
  if (!colsVerm.some(c => c.name === 'fabricante')) {
    db.exec("ALTER TABLE vermifugacoes ADD COLUMN fabricante TEXT");
    console.log('✓ Migração: coluna fabricante adicionada em vermifugacoes');
  }
  const colsEcto = db.prepare("PRAGMA table_info(ectoparasitarios)").all();
  if (!colsEcto.some(c => c.name === 'fabricante')) {
    db.exec("ALTER TABLE ectoparasitarios ADD COLUMN fabricante TEXT");
    console.log('✓ Migração: coluna fabricante adicionada em ectoparasitarios');
  }
} catch (err) {
  console.warn('Migração fabricante saúde:', err.message);
}

// 2. Criar usuário admin padrão se não existir
const adminExists = db.prepare(
  'SELECT id FROM usuarios WHERE email = ? OR username = ?'
).get('admin@bcocais.mg.gov.br', 'admin');

if (!adminExists) {
  const senhaHash = bcrypt.hashSync('admin123', 10);
  db.prepare(`
    INSERT INTO usuarios (nome, username, email, senha_hash, perfil, ativo, deve_trocar_senha)
    VALUES (?, ?, ?, ?, ?, 1, 1)
  `).run('Administrador', 'admin', 'admin@bcocais.mg.gov.br', senhaHash, 'admin');
  console.log('✓ Usuário admin criado');
  console.log('  Usuário: admin   ou   admin@bcocais.mg.gov.br');
  console.log('  Senha:   admin123  (você será forçado a trocar no primeiro login)');
} else {
  // Garantir que tem username
  db.prepare('UPDATE usuarios SET username = COALESCE(username, ?) WHERE id = ?').run('admin', adminExists.id);
  console.log('✓ Usuário admin já existe');
}

// 3. Usuário veterinário de exemplo
const vetExists = db.prepare(
  'SELECT id FROM usuarios WHERE email = ? OR username = ?'
).get('veterinario@bcocais.mg.gov.br', 'veterinario');
if (!vetExists) {
  const senhaHash = bcrypt.hashSync('vet123', 10);
  db.prepare(`
    INSERT INTO usuarios (nome, username, email, senha_hash, perfil, ativo, deve_trocar_senha)
    VALUES (?, ?, ?, ?, ?, 1, 1)
  `).run('Dr. Médico Veterinário', 'veterinario', 'veterinario@bcocais.mg.gov.br', senhaHash, 'veterinario');
  console.log('✓ Usuário veterinário criado');
} else {
  db.prepare('UPDATE usuarios SET username = COALESCE(username, ?) WHERE id = ?').run('veterinario', vetExists.id);
}

// 4. Dados de exemplo (apenas se a base estiver vazia)
async function seedExemplo() {
  const totalResp = db.prepare('SELECT COUNT(*) as t FROM responsaveis').get().t;
  if (totalResp !== 0) return;

  console.log('\nInserindo dados de exemplo...');

  const insertResp = db.prepare(`
    INSERT INTO responsaveis (nome, cpf, telefone, email, endereco, numero, bairro, cep)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
  `);

  const r1 = insertResp.run('João da Silva', '39053344705', '(31) 99999-9999', 'joao@email.com', 'Rua das Flores', '100', 'Centro', '35970-000');
  const r2 = insertResp.run('Maria Souza', '52998224725', '(31) 98888-8888', 'maria@email.com', 'Av. Principal', '250', 'São José', '35970-100');
  const r3 = insertResp.run('Pedro Oliveira', '11144477735', '(31) 97777-7777', null, 'Rua do Sol', '45', 'Cocaes', '35970-200');

  // Gerar QR Codes para os animais do seed (URL aponta para localhost; ajustar em produção)
  const baseUrl = 'http://localhost:3000';
  const qr = async (codigo) => await QRCode.toDataURL(`${baseUrl}/consulta.html?codigo=${codigo}`, { width: 200, margin: 1 });

  const insertAnimal = db.prepare(`
    INSERT INTO animais (codigo, nome, especie, raca, sexo, idade_aproximada, porte,
                         status_reprodutivo, habitacao, responsavel_id, observacoes, qrcode)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `);

  const a1 = insertAnimal.run('ANI-2026-0001', 'Thor', 'Canino', 'SRD', 'Macho', '4 anos', 'Grande', 'Castrado(a)', 'Domiciliado', r1.lastInsertRowid, 'Animal dócil', await qr('ANI-2026-0001'));
  const a2 = insertAnimal.run('ANI-2026-0002', 'Luna', 'Felino', 'SRD', 'Fêmea', '2 anos', 'Pequeno', 'Castrado(a)', 'Domiciliado', r2.lastInsertRowid, null, await qr('ANI-2026-0002'));
  const a3 = insertAnimal.run('ANI-2026-0003', 'Rex', 'Canino', 'Pastor Alemão', 'Macho', '6 anos', 'Grande', 'Inteiro(a)', 'Domiciliado', r1.lastInsertRowid, null, await qr('ANI-2026-0003'));
  const a4 = insertAnimal.run('ANI-2026-0004', 'Mel', 'Canino', 'Poodle', 'Fêmea', '3 anos', 'Pequeno', 'Castrado(a)', 'Domiciliado', r3.lastInsertRowid, null, await qr('ANI-2026-0004'));

  // Vacinas de exemplo
  const insertVacina = db.prepare(`
    INSERT INTO vacinas (animal_id, vacina, fabricante, lote, data_aplicacao, data_validade, proxima_aplicacao, responsavel_aplicacao)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
  `);
  insertVacina.run(a1.lastInsertRowid, 'Raiva', 'Zoetis', 'L2024-A', '2026-01-15', '2027-01-15', '2027-01-15', 'Dr. Veterinário');
  insertVacina.run(a1.lastInsertRowid, 'V10', 'MSD', 'L2024-B', '2026-02-10', '2027-02-10', '2027-02-10', 'Dr. Veterinário');
  insertVacina.run(a2.lastInsertRowid, 'V4', 'Zoetis', 'L2024-C', '2026-03-05', '2027-03-05', '2027-03-05', 'Dr. Veterinário');

  // Zoonose de exemplo
  const insertZoo = db.prepare(`
    INSERT INTO zoonoses (animal_id, zoonose, data_notificacao, status_investigacao, diagnostico, bairro_ocorrencia, observacoes)
    VALUES (?, ?, ?, ?, ?, ?, ?)
  `);
  insertZoo.run(a3.lastInsertRowid, 'Leishmaniose', '2026-04-12', 'Em análise', 'Aguardando', 'Centro', 'Aguardando resultado do exame');

  console.log('✓ Dados de exemplo inseridos');
  console.log(`  - ${3} responsáveis`);
  console.log(`  - ${4} animais (com QR Code)`);
  console.log(`  - ${3} vacinas`);
  console.log(`  - ${1} ocorrência de zoonose`);
}

(async () => {
  await seedExemplo();

  console.log('\n==========================================');
  console.log('  Inicialização concluída com sucesso!');
  console.log('==========================================');
  console.log('\nPróximos passos:');
  console.log('  1. npm start');
  console.log('  2. Abrir http://localhost:3000');
  console.log('  3. Login: admin@bcocais.mg.gov.br / admin123\n');

  db.close();
})();
