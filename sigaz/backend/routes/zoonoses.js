/**
 * Rotas de Zoonoses
 * SIGAZ - PMBC
 */
const express = require('express');
const db = require('../db/connection');
const { autenticar } = require('../middleware/auth');
const { registrarLog } = require('../utils/logger');

const router = express.Router();
router.use(autenticar);

router.get('/', (req, res) => {
  const { zoonose, status, bairro, animal_id } = req.query;
  let where = 'WHERE 1=1';
  const params = [];

  if (zoonose) { where += ' AND z.zoonose = ?'; params.push(zoonose); }
  if (status) { where += ' AND z.status_investigacao = ?'; params.push(status); }
  if (bairro) { where += ' AND z.bairro_ocorrencia = ?'; params.push(bairro); }
  if (animal_id) { where += ' AND z.animal_id = ?'; params.push(animal_id); }

  const dados = db.prepare(`
    SELECT z.*, a.nome AS animal_nome, a.codigo AS animal_codigo, a.especie AS animal_especie,
           r.nome AS responsavel_nome, r.telefone AS responsavel_telefone
    FROM zoonoses z
    INNER JOIN animais a ON a.id = z.animal_id
    LEFT JOIN responsaveis r ON r.id = a.responsavel_id
    ${where}
    ORDER BY z.data_notificacao DESC
  `).all(...params);

  res.json({ dados });
});

router.get('/:id', (req, res) => {
  const dado = db.prepare(`
    SELECT z.*, a.nome AS animal_nome, a.codigo AS animal_codigo
    FROM zoonoses z
    INNER JOIN animais a ON a.id = z.animal_id
    WHERE z.id = ?
  `).get(req.params.id);
  if (!dado) return res.status(404).json({ erro: 'Ocorrência não encontrada' });
  res.json(dado);
});

router.post('/', (req, res) => {
  const {
    animal_id, zoonose, data_notificacao, status_investigacao, diagnostico,
    prognostico, obito, data_obito, metodo_diagnostico, bairro_ocorrencia, observacoes
  } = req.body;

  if (!animal_id || !zoonose || !data_notificacao) {
    return res.status(400).json({ erro: 'animal_id, zoonose e data_notificacao são obrigatórios' });
  }

  const info = db.prepare(`
    INSERT INTO zoonoses (animal_id, zoonose, data_notificacao, status_investigacao, diagnostico,
                          prognostico, obito, data_obito, metodo_diagnostico, bairro_ocorrencia,
                          observacoes, usuario_id)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `).run(animal_id, zoonose, data_notificacao, status_investigacao || 'À investigar',
          diagnostico || 'Aguardando', prognostico || null, obito ? 1 : 0, data_obito || null,
          metodo_diagnostico || null, bairro_ocorrencia || null, observacoes || null, req.usuario.id);

  registrarLog(req, 'CRIAR', 'zoonoses', info.lastInsertRowid, { animal_id, zoonose });
  res.status(201).json({ id: info.lastInsertRowid });
});

router.put('/:id', (req, res) => {
  const existe = db.prepare('SELECT id FROM zoonoses WHERE id = ?').get(req.params.id);
  if (!existe) return res.status(404).json({ erro: 'Ocorrência não encontrada' });

  const {
    zoonose, data_notificacao, status_investigacao, diagnostico, prognostico,
    obito, data_obito, metodo_diagnostico, bairro_ocorrencia, observacoes
  } = req.body;

  db.prepare(`
    UPDATE zoonoses SET zoonose=?, data_notificacao=?, status_investigacao=?, diagnostico=?,
      prognostico=?, obito=?, data_obito=?, metodo_diagnostico=?, bairro_ocorrencia=?, observacoes=?,
      atualizado_em=CURRENT_TIMESTAMP
    WHERE id=?
  `).run(zoonose, data_notificacao, status_investigacao, diagnostico, prognostico || null,
          obito ? 1 : 0, data_obito || null, metodo_diagnostico || null, bairro_ocorrencia || null,
          observacoes || null, req.params.id);

  registrarLog(req, 'ATUALIZAR', 'zoonoses', req.params.id);
  res.json({ ok: true });
});

router.delete('/:id', (req, res) => {
  db.prepare('DELETE FROM zoonoses WHERE id = ?').run(req.params.id);
  registrarLog(req, 'EXCLUIR', 'zoonoses', req.params.id);
  res.json({ ok: true });
});

module.exports = router;
