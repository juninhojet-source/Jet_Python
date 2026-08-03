/**
 * Rotas de Usuários (gestão administrativa)
 * SIGAZ - PMBC
 */
const express = require('express');
const bcrypt = require('bcryptjs');
const db = require('../db/connection');
const { autenticar, autorizar } = require('../middleware/auth');
const { registrarLog } = require('../utils/logger');
const { validarSenha } = require('../utils/senha');

const router = express.Router();
router.use(autenticar);

/**
 * GET /api/usuarios — somente admin
 */
router.get('/', autorizar('admin', 'ti'), (req, res) => {
  const dados = db.prepare(`
    SELECT id, nome, username, email, perfil, ativo, cpf, telefone,
           deve_trocar_senha, tentativas_falhas, bloqueado_ate, ultimo_login,
           criado_em
    FROM usuarios
    WHERE perfil != 'cidadao'
    ORDER BY nome ASC
  `).all();
  res.json({ dados });
});

router.post('/', autorizar('admin', 'ti'), (req, res) => {
  const { nome, username, email, senha, perfil, cpf, telefone } = req.body;
  if (!nome || !email || !senha || !perfil) {
    return res.status(400).json({ erro: 'Nome, e-mail, senha e perfil são obrigatórios' });
  }
  if (username && !/^[a-zA-Z0-9._-]+$/.test(username)) {
    return res.status(400).json({ erro: 'Usuário deve conter apenas letras, números, ponto, hífen e underline' });
  }

  // Validar senha forte
  const v = validarSenha(senha);
  if (!v.valida) {
    return res.status(400).json({ erro: 'Senha não atende aos requisitos: ' + v.motivos.join('; ') });
  }

  const existeEmail = db.prepare('SELECT id FROM usuarios WHERE email = ?').get(email);
  if (existeEmail) return res.status(409).json({ erro: 'E-mail já cadastrado' });

  if (username) {
    const existeUser = db.prepare('SELECT id FROM usuarios WHERE username = ?').get(username);
    if (existeUser) return res.status(409).json({ erro: 'Nome de usuário já cadastrado' });
  }

  const senhaHash = bcrypt.hashSync(senha, 10);
  // Por padrão, força troca de senha no primeiro login
  const info = db.prepare(`
    INSERT INTO usuarios (nome, username, email, senha_hash, perfil, cpf, telefone, deve_trocar_senha)
    VALUES (?, ?, ?, ?, ?, ?, ?, 1)
  `).run(nome, username || null, email, senhaHash, perfil, cpf || null, telefone || null);

  registrarLog(req, 'CRIAR', 'usuarios', info.lastInsertRowid, { username, email, perfil });
  res.status(201).json({ id: info.lastInsertRowid });
});

router.put('/:id', autorizar('admin', 'ti'), (req, res) => {
  const { nome, username, email, perfil, ativo, senha, cpf, telefone } = req.body;

  const atual = db.prepare('SELECT * FROM usuarios WHERE id = ?').get(req.params.id);
  if (!atual) return res.status(404).json({ erro: 'Usuário não encontrado' });

  if (username && !/^[a-zA-Z0-9._-]+$/.test(username)) {
    return res.status(400).json({ erro: 'Usuário deve conter apenas letras, números, ponto, hífen e underline' });
  }

  if (username) {
    const outro = db.prepare('SELECT id FROM usuarios WHERE username = ? AND id != ?').get(username, req.params.id);
    if (outro) return res.status(409).json({ erro: 'Nome de usuário já está em uso' });
  }

  // Calcular diff para auditoria
  const diff = {};
  const campos = { nome, username, email, perfil, cpf, telefone };
  for (const [k, v] of Object.entries(campos)) {
    const novoVal = v == null ? null : v;
    const antigoVal = atual[k] == null ? null : atual[k];
    if (String(novoVal) !== String(antigoVal)) {
      diff[k] = { de: antigoVal, para: novoVal };
    }
  }
  if (atual.ativo !== (ativo ? 1 : 0)) {
    diff.ativo = { de: atual.ativo ? 'Ativo' : 'Inativo', para: ativo ? 'Ativo' : 'Inativo' };
  }

  if (senha) {
    const v = validarSenha(senha);
    if (!v.valida) {
      return res.status(400).json({ erro: 'Senha não atende aos requisitos: ' + v.motivos.join('; ') });
    }
    const senhaHash = bcrypt.hashSync(senha, 10);
    // Quando o admin reseta a senha, força o usuário a trocar no próximo login
    db.prepare(`
      UPDATE usuarios SET nome=?, username=?, email=?, perfil=?, ativo=?, senha_hash=?, cpf=?, telefone=?,
                          deve_trocar_senha=1, atualizado_em=CURRENT_TIMESTAMP
      WHERE id=?
    `).run(nome, username || null, email, perfil, ativo ? 1 : 0, senhaHash, cpf || null, telefone || null, req.params.id);
    diff.senha = { de: '***', para: '*** (resetada — usuário deverá trocar no próximo login)' };
  } else {
    db.prepare(`
      UPDATE usuarios SET nome=?, username=?, email=?, perfil=?, ativo=?, cpf=?, telefone=?,
                          atualizado_em=CURRENT_TIMESTAMP
      WHERE id=?
    `).run(nome, username || null, email, perfil, ativo ? 1 : 0, cpf || null, telefone || null, req.params.id);
  }

  registrarLog(req, 'ATUALIZAR', 'usuarios', req.params.id, diff);
  res.json({ ok: true, alteracoes: Object.keys(diff).length });
});

