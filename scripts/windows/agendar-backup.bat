@echo off
REM ============================================================================
REM  Agenda o BACKUP DIARIO do Sistema MCMV no Agendador de Tarefas do Windows.
REM  Cria a tarefa "MCMV Backup Diario" rodando todo dia as 23:00 (SYSTEM).
REM
REM  Uso (Prompt de Comando COMO ADMINISTRADOR):
REM    cd C:\mcmv\Jet_Python
REM    scripts\windows\agendar-backup.bat            (padrao 23:00)
REM    scripts\windows\agendar-backup.bat 02:30      (outro horario)
REM ============================================================================
setlocal
cd /d "%~dp0..\.."
set "PROJ=%CD%"
set "HORA=%~1"
if "%HORA%"=="" set "HORA=23:00"

net session >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Execute COMO ADMINISTRADOR.
    exit /b 1
)

echo Criando a tarefa "MCMV Backup Diario" para as %HORA% ...
schtasks /Create /F /TN "MCMV Backup Diario" /SC DAILY /ST %HORA% /RL HIGHEST /RU SYSTEM ^
    /TR "\"%PROJ%\scripts\windows\backup.bat\""
if errorlevel 1 (
    echo [ERRO] Nao foi possivel criar a tarefa.
    exit /b 1
)

echo.
echo Tarefa criada. Testando uma execucao agora...
schtasks /Run /TN "MCMV Backup Diario"
echo.
echo Pronto. Veja os backups em MCMV_BACKUP_DIR (padrao: %PROJ%\backups).
echo Para remover a tarefa:  schtasks /Delete /F /TN "MCMV Backup Diario"
endlocal
