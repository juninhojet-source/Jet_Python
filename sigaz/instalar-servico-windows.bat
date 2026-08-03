@echo off
chcp 65001 > nul
title SIGAZ - Instalador de Servico Windows
echo.
echo ==========================================
echo   SIGAZ - Instalador de Servico Windows
echo   Prefeitura Municipal de Barao de Cocais
echo ==========================================
echo.

REM Verifica se esta rodando como Administrador
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERRO] Este script precisa ser executado como Administrador.
    echo.
    echo Como fazer:
    echo   1. Clique com o botao direito neste arquivo
    echo   2. Selecione "Executar como administrador"
    echo.
    pause
    exit /b 1
)

REM Verifica se o Node esta instalado
where node >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERRO] Node.js nao encontrado. Instale a partir de https://nodejs.org
    pause
    exit /b 1
)

cd /d "%~dp0"

echo Instalando dependencias (se necessario)...
if not exist "node_modules" (
    call npm install
)

echo.
echo Instalando node-windows (modulo do servico)...
call npm install node-windows --no-save

echo.
echo Instalando o SIGAZ como servico do Windows...
node servico-windows.js instalar

echo.
echo ==========================================
echo   Concluido!
echo ==========================================
echo.
echo Acesse o sistema em: http://localhost:3000
echo.
echo O SIGAZ agora subira automaticamente quando o Windows ligar.
echo Para gerenciar o servico, abra "services.msc" e procure por "SIGAZ".
echo.
pause
