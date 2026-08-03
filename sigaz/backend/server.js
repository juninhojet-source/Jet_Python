/**
 * ============================================================
 * SIGAZ — Sistema Integrado de Gestão Animal e Zoonoses
 * Prefeitura Municipal de Barão de Cocais
 * Servidor Principal
 * ============================================================
 */
const express = require('express');
const cors = require('cors');
const path = require('path');
const fs = require('fs');
require('dotenv').config();

const db = require('./db/connection');
const { limitarTaxa } = require('./middleware/rateLimit');
const { version: VERSAO_SISTEMA } = require('../package.json');

const PORT = process.env.PORT || 3000;
const app = express();

// Confia no reverse proxy (IIS + ARR) para obter o IP real do cliente em
// req.ip — necessário para o rate limiting funcionar por IP, não globalmente.
app.set('trust proxy', true);

// ----- Middlewares globais -----
app.use(cors());

// Limite de corpo padrão baixo (protege endpoints públicos sem login contra
// esgotamento de memória). A restauração de banco (upload em base64) recebe
// um limite maior só para sua própria rota, abaixo.
const jsonPadrao = express.json({ limit: '10mb' });
const urlencodedPadrao = express.urlencoded({ extended: true, limit: '10mb' });
app.use((req, res, next) => req.path === '/api/admin/restore' ? next() : jsonPadrao(req, res, next));
app.use((req, res, next) => req.path === '/api/admin/restore' ? next() : urlencodedPadrao(req, res, next));
app.use('/api/admin/restore', express.json({ limit: '50mb' }));

// Log básico de requisições
app.use((req, res, next) => {
  const t = new Date().toISOString().substring(11, 19);
  console.log(`[${t}] ${req.method} ${req.path}`);
  next();
});

// ----- Frontend estático -----
const frontendDir = path.join(__dirname, '..', 'frontend');

// O arquivo do Service Worker nunca pode ser servido do cache HTTP — senão
// o navegador não percebe uma versão nova mesmo com auto-update no cliente.
app.get('/service-worker.js', (req, res) => {
  res.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate');
  res.sendFile(path.join(frontendDir, 'service-worker.js'));
});

app.use(express.static(frontendDir));

// ----- Verificar se o banco está inicializado -----
const tabela = db.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name='usuarios'").get();
if (!tabela) {
  console.error('\n⚠️  Banco de dados não inicializado!');
  console.error('Execute: npm run init-db\n');
  process.exit(1);
}

// ----- Rotas públicas (sem autenticação) - DEVEM vir antes dos routers com auth -----

// Healthcheck
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', servico: 'SIGAZ', versao: VERSAO_SISTEMA, timestamp: new Date().toISOString() });
});

// Consulta pública via QR Code
app.get('/api/publico/animal/:codigo', (req, res) => {
  const animal = db.prepare(`
    SELECT a.codigo, a.nome, a.especie, a.raca, a.sexo, a.idade_aproximada,
           a.status_reprodutivo, a.microchip, a.foto,
           r.nome AS responsavel_nome, r.telefone AS responsavel_telefone,
           r.bairro AS responsavel_bairro
    FROM animais a
    LEFT JOIN responsaveis r ON r.id = a.responsavel_id
    WHERE a.codigo = ? AND a.ativo = 1
  `).get(req.params.codigo);

  if (!animal) return res.status(404).json({ erro: 'Animal não encontrado' });

  const vacinas = db.prepare(`
    SELECT vacina, data_aplicacao, proxima_aplicacao
    FROM vacinas WHERE animal_id = (SELECT id FROM animais WHERE codigo = ?)
    ORDER BY data_aplicacao DESC LIMIT 10
  `).all(req.params.codigo);

  res.json({ animal, vacinas });
});

// ----- Denúncia pública (cidadão registra maus-tratos) -----
app.post('/api/publico/denuncia', limitarTaxa(5, 10 * 60 * 1000), (req, res) => {
  const { tipo, descricao, endereco, bairro, referencia,
          denunciante_nome, denunciante_telefone, anonimo } = req.body;
  if (!descricao || descricao.length < 10) {
    return res.status(400).json({ erro: 'Descrição é obrigatória (mínimo 10 caracteres)' });
  }
  // Gera protocolo único
  const ano = new Date().getFullYear();
  const ult = db.prepare(`SELECT protocolo FROM denuncias WHERE protocolo LIKE ? ORDER BY id DESC LIMIT 1`).get(`DEN-${ano}-%`);
  let proximo = 1;
  if (ult) proximo = parseInt(ult.protocolo.split('-')[2]) + 1;
  const protocolo = `DEN-${ano}-${String(proximo).padStart(5, '0')}`;

  const info = db.prepare(`
    INSERT INTO denuncias (protocolo, tipo, descricao, endereco, bairro, referencia,
                            denunciante_nome, denunciante_telefone, anonimo, status)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Recebida')
  `).run(protocolo, tipo || null, descricao, endereco || null, bairro || null, referencia || null,
         anonimo ? null : (denunciante_nome || null),
         anonimo ? null : (denunciante_telefone || null),
         anonimo ? 1 : 0);

  res.status(201).json({ protocolo, mensagem: 'Denúncia registrada com sucesso. Guarde seu protocolo para consultas futuras.' });
});

