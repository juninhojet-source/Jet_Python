/**
 * Rotas de Animais
 * SIGAZ - PMBC
 */
const express = require('express');
const QRCode = require('qrcode');
const db = require('../db/connection');
const { autenticar, autorizar } = require('../middleware/auth');
const { registrarLog } = require('../utils/logger');
const { gerarCodigoAnimal } = require('../utils/codigos');

const router = express.Router();
router.use(autenticar);

/**
 * GET /api/animais — Listar (com filtros e busca)
 */
router.get('/', (req, res) => {
  const { busca = '', especie = '', responsavel_id = '', limite = 50, pagina = 1 } = req.query;
  const offset = (parseInt(pagina) - 1) * parseInt(limite);

  let where = 'WHERE a.ativo = 1';
  const params = [];

  if (busca) {
    where += ' AND (a.nome LIKE ? OR a.codigo LIKE ? OR r.nome LIKE ?)';
    params.push(`%${busca}%`, `%${busca}%`, `%${busca}%`);
  }
  if (especie) {
    where += ' AND a.especie = ?';
    params.push(especie);
  }
  if (responsavel_id) {
    where += ' AND a.responsavel_id = ?';
    params.push(responsavel_id);
  }

  const total = db.prepare(`
    SELECT COUNT(*) as t FROM animais a
    LEFT JOIN responsaveis r ON r.id = a.responsavel_id
    ${where}
  `).get(...params).t;

  const dados = db.prepare(`
    SELECT a.*, r.nome AS responsavel_nome, r.cpf AS responsavel_cpf, r.telefone AS responsavel_telefone
    FROM animais a
    LEFT JOIN responsaveis r ON r.id = a.responsavel_id
    ${where}
    ORDER BY a.criado_em DESC
    LIMIT ? OFFSET ?
  `).all(...params, parseInt(limite), offset);

  res.json({ total, pagina: parseInt(pagina), dados });
});

/**
 * GET /api/animais/:id — Detalhar (com histórico completo)
 */
router.get('/:id', (req, res) => {
  const animal = db.prepare(`
    SELECT a.*, r.nome AS responsavel_nome, r.cpf AS responsavel_cpf,
           r.telefone AS responsavel_telefone, r.endereco AS responsavel_endereco,
           r.bairro AS responsavel_bairro
    FROM animais a
    LEFT JOIN responsaveis r ON r.id = a.responsavel_id
    WHERE a.id = ?
  `).get(req.params.id);

  if (!animal) return res.status(404).json({ erro: 'Animal não encontrado' });

  animal.vacinas = db.prepare('SELECT * FROM vacinas WHERE animal_id = ? ORDER BY data_aplicacao DESC').all(req.params.id);
  animal.vermifugacoes = db.prepare('SELECT * FROM vermifugacoes WHERE animal_id = ? ORDER BY data_aplicacao DESC').all(req.params.id);
  animal.ectoparasitarios = db.prepare('SELECT * FROM ectoparasitarios WHERE animal_id = ? ORDER BY data_aplicacao DESC').all(req.params.id);
  animal.zoonoses = db.prepare('SELECT * FROM zoonoses WHERE animal_id = ? ORDER BY data_notificacao DESC').all(req.params.id);
  animal.documentos = db.prepare('SELECT * FROM documentos WHERE animal_id = ? ORDER BY criado_em DESC').all(req.params.id);

  res.json(animal);
});

/**
 * POST /api/animais — Criar
 */
