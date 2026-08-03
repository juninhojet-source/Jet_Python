/**
 * SIGAZ - Biblioteca de utilidades comuns
 * PMBC
 */

// ============================================================
// AUTENTICAÇÃO E REDIRECIONAMENTO
// ============================================================
const SIGAZ = {
  token: localStorage.getItem('sigaz_token'),
  usuario: JSON.parse(localStorage.getItem('sigaz_usuario') || 'null'),

  exigirLogin() {
    if (!this.token) {
      window.location.href = '/index.html';
      throw new Error('Não autenticado');
    }
  },

  logout() {
    fetch('/api/auth/logout', {
      method: 'POST',
      headers: { Authorization: 'Bearer ' + this.token }
    }).finally(() => {
      localStorage.removeItem('sigaz_token');
      localStorage.removeItem('sigaz_usuario');
      window.location.href = '/index.html';
    });
  }
};

// ============================================================
// API CLIENT
// ============================================================
async function api(endpoint, options = {}) {
  const opts = {
    method: options.method || 'GET',
    headers: {
      'Content-Type': 'application/json',
      ...(SIGAZ.token ? { 'Authorization': 'Bearer ' + SIGAZ.token } : {}),
      ...(options.headers || {})
    }
  };
  if (options.body) opts.body = JSON.stringify(options.body);

  const r = await fetch('/api' + endpoint, opts);
  const ct = r.headers.get('content-type') || '';
  const data = ct.includes('application/json') ? await r.json() : await r.text();

  if (r.status === 401) {
    SIGAZ.logout();
    throw new Error('Sessão expirada');
  }
  // 428 = usuário precisa trocar senha
  if (r.status === 428) {
    if (window.location.pathname !== '/trocar-senha.html') {
      window.location.href = '/trocar-senha.html';
    }
    throw new Error(data.erro || 'Troca de senha obrigatória');
  }
  if (!r.ok) throw new Error(data.erro || data || 'Erro na requisição');
  return data;
}

// ============================================================
// TOASTS
// ============================================================
function getToastContainer() {
  let c = document.getElementById('toastContainer');
  if (!c) {
    c = document.createElement('div');
    c.id = 'toastContainer';
    c.className = 'toast-container';
    document.body.appendChild(c);
  }
  return c;
}

function toast(mensagem, tipo = 'info', duracao = 3500) {
  const c = getToastContainer();
  const el = document.createElement('div');
  el.className = `toast ${tipo}`;
  const icones = { sucesso: '✓', erro: '✕', alerta: '⚠', info: 'ℹ' };
  el.innerHTML = `<span style="font-size:18px;font-weight:700;">${icones[tipo] || 'ℹ'}</span><span>${mensagem}</span>`;
  c.appendChild(el);
  setTimeout(() => {
    el.style.transition = 'opacity 0.3s';
    el.style.opacity = '0';
    setTimeout(() => el.remove(), 300);
  }, duracao);
}

// ============================================================
// MODAL
// ============================================================
function abrirModal(id) {
  document.getElementById(id).classList.add('ativo');
}

function fecharModal(id) {
  document.getElementById(id).classList.remove('ativo');
}

// NOTA: Removido o "fechar ao clicar fora" para evitar perda acidental
// de dados durante o cadastro. O usuário fecha pelo botão X ou Cancelar.

// ============================================================
// FORMATAÇÃO
// ============================================================
function formatarData(dataIso) {
  if (!dataIso) return '—';
  const [ano, mes, dia] = dataIso.substring(0, 10).split('-');
  return `${dia}/${mes}/${ano}`;
}

function formatarDataHora(iso) {
  if (!iso) return '—';
  const d = new Date(iso.replace(' ', 'T'));
  return d.toLocaleString('pt-BR');
}

function formatarCpf(cpf) {
  if (!cpf) return '—';
  const c = String(cpf).replace(/\D/g, '');
  if (c.length !== 11) return cpf;
  return `${c.substring(0,3)}.${c.substring(3,6)}.${c.substring(6,9)}-${c.substring(9)}`;
}

