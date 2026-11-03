# 01 — Diagnóstico

Leitura crítica do **Edital de Chamamento nº 001/2026 (Barão de Cocais/MG)** e do documento
de requisitos (`Sistema_bolsa_familia.docx`), com o objetivo de iniciar o desenvolvimento
com segurança jurídica e técnica.

---

## 1. O que o sistema é (e o que não é)

**É** uma ferramenta **interna** da Secretaria Municipal de Assistência Social, operada por
servidores. As inscrições são presenciais, "por ordem de chegada", na sede da Secretaria,
de 01 a 30/09/2026 (item 2.1 do edital). **Não** é um portal de autoatendimento do cidadão.

Consequências de projeto:
- O ator primário é o **servidor** (atendente/analista/comissão), não o requerente.
- A "ordem de chegada" **não** é critério de classificação (item 7.2) — serve apenas para
  organizar o atendimento. A classificação é 100% por pontuação + desempate.
- O sistema municipal **termina** no encaminhamento à CAIXA. Análise de crédito, simulação
  e contratação são da CAIXA (itens 9.1 a 9.7) e estão **fora do escopo**.

## 2. Alinhamento entre os dois documentos

O `.docx` é um bom anteprojeto e está, na maior parte, **alinhado ao edital**. Ele acerta em
pontos que a lista de campos original do pedido não cobria e que o edital **exige**:

- **Cadastro individual de cada integrante** do núcleo (não só "nº de integrantes"), com
  parentesco, idade, deficiência, e renda por pessoa → necessário para renda per capita,
  desempate e grupos prioritários.
- **Exclusão de rendas não computáveis** (BPC, Bolsa Família, Seguro-Desemprego, benefícios
  temporários) do cálculo de enquadramento (item 3.1.4.1).
- **Média do aluguel dos 3 meses** anteriores à publicação — e não um único valor mensal
  (itens 8.8.5.1, 8.8.2, 8.8.8). *Este ponto corrige o pedido original*, que previa apenas
  "valor mensal do aluguel".
