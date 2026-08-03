-- ============================================================
-- SIGAZ - Sistema Integrado de Gestão Animal e Zoonoses
-- Schema do Banco de Dados
-- Prefeitura Municipal de Barão de Cocais
-- ============================================================

PRAGMA foreign_keys = ON;

-- ------------------------------------------------------------
-- USUÁRIOS DO SISTEMA
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS usuarios (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nome        TEXT    NOT NULL,
    username    TEXT    UNIQUE,
    email       TEXT    NOT NULL UNIQUE,
    senha_hash  TEXT    NOT NULL,
    perfil      TEXT    NOT NULL CHECK (perfil IN ('admin','veterinario','auxiliar','endemias','secretaria','ti','cidadao')),
    ativo       INTEGER NOT NULL DEFAULT 1,
    cpf         TEXT,
    telefone    TEXT,
    deve_trocar_senha INTEGER NOT NULL DEFAULT 0,
    tentativas_falhas INTEGER NOT NULL DEFAULT 0,
    bloqueado_ate DATETIME,
    ultimo_login DATETIME,
    criado_em   DATETIME DEFAULT CURRENT_TIMESTAMP,
    atualizado_em DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------------------------
-- RESPONSÁVEIS (Tutores)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS responsaveis (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nome        TEXT    NOT NULL,
    cpf         TEXT    NOT NULL UNIQUE,
    rg          TEXT,
    telefone    TEXT,
    email       TEXT,
    endereco    TEXT,
    numero      TEXT,
    bairro      TEXT,
    cidade      TEXT DEFAULT 'Barão de Cocais',
    uf          TEXT DEFAULT 'MG',
    cep         TEXT,
    observacoes TEXT,
    criado_em   DATETIME DEFAULT CURRENT_TIMESTAMP,
    atualizado_em DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_responsaveis_cpf ON responsaveis(cpf);
CREATE INDEX IF NOT EXISTS idx_responsaveis_bairro ON responsaveis(bairro);

-- ------------------------------------------------------------
-- ANIMAIS
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS animais (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo              TEXT    NOT NULL UNIQUE,
    nome                TEXT    NOT NULL,
    especie             TEXT    NOT NULL CHECK (especie IN ('Canino','Felino','Equídeo','Bovídeo','Suídeo','Ave','Outro')),
    raca                TEXT,
    sexo                TEXT    CHECK (sexo IN ('Macho','Fêmea','Indeterminado')),
    data_nascimento     DATE,
    idade_aproximada    TEXT,
    pelagem             TEXT,
    porte               TEXT CHECK (porte IN ('Pequeno','Médio','Grande','Gigante')),
    peso_kg             REAL,
    status_reprodutivo  TEXT CHECK (status_reprodutivo IN ('Inteiro(a)','Castrado(a)','Rufião','Criptorquida')),
    habitacao           TEXT CHECK (habitacao IN ('Domiciliado','Semidomiciliado','Comunitário','Errante')),
    microchip           TEXT,
    numero_identificacao TEXT,
    foto                TEXT,
    qrcode              TEXT,
    responsavel_id      INTEGER,
    observacoes         TEXT,
    ativo               INTEGER NOT NULL DEFAULT 1,
    criado_em           DATETIME DEFAULT CURRENT_TIMESTAMP,
    atualizado_em       DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (responsavel_id) REFERENCES responsaveis(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_animais_codigo ON animais(codigo);
CREATE INDEX IF NOT EXISTS idx_animais_responsavel ON animais(responsavel_id);
CREATE INDEX IF NOT EXISTS idx_animais_especie ON animais(especie);

-- ------------------------------------------------------------
-- VACINAÇÃO
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS vacinas (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    animal_id           INTEGER NOT NULL,
    vacina              TEXT    NOT NULL,
    fabricante          TEXT,
    lote                TEXT,
    data_aplicacao      DATE    NOT NULL,
    data_validade       DATE,
    proxima_aplicacao   DATE,
    responsavel_aplicacao TEXT,
    crmv                TEXT,
    observacoes         TEXT,
    usuario_id          INTEGER,
    criado_em           DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (animal_id) REFERENCES animais(id) ON DELETE CASCADE,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_vacinas_animal ON vacinas(animal_id);
CREATE INDEX IF NOT EXISTS idx_vacinas_proxima ON vacinas(proxima_aplicacao);

-- ------------------------------------------------------------
-- VERMIFUGAÇÃO
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS vermifugacoes (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    animal_id           INTEGER NOT NULL,
    produto             TEXT    NOT NULL,
    lote                TEXT,
    data_aplicacao      DATE    NOT NULL,
    data_validade       DATE,
    proxima_aplicacao   DATE,
    responsavel         TEXT,
    observacoes         TEXT,
    usuario_id          INTEGER,
    criado_em           DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (animal_id) REFERENCES animais(id) ON DELETE CASCADE,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_vermifugacoes_animal ON vermifugacoes(animal_id);

-- ------------------------------------------------------------
-- ECTOPARASITÁRIOS
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ectoparasitarios (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    animal_id           INTEGER NOT NULL,
    produto             TEXT    NOT NULL,
    lote                TEXT,
    data_aplicacao      DATE    NOT NULL,
    data_validade       DATE,
    proxima_aplicacao   DATE,
    responsavel         TEXT,
    observacoes         TEXT,
    usuario_id          INTEGER,
    criado_em           DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (animal_id) REFERENCES animais(id) ON DELETE CASCADE,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_ecto_animal ON ectoparasitarios(animal_id);

-- ------------------------------------------------------------
-- ZOONOSES
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS zoonoses (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    animal_id           INTEGER NOT NULL,
    zoonose             TEXT    NOT NULL,
    data_notificacao    DATE    NOT NULL,
    status_investigacao TEXT CHECK (status_investigacao IN ('À investigar','Em análise','Investigação concluída')),
    diagnostico         TEXT CHECK (diagnostico IN ('Positivo','Negativo','Inconclusivo','Aguardando')),
    prognostico         TEXT,
    obito               INTEGER DEFAULT 0,
    data_obito          DATE,
    metodo_diagnostico  TEXT,
    bairro_ocorrencia   TEXT,
    observacoes         TEXT,
    usuario_id          INTEGER,
    criado_em           DATETIME DEFAULT CURRENT_TIMESTAMP,
    atualizado_em       DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (animal_id) REFERENCES animais(id) ON DELETE CASCADE,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_zoonoses_animal ON zoonoses(animal_id);
CREATE INDEX IF NOT EXISTS idx_zoonoses_zoonose ON zoonoses(zoonose);
CREATE INDEX IF NOT EXISTS idx_zoonoses_bairro ON zoonoses(bairro_ocorrencia);

-- ------------------------------------------------------------
-- DOCUMENTOS ANEXADOS
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS documentos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    animal_id       INTEGER NOT NULL,
    tipo            TEXT,
    descricao       TEXT,
    arquivo         TEXT    NOT NULL,
    mime_type       TEXT,
    tamanho_bytes   INTEGER,
    usuario_id      INTEGER,
    criado_em       DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (animal_id) REFERENCES animais(id) ON DELETE CASCADE,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL
);

-- ------------------------------------------------------------
-- LOGS / AUDITORIA
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id  INTEGER,
    acao        TEXT NOT NULL,
    entidade    TEXT,
    entidade_id INTEGER,
    detalhes    TEXT,
    ip          TEXT,
    criado_em   DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_logs_usuario ON logs(usuario_id);
CREATE INDEX IF NOT EXISTS idx_logs_data ON logs(criado_em);

-- ------------------------------------------------------------
-- TERMOS GERADOS
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS termos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    animal_id   INTEGER NOT NULL,
    tipo        TEXT NOT NULL,
    conteudo    TEXT,
    usuario_id  INTEGER,
    criado_em   DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (animal_id) REFERENCES animais(id) ON DELETE CASCADE,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL
);

-- ------------------------------------------------------------
-- AGENDAMENTOS (castrações, vacinas em campo, visitas)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS agendamentos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo            TEXT NOT NULL CHECK (tipo IN ('Castração','Vacinação','Visita Técnica','Consulta','Outro')),
    animal_id       INTEGER,
    responsavel_id  INTEGER,
    data_agendada   DATETIME NOT NULL,
    duracao_min     INTEGER DEFAULT 30,
    local           TEXT,
    observacoes     TEXT,
    status          TEXT DEFAULT 'Agendado' CHECK (status IN ('Agendado','Confirmado','Realizado','Cancelado','Não Compareceu')),
    realizado_em    DATETIME,
    usuario_id      INTEGER,
    criado_em       DATETIME DEFAULT CURRENT_TIMESTAMP,
    atualizado_em   DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (animal_id) REFERENCES animais(id) ON DELETE SET NULL,
    FOREIGN KEY (responsavel_id) REFERENCES responsaveis(id) ON DELETE SET NULL,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_agendamentos_data ON agendamentos(data_agendada);
CREATE INDEX IF NOT EXISTS idx_agendamentos_status ON agendamentos(status);

-- ------------------------------------------------------------
-- CAMPANHAS E MUTIRÕES
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS campanhas (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    nome            TEXT NOT NULL,
    tipo            TEXT,
    descricao       TEXT,
    data_inicio     DATE,
    data_fim        DATE,
    local           TEXT,
    bairro          TEXT,
    meta_atendimentos INTEGER DEFAULT 0,
    status          TEXT DEFAULT 'Planejada' CHECK (status IN ('Planejada','Em Andamento','Concluída','Cancelada')),
    usuario_id      INTEGER,
    criado_em       DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS campanha_atendimentos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    campanha_id     INTEGER NOT NULL,
    animal_id       INTEGER NOT NULL,
    procedimento    TEXT,
    observacoes     TEXT,
    criado_em       DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (campanha_id) REFERENCES campanhas(id) ON DELETE CASCADE,
    FOREIGN KEY (animal_id) REFERENCES animais(id) ON DELETE CASCADE
);

-- ------------------------------------------------------------
-- DENÚNCIAS DE MAUS-TRATOS
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS denuncias (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    protocolo       TEXT NOT NULL UNIQUE,
    tipo            TEXT,
    descricao       TEXT NOT NULL,
    endereco        TEXT,
    bairro          TEXT,
    referencia      TEXT,
    denunciante_nome TEXT,
    denunciante_telefone TEXT,
    anonimo         INTEGER DEFAULT 0,
    status          TEXT DEFAULT 'Recebida' CHECK (status IN ('Recebida','Em Apuração','Atendida','Improcedente','Encaminhada')),
    desfecho        TEXT,
    fiscal_id       INTEGER,
    data_atendimento DATE,
    criado_em       DATETIME DEFAULT CURRENT_TIMESTAMP,
    atualizado_em   DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (fiscal_id) REFERENCES usuarios(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_denuncias_status ON denuncias(status);
CREATE INDEX IF NOT EXISTS idx_denuncias_bairro ON denuncias(bairro);

-- ------------------------------------------------------------
-- ESTOQUE DE INSUMOS
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS estoque_itens (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    nome            TEXT NOT NULL,
    categoria       TEXT,
    unidade         TEXT DEFAULT 'unidade',
    estoque_minimo  INTEGER DEFAULT 0,
    observacoes     TEXT,
    ativo           INTEGER DEFAULT 1,
    criado_em       DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS estoque_movimentos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id         INTEGER NOT NULL,
    tipo            TEXT NOT NULL CHECK (tipo IN ('Entrada','Saída','Ajuste','Vencimento')),
    quantidade      INTEGER NOT NULL,
    lote            TEXT,
    data_validade   DATE,
    motivo          TEXT,
    animal_id       INTEGER,
    usuario_id      INTEGER,
    criado_em       DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (item_id) REFERENCES estoque_itens(id) ON DELETE CASCADE,
    FOREIGN KEY (animal_id) REFERENCES animais(id) ON DELETE SET NULL,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_estoque_validade ON estoque_movimentos(data_validade);

-- ------------------------------------------------------------
-- CONFIGURAÇÕES DO SISTEMA (chave-valor)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS configuracoes (
    chave           TEXT PRIMARY KEY,
    valor           TEXT,
    descricao       TEXT,
    atualizado_em   DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------------------------
-- BAIRROS OFICIAIS DO MUNICÍPIO
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS bairros (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nome        TEXT NOT NULL UNIQUE,
    eh_distrito INTEGER DEFAULT 0,
    ativo       INTEGER DEFAULT 1,
    ordem       INTEGER DEFAULT 0,
    latitude    REAL,
    longitude   REAL,
    geocoded_em DATETIME,
    criado_em   DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_bairros_ativo ON bairros(ativo);
CREATE INDEX IF NOT EXISTS idx_bairros_nome ON bairros(nome);

-- ------------------------------------------------------------
-- SOLICITAÇÕES DO CIDADÃO (Portal)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS solicitacoes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    protocolo       TEXT UNIQUE,
    tipo            TEXT NOT NULL CHECK (tipo IN ('Castração','Vacinação','Atendimento','Outro')),
    cidadao_id      INTEGER,
    animal_id       INTEGER,
    descricao       TEXT,
    status          TEXT DEFAULT 'Solicitada' CHECK (status IN ('Solicitada','Aprovada','Agendada','Atendida','Negada','Cancelada')),
    resposta        TEXT,
    agendamento_id  INTEGER,
    criado_em       DATETIME DEFAULT CURRENT_TIMESTAMP,
    atualizado_em   DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cidadao_id) REFERENCES usuarios(id) ON DELETE SET NULL,
    FOREIGN KEY (animal_id) REFERENCES animais(id) ON DELETE SET NULL,
    FOREIGN KEY (agendamento_id) REFERENCES agendamentos(id) ON DELETE SET NULL
);

-- ------------------------------------------------------------
-- FICHA SINAN — ATENDIMENTO ANTIRRÁBICO HUMANO (mordedura)
-- Notificação compulsória conforme Portaria GM/MS nº 264/2020
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mordeduras (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    protocolo               TEXT NOT NULL UNIQUE,
    data_notificacao        DATE NOT NULL,
    data_ocorrencia         DATE,

    -- Vítima humana
    vitima_nome             TEXT NOT NULL,
    vitima_cpf              TEXT,
    vitima_data_nascimento  DATE,
    vitima_sexo             TEXT CHECK (vitima_sexo IN ('M','F','I')),
    vitima_telefone         TEXT,
    vitima_endereco         TEXT,
    vitima_bairro           TEXT,
    vitima_cidade           TEXT,
    vitima_uf               TEXT,
    vitima_cep              TEXT,

    -- Características do acidente
    local_anatomico         TEXT,           -- mão, perna, face, etc.
    tipo_ferimento          TEXT,           -- único/múltiplo, profundo/superficial
    descricao_acidente      TEXT,
    local_ocorrencia        TEXT,           -- via pública, residência, etc.
    bairro_ocorrencia       TEXT,

    -- Animal agressor
    animal_id               INTEGER,        -- se o animal está cadastrado no SIGAZ
    animal_especie          TEXT,           -- Canino/Felino/etc.
    animal_conhecido        INTEGER DEFAULT 0,  -- 1=conhecido, 0=desconhecido
    animal_vacinado         TEXT CHECK (animal_vacinado IN ('Sim','Não','Desconhecido')),
    animal_proprietario_nome    TEXT,
    animal_proprietario_telefone TEXT,
    animal_proprietario_endereco TEXT,

    -- Conduta médica
    tipo_exposicao          TEXT CHECK (tipo_exposicao IN ('Leve','Grave','Sem indicação')),
    conduta                 TEXT,           -- Soro+Vacina / Vacina / Reexposição / etc.
    profilaxia_iniciada     INTEGER DEFAULT 0,
    unidade_atendimento     TEXT,

    -- Observação dos 10 dias
    observacao_iniciada     INTEGER DEFAULT 0,
    observacao_status       TEXT CHECK (observacao_status IN ('Em curso','Concluída','Animal Sumiu','Animal Sacrificado','Animal Morreu','Não Aplicável')),
    observacao_inicio       DATE,
    observacao_fim_previsto DATE,
    observacao_resultado    TEXT,            -- "Sadio ao final" / "Morreu" / etc.

    status_caso             TEXT DEFAULT 'Aberto' CHECK (status_caso IN ('Aberto','Em Acompanhamento','Encerrado','Cancelado')),
    encerramento_data       DATE,
    encerramento_observacao TEXT,

    usuario_id              INTEGER,
    criado_em               DATETIME DEFAULT CURRENT_TIMESTAMP,
    atualizado_em           DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (animal_id) REFERENCES animais(id) ON DELETE SET NULL,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_mordeduras_protocolo ON mordeduras(protocolo);
CREATE INDEX IF NOT EXISTS idx_mordeduras_status ON mordeduras(status_caso);
CREATE INDEX IF NOT EXISTS idx_mordeduras_obs_fim ON mordeduras(observacao_fim_previsto);

-- Eventos da observação dos 10 dias (visitas, ligações)
CREATE TABLE IF NOT EXISTS mordedura_observacoes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    mordedura_id    INTEGER NOT NULL,
    data            DATE NOT NULL,
    dia_observacao  INTEGER,                -- 1, 5, 10
    situacao_animal TEXT,                   -- Sadio, Doente, Sumiu, Morreu
    observacoes     TEXT,
    usuario_id      INTEGER,
    criado_em       DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (mordedura_id) REFERENCES mordeduras(id) ON DELETE CASCADE,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL
);

-- ------------------------------------------------------------
-- PRONTUÁRIO VETERINÁRIO (consultas clínicas)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS prontuario (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    animal_id           INTEGER NOT NULL,
    data_consulta       DATE NOT NULL,
    tipo                TEXT,            -- Consulta, Retorno, Emergência, Pré-cirúrgico, Pós-cirúrgico
    motivo              TEXT,            -- Queixa do tutor / motivo da consulta
    anamnese            TEXT,            -- Histórico clínico

    -- Sinais vitais
    peso_kg             REAL,
    temperatura         REAL,
    frequencia_cardiaca INTEGER,
    frequencia_respiratoria INTEGER,
    escore_corporal     INTEGER,         -- 1 a 9

    exame_fisico        TEXT,
    diagnostico         TEXT,
    cid                 TEXT,            -- CID-10 quando aplicável
    conduta             TEXT,            -- Plano terapêutico

    medicamentos        TEXT,            -- texto livre (prescrição)
    exames_solicitados  TEXT,

    retorno_data        DATE,
    retorno_motivo      TEXT,

    veterinario_id      INTEGER,         -- usuário (perfil veterinario)
    veterinario_crmv    TEXT,

    criado_em           DATETIME DEFAULT CURRENT_TIMESTAMP,
    atualizado_em       DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (animal_id) REFERENCES animais(id) ON DELETE CASCADE,
    FOREIGN KEY (veterinario_id) REFERENCES usuarios(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_prontuario_animal ON prontuario(animal_id);
CREATE INDEX IF NOT EXISTS idx_prontuario_data ON prontuario(data_consulta);
