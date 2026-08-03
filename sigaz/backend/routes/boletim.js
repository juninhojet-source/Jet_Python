/**
 * Boletim Epidemiológico de Zoonoses
 * SIGAZ - PMBC
 *
 * Gera dados para boletim mensal e exportação compatível com SINAN.
 * Os dados retornados são consumidos pelo frontend que monta o PDF.
 */
const express = require('express');
const db = require('../db/connection');
const { autenticar } = require('../middleware/auth');
const { registrarLog } = require('../utils/logger');

const router = express.Router();
router.use(autenticar);

/**
 * GET /api/boletim/zoonoses?ano=2026&mes=5
 * Retorna o consolidado para o boletim mensal.
 */
router.get('/zoonoses', (req, res) => {
  const ano = parseInt(req.query.ano) || new Date().getFullYear();
  const mes = parseInt(req.query.mes) || (new Date().getMonth() + 1);

  const inicio = `${ano}-${String(mes).padStart(2,'0')}-01`;
  const ultimoDia = new Date(ano, mes, 0).getDate();
  const fim = `${ano}-${String(mes).padStart(2,'0')}-${ultimoDia}`;

  // Totais por tipo de zoonose
  const porZoonose = db.prepare(`
    SELECT zoonose, COUNT(*) as total,
      SUM(CASE WHEN diagnostico = 'Positivo' THEN 1 ELSE 0 END) AS positivos,
      SUM(CASE WHEN diagnostico = 'Negativo' THEN 1 ELSE 0 END) AS negativos,
      SUM(CASE WHEN diagnostico = 'Aguardando' OR diagnostico = 'Inconclusivo' THEN 1 ELSE 0 END) AS pendentes,
      SUM(CASE WHEN obito = 1 THEN 1 ELSE 0 END) AS obitos
    FROM zoonoses
    WHERE data_notificacao BETWEEN ? AND ?
    GROUP BY zoonose
    ORDER BY total DESC
  `).all(inicio, fim);

  // Distribuição por bairro
  const porBairro = db.prepare(`
    SELECT COALESCE(bairro_ocorrencia, 'Não informado') as bairro,
           COUNT(*) as total,
           SUM(CASE WHEN diagnostico = 'Positivo' THEN 1 ELSE 0 END) AS positivos
    FROM zoonoses
    WHERE data_notificacao BETWEEN ? AND ?
    GROUP BY bairro_ocorrencia
    ORDER BY total DESC
  `).all(inicio, fim);

  // Por espécie animal
  const porEspecie = db.prepare(`
    SELECT a.especie, COUNT(*) as total,
           SUM(CASE WHEN z.diagnostico = 'Positivo' THEN 1 ELSE 0 END) AS positivos
    FROM zoonoses z
    INNER JOIN animais a ON a.id = z.animal_id
    WHERE z.data_notificacao BETWEEN ? AND ?
    GROUP BY a.especie
    ORDER BY total DESC
  `).all(inicio, fim);

  // Por status de investigação
  const porStatus = db.prepare(`
    SELECT status_investigacao as status, COUNT(*) as total
    FROM zoonoses
    WHERE data_notificacao BETWEEN ? AND ?
    GROUP BY status_investigacao
  `).all(inicio, fim);

  // Comparativo com o mês anterior
  const mesAnt = mes === 1 ? 12 : mes - 1;
  const anoAnt = mes === 1 ? ano - 1 : ano;
  const ultDiaAnt = new Date(anoAnt, mesAnt, 0).getDate();
  const inicioAnt = `${anoAnt}-${String(mesAnt).padStart(2,'0')}-01`;
  const fimAnt = `${anoAnt}-${String(mesAnt).padStart(2,'0')}-${ultDiaAnt}`;

  const totalMesAnt = db.prepare(`
    SELECT COUNT(*) as t,
      SUM(CASE WHEN diagnostico='Positivo' THEN 1 ELSE 0 END) AS positivos
    FROM zoonoses WHERE data_notificacao BETWEEN ? AND ?
  `).get(inicioAnt, fimAnt);

  // Acumulado do ano
  const acumuladoAno = db.prepare(`
    SELECT COUNT(*) as t,
      SUM(CASE WHEN diagnostico='Positivo' THEN 1 ELSE 0 END) AS positivos
    FROM zoonoses WHERE data_notificacao BETWEEN ? AND ?
  `).get(`${ano}-01-01`, `${ano}-12-31`);

  // Total do mês corrente
  const totalMes = db.prepare(`
    SELECT COUNT(*) as t,
      SUM(CASE WHEN diagnostico='Positivo' THEN 1 ELSE 0 END) AS positivos,
      SUM(CASE WHEN obito = 1 THEN 1 ELSE 0 END) AS obitos
    FROM zoonoses WHERE data_notificacao BETWEEN ? AND ?
  `).get(inicio, fim);

  // Lista detalhada (para impressão)
  const ocorrencias = db.prepare(`
    SELECT z.*, a.codigo AS animal_codigo, a.nome AS animal_nome, a.especie,
           r.nome AS responsavel_nome
    FROM zoonoses z
    INNER JOIN animais a ON a.id = z.animal_id
    LEFT JOIN responsaveis r ON r.id = a.responsavel_id
    WHERE z.data_notificacao BETWEEN ? AND ?
    ORDER BY z.data_notificacao DESC
  `).all(inicio, fim);

  res.json({
    periodo: { ano, mes, inicio, fim },
    totais: {
      mes: totalMes,
      mesAnterior: totalMesAnt,
      acumuladoAno
    },
    porZoonose,
    porBairro,
    porEspecie,
    porStatus,
    ocorrencias
  });
});

