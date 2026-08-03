/**
 * Rotas de Dashboard e Relatórios
 * SIGAZ - PMBC
 */
const express = require('express');
const db = require('../db/connection');
const { autenticar } = require('../middleware/auth');

const router = express.Router();
router.use(autenticar);

/**
 * GET /api/dashboard
 * Retorna todos os indicadores principais
 */
router.get('/dashboard', (req, res) => {
  // Totais gerais
  const totalAnimais = db.prepare('SELECT COUNT(*) as t FROM animais WHERE ativo = 1').get().t;
  const totalCanino = db.prepare("SELECT COUNT(*) as t FROM animais WHERE ativo = 1 AND especie = 'Canino'").get().t;
  const totalFelino = db.prepare("SELECT COUNT(*) as t FROM animais WHERE ativo = 1 AND especie = 'Felino'").get().t;
  const totalOutros = totalAnimais - totalCanino - totalFelino;

  const totalResponsaveis = db.prepare('SELECT COUNT(*) as t FROM responsaveis').get().t;
  const totalCastrados = db.prepare("SELECT COUNT(*) as t FROM animais WHERE ativo = 1 AND status_reprodutivo = 'Castrado(a)'").get().t;
  const totalMicrochipados = db.prepare("SELECT COUNT(*) as t FROM animais WHERE ativo = 1 AND microchip IS NOT NULL AND microchip != ''").get().t;

  // Vacinação
  const totalVacinados = db.prepare(`
    SELECT COUNT(DISTINCT animal_id) as t FROM vacinas
  `).get().t;

  const totalVermifugados = db.prepare(`
    SELECT COUNT(DISTINCT animal_id) as t FROM vermifugacoes
  `).get().t;

  const totalEcto = db.prepare(`
    SELECT COUNT(DISTINCT animal_id) as t FROM ectoparasitarios
  `).get().t;

  // Zoonoses
  const zoonosesAtivas = db.prepare(`
    SELECT COUNT(*) as t FROM zoonoses
    WHERE status_investigacao IN ('À investigar', 'Em análise')
  `).get().t;

  const zoonosesPositivas = db.prepare(`
    SELECT COUNT(*) as t FROM zoonoses WHERE diagnostico = 'Positivo'
  `).get().t;

  // Animais por bairro
  const porBairro = db.prepare(`
    SELECT r.bairro, COUNT(*) as total
    FROM animais a
    INNER JOIN responsaveis r ON r.id = a.responsavel_id
    WHERE a.ativo = 1 AND r.bairro IS NOT NULL AND r.bairro != ''
    GROUP BY r.bairro
    ORDER BY total DESC
    LIMIT 10
  `).all();

  // Zoonoses por bairro
  const zoonosesPorBairro = db.prepare(`
    SELECT bairro_ocorrencia AS bairro, COUNT(*) as total
    FROM zoonoses
    WHERE bairro_ocorrencia IS NOT NULL AND bairro_ocorrencia != ''
    GROUP BY bairro_ocorrencia
    ORDER BY total DESC
    LIMIT 10
  `).all();

  // Vacinação mensal (últimos 12 meses)
  const vacinacaoMensal = db.prepare(`
    SELECT strftime('%Y-%m', data_aplicacao) as mes, COUNT(*) as total
    FROM vacinas
    WHERE data_aplicacao >= date('now', '-12 months')
    GROUP BY mes
    ORDER BY mes ASC
  `).all();

  // Alertas — vacinas vencendo nos próximos 30 dias
  // Considera apenas a dose mais recente de cada (animal + vacina),
  // para não alertar sobre doses já substituídas por revacinação.
  const alertasVacinas = db.prepare(`
    SELECT v.id, v.vacina, v.proxima_aplicacao, a.nome AS animal_nome, a.codigo AS animal_codigo
    FROM vacinas v
    INNER JOIN animais a ON a.id = v.animal_id
    WHERE v.proxima_aplicacao IS NOT NULL
      AND v.proxima_aplicacao BETWEEN date('now') AND date('now', '+30 days')
      AND a.ativo = 1
      AND v.id = (
        SELECT v2.id FROM vacinas v2
        WHERE v2.animal_id = v.animal_id AND v2.vacina = v.vacina
        ORDER BY v2.data_aplicacao DESC, v2.id DESC
        LIMIT 1
      )
    ORDER BY v.proxima_aplicacao ASC
    LIMIT 20
  `).all();

  res.json({
    indicadores: {
      totalAnimais,
      totalCanino,
      totalFelino,
      totalOutros,
      totalResponsaveis,
      totalCastrados,
      totalMicrochipados,
      totalVacinados,
      totalVermifugados,
      totalEcto,
      zoonosesAtivas,
      zoonosesPositivas
    },
    porBairro,
    zoonosesPorBairro,
    vacinacaoMensal,
    alertasVacinas
  });
});

