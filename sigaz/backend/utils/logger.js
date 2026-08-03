/**
 * Utilitário para registro de logs/auditoria
 * SIGAZ - PMBC
 */
const db = require('../db/connection');

const insertLog = db.prepare(`
  INSERT INTO logs (usuario_id, acao, entidade, entidade_id, detalhes, ip)
  VALUES (?, ?, ?, ?, ?, ?)
`);

/**
 * Registra uma ação no log de auditoria
 */
function registrarLog(req, acao, entidade, entidadeId = null, detalhes = null) {
  try {
    const usuarioId = req.usuario ? req.usuario.id : null;
    const ip = req.ip || req.connection.remoteAddress || null;
    const det = typeof detalhes === 'object' ? JSON.stringify(detalhes) : detalhes;
    insertLog.run(usuarioId, acao, entidade, entidadeId, det, ip);
  } catch (err) {
    console.error('Erro ao registrar log:', err.message);
  }
}

module.exports = { registrarLog };
