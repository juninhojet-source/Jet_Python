/**
 * Dados Geográficos para o Mapa do Município
 * SIGAZ - PMBC
 *
 * As coordenadas dos bairros vêm da tabela `bairros` do banco
 * (populada por seed + geocoding automático via Nominatim).
 */
const express = require('express');
const db = require('../db/connection');
const { autenticar } = require('../middleware/auth');

const router = express.Router();
router.use(autenticar);

// Centro do município (Praça central de Barão de Cocais)
const CENTRO_MUNICIPIO = { lat: -19.9444, lng: -43.4912 };

/**
 * Carrega o cache de coordenadas dos bairros (regerado a cada chamada).
 * Retorna um Map {nome_lower: {lat, lng}} para consulta rápida.
 */
// Normaliza nome de bairro: minúsculas, sem acento, sem espaços extras
function chaveBairro(nome) {
  return String(nome || '')
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '') // remove acentos
    .toLowerCase().trim().replace(/\s+/g, ' ');
}

function carregarBairros() {
  const dados = db.prepare(`
    SELECT nome, latitude, longitude
    FROM bairros
    WHERE ativo = 1 AND latitude IS NOT NULL AND longitude IS NOT NULL
  `).all();
  const mapa = new Map();
  for (const b of dados) {
    mapa.set(chaveBairro(b.nome), { lat: b.latitude, lng: b.longitude });
  }
  return mapa;
}

function coordsBairro(nome, cache) {
  if (!nome) return null;
  const n = chaveBairro(nome);
  if (cache.has(n)) return cache.get(n);
  // Match parcial (fallback fuzzy básico)
  for (const [k, v] of cache.entries()) {
    if (k.includes(n) || n.includes(k)) return v;
  }
  return null;
}

/**
 * Adiciona um pequeno jitter para não empilhar todos os pins no mesmo ponto.
 * Determinístico para um dado id (sempre o mesmo desvio para o mesmo id).
 */
function jitter(coords, id) {
  if (!coords) return null;
  const seed = (id * 9301 + 49297) % 233280;
  const r1 = (seed / 233280) - 0.5;
  const seed2 = (id * 7331 + 12345) % 233280;
  const r2 = (seed2 / 233280) - 0.5;
  return {
    lat: coords.lat + r1 * 0.004, // ~400 metros
    lng: coords.lng + r2 * 0.004
  };
}

/**
 * GET /api/mapa/animais — Pins de animais agrupados por bairro
 */
router.get('/animais', (req, res) => {
  const cacheCoords = carregarBairros();
  const linhas = db.prepare(`
    SELECT a.id, a.codigo, a.nome, a.especie, r.bairro
    FROM animais a
    LEFT JOIN responsaveis r ON r.id = a.responsavel_id
    WHERE a.ativo = 1 AND r.bairro IS NOT NULL AND r.bairro != ''
  `).all();

  const pontos = [];
  const semCoord = [];
  for (const l of linhas) {
    const c = coordsBairro(l.bairro, cacheCoords);
    if (!c) {
      if (!semCoord.includes(l.bairro)) semCoord.push(l.bairro);
      continue;
    }
    const p = jitter(c, l.id);
    pontos.push({
      id: l.id, codigo: l.codigo, nome: l.nome, especie: l.especie, bairro: l.bairro,
      lat: p.lat, lng: p.lng
    });
  }

  // Agregação por bairro
  const porBairro = db.prepare(`
    SELECT r.bairro, COUNT(*) AS total
    FROM animais a
    INNER JOIN responsaveis r ON r.id = a.responsavel_id
    WHERE a.ativo = 1 AND r.bairro IS NOT NULL AND r.bairro != ''
    GROUP BY r.bairro
  `).all().map(b => {
    const c = coordsBairro(b.bairro, cacheCoords);
    return c ? { ...b, lat: c.lat, lng: c.lng } : null;
  }).filter(Boolean);

  res.json({ pontos, porBairro, centro: CENTRO_MUNICIPIO, bairros_sem_coordenada: semCoord });
});

/**
 * GET /api/mapa/status-reprodutivo (alias: /reprodutivo)
 * Pontos de animais coloridos por status reprodutivo, com filtro opcional.
 * Query: ?status=Castrado(a) (opcional) — filtra um status específico.
 */
