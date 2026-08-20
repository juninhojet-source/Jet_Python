@echo off
rem ============================================================
rem  SIGTRANS Saude - Gerar arquivo .env de PRODUCAO
rem  Cria o .env com SECRET_KEY aleatoria, DEBUG=False, o dominio
rem  e cookies seguros. Mantem SQLite (nao apaga os dados atuais).
rem  Passe "quiet" como argumento para nao pausar (uso interno).
rem ============================================================
pushd "%~dp0..\.."

if not exist ".venv\Scripts\python.exe" (
  echo [ERRO] Ambiente nao encontrado. Rode primeiro: scripts\windows\instalar.bat
  popd & if /i not "%~1"=="quiet" pause
  exit /b 1
)

".venv\Scripts\python.exe" "%~dp0gerar_env.py"
set "ERR=%ERRORLEVEL%"

popd
if /i not "%~1"=="quiet" pause
exit /b %ERR%
