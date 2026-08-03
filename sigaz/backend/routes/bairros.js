/**
 * Bairros Oficiais do Município
 * SIGAZ - PMBC
 */
const express = require('express');
const db = require('../db/connection');
const { autenticar, autorizar } = require('../middleware/auth');
const { registrarLog } = require('../utils/logger');

const router = express.Router();
router.use(autenticar);

// Listagem disponível para qualquer usuário autenticado (todos os formulários usam)
router.get('/', (req, res) => {
  const { incluir_inativos } = req.query;
  const where = incluir_inativos === '1' ? '' : 'WHERE ativo = 1';
  const dados = db.prepare(`
    SELECT id, nome, eh_distrito, ativo, ordem, latitude, longitude, geocoded_em
    FROM bairros
    ${where}
    ORDER BY ordem, nome
  `).all();
  res.json({ dados });
});

// Normaliza para comparação: minúsculas, sem acento, sem espaços extras
function chaveNome(nome) {
  return String(nome || '')
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '') // remove acentos
    .toLowerCase().trim().replace(/\s+/g, ' ');
}

// Padroniza exibição em formato "Título" (primeira letra de cada palavra maiúscula),
// preservando algarismos romanos comuns (I, II, III) e siglas.
function formatarTitulo(nome) {
  const minusculas = ['de','da','do','das','dos','e'];
  return String(nome || '').trim().replace(/\s+/g, ' ').split(' ').map((palavra, i) => {
    const lower = palavra.toLowerCase();
    // Mantém algarismos romanos em maiúsculo
    if (/^(i{1,3}|iv|v|vi{0,3}|ix|x)$/i.test(palavra)) return palavra.toUpperCase();
    // Preposições em minúsculo (exceto se for a primeira palavra)
    if (i > 0 && minusculas.includes(lower)) return lower;
    return palavra.charAt(0).toUpperCase() + palavra.slice(1).toLowerCase();
  }).join(' ');
}

// CRUD restrito a admin/ti
router.post('/', autorizar('admin', 'ti'), (req, res) => {
  const { nome, eh_distrito } = req.body;
  if (!nome || !nome.trim()) {
    return res.status(400).json({ erro: 'Nome do bairro é obrigatório' });
  }

  const nomeFormatado = formatarTitulo(nome);
  const chave = chaveNome(nome);

  // Verifica duplicata de forma insensível a maiúsculas/acentos
  const existentes = db.prepare('SELECT id, nome FROM bairros').all();
  const dup = existentes.find(b => chaveNome(b.nome) === chave);
  if (dup) {
    return res.status(409).json({
      erro: `Já existe um bairro equivalente: "${dup.nome}". Nomes são comparados ignorando maiúsculas e acentos.`,
      id: dup.id
    });
  }

  try {
    const proxOrdem = db.prepare('SELECT COALESCE(MAX(ordem), 0) + 1 AS o FROM bairros').get().o;
    const info = db.prepare(`
      INSERT INTO bairros (nome, eh_distrito, ordem) VALUES (?, ?, ?)
    `).run(nomeFormatado, eh_distrito ? 1 : 0, proxOrdem);
    registrarLog(req, 'CRIAR', 'bairros', info.lastInsertRowid, { nome: nomeFormatado });
    res.status(201).json({ id: info.lastInsertRowid, nome: nomeFormatado });
  } catch (err) {
    if (err.message && err.message.includes('UNIQUE')) {
      return res.status(409).json({ erro: 'Já existe um bairro com este nome' });
    }
    res.status(500).json({ erro: 'Erro ao criar bairro: ' + err.message });
  }
});

