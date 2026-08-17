@echo off
setlocal EnableDelayedExpansion
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

if exist ".env" (
  echo O arquivo .env ja existe - nada foi alterado.
  echo Para refazer do zero, apague o .env e rode este script de novo.
  popd & if /i not "%~1"=="quiet" pause
  exit /b 0
)

echo Gerando SECRET_KEY...
set "SECRETKEY="
for /f "delims=" %%i in ('".venv\Scripts\python.exe" -c "import secrets;print(secrets.token_urlsafe(64))"') do set "SECRETKEY=%%i"
if "!SECRETKEY!"=="" (
  echo [ERRO] Falha ao gerar a chave secreta.
  popd & if /i not "%~1"=="quiet" pause
  exit /b 1
)

(
  echo # SIGTRANS Saude - configuracao de PRODUCAO ^(gerada automaticamente^)
  echo # NAO compartilhe este arquivo: a SECRET_KEY e sensivel.
  echo SECRET_KEY=!SECRETKEY!
  echo DEBUG=False
  echo ALLOWED_HOSTS=sigtrans.baraodecocais.mg.gov.br,172.16.64.8,localhost,127.0.0.1
  echo CSRF_TRUSTED_ORIGINS=https://sigtrans.baraodecocais.mg.gov.br
  echo SESSION_COOKIE_SECURE=True
  echo CSRF_COOKIE_SECURE=True
  echo ATRAS_DE_PROXY=True
) > .env

echo.
echo [OK] Arquivo .env de producao criado.
echo      Banco de dados: SQLite ^(mantem os dados atuais^).
echo      Para usar PostgreSQL, edite o .env conforme .env.example.
echo.
popd
if /i not "%~1"=="quiet" pause
endlocal
exit /b 0
