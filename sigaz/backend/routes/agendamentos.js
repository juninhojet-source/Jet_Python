/**
 * Rotas de Agendamento
 * SIGAZ - PMBC
 */
const express = require('express');
const db = require('../db/connection');
const { autenticar } = require('../middleware/auth');
const { registrarLog } = require('../utils/logger');

const router = express.Router();
router.use(autenticar);

router.get('/', (req, res) => {
  const { data_inicio, data_fim, status, tipo, animal_id } = req.query;
  let where = 'WHERE 1=1';
  const params = [];
  if (data_inicio) { where += ' AND a.data_agendada >= ?'; params.push(data_inicio); }
  if (data_fim) { where += ' AND a.data_agendada <= ?'; params.push(data_fim + ' 23:59:59'); }
  if (status) { where += ' AND a.status = ?'; params.push(status); }
  if (tipo) { where += ' AND a.tipo = ?'; params.push(tipo); }
  if (animal_id) { where += ' AND a.animal_id = ?'; params.push(animal_id); }

  const dados = db.prepare(`
    SELECT a.*, an.nome AS animal_nome, an.codigo AS animal_codigo,
           r.nome AS responsavel_nome, r.telefone AS responsavel_telefone
    FROM agendamentos a
    LEFT JOIN animais an ON an.id = a.animal_id
    LEFT JOIN responsaveis r ON r.id = a.responsavel_id
    ${where}
    ORDER BY a.data_agendada ASC
  `).all(...params);
  res.json({ dados });
});

router.get('/:id', (req, res) => {
  const d = db.prepare(`
    SELECT a.*, an.nome AS animal_nome, an.codigo AS animal_codigo,
           r.nome AS responsavel_nome, r.telefone AS responsavel_telefone
    FROM agendamentos a
    LEFT JOIN animais an ON an.id = a.animal_id
    LEFT JOIN responsaveis r ON r.id = a.responsavel_id
    WHERE a.id = ?
  `).get(req.params.id);
  if (!d) return res.status(404).json({ erro: 'Agendamento não encontrado' });
  res.json(d);
});

router.post('/', (req, res) => {
  const { tipo, animal_id, responsavel_id, data_agendada, duracao_min, local, observacoes, status } = req.body;
  if (!tipo || !data_agendada) {
    return res.status(400).json({ erro: 'Tipo e data são obrigatórios' });
  }
  const info = db.prepare(`
    INSERT INTO agendamentos (tipo, animal_id, responsavel_id, data_agendada, duracao_min, local, observacoes, status, usuario_id)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
  `).run(tipo, animal_id || null, responsavel_id || null, data_agendada,
         duracao_min || 30, local || null, observacoes || null, status || 'Agendado', req.usuario.id);
  registrarLog(req, 'CRIAR', 'agendamentos', info.lastInsertRowid, { tipo, data_agendada });
  res.status(201).json({ id: info.lastInsertRowid });
});

router.put('/:id', (req, res) => {
  const a = db.prepare('SELECT * FROM agendamentos WHERE id = ?').get(req.params.id);
  if (!a) return res.status(404).json({ erro: 'Agendamento não encontrado' });

  const { tipo, animal_id, responsavel_id, data_agendada, duracao_min, local, observacoes, status, realizado_em } = req.body;

  db.prepare(`
    UPDATE agendamentos SET
      tipo=?, animal_id=?, responsavel_id=?, data_agendada=?, duracao_min=?,
      local=?, observacoes=?, status=?, realizado_em=?, atualizado_em=CURRENT_TIMESTAMP
    WHERE id=?
  `).run(tipo, animal_id || null, responsavel_id || null, data_agendada,
         duracao_min || 30, local || null, observacoes || null,
         status || 'Agendado', realizado_em || null, req.params.id);

  registrarLog(req, 'ATUALIZAR', 'agendamentos', req.params.id, { status });
  res.json({ ok: true });
});

router.delete('/:id', (req, res) => {
  db.prepare('DELETE FROM agendamentos WHERE id = ?').run(req.params.id);
  registrarLog(req, 'EXCLUIR', 'agendamentos', req.params.id);
  res.json({ ok: true });
});

module.exports = router;
