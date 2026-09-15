@echo off
rem ============================================================
rem  SIGTRANS Saude - Configurar o IIS (proxy reverso + HTTPS)
rem  Pede elevacao de administrador e roda o script PowerShell.
rem  Requisitos: URL Rewrite 2.1 e ARR 3.0 instalados no IIS.
rem  Detalhes: docs\MANUAL_PUBLICACAO_DOMINIO_HTTPS.md (secao 5)
rem ============================================================

rem Verifica se ja esta como administrador; se nao, reabre elevado.
net session >nul 2>&1
if %errorlevel% neq 0 (
  echo Solicitando permissao de administrador...
  powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
  exit /b
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0configurar-iis.ps1"
echo.
pause