/**
 * GET /api/boletim/zoonoses/sinan-csv?ano=2026&mes=5
 * Exporta CSV no formato compatível com SINAN Net
 * (estrutura simplificada — cada município pode ajustar campos no painel)
 */
router.get('/zoonoses/sinan-csv', (req, res) => {
  const ano = parseInt(req.query.ano) || new Date().getFullYear();
  const mes = parseInt(req.query.mes) || (new Date().getMonth() + 1);
  const inicio = `${ano}-${String(mes).padStart(2,'0')}-01`;
  const ultimoDia = new Date(ano, mes, 0).getDate();
  const fim = `${ano}-${String(mes).padStart(2,'0')}-${ultimoDia}`;

  const dados = db.prepare(`
    SELECT z.id, z.zoonose, z.data_notificacao, z.status_investigacao, z.diagnostico,
           z.metodo_diagnostico, z.bairro_ocorrencia, z.obito, z.data_obito,
           a.codigo AS animal_codigo, a.nome AS animal_nome, a.especie, a.raca,
           a.sexo, a.idade_aproximada,
           r.nome AS responsavel_nome, r.cpf AS responsavel_cpf,
           r.endereco AS responsavel_endereco, r.bairro AS responsavel_bairro
    FROM zoonoses z
    INNER JOIN animais a ON a.id = z.animal_id
    LEFT JOIN responsaveis r ON r.id = a.responsavel_id
    WHERE z.data_notificacao BETWEEN ? AND ?
    ORDER BY z.data_notificacao ASC
  `).all(inicio, fim);

  registrarLog(req, 'EXPORTAR_SINAN', 'zoonoses', null, { ano, mes, total: dados.length });

  // Cabeçalho compatível com SINAN
  const header = [
    'ID_OCORRENCIA','AGRAVO','DT_NOTIFICACAO','SG_UF_NOTIFIC','ID_MUNIC_NOTIFIC',
    'ID_PACIENTE','TP_NOT','DT_SIN_PRI','SEMANA_NOT','ANO_NASC',
    'CS_SEXO','BAIRRO_OCORRENCIA','ID_ESPECIE_ANIMAL','ID_RACA_ANIMAL',
    'DIAGNOSTICO','METODO_DIAGNOSTICO','EVOLUCAO_OBITO','DT_OBITO',
    'NM_RESPONSAVEL','CPF_RESPONSAVEL','ENDERECO_RESPONSAVEL','BAIRRO_RESPONSAVEL',
    'STATUS_INVESTIGACAO'
  ];

  const escape = v => {
    if (v == null) return '';
    const s = String(v);
    return /[",;\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };

  const linhas = [header.join(';')];
  for (const z of dados) {
    const dt = new Date(z.data_notificacao);
    const semana = Math.ceil((dt - new Date(dt.getFullYear(),0,1)) / 604800000);
    linhas.push([
      z.id, z.zoonose, z.data_notificacao, 'MG', '310620', // 310620 = IBGE Barão de Cocais
      z.animal_codigo, '02' /* notificação individual */, z.data_notificacao,
      semana, '', // ano_nasc não aplicável a animais
      z.sexo === 'Macho' ? 'M' : (z.sexo === 'Fêmea' ? 'F' : 'I'),
      z.bairro_ocorrencia, z.especie, z.raca,
      z.diagnostico, z.metodo_diagnostico,
      z.obito ? '1' : '2', z.data_obito,
      z.responsavel_nome, z.responsavel_cpf, z.responsavel_endereco, z.responsavel_bairro,
      z.status_investigacao
    ].map(escape).join(';'));
  }

  const csv = '\uFEFF' + linhas.join('\n');
  res.setHeader('Content-Type', 'text/csv; charset=utf-8');
  res.setHeader('Content-Disposition',
    `attachment; filename="sinan_zoonoses_${ano}-${String(mes).padStart(2,'0')}.csv"`);
  res.send(csv);
});

module.exports = router;
