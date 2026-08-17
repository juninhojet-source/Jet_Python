@echo off
rem ============================================================
rem  SIGTRANS Saude - Criar certificado interno (HTTPS)
rem  Lancador do script PowerShell (evita bloqueio de execucao).
rem  Gera a CA da Prefeitura e o certificado do site em C:\certs.
rem  Detalhes: docs\MANUAL_PUBLICACAO_DOMINIO_HTTPS.md
rem ============================================================
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0criar-certificado.ps1" %*
echo.
pause
