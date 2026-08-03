/**
 * Rotas de Importação em Lote
 * SIGAZ - PMBC
 *
 * Aceita CSV (ou colado da planilha) com cabeçalho na 1ª linha.
 * Valida tudo antes de importar e devolve o relatório.
 */
const express = require('express');
const QRCode = require('qrcode');
const db = require('../db/connection');
const { autenticar, autorizar } = require('../middleware/auth');
const { registrarLog } = require('../utils/logger');
const { validarCpf } = require('../utils/cpf');
const { gerarCodigoAnimal } = require('../utils/codigos');

const router = express.Router();
router.use(autenticar);
router.use(autorizar('admin', 'ti', 'veterinario'));

/**
 * Parser CSV simples (suporta vírgula, ponto-vírgula ou tab como separador)
 * Detecta separador automaticamente.
 */
function parseCsv(texto) {
  if (!texto || typeof texto !== 'string') return [];
  const linhas = texto.replace(/\r/g, '').trim().split('\n');
  if (linhas.length < 2) return [];

  // Detectar separador (vírgula, ponto-vírgula ou tab)
  const candidatos = [';', ',', '\t'];
  let sep = ';';
  let maxCols = 0;
  for (const c of candidatos) {
    const cols = linhas[0].split(c).length;
    if (cols > maxCols) { maxCols = cols; sep = c; }
  }

  const parseLinha = (linha) => {
    // Suporte básico a campos entre aspas
    const resultado = [];
    let atual = '';
    let dentroAspas = false;
    for (let i = 0; i < linha.length; i++) {
      const ch = linha[i];
      if (ch === '"') { dentroAspas = !dentroAspas; continue; }
      if (ch === sep && !dentroAspas) { resultado.push(atual); atual = ''; continue; }
      atual += ch;
    }
    resultado.push(atual);
    return resultado.map(s => s.trim());
  };

  const cabecalho = parseLinha(linhas[0]).map(c => c.toLowerCase().replace(/[\s_-]/g, ''));
  const dados = [];
  for (let i = 1; i < linhas.length; i++) {
    if (!linhas[i].trim()) continue;
    const cols = parseLinha(linhas[i]);
    const obj = {};
    cabecalho.forEach((k, idx) => obj[k] = cols[idx] || '');
    dados.push(obj);
  }
  return { cabecalho, dados };
}

/**
 * POST /api/importacao/responsaveis
 * Body: { csv: "texto", confirmar: false }
 * Aceita campos: nome, cpf, rg, telefone, email, endereco, numero, bairro, cidade, uf, cep
 */
router.post('/responsaveis', (req, res) => {
  const { csv, confirmar } = req.body;
  if (!csv) return res.status(400).json({ erro: 'CSV não enviado' });

  const parsed = parseCsv(csv);
  if (!parsed || !parsed.dados || parsed.dados.length === 0) {
    return res.status(400).json({ erro: 'CSV vazio ou inválido' });
  }

  // Validação de cada linha
  const validos = [];
  const erros = [];
  parsed.dados.forEach((row, idx) => {
    const linha = idx + 2; // +1 cabeçalho, +1 zero-index
    if (!row.nome) { erros.push({ linha, erro: 'Nome ausente', dados: row }); return; }
    if (!row.cpf) { erros.push({ linha, erro: 'CPF ausente', dados: row }); return; }
    const cpfLimpo = String(row.cpf).replace(/\D/g, '');
    if (!validarCpf(cpfLimpo)) { erros.push({ linha, erro: 'CPF inválido: ' + row.cpf, dados: row }); return; }

    const jaExiste = db.prepare('SELECT id FROM responsaveis WHERE cpf = ?').get(cpfLimpo);
    if (jaExiste) { erros.push({ linha, erro: `CPF já cadastrado (id ${jaExiste.id}): ${row.nome}`, dados: row }); return; }

    validos.push({
      ...row,
      cpf: cpfLimpo,
      telefone: row.telefone ? String(row.telefone).replace(/\D/g, '') : null,
      cep: row.cep ? String(row.cep).replace(/\D/g, '') : null,
      cidade: row.cidade || 'Barão de Cocais',
      uf: row.uf || 'MG'
    });
  });

  if (!confirmar) {
    // Modo "preview" — devolve o que importaria sem gravar
    return res.json({
      preview: true,
      total: parsed.dados.length,
      validos: validos.length,
      erros: erros.length,
      detalhe_erros: erros.slice(0, 50),
      amostra: validos.slice(0, 5)
    });
  }

  // Modo confirmado — inserir tudo
  const stmt = db.prepare(`
    INSERT INTO responsaveis (nome, cpf, rg, telefone, email, endereco, numero, bairro, cidade, uf, cep)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `);
  let inseridos = 0;
  const transacao = db.prepare('BEGIN'); db.exec('BEGIN');
  try {
    for (const r of validos) {
      stmt.run(r.nome, r.cpf, r.rg || null, r.telefone || null, r.email || null,
               r.endereco || null, r.numero || null, r.bairro || null,
               r.cidade || 'Barão de Cocais', r.uf || 'MG', r.cep || null);
      inseridos++;
    }
    db.exec('COMMIT');
  } catch (err) {
    db.exec('ROLLBACK');
    return res.status(500).json({ erro: 'Falha na importação: ' + err.message });
  }

  registrarLog(req, 'IMPORTAR', 'responsaveis', null, { inseridos, erros: erros.length });
  res.json({ ok: true, inseridos, erros: erros.length, detalhe_erros: erros.slice(0, 50) });
});

