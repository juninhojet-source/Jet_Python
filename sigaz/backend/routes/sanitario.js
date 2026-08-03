/**
 * Rotas de Controle Sanitário
 * Vacinas, Vermifugação e Ectoparasitários
 * SIGAZ - PMBC
 */
const express = require('express');
const db = require('../db/connection');
const { autenticar } = require('../middleware/auth');
const { registrarLog } = require('../utils/logger');

const router = express.Router();
router.use(autenticar);

// ============================================================
// VACINAS
// ============================================================

router.get('/vacinas', (req, res) => {
  const { animal_id, vencendo_dias, status } = req.query;
  let where = 'WHERE 1=1';
  const params = [];

  if (animal_id) {
    where += ' AND v.animal_id = ?';
    params.push(animal_id);
  }

  if (vencendo_dias) {
    where += " AND v.proxima_aplicacao IS NOT NULL AND v.proxima_aplicacao <= date('now', '+' || ? || ' days')";
    params.push(parseInt(vencendo_dias));
  }

  // status='vencidas': apenas vacinas realmente vencidas, considerando
  // SOMENTE a dose mais recente de cada combinação (animal + tipo de vacina).
  // Assim, se o animal foi revacinado, a dose antiga não conta como vencida.
  if (status === 'vencidas') {
    where += `
      AND v.proxima_aplicacao IS NOT NULL
      AND v.proxima_aplicacao < date('now')
      AND v.id = (
        SELECT v2.id FROM vacinas v2
        WHERE v2.animal_id = v.animal_id AND v2.vacina = v.vacina
        ORDER BY v2.data_aplicacao DESC, v2.id DESC
        LIMIT 1
      )
    `;
  }

  // status='vencendo': dose mais recente cuja próxima aplicação está dentro da janela
  if (status === 'vencendo') {
    where += `
      AND v.proxima_aplicacao IS NOT NULL
      AND v.proxima_aplicacao >= date('now')
      AND v.proxima_aplicacao <= date('now', '+30 days')
      AND v.id = (
        SELECT v2.id FROM vacinas v2
        WHERE v2.animal_id = v.animal_id AND v2.vacina = v.vacina
        ORDER BY v2.data_aplicacao DESC, v2.id DESC
        LIMIT 1
      )
    `;
  }

  const dados = db.prepare(`
    SELECT v.*, a.nome AS animal_nome, a.codigo AS animal_codigo,
      CASE WHEN v.id = (
        SELECT v2.id FROM vacinas v2
        WHERE v2.animal_id = v.animal_id AND v2.vacina = v.vacina
        ORDER BY v2.data_aplicacao DESC, v2.id DESC
        LIMIT 1
      ) THEN 1 ELSE 0 END AS eh_vigente
    FROM vacinas v
    INNER JOIN animais a ON a.id = v.animal_id
    ${where}
    ORDER BY v.data_aplicacao DESC
    LIMIT 200
  `).all(...params);

  res.json({ dados });
});

router.post('/vacinas', (req, res) => {
  const {
    animal_id, vacina, fabricante, lote, data_aplicacao, data_validade,
    proxima_aplicacao, responsavel_aplicacao, crmv, observacoes
  } = req.body;

  if (!animal_id || !vacina || !data_aplicacao) {
    return res.status(400).json({ erro: 'animal_id, vacina e data_aplicacao são obrigatórios' });
  }

  const info = db.prepare(`
    INSERT INTO vacinas (animal_id, vacina, fabricante, lote, data_aplicacao, data_validade,
                         proxima_aplicacao, responsavel_aplicacao, crmv, observacoes, usuario_id)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `).run(animal_id, vacina, fabricante || null, lote || null, data_aplicacao,
          data_validade || null, proxima_aplicacao || null, responsavel_aplicacao || null,
          crmv || null, observacoes || null, req.usuario.id);

  registrarLog(req, 'CRIAR', 'vacinas', info.lastInsertRowid, { animal_id, vacina });
  res.status(201).json({ id: info.lastInsertRowid });
});

