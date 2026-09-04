@echo off
REM Inicia o Sistema MCMV com Waitress (servidor WSGI para Windows).
REM As configuracoes vem do arquivo .env na raiz do projeto.
REM O run_waitress.py aplica migracoes e coleta estaticos antes de servir.
setlocal
cd /d "%~dp0..\.."
call .venv\Scripts\activate.bat
python run_waitress.py
