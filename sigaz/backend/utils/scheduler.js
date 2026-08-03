/**
 * Agendador interno de backup automático
 * SIGAZ - PMBC
 *
 * Roda dentro do próprio processo Node.js. Verifica a cada 10 minutos
 * se chegou a hora configurada para o backup do dia. Mantém retenção
 * configurada e exclui backups antigos automaticamente.
 */
const fs = require('fs');
const path = require('path');
const db = require('../db/connection');

const BACKUPS_DIR = path.join(__dirname, '..', 'backups');

function getConfig(chave, padrao) {
  try {
    const r = db.prepare('SELECT valor FROM configuracoes WHERE chave = ?').get(chave);
    return r ? r.valor : padrao;
  } catch {
    return padrao;
  }
}

// Garantir que a pasta de backups exista
if (!fs.existsSync(BACKUPS_DIR)) {
  fs.mkdirSync(BACKUPS_DIR, { recursive: true });
}

let ultimaDataExecucao = null; // YYYY-MM-DD da última execução

function nomeBackupAutomatico() {
  const stamp = new Date().toISOString().replace(/[:.]/g, '-').substring(0, 19);
  return `sigaz_auto_${stamp}.db`;
}

function executarBackup() {
  const destino = path.join(BACKUPS_DIR, nomeBackupAutomatico());
  try {
    db.exec(`VACUUM INTO '${destino.replace(/'/g, "''")}'`);
    const stat = fs.statSync(destino);
    console.log(`[BACKUP-AUTO] ✓ Backup criado: ${path.basename(destino)} (${(stat.size / 1024).toFixed(1)} KB)`);

    // Registrar no log de auditoria
    try {
      db.prepare(`
        INSERT INTO logs (usuario_id, acao, entidade, detalhes, ip)
        VALUES (NULL, 'BACKUP_AUTO', 'sistema', ?, 'localhost')
      `).run(JSON.stringify({ arquivo: path.basename(destino), tamanho_bytes: stat.size }));
    } catch {}

    return true;
  } catch (err) {
    console.error('[BACKUP-AUTO] ✗ Erro:', err.message);
    try {
      db.prepare(`
        INSERT INTO logs (usuario_id, acao, entidade, detalhes, ip)
        VALUES (NULL, 'BACKUP_AUTO_FALHA', 'sistema', ?, 'localhost')
      `).run(JSON.stringify({ erro: err.message }));
    } catch {}
    return false;
  }
}

function aplicarRetencao() {
  const dias = parseInt(getConfig('backup_retencao_dias', '30'));
  const limite = Date.now() - dias * 24 * 60 * 60 * 1000;

  try {
    const arquivos = fs.readdirSync(BACKUPS_DIR)
      .filter(f => f.startsWith('sigaz_auto_') && f.endsWith('.db'));

    let removidos = 0;
    for (const f of arquivos) {
      const full = path.join(BACKUPS_DIR, f);
      const stat = fs.statSync(full);
      if (stat.mtime.getTime() < limite) {
        fs.unlinkSync(full);
        removidos++;
      }
    }
    if (removidos > 0) {
      console.log(`[BACKUP-AUTO] ✓ Retenção: ${removidos} backup(s) antigo(s) removido(s)`);
    }
  } catch (err) {
    console.error('[BACKUP-AUTO] Erro na retenção:', err.message);
  }
}

function tick() {
  try {
    const habilitado = getConfig('backup_automatico', '1') === '1';
    if (!habilitado) return;

    const horaBackup = parseInt(getConfig('backup_hora', '23'));
    const agora = new Date();
    const dataHoje = agora.toISOString().substring(0, 10);

    // Já executou hoje? Pula.
    if (ultimaDataExecucao === dataHoje) return;

    // Chegou na hora?
    if (agora.getHours() >= horaBackup) {
      console.log('[BACKUP-AUTO] Iniciando backup diário...');
      const sucesso = executarBackup();
      if (sucesso) {
        ultimaDataExecucao = dataHoje;
        aplicarRetencao();
      }
    }
  } catch (err) {
    console.error('[BACKUP-AUTO] Tick error:', err.message);
  }
}

/**
 * Inicia o agendador. Roda a cada 10 minutos.
 */
function iniciarAgendador() {
  console.log('[BACKUP-AUTO] Agendador iniciado.');
  // Executar uma checagem inicial após 30s (dá tempo do servidor estabilizar)
  setTimeout(tick, 30000);
  // E depois a cada 10 minutos
  setInterval(tick, 10 * 60 * 1000);
}

/**
 * Força um backup imediato (chamado pela API)
 */
function backupAgora() {
  return executarBackup();
}

module.exports = { iniciarAgendador, backupAgora, aplicarRetencao };
