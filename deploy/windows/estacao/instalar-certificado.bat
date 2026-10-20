@echo off
REM ============================================================================
REM  Instala o certificado do Sistema MCMV como "Raiz Confiavel" NA ESTACAO,
REM  para o Chrome/Edge pararem de mostrar "Nao seguro" ao acessar o sistema.
REM
REM  COMO USAR (em cada estacao que vai acessar o sistema):
REM    1) Crie a pasta C:\mcmv na estacao.
REM    2) Copie para C:\mcmv estes dois arquivos:
REM         - mcmv-cert.cer   (gerado no servidor: C:\mcmv\mcmv-cert.cer)
REM         - instalar-certificado.bat  (este arquivo)
REM    3) Clique com o botao direito em instalar-certificado.bat
REM         -> "Executar como administrador".
REM
REM  Observacao: instala no repositorio da MAQUINA (todos os usuarios do PC).
REM ============================================================================
setlocal

REM Procura o .cer ao lado deste script; se nao achar, tenta C:\mcmv.
set "CERT=%~dp0mcmv-cert.cer"
if not exist "%CERT%" set "CERT=C:\mcmv\mcmv-cert.cer"

REM --- exige privilegios de administrador ---
net session >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Execute COMO ADMINISTRADOR ^(botao direito ^> Executar como administrador^).
    echo.
    pause
    exit /b 1
)

if not exist "%CERT%" (
    echo [ERRO] Certificado nao encontrado.
    echo         Copie o "mcmv-cert.cer" para C:\mcmv ^(ou para a pasta deste script^).
    echo.
    pause
    exit /b 1
)

echo Instalando o certificado como Raiz Confiavel...
echo   Arquivo: %CERT%
certutil -addstore -f Root "%CERT%"
if errorlevel 1 (
    echo [ERRO] Falha ao instalar o certificado.
    echo.
    pause
    exit /b 1
)

echo.
echo Verificando...
certutil -store Root | findstr /i "baraodecocais" >nul
if errorlevel 1 (
    echo   [AVISO] Nao encontrei o certificado no repositorio Raiz. Verifique manualmente.
) else (
    echo   [ OK ] Certificado presente no repositorio "Autoridades de Certificacao Raiz Confiaveis".
)

echo.
echo Fechando navegadores para eles relerem os certificados...
taskkill /F /IM chrome.exe  >nul 2>&1
taskkill /F /IM msedge.exe  >nul 2>&1

echo.
echo ============================================================
echo  Certificado instalado nesta estacao.
echo  Abra o navegador e acesse:
echo    https://172.16.64.9
echo    ^(ou https://mcmv.baraodecocais.mg.gov.br apos o DNS^)
echo  O cadeado deve aparecer, sem o aviso "Nao seguro".
echo ============================================================
echo.
pause
endlocal
