@echo off
setlocal EnableDelayedExpansion
rem ============================================================
rem  SIGTRANS Saude - Atualizar (um clique)
rem  Baixa novidades do repositorio e, SE houver mudanca:
rem  instala dependencias, aplica migracoes, coleta estaticos
rem  e reinicia o servidor. Se nada mudou, nao faz nada.
rem  Pede permissao de administrador automaticamente.
rem ============================================================

net session >nul 2>&1
if %errorlevel% neq 0 (
  echo Solicitando permissao de administrador...
  powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
  exit /b
)

pushd "%~dp0..\.."
if not exist ".venv\Scripts\python.exe" (
  echo [ERRO] Ambiente .venv nao encontrado. Rode scripts\windows\instalar.bat
  popd & pause & exit /b 1
)

echo === Atualizando o SIGTRANS Saude ===
echo.

for /f "delims=" %%h in ('git rev-parse HEAD 2^>nul') do set "ANTES=%%h"

echo Baixando novidades do repositorio...
git pull
if errorlevel 1 (
  echo [ERRO] Falha no git pull ^(verifique a conexao/credencial^).
  popd & pause & exit /b 1
)

for /f "delims=" %%h in ('git rev-parse HEAD 2^>nul') do set "DEPOIS=%%h"

if "!ANTES!"=="!DEPOIS!" (
  echo.
  echo Nenhuma novidade - o sistema ja esta atualizado. Nada a fazer.
  popd & pause & exit /b 0
)

echo.
echo Novidades baixadas. Aplicando...
echo [1/4] Dependencias...
".venv\Scripts\python.exe" -m pip install -q -r requirements.txt
echo [2/4] Banco de dados ^(migracoes^)...
".venv\Scripts\python.exe" manage.py migrate
echo [3/4] Arquivos estaticos...
".venv\Scripts\python.exe" manage.py collectstatic --noinput >nul

echo [4/4] Reiniciando o servidor...
taskkill /F /IM python.exe >nul 2>&1
timeout /t 3 /nobreak >nul
schtasks /Run /TN "SIGTRANS Servidor" >nul 2>&1

echo.
echo ==========================================================
echo  [OK] Atualizacao concluida!
echo  Aguarde ~15 segundos e acesse o sistema.
echo  No navegador, use Ctrl+F5 para pegar o visual novo.
echo ==========================================================
echo.
popd
pause
