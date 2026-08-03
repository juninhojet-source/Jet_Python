/**
 * Geração de códigos únicos para animais
 * Formato: ANI-AAAA-NNNN
 */
const db = require('../db/connection');

function gerarCodigoAnimal() {
  const ano = new Date().getFullYear();
  const prefixo = `ANI-${ano}-`;

  const row = db.prepare(`
    SELECT codigo FROM animais
    WHERE codigo LIKE ?
    ORDER BY id DESC LIMIT 1
  `).get(prefixo + '%');

  let proximo = 1;
  if (row && row.codigo) {
    const partes = row.codigo.split('-');
    proximo = parseInt(partes[2], 10) + 1;
  }
  return prefixo + String(proximo).padStart(4, '0');
}

module.exports = { gerarCodigoAnimal };