router.post('/', async (req, res) => {
  const {
    nome, especie, raca, sexo, data_nascimento, idade_aproximada, pelagem, porte, peso_kg,
    status_reprodutivo, habitacao, microchip, numero_identificacao, foto, responsavel_id, observacoes
  } = req.body;

  if (!nome || !especie) {
    return res.status(400).json({ erro: 'Nome e espécie são obrigatórios' });
  }

  const codigo = gerarCodigoAnimal();

  try {
    // Gerar QR Code (URL para consulta pública)
    const qrUrl = `${req.protocol}://${req.get('host')}/consulta.html?codigo=${codigo}`;
    const qrcodeData = await QRCode.toDataURL(qrUrl, { width: 200, margin: 1 });

    const info = db.prepare(`
      INSERT INTO animais (codigo, nome, especie, raca, sexo, data_nascimento, idade_aproximada,
                           pelagem, porte, peso_kg, status_reprodutivo, habitacao, microchip,
                           numero_identificacao, foto, qrcode, responsavel_id, observacoes)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `).run(codigo, nome, especie, raca || null, sexo || null, data_nascimento || null,
            idade_aproximada || null, pelagem || null, porte || null, peso_kg || null,
            status_reprodutivo || null, habitacao || null, microchip || null,
            numero_identificacao || null, foto || null, qrcodeData, responsavel_id || null, observacoes || null);

    registrarLog(req, 'CRIAR', 'animais', info.lastInsertRowid, { codigo, nome });
    res.status(201).json({ id: info.lastInsertRowid, codigo });
  } catch (err) {
    res.status(500).json({ erro: err.message });
  }
});

/**
 * PUT /api/animais/:id — Atualizar
 */
router.put('/:id', (req, res) => {
  const existe = db.prepare('SELECT id FROM animais WHERE id = ?').get(req.params.id);
  if (!existe) return res.status(404).json({ erro: 'Animal não encontrado' });

  const {
    nome, especie, raca, sexo, data_nascimento, idade_aproximada, pelagem, porte, peso_kg,
    status_reprodutivo, habitacao, microchip, numero_identificacao, foto, responsavel_id, observacoes
  } = req.body;

  db.prepare(`
    UPDATE animais SET
      nome=?, especie=?, raca=?, sexo=?, data_nascimento=?, idade_aproximada=?, pelagem=?,
      porte=?, peso_kg=?, status_reprodutivo=?, habitacao=?, microchip=?, numero_identificacao=?,
      foto=COALESCE(?, foto), responsavel_id=?, observacoes=?, atualizado_em=CURRENT_TIMESTAMP
    WHERE id=?
  `).run(nome, especie, raca || null, sexo || null, data_nascimento || null, idade_aproximada || null,
         pelagem || null, porte || null, peso_kg || null, status_reprodutivo || null,
         habitacao || null, microchip || null, numero_identificacao || null, foto || null,
         responsavel_id || null, observacoes || null, req.params.id);

  registrarLog(req, 'ATUALIZAR', 'animais', req.params.id);
  res.json({ ok: true });
});

/**
 * DELETE /api/animais/:id — Soft delete (inativar)
 */
router.delete('/:id', (req, res) => {
  db.prepare('UPDATE animais SET ativo = 0, atualizado_em = CURRENT_TIMESTAMP WHERE id = ?').run(req.params.id);
  registrarLog(req, 'INATIVAR', 'animais', req.params.id);
  res.json({ ok: true });
});

/**
 * POST /api/animais/excluir-lote — Inativa vários animais de uma vez
 * Body: { ids: [1, 2, 3, ...] }
 * Restrito a admin/ti para evitar exclusões acidentais em massa.
 */
