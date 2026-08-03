/**
 * Ficha SINAN — Atendimento Antirrábico Humano (Mordeduras)
 * SIGAZ - PMBC
 *
 * Notificação compulsória obrigatória conforme:
 * - Portaria GM/MS nº 264/2020 (Lista Nacional de Notificação Compulsória)
 * - Manual de Vigilância da Raiva (Ministério da Saúde)
 */
const express = require('express');
const db = require('../db/connection');
const { autenticar } = require('../middleware/auth');
const { registrarLog } = require('../utils/logger');

const router = express.Router();
router.use(autenticar);

function gerarProtocolo() {
  const ano = new Date().getFullYear();
  const ult = db.prepare(`SELECT protocolo FROM mordeduras WHERE protocolo LIKE ? ORDER BY id DESC LIMIT 1`).get(`MOR-${ano}-%`);
  let proximo = 1;
  if (ult) proximo = parseInt(ult.protocolo.split('-')[2]) + 1;
  return `MOR-${ano}-${String(proximo).padStart(5, '0')}`;
}

// Listar com filtros
router.get('/', (req, res) => {
  const { status, ano, mes, observacao_pendente } = req.query;
  let where = 'WHERE 1=1';
  const params = [];
  if (status) { where += ' AND status_caso = ?'; params.push(status); }
  if (ano) { where += " AND strftime('%Y', data_notificacao) = ?"; params.push(String(ano)); }
  if (mes) { where += " AND strftime('%m', data_notificacao) = ?"; params.push(String(mes).padStart(2, '0')); }
  if (observacao_pendente === '1') {
    where += ` AND observacao_iniciada = 1 AND observacao_status = 'Em curso'`;
  }

  const dados = db.prepare(`
    SELECT m.*, a.codigo AS animal_codigo, a.nome AS animal_nome,
           u.nome AS usuario_nome
    FROM mordeduras m
    LEFT JOIN animais a ON a.id = m.animal_id
    LEFT JOIN usuarios u ON u.id = m.usuario_id
    ${where}
    ORDER BY m.data_notificacao DESC, m.id DESC
  `).all(...params);

  res.json({ dados });
});

router.get('/:id', (req, res) => {
  const m = db.prepare(`
    SELECT m.*, a.codigo AS animal_codigo, a.nome AS animal_nome
    FROM mordeduras m
    LEFT JOIN animais a ON a.id = m.animal_id
    WHERE m.id = ?
  `).get(req.params.id);
  if (!m) return res.status(404).json({ erro: 'Notificação não encontrada' });

  m.observacoes_diarias = db.prepare(`
    SELECT mo.*, u.nome AS usuario_nome
    FROM mordedura_observacoes mo
    LEFT JOIN usuarios u ON u.id = mo.usuario_id
    WHERE mo.mordedura_id = ?
    ORDER BY mo.data ASC
  `).all(req.params.id);

  res.json(m);
});

router.post('/', (req, res) => {
  const b = req.body;
  if (!b.vitima_nome || !b.data_notificacao) {
    return res.status(400).json({ erro: 'Nome da vítima e data de notificação são obrigatórios' });
  }

  const protocolo = gerarProtocolo();

  // Calcular data prevista de fim da observação (10 dias a partir da ocorrência)
  let obsFim = null;
  if (b.observacao_iniciada && b.data_ocorrencia) {
    const d = new Date(b.data_ocorrencia + 'T00:00:00');
    d.setDate(d.getDate() + 10);
    obsFim = d.toISOString().substring(0, 10);
  }

  const info = db.prepare(`
    INSERT INTO mordeduras (
      protocolo, data_notificacao, data_ocorrencia,
      vitima_nome, vitima_cpf, vitima_data_nascimento, vitima_sexo, vitima_telefone,
      vitima_endereco, vitima_bairro, vitima_cidade, vitima_uf, vitima_cep,
      local_anatomico, tipo_ferimento, descricao_acidente, local_ocorrencia, bairro_ocorrencia,
      animal_id, animal_especie, animal_conhecido, animal_vacinado,
      animal_proprietario_nome, animal_proprietario_telefone, animal_proprietario_endereco,
      tipo_exposicao, conduta, profilaxia_iniciada, unidade_atendimento,
      observacao_iniciada, observacao_status, observacao_inicio, observacao_fim_previsto,
      status_caso, usuario_id
    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
  `).run(
    protocolo, b.data_notificacao, b.data_ocorrencia || null,
    b.vitima_nome, (b.vitima_cpf || '').replace(/\D/g, '') || null,
    b.vitima_data_nascimento || null, b.vitima_sexo || null,
    (b.vitima_telefone || '').replace(/\D/g, '') || null,
    b.vitima_endereco || null, b.vitima_bairro || null,
    b.vitima_cidade || 'Barão de Cocais', b.vitima_uf || 'MG',
    (b.vitima_cep || '').replace(/\D/g, '') || null,
    b.local_anatomico || null, b.tipo_ferimento || null,
    b.descricao_acidente || null, b.local_ocorrencia || null, b.bairro_ocorrencia || null,
    b.animal_id || null, b.animal_especie || null,
    b.animal_conhecido ? 1 : 0, b.animal_vacinado || null,
    b.animal_proprietario_nome || null,
    (b.animal_proprietario_telefone || '').replace(/\D/g, '') || null,
    b.animal_proprietario_endereco || null,
    b.tipo_exposicao || null, b.conduta || null,
    b.profilaxia_iniciada ? 1 : 0, b.unidade_atendimento || null,
    b.observacao_iniciada ? 1 : 0,
    b.observacao_iniciada ? 'Em curso' : null,
    b.observacao_iniciada ? (b.data_ocorrencia || b.data_notificacao) : null,
    obsFim,
    'Aberto', req.usuario.id
  );

  registrarLog(req, 'CRIAR', 'mordeduras', info.lastInsertRowid, { protocolo, vitima: b.vitima_nome });
  res.status(201).json({ id: info.lastInsertRowid, protocolo });
});

