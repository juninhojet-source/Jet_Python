@echo off
REM Inicia o Sistema MCMV com Waitress (servidor WSGI para Windows).
REM As configuracoes vem do arquivo .env na raiz do projeto.
setlocal
cd /d "%~dp0..\.."
call .venv\Scripts\activate.bat
REM Garante que os estaticos (CSS/JS) estejam coletados e atualizados. Sem isso,
REM um arquivo novo referenciado nos templates derruba a pagina (erro 500) em
REM producao (DEBUG=0). E rapido e idempotente, entao roda sempre no start.
python manage.py collectstatic --noinput
python run_waitress.py