router.put('/:id', autorizar('admin', 'ti'), (req, res) => {
  const { nome, eh_distrito, ativo, latitude, longitude } = req.body;
  const atual = db.prepare('SELECT * FROM bairros WHERE id = ?').get(req.params.id);
  if (!atual) return res.status(404).json({ erro: 'Bairro não encontrado' });

  try {
    // Se está mudando o nome, padroniza e verifica duplicata
    let nomeFinal = atual.nome;
    if (nome != null && nome.trim() && chaveNome(nome) !== chaveNome(atual.nome)) {
      const chave = chaveNome(nome);
      const outros = db.prepare('SELECT id, nome FROM bairros WHERE id != ?').all(req.params.id);
      const dup = outros.find(b => chaveNome(b.nome) === chave);
      if (dup) {
        return res.status(409).json({ erro: `Já existe um bairro equivalente: "${dup.nome}".`, id: dup.id });
      }
      nomeFinal = formatarTitulo(nome);
    } else if (nome != null && nome.trim()) {
      nomeFinal = formatarTitulo(nome);
    }

    // Decide se foi alteração de coordenada (atualiza geocoded_em se for o caso)
    const novaLat = latitude != null ? parseFloat(latitude) : atual.latitude;
    const novaLng = longitude != null ? parseFloat(longitude) : atual.longitude;
    const mudouCoord = (latitude != null && novaLat !== atual.latitude) ||
                       (longitude != null && novaLng !== atual.longitude);

    db.prepare(`
      UPDATE bairros SET
        nome = ?, eh_distrito = ?, ativo = ?,
        latitude = ?, longitude = ?,
        geocoded_em = ${mudouCoord ? 'CURRENT_TIMESTAMP' : 'geocoded_em'}
      WHERE id = ?
    `).run(
      nomeFinal,
      eh_distrito != null ? (eh_distrito ? 1 : 0) : atual.eh_distrito,
      ativo != null ? (ativo ? 1 : 0) : atual.ativo,
      isNaN(novaLat) ? null : novaLat,
      isNaN(novaLng) ? null : novaLng,
      req.params.id
    );
    registrarLog(req, 'ATUALIZAR', 'bairros', req.params.id);
    res.json({ ok: true });
  } catch (err) {
    if (err.message && err.message.includes('UNIQUE')) {
      return res.status(409).json({ erro: 'Já existe um bairro com este nome' });
    }
    res.status(500).json({ erro: 'Erro ao atualizar: ' + err.message });
  }
});

router.delete('/:id', autorizar('admin', 'ti'), (req, res) => {
  // Inativa em vez de excluir (preserva referências históricas)
  const atual = db.prepare('SELECT * FROM bairros WHERE id = ?').get(req.params.id);
  if (!atual) return res.status(404).json({ erro: 'Bairro não encontrado' });

  db.prepare('UPDATE bairros SET ativo = 0 WHERE id = ?').run(req.params.id);
  registrarLog(req, 'INATIVAR', 'bairros', req.params.id, { nome: atual.nome });
  res.json({ ok: true });
});

/**
 * Geocoding em lote — busca coordenadas no Nominatim (OpenStreetMap) para
 * todos os bairros que ainda não têm latitude/longitude.
 *
 * Respeita a política do Nominatim: 1 requisição por segundo, com User-Agent.
 */
router.post('/geocodificar', autorizar('admin', 'ti'), async (req, res) => {
  const forcar = req.query.forcar === '1';

  // Pega bairros sem coordenadas (ou todos, se forcar=1)
  const lista = db.prepare(`
    SELECT id, nome, eh_distrito FROM bairros
    WHERE ativo = 1 ${forcar ? '' : 'AND (latitude IS NULL OR longitude IS NULL)'}
    ORDER BY ordem, nome
  `).all();

  if (lista.length === 0) {
    return res.json({ ok: true, processados: 0, encontrados: 0, mensagem: 'Nenhum bairro pendente' });
  }

  const upd = db.prepare(`
    UPDATE bairros SET latitude = ?, longitude = ?, geocoded_em = CURRENT_TIMESTAMP WHERE id = ?
  `);

  let encontrados = 0, naoEncontrados = 0;
  const detalhes = [];

  const sleep = (ms) => new Promise(r => setTimeout(r, ms));
  const limparAcentos = (s) => s.normalize('NFD').replace(/[\u0300-\u036f]/g, '');

  for (const b of lista) {
    // Aguarda 1.1s entre requisições (política do Nominatim)
    if (detalhes.length > 0) await sleep(1100);

    // Tenta 2 buscas: 1) bairro + município, 2) bairro + município sem acentos
    const tentativas = [
      `${b.nome}, Barão de Cocais, Minas Gerais, Brasil`,
      `${limparAcentos(b.nome)}, Barao de Cocais, MG, Brasil`
    ];
    let achou = null;
    for (const q of tentativas) {
      try {
        const url = `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(q)}&format=json&limit=1&countrycodes=br`;
        const r = await fetch(url, {
          headers: { 'User-Agent': 'SIGAZ-PMBC/1.0 (TI Prefeitura Barao de Cocais)' }
        });
        if (!r.ok) continue;
        const arr = await r.json();
        if (arr && arr.length > 0) {
          achou = { lat: parseFloat(arr[0].lat), lng: parseFloat(arr[0].lon), display: arr[0].display_name };
          break;
        }
      } catch (err) {
        console.error('[Geocoding] Erro em', b.nome, ':', err.message);
      }
    }

    if (achou) {
      upd.run(achou.lat, achou.lng, b.id);
      encontrados++;
      detalhes.push({ id: b.id, nome: b.nome, status: 'ok', lat: achou.lat, lng: achou.lng });
    } else {
      naoEncontrados++;
      detalhes.push({ id: b.id, nome: b.nome, status: 'nao_encontrado' });
    }
  }

  registrarLog(req, 'GEOCODIFICAR', 'bairros', null,
    { processados: lista.length, encontrados, nao_encontrados: naoEncontrados });

  res.json({
    ok: true,
    processados: lista.length,
    encontrados,
    nao_encontrados: naoEncontrados,
    detalhes
  });
});