/**
 * POST /api/importacao/animais
 * Aceita: nome, especie, raca, sexo, idade_aproximada, peso_kg, porte, pelagem,
 *         status_reprodutivo, habitacao, microchip, observacoes, cpf_responsavel
 */
router.post('/animais', async (req, res) => {
  const { csv, confirmar } = req.body;
  if (!csv) return res.status(400).json({ erro: 'CSV não enviado' });

  const parsed = parseCsv(csv);
  if (!parsed || !parsed.dados || parsed.dados.length === 0) {
    return res.status(400).json({ erro: 'CSV vazio ou inválido' });
  }

  const validos = [];
  const erros = [];
  const especiesValidas = ['Canino','Felino','Equídeo','Bovídeo','Suídeo','Ave','Outro'];

  parsed.dados.forEach((row, idx) => {
    const linha = idx + 2;
    if (!row.nome) { erros.push({ linha, erro: 'Nome ausente', dados: row }); return; }
    if (!row.especie) { erros.push({ linha, erro: 'Espécie ausente', dados: row }); return; }
    if (!especiesValidas.includes(row.especie)) {
      erros.push({ linha, erro: `Espécie inválida: ${row.especie}. Use: ${especiesValidas.join(', ')}`, dados: row }); return;
    }

    let responsavel_id = null;
    if (row.cpfresponsavel) {
      const cpfLimpo = String(row.cpfresponsavel).replace(/\D/g, '');
      const r = db.prepare('SELECT id FROM responsaveis WHERE cpf = ?').get(cpfLimpo);
      if (!r) {
        erros.push({ linha, erro: `Responsável com CPF ${row.cpfresponsavel} não encontrado`, dados: row });
        return;
      }
      responsavel_id = r.id;
    }

    validos.push({ ...row, responsavel_id });
  });

  if (!confirmar) {
    return res.json({
      preview: true, total: parsed.dados.length, validos: validos.length, erros: erros.length,
      detalhe_erros: erros.slice(0, 50), amostra: validos.slice(0, 5)
    });
  }

  // Inserir com QR Code
  const baseUrl = `${req.protocol}://${req.get('host')}`;
  let inseridos = 0;
  for (const r of validos) {
    try {
      const codigo = gerarCodigoAnimal();
      const qrUrl = `${baseUrl}/consulta.html?codigo=${codigo}`;
      const qrcodeData = await QRCode.toDataURL(qrUrl, { width: 200, margin: 1 });

      db.prepare(`
        INSERT INTO animais (codigo, nome, especie, raca, sexo, idade_aproximada,
                              peso_kg, porte, pelagem, status_reprodutivo, habitacao,
                              microchip, observacoes, responsavel_id, qrcode)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      `).run(codigo, r.nome, r.especie, r.raca || null, r.sexo || null,
             r.idadeaproximada || null, parseFloat(r.pesokg) || null,
             r.porte || null, r.pelagem || null, r.statusreprodutivo || null,
             r.habitacao || null, r.microchip || null, r.observacoes || null,
             r.responsavel_id, qrcodeData);
      inseridos++;
    } catch (err) {
      erros.push({ linha: '?', erro: err.message, dados: r });
    }
  }

  registrarLog(req, 'IMPORTAR', 'animais', null, { inseridos, erros: erros.length });
  res.json({ ok: true, inseridos, erros: erros.length, detalhe_erros: erros.slice(0, 50) });
});

