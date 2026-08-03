/**
 * Rotas de Administração: Backup e Restauração
 * SIGAZ - PMBC
 * Restrito ao perfil admin.
 */
const express = require('express');
const fs = require('fs');
const path = require('path');
const { DatabaseSync } = require('node:sqlite');
const db = require('../db/connection');
const { autenticar, autorizar } = require('../middleware/auth');
const { registrarLog } = require('../utils/logger');

const router = express.Router();
router.use(autenticar);
router.use(autorizar('admin', 'ti'));

/**
 * POST /api/admin/normalizar-dados
 * Corrige retroativamente valores de status reprodutivo e habitação que
 * foram importados fora do padrão (ex.: "Castrado" em vez de "Castrado(a)").
 * Resolve o caso dos 103 animais castrados que não eram contabilizados.
 *
 * Com ?simular=1 (ou body { simular: true }) apenas mostra o que mudaria,
 * sem gravar.
 */
router.post('/normalizar-dados', (req, res) => {
  const simular = req.body && req.body.simular;

  // Mapeamentos de normalização (de => para)
  const mapaStatus = {
    'castrado': 'Castrado(a)', 'castrada': 'Castrado(a)', 'CASTRADO': 'Castrado(a)',
    'Castrado': 'Castrado(a)', 'Castrada': 'Castrado(a)', 'castrado(a)': 'Castrado(a)',
    'inteiro': 'Inteiro(a)', 'inteira': 'Inteiro(a)', 'Inteiro': 'Inteiro(a)', 'Inteira': 'Inteiro(a)',
    'rufiao': 'Rufião', 'Rufiao': 'Rufião',
    'criptorquido': 'Criptorquida', 'criptorquida': 'Criptorquida',
    'ovario remanescente': 'Ovário remanescente', 'Ovario remanescente': 'Ovário remanescente',
    'ovário remanescente': 'Ovário remanescente'
  };
  const mapaHabitacao = {
    'domiciliado': 'Domiciliado', 'Domiciliado ': 'Domiciliado',
    'semidomiciliado': 'Semidomiciliado', 'semi-domiciliado': 'Semidomiciliado',
    'comunitario': 'Comunitário', 'comunitário': 'Comunitário',
    'colonia': 'Colônia', 'colônia': 'Colônia',
    'errante': 'Errante'
  };

  const mudancas = { status_reprodutivo: [], habitacao: [] };

  // Levanta os animais cujo valor não está no padrão
  const animais = db.prepare('SELECT id, codigo, nome, status_reprodutivo, habitacao FROM animais').all();
  const padroesStatus = ['Castrado(a)','Inteiro(a)','Ovário remanescente','Rufião','Criptorquida', null, ''];
  const padroesHab = ['Domiciliado','Semidomiciliado','Comunitário','Colônia','Errante', null, ''];

  for (const a of animais) {
    // Status reprodutivo
    if (a.status_reprodutivo && !padroesStatus.includes(a.status_reprodutivo)) {
      const novo = mapaStatus[a.status_reprodutivo] || mapaStatus[a.status_reprodutivo.trim().toLowerCase()];
      if (novo && novo !== a.status_reprodutivo) {
        mudancas.status_reprodutivo.push({ id: a.id, codigo: a.codigo, de: a.status_reprodutivo, para: novo });
      }
    }
    // Habitação
    if (a.habitacao && !padroesHab.includes(a.habitacao)) {
      const novo = mapaHabitacao[a.habitacao] || mapaHabitacao[a.habitacao.trim().toLowerCase()];
      if (novo && novo !== a.habitacao) {
        mudancas.habitacao.push({ id: a.id, codigo: a.codigo, de: a.habitacao, para: novo });
      }
    }
  }

  const totalStatus = mudancas.status_reprodutivo.length;
  const totalHab = mudancas.habitacao.length;

  if (simular) {
    return res.json({
      simulacao: true,
      status_reprodutivo_a_corrigir: totalStatus,
      habitacao_a_corrigir: totalHab,
      amostra_status: mudancas.status_reprodutivo.slice(0, 20),
      amostra_habitacao: mudancas.habitacao.slice(0, 20)
    });
  }

  // Aplica
  try {
    db.exec('BEGIN');
    const updStatus = db.prepare('UPDATE animais SET status_reprodutivo = ? WHERE id = ?');
    const updHab = db.prepare('UPDATE animais SET habitacao = ? WHERE id = ?');
    for (const m of mudancas.status_reprodutivo) updStatus.run(m.para, m.id);
    for (const m of mudancas.habitacao) updHab.run(m.para, m.id);
    db.exec('COMMIT');
  } catch (err) {
    try { db.exec('ROLLBACK'); } catch(_){}
    return res.status(500).json({ erro: 'Erro ao normalizar: ' + err.message });
  }

  registrarLog(req, 'NORMALIZAR_DADOS', 'animais', null,
    { status_corrigidos: totalStatus, habitacao_corrigidos: totalHab });

  res.json({
    ok: true,
    status_reprodutivo_corrigidos: totalStatus,
    habitacao_corrigidos: totalHab
  });
});

