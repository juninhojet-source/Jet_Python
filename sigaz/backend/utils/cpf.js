/**
 * Validação de CPF — dígitos verificadores
 * SIGAZ - PMBC
 */
function validarCpf(cpf) {
  if (!cpf) return false;
  const c = String(cpf).replace(/\D/g, '');
  if (c.length !== 11) return false;

  // Rejeitar todos iguais (000.000.000-00, 111.111.111-11, etc)
  if (/^(\d)\1{10}$/.test(c)) return false;

  // Primeiro dígito verificador
  let soma = 0;
  for (let i = 0; i < 9; i++) {
    soma += parseInt(c[i]) * (10 - i);
  }
  let resto = (soma * 10) % 11;
  if (resto === 10) resto = 0;
  if (resto !== parseInt(c[9])) return false;

  // Segundo dígito verificador
  soma = 0;
  for (let i = 0; i < 10; i++) {
    soma += parseInt(c[i]) * (11 - i);
  }
  resto = (soma * 10) % 11;
  if (resto === 10) resto = 0;
  if (resto !== parseInt(c[10])) return false;

  return true;
}

module.exports = { validarCpf };
