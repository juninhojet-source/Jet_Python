@echo off
rem ============================================================
rem  SIGTRANS Saude - Iniciar sozinho quando a VM ligar
rem  Cria uma tarefa do Windows que sobe o sistema no boot
rem  (roda como SYSTEM, sem precisar abrir o iniciar-producao).
rem  Pede permissao de administrador automaticamente.
rem ============================================================

net session >nul 2>&1
if %errorlevel% neq 0 (
  echo Solicitando permissao de administrador...
  powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
  exit /b
)

set "VBS=%~dp0iniciar-servico-oculto.vbs"

echo Criando a tarefa de inicializacao "SIGTRANS Servidor"...
schtasks /Create /TN "SIGTRANS Servidor" /SC ONSTART /RL HIGHEST /RU SYSTEM /TR "wscript.exe \"%VBS%\"" /F
if errorlevel 1 (
  echo [ERRO] Nao foi possivel criar a tarefa.
  pause & exit /b 1
)

echo.
echo Iniciando o sistema agora ^(sem precisar reiniciar^)...
schtasks /Run /TN "SIGTRANS Servidor" >nul 2>&1

echo.
echo ==========================================================
echo  [OK] Pronto! O SIGTRANS vai subir sozinho toda vez que a
echo  VM/servidor for ligado ou reiniciado.
echo.
echo  - Testar agora: aguarde uns 20s e acesse o sistema.
echo  - Ver log: backups\servico.log
echo  - Remover a inicializacao automatica:
echo      schtasks /Delete /TN "SIGTRANS Servidor" /F
echo ==========================================================
echo.
pause
