@echo off
setlocal EnableDelayedExpansion
rem ============================================================
rem  SIGTRANS Saude - Backup automatico (diario)
rem  1) Gera o backup (.json.gz) localmente em .\backups
rem  2) Copia para o compartilhamento de rede (outro servidor)
rem  3) Remove backups antigos (local e na rede)
rem  Agende no Agendador de Tarefas do Windows (ver README).
rem ============================================================

rem --- Configuracao (ajuste se precisar) ---
set "DEST=\\172.16.64.2\ti\Sigtrans"
set "DIAS_LOCAL=30"
set "DIAS_REDE=90"
rem -----------------------------------------

pushd "%~dp0..\.."
set "LOCAL=%CD%\backups"
set "LOG=%LOCAL%\backup-automatico.log"

if not exist ".venv\Scripts\python.exe" (
  echo [ERRO] Ambiente nao encontrado. Rode scripts\windows\instalar.bat
  popd & exit /b 1
)
if not exist "%LOCAL%" mkdir "%LOCAL%"

echo(>> "%LOG%"
echo ==== %date% %time% ==== >> "%LOG%"

rem 1) Gera o backup local
".venv\Scripts\python.exe" manage.py backup --dir "%LOCAL%" >> "%LOG%" 2>&1
if errorlevel 1 (
  echo [ERRO] Falha ao gerar o backup. >> "%LOG%"
  popd & exit /b 1
)

rem Descobre o arquivo mais recente
set "NEWEST="
for /f "delims=" %%f in ('dir /b /o-d "%LOCAL%\sigtrans_*.json.gz" 2^>nul') do (
  set "NEWEST=%%f"
  goto :achou
)
:achou
if "!NEWEST!"=="" (
  echo [ERRO] Nenhum arquivo de backup encontrado. >> "%LOG%"
  popd & exit /b 1
)

rem 2) Copia para o compartilhamento de rede (robocopy e robusto p/ rede)
robocopy "%LOCAL%" "%DEST%" "!NEWEST!" /R:3 /W:5 >> "%LOG%" 2>&1
if !errorlevel! GEQ 8 (
  echo [ERRO] Falha ao copiar para %DEST% ^(verifique a rede/permissao^). >> "%LOG%"
  popd & exit /b 1
)
echo [OK] Backup !NEWEST! enviado para %DEST% >> "%LOG%"

rem 3) Limpeza dos antigos
forfiles /p "%LOCAL%" /m sigtrans_*.json.gz /d -%DIAS_LOCAL% /c "cmd /c del @path" >nul 2>&1
forfiles /p "%DEST%" /m sigtrans_*.json.gz /d -%DIAS_REDE% /c "cmd /c del @path" >nul 2>&1

popd
endlocal
exit /b 0