router.get(['/status-reprodutivo', '/reprodutivo'], (req, res) => {
  const cacheCoords = carregarBairros();
  const { status } = req.query;

  let filtro = '';
  const params = [];
  if (status) { filtro = ' AND a.status_reprodutivo = ?'; params.push(status); }

  const linhas = db.prepare(`
    SELECT a.id, a.codigo, a.nome, a.especie, a.status_reprodutivo, r.bairro
    FROM animais a
    LEFT JOIN responsaveis r ON r.id = a.responsavel_id
    WHERE a.ativo = 1 AND r.bairro IS NOT NULL AND r.bairro != ''${filtro}
  `).all(...params);

  const pontos = [];
  const semCoord = [];
  for (const l of linhas) {
    const c = coordsBairro(l.bairro, cacheCoords);
    if (!c) { if (!semCoord.includes(l.bairro)) semCoord.push(l.bairro); continue; }
    const p = jitter(c, l.id);
    pontos.push({
      id: l.id, codigo: l.codigo, nome: l.nome, especie: l.especie,
      status_reprodutivo: l.status_reprodutivo || 'Não informado',
      bairro: l.bairro, lat: p.lat, lng: p.lng
    });
  }

  // Resumo por bairro x status (para a tabela/legenda)
  const resumo = db.prepare(`
    SELECT r.bairro,
           a.status_reprodutivo AS status,
           COUNT(*) AS total
    FROM animais a
    INNER JOIN responsaveis r ON r.id = a.responsavel_id
    WHERE a.ativo = 1 AND r.bairro IS NOT NULL AND r.bairro != ''${filtro}
    GROUP BY r.bairro, a.status_reprodutivo
  `).all(...params);

  // Contagem geral por status (para a legenda)
  const totaisPorStatus = db.prepare(`
    SELECT COALESCE(status_reprodutivo, 'Não informado') AS status, COUNT(*) AS total
    FROM animais
    WHERE ativo = 1
    GROUP BY status_reprodutivo
    ORDER BY total DESC
  `).all();

  res.json({ pontos, resumo, totaisPorStatus, centro: CENTRO_MUNICIPIO, bairros_sem_coordenada: semCoord });
});

/**
 * GET /api/mapa/vacinacao
 * Pontos de animais classificados como vacinados / não vacinados.
 * Query: ?vacina=Raiva (opcional) — considera vacinado quem tem essa vacina
 *        em dia (dose mais recente com proxima_aplicacao futura ou sem data).
 *        Sem o parâmetro, considera vacinado quem tem QUALQUER vacina em dia.
 */
router.get('/vacinacao', (req, res) => {
  const cacheCoords = carregarBairros();
  const { vacina } = req.query;

  const animais = db.prepare(`
    SELECT a.id, a.codigo, a.nome, a.especie, r.bairro
    FROM animais a
    LEFT JOIN responsaveis r ON r.id = a.responsavel_id
    WHERE a.ativo = 1 AND r.bairro IS NOT NULL AND r.bairro != ''
  `).all();

  // Para cada animal, decide se está vacinado conforme o filtro
  const hoje = new Date().toISOString().substring(0, 10);

  // Pré-carrega vacinas vigentes (dose mais recente de cada animal+vacina)
  let queryVac = `
    SELECT v.animal_id, v.vacina, v.proxima_aplicacao
    FROM vacinas v
    WHERE v.id = (
      SELECT v2.id FROM vacinas v2
      WHERE v2.animal_id = v.animal_id AND v2.vacina = v.vacina
      ORDER BY v2.data_aplicacao DESC, v2.id DESC LIMIT 1
    )
  `;
  const paramsVac = [];
  if (vacina) { queryVac += ' AND v.vacina = ?'; paramsVac.push(vacina); }
  const vacinasVigentes = db.prepare(queryVac).all(...paramsVac);

  // Monta um set de animais vacinados (com a vacina em dia)
  const vacinadosSet = new Set();
  for (const v of vacinasVigentes) {
    // "em dia" = sem próxima aplicação OU próxima no futuro
    if (!v.proxima_aplicacao || v.proxima_aplicacao >= hoje) {
      vacinadosSet.add(v.animal_id);
    }
  }

  const pontos = [];
  const semCoord = [];
  let totVac = 0, totNao = 0;
  for (const a of animais) {
    const c = coordsBairro(a.bairro, cacheCoords);
    if (!c) { if (!semCoord.includes(a.bairro)) semCoord.push(a.bairro); continue; }
    const p = jitter(c, a.id);
    const vacinado = vacinadosSet.has(a.id);
    if (vacinado) totVac++; else totNao++;
    pontos.push({
      id: a.id, codigo: a.codigo, nome: a.nome, especie: a.especie,
      bairro: a.bairro, vacinado, lat: p.lat, lng: p.lng
    });
  }

  // Lista de vacinas disponíveis para o filtro
  const tiposVacina = db.prepare(`
    SELECT DISTINCT vacina FROM vacinas ORDER BY vacina
  `).all().map(r => r.vacina);

  res.json({
    pontos, centro: CENTRO_MUNICIPIO, bairros_sem_coordenada: semCoord,
    totais: { vacinados: totVac, nao_vacinados: totNao },
    tipos_vacina: tiposVacina,
    filtro_vacina: vacina || null
  });
});

