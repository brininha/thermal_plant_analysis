@echo off
TITLE Instalador Analise Termica
echo ==========================================
echo      INICIANDO ANALISE TERMICA
echo ==========================================
echo.
echo 1. Verificando Python...
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [ERRO] Python nao encontrado!
    echo Por favor, instale o Python no site python.org e marque a opcao "Add to PATH".
    pause
    exit
)

echo 2. Criando ambiente virtual (pode demorar na primeira vez)...
if not exist ".venv" (
    python -m venv .venv
    echo Ambiente criado.
)

echo 3. Instalando bibliotecas necessarias...
call .venv\Scripts\activate
pip install -r requirements.txt >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [AVISO] Tentando instalar dependencias novamente...
    pip install streamlit pandas plotly pillow opencv-python-headless numpy matplotlib
)

echo.
echo ==========================================
echo      TUDO PRONTO! ABRINDO O SISTEMA...
echo ==========================================
echo.

REM Configura o caminho do ExifTool para a pasta atual
set EXIFTOOL_PATH=%CD%\exiftool.exe

REM Roda o Streamlit
streamlit run app_completo.py --server.headless true

pause