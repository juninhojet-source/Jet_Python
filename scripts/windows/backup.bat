@echo off
REM Backup do Sistema MCMV (banco + documentos). Roda com o serviço no ar.
REM Usado pelo Agendador de Tarefas (ver agendar-backup.bat) ou manualmente.
setlocal
cd /d "%~dp0..\.."
call .venv\Scripts\activate.bat
python manage.py backup
