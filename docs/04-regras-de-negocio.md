# 04 — Regras de Negócio (Matriz do Edital)

Todas as regras do edital transformadas em regras do sistema. Os **valores** vivem em
[`regras/parametros_edital.yaml`](../regras/parametros_edital.yaml) (fonte única). Este
documento é a leitura humana dessa matriz, com a referência ao item do edital.

> ⚠️ **Bordas das faixas** seguem o edital literalmente (`≤`, `<`, `≥`, `>`). Cada borda deve
> ter **teste unitário no valor exato**.

## A. Pré-requisitos eliminatórios (itens 3.1 e 6.1)

| # | Requisito | Regra | Item |
|---|-----------|-------|------|
| R1 | Idade | Requerente ≥ 18 anos | 3.1.1 |
| R2 | Residência | ≥ 5 anos contínuos em Barão de Cocais | 3.1.2 / 6.1.3 |
| R3 | Nacionalidade | Brasileiro nato ou naturalizado | 3.1.3 |
| R4 | Renda mínima | Renda bruta familiar **≥ R$ 1.621,00** | 3.1.4 / 6.1.4 |
| R5 | Renda máxima | Renda bruta familiar **≤ R$ 8.105,00** | 3.1.4 / 6.1.4 |
| R6 | Propriedade | Não ser proprietário/promitente comprador de imóvel (qualquer lugar) | 3.1.5 / 6.1.1 |
| R7 | Benefício anterior | Nunca beneficiado por programa habitacional | 3.1.6 / 6.1.2 |
| R8 | Unicidade | Uma única inscrição por núcleo familiar | 2.2 / 3.2 / 3.3.4 |

Falha em qualquer um → **NÃO APTO** (sinalizado; indeferimento exige confirmação humana, D-5).
Rendas não computáveis (BPC, Bolsa Família, Seguro-Desemprego, benefícios temporários) são
**excluídas** antes de qualquer verificação de renda (item 3.1.4.1).

## B. Critérios Legais — `CL` (item 8.5) · 40 pts/inciso · cumuláveis · máx **160**

| Inciso | Condição para 40 pontos | Observações | Item |
|--------|-------------------------|-------------|------|
| **I** | Habitação precária/emergencial/risco **ou** inadequação estrutural de acessibilidade | Situações diferentes **no mesmo inciso não somam** → 40 (não 80/120) | 8.5 I, 8.5.2.1 |
| **II** | Existe criança 0–12 anos **E** matrícula comprovada na rede regular do município | **Duas** condições obrigatórias; sem matrícula = 0 | 8.5 II |
| **III** | Arrimo do núcleo é **mulher ou pessoa idosa** | Basta uma das duas | 8.5 III |
| **IV** | Renda bruta familiar mensal **≤ R$ 4.863,00** | Valor **fixo e irreajustável** (3 SM) | 8.5 IV, 8.5.1 |

`CL = 40 × (nº de incisos atendidos)`, limitado a 160.

## C. Critérios Complementares — `CC` (item 8.6) · máx **30**

### C.1 Renda per capita (item 8.7) — até 15 pts · faixa exclusiva

`per_capita = renda_bruta_computável ÷ nº integrantes considerados` (D-2)

| Faixa | Pontos | Item |
|-------|--------|------|
| `≤ R$ 810,50` | **15** | 8.7.1 I |
| `> 810,50` e `≤ 1.621,00` | **10** | 8.7.1 II |
| `> 1.621,00` e `≤ 2.431,50` | **5** | 8.7.1 III |
| `> 2.431,50` | **0** | 8.7.1 IV |

### C.2 Comprometimento com aluguel (item 8.8) — até 15 pts · faixa exclusiva

`percentual = (média_aluguel_3_meses ÷ renda_bruta_mensal_familiar) × 100`

Aluguel = **média dos 3 meses** anteriores à publicação (8.8.8); se variou, média aritmética
(8.8.5.2); imóvel **cedido/emprestado = 0** (8.8.6); dividido com externos → só o valor
suportado pelo núcleo, comprovado (8.8.7); só conta se houve pagamento nos 3 meses (8.8.5.1).

| Faixa (%) | Pontos | Item |
|-----------|--------|------|
| `< 20` | **0** | 8.8.2 I |
| `≥ 20` e `≤ 25` | **1** | 8.8.2 II |
| `> 25` e `≤ 30` | **3** | 8.8.2 III |
| `> 30` e `≤ 35` | **6** | 8.8.2 IV |
| `> 35` e `≤ 40` | **8** | 8.8.2 V |
| `> 40` e `≤ 45` | **10** | 8.8.2 VI |
| `> 45` e `≤ 50` | **13** | 8.8.2 VII |
| `> 50` | **15** | 8.8.2 VIII |

`CC = pontos_per_capita + pontos_aluguel`, limitado a 30.

## D. Pontuação total (item 8.4.1)

```
P = CL + CC        (CL ≤ 160, CC ≤ 30, P ≤ 190)
```
Vedada dupla pontuação pelo mesmo fato (8.5.2.2 / 8.6.5) — alerta ao operador, não bloqueio
automático.

## E. Classificação e desempate (itens 8.9 e 8.10)

1. **Pontuação total** decrescente.
2. Empate → **maior nº de filhos/dependentes ≤ 12 anos** (sem exigir matrícula — difere do CL II).
3. Ainda empatado → **maior nº de idosos** (≥ 60 anos).
4. Persistindo → **sorteio público** (ato administrativo; sistema marca e registra ata).

## F. Exemplo verificável (para teste de aceitação)

Núcleo com: habitação em risco (CL I ✓), crianças 0–12 com matrícula (CL II ✓), arrimo homem
não idoso (CL III ✗), renda R$ 3.000 ≤ 4.863 (CL IV ✓); 4 integrantes → per capita R$ 750,00
(≤ 810,50 → **15**); aluguel médio R$ 1.033,33 sobre renda R$ 3.000 → 34,44% (`>30 e ≤35` →
**6**).

```
CL = 40 + 40 + 0 + 40 = 120
CC = 15 + 6            = 21
P  = 120 + 21          = 141
```
