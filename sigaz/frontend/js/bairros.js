/**
 * SIGAZ - Helper de Bairros Oficiais
 * PMBC
 *
 * Transforma campos de bairro em dropdown padronizado + opção "Outros".
 *
 * USO:
 *   // 1. Em HTML, criar um <select> simples:
 *   //    <select id="bairro" class="form-controle"></select>
 *   //
 *   // 2. Em JS, inicializar:
 *   //    await BairrosHelper.inicializar('bairro');
 *   //
 *   // 3. Para ler o valor preenchido:
 *   //    BairrosHelper.lerValor('bairro') → "Centro" ou "Outro: Bairro X"
 *   //
 *   // 4. Para preencher (ex: edição):
 *   //    BairrosHelper.definirValor('bairro', 'Centro')
 */
window.BairrosHelper = (function() {
  let _cacheBairros = null;
  const VALOR_OUTROS = '__OUTROS__';

  /**
   * Carrega a lista de bairros oficiais (com cache de sessão).
   */
  async function carregarBairros() {
    if (_cacheBairros) return _cacheBairros;
    try {
      const r = await api('/bairros');
      _cacheBairros = r.dados;
      return _cacheBairros;
    } catch (err) {
      console.error('[SIGAZ-Bairros] Erro ao carregar:', err);
      return [];
    }
  }

  /**
   * Inicializa um select com a lista de bairros + opção "Outros".
   * Cria um input adjacente para "Outros".
   */
  async function inicializar(idSelect, opcoes) {
    const sel = document.getElementById(idSelect);
    if (!sel) {
      console.warn(`[SIGAZ-Bairros] Select #${idSelect} não encontrado`);
      return;
    }
    const obrigatorio = !!(opcoes && opcoes.obrigatorio);
    const placeholder = (opcoes && opcoes.placeholder) || '— Selecione o bairro —';

    const bairros = await carregarBairros();

    // Constrói as opções
    let html = `<option value="">${placeholder}</option>`;
    for (const b of bairros) {
      const sufixo = b.eh_distrito ? ' (Distrito)' : '';
      html += `<option value="${escapeHtml(b.nome)}">${escapeHtml(b.nome)}${sufixo}</option>`;
    }
    html += `<option value="${VALOR_OUTROS}">— Outros (digitar manualmente) —</option>`;
    sel.innerHTML = html;
    if (obrigatorio) sel.required = true;

    // Cria input "Outros" logo após o select, escondido por padrão
    const idOutros = idSelect + '_outros';
    let inputOutros = document.getElementById(idOutros);
    if (!inputOutros) {
      inputOutros = document.createElement('input');
      inputOutros.type = 'text';
      inputOutros.id = idOutros;
      inputOutros.className = 'form-controle';
      inputOutros.placeholder = 'Informe o nome do bairro';
      inputOutros.maxLength = 80;
      inputOutros.style.display = 'none';
      inputOutros.style.marginTop = '6px';
      sel.parentNode.insertBefore(inputOutros, sel.nextSibling);
    }

    // Toggle do input quando "Outros" é selecionado
    sel.addEventListener('change', () => {
      if (sel.value === VALOR_OUTROS) {
        inputOutros.style.display = 'block';
        if (obrigatorio) inputOutros.required = true;
        setTimeout(() => inputOutros.focus(), 50);
      } else {
        inputOutros.style.display = 'none';
        inputOutros.required = false;
        inputOutros.value = '';
      }
    });
  }

  /**
   * Lê o valor final escolhido pelo usuário.
   * Retorna a string do bairro (oficial ou digitado).
   */
  function lerValor(idSelect) {
    const sel = document.getElementById(idSelect);
    if (!sel) return '';
    if (sel.value === VALOR_OUTROS) {
      const inputOutros = document.getElementById(idSelect + '_outros');
      return inputOutros ? inputOutros.value.trim() : '';
    }
    return sel.value;
  }

  /**
   * Preenche o select com um valor existente (em edição).
   * Se o valor não estiver na lista oficial, automaticamente seleciona "Outros"
   * e coloca o texto no campo manual.
   */
  async function definirValor(idSelect, valor) {
    const sel = document.getElementById(idSelect);
    if (!sel) return;

    // Garante que as opções já foram carregadas
    if (!_cacheBairros) await carregarBairros();

    // Aguarda eventuais opções carregadas se ainda for assíncrono
    if (sel.options.length <= 1) await new Promise(r => setTimeout(r, 100));

    const v = (valor || '').trim();
    if (!v) {
      sel.value = '';
      return;
    }

    // Procura match exato (case-insensitive)
    let achou = false;
    for (let i = 0; i < sel.options.length; i++) {
      if (sel.options[i].value.toLowerCase() === v.toLowerCase()) {
        sel.value = sel.options[i].value;
        achou = true;
        break;
      }
    }

    if (!achou) {
      // Valor antigo que não está na lista oficial → cai em "Outros"
      sel.value = VALOR_OUTROS;
      const inputOutros = document.getElementById(idSelect + '_outros');
      if (inputOutros) {
        inputOutros.style.display = 'block';
        inputOutros.value = v;
      }
    }
  }

  /**
   * Recarrega a lista (útil após cadastrar um bairro novo no admin).
   */
  function limparCache() {
    _cacheBairros = null;
  }

  return { inicializar, lerValor, definirValor, carregarBairros, limparCache };
})();
