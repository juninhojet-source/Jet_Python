/**
 * Rotas de Campanhas, Estoque e Denúncias
 * SIGAZ - PMBC
 */
const express = require('express');
const db = require('../db/connection');
const { autenticar } = require('../middleware/auth');
const { registrarLog } = require('../utils/logger');

const router = express.Router();

// ============ DENÚNCIAS PÚBLICAS (sem autenticação) ============
// (registradas em server.js separadamente)

router.use(autenticar);

// ============================================================
// CAMPANHAS
// ============================================================
router.get('/campanhas', (req, res) => {
  const dados = db.prepare(`
    SELECT c.*, (SELECT COUNT(*) FROM campanha_atendimentos WHERE campanha_id = c.id) AS atendimentos
    FROM campanhas c ORDER BY c.data_inicio DESC, c.criado_em DESC
  `).all();
  res.json({ dados });
});

router.get('/campanhas/:id', (req, res) => {
  const c = db.prepare('SELECT * FROM campanhas WHERE id = ?').get(req.params.id);
  if (!c) return res.status(404).json({ erro: 'Campanha não encontrada' });
  c.atendimentos = db.prepare(`
    SELECT ca.*, a.nome AS animal_nome, a.codigo AS animal_codigo, a.especie
    FROM campanha_atendimentos ca
    INNER JOIN animais a ON a.id = ca.animal_id
    WHERE ca.campanha_id = ?
    ORDER BY ca.criado_em DESC
  `).all(req.params.id);
  res.json(c);
});

router.post('/campanhas', (req, res) => {
  const { nome, tipo, descricao, data_inicio, data_fim, local, bairro, meta_atendimentos, status } = req.body;
  if (!nome) return res.status(400).json({ erro: 'Nome é obrigatório' });
  const info = db.prepare(`
    INSERT INTO campanhas (nome, tipo, descricao, data_inicio, data_fim, local, bairro, meta_atendimentos, status, usuario_id)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `).run(nome, tipo || null, descricao || null, data_inicio || null, data_fim || null,
         local || null, bairro || null, meta_atendimentos || 0, status || 'Planejada', req.usuario.id);
  registrarLog(req, 'CRIAR', 'campanhas', info.lastInsertRowid, { nome });
  res.status(201).json({ id: info.lastInsertRowid });
});

router.put('/campanhas/:id', (req, res) => {
  const c = db.prepare('SELECT id FROM campanhas WHERE id = ?').get(req.params.id);
  if (!c) return res.status(404).json({ erro: 'Campanha não encontrada' });
  const { nome, tipo, descricao, data_inicio, data_fim, local, bairro, meta_atendimentos, status } = req.body;
  db.prepare(`
    UPDATE campanhas SET nome=?, tipo=?, descricao=?, data_inicio=?, data_fim=?,
      local=?, bairro=?, meta_atendimentos=?, status=? WHERE id=?
  `).run(nome, tipo || null, descricao || null, data_inicio || null, data_fim || null,
         local || null, bairro || null, meta_atendimentos || 0, status || 'Planejada', req.params.id);
  registrarLog(req, 'ATUALIZAR', 'campanhas', req.params.id);
  res.json({ ok: true });
});

router.delete('/campanhas/:id', (req, res) => {
  db.prepare('DELETE FROM campanhas WHERE id = ?').run(req.params.id);
  registrarLog(req, 'EXCLUIR', 'campanhas', req.params.id);
  res.json({ ok: true });
});

router.post('/campanhas/:id/atendimentos', (req, res) => {
  const { animal_id, procedimento, observacoes } = req.body;
  if (!animal_id) return res.status(400).json({ erro: 'animal_id é obrigatório' });
  const info = db.prepare(`
    INSERT INTO campanha_atendimentos (campanha_id, animal_id, procedimento, observacoes)
    VALUES (?, ?, ?, ?)
  `).run(req.params.id, animal_id, procedimento || null, observacoes || null);
  registrarLog(req, 'CRIAR', 'campanha_atendimentos', info.lastInsertRowid);
  res.status(201).json({ id: info.lastInsertRowid });
});

router.delete('/campanhas/atendimentos/:id', (req, res) => {
  db.prepare('DELETE FROM campanha_atendimentos WHERE id = ?').run(req.params.id);
  res.json({ ok: true });
});

// ============================================================
// ESTOQUE
// ============================================================
router.get('/estoque/itens', (req, res) => {
  const dados = db.prepare(`
    SELECT i.*,
      COALESCE((SELECT SUM(CASE WHEN tipo IN ('Entrada','Ajuste') THEN quantidade
                                WHEN tipo IN ('Saída','Vencimento') THEN -quantidade END)
                FROM estoque_movimentos WHERE item_id = i.id), 0) AS saldo,
      (SELECT MIN(data_validade) FROM estoque_movimentos WHERE item_id = i.id AND data_validade IS NOT NULL AND data_validade >= date('now')) AS proxima_validade
    FROM estoque_itens i
    WHERE i.ativo = 1
    ORDER BY i.nome ASC
  `).all();
  res.json({ dados });
});