/**
 * POST /api/importacao/combinada
 * Importa responsável + animal na MESMA linha da planilha.
 * Cada linha cria (ou reutiliza) o responsável pelo CPF e cadastra o animal vinculado.
 *
 * Colunas de RESPONSÁVEL: nome, cpf, rg, telefone, email, endereco, numero, bairro, cidade, uf, cep
 * Colunas de ANIMAL: animal (nome), especie, raca, sexo, statusreprodutivo, idade,
 *                     datadenascimento, microchip, porte, pelagem, peso, habitacao, observacoes
 *
 * Regras:
 * - Se o CPF já existe, reutiliza o responsável (não duplica) e só adiciona o animal.
 * - Se a mesma planilha tiver o mesmo CPF em várias linhas, cadastra o responsável 1x
 *   e vincula vários animais (ótimo para tutor com vários bichos).
 * - Linha sem dados de animal (coluna "animal" vazia) cadastra só o responsável.
 */
router.post('/combinada', async (req, res) => {
  const { csv, confirmar } = req.body;
  if (!csv) return res.status(400).json({ erro: 'CSV não enviado' });

  const parsed = parseCsv(csv);
  if (!parsed || !parsed.dados || parsed.dados.length === 0) {
    return res.status(400).json({ erro: 'CSV vazio ou inválido' });
  }

  const especiesValidas = ['Canino','Felino','Equídeo','Bovídeo','Suídeo','Ave','Outro'];

  // Mapeia possíveis nomes de coluna (normalizados sem espaço/acento) para campos canônicos
  function val(row, ...chaves) {
    for (const k of chaves) {
      if (row[k] !== undefined && row[k] !== '') return row[k];
    }
    return '';
  }

  // Normaliza espécie digitada livremente
  function normalizarEspecie(e) {
    if (!e) return '';
    const s = e.trim().toLowerCase();
    if (['cão','cao','cachorro','canino','cadela','cadela'].includes(s)) return 'Canino';
    if (['gato','felino','gata'].includes(s)) return 'Felino';
    if (['cavalo','equino','equídeo','equideo','égua','egua','jumento','asinino'].includes(s)) return 'Equídeo';
    if (['boi','vaca','bovino','bovídeo','bovideo'].includes(s)) return 'Bovídeo';
    if (['porco','suíno','suino','suídeo','suideo'].includes(s)) return 'Suídeo';
    if (['ave','galinha','pássaro','passaro','pato'].includes(s)) return 'Ave';
    // Se já vier capitalizado corretamente
    const cap = e.trim().charAt(0).toUpperCase() + e.trim().slice(1).toLowerCase();
    if (especiesValidas.includes(cap)) return cap;
    return e.trim();
  }

  // Normaliza sexo
  function normalizarSexo(s) {
    if (!s) return null;
    const v = s.trim().toLowerCase();
    if (['m','macho','masculino'].includes(v)) return 'Macho';
    if (['f','fêmea','femea','feminino'].includes(v)) return 'Fêmea';
    return null;
  }

  // Normaliza status reprodutivo para o padrão do sistema (com "(a)")
  // Resolve o bug: planilha trazia "Castrado" mas o sistema conta "Castrado(a)"
  function normalizarStatusReprodutivo(s) {
    if (!s) return null;
    const v = s.trim().toLowerCase().replace(/[()]/g, '').replace(/\s+/g, ' ');
    if (['castrado','castrada','castrado a','castrado(a)','castrada(o)'].includes(v)) return 'Castrado(a)';
    if (['inteiro','inteira','inteiro a','inteiro(a)','não castrado','nao castrado'].includes(v)) return 'Inteiro(a)';
    if (['ovario remanescente','ovário remanescente','ovariorremanescente','ovário-remanescente'].includes(v)) return 'Ovário remanescente';
    if (['rufião','rufiao','rufian'].includes(v)) return 'Rufião';
    if (['criptorquida','criptorquido','criptorquidismo'].includes(v)) return 'Criptorquida';
    // Se não reconhecer, devolve como veio (capitalizado) para não perder o dado
    return s.trim();
  }

  // Normaliza habitação para o padrão do sistema
  function normalizarHabitacao(h) {
    if (!h) return null;
    const v = h.trim().toLowerCase();
    if (['domiciliado','domiciliada','domiciliar'].includes(v)) return 'Domiciliado';
    if (['semidomiciliado','semi-domiciliado','semi domiciliado','semidomiciliada'].includes(v)) return 'Semidomiciliado';
    if (['comunitário','comunitario','comunitária','comunitaria'].includes(v)) return 'Comunitário';
    if (['colônia','colonia'].includes(v)) return 'Colônia';
    if (['errante','de rua','rua'].includes(v)) return 'Errante';
    return h.trim();
  }

  // Converte idade ("3 anos", "2", "6 meses") em data de nascimento aproximada
  function idadeParaNascimento(idade) {
    if (!idade) return null;
    const txt = String(idade).toLowerCase();
    const num = parseFloat(txt.replace(',', '.').replace(/[^\d.]/g, ''));
    if (isNaN(num)) return null;
    const hoje = new Date();
    if (txt.includes('mes') || txt.includes('mês')) {
      hoje.setMonth(hoje.getMonth() - Math.round(num));
    } else {
      // assume anos
      hoje.setFullYear(hoje.getFullYear() - Math.round(num));
    }
    return hoje.toISOString().substring(0, 10);
  }

  // Valida data no formato AAAA-MM-DD ou DD/MM/AAAA
  function normalizarData(d) {
    if (!d) return null;
    const txt = String(d).trim();
    let m = txt.match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (m) return txt;
    m = txt.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
    if (m) return `${m[3]}-${m[2]}-${m[1]}`;
    return null;
  }

  // Extrai até 4 ações sanitárias de uma linha da planilha.
  // Tipos: vacina, ectoparasiticida, vermifugo, coleira (repelente).
  // "Coleira repelente" é registrada na tabela de ectoparasitários (antiparasitário externo),
  // com o nome do produto prefixado por "Coleira: ".
  // Cada ação só conta se tiver o nome/produto preenchido.
  function extrairAcoesSanitarias(row) {
    const acoes = [];
    const hoje = new Date().toISOString().substring(0, 10);
    // OBS: o parser remove espaços/underscores/hífens dos cabeçalhos.
    // Então "aplicacao_vacina" na planilha vira a chave "aplicacaovacina".
    // Os nomes abaixo já estão no formato normalizado (sem _ - espaço).

    // VACINA
    const vac = val(row, 'vacina');
    if (vac && String(vac).trim()) {
      acoes.push({
        tipo: 'vacina',
        nome: String(vac).trim(),
        lote: val(row, 'lotevacina') || null,
        fabricante: val(row, 'fabricantevacina') || null,
        validade: normalizarData(val(row, 'validadevacina')),
        aplicacao: normalizarData(val(row, 'aplicacaovacina', 'dataaplicacaovacina', 'dataaplicacao')) || hoje,
        proxima: normalizarData(val(row, 'proximavacina', 'proximaaplicacaovacina', 'proximaaplicacao'))
      });
    }
    // ECTOPARASITICIDA
    const ecto = val(row, 'ectoparasiticida', 'ecto');
    if (ecto && String(ecto).trim()) {
      acoes.push({
        tipo: 'ecto',
        nome: String(ecto).trim(),
        lote: val(row, 'loteecto') || null,
        fabricante: val(row, 'fabricanteecto') || null,
        validade: normalizarData(val(row, 'validadeecto')),
        aplicacao: normalizarData(val(row, 'aplicacaoecto', 'dataaplicacaoecto')) || hoje,
        proxima: normalizarData(val(row, 'proximaecto', 'proximaaplicacaoecto'))
      });
    }
    // VERMÍFUGO
    const verm = val(row, 'vermifugo', 'vermífugo');
    if (verm && String(verm).trim()) {
      acoes.push({
        tipo: 'vermifugo',
        nome: String(verm).trim(),
        lote: val(row, 'lotevermifugo') || null,
        fabricante: val(row, 'fabricantevermifugo') || null,
        validade: normalizarData(val(row, 'validadevermifugo')),
        aplicacao: normalizarData(val(row, 'aplicacaovermifugo', 'dataaplicacaovermifugo')) || hoje,
        proxima: normalizarData(val(row, 'proximavermifugo', 'proximaaplicacaovermifugo'))
      });
    }
    // COLEIRA REPELENTE (registrada como ectoparasitário)
    const coleira = val(row, 'coleirarepelente', 'coleira');
    if (coleira && String(coleira).trim()) {
      acoes.push({
        tipo: 'coleira',
        nome: 'Coleira: ' + String(coleira).trim(),
        lote: val(row, 'lotecoleira') || null,
        fabricante: val(row, 'fabricantecoleira') || null,
        validade: normalizarData(val(row, 'validadecoleira')),
        aplicacao: normalizarData(val(row, 'aplicacaocoleira', 'dataaplicacaocoleira')) || hoje,
        proxima: normalizarData(val(row, 'proximacoleira', 'proximaaplicacaocoleira'))
      });
    }
    return acoes;
  }

  // Processa linha por linha
  const linhasProcessadas = [];
  const erros = [];
  // Mapa de CPF -> dados do responsável (para deduplicar dentro da planilha)
  const responsaveisPlanilha = new Map();

  parsed.dados.forEach((row, idx) => {
    const linha = idx + 2;

    // ----- RESPONSÁVEL -----
    const nome = val(row, 'nome', 'responsavel', 'tutor');
    const cpfRaw = val(row, 'cpf', 'cpfresponsavel');
    const cnpjRaw = val(row, 'cnpj');

    if (!nome) { erros.push({ linha, erro: 'Nome do responsável ausente', dados: row }); return; }

    // Documento: aceita CPF (11 díg) ou CNPJ (14 díg)
    let docLimpo = null;
    let tipoDoc = null;
    if (cpfRaw) {
      docLimpo = String(cpfRaw).replace(/\D/g, '');
      if (docLimpo.length === 14) { tipoDoc = 'CNPJ'; }
      else if (validarCpf(docLimpo)) { tipoDoc = 'CPF'; }
      else { erros.push({ linha, erro: `CPF inválido: ${cpfRaw}`, dados: row }); return; }
    } else if (cnpjRaw) {
      docLimpo = String(cnpjRaw).replace(/\D/g, '');
      tipoDoc = 'CNPJ';
    } else {
      erros.push({ linha, erro: 'CPF ou CNPJ ausente', dados: row }); return;
    }

    // ----- ANIMAL (opcional na linha) -----
    const nomeAnimal = val(row, 'animal', 'nomeanimal', 'nomedoanimal');
    let animalObj = null;
    if (nomeAnimal) {
      const especie = normalizarEspecie(val(row, 'especie', 'espécie'));
      if (!especie) {
        erros.push({ linha, erro: `Espécie do animal "${nomeAnimal}" ausente ou inválida`, dados: row }); return;
      }
      if (!especiesValidas.includes(especie)) {
        erros.push({ linha, erro: `Espécie inválida: "${especie}". Use: ${especiesValidas.join(', ')}`, dados: row }); return;
      }

      // Data de nascimento: usa a coluna se houver, senão calcula da idade
      let dataNasc = normalizarData(val(row, 'datadenascimento', 'datanascimento', 'nascimento'));
      if (!dataNasc) {
        dataNasc = idadeParaNascimento(val(row, 'idade'));
      }

      animalObj = {
        nome: nomeAnimal,
        especie,
        raca: val(row, 'raca', 'raça') || null,
        sexo: normalizarSexo(val(row, 'sexo')),
        status_reprodutivo: normalizarStatusReprodutivo(val(row, 'statusreprodutivo', 'status')),
        data_nascimento: dataNasc,
        idade_aproximada: val(row, 'idade') || null,
        microchip: (val(row, 'microchip', 'chip') || '').toString().trim() || null,
        porte: val(row, 'porte') || null,
        pelagem: val(row, 'pelagem', 'cor') || null,
        peso_kg: parseFloat(String(val(row, 'peso', 'pesokg')).replace(',', '.')) || null,
        habitacao: normalizarHabitacao(val(row, 'habitacao', 'habitação')),
        observacoes: val(row, 'observacoes', 'observação', 'obs') || null
      };
    }

    // Extrai ações sanitárias da linha (todas opcionais).
    // Cada ação só é registrada se tiver pelo menos o nome/produto + data de aplicação.
    const acoesSanitarias = animalObj ? extrairAcoesSanitarias(row) : [];

    linhasProcessadas.push({ linha, nome, docLimpo, tipoDoc, row, animal: animalObj, acoes: acoesSanitarias });
  });

  // Estatísticas para preview
  const cpfsUnicos = new Set(linhasProcessadas.map(l => l.docLimpo));
  const totalAnimais = linhasProcessadas.filter(l => l.animal).length;

  // Quantos responsáveis já existem no banco
  let respExistentes = 0;
  let respNovos = 0;
  for (const cpf of cpfsUnicos) {
    const existe = db.prepare('SELECT id FROM responsaveis WHERE cpf = ?').get(cpf);
    if (existe) respExistentes++; else respNovos++;
  }

  if (!confirmar) {
    const totalAcoes = linhasProcessadas.reduce((s, l) => s + (l.acoes ? l.acoes.length : 0), 0);
    return res.json({
      preview: true,
      total_linhas: parsed.dados.length,
      responsaveis_unicos: cpfsUnicos.size,
      responsaveis_novos: respNovos,
      responsaveis_existentes: respExistentes,
      animais_a_cadastrar: totalAnimais,
      acoes_sanitarias: totalAcoes,
      erros: erros.length,
      detalhe_erros: erros.slice(0, 50),
      amostra: linhasProcessadas.slice(0, 5).map(l => ({
        responsavel: l.nome,
        documento: l.tipoDoc + ': ' + l.docLimpo,
        animal: l.animal ? `${l.animal.nome} (${l.animal.especie})` : '(sem animal nesta linha)',
        acoes: l.acoes && l.acoes.length ? l.acoes.map(x => x.tipo).join(', ') : '—'
      }))
    });
  }

  // ----- EXECUÇÃO -----
  const baseUrl = `${req.protocol}://${req.get('host')}`;
  let respInseridos = 0;
  let animaisInseridos = 0;
  let animaisDuplicados = 0;
  let acoesInseridas = 0;
  const cacheRespId = new Map(); // cpf -> id

  for (const item of linhasProcessadas) {
    try {
      // 1) Responsável: busca por CPF; se não existe, cria
      let responsavelId = cacheRespId.get(item.docLimpo);
      if (!responsavelId) {
        const existente = db.prepare('SELECT id FROM responsaveis WHERE cpf = ?').get(item.docLimpo);
        if (existente) {
          responsavelId = existente.id;
        } else {
          const r = item.row;
          const info = db.prepare(`
            INSERT INTO responsaveis (nome, cpf, rg, telefone, email, endereco, numero, bairro, cidade, uf, cep)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
          `).run(
            item.nome,
            item.docLimpo,
            val(r, 'rg') || null,
            (val(r, 'telefone') ? String(val(r, 'telefone')).replace(/\D/g, '') : null),
            val(r, 'email') || null,
            val(r, 'endereco', 'endereço') || null,
            val(r, 'numero', 'número') || null,
            val(r, 'bairro') || null,
            val(r, 'cidade') || 'Barão de Cocais',
            val(r, 'uf') || 'MG',
            (val(r, 'cep') ? String(val(r, 'cep')).replace(/\D/g, '') : null)
          );
          responsavelId = info.lastInsertRowid;
          respInseridos++;
        }
        cacheRespId.set(item.docLimpo, responsavelId);
      }

      // 2) Animal (se houver na linha)
      if (item.animal) {
        const a = item.animal;

        // ----- DEDUPLICAÇÃO DE ANIMAL -----
        // Evita duplicar quando a mesma planilha é reimportada (bug reportado).
        // Chave A: microchip (se informado) — identificador único e confiável.
        // Chave B: mesmo nome + espécie + mesmo responsável.
        // IMPORTANTE: só considera animais ATIVOS. Se o animal foi excluído
        // (inativado), permite recadastrar normalmente.
        let jaExiste = null;
        if (a.microchip && String(a.microchip).trim()) {
          jaExiste = db.prepare(
            "SELECT id FROM animais WHERE microchip = ? AND microchip IS NOT NULL AND microchip != '' AND ativo = 1"
          ).get(String(a.microchip).trim());
        }
        if (!jaExiste) {
          jaExiste = db.prepare(`
            SELECT id FROM animais
            WHERE responsavel_id = ?
              AND LOWER(TRIM(nome)) = LOWER(TRIM(?))
              AND especie = ?
              AND ativo = 1
          `).get(responsavelId, a.nome, a.especie);
        }

        let animalIdParaAcoes = null;
        if (jaExiste) {
          // Já existe — não duplica. Mas ainda podemos registrar ações sanitárias nele.
          animaisDuplicados++;
          animalIdParaAcoes = jaExiste.id;
        } else {
          const codigo = gerarCodigoAnimal();
          const qrUrl = `${baseUrl}/consulta.html?codigo=${codigo}`;
          const qrcodeData = await QRCode.toDataURL(qrUrl, { width: 200, margin: 1 });

          const infoAnimal = db.prepare(`
            INSERT INTO animais (codigo, nome, especie, raca, sexo, data_nascimento, idade_aproximada,
                                  peso_kg, porte, pelagem, status_reprodutivo, habitacao,
                                  microchip, observacoes, responsavel_id, qrcode)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
          `).run(codigo, a.nome, a.especie, a.raca, a.sexo, a.data_nascimento, a.idade_aproximada,
                 a.peso_kg, a.porte, a.pelagem, a.status_reprodutivo, a.habitacao,
                 a.microchip, a.observacoes, responsavelId, qrcodeData);
          animaisInseridos++;
          animalIdParaAcoes = infoAnimal.lastInsertRowid;
        }

        // 3) Ações sanitárias da linha (vacina, ecto, vermífugo, coleira)
        if (animalIdParaAcoes && item.acoes && item.acoes.length > 0) {
          for (const acao of item.acoes) {
            try {
              if (acao.tipo === 'vacina') {
                db.prepare(`
                  INSERT INTO vacinas (animal_id, vacina, fabricante, lote, data_aplicacao, data_validade, proxima_aplicacao, usuario_id)
                  VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                `).run(animalIdParaAcoes, acao.nome, acao.fabricante, acao.lote, acao.aplicacao, acao.validade, acao.proxima, req.usuario.id);
                acoesInseridas++;
              } else if (acao.tipo === 'vermifugo') {
                db.prepare(`
                  INSERT INTO vermifugacoes (animal_id, produto, fabricante, lote, data_aplicacao, data_validade, proxima_aplicacao, usuario_id)
                  VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                `).run(animalIdParaAcoes, acao.nome, acao.fabricante, acao.lote, acao.aplicacao, acao.validade, acao.proxima, req.usuario.id);
                acoesInseridas++;
              } else {
                // ecto e coleira vão para ectoparasitarios
                db.prepare(`
                  INSERT INTO ectoparasitarios (animal_id, produto, fabricante, lote, data_aplicacao, data_validade, proxima_aplicacao, usuario_id)
                  VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                `).run(animalIdParaAcoes, acao.nome, acao.fabricante, acao.lote, acao.aplicacao, acao.validade, acao.proxima, req.usuario.id);
                acoesInseridas++;
              }
            } catch (errAcao) {
              erros.push({ linha: item.linha, erro: `Ação sanitária (${acao.tipo}): ${errAcao.message}`, dados: item.row });
            }
          }
        }
      }
    } catch (err) {
      erros.push({ linha: item.linha, erro: err.message, dados: item.row });
    }
  }

  registrarLog(req, 'IMPORTAR', 'combinada', null, {
    responsaveis: respInseridos, animais: animaisInseridos,
    animais_duplicados: animaisDuplicados, acoes_sanitarias: acoesInseridas, erros: erros.length
  });

  res.json({
    ok: true,
    responsaveis_inseridos: respInseridos,
    animais_inseridos: animaisInseridos,
    animais_duplicados_ignorados: animaisDuplicados,
    acoes_sanitarias_inseridas: acoesInseridas,
    erros: erros.length,
    detalhe_erros: erros.slice(0, 50)
  });
});