/**
 * GET /api/bairros/duplicados
 * Lista grupos de bairros que são equivalentes (ignorando maiúsculas/acentos),
 * para o admin decidir mesclar.
 */
router.get('/duplicados', autorizar('admin', 'ti'), (req, res) => {
  const todos = db.prepare('SELECT id, nome, ativo, latitude, longitude FROM bairros').all();
  const grupos = {};
  for (const b of todos) {
    const k = chaveNome(b.nome);
    if (!grupos[k]) grupos[k] = [];
    grupos[k].push(b);
  }
  const duplicados = Object.values(grupos).filter(g => g.length > 1);
  res.json({ duplicados });
});

/**
 * POST /api/bairros/mesclar
 * Mescla bairros duplicados: move todos os registros (responsáveis, animais,
 * zoonoses, etc.) que usam os nomes duplicados para o nome do bairro "mestre",
 * e inativa os demais.
 * Body: { mestre_id, ids_para_mesclar: [ ... ] }
 */
router.post('/mesclar', autorizar('admin', 'ti'), (req, res) => {
  const { mestre_id, ids_para_mesclar } = req.body;
  if (!mestre_id || !Array.isArray(ids_para_mesclar) || ids_para_mesclar.length === 0) {
    return res.status(400).json({ erro: 'Informe mestre_id e ids_para_mesclar (lista)' });
  }

  const mestre = db.prepare('SELECT id, nome FROM bairros WHERE id = ?').get(mestre_id);
  if (!mestre) return res.status(404).json({ erro: 'Bairro mestre não encontrado' });

  const nomesParaMesclar = ids_para_mesclar
    .map(id => db.prepare('SELECT nome FROM bairros WHERE id = ?').get(id))
    .filter(Boolean)
    .map(b => b.nome);

  if (nomesParaMesclar.length === 0) {
    return res.status(400).json({ erro: 'Nenhum bairro válido para mesclar' });
  }

  // Tabelas que têm coluna "bairro" (texto) que apontam para o nome do bairro
  const tabelasComBairro = ['responsaveis', 'zoonoses', 'denuncias', 'mordeduras'];
  const totais = {};

  try {
    db.exec('BEGIN');
    for (const tabela of tabelasComBairro) {
      // Confirma que a tabela tem a coluna 'bairro'
      const cols = db.prepare(`PRAGMA table_info(${tabela})`).all();
      const temBairro = cols.some(c => c.name === 'bairro');
      const temBairroOcorrencia = cols.some(c => c.name === 'bairro_ocorrencia');

      let n = 0;
      for (const nomeAntigo of nomesParaMesclar) {
        if (temBairro) {
          const r = db.prepare(`UPDATE ${tabela} SET bairro = ? WHERE bairro = ?`).run(mestre.nome, nomeAntigo);
          n += r.changes;
        }
        if (temBairroOcorrencia) {
          const r2 = db.prepare(`UPDATE ${tabela} SET bairro_ocorrencia = ? WHERE bairro_ocorrencia = ?`).run(mestre.nome, nomeAntigo);
          n += r2.changes;
        }
      }
      if (n > 0) totais[tabela] = n;
    }

    // Inativa os bairros mesclados
    const inativar = db.prepare('UPDATE bairros SET ativo = 0 WHERE id = ?');
    for (const id of ids_para_mesclar) inativar.run(id);

    db.exec('COMMIT');
  } catch (err) {
    try { db.exec('ROLLBACK'); } catch(_){}
    return res.status(500).json({ erro: 'Erro ao mesclar: ' + err.message });
  }

  registrarLog(req, 'MESCLAR', 'bairros', mestre_id,
    { mestre: mestre.nome, mesclados: nomesParaMesclar, registros_movidos: totais });

  res.json({ ok: true, mestre: mestre.nome, mesclados: nomesParaMesclar, registros_movidos: totais });
});

module.exports = router;