// Pasta onde ficam os backups locais do servidor
const BACKUPS_DIR = path.join(__dirname, '..', 'backups');
if (!fs.existsSync(BACKUPS_DIR)) {
  fs.mkdirSync(BACKUPS_DIR, { recursive: true });
}

/**
 * Gera um nome de backup com timestamp
 */
function nomeBackup(prefixo = 'sigaz') {
  const agora = new Date();
  const stamp = agora.toISOString().replace(/[:.]/g, '-').substring(0, 19);
  return `${prefixo}_${stamp}.db`;
}

/**
 * Validar se um arquivo é um SQLite válido
 * Verifica o header mágico nos primeiros 16 bytes: "SQLite format 3\0"
 */
function ehSqliteValido(filePath) {
  try {
    const fd = fs.openSync(filePath, 'r');
    const buf = Buffer.alloc(16);
    fs.readSync(fd, buf, 0, 16, 0);
    fs.closeSync(fd);
    return buf.toString('utf8', 0, 15) === 'SQLite format 3';
  } catch {
    return false;
  }
}

/**
 * Verifica se o banco tem a estrutura básica esperada do SIGAZ
 */
function ehBancoSigaz(filePath) {
  let temp;
  try {
    temp = new DatabaseSync(filePath, { readOnly: true });
    const r = temp.prepare(`SELECT name FROM sqlite_master WHERE type='table' AND name IN ('usuarios','animais','responsaveis')`).all();
    return r.length === 3;
  } catch {
    return false;
  } finally {
    if (temp) {
      try { temp.close(); } catch {}
    }
  }
}

/**
 * GET /api/admin/backup
 * Faz download do banco atual (cópia consistente via VACUUM INTO)
 */
router.get('/backup', (req, res) => {
  const tmpPath = path.join(BACKUPS_DIR, `_download_temp_${Date.now()}.db`);

  try {
    // VACUUM INTO cria uma cópia consistente mesmo com o sistema rodando
    db.exec(`VACUUM INTO '${tmpPath.replace(/'/g, "''")}'`);
  } catch (err) {
    return res.status(500).json({ erro: 'Erro ao gerar backup: ' + err.message });
  }

  const nome = nomeBackup('sigaz_backup');
  const stat = fs.statSync(tmpPath);

  registrarLog(req, 'BACKUP_DOWNLOAD', 'sistema', null, { tamanho_bytes: stat.size });

  res.setHeader('Content-Type', 'application/octet-stream');
  res.setHeader('Content-Disposition', `attachment; filename="${nome}"`);
  res.setHeader('Content-Length', stat.size);

  const stream = fs.createReadStream(tmpPath);
  stream.pipe(res);
  stream.on('close', () => {
    try { fs.unlinkSync(tmpPath); } catch {}
  });
});

/**
 * POST /api/admin/backups/criar
 * Cria um backup localmente no servidor (pasta backend/backups)
 */
