@echo off
setlocal
rem ============================================================
rem  SIGTRANS Saude - Iniciar (modo teste)
rem  Sobe o sistema acessivel na rede local para testes.
rem  NAO usar em producao (ver docs\MANUAL_INSTALACAO.md).
rem ============================================================
pushd "%~dp0..\.."

if not exist ".venv\Scripts\python.exe" (
  echo [ERRO] Ambiente nao encontrado. Rode primeiro: scripts\windows\instalar.bat
  popd & pause & exit /b 1
)

rem Libera acesso pela rede local durante os testes.
set "ALLOWED_HOSTS=*"

echo.
echo ==== SIGTRANS Saude (modo teste) ====
echo Acesse neste servidor:  http://localhost:8000
echo Acesse de outro PC:     http://IP-DO-SERVIDOR:8000
echo (descubra o IP com o comando: ipconfig)
echo.
echo Pressione Ctrl+C para parar o servidor.
echo.

".venv\Scripts\python.exe" manage.py runserver 0.0.0.0:8000

popd
