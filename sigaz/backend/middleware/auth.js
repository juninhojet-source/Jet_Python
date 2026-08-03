/**
 * Middleware de Autenticação JWT
 * SIGAZ - PMBC
 */
const jwt = require('jsonwebtoken');
require('dotenv').config();

const JWT_SECRET = process.env.JWT_SECRET || 'sigaz-default-secret-change-me';

/**
 * Verifica o token JWT no header Authorization
 */
function autenticar(req, res, next) {
  const authHeader = req.headers.authorization;

  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return res.status(401).json({ erro: 'Token não fornecido' });
  }

  const token = authHeader.substring(7);

  try {
    const payload = jwt.verify(token, JWT_SECRET);
    req.usuario = payload;

    // Se o usuário precisa trocar senha, só permite acessar:
    // - GET /api/auth/me
    // - POST /api/auth/trocar-senha
    // - POST /api/auth/logout
    if (payload.deve_trocar_senha) {
      const liberadas = [
        '/api/auth/me',
        '/api/auth/trocar-senha',
        '/api/auth/logout'
      ];
      if (!liberadas.includes(req.path) && !liberadas.includes(req.originalUrl)) {
        return res.status(428).json({
          erro: 'Você deve trocar sua senha antes de prosseguir.',
          codigo: 'TROCAR_SENHA_OBRIGATORIO'
        });
      }
    }

    next();
  } catch (err) {
    return res.status(401).json({ erro: 'Token inválido ou expirado' });
  }
}

/**
 * Verifica se o usuário tem um dos perfis permitidos
 * Uso: autorizar('admin', 'veterinario')
 */
function autorizar(...perfisPermitidos) {
  return (req, res, next) => {
    if (!req.usuario) {
      return res.status(401).json({ erro: 'Não autenticado' });
    }
    if (!perfisPermitidos.includes(req.usuario.perfil)) {
      return res.status(403).json({ erro: 'Acesso negado para este perfil' });
    }
    next();
  };
}

module.exports = { autenticar, autorizar, JWT_SECRET };