/**
 * Função genérica: monta o mapa de "tratado / não tratado" para uma tabela
 * de ação sanitária com colunas (animal_id, produto, proxima_aplicacao).
 * Usada por vermifugação e ectoparasitários/coleira.
 */
function mapaAcaoSanitaria(tabela, filtroProduto, req, res) {
  const cacheCoords = carregarBairros();
  const hoje = new Date().toISOString().substring(0, 10);

  const animais = db.prepare(`
    SELECT a.id, a.codigo, a.nome, a.especie, r.bairro
    FROM animais a
    LEFT JOIN responsaveis r ON r.id = a.responsavel_id
    WHERE a.ativo = 1 AND r.bairro IS NOT NULL AND r.bairro != ''
  `).all();

  // Dose mais recente de cada animal+produto na tabela informada
  let query = `
    SELECT t.animal_id, t.produto, t.proxima_aplicacao
    FROM ${tabela} t
    WHERE t.id = (
      SELECT t2.id FROM ${tabela} t2
      WHERE t2.animal_id = t.animal_id AND t2.produto = t.produto
      ORDER BY t2.data_aplicacao DESC, t2.id DESC LIMIT 1
    )
  `;
  const params = [];
  if (filtroProduto) { query += ' AND t.produto = ?'; params.push(filtroProduto); }
  const vigentes = db.prepare(query).all(...params);

  const tratadosSet = new Set();
  for (const v of vigentes) {
    if (!v.proxima_aplicacao || v.proxima_aplicacao >= hoje) {
      tratadosSet.add(v.animal_id);
    }
  }

  const pontos = [];
  const semCoord = [];
  let totSim = 0, totNao = 0;
  for (const a of animais) {
    const c = coordsBairro(a.bairro, cacheCoords);
    if (!c) { if (!semCoord.includes(a.bairro)) semCoord.push(a.bairro); continue; }
    const p = jitter(c, a.id);
    const tratado = tratadosSet.has(a.id);
    if (tratado) totSim++; else totNao++;
    pontos.push({
      id: a.id, codigo: a.codigo, nome: a.nome, especie: a.especie,
      bairro: a.bairro, tratado, lat: p.lat, lng: p.lng
    });
  }

  const tiposProduto = db.prepare(`
    SELECT DISTINCT produto FROM ${tabela} ORDER BY produto
  `).all().map(r => r.produto);

  res.json({
    pontos, centro: CENTRO_MUNICIPIO, bairros_sem_coordenada: semCoord,
    totais: { tratados: totSim, nao_tratados: totNao },
    tipos_produto: tiposProduto,
    filtro_produto: filtroProduto || null
  });
}

/**
 * GET /api/mapa/vermifugacao — animais vermifugados / não vermifugados
 */
router.get('/vermifugacao', (req, res) => {
  mapaAcaoSanitaria('vermifugacoes', req.query.produto || null, req, res);
});

/**
 * GET /api/mapa/antiparasitario — animais com ectoparasiticida/coleira em dia
 */
router.get('/antiparasitario', (req, res) => {
  mapaAcaoSanitaria('ectoparasitarios', req.query.produto || null, req, res);
});

