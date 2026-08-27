# 10 — Backup e Restauração

Backup **automático diário** do Sistema MCMV (banco + documentos) com retenção
e **restauração** simples em caso de falha. Cobre o cenário padrão em **SQLite**;
há nota para PostgreSQL ao final.

## O que é copiado

Cada backup é um único arquivo `mcmv-backup-AAAAMMDD-HHMMSS.zip` contendo:
- `db.sqlite3` — cópia **consistente** do banco (via API de backup do SQLite;
  **não precisa parar o serviço**);
- `media/` — os documentos anexados (`MEDIA_ROOT`);
- `manifesto.json` — data, tamanho e metadados do backup.

## Configuração (`.env`)

```
MCMV_BACKUP_DIR=C:\mcmv\backups          REM pasta local dos backups
MCMV_BACKUP_RETENCAO_DIAS=30             REM remove backups mais antigos que N dias
MCMV_BACKUP_COPIA=\\SERVIDOR\compart\mcmv  REM (opcional) copia p/ outro servidor
```

Com `MCMV_BACKUP_COPIA` preenchido, cada backup é gerado localmente **e** copiado
para o outro local (a retenção também é aplicada na cópia).

> ⚠️ **Unidade mapeada (M:) x tarefa agendada:** a tarefa de backup roda como
> **SYSTEM**, e o SYSTEM **não enxerga** unidades mapeadas por usuário (ex.: `M:`).
> Por isso, em `MCMV_BACKUP_COPIA` use o **caminho UNC** do compartilhamento
> (ex.: `\\SERVIDOR\compartilhamento\mcmv`), não `M:\mcmv`. Descubra o UNC do `M:`
> com `net use` no Prompt. Se o outro servidor exigir login, ou rode a tarefa com
> uma conta de usuário que tenha acesso, ou garanta permissão de escrita ao
> computador do servidor no compartilhamento.

> Recomendado: `MCMV_BACKUP_DIR` num **segundo disco** do próprio servidor e
> `MCMV_BACKUP_COPIA` na **pasta de rede de outro servidor** — assim há cópia
> local (rápida) e remota (fora da máquina).

## Backup manual

```bat
cd C:\mcmv\Jet_Python
scripts\windows\backup.bat
REM ou: .venv\Scripts\activate.bat  &&  python manage.py backup
```

Opções: `python manage.py backup --destino D:\seguro\mcmv --reter 60`.

## Agendar o backup diário (Agendador de Tarefas)

Como **Administrador**, cria a tarefa "MCMV Backup Diario" (padrão 23:00):

```bat
cd C:\mcmv\Jet_Python
scripts\windows\agendar-backup.bat            REM 23:00
scripts\windows\agendar-backup.bat 02:30      REM outro horario
```

O script cria a tarefa (usuário SYSTEM), executa um teste imediato e mostra onde
os backups são gravados. Para remover: `schtasks /Delete /F /TN "MCMV Backup Diario"`.

## Restauração (em caso de falha)

⚠️ A restauração **sobrescreve** o banco e os documentos atuais. Antes de
sobrescrever, o banco atual é salvo como `db.sqlite3.pre-restauracao`.

```bat
cd C:\mcmv\Jet_Python
REM Restaura o backup MAIS RECENTE (para o servico, restaura e reinicia):
scripts\windows\restaurar.bat

REM ou um backup especifico:
scripts\windows\restaurar.bat C:\mcmv\backups\mcmv-backup-20260827-230000.zip
```

Por baixo, o `restaurar.bat` faz `net stop MCMV`, roda
`python manage.py restaurar_backup --ultimo --confirmar` (ou `--arquivo <zip>`)
e `net start MCMV`.

Para conferir sem aplicar (mostra o que faria, sem sobrescrever):
```bat
.venv\Scripts\activate.bat
python manage.py restaurar_backup --ultimo        REM sem --confirmar: apenas avisa
```

## Teste de restauração (recomendado)

Periodicamente, valide que os backups restauram:
1. Gere um backup (`backup.bat`).
2. Numa cópia/ambiente de teste, rode `restaurar_backup --arquivo <zip> --confirmar`.
3. Confira se o sistema abre e os dados estão presentes.

## PostgreSQL (quando aplicável)

Se migrar para PostgreSQL, use as ferramentas nativas:
- Backup: `pg_dump -Fc -f mcmv.dump <banco>` (agende no Agendador de Tarefas) +
  cópia da pasta `MEDIA_ROOT`.
- Restauração: `pg_restore -d <banco> --clean mcmv.dump` + restaurar a mídia.

O comando `manage.py backup`/`restaurar_backup` recusa-se a rodar fora do SQLite
para evitar backup incompleto.
