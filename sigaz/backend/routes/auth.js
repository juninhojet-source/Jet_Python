/**
 * Rotas de Autenticação
 * SIGAZ - PMBC
 */
const express = require('express');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const db = require('../db/connection');
const { autenticar, JWT_SECRET } = require('../middleware/auth');
const { registrarLog } = require('../utils/logger');
const { validarSenha, getConfig } = require('../utils/senha');
require('dotenv').config();

const router = express.Router();
const JWT_EXPIRES_IN = process.env.JWT_EXPIRES_IN || '8h';

/**
 * POST /api/auth/login
 * Aceita identificador como email ou username
 * Implementa bloqueio após N tentativas falhas
 */
router.post('/login', (req, res) => {
  const { email, usuario, senha } = req.body;
  const identificador = (usuario || email || '').trim();

  if (!identificador || !senha) {
    return res.status(400).json({ erro: 'Usuário e senha são obrigatórios' });
  }

  const usuarioDb = db.prepare(`
    SELECT id, nome, username, email, senha_hash, perfil, ativo,
           deve_trocar_senha, tentativas_falhas, bloqueado_ate
    FROM usuarios WHERE email = ? OR username = ?
  `).get(identificador, identificador);

  // Resposta genérica para não vazar se o usuário existe ou não
  const respostaInvalida = () => res.status(401).json({ erro: 'Usuário ou senha inválidos' });

  if (!usuarioDb || !usuarioDb.ativo) {
    return respostaInvalida();
  }

  // Verificar bloqueio temporário
  if (usuarioDb.bloqueado_ate) {
    const ate = new Date(usuarioDb.bloqueado_ate.replace(' ', 'T') + 'Z');
    if (ate > new Date()) {
      const minutosRestantes = Math.ceil((ate - new Date()) / 60000);
      return res.status(423).json({
        erro: `Usuário bloqueado por excesso de tentativas. Tente novamente em ${minutosRestantes} minuto(s).`
      });
    }
    // Bloqueio expirou — limpar
    db.prepare('UPDATE usuarios SET bloqueado_ate = NULL, tentativas_falhas = 0 WHERE id = ?').run(usuarioDb.id);
  }

  const senhaOk = bcrypt.compareSync(senha, usuarioDb.senha_hash);
  if (!senhaOk) {
    // Incrementar tentativas falhas
    const maxTentativas = parseInt(getConfig('max_tentativas_login', '5'));
    const minutosBloqueio = parseInt(getConfig('minutos_bloqueio', '15'));
    const novaQtd = (usuarioDb.tentativas_falhas || 0) + 1;

    if (novaQtd >= maxTentativas) {
      const ate = new Date(Date.now() + minutosBloqueio * 60000);
      db.prepare('UPDATE usuarios SET tentativas_falhas = ?, bloqueado_ate = ? WHERE id = ?')
        .run(novaQtd, ate.toISOString().substring(0, 19).replace('T', ' '), usuarioDb.id);
      registrarLog({ usuario: { id: usuarioDb.id }, ip: req.ip }, 'BLOQUEIO_LOGIN', 'usuarios', usuarioDb.id,
        { tentativas: novaQtd, bloqueado_ate: ate.toISOString() });
      return res.status(423).json({
        erro: `Usuário bloqueado por ${minutosBloqueio} minutos devido a ${maxTentativas} tentativas falhas.`
      });
    }

    db.prepare('UPDATE usuarios SET tentativas_falhas = ? WHERE id = ?').run(novaQtd, usuarioDb.id);
    registrarLog({ usuario: { id: usuarioDb.id }, ip: req.ip }, 'LOGIN_FALHA', 'usuarios', usuarioDb.id,
      { tentativas: novaQtd, max: maxTentativas });
    const tentativasRestantes = maxTentativas - novaQtd;
    return res.status(401).json({
      erro: `Usuário ou senha inválidos. ${tentativasRestantes} tentativa(s) antes do bloqueio.`
    });
  }

  // Login OK — resetar contadores e registrar último login
  db.prepare(`
    UPDATE usuarios SET tentativas_falhas = 0, bloqueado_ate = NULL,
                        ultimo_login = CURRENT_TIMESTAMP WHERE id = ?
  `).run(usuarioDb.id);

  const payload = {
    id: usuarioDb.id,
    nome: usuarioDb.nome,
    username: usuarioDb.username,
    email: usuarioDb.email,
    perfil: usuarioDb.perfil,
    deve_trocar_senha: !!usuarioDb.deve_trocar_senha
  };
  const token = jwt.sign(payload, JWT_SECRET, { expiresIn: JWT_EXPIRES_IN });

  registrarLog({ usuario: payload, ip: req.ip }, 'LOGIN', 'usuarios', usuarioDb.id);

  res.json({
    token,
    usuario: payload,
    deve_trocar_senha: !!usuarioDb.deve_trocar_senha
  });
});

/**
 * POST /api/auth/trocar-senha
 * O próprio usuário troca a senha (sempre exigido após primeiro login com senha padrão)
 */
router.post('/trocar-senha', autenticar, (req, res) => {
  const { senha_atual, senha_nova } = req.body;

  if (!senha_atual || !senha_nova) {
    return res.status(400).json({ erro: 'Senha atual e nova são obrigatórias' });
  }

  const usuario = db.prepare('SELECT senha_hash FROM usuarios WHERE id = ?').get(req.usuario.id);
  if (!usuario) return res.status(404).json({ erro: 'Usuário não encontrado' });

  if (!bcrypt.compareSync(senha_atual, usuario.senha_hash)) {
    return res.status(401).json({ erro: 'Senha atual incorreta' });
  }

  // Validar a nova senha
  const validacao = validarSenha(senha_nova);
  if (!validacao.valida) {
    return res.status(400).json({ erro: 'Senha inválida: ' + validacao.motivos.join('; ') });
  }

  // Não permitir reusar a senha atual
  if (bcrypt.compareSync(senha_nova, usuario.senha_hash)) {
    return res.status(400).json({ erro: 'A nova senha deve ser diferente da atual' });
  }

  const novoHash = bcrypt.hashSync(senha_nova, 10);
  db.prepare(`
    UPDATE usuarios SET senha_hash = ?, deve_trocar_senha = 0, atualizado_em = CURRENT_TIMESTAMP
    WHERE id = ?
  `).run(novoHash, req.usuario.id);

  registrarLog(req, 'TROCAR_SENHA', 'usuarios', req.usuario.id);
  res.json({ ok: true, mensagem: 'Senha alterada com sucesso' });
});

/**
 * GET /api/auth/me
 */
router.get('/me', autenticar, (req, res) => {
  res.json({ usuario: req.usuario });
});

/**
 * POST /api/auth/logout
 */
router.post('/logout', autenticar, (req, res) => {
  registrarLog(req, 'LOGOUT', 'usuarios', req.usuario.id);
  res.json({ ok: true });
});

module.exports = router;
