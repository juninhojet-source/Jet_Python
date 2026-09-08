# Manual de Backup e Restauração — SIGTRANS Saúde

Os dados dos pacientes são patrimônio exclusivo da Prefeitura e devem ser protegidos
contra perda (LGPD). Este manual descreve a rotina de backup e restauração.

## 1. Backup lógico pelo sistema (portável)

Gera um arquivo comprimido com todos os dados do sistema:

```bash
python manage.py backup            # grava em ./backups/
python manage.py backup --dir D:\backups\sigtrans
```

O arquivo tem o nome `sigtrans_AAAAMMDD_HHMMSS.json.gz` e a operação é registrada
na trilha de auditoria. Este backup é independente do banco (serve para SQLite e
PostgreSQL) e é útil para exportação/migração.

## 2. Backup físico do PostgreSQL (recomendado em produção)

Complementarmente, a equipe de TI deve manter o backup nativo do PostgreSQL:

```bash
pg_dump -U sigtrans -F c -f sigtrans_AAAAMMDD.dump sigtrans
```

Restauração:

```bash
pg_restore -U sigtrans -d sigtrans --clean sigtrans_AAAAMMDD.dump
```

## 3. Restauração pelo sistema

```bash
python manage.py restore backups/sigtrans_AAAAMMDD_HHMMSS.json.gz
```

> A restauração sobrescreve os dados atuais. Execute em ambiente controlado e com um
> backup recente disponível. Use `--sim` para confirmar sem interação.

## 4. Política recomendada

- **Backup completo diário** (fora do horário de atendimento).
- **Retenção** conforme política da TI (ex.: 30 dias) e cópia fora do servidor.
- **Teste de restauração** periódico, para garantir a integridade dos backups.
- Agende via **Agendador de Tarefas do Windows** (ou `cron` no Linux) executando o
  comando de backup no ambiente virtual do sistema.