router.post('/backups/criar', (req, res) => {
  const nome = nomeBackup('sigaz_backup');
  const destino = path.join(BACKUPS_DIR, nome);

  try {
    db.exec(`VACUUM INTO '${destino.replace(/'/g, "''")}'`);
    const stat = fs.statSync(destino);

    registrarLog(req, 'BACKUP_CRIAR', 'sistema', null, { arquivo: nome, tamanho_bytes: stat.size });

    res.status(201).json({
      ok: true,
      arquivo: nome,
      tamanho_bytes: stat.size,
      criado_em: new Date().toISOString()
    });
  } catch (err) {
    res.status(500).json({ erro: 'Erro ao criar backup: ' + err.message });
  }
});

/**
 * GET /api/admin/backups
 * Lista backups disponíveis no servidor
 */
router.get('/backups', (req, res) => {
  try {
    const arquivos = fs.readdirSync(BACKUPS_DIR)
      .filter(f => f.endsWith('.db') && !f.startsWith('_'))
      .map(f => {
        const p = path.join(BACKUPS_DIR, f);
        const stat = fs.statSync(p);
        return {
          arquivo: f,
          tamanho_bytes: stat.size,
          criado_em: stat.mtime.toISOString()
        };
      })
      .sort((a, b) => b.criado_em.localeCompare(a.criado_em));

    res.json({ dados: arquivos, total: arquivos.length });
  } catch (err) {
    res.status(500).json({ erro: err.message });
  }
});

/**
 * GET /api/admin/backups/:arquivo/download
 * Baixa um backup específico salvo no servidor
 */
router.get('/backups/:arquivo/download', (req, res) => {
  const arquivo = req.params.arquivo;
  if (!/^[\w\-.]+\.db$/.test(arquivo)) {
    return res.status(400).json({ erro: 'Nome de arquivo inválido' });
  }
  const fullPath = path.join(BACKUPS_DIR, arquivo);
  if (!fs.existsSync(fullPath)) {
    return res.status(404).json({ erro: 'Backup não encontrado' });
  }

  registrarLog(req, 'BACKUP_DOWNLOAD_LOCAL', 'sistema', null, { arquivo });

  res.download(fullPath, arquivo);
});

/**
 * DELETE /api/admin/backups/:arquivo
 */
router.delete('/backups/:arquivo', (req, res) => {
  const arquivo = req.params.arquivo;
  if (!/^[\w\-.]+\.db$/.test(arquivo)) {
    return res.status(400).json({ erro: 'Nome de arquivo inválido' });
  }
  const fullPath = path.join(BACKUPS_DIR, arquivo);
  if (!fs.existsSync(fullPath)) {
    return res.status(404).json({ erro: 'Backup não encontrado' });
  }
  try {
    fs.unlinkSync(fullPath);
    registrarLog(req, 'BACKUP_EXCLUIR', 'sistema', null, { arquivo });
    res.json({ ok: true });
  } catch (err) {
    res.status(500).json({ erro: err.message });
  }
});

/**
 * POST /api/admin/restore
 * Recebe um banco em base64 no body e restaura.
 * Body: { conteudo_base64: "...", confirmacao: "RESTAURAR" }
 */