router.put('/:id', (req, res) => {
  const m = db.prepare('SELECT * FROM mordeduras WHERE id = ?').get(req.params.id);
  if (!m) return res.status(404).json({ erro: 'Notificação não encontrada' });

  const b = req.body;
  let obsFim = m.observacao_fim_previsto;
  if (b.observacao_iniciada && b.data_ocorrencia) {
    const d = new Date(b.data_ocorrencia + 'T00:00:00');
    d.setDate(d.getDate() + 10);
    obsFim = d.toISOString().substring(0, 10);
  }

  db.prepare(`
    UPDATE mordeduras SET
      data_notificacao=?, data_ocorrencia=?,
      vitima_nome=?, vitima_cpf=?, vitima_data_nascimento=?, vitima_sexo=?, vitima_telefone=?,
      vitima_endereco=?, vitima_bairro=?, vitima_cidade=?, vitima_uf=?, vitima_cep=?,
      local_anatomico=?, tipo_ferimento=?, descricao_acidente=?, local_ocorrencia=?, bairro_ocorrencia=?,
      animal_id=?, animal_especie=?, animal_conhecido=?, animal_vacinado=?,
      animal_proprietario_nome=?, animal_proprietario_telefone=?, animal_proprietario_endereco=?,
      tipo_exposicao=?, conduta=?, profilaxia_iniciada=?, unidade_atendimento=?,
      observacao_iniciada=?, observacao_status=?, observacao_inicio=?, observacao_fim_previsto=?,
      observacao_resultado=?, status_caso=?, encerramento_data=?, encerramento_observacao=?,
      atualizado_em=CURRENT_TIMESTAMP
    WHERE id=?
  `).run(
    b.data_notificacao, b.data_ocorrencia || null,
    b.vitima_nome, (b.vitima_cpf || '').replace(/\D/g, '') || null,
    b.vitima_data_nascimento || null, b.vitima_sexo || null,
    (b.vitima_telefone || '').replace(/\D/g, '') || null,
    b.vitima_endereco || null, b.vitima_bairro || null,
    b.vitima_cidade || 'Barão de Cocais', b.vitima_uf || 'MG',
    (b.vitima_cep || '').replace(/\D/g, '') || null,
    b.local_anatomico || null, b.tipo_ferimento || null,
    b.descricao_acidente || null, b.local_ocorrencia || null, b.bairro_ocorrencia || null,
    b.animal_id || null, b.animal_especie || null,
    b.animal_conhecido ? 1 : 0, b.animal_vacinado || null,
    b.animal_proprietario_nome || null,
    (b.animal_proprietario_telefone || '').replace(/\D/g, '') || null,
    b.animal_proprietario_endereco || null,
    b.tipo_exposicao || null, b.conduta || null,
    b.profilaxia_iniciada ? 1 : 0, b.unidade_atendimento || null,
    b.observacao_iniciada ? 1 : 0,
    b.observacao_status || null,
    b.observacao_iniciada ? (b.observacao_inicio || b.data_ocorrencia || b.data_notificacao) : null,
    obsFim,
    b.observacao_resultado || null,
    b.status_caso || 'Aberto',
    b.encerramento_data || null, b.encerramento_observacao || null,
    req.params.id
  );

  registrarLog(req, 'ATUALIZAR', 'mordeduras', req.params.id);
  res.json({ ok: true });
});

router.delete('/:id', (req, res) => {
  db.prepare('DELETE FROM mordeduras WHERE id = ?').run(req.params.id);
  registrarLog(req, 'EXCLUIR', 'mordeduras', req.params.id);
  res.json({ ok: true });
});

