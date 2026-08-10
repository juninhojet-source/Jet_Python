@echo off
setlocal enabledelayedexpansion
rem ============================================================
rem  SIGTRANS Saude - Instalacao automatica (Windows)
rem  Cria o ambiente, instala dependencias, prepara o banco
rem  e cria o usuario administrador.
rem ============================================================
pushd "%~dp0..\.."
echo.
echo ==== SIGTRANS Saude - Instalacao ====
echo Pasta do projeto: %CD%
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo [ERRO] Python nao foi encontrado.
  echo Instale o Python 3.12 em https://www.python.org/downloads/
  echo e marque "Add python.exe to PATH" durante a instalacao.
  popd & pause & exit /b 1
)

echo [1/5] Criando ambiente virtual (.venv)...
python -m venv .venv
if errorlevel 1 ( echo [ERRO] Falha ao criar o ambiente virtual. & popd & pause & exit /b 1 )

echo [2/5] Instalando dependencias...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo [AVISO] Falha ao instalar todos os pacotes ^(comum em Python muito novo^).
  echo Instalando o conjunto minimo para testes com SQLite...
  ".venv\Scripts\python.exe" -m pip install Django djangorestframework django-simple-history python-dotenv whitenoise waitress reportlab openpyxl
  if errorlevel 1 ( echo [ERRO] Falha ao instalar as dependencias. & popd & pause & exit /b 1 )
)

echo [3/5] Preparando o banco de dados...
".venv\Scripts\python.exe" manage.py migrate
if errorlevel 1 ( echo [ERRO] Falha ao aplicar as migracoes. & popd & pause & exit /b 1 )

echo [4/5] Cadastrando municipios...
".venv\Scripts\python.exe" manage.py seed_municipios

echo [5/5] Criando o usuario administrador...
set "ADMINUSER="
set /p ADMINUSER=Nome de usuario do administrador [admin]:
if "%ADMINUSER%"=="" set "ADMINUSER=admin"
".venv\Scripts\python.exe" manage.py criar_admin --username %ADMINUSER% --nome "Administrador"

echo.
echo ==== Instalacao concluida! ====
echo Para iniciar o sistema, execute: scripts\windows\iniciar.bat
echo.
popd
pause