router.post('/restore', (req, res) => {
  const { conteudo_base64, confirmacao } = req.body;

  if (confirmacao !== 'RESTAURAR') {
    return res.status(400).json({ erro: 'Confirmação inválida. Digite "RESTAURAR" para prosseguir.' });
  }
  if (!conteudo_base64 || typeof conteudo_base64 !== 'string') {
    return res.status(400).json({ erro: 'Arquivo não enviado' });
  }

  // Decodificar base64
  let buffer;
  try {
    buffer = Buffer.from(conteudo_base64, 'base64');
  } catch (err) {
    return res.status(400).json({ erro: 'Arquivo inválido (base64)' });
  }

  if (buffer.length < 100) {
    return res.status(400).json({ erro: 'Arquivo muito pequeno para ser um banco SQLite' });
  }

  // Salvar em arquivo temporário
  const tmpPath = path.join(BACKUPS_DIR, `_restore_temp_${Date.now()}.db`);
  fs.writeFileSync(tmpPath, buffer);

  // Validar
  if (!ehSqliteValido(tmpPath)) {
    fs.unlinkSync(tmpPath);
    return res.status(400).json({ erro: 'O arquivo enviado não é um banco SQLite válido.' });
  }
  if (!ehBancoSigaz(tmpPath)) {
    fs.unlinkSync(tmpPath);
    return res.status(400).json({ erro: 'O arquivo enviado não parece ser um banco do SIGAZ (faltam tabelas esperadas).' });
  }

  try {
    // Antes de substituir, faz um backup automático do estado atual
    const backupSeguranca = path.join(BACKUPS_DIR, `sigaz_pre_restore_${Date.now()}.db`);
    try {
      db.exec(`VACUUM INTO '${backupSeguranca.replace(/'/g, "''")}'`);
    } catch (e) {
      // Se falhar, tenta cópia direta
      try { fs.copyFileSync(db.caminho, backupSeguranca); } catch {}
    }

    // Fechar conexão atual
    db.close();

    // Substituir arquivo do banco
    fs.copyFileSync(tmpPath, db.caminho);

    // Remover arquivos auxiliares do WAL antigos (podem ter dados conflitantes do banco anterior)
    const walPath = db.caminho + '-wal';
    const shmPath = db.caminho + '-shm';
    try { if (fs.existsSync(walPath)) fs.unlinkSync(walPath); } catch {}
    try { if (fs.existsSync(shmPath)) fs.unlinkSync(shmPath); } catch {}

    // Limpar arquivo temporário do upload
    fs.unlinkSync(tmpPath);

    // Reabrir conexão (no novo banco)
    db.reconectar();

    registrarLog(req, 'RESTAURAR', 'sistema', null, {
      tamanho_bytes: buffer.length,
      backup_seguranca: path.basename(backupSeguranca)
    });

    res.json({
      ok: true,
      mensagem: 'Banco restaurado com sucesso.',
      backup_seguranca: path.basename(backupSeguranca),
      aviso: 'Faça logout e login novamente para usar o sistema com o banco restaurado.'
    });
  } catch (err) {
    // Tentar restaurar o estado anterior se possível
    try { db.reconectar(); } catch {}
    res.status(500).json({ erro: 'Erro ao restaurar: ' + err.message });
  }
});

/**
 * GET /api/admin/config — Lista todas as configurações
 */
router.get('/config', (req, res) => {
  const dados = db.prepare('SELECT chave, valor, descricao, atualizado_em FROM configuracoes ORDER BY chave').all();
  res.json({ dados });
});

/**
 * PUT /api/admin/config — Atualiza configurações em lote
 * Body: { configs: [{chave, valor}, ...] }
 */
router.put('/config', (req, res) => {
  const { configs } = req.body;
  if (!Array.isArray(configs)) {
    return res.status(400).json({ erro: 'Parâmetro "configs" deve ser uma lista' });
  }

  const stmt = db.prepare(`
    UPDATE configuracoes SET valor = ?, atualizado_em = CURRENT_TIMESTAMP WHERE chave = ?
  `);
  let atualizadas = 0;
  for (const c of configs) {
    if (c.chave && c.valor !== undefined) {
      const r = stmt.run(String(c.valor), c.chave);
      if (r.changes > 0) atualizadas++;
    }
  }

  registrarLog(req, 'ATUALIZAR_CONFIG', 'sistema', null, { atualizadas, configs });
  res.json({ ok: true, atualizadas });
});

/**
 * POST /api/admin/backup-agora — Força um backup automático imediato
 */
router.post('/backup-agora', (req, res) => {
  try {
    const { backupAgora } = require('../utils/scheduler');
    const ok = backupAgora();
    if (ok) {
      res.json({ ok: true, mensagem: 'Backup executado com sucesso.' });
    } else {
      res.status(500).json({ erro: 'Falha ao gerar backup. Verifique o console do servidor.' });
    }
  } catch (err) {
    res.status(500).json({ erro: err.message });
  }
});

module.exports = router;