/**
 * GET /api/mapa/zoonoses — Pins e heatmap de zoonoses
 */
router.get('/zoonoses', (req, res) => {
  const cacheCoords = carregarBairros();
  const { zoonose, data_inicio, data_fim } = req.query;
  let where = 'WHERE z.bairro_ocorrencia IS NOT NULL AND z.bairro_ocorrencia != \'\'';
  const params = [];
  if (zoonose) { where += ' AND z.zoonose = ?'; params.push(zoonose); }
  if (data_inicio) { where += ' AND z.data_notificacao >= ?'; params.push(data_inicio); }
  if (data_fim) { where += ' AND z.data_notificacao <= ?'; params.push(data_fim); }

  const linhas = db.prepare(`
    SELECT z.id, z.zoonose, z.data_notificacao, z.diagnostico, z.bairro_ocorrencia,
           a.codigo AS animal_codigo, a.nome AS animal_nome, a.especie
    FROM zoonoses z
    INNER JOIN animais a ON a.id = z.animal_id
    ${where}
    ORDER BY z.data_notificacao DESC
  `).all(...params);

  const pontos = [];
  const semCoord = [];
  for (const l of linhas) {
    const c = coordsBairro(l.bairro_ocorrencia, cacheCoords);
    if (!c) {
      if (!semCoord.includes(l.bairro_ocorrencia)) semCoord.push(l.bairro_ocorrencia);
      continue;
    }
    const p = jitter(c, l.id);
    pontos.push({ ...l, lat: p.lat, lng: p.lng });
  }

  // Agregação por bairro
  const porBairro = {};
  for (const l of linhas) {
    const c = coordsBairro(l.bairro_ocorrencia, cacheCoords);
    if (!c) continue;
    if (!porBairro[l.bairro_ocorrencia]) {
      porBairro[l.bairro_ocorrencia] = {
        bairro: l.bairro_ocorrencia, total: 0, positivos: 0,
        lat: c.lat, lng: c.lng
      };
    }
    porBairro[l.bairro_ocorrencia].total++;
    if (l.diagnostico === 'Positivo') porBairro[l.bairro_ocorrencia].positivos++;
  }

  res.json({
    pontos, porBairro: Object.values(porBairro), centro: CENTRO_MUNICIPIO,
    bairros_sem_coordenada: semCoord
  });
});

/**
 * GET /api/mapa/denuncias — Pins de denúncias
 */
router.get('/denuncias', (req, res) => {
  const cacheCoords = carregarBairros();
  const linhas = db.prepare(`
    SELECT id, protocolo, tipo, status, bairro, endereco, criado_em
    FROM denuncias
    WHERE bairro IS NOT NULL AND bairro != ''
    ORDER BY criado_em DESC
  `).all();

  const pontos = [];
  const porBairro = {};
  const semCoord = [];
  for (const l of linhas) {
    const c = coordsBairro(l.bairro, cacheCoords);
    if (!c) {
      if (!semCoord.includes(l.bairro)) semCoord.push(l.bairro);
      continue;
    }
    const p = jitter(c, l.id);
    pontos.push({ ...l, lat: p.lat, lng: p.lng });

    if (!porBairro[l.bairro]) {
      porBairro[l.bairro] = { bairro: l.bairro, total: 0, pendentes: 0, lat: c.lat, lng: c.lng };
    }
    porBairro[l.bairro].total++;
    if (l.status === 'Recebida' || l.status === 'Em Apuração') porBairro[l.bairro].pendentes++;
  }

  res.json({ pontos, porBairro: Object.values(porBairro), centro: CENTRO_MUNICIPIO,
            bairros_sem_coordenada: semCoord });
});

/**
 * GET /api/mapa/bairros — Lista os bairros com coordenadas
 */
router.get('/bairros', (req, res) => {
  const dados = db.prepare(`
    SELECT nome, latitude AS lat, longitude AS lng, eh_distrito
    FROM bairros
    WHERE ativo = 1 AND latitude IS NOT NULL AND longitude IS NOT NULL
    ORDER BY ordem, nome
  `).all();
  res.json({ dados, centro: CENTRO_MUNICIPIO });
});

module.exports = router;
