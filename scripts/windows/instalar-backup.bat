@echo off
rem ============================================================
rem  SIGTRANS Saude - Agendar o backup diario
rem  Cria a tarefa do Windows que roda o backup-automatico.bat
rem  todo dia. A conta informada precisa ter acesso de escrita
rem  na pasta de rede (\\172.16.64.2\ti\Sigtrans).
rem  Pede permissao de administrador automaticamente.
rem ============================================================

net session >nul 2>&1
if %errorlevel% neq 0 (
  echo Solicitando permissao de administrador...
  powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
  exit /b
)

set "HORA=20:00"
set "RUNNER=%~dp0backup-automatico.bat"

echo.
echo ==== SIGTRANS Saude - Agendar backup diario ====
echo.
echo Horario padrao: %HORA%  (para mudar, edite este arquivo)
echo.
echo Informe a conta que vai rodar o backup. Ela PRECISA ter
echo acesso a pasta de rede \\172.16.64.2\ti\Sigtrans.
echo Exemplos: %COMPUTERNAME%\Administrator  ou  DOMINIO\usuario
echo.
set "CONTA="
set /p CONTA=Conta [%USERDOMAIN%\%USERNAME%]:
if "%CONTA%"=="" set "CONTA=%USERDOMAIN%\%USERNAME%"

echo.
echo Criando a tarefa "SIGTRANS Backup Diario" para %CONTA% as %HORA%...
schtasks /Create /TN "SIGTRANS Backup Diario" /SC DAILY /ST %HORA% /TR "\"%RUNNER%\"" /RU "%CONTA%" /RP * /RL HIGHEST /F
if errorlevel 1 (
  echo [ERRO] Nao foi possivel criar a tarefa. Verifique a conta/senha.
  pause & exit /b 1
)

echo.
echo Rodando um backup de teste agora...
schtasks /Run /TN "SIGTRANS Backup Diario" >nul 2>&1

echo.
echo ==========================================================
echo  [OK] Backup diario agendado para %HORA%.
echo  - Confira em uns instantes se apareceu um arquivo em
echo    \\172.16.64.2\ti\Sigtrans e no log backups\backup-automatico.log
echo  - Ver a tarefa: schtasks /Query /TN "SIGTRANS Backup Diario" /V /FO LIST
echo ==========================================================
echo.
pause
