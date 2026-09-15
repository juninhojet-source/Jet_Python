@echo off
rem ============================================================
rem  SIGTRANS Saude - runner do servico (uso interno)
rem  Sobe o Waitress em 127.0.0.1:8000 SEM interacao (sem pause),
rem  gravando log. Chamado pela tarefa de inicializacao do Windows
rem  (ver instalar-servico.bat). Nao rode direto: use o
rem  iniciar-producao.bat para testes manuais.
rem ============================================================
setlocal
pushd "%~dp0..\.."

if not exist "%CD%\backups" mkdir "%CD%\backups"
set "LOG=%CD%\backups\servico.log"

echo(>> "%LOG%"
echo ==== %date% %time% - iniciando SIGTRANS >> "%LOG%"

if not exist ".venv\Scripts\python.exe" (
  echo [ERRO] Ambiente .venv nao encontrado. >> "%LOG%"
  popd & exit /b 1
)

if not exist ".env" (
  call "%~dp0configurar-env.bat" quiet >> "%LOG%" 2>&1
)

".venv\Scripts\python.exe" manage.py collectstatic --noinput >> "%LOG%" 2>&1

echo Servidor no ar em 127.0.0.1:8000 >> "%LOG%"
".venv\Scripts\python.exe" -m waitress --listen=127.0.0.1:8000 config.wsgi:application >> "%LOG%" 2>&1

popd