function escapeHtml(s) {
  if (s == null) return '';
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// ============================================================
// SIDEBAR (montagem dinâmica)
// ============================================================
function renderizarShell(paginaAtiva) {
  SIGAZ.exigirLogin();

  const u = SIGAZ.usuario || {};
  const iniciais = (u.nome || 'U').split(' ').slice(0, 2).map(s => s[0]).join('').toUpperCase();

  // Sidebar
  const menus = [
    { id: 'dashboard', href: '/dashboard.html', icone: '🏠', label: 'Dashboard' },
    { id: 'animais', href: '/animais.html', icone: '🐶', label: 'Animais' },
    { id: 'responsaveis', href: '/responsaveis.html', icone: '👤', label: 'Responsáveis' },
    { id: 'agendamentos', href: '/agendamentos.html', icone: '📅', label: 'Agendamentos' },
    { id: 'vacinacao', href: '/vacinacao.html', icone: '💉', label: 'Vacinação' },
    { id: 'zoonoses', href: '/zoonoses.html', icone: '🦠', label: 'Zoonoses' },
    { id: 'mordeduras', href: '/mordeduras.html', icone: '🦷', label: 'Mordeduras (SINAN)' },
    { id: 'campanhas', href: '/campanhas.html', icone: '📣', label: 'Campanhas' },
    { id: 'denuncias', href: '/denuncias.html', icone: '📢', label: 'Denúncias' },
    { id: 'estoque', href: '/estoque.html', icone: '📦', label: 'Estoque' },
    { id: 'carteirinhas', href: '/carteirinhas.html', icone: '🪪', label: 'Carteirinhas' },
    { id: 'mapa', href: '/mapa.html', icone: '🗺️', label: 'Mapa' },
    { id: 'boletim', href: '/boletim.html', icone: '📊', label: 'Boletim SINAN' },
    { id: 'relatorios', href: '/relatorios.html', icone: '📄', label: 'Relatórios' },
    { id: 'sobre', href: '/sobre.html', icone: 'ℹ️', label: 'Sobre / LGPD' },
  ];
  const menusAdmin = [
    { id: 'bairros', href: '/bairros.html', icone: '📍', label: 'Bairros' },
    { id: 'importacao', href: '/importacao.html', icone: '📥', label: 'Importação' },
    { id: 'usuarios', href: '/usuarios.html', icone: '⚙️', label: 'Administração' },
  ];

  const itensHtml = menus.map(m => `
    <a href="${m.href}" class="${paginaAtiva === m.id ? 'ativo' : ''}">
      <span class="ico">${m.icone}</span> ${m.label}
    </a>
  `).join('');

  const adminHtml = u.perfil === 'admin' || u.perfil === 'ti' ? `
    <div class="sidebar-section-title">Administração</div>
    ${menusAdmin.map(m => `
      <a href="${m.href}" class="${paginaAtiva === m.id ? 'ativo' : ''}">
        <span class="ico">${m.icone}</span> ${m.label}
      </a>
    `).join('')}
  ` : '';

  const sidebarHtml = `
    <aside class="sidebar">
      <div class="sidebar-brand">
        <div class="sidebar-brand-logo">
          <img src="/assets/brasao.png" alt="Brasão Barão de Cocais">
        </div>
        <div class="sidebar-brand-text">
          <strong>SIGAZ</strong>
          <small>PMBC · Saúde</small>
        </div>
      </div>
      <nav class="sidebar-nav">
        <div class="sidebar-section-title">Principal</div>
        ${itensHtml}
        ${adminHtml}
      </nav>
      <div class="sidebar-footer">
        <strong>SIGAZ v1.0</strong><br>
        Dep. de Informática e Tecnologia<br>
        Prefeitura Municipal de<br>
        Barão de Cocais — MG<br>
        <span style="color: rgba(255,255,255,0.85); font-weight: 600;">📞 (31) 3837-7661</span><br>
        <a href="/privacidade.html" target="_blank" style="color:rgba(255,255,255,0.7);font-size:11px;text-decoration:underline;margin-top:8px;display:inline-block;">🛡️ Política de Privacidade · LGPD</a>
      </div>
    </aside>
  `;

  return { sidebarHtml, usuario: u, iniciais };
}

function renderizarTopbar(titulo, subtitulo) {
  const u = SIGAZ.usuario || {};
  const iniciais = (u.nome || 'U').split(' ').slice(0, 2).map(s => s[0]).join('').toUpperCase();
  const perfilLabel = {
    admin: 'Administrador',
    veterinario: 'Méd. Veterinário',
    auxiliar: 'Auxiliar',
    endemias: 'Endemias',
    secretaria: 'Secretaria',
    ti: 'TI'
  }[u.perfil] || u.perfil;

  return `
    <header class="topbar">
      <div class="topbar-titulo">
        <h1>${escapeHtml(titulo)}</h1>
        <p>${escapeHtml(subtitulo || '')}</p>
      </div>
      <div class="topbar-acoes">
        <button class="btn-tema" onclick="alternarTema()" title="Alternar tema claro/escuro" id="btnTema">🌙</button>
        <div class="user-chip">
          <div class="user-avatar">${iniciais}</div>
          <div style="line-height:1.2;">
            <div class="user-nome">${escapeHtml(u.nome || '')}</div>
            <div class="user-perfil">${escapeHtml(perfilLabel || '')}</div>
          </div>
        </div>
        <button class="btn btn-secundario btn-sm" onclick="SIGAZ.logout()">Sair</button>
      </div>
    </header>
  `;
}

// Tema claro/escuro
function aplicarTema() {
  const tema = localStorage.getItem('sigaz_tema') || 'claro';
  document.documentElement.setAttribute('data-tema', tema);
  const btn = document.getElementById('btnTema');
  if (btn) btn.textContent = tema === 'escuro' ? '☀️' : '🌙';
}

function alternarTema() {
  const atual = localStorage.getItem('sigaz_tema') || 'claro';
  const novo = atual === 'claro' ? 'escuro' : 'claro';
  localStorage.setItem('sigaz_tema', novo);
  aplicarTema();
}

// PWA: registrar service worker
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/service-worker.js').catch(() => {});
  });
}

