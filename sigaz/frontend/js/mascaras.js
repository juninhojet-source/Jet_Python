/**
 * SIGAZ - Máscaras, Validações e Busca de CEP
 * PMBC - Departamento de Informática
 */

// ============================================================
// VALIDAÇÃO DE CPF
// ============================================================
function validarCpf(cpf) {
  if (!cpf) return false;
  const c = String(cpf).replace(/\D/g, '');
  if (c.length !== 11) return false;
  if (/^(\d)\1{10}$/.test(c)) return false;

  let soma = 0;
  for (let i = 0; i < 9; i++) soma += parseInt(c[i]) * (10 - i);
  let resto = (soma * 10) % 11;
  if (resto === 10) resto = 0;
  if (resto !== parseInt(c[9])) return false;

  soma = 0;
  for (let i = 0; i < 10; i++) soma += parseInt(c[i]) * (11 - i);
  resto = (soma * 10) % 11;
  if (resto === 10) resto = 0;
  if (resto !== parseInt(c[10])) return false;

  return true;
}

// ============================================================
// MÁSCARAS DE FORMATAÇÃO
// ============================================================

function mascararCpf(valor) {
  const v = String(valor).replace(/\D/g, '').substring(0, 11);
  if (v.length <= 3) return v;
  if (v.length <= 6) return `${v.substring(0,3)}.${v.substring(3)}`;
  if (v.length <= 9) return `${v.substring(0,3)}.${v.substring(3,6)}.${v.substring(6)}`;
  return `${v.substring(0,3)}.${v.substring(3,6)}.${v.substring(6,9)}-${v.substring(9)}`;
}

function mascararTelefone(valor) {
  const v = String(valor).replace(/\D/g, '').substring(0, 11);
  if (v.length === 0) return '';
  if (v.length <= 2) return `(${v}`;
  if (v.length <= 6) return `(${v.substring(0,2)}) ${v.substring(2)}`;
  if (v.length <= 10) return `(${v.substring(0,2)}) ${v.substring(2,6)}-${v.substring(6)}`;
  return `(${v.substring(0,2)}) ${v.substring(2,7)}-${v.substring(7)}`;
}

function mascararCep(valor) {
  const v = String(valor).replace(/\D/g, '').substring(0, 8);
  if (v.length <= 5) return v;
  return `${v.substring(0,5)}-${v.substring(5)}`;
}

function mascararRg(valor) {
  // RG é variável por estado, então só limitamos caracteres e tiramos não-alfanuméricos
  return String(valor).replace(/[^\dXx]/g, '').substring(0, 12);
}

// ============================================================
// APLICAR MÁSCARAS EM INPUTS
// ============================================================

/**
 * Aplica máscara ao input enquanto digita.
 * Uso: aplicarMascara(input, mascararCpf)
 */
function aplicarMascara(input, fnMascara) {
  if (!input) return;
  input.addEventListener('input', (e) => {
    const cursorPos = e.target.selectionStart;
    const valorAntigo = e.target.value;
    const valorNovo = fnMascara(valorAntigo);
    e.target.value = valorNovo;
    // Ajustar cursor (aproximado, suficiente pra UX)
    const diff = valorNovo.length - valorAntigo.length;
    e.target.setSelectionRange(cursorPos + diff, cursorPos + diff);
  });
}

/**
 * Atalho — aplica máscara num input pelo id
 */
function mascarar(idInput, tipo) {
  const el = document.getElementById(idInput);
  if (!el) return;
  const fns = {
    cpf: mascararCpf,
    telefone: mascararTelefone,
    cep: mascararCep,
    rg: mascararRg
  };
  const fn = fns[tipo];
  if (fn) aplicarMascara(el, fn);
}

// ============================================================
// BUSCA DE CEP (ViaCEP)
// ============================================================

/**
 * Busca o CEP no ViaCEP e preenche os campos.
 * Espera receber um objeto com os IDs dos inputs:
 * { cep, endereco, bairro, cidade, uf }
 *
 * O segundo parâmetro `opcoes` pode conter:
 *   - sobrescrever: true  → preenche mesmo se o campo já tem valor (padrão: true)
 */
