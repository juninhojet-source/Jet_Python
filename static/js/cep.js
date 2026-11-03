// Preenche endereço/bairro/cidade/UF a partir do CEP (ViaCEP), ao sair do campo.
// Falha silenciosamente se não houver internet — os campos continuam editáveis.
(function () {
  function definir(id, valor, sobrescrever) {
    var el = document.getElementById(id);
    if (!el || !valor) return;
    if (sobrescrever || !el.value) el.value = valor;
  }

  document.addEventListener("DOMContentLoaded", function () {
    var cep = document.getElementById("id_cep");
    if (!cep) return;
    cep.addEventListener("blur", function () {
      var v = (cep.value || "").replace(/\D/g, "");
      if (v.length !== 8) return;
      fetch("https://viacep.com.br/ws/" + v + "/json/")
        .then(function (r) { return r.json(); })
        .then(function (d) {
          if (!d || d.erro) return;
          definir("id_endereco", d.logradouro, false);
          definir("id_bairro", d.bairro, false);
          definir("id_cidade", d.localidade, true);
          definir("id_uf", d.uf, true);
        })
        .catch(function () {});
    });
  });
})();