// Aplicar tema imediatamente, antes da página renderizar
(function() {
  const tema = localStorage.getItem('sigaz_tema') || 'claro';
  document.documentElement.setAttribute('data-tema', tema);
})();

/**
 * Renderiza o shell completo (sidebar + topbar) em volta do conteúdo já presente
 * Espera <main id="conteudo"> e <div id="appShell"> no HTML.
 */
function montarShell(opcoes) {
  const { sidebarHtml } = renderizarShell(opcoes.paginaAtiva);
  const topbarHtml = renderizarTopbar(opcoes.titulo, opcoes.subtitulo);
  document.getElementById('appShell').innerHTML = sidebarHtml +
    `<div class="main">${topbarHtml}<div class="conteudo" id="conteudo"></div></div>`;
  aplicarTema();
  mostrarBannerLgpd();
}

function mostrarBannerLgpd() {
  // Servidor já reconheceu? Não mostra de novo
  if (localStorage.getItem('sigaz_lgpd_ack') === '1') return;
  // Não mostra na própria página da política
  if (window.location.pathname === '/privacidade.html') return;

  const banner = document.createElement('div');
  banner.id = 'bannerLgpd';
  banner.style.cssText = `
    position: fixed; bottom: 18px; left: 18px; right: 18px;
    background: var(--branco); border: 1px solid var(--cinza-300);
    border-left: 4px solid var(--azul-bandeira);
    border-radius: 8px; padding: 16px 20px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.18);
    z-index: 9999; max-width: 720px; margin: 0 auto;
    display: flex; gap: 16px; align-items: center; flex-wrap: wrap;
    font-size: 13px; line-height: 1.5;
  `;
  banner.innerHTML = `
    <div style="flex:1;min-width:240px;">
      <strong style="display:block;color:var(--azul-bandeira);margin-bottom:4px;">🛡️ Conformidade com a LGPD</strong>
      Este sistema trata dados pessoais conforme a Lei nº 13.709/2018 (LGPD). Os dados são armazenados em servidor municipal seguro e usados exclusivamente para finalidades de saúde pública e gestão animal.
    </div>
    <div style="display:flex;gap:8px;flex-wrap:wrap;">
      <a href="/privacidade.html" target="_blank" class="btn btn-secundario btn-sm">Saiba mais</a>
      <button class="btn btn-primario btn-sm" onclick="aceitarLgpd()">Entendi</button>
    </div>
  `;
  document.body.appendChild(banner);
}

function aceitarLgpd() {
  localStorage.setItem('sigaz_lgpd_ack', '1');
  const b = document.getElementById('bannerLgpd');
  if (b) b.remove();
}
