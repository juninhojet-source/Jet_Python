// Máscaras de entrada: CPF (000.000.000-00) e valores em R$ (1.234,56).
(function () {
  "use strict";

  function mascaraCPF(v) {
    v = (v || "").replace(/\D/g, "").slice(0, 11);
    if (v.length > 9) return v.replace(/(\d{3})(\d{3})(\d{3})(\d{1,2})/, "$1.$2.$3-$4");
    if (v.length > 6) return v.replace(/(\d{3})(\d{3})(\d{1,3})/, "$1.$2.$3");
    if (v.length > 3) return v.replace(/(\d{3})(\d{1,3})/, "$1.$2");
    return v;
  }

  function mascaraDinheiro(v) {
    // mantém apenas dígitos; os 2 últimos são os centavos
    var d = (v || "").replace(/\D/g, "");
    if (!d) return "";
    d = d.replace(/^0+(?=\d)/, "");          // remove zeros à esquerda
    while (d.length < 3) d = "0" + d;         // garante centavos
    var centavos = d.slice(-2);
    var inteiros = d.slice(0, -2);
    inteiros = inteiros.replace(/\B(?=(\d{3})+(?!\d))/g, "."); // milhar
    return inteiros + "," + centavos;
  }

  function aplicar(seletor, fn) {
    document.querySelectorAll(seletor).forEach(function (el) {
      var ini = fn(el.value);
      if (ini !== el.value) el.value = ini;
      el.addEventListener("input", function () {
        var pos = el.selectionStart;
        var antes = el.value.length;
        el.value = fn(el.value);
        // ajuste simples do cursor
        var depois = el.value.length;
        try { el.setSelectionRange(pos + (depois - antes), pos + (depois - antes)); } catch (e) {}
      });
    });
  }

  function init() {
    aplicar("input.cpf", mascaraCPF);
    aplicar("input.dinheiro", mascaraDinheiro);
  }

  if (document.readyState !== "loading") init();
  else document.addEventListener("DOMContentLoaded", init);
})();
