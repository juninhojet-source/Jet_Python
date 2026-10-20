@echo off
REM Instalacao do Sistema MCMV em Windows Server (2012 R2 Standard).
REM Execute como Administrador, a partir de qualquer lugar (usa caminho do script).
setlocal
cd /d "%~dp0..\.."

echo === Verificando .env ===
if not exist ".env" (
  echo ATENCAO: arquivo .env nao encontrado.
  echo Copie .env.windows.example para .env e ajuste antes de continuar.
  pause
  exit /b 1
)

echo === Criando ambiente virtual (.venv) ===
if not exist ".venv" (
  py -3.12 -m venv .venv || python -m venv .venv
)
call .venv\Scripts\activate.bat

echo === Instalando dependencias ===
python -m pip install --upgrade pip
pip install -r requirements-windows.txt || exit /b 1

echo === Aplicando migracoes do banco ===
python manage.py migrate || exit /b 1

echo === Coletando arquivos estaticos ===
python manage.py collectstatic --noinput || exit /b 1

echo.
echo === Criando usuario administrador ===
python manage.py createsuperuser

echo.
echo Instalacao concluida. Use iniciar.bat para subir o servidor,
echo ou instale como servico com NSSM (ver docs\08-implantacao-windows.md).
pause
