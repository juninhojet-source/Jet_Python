@echo off
rem ============================================================
rem  SIGTRANS Saude - Instalacao nos COMPUTADORES que acessam
rem  1) Instala o certificado da Prefeitura (Autoridade Raiz
rem     Confiavel) -> navegador abre o HTTPS sem aviso.
rem  2) Habilita o Firefox a confiar no certificado do Windows.
rem  3) Cria um atalho do sistema na area de trabalho.
rem
rem  Como usar: coloque este .bat na MESMA pasta que o arquivo
rem  "prefeitura-ca.crt" (copie do servidor: C:\certs) e execute.
rem  (Ele pede permissao de administrador automaticamente.)
rem ============================================================

rem --- Configuracao ---
set "URL=https://sigtrans.baraodecocais.mg.gov.br"
set "CERT=%~dp0prefeitura-ca.crt"
if not "%~1"=="" set "CERT=%~1"
rem --------------------

rem Eleva para administrador se necessario
net session >nul 2>&1
if %errorlevel% neq 0 (
  echo Solicitando permissao de administrador...
  powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -ArgumentList '\"%CERT%\"' -Verb RunAs"
  exit /b
)

echo.
echo ==== SIGTRANS Saude - Instalacao no computador cliente ====
echo.

if not exist "%CERT%" (
  echo [ERRO] Arquivo do certificado nao encontrado:
  echo        %CERT%
  echo Copie o "prefeitura-ca.crt" do servidor ^(C:\certs^) para esta pasta
  echo e rode de novo.
  echo.
  pause
  exit /b 1
)

echo [1/3] Instalando o certificado da Prefeitura ^(Autoridade Raiz Confiavel^)...
certutil -addstore -f Root "%CERT%"
if errorlevel 1 (
  echo [ERRO] Falha ao instalar o certificado.
  pause
  exit /b 1
)

echo.
echo [2/3] Habilitando o Firefox a confiar no certificado do Windows...
reg add "HKLM\SOFTWARE\Policies\Mozilla\Firefox\Certificates" /v ImportEnterpriseRoots /t REG_DWORD /d 1 /f >nul 2>&1

echo.
echo [3/3] Criando atalho do sistema na area de trabalho...
set "ATALHO=%PUBLIC%\Desktop\SIGTRANS Saude.url"
(
  echo [InternetShortcut]
  echo URL=%URL%
) > "%ATALHO%"

echo.
echo ==========================================================
echo  [OK] Concluido!
echo  - O navegador ^(Chrome/Edge^) abre %URL%
echo    com cadeado, sem aviso de seguranca.
echo  - Se o Firefox ja estiver aberto, feche e abra de novo.
echo  - Um atalho "SIGTRANS Saude" foi criado na area de trabalho.
echo ==========================================================
echo.
pause