router.post('/excluir-lote', autorizar('admin', 'ti'), (req, res) => {
  const { ids, definitivo } = req.body;
  if (!Array.isArray(ids) || ids.length === 0) {
    return res.status(400).json({ erro: 'Informe a lista de ids a excluir' });
  }
  // Sanitiza: só números inteiros
  const idsValidos = ids.map(n => parseInt(n)).filter(n => Number.isInteger(n) && n > 0);
  if (idsValidos.length === 0) {
    return res.status(400).json({ erro: 'Nenhum id válido informado' });
  }

  let afetados = 0;
  try {
    db.exec('BEGIN');
    if (definitivo) {
      // Exclusão DEFINITIVA: remove o animal e todos os seus registros de saúde.
      // Usado para limpar importações erradas. NÃO pode ser desfeito.
      const delVac = db.prepare('DELETE FROM vacinas WHERE animal_id = ?');
      const delVerm = db.prepare('DELETE FROM vermifugacoes WHERE animal_id = ?');
      const delEcto = db.prepare('DELETE FROM ectoparasitarios WHERE animal_id = ?');
      const delPront = db.prepare('DELETE FROM prontuario WHERE animal_id = ?');
      const delAnimal = db.prepare('DELETE FROM animais WHERE id = ?');
      for (const id of idsValidos) {
        delVac.run(id); delVerm.run(id); delEcto.run(id); delPront.run(id);
        const r = delAnimal.run(id);
        afetados += r.changes;
      }
    } else {
      // Inativação (reversível)
      const stmt = db.prepare('UPDATE animais SET ativo = 0, atualizado_em = CURRENT_TIMESTAMP WHERE id = ? AND ativo = 1');
      for (const id of idsValidos) {
        const r = stmt.run(id);
        afetados += r.changes;
      }
    }
    db.exec('COMMIT');
  } catch (err) {
    try { db.exec('ROLLBACK'); } catch(_){}
    return res.status(500).json({ erro: 'Erro ao excluir em lote: ' + err.message });
  }

  registrarLog(req, definitivo ? 'EXCLUIR_DEFINITIVO_LOTE' : 'INATIVAR_LOTE', 'animais', null,
    { quantidade: afetados, definitivo: !!definitivo });
  res.json({ ok: true, inativados: afetados, definitivo: !!definitivo });
});

/**
 * POST /api/animais/limpar-inativos — Remove DEFINITIVAMENTE todos os animais
 * já inativados (ativo=0) e seus registros de saúde. Serve para limpar de vez
 * importações que foram excluídas mas continuavam ocupando o banco e bloqueando
 * reimportação. Com ?simular conta sem apagar.
 */
router.post('/limpar-inativos', autorizar('admin', 'ti'), (req, res) => {
  const simular = req.body && req.body.simular;
  const inativos = db.prepare('SELECT id FROM animais WHERE ativo = 0').all().map(a => a.id);

  if (simular) {
    return res.json({ simulacao: true, animais_inativos: inativos.length });
  }
  if (inativos.length === 0) {
    return res.json({ ok: true, removidos: 0 });
  }

  let removidos = 0;
  try {
    db.exec('BEGIN');
    const delVac = db.prepare('DELETE FROM vacinas WHERE animal_id = ?');
    const delVerm = db.prepare('DELETE FROM vermifugacoes WHERE animal_id = ?');
    const delEcto = db.prepare('DELETE FROM ectoparasitarios WHERE animal_id = ?');
    const delPront = db.prepare('DELETE FROM prontuario WHERE animal_id = ?');
    const delAnimal = db.prepare('DELETE FROM animais WHERE id = ?');
    for (const id of inativos) {
      delVac.run(id); delVerm.run(id); delEcto.run(id); delPront.run(id);
      const r = delAnimal.run(id);
      removidos += r.changes;
    }
    db.exec('COMMIT');
  } catch (err) {
    try { db.exec('ROLLBACK'); } catch(_){}
    return res.status(500).json({ erro: 'Erro ao limpar inativos: ' + err.message });
  }

  registrarLog(req, 'LIMPAR_INATIVOS', 'animais', null, { removidos });
  res.json({ ok: true, removidos });
});

/**
 * GET /api/animais/consulta-publica/:codigo
 * Endpoint público para a leitura do QR Code (sem autenticação)
 */
router.get('/consulta-publica/:codigo', (req, res) => {
  // Esta rota está montada em router que usa autenticação. Vamos delegar.
  // Implementado em rota separada em server.js.
  res.status(404).end();
});

module.exports = router;