async function buscarCep(cep, campos, opcoes) {
  const cepLimpo = String(cep).replace(/\D/g, '');
  if (cepLimpo.length !== 8) return false;
  const sobrescrever = !opcoes || opcoes.sobrescrever !== false;

  console.log('[SIGAZ-CEP] Buscando CEP:', cepLimpo);

  let dados = null;
  let origem = null;

  // 1ª tentativa: usar o backend como proxy (passa pela rede da prefeitura)
  try {
    const r = await fetch('/api/publico/cep/' + cepLimpo, { cache: 'no-store' });
    if (r.ok) {
      dados = await r.json();
      origem = 'backend (proxy)';
    } else if (r.status === 404) {
      console.warn('[SIGAZ-CEP] Backend respondeu: CEP não encontrado');
      if (typeof toast === 'function') toast('CEP não encontrado', 'alerta');
      return false;
    } else {
      const erro = await r.json().catch(() => ({}));
      console.warn('[SIGAZ-CEP] Backend retornou erro:', r.status, erro.erro);
    }
  } catch (err) {
    console.warn('[SIGAZ-CEP] Backend indisponível:', err.message);
  }

  // 2ª tentativa: chamar ViaCEP diretamente do navegador (fallback)
  if (!dados) {
    try {
      console.log('[SIGAZ-CEP] Tentando ViaCEP diretamente do navegador...');
      const r = await fetch(`https://viacep.com.br/ws/${cepLimpo}/json/`, { cache: 'no-store' });
      if (!r.ok) throw new Error('HTTP ' + r.status);
      const v = await r.json();
      if (v.erro) {
        if (typeof toast === 'function') toast('CEP não encontrado', 'alerta');
        return false;
      }
      // Normalizar formato (ViaCEP usa "logradouro", "localidade")
      dados = {
        logradouro: v.logradouro || '',
        bairro: v.bairro || '',
        cidade: v.localidade || '',
        uf: v.uf || ''
      };
      origem = 'navegador (direto)';
    } catch (err) {
      console.error('[SIGAZ-CEP] Falha total:', err.message);
      if (typeof toast === 'function') {
        toast('Não foi possível consultar o CEP. Verifique se o firewall libera viacep.com.br. Preencha o endereço manualmente.', 'erro', 5000);
      }
      return false;
    }
  }

  console.log('[SIGAZ-CEP] Dados recebidos via', origem, '→', dados);

  // Preencher campos
  const preencher = (id, valor) => {
    if (!id || !valor) return;
    const el = document.getElementById(id);
    if (!el) {
      console.warn('[SIGAZ-CEP] Campo não encontrado:', id);
      return;
    }
    if (sobrescrever || !el.value || el.value.trim() === '') {
      el.value = valor;
      // Disparar evento change para que validações reativas funcionem
      el.dispatchEvent(new Event('change', { bubbles: true }));
    }
  };

  preencher(campos.endereco, dados.logradouro);
  preencher(campos.bairro, dados.bairro);
  preencher(campos.cidade, dados.cidade);
  preencher(campos.uf, dados.uf);

  if (typeof toast === 'function') toast('Endereço preenchido pelo CEP', 'sucesso', 1500);
  return true;
}

/**
 * Liga a busca automática de CEP a um input.
 * O CEP é buscado quando:
 *   - o usuário completa 8 dígitos (input)
 *   - ou quando o campo perde o foco com 8 dígitos (blur)
 *
 * Inclui debounce de 500ms para evitar requisições duplicadas.
 */
function ligarBuscaCep(idCep, campos, opcoes) {
  const el = document.getElementById(idCep);
  if (!el) return;

  let ultimoCep = '';
  let timer = null;

  const tentarBuscar = () => {
    const cep = el.value.replace(/\D/g, '');
    if (cep.length !== 8 || cep === ultimoCep) return;
    ultimoCep = cep;
    buscarCep(cep, campos, opcoes);
  };

  // Dispara ao completar 8 dígitos (com debounce)
  el.addEventListener('input', () => {
    if (timer) clearTimeout(timer);
    timer = setTimeout(tentarBuscar, 500);
  });

  // Dispara também ao sair do campo (caso o usuário cole o CEP)
  el.addEventListener('blur', () => {
    if (timer) clearTimeout(timer);
    tentarBuscar();
  });
}
