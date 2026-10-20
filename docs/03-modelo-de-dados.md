# 03 — Modelo de Dados

Modelo relacional inicial. Nomes em `snake_case`. Alvo: SQLite (dev) → PostgreSQL (prod).
Idades **nunca** são armazenadas — calcula-se a partir de `data_nascimento` na data de referência.

## Diagrama ER

```mermaid
erDiagram
    usuario ||--o{ auditoria : registra
    usuario ||--o{ inscricao : cria
    inscricao ||--|| pessoa : requerente
    inscricao ||--o{ membro_nucleo : possui
    pessoa ||--o{ membro_nucleo : e
    membro_nucleo ||--o{ renda : tem
    inscricao ||--o{ documento : anexa
    pessoa ||--o{ documento : refere
    inscricao ||--o{ criterio_legal : avalia
    inscricao ||--|| criterio_complementar : calcula
    inscricao ||--o| classificacao : gera
    inscricao ||--o{ auditoria : alvo

    usuario {
        int id PK
        string nome
        string login
        string senha_hash
        string perfil
        bool ativo
    }
    inscricao {
        int id PK
        string numero_inscricao UK
        datetime data_inscricao
        int requerente_id FK
        string status
        decimal renda_bruta_computavel
        decimal aluguel_medio
        bool aluguel_cedido
        decimal renda_per_capita
        decimal percentual_aluguel
        int pontos_legais
        int pontos_complementares
        int pontuacao_total
        datetime data_finalizacao
        bool bloqueada
    }
    pessoa {
        int id PK
        string nome
        string cpf UK
        date data_nascimento
        string sexo
        string estado_civil
        bool pcd
        bool brasileiro
    }
    membro_nucleo {
        int id PK
        int inscricao_id FK
        int pessoa_id FK
        string parentesco
        bool dependente
        bool arrimo
        bool considerado_apuracao_renda
    }
    renda {
        int id PK
        int membro_id FK
        string tipo
        decimal valor
        bool computavel
        string competencia
    }
    documento {
        int id PK
        int inscricao_id FK
        int pessoa_id FK
        string tipo
        bool obrigatorio
        string arquivo_ref
        string status
        string observacao
        int conferido_por_id FK
        datetime data_conferencia
    }
    criterio_legal {
        int id PK
        int inscricao_id FK
        string inciso
        bool atendido
        bool comprovado
        int pontos
        int documento_comprova_id FK
    }
    criterio_complementar {
        int id PK
        int inscricao_id FK
        decimal renda_per_capita
        int pontos_renda
        decimal aluguel_medio
        decimal percentual
        int pontos_aluguel
    }
    classificacao {
        int id PK
        int inscricao_id FK
        int posicao
        int pontuacao
        int dependentes_ate_12
        int idosos
        bool empate_pendente_sorteio
        string sorteio_ata_ref
    }
    auditoria {
        int id PK
        int usuario_id FK
        datetime data_hora
        string ip
        string operacao
        string tabela
        string registro_id
        string campo
        string valor_anterior
        string valor_novo
        string justificativa
    }
```

## Notas de modelagem

- **`pessoa` é única por CPF** e reutilizável — permite detectar a mesma pessoa em núcleos
  diferentes (regra "uma inscrição por núcleo", itens 3.2/3.3.4). A checagem de duplicidade
  varre o CPF de **todos** os integrantes, não só o requerente.
- **`membro_nucleo`** liga `pessoa` a `inscricao` com o papel (`parentesco`) e as flags usadas
  na pontuação/desempate. `considerado_apuracao_renda` implementa a decisão D-2 (divisor da
  per capita).
- **`renda.computavel`** materializa as exclusões do item 3.1.4.1; a renda de enquadramento e
  a per capita somam apenas `computavel = true`.
- **`criterio_legal.documento_comprova_id`** e **`documento` por critério** dão a
  rastreabilidade exigida ("por que este candidato recebeu 170 pontos e qual documento
  comprova cada ponto").
- **Campos derivados na `inscricao`** (renda per capita, percentual, pontos) são **calculados
  pelo motor** e persistidos como *snapshot* no momento da finalização — mas sempre
  recomputáveis a partir dos dados-fonte e dos parâmetros.
- **`arquivo_ref`** guarda apenas a **referência**; o binário fica fora da raiz web
  (ver [05-seguranca-lgpd](05-seguranca-lgpd.md)).
- **`auditoria`** é *append-only*: sem update/delete; toda alteração pós-finalização passa por
  aqui com `justificativa`.
- **Grupos prioritários** (5% PcD / 5% idosos) derivam de `pessoa.pcd` e das idades — não
  precisam de tabela própria; entram como indicador na fase de encaminhamento.