- **Bloqueio do cadastro após finalização** da inscrição (Anexo II: "após realização deste
  requerimento não poderei mais realizar alterações no meu cadastro").
- **Trilha de auditoria** e **controle de acesso por perfil** (item 6 dos requisitos e item
  6 do próprio pedido).

Adotamos o `.docx` como base, com os ajustes de precisão detalhados em
[`04-regras-de-negocio.md`](04-regras-de-negocio.md).

## 3. Regras críticas extraídas do edital (resumo)

Detalhamento completo e parametrizado em [`04-regras-de-negocio.md`](04-regras-de-negocio.md)
e em [`regras/parametros_edital.yaml`](../regras/parametros_edital.yaml). Em resumo:

- **Pontuação máxima: 190** — `P = CL + CC`, com `CL ≤ 160` e `CC ≤ 30` (item 8.4.1).
- **Critérios Legais (item 8.5):** 4 incisos, **40 pontos cada, cumuláveis**. Situações
  diferentes *dentro do mesmo inciso* **não** acumulam (item 8.5.2.1).
- **Complementar renda per capita (8.7):** faixas de 15/10/5/0, **exclusivas** (sem soma).
- **Complementar aluguel (8.8):** 8 faixas de 0 a 15, **exclusivas**, sobre a **média de 3
  meses**; imóvel cedido/emprestado = 0.
- **Enquadramento de renda:** entre **R$ 1.621,00 e R$ 8.105,00** (itens 3.1.4 e 6.1.4).
  Fora disso → eliminado.
- **Desempate (8.10):** (1) mais filhos/dependentes ≤ 12 anos; (2) mais idosos;
  (3) sorteio público.
- **Valores fixos:** ancorados na publicação (28/08/2026). Salário-mínimo de referência =
  **R$ 1.621,00**; teto do Critério Legal IV = **R$ 4.863,00** (3 SM), "fixo e irreajustável"
  (item 8.5.1). O sistema **não** deve reajustar automaticamente esses valores.

## 4. Riscos e armadilhas (atenção do desenvolvedor)

1. **Operadores de comparação nas bordas das faixas.** O edital é explícito em `≤`/`<`
   (ex.: aluguel "≥20% e ≤25%" = 1 ponto; ">25% e ≤30%" = 3 pontos). Um erro de borda
   muda pontuação. Todas as faixas estão parametrizadas com o operador correto e **devem
   ter teste unitário no valor exato da borda**.
2. **"Filhos ≤ 12" aparece em dois lugares com regras diferentes:**
   - *Critério Legal II* (40 pts) **exige comprovação de matrícula** na rede regular.
   - *Desempate I* usa apenas o número de filhos/dependentes ≤ 12 anos (sem matrícula).
   São contagens distintas — não confundir no código.
3. **Renda para enquadramento ≠ renda para per capita ≠ renda para Critério IV.** As três
   usam a "renda bruta computável" (com exclusões do 3.1.4.1), mas comparam contra limites
   diferentes. Modelar a renda computável uma única vez e derivar as três verificações.
4. **Divisor da renda per capita:** "número de integrantes considerados para fins de
   apuração da renda" (item 8.7.4). Definir com a Comissão se é o total de integrantes do
   núcleo (interpretação padrão) — ver decisão pendente D-2.
5. **Idade é dinâmica.** "0 a 12 anos", "≥ 60 anos" e "≥ 18 anos" dependem de uma **data de
   referência**. Fixar a data de referência (provável: data da inscrição ou data de
   publicação) — ver D-1. Guardar data de nascimento e **calcular**, nunca armazenar idade.
6. **Dupla pontuação pelo mesmo fato** é vedada (8.5.2.2 / 8.6.5). O motor trata os
   critérios de forma independente como o edital os enumera; a checagem de "mesmo fato" é
   ato da Comissão, apoiado por alertas do sistema, não bloqueio automático.
7. **Sorteio não é automatizável.** É ato público administrativo (8.10 III). O sistema
   **identifica** os empates remanescentes e **registra** a ata do sorteio; não sorteia.
8. **Imutabilidade após finalização.** Depois de finalizada a inscrição, edição só por
   procedimento administrativo autorizado e **sempre** registrada em auditoria (Anexo II).
9. **Uma inscrição por núcleo** (itens 2.2, 3.2, 3.3.4). Prevenir duplicidade por CPF de
   qualquer integrante, não só do requerente.
10. **Grupos prioritários (5% PcD / 5% idosos, item 5)** afetam a **contratação**, não a
    pontuação. Modelar como marcação/indicador para a fase de encaminhamento, sem alterar CL/CC.

## 5. Decisões pendentes (a validar com a Comissão de Inscrição)

| ID | Decisão | Impacto | Sugestão padrão |
|----|---------|---------|-----------------|
| D-1 | **Data de referência** para cálculo de idades (18/0-12/60) | Pontuação e requisitos | Data da inscrição de cada núcleo |
| D-2 | Divisor da renda per capita: todos os integrantes ou só provedores? | Pontuação complementar | Todos os integrantes do núcleo |
| D-3 | Arredondamento do percentual de comprometimento do aluguel | Faixa de pontuação do aluguel | 2 casas decimais, sem arredondar antes de comparar |
| D-4 | Rendas não computáveis afetam **também** o enquadramento mínimo (piso de R$ 1.621)? | Elegibilidade | Aplicar exclusões antes de qualquer verificação de renda |
| D-5 | O que fazer com inscrição cujo requisito não é atendido (item 6): indeferir na hora ou marcar "não apto" e exigir confirmação? | Fluxo | Marcar "não apto" + confirmação humana (nunca indeferir automático) |
| D-6 | Guarda e retenção dos documentos após o processo (prazo LGPD) | Conformidade | Definir tabela de temporalidade documental |

## 6. Conclusão do diagnóstico

O projeto é viável e bem delimitado. O maior risco **não** é técnico — é de **fidelidade ao
edital**. A estratégia de mitigação é: (a) transformar cada regra do edital em parâmetro
versionado; (b) isolar o motor de pontuação num módulo puro e cobri-lo com testes nas
bordas; (c) tornar todo ato do servidor auditável e o cadastro imutável após finalização.

A stack **Django + SQLite (dev) → PostgreSQL (prod)** atende bem: entrega autenticação,
perfis, admin, upload controlado, auditoria e relatórios com baixo esforço, e é simples de
manter por uma equipe pequena de TI municipal.

Próximo passo de desenvolvimento em [`06-roadmap.md`](06-roadmap.md).
