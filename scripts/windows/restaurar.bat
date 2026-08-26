@echo off
REM ============================================================================
REM  Restaura um backup do Sistema MCMV (banco + documentos).
REM  Para o servico, restaura e reinicia. SOBRESCREVE os dados atuais
REM  (o banco atual e salvo como db.sqlite3.pre-restauracao antes).
REM
REM  Uso (Prompt de Comando COMO ADMINISTRADOR):
REM    cd C:\mcmv\Jet_Python
REM    scripts\windows\restaurar.bat                         (restaura o MAIS RECENTE)
REM    scripts\windows\restaurar.bat C:\mcmv\backups\mcmv-backup-20260827-230000.zip
REM ============================================================================
setlocal
cd /d "%~dp0..\.."
call .venv\Scripts\activate.bat

set "ARQ=%~1"

echo Parando o servico MCMV...
net stop MCMV >nul 2>&1

if "%ARQ%"=="" (
    echo Restaurando o backup MAIS RECENTE...
    python manage.py restaurar_backup --ultimo --confirmar
) else (
    echo Restaurando: %ARQ%
    python manage.py restaurar_backup --arquivo "%ARQ%" --confirmar
)
set "RC=%ERRORLEVEL%"

echo Iniciando o servico MCMV...
net start MCMV >nul 2>&1

if not "%RC%"=="0" (
    echo [ERRO] A restauracao falhou (codigo %RC%). Verifique a mensagem acima.
    exit /b %RC%
)
echo.
echo Restauracao concluida e servico reiniciado.
endlocal