// ----- Consulta pública de denúncia pelo protocolo -----
app.get('/api/publico/denuncia/:protocolo', (req, res) => {
  const d = db.prepare(`
    SELECT protocolo, tipo, status, data_atendimento, criado_em,
           CASE WHEN anonimo = 1 THEN '(anônima)' ELSE denunciante_nome END AS denunciante
    FROM denuncias WHERE protocolo = ?
  `).get(req.params.protocolo);
  if (!d) return res.status(404).json({ erro: 'Protocolo não encontrado' });
  res.json(d);
});

// ----- Proxy de busca de CEP (passa pelo servidor — útil em redes restritas) -----
app.get('/api/publico/cep/:cep', limitarTaxa(30, 60 * 1000), async (req, res) => {
  const cep = String(req.params.cep || '').replace(/\D/g, '');
  if (cep.length !== 8) {
    return res.status(400).json({ erro: 'CEP deve ter 8 dígitos' });
  }
  try {
    // Node 22+ tem fetch nativo
    const r = await fetch(`https://viacep.com.br/ws/${cep}/json/`, {
      headers: { 'User-Agent': 'SIGAZ-PMBC/1.0' }
    });
    if (!r.ok) {
      return res.status(502).json({ erro: 'ViaCEP retornou status ' + r.status });
    }
    const dados = await r.json();
    if (dados.erro) {
      return res.status(404).json({ erro: 'CEP não encontrado' });
    }
    // Normaliza o formato para o frontend
    res.json({
      cep: dados.cep,
      logradouro: dados.logradouro || '',
      bairro: dados.bairro || '',
      cidade: dados.localidade || '',
      uf: dados.uf || ''
    });
  } catch (err) {
    console.error('Erro ViaCEP (proxy):', err.message);
    res.status(502).json({
      erro: 'Servidor não conseguiu acessar ViaCEP. Verifique se o firewall libera viacep.com.br (porta 443).'
    });
  }
});

// ----- Lista pública de bairros oficiais (usada em formulários do cidadão) -----
app.get('/api/publico/bairros', (req, res) => {
  const dados = db.prepare(`
    SELECT id, nome, eh_distrito FROM bairros WHERE ativo = 1 ORDER BY ordem, nome
  `).all();
  res.json({ dados });
});

// ----- API Routes (com autenticação) -----
app.use('/api/auth', require('./routes/auth'));
app.use('/api/responsaveis', require('./routes/responsaveis'));
app.use('/api/animais', require('./routes/animais'));
app.use('/api/sanitario', require('./routes/sanitario'));
app.use('/api/zoonoses', require('./routes/zoonoses'));
app.use('/api/usuarios', require('./routes/usuarios'));
app.use('/api/admin', require('./routes/admin'));
app.use('/api/agendamentos', require('./routes/agendamentos'));
app.use('/api/importacao', require('./routes/importacao'));
app.use('/api/boletim', require('./routes/boletim'));
app.use('/api/mapa', require('./routes/mapa'));
app.use('/api/mordeduras', require('./routes/mordeduras'));
app.use('/api/prontuario', require('./routes/prontuario'));
app.use('/api/bairros', require('./routes/bairros'));
app.use('/api', require('./routes/operacao'));
app.use('/api', require('./routes/dashboard'));

// ----- SPA fallback (rota raiz envia login) -----
app.get('/', (req, res) => {
  res.sendFile(path.join(frontendDir, 'index.html'));
});

// ----- 404 handler -----
app.use((req, res) => {
  if (req.path.startsWith('/api/')) {
    return res.status(404).json({ erro: 'Endpoint não encontrado' });
  }
  res.status(404).sendFile(path.join(frontendDir, 'index.html'));
});

// ----- Error handler -----
app.use((err, req, res, next) => {
  console.error('ERRO:', err);
  res.status(500).json({ erro: err.message || 'Erro interno' });
});

app.listen(PORT, () => {
  console.log('\n==========================================');
  console.log('  SIGAZ — Sistema rodando');
  console.log('  Prefeitura Municipal de Barão de Cocais');
  console.log('==========================================');
  console.log(`  Servidor:  http://localhost:${PORT}`);
  console.log(`  API:       http://localhost:${PORT}/api/health`);
  console.log('==========================================\n');

  // Iniciar agendador interno de backup automático
  try {
    const { iniciarAgendador } = require('./utils/scheduler');
    iniciarAgendador();
  } catch (err) {
    console.error('Erro ao iniciar agendador:', err.message);
  }
});
