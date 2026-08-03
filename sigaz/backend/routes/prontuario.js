/**
 * Prontuário Veterinário
 * SIGAZ - PMBC
 *
 * Registro clínico de consultas, exames, prescrições e retornos.
 */
const express = require('express');
const db = require('../db/connection');
const { autenticar } = require('../middleware/auth');
const { registrarLog } = require('../utils/logger');

const router = express.Router();
router.use(autenticar);

// Consultas de um animal específico
router.get('/animal/:animal_id', (req, res) => {
  const dados = db.prepare(`
    SELECT p.*, u.nome AS veterinario_nome
    FROM prontuario p
    LEFT JOIN usuarios u ON u.id = p.veterinario_id
    WHERE p.animal_id = ?
    ORDER BY p.data_consulta DESC, p.id DESC
  `).all(req.params.animal_id);
  res.json({ dados });
});

// Detalhe de uma consulta
router.get('/:id', (req, res) => {
  const c = db.prepare(`
    SELECT p.*, u.nome AS veterinario_nome,
           a.codigo AS animal_codigo, a.nome AS animal_nome, a.especie, a.raca,
           r.nome AS responsavel_nome, r.cpf AS responsavel_cpf,
           r.telefone AS responsavel_telefone
    FROM prontuario p
    LEFT JOIN usuarios u ON u.id = p.veterinario_id
    INNER JOIN animais a ON a.id = p.animal_id
    LEFT JOIN responsaveis r ON r.id = a.responsavel_id
    WHERE p.id = ?
  `).get(req.params.id);
  if (!c) return res.status(404).json({ erro: 'Consulta não encontrada' });
  res.json(c);
});

router.post('/', (req, res) => {
  const b = req.body;
  if (!b.animal_id || !b.data_consulta) {
    return res.status(400).json({ erro: 'Animal e data são obrigatórios' });
  }

  const info = db.prepare(`
    INSERT INTO prontuario (
      animal_id, data_consulta, tipo, motivo, anamnese,
      peso_kg, temperatura, frequencia_cardiaca, frequencia_respiratoria, escore_corporal,
      exame_fisico, diagnostico, prognostico, conduta,
      medicamentos, exames_solicitados,
      retorno_data, retorno_motivo,
      veterinario_id, veterinario_crmv
    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
  `).run(
    b.animal_id, b.data_consulta, b.tipo || 'Consulta',
    b.motivo || null, b.anamnese || null,
    parseFloat(b.peso_kg) || null,
    parseFloat(b.temperatura) || null,
    parseInt(b.frequencia_cardiaca) || null,
    parseInt(b.frequencia_respiratoria) || null,
    parseInt(b.escore_corporal) || null,
    b.exame_fisico || null, b.diagnostico || null,
    b.prognostico || null, b.conduta || null,
    b.medicamentos || null, b.exames_solicitados || null,
    b.retorno_data || null, b.retorno_motivo || null,
    req.usuario.id, b.veterinario_crmv || null
  );

  // Sincroniza peso atual do animal, se informado
  if (b.peso_kg) {
    db.prepare('UPDATE animais SET peso_kg = ?, atualizado_em = CURRENT_TIMESTAMP WHERE id = ?')
      .run(parseFloat(b.peso_kg), b.animal_id);
  }

  registrarLog(req, 'CRIAR', 'prontuario', info.lastInsertRowid, { animal_id: b.animal_id });
  res.status(201).json({ id: info.lastInsertRowid });
});

router.put('/:id', (req, res) => {
  const c = db.prepare('SELECT id FROM prontuario WHERE id = ?').get(req.params.id);
  if (!c) return res.status(404).json({ erro: 'Consulta não encontrada' });

  const b = req.body;
  db.prepare(`
    UPDATE prontuario SET
      data_consulta=?, tipo=?, motivo=?, anamnese=?,
      peso_kg=?, temperatura=?, frequencia_cardiaca=?, frequencia_respiratoria=?, escore_corporal=?,
      exame_fisico=?, diagnostico=?, prognostico=?, conduta=?,
      medicamentos=?, exames_solicitados=?,
      retorno_data=?, retorno_motivo=?,
      veterinario_crmv=?, atualizado_em=CURRENT_TIMESTAMP
    WHERE id=?
  `).run(
    b.data_consulta, b.tipo || 'Consulta',
    b.motivo || null, b.anamnese || null,
    parseFloat(b.peso_kg) || null,
    parseFloat(b.temperatura) || null,
    parseInt(b.frequencia_cardiaca) || null,
    parseInt(b.frequencia_respiratoria) || null,
    parseInt(b.escore_corporal) || null,
    b.exame_fisico || null, b.diagnostico || null,
    b.prognostico || null, b.conduta || null,
    b.medicamentos || null, b.exames_solicitados || null,
    b.retorno_data || null, b.retorno_motivo || null,
    b.veterinario_crmv || null,
    req.params.id
  );

  registrarLog(req, 'ATUALIZAR', 'prontuario', req.params.id);
  res.json({ ok: true });
});

router.delete('/:id', (req, res) => {
  db.prepare('DELETE FROM prontuario WHERE id = ?').run(req.params.id);
  registrarLog(req, 'EXCLUIR', 'prontuario', req.params.id);
  res.json({ ok: true });
});

// Próximos retornos agendados (alerta no dashboard)
router.get('/proximos/retornos', (req, res) => {
  const dados = db.prepare(`
    SELECT p.id, p.animal_id, p.data_consulta, p.retorno_data, p.retorno_motivo,
           a.codigo AS animal_codigo, a.nome AS animal_nome,
           r.nome AS responsavel_nome, r.telefone AS responsavel_telefone
    FROM prontuario p
    INNER JOIN animais a ON a.id = p.animal_id
    LEFT JOIN responsaveis r ON r.id = a.responsavel_id
    WHERE p.retorno_data IS NOT NULL
      AND p.retorno_data BETWEEN date('now') AND date('now', '+15 days')
    ORDER BY p.retorno_data ASC
  `).all();
  res.json({ dados });
});

module.exports = router;