router.delete('/vacinas/:id', (req, res) => {
  db.prepare('DELETE FROM vacinas WHERE id = ?').run(req.params.id);
  registrarLog(req, 'EXCLUIR', 'vacinas', req.params.id);
  res.json({ ok: true });
});

// ============================================================
// VERMIFUGAÇÕES
// ============================================================

router.get('/vermifugacoes', (req, res) => {
  const { animal_id } = req.query;
  let where = '';
  const params = [];
  if (animal_id) {
    where = 'WHERE v.animal_id = ?';
    params.push(animal_id);
  }
  const dados = db.prepare(`
    SELECT v.*, a.nome AS animal_nome, a.codigo AS animal_codigo
    FROM vermifugacoes v
    INNER JOIN animais a ON a.id = v.animal_id
    ${where}
    ORDER BY v.data_aplicacao DESC LIMIT 200
  `).all(...params);
  res.json({ dados });
});

router.post('/vermifugacoes', (req, res) => {
  const { animal_id, produto, lote, data_aplicacao, data_validade, proxima_aplicacao, responsavel, observacoes } = req.body;
  if (!animal_id || !produto || !data_aplicacao) {
    return res.status(400).json({ erro: 'animal_id, produto e data_aplicacao são obrigatórios' });
  }
  const info = db.prepare(`
    INSERT INTO vermifugacoes (animal_id, produto, lote, data_aplicacao, data_validade, proxima_aplicacao, responsavel, observacoes, usuario_id)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
  `).run(animal_id, produto, lote || null, data_aplicacao, data_validade || null,
          proxima_aplicacao || null, responsavel || null, observacoes || null, req.usuario.id);
  registrarLog(req, 'CRIAR', 'vermifugacoes', info.lastInsertRowid);
  res.status(201).json({ id: info.lastInsertRowid });
});

router.delete('/vermifugacoes/:id', (req, res) => {
  db.prepare('DELETE FROM vermifugacoes WHERE id = ?').run(req.params.id);
  registrarLog(req, 'EXCLUIR', 'vermifugacoes', req.params.id);
  res.json({ ok: true });
});

// ============================================================
// ECTOPARASITÁRIOS
// ============================================================

router.get('/ectoparasitarios', (req, res) => {
  const { animal_id } = req.query;
  let where = '';
  const params = [];
  if (animal_id) {
    where = 'WHERE e.animal_id = ?';
    params.push(animal_id);
  }
  const dados = db.prepare(`
    SELECT e.*, a.nome AS animal_nome, a.codigo AS animal_codigo
    FROM ectoparasitarios e
    INNER JOIN animais a ON a.id = e.animal_id
    ${where}
    ORDER BY e.data_aplicacao DESC LIMIT 200
  `).all(...params);
  res.json({ dados });
});

router.post('/ectoparasitarios', (req, res) => {
  const { animal_id, produto, lote, data_aplicacao, data_validade, proxima_aplicacao, responsavel, observacoes } = req.body;
  if (!animal_id || !produto || !data_aplicacao) {
    return res.status(400).json({ erro: 'animal_id, produto e data_aplicacao são obrigatórios' });
  }
  const info = db.prepare(`
    INSERT INTO ectoparasitarios (animal_id, produto, lote, data_aplicacao, data_validade, proxima_aplicacao, responsavel, observacoes, usuario_id)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
  `).run(animal_id, produto, lote || null, data_aplicacao, data_validade || null,
          proxima_aplicacao || null, responsavel || null, observacoes || null, req.usuario.id);
  registrarLog(req, 'CRIAR', 'ectoparasitarios', info.lastInsertRowid);
  res.status(201).json({ id: info.lastInsertRowid });
});

router.delete('/ectoparasitarios/:id', (req, res) => {
  db.prepare('DELETE FROM ectoparasitarios WHERE id = ?').run(req.params.id);
  registrarLog(req, 'EXCLUIR', 'ectoparasitarios', req.params.id);
  res.json({ ok: true });
});

module.exports = router;