/**
 * GET /api/importacao/templates/:tipo
 * Retorna um template CSV para o tipo solicitado
 */
router.get('/templates/:tipo', (req, res) => {
  const templates = {
    responsaveis: 'nome;cpf;rg;telefone;email;endereco;numero;bairro;cidade;uf;cep\nJoão da Silva;39053344705;MG12345;31999998888;joao@email.com;Rua das Flores;100;Centro;Barão de Cocais;MG;35970000\n',
    animais: 'nome;especie;raca;sexo;idade_aproximada;peso_kg;porte;pelagem;status_reprodutivo;habitacao;microchip;observacoes;cpf_responsavel\nThor;Canino;SRD;Macho;3 anos;15;Grande;Marrom;Castrado(a);Domiciliado;;;39053344705\nLuna;Felino;Siamesa;Fêmea;2 anos;4;Pequeno;Cinza;Inteiro(a);Domiciliado;;;52998224725\n',
    combinada: 'nome;cpf;rg;telefone;email;endereco;numero;bairro;cidade;uf;cep;animal;especie;raca;sexo;status_reprodutivo;idade;data_de_nascimento;microchip;porte;pelagem;peso;habitacao;observacoes\n' +
      'João da Silva;39053344705;MG12345;31999998888;joao@email.com;Rua das Flores;100;Centro;Barão de Cocais;MG;35970000;Thor;Canino;SRD;Macho;Castrado;3 anos;;;Grande;Marrom;15;Domiciliado;Animal dócil\n' +
      'João da Silva;39053344705;;;;;;;;;;Luna;Felino;Siamesa;Fêmea;Inteiro;2 anos;;;Pequeno;Cinza;4;Domiciliado;Mesmo dono do Thor\n' +
      'Maria Souza;52998224725;;31988887777;;Rua A;50;Lagoa;Barão de Cocais;MG;35970000;Bidu;Canino;Poodle;Macho;Castrado;;2020-05-10;;Pequeno;Branco;8;Domiciliado;\n',
    completa: 'nome;cpf;telefone;bairro;animal;especie;raca;sexo;status_reprodutivo;idade;microchip;' +
      'vacina;lote_vacina;fabricante_vacina;validade_vacina;aplicacao_vacina;proxima_vacina;' +
      'ectoparasiticida;lote_ecto;fabricante_ecto;validade_ecto;aplicacao_ecto;proxima_ecto;' +
      'vermifugo;lote_vermifugo;fabricante_vermifugo;validade_vermifugo;aplicacao_vermifugo;proxima_vermifugo;' +
      'coleira_repelente;lote_coleira;fabricante_coleira;validade_coleira;aplicacao_coleira;proxima_coleira\n' +
      'João da Silva;39053344705;31999998888;Centro;Thor;Canino;SRD;Macho;Castrado;3 anos;CHIP123;' +
      'Raiva;LOTE-RV01;Zoetis;2027-01-01;2026-06-01;2027-06-01;' +
      'Simparic;LOTE-EC01;Zoetis;2027-01-01;2026-06-01;2026-09-01;' +
      'Vermivet;LOTE-VM01;Biovet;2027-01-01;2026-06-01;2026-09-01;' +
      'Scalibor;LOTE-CO01;MSD;2027-06-01;2026-06-01;2026-12-01\n'
  };
  const tpl = templates[req.params.tipo];
  if (!tpl) return res.status(404).json({ erro: 'Template não encontrado' });
  res.setHeader('Content-Type', 'text/csv; charset=utf-8');
  res.setHeader('Content-Disposition', `attachment; filename="template_${req.params.tipo}.csv"`);
  res.send('\uFEFF' + tpl);
});

module.exports = router;