router.post('/estoque/itens', (req, res) => {
  const { nome, categoria, unidade, estoque_minimo, observacoes, saldo_inicial, lote_inicial, validade_inicial } = req.body;
  if (!nome) return res.status(400).json({ erro: 'Nome é obrigatório' });

  try {
    db.exec('BEGIN');
    const info = db.prepare(`
      INSERT INTO estoque_itens (nome, categoria, unidade, estoque_minimo, observacoes)
      VALUES (?, ?, ?, ?, ?)
    `).run(nome, categoria || null, unidade || 'unidade', estoque_minimo || 0, observacoes || null);

    registrarLog(req, 'CRIAR', 'estoque_itens', info.lastInsertRowid, { nome });

    // Se foi informado saldo inicial > 0, cria automaticamente um movimento de entrada
    const qtdInicial = parseInt(saldo_inicial) || 0;
    if (qtdInicial > 0) {
      const mov = db.prepare(`
        INSERT INTO estoque_movimentos (item_id, tipo, quantidade, lote, data_validade, motivo, usuario_id)
        VALUES (?, 'Entrada', ?, ?, ?, ?, ?)
      `).run(
        info.lastInsertRowid,
        qtdInicial,
        lote_inicial || null,
        validade_inicial || null,
        'Estoque inicial (cadastro do item)',
        req.usuario.id
      );
      registrarLog(req, 'CRIAR', 'estoque_movimentos', mov.lastInsertRowid,
        { tipo: 'Entrada', quantidade: qtdInicial, motivo: 'Estoque inicial' });
    }

    db.exec('COMMIT');
    res.status(201).json({ id: info.lastInsertRowid });
  } catch (err) {
    try { db.exec('ROLLBACK'); } catch(_){}
    res.status(500).json({ erro: 'Erro ao criar item: ' + err.message });
  }
});

router.put('/estoque/itens/:id', (req, res) => {
  const { nome, categoria, unidade, estoque_minimo, observacoes, ativo } = req.body;
  db.prepare(`
    UPDATE estoque_itens SET nome=?, categoria=?, unidade=?, estoque_minimo=?, observacoes=?, ativo=? WHERE id=?
  `).run(nome, categoria || null, unidade || 'unidade', estoque_minimo || 0,
         observacoes || null, ativo ? 1 : 0, req.params.id);
  registrarLog(req, 'ATUALIZAR', 'estoque_itens', req.params.id);
  res.json({ ok: true });
});

router.get('/estoque/movimentos', (req, res) => {
  const { item_id, limite = 100 } = req.query;
  let where = '';
  const params = [];
  if (item_id) { where = 'WHERE m.item_id = ?'; params.push(item_id); }
  const dados = db.prepare(`
    SELECT m.*, i.nome AS item_nome, u.nome AS usuario_nome,
           a.nome AS animal_nome, a.codigo AS animal_codigo
    FROM estoque_movimentos m
    INNER JOIN estoque_itens i ON i.id = m.item_id
    LEFT JOIN usuarios u ON u.id = m.usuario_id
    LEFT JOIN animais a ON a.id = m.animal_id
    ${where}
    ORDER BY m.criado_em DESC
    LIMIT ?
  `).all(...params, parseInt(limite));
  res.json({ dados });
});

router.post('/estoque/movimentos', (req, res) => {
  const { item_id, tipo, quantidade, lote, data_validade, motivo, animal_id } = req.body;
  if (!item_id || !tipo || !quantidade) {
    return res.status(400).json({ erro: 'item_id, tipo e quantidade são obrigatórios' });
  }
  const info = db.prepare(`
    INSERT INTO estoque_movimentos (item_id, tipo, quantidade, lote, data_validade, motivo, animal_id, usuario_id)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
  `).run(item_id, tipo, Math.abs(parseInt(quantidade)), lote || null,
         data_validade || null, motivo || null, animal_id || null, req.usuario.id);
  registrarLog(req, 'CRIAR', 'estoque_movimentos', info.lastInsertRowid, { tipo, quantidade });
  res.status(201).json({ id: info.lastInsertRowid });
});

/**
 * Ajuste de saldo — calcula a diferença entre saldo atual e novo,
 * e gera uma movimentação rastreável com motivo obrigatório.
 */
