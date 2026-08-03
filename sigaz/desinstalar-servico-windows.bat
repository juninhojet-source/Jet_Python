@echo off
chcp 65001 > nul
title SIGAZ - Desinstalador de Servico
echo.
echo ==========================================
echo   SIGAZ - Desinstalar Servico Windows
echo ==========================================
echo.

net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERRO] Execute como Administrador.
    pause
    exit /b 1
)

cd /d "%~dp0"
node servico-windows.js desinstalar

echo.
pause