router.delete('/:id', autorizar('admin', 'ti'), (req, res) => {
  if (parseInt(req.params.id) === req.usuario.id) {
    return res.status(400).json({ erro: 'Você não pode excluir a si mesmo' });
  }
  db.prepare('UPDATE usuarios SET ativo = 0 WHERE id = ?').run(req.params.id);
  registrarLog(req, 'INATIVAR', 'usuarios', req.params.id);
  res.json({ ok: true });
});

/**
 * POST /api/usuarios/:id/desbloquear
 * Admin pode desbloquear manualmente um usuário bloqueado por tentativas
 */
router.post('/:id/desbloquear', autorizar('admin', 'ti'), (req, res) => {
  const u = db.prepare('SELECT id, nome FROM usuarios WHERE id = ?').get(req.params.id);
  if (!u) return res.status(404).json({ erro: 'Usuário não encontrado' });

  db.prepare(`
    UPDATE usuarios SET tentativas_falhas = 0, bloqueado_ate = NULL
    WHERE id = ?
  `).run(req.params.id);

  registrarLog(req, 'DESBLOQUEAR', 'usuarios', req.params.id, { usuario: u.nome });
  res.json({ ok: true });
});

/**
 * POST /api/usuarios/:id/resetar-senha
 * Admin gera nova senha temporária e força troca no próximo login
 */
router.post('/:id/resetar-senha', autorizar('admin', 'ti'), (req, res) => {
  const u = db.prepare('SELECT id, nome, username FROM usuarios WHERE id = ?').get(req.params.id);
  if (!u) return res.status(404).json({ erro: 'Usuário não encontrado' });

  // Gera senha temporária forte
  const senhaTemp = gerarSenhaTemporaria();
  const senhaHash = bcrypt.hashSync(senhaTemp, 10);

  db.prepare(`
    UPDATE usuarios SET senha_hash = ?, deve_trocar_senha = 1,
                        tentativas_falhas = 0, bloqueado_ate = NULL,
                        atualizado_em = CURRENT_TIMESTAMP
    WHERE id = ?
  `).run(senhaHash, req.params.id);

  registrarLog(req, 'RESETAR_SENHA', 'usuarios', req.params.id, { usuario: u.nome });
  res.json({
    ok: true,
    senha_temporaria: senhaTemp,
    mensagem: `Informe ao usuário ${u.nome} a senha temporária. Ele será obrigado a trocá-la no próximo login.`
  });
});

function gerarSenhaTemporaria() {
  // 10 caracteres: 1 maiúscula + 1 número + 8 letras/números aleatórios garantindo força
  const mai = 'ABCDEFGHJKLMNPQRSTUVWXYZ'; // sem I, O para evitar confusão
  const min = 'abcdefghjkmnpqrstuvwxyz';
  const num = '23456789';
  const todos = mai + min + num;
  let s = '';
  s += mai[Math.floor(Math.random() * mai.length)];
  s += num[Math.floor(Math.random() * num.length)];
  for (let i = 0; i < 8; i++) s += todos[Math.floor(Math.random() * todos.length)];
  // Embaralhar
  return s.split('').sort(() => Math.random() - 0.5).join('');
}

/**
 * GET /api/usuarios/logs/auditoria
 */
router.get('/logs/auditoria', autorizar('admin', 'ti'), (req, res) => {
  const { acao, usuario_id, entidade, limite = 200 } = req.query;
  let where = 'WHERE 1=1';
  const params = [];
  if (acao) { where += ' AND l.acao = ?'; params.push(acao); }
  if (usuario_id) { where += ' AND l.usuario_id = ?'; params.push(usuario_id); }
  if (entidade) { where += ' AND l.entidade = ?'; params.push(entidade); }

  const dados = db.prepare(`
    SELECT l.*, u.nome AS usuario_nome
    FROM logs l
    LEFT JOIN usuarios u ON u.id = l.usuario_id
    ${where}
    ORDER BY l.criado_em DESC
    LIMIT ?
  `).all(...params, parseInt(limite));
  res.json({ dados });
});

module.exports = router;
