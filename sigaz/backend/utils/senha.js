/**
 * Validação de senha forte conforme regras configuráveis
 * SIGAZ - PMBC
 */
const db = require('../db/connection');

function getConfig(chave, padrao) {
  const r = db.prepare('SELECT valor FROM configuracoes WHERE chave = ?').get(chave);
  return r ? r.valor : padrao;
}

/**
 * Valida uma senha contra as regras da prefeitura.
 * Retorna { valida: true } ou { valida: false, motivos: [...] }
 */
function validarSenha(senha) {
  const motivos = [];
  if (!senha || typeof senha !== 'string') {
    return { valida: false, motivos: ['Senha não informada'] };
  }

  const min = parseInt(getConfig('senha_min_caracteres', '8'));
  if (senha.length < min) motivos.push(`Mínimo ${min} caracteres`);

  if (getConfig('senha_exige_maiuscula', '1') === '1' && !/[A-Z]/.test(senha)) {
    motivos.push('Deve conter ao menos uma letra maiúscula');
  }
  if (getConfig('senha_exige_numero', '1') === '1' && !/[0-9]/.test(senha)) {
    motivos.push('Deve conter ao menos um número');
  }
  if (getConfig('senha_exige_especial', '0') === '1' && !/[!@#$%^&*(),.?":{}|<>_\-+=\/\\]/.test(senha)) {
    motivos.push('Deve conter ao menos um caractere especial');
  }

  // Senhas óbvias (rejeita as 10 mais comuns)
  const fracas = ['senha', 'password', '12345678', 'admin', 'admin123',
                  '123456', 'qwerty', 'abc123', 'mudar123', 'sigaz123'];
  if (fracas.includes(senha.toLowerCase())) {
    motivos.push('Senha muito comum/previsível');
  }

  return { valida: motivos.length === 0, motivos };
}

module.exports = { validarSenha, getConfig };
