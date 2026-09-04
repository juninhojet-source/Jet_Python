@echo off
REM Remove o servico do Windows do Sistema MCMV (criado por instalar-servico.bat).
REM Uso (Prompt de Comando COMO ADMINISTRADOR):
REM   cd C:\mcmv\Jet_Python
REM   scripts\windows\remover-servico.bat
setlocal
cd /d "%~dp0..\.."
set "PROJ=%CD%"
set "SERVICO=MCMV"

net session >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Rode este script COMO ADMINISTRADOR.
    exit /b 1
)

set "NSSM="
if exist "%PROJ%\nssm.exe" set "NSSM=%PROJ%\nssm.exe"
if not defined NSSM if exist "C:\mcmv\nssm.exe" set "NSSM=C:\mcmv\nssm.exe"
if not defined NSSM (
    for %%I in (nssm.exe) do if exist "%%~$PATH:I" set "NSSM=%%~$PATH:I"
)

echo Parando o servico %SERVICO%...
net stop %SERVICO% >nul 2>&1

if defined NSSM (
    "%NSSM%" remove %SERVICO% confirm
) else (
    echo nssm.exe nao encontrado; removendo via sc...
    sc delete %SERVICO%
)
echo Servico %SERVICO% removido.
endlocal