router.post('/estoque/itens/:id/ajustar', (req, res) => {
  const { saldo_novo, motivo, observacao } = req.body;
  const itemId = parseInt(req.params.id);

  if (saldo_novo == null || saldo_novo === '') {
    return res.status(400).json({ erro: 'Saldo novo é obrigatório' });
  }
  if (!motivo) {
    return res.status(400).json({ erro: 'Motivo do ajuste é obrigatório' });
  }

  const item = db.prepare('SELECT id, nome FROM estoque_itens WHERE id = ?').get(itemId);
  if (!item) return res.status(404).json({ erro: 'Item não encontrado' });

  const saldoAtual = db.prepare(`
    SELECT COALESCE(SUM(CASE WHEN tipo = 'Entrada' THEN quantidade ELSE -quantidade END), 0) AS saldo
    FROM estoque_movimentos WHERE item_id = ?
  `).get(itemId).saldo;

  const novoSaldo = parseInt(saldo_novo);
  if (isNaN(novoSaldo) || novoSaldo < 0) {
    return res.status(400).json({ erro: 'Saldo deve ser um número inteiro maior ou igual a zero' });
  }

  const diferenca = novoSaldo - saldoAtual;
  if (diferenca === 0) {
    return res.json({ ok: true, mensagem: 'Saldo informado é igual ao atual; nenhum ajuste gerado.', diferenca: 0 });
  }

  const tipo = diferenca > 0 ? 'Entrada' : 'Saída';
  const quantidade = Math.abs(diferenca);
  const motivoCompleto = `[Ajuste] ${motivo}${observacao ? ' — ' + observacao : ''} (de ${saldoAtual} para ${novoSaldo})`;

  const mov = db.prepare(`
    INSERT INTO estoque_movimentos (item_id, tipo, quantidade, motivo, usuario_id)
    VALUES (?, ?, ?, ?, ?)
  `).run(itemId, tipo, quantidade, motivoCompleto, req.usuario.id);

  registrarLog(req, 'AJUSTAR', 'estoque_movimentos', mov.lastInsertRowid,
    { item_id: itemId, item_nome: item.nome, saldo_anterior: saldoAtual,
      saldo_novo: novoSaldo, diferenca, motivo });

  res.json({
    ok: true,
    saldo_anterior: saldoAtual,
    saldo_novo: novoSaldo,
    diferenca,
    movimento_id: mov.lastInsertRowid
  });
});

router.get('/estoque/alertas', (req, res) => {
  // Itens abaixo do estoque mínimo
  const baixoEstoque = db.prepare(`
    SELECT i.id, i.nome, i.categoria, i.estoque_minimo, i.unidade,
      COALESCE((SELECT SUM(CASE WHEN tipo IN ('Entrada','Ajuste') THEN quantidade
                                WHEN tipo IN ('Saída','Vencimento') THEN -quantidade END)
                FROM estoque_movimentos WHERE item_id = i.id), 0) AS saldo
    FROM estoque_itens i WHERE i.ativo = 1
  `).all().filter(i => i.saldo <= i.estoque_minimo);

  // Lotes vencendo em até 30 dias
  const vencendo = db.prepare(`
    SELECT m.id, m.item_id, m.lote, m.data_validade, m.quantidade, i.nome AS item_nome
    FROM estoque_movimentos m
    INNER JOIN estoque_itens i ON i.id = m.item_id
    WHERE m.tipo = 'Entrada' AND m.data_validade IS NOT NULL
      AND m.data_validade BETWEEN date('now') AND date('now', '+30 days')
    ORDER BY m.data_validade ASC
  `).all();

  res.json({ baixoEstoque, vencendo });
});

// ============================================================
// DENÚNCIAS (autenticadas — para fiscal atender)
// ============================================================
router.get('/denuncias', (req, res) => {
  const { status, bairro } = req.query;
  let where = 'WHERE 1=1';
  const params = [];
  if (status) { where += ' AND status = ?'; params.push(status); }
  if (bairro) { where += ' AND bairro LIKE ?'; params.push('%' + bairro + '%'); }
  const dados = db.prepare(`
    SELECT d.*, u.nome AS fiscal_nome
    FROM denuncias d
    LEFT JOIN usuarios u ON u.id = d.fiscal_id
    ${where}
    ORDER BY d.criado_em DESC
  `).all(...params);
  res.json({ dados });
});

router.get('/denuncias/:id', (req, res) => {
  const d = db.prepare(`
    SELECT d.*, u.nome AS fiscal_nome FROM denuncias d
    LEFT JOIN usuarios u ON u.id = d.fiscal_id WHERE d.id = ?
  `).get(req.params.id);
  if (!d) return res.status(404).json({ erro: 'Denúncia não encontrada' });
  res.json(d);
});

router.put('/denuncias/:id', (req, res) => {
  const { status, desfecho, fiscal_id, data_atendimento } = req.body;
  const d = db.prepare('SELECT id FROM denuncias WHERE id = ?').get(req.params.id);
  if (!d) return res.status(404).json({ erro: 'Denúncia não encontrada' });

  db.prepare(`
    UPDATE denuncias SET status=?, desfecho=?, fiscal_id=?, data_atendimento=?,
      atualizado_em=CURRENT_TIMESTAMP WHERE id=?
  `).run(status, desfecho || null, fiscal_id || req.usuario.id,
         data_atendimento || null, req.params.id);

  registrarLog(req, 'ATUALIZAR', 'denuncias', req.params.id, { status });
  res.json({ ok: true });
});

module.exports = router;