/**
 * GET /api/relatorios/animais
 */
router.get('/relatorios/animais', (req, res) => {
  const { especie, bairro, status_reprodutivo, data_inicio, data_fim } = req.query;
  let where = 'WHERE a.ativo = 1';
  const params = [];

  if (especie) { where += ' AND a.especie = ?'; params.push(especie); }
  if (bairro) { where += ' AND r.bairro = ?'; params.push(bairro); }
  if (status_reprodutivo) { where += ' AND a.status_reprodutivo = ?'; params.push(status_reprodutivo); }
  if (data_inicio) { where += ' AND a.criado_em >= ?'; params.push(data_inicio); }
  if (data_fim) { where += ' AND a.criado_em <= ?'; params.push(data_fim + ' 23:59:59'); }

  const dados = db.prepare(`
    SELECT a.codigo, a.nome, a.especie, a.raca, a.sexo, a.status_reprodutivo,
           a.idade_aproximada, r.nome AS responsavel, r.cpf, r.telefone, r.bairro,
           a.criado_em
    FROM animais a
    LEFT JOIN responsaveis r ON r.id = a.responsavel_id
    ${where}
    ORDER BY a.criado_em DESC
  `).all(...params);

  res.json({ total: dados.length, dados });
});

/**
 * GET /api/relatorios/vacinacao
 */
router.get('/relatorios/vacinacao', (req, res) => {
  const { vacina, data_inicio, data_fim } = req.query;
  let where = 'WHERE 1=1';
  const params = [];

  if (vacina) { where += ' AND v.vacina = ?'; params.push(vacina); }
  if (data_inicio) { where += ' AND v.data_aplicacao >= ?'; params.push(data_inicio); }
  if (data_fim) { where += ' AND v.data_aplicacao <= ?'; params.push(data_fim); }

  const dados = db.prepare(`
    SELECT v.*, a.codigo AS animal_codigo, a.nome AS animal_nome, a.especie,
           r.nome AS responsavel_nome, r.bairro
    FROM vacinas v
    INNER JOIN animais a ON a.id = v.animal_id
    LEFT JOIN responsaveis r ON r.id = a.responsavel_id
    ${where}
    ORDER BY v.data_aplicacao DESC
  `).all(...params);

  res.json({ total: dados.length, dados });
});

/**
 * GET /api/relatorios/zoonoses
 */
router.get('/relatorios/zoonoses', (req, res) => {
  const { zoonose, diagnostico, data_inicio, data_fim } = req.query;
  let where = 'WHERE 1=1';
  const params = [];

  if (zoonose) { where += ' AND z.zoonose = ?'; params.push(zoonose); }
  if (diagnostico) { where += ' AND z.diagnostico = ?'; params.push(diagnostico); }
  if (data_inicio) { where += ' AND z.data_notificacao >= ?'; params.push(data_inicio); }
  if (data_fim) { where += ' AND z.data_notificacao <= ?'; params.push(data_fim); }

  const dados = db.prepare(`
    SELECT z.*, a.codigo AS animal_codigo, a.nome AS animal_nome, a.especie,
           r.nome AS responsavel_nome, r.bairro AS responsavel_bairro
    FROM zoonoses z
    INNER JOIN animais a ON a.id = z.animal_id
    LEFT JOIN responsaveis r ON r.id = a.responsavel_id
    ${where}
    ORDER BY z.data_notificacao DESC
  `).all(...params);

  res.json({ total: dados.length, dados });
});

module.exports = router;
