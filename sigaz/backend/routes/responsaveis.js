/**
 * Rotas de Responsáveis (Tutores)
 * SIGAZ - PMBC
 */
const express = require('express');
const db = require('../db/connection');
const { autenticar } = require('../middleware/auth');
const { registrarLog } = require('../utils/logger');
const { validarCpf } = require('../utils/cpf');

const router = express.Router();
router.use(autenticar);

/**
 * GET /api/responsaveis  — Listar (com busca)
 */
router.get('/', (req, res) => {
  const { busca = '', bairro = '', limite = 50, pagina = 1 } = req.query;
  const offset = (parseInt(pagina) - 1) * parseInt(limite);

  let where = 'WHERE 1=1';
  const params = [];

  if (busca) {
    where += ' AND (nome LIKE ? OR cpf LIKE ? OR telefone LIKE ?)';
    params.push(`%${busca}%`, `%${busca}%`, `%${busca}%`);
  }
  if (bairro) {
    where += ' AND bairro = ?';
    params.push(bairro);
  }

  const total = db.prepare(`SELECT COUNT(*) as t FROM responsaveis ${where}`).get(...params).t;
  const dados = db.prepare(`
    SELECT * FROM responsaveis ${where}
    ORDER BY nome ASC LIMIT ? OFFSET ?
  `).all(...params, parseInt(limite), offset);

  res.json({ total, pagina: parseInt(pagina), dados });
});

/**
 * GET /api/responsaveis/:id  — Detalhar
 */
router.get('/:id', (req, res) => {
  const resp = db.prepare('SELECT * FROM responsaveis WHERE id = ?').get(req.params.id);
  if (!resp) return res.status(404).json({ erro: 'Responsável não encontrado' });

  const animais = db.prepare(`
    SELECT id, codigo, nome, especie, raca FROM animais
    WHERE responsavel_id = ? AND ativo = 1
  `).all(req.params.id);

  res.json({ ...resp, animais });
});

/**
 * POST /api/responsaveis  — Criar
 */
router.post('/', (req, res) => {
  const { nome, cpf, rg, telefone, email, endereco, numero, bairro, cidade, uf, cep, observacoes } = req.body;

  if (!nome || !cpf) {
    return res.status(400).json({ erro: 'Nome e documento (CPF/CNPJ) são obrigatórios' });
  }
  const cpfLimpo = String(cpf).replace(/\D/g, '');

  // Aceita CPF (11 dígitos, com validação) ou CNPJ (14 dígitos)
  if (cpfLimpo.length === 14) {
    // CNPJ — valida apenas o tamanho (ONGs, município, empresas)
  } else if (cpfLimpo.length === 11) {
    if (!validarCpf(cpfLimpo)) {
      return res.status(400).json({ erro: 'CPF inválido. Verifique os dígitos informados.' });
    }
  } else {
    return res.status(400).json({ erro: 'Documento inválido. Informe um CPF (11 dígitos) ou CNPJ (14 dígitos).' });
  }

  // Verificar duplicidade
  const existe = db.prepare('SELECT id FROM responsaveis WHERE cpf = ?').get(cpfLimpo);
  if (existe) {
    return res.status(409).json({ erro: 'Já existe responsável com este documento', id: existe.id });
  }

  try {
    const info = db.prepare(`
      INSERT INTO responsaveis (nome, cpf, rg, telefone, email, endereco, numero, bairro, cidade, uf, cep, observacoes)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `).run(nome, cpfLimpo, rg || null, telefone || null, email || null, endereco || null,
            numero || null, bairro || null, cidade || 'Barão de Cocais', uf || 'MG', cep || null, observacoes || null);

    registrarLog(req, 'CRIAR', 'responsaveis', info.lastInsertRowid, { nome, cpf: cpfLimpo });
    res.status(201).json({ id: info.lastInsertRowid });
  } catch (err) {
    res.status(500).json({ erro: err.message });
  }
});

/**
 * PUT /api/responsaveis/:id  — Atualizar
 */
router.put('/:id', (req, res) => {
  const { nome, cpf, rg, telefone, email, endereco, numero, bairro, cidade, uf, cep, observacoes } = req.body;

  const existe = db.prepare('SELECT id FROM responsaveis WHERE id = ?').get(req.params.id);
  if (!existe) return res.status(404).json({ erro: 'Responsável não encontrado' });

  const cpfLimpo = cpf ? String(cpf).replace(/\D/g, '') : null;

  // Validar documento se fornecido: CPF (11, com dígitos) ou CNPJ (14)
  if (cpfLimpo) {
    if (cpfLimpo.length === 14) {
      // CNPJ válido por tamanho
    } else if (cpfLimpo.length === 11) {
      if (!validarCpf(cpfLimpo)) {
        return res.status(400).json({ erro: 'CPF inválido. Verifique os dígitos informados.' });
      }
    } else {
      return res.status(400).json({ erro: 'Documento inválido. Informe CPF (11 dígitos) ou CNPJ (14 dígitos).' });
    }
  }

  // Verificar duplicidade (mas permitir manter o próprio)
  if (cpfLimpo) {
    const outro = db.prepare('SELECT id FROM responsaveis WHERE cpf = ? AND id != ?').get(cpfLimpo, req.params.id);
    if (outro) {
      return res.status(409).json({ erro: 'Já existe outro responsável com este CPF' });
    }
  }

  db.prepare(`
    UPDATE responsaveis
    SET nome=?, cpf=?, rg=?, telefone=?, email=?, endereco=?, numero=?, bairro=?, cidade=?, uf=?, cep=?, observacoes=?,
        atualizado_em=CURRENT_TIMESTAMP
    WHERE id=?
  `).run(nome, cpfLimpo, rg || null, telefone || null, email || null, endereco || null,
         numero || null, bairro || null, cidade || 'Barão de Cocais', uf || 'MG', cep || null, observacoes || null, req.params.id);

  registrarLog(req, 'ATUALIZAR', 'responsaveis', req.params.id);
  res.json({ ok: true });
});

/**
 * DELETE /api/responsaveis/:id
 */
router.delete('/:id', (req, res) => {
  // Verificar se há animais vinculados
  const animais = db.prepare('SELECT COUNT(*) as t FROM animais WHERE responsavel_id = ? AND ativo = 1').get(req.params.id).t;
  if (animais > 0) {
    return res.status(409).json({ erro: `Existem ${animais} animal(is) vinculado(s). Remova-os ou transfira-os antes.` });
  }
  db.prepare('DELETE FROM responsaveis WHERE id = ?').run(req.params.id);
  registrarLog(req, 'EXCLUIR', 'responsaveis', req.params.id);
  res.json({ ok: true });
});

module.exports = router;
