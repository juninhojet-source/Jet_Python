@echo off
REM ============================================================================
REM  Instala o Sistema MCMV como SERVICO do Windows usando o NSSM.
REM  O servico sobe sozinho com o servidor e reinicia em caso de falha.
REM
REM  Pre-requisitos:
REM    - Ja ter rodado scripts\windows\instalar.bat (cria o .venv) e o .env.
REM    - nssm.exe disponivel (baixe em https://nssm.cc/download e copie para
REM      a pasta do projeto, para C:\mcmv\ ou deixe no PATH).
REM
REM  Uso (Prompt de Comando COMO ADMINISTRADOR):
REM    cd C:\mcmv\Jet_Python
REM    scripts\windows\instalar-servico.bat
REM
REM  Parar/iniciar depois:  net stop MCMV  /  net start MCMV
REM  Remover o servico:     scripts\windows\remover-servico.bat
REM ============================================================================
setlocal enabledelayedexpansion
cd /d "%~dp0..\.."
set "PROJ=%CD%"
set "SERVICO=MCMV"
set "PYEXE=%PROJ%\.venv\Scripts\python.exe"
set "APPSCRIPT=%PROJ%\run_waitress.py"

REM --- Verifica administrador ---
net session >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Rode este script COMO ADMINISTRADOR ^(botao direito ^> Executar como administrador^).
    exit /b 1
)

REM --- Verifica o virtualenv ---
if not exist "%PYEXE%" (
    echo [ERRO] Nao encontrei o Python do venv em: %PYEXE%
    echo         Rode antes: scripts\windows\instalar.bat
    exit /b 1
)

REM --- Localiza o nssm.exe ---
set "NSSM="
if exist "%PROJ%\nssm.exe" set "NSSM=%PROJ%\nssm.exe"
if not defined NSSM if exist "C:\mcmv\nssm.exe" set "NSSM=C:\mcmv\nssm.exe"
if not defined NSSM (
    for %%I in (nssm.exe) do if exist "%%~$PATH:I" set "NSSM=%%~$PATH:I"
)
if not defined NSSM (
    echo [ERRO] nssm.exe nao encontrado.
    echo         Baixe em https://nssm.cc/download, extraia o win64\nssm.exe e
    echo         copie para "%PROJ%" ou para C:\mcmv\ e rode novamente.
    exit /b 1
)
echo Usando NSSM: %NSSM%

REM --- Pasta de logs ---
set "LOGDIR=C:\mcmv\logs"
if not exist "%LOGDIR%" mkdir "%LOGDIR%" 2>nul

REM --- Se o servico ja existir, para e remove antes de recriar ---
sc query %SERVICO% >nul 2>&1
if not errorlevel 1 (
    echo Servico %SERVICO% ja existe. Parando e removendo para recriar...
    net stop %SERVICO% >nul 2>&1
    "%NSSM%" remove %SERVICO% confirm >nul 2>&1
)

echo Instalando o servico %SERVICO%...
"%NSSM%" install %SERVICO% "%PYEXE%" "%APPSCRIPT%"
"%NSSM%" set %SERVICO% AppDirectory "%PROJ%"
"%NSSM%" set %SERVICO% DisplayName "Sistema MCMV - Cadastro Habitacional"
"%NSSM%" set %SERVICO% Description "Cadastro Habitacional MCMV (Edital 001/2026) - Waitress/Django"
"%NSSM%" set %SERVICO% Start SERVICE_AUTO_START
"%NSSM%" set %SERVICO% AppStdout "%LOGDIR%\servico.log"
"%NSSM%" set %SERVICO% AppStderr "%LOGDIR%\servico.log"
"%NSSM%" set %SERVICO% AppRotateFiles 1
"%NSSM%" set %SERVICO% AppRotateBytes 5242880

echo Iniciando o servico...
net start %SERVICO%
if errorlevel 1 (
    echo [ERRO] O servico nao iniciou. Veja o log: %LOGDIR%\servico.log
    exit /b 1
)

echo.
echo ============================================================
echo  Servico %SERVICO% instalado e em execucao.
echo  Ele subira sozinho a cada boot do servidor.
echo  Log: %LOGDIR%\servico.log
echo  Parar/iniciar:  net stop %SERVICO%  /  net start %SERVICO%
echo ============================================================
endlocal
