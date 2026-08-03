/**
 * Rate limiting simples em memória, para endpoints públicos (sem login).
 * SIGAZ - PMBC
 *
 * Não usa dependência externa: o serviço roda numa única instância Node,
 * então um contador em memória por IP é suficiente.
 */

/**
 * @param {number} max      Máximo de requisições permitidas na janela.
 * @param {number} janelaMs Duração da janela em milissegundos.
 */
function limitarTaxa(max, janelaMs) {
  const contadores = new Map();

  return (req, res, next) => {
    const chave = req.ip;
    const agora = Date.now();
    const registro = contadores.get(chave);

    if (!registro || agora > registro.resetaEm) {
      contadores.set(chave, { total: 1, resetaEm: agora + janelaMs });
      return next();
    }

    if (registro.total >= max) {
      const segundosRestantes = Math.ceil((registro.resetaEm - agora) / 1000);
      return res.status(429).json({
        erro: `Muitas requisições. Tente novamente em ${segundosRestantes} segundo(s).`
      });
    }

    registro.total++;
    next();
  };
}

module.exports = { limitarTaxa };
