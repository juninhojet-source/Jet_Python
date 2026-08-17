@echo off
setlocal
rem ============================================================
rem  SIGTRANS Saude - Iniciar em PRODUCAO (Waitress)
rem  Sobe o sistema em 127.0.0.1:8000 (somente local).
rem  O acesso externo (dominio + HTTPS) e feito pelo proxy
rem  reverso (IIS/nginx). Ver docs\MANUAL_PUBLICACAO_DOMINIO_HTTPS.md
rem ============================================================
pushd "%~dp0..\.."

if not exist ".venv\Scripts\python.exe" (
  echo [ERRO] Ambiente nao encontrado. Rode primeiro: scripts\windows\instalar.bat
  popd & pause & exit /b 1
)

if not exist ".env" (
  echo [ERRO] Arquivo .env nao encontrado. Copie o .env.example para .env
  echo        e defina SECRET_KEY, DEBUG=False e ALLOWED_HOSTS.
  popd & pause & exit /b 1
)

echo [1/2] Coletando arquivos estaticos...
".venv\Scripts\python.exe" manage.py collectstatic --noinput
if errorlevel 1 ( echo [ERRO] Falha no collectstatic. & popd & pause & exit /b 1 )

echo [2/2] Iniciando o servidor de producao (Waitress) em 127.0.0.1:8000 ...
echo.
echo O sistema responde localmente em http://127.0.0.1:8000
echo O acesso pelo dominio/HTTPS e feito pelo proxy reverso.
echo Pressione Ctrl+C para parar.
echo.

".venv\Scripts\python.exe" -m waitress --listen=127.0.0.1:8000 config.wsgi:application

popd