// Observação dos 10 dias
router.post('/:id/observacao', (req, res) => {
  const { data, dia_observacao, situacao_animal, observacoes } = req.body;
  if (!data || !situacao_animal) {
    return res.status(400).json({ erro: 'Data e situação são obrigatórias' });
  }

  const info = db.prepare(`
    INSERT INTO mordedura_observacoes (mordedura_id, data, dia_observacao, situacao_animal, observacoes, usuario_id)
    VALUES (?, ?, ?, ?, ?, ?)
  `).run(req.params.id, data, dia_observacao || null, situacao_animal,
         observacoes || null, req.usuario.id);

  // Se animal morreu ou sumiu, atualiza o status da mordedura
  if (situacao_animal === 'Morreu') {
    db.prepare(`UPDATE mordeduras SET observacao_status='Animal Morreu' WHERE id=?`).run(req.params.id);
  } else if (situacao_animal === 'Sumiu') {
    db.prepare(`UPDATE mordeduras SET observacao_status='Animal Sumiu' WHERE id=?`).run(req.params.id);
  } else if (dia_observacao && parseInt(dia_observacao) >= 10) {
    db.prepare(`UPDATE mordeduras SET observacao_status='Concluída', observacao_resultado=? WHERE id=?`)
      .run(`Animal ${situacao_animal} no 10º dia`, req.params.id);
  }

  registrarLog(req, 'CRIAR', 'mordedura_observacoes', info.lastInsertRowid);
  res.status(201).json({ id: info.lastInsertRowid });
});

router.delete('/observacao/:id', (req, res) => {
  db.prepare('DELETE FROM mordedura_observacoes WHERE id = ?').run(req.params.id);
  res.json({ ok: true });
});

// CSV no formato SINAN para exportação
router.get('/exportar/sinan-csv', (req, res) => {
  const { ano, mes } = req.query;
  let where = 'WHERE 1=1';
  const params = [];
  if (ano) { where += " AND strftime('%Y', data_notificacao) = ?"; params.push(String(ano)); }
  if (mes) { where += " AND strftime('%m', data_notificacao) = ?"; params.push(String(mes).padStart(2, '0')); }

  const dados = db.prepare(`SELECT * FROM mordeduras ${where} ORDER BY data_notificacao`).all(...params);

  registrarLog(req, 'EXPORTAR_SINAN', 'mordeduras', null, { ano, mes, total: dados.length });

  const header = [
    'NU_NOTIFIC','TP_NOT','ID_AGRAVO','DT_NOTIFIC','SG_UF_NOT','ID_MUNIC_NOT',
    'NM_PACIENT','CPF_PACIENT','DT_NASC','CS_SEXO','NU_DDD_TEL','NU_TELEFON',
    'NM_LOGRADO','NU_BAIRRO','ID_MUNIC_RES','SG_UF','NU_CEP',
    'LOCAL_FERIM','TP_FERIMEN','LOCAL_OCOR','BAIRRO_OCOR',
    'TP_ESPECIE','ANIMAL_CON','ANIMAL_VAC','TP_EXPOSIC','CONDUTA',
    'PROFILAXIA','UN_ATENDIM','DT_OBS_INI','DT_OBS_FIM','RESULTADO_OBS','EVOLUCAO_CASO'
  ];

  const esc = v => {
    if (v == null) return '';
    let s = String(v);
    // Neutraliza CSV/Formula Injection: Excel/LibreOffice interpretam como
    // fórmula valores que começam com =, +, -, @, tab ou CR.
    if (/^[=+\-@\t\r]/.test(s)) s = `'${s}`;
    return /[",;\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };

  const linhas = [header.join(';')];
  for (const m of dados) {
    linhas.push([
      m.protocolo, '02' /* individual */, 'A82.9' /* CID Raiva */, m.data_notificacao,
      'MG', '310620', // IBGE Barão de Cocais
      m.vitima_nome, m.vitima_cpf, m.vitima_data_nascimento, m.vitima_sexo,
      '31', m.vitima_telefone,
      m.vitima_endereco, m.vitima_bairro, '310620', m.vitima_uf, m.vitima_cep,
      m.local_anatomico, m.tipo_ferimento, m.local_ocorrencia, m.bairro_ocorrencia,
      m.animal_especie, m.animal_conhecido ? 'Sim' : 'Não', m.animal_vacinado,
      m.tipo_exposicao, m.conduta,
      m.profilaxia_iniciada ? 'Sim' : 'Não', m.unidade_atendimento,
      m.observacao_inicio, m.observacao_fim_previsto, m.observacao_resultado,
      m.status_caso
    ].map(esc).join(';'));
  }

  const csv = '\uFEFF' + linhas.join('\n');
  res.setHeader('Content-Type', 'text/csv; charset=utf-8');
  res.setHeader('Content-Disposition',
    `attachment; filename="sinan_mordeduras_${ano || 'todos'}-${mes || ''}.csv"`);
  res.send(csv);
});

module.exports = router;
