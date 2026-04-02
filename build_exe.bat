@echo off
REM build_exe.bat — Compila setup_mt5_vps.exe per la VPS Windows
REM Installa automaticamente Python e PyInstaller se mancanti

echo.
echo ============================================
echo  mt5-remote-reader-mcp -- Build VPS Installer
echo ============================================
echo.

REM -----------------------------------------------
REM STEP 1: Controlla se Python e' disponibile
REM -----------------------------------------------
echo [1/4] Verifica Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo  Python non trovato nel PATH.
    echo  Avvio download Python 3.11.9 da python.org...
    echo.
    powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Write-Host '  Download in corso...'; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe' -OutFile '%TEMP%\python_installer.exe'; Write-Host '  Download completato.'"
    if errorlevel 1 (
        echo.
        echo  ERRORE: impossibile scaricare Python. Controlla la connessione internet.
        pause
        exit /b 1
    )
    echo.
    echo  Installazione Python in corso (potrebbe richiedere 1-2 minuti)...
    "%TEMP%\python_installer.exe" /quiet InstallAllUsers=1 PrependPath=1 Include_pip=1 Include_launcher=1
    if errorlevel 1 (
        echo.
        echo  ERRORE: installazione Python fallita.
        echo  Installa Python manualmente da https://www.python.org/downloads/
        pause
        exit /b 1
    )
    echo  Python installato con successo.
    echo  Aggiornamento PATH dalla registry di Windows...
    REM Aggiorna PATH nella sessione corrente senza riavviare
    for /f "usebackq tokens=*" %%i in (`powershell -Command "[System.Environment]::GetEnvironmentVariable('PATH','Machine')"`) do set "SYSPATH=%%i"
    for /f "usebackq tokens=*" %%i in (`powershell -Command "[System.Environment]::GetEnvironmentVariable('PATH','User')"`) do set "USERPATH=%%i"
    set "PATH=%SYSPATH%;%USERPATH%"
    echo  PATH aggiornato.
    echo.
    python --version >nul 2>&1
    if errorlevel 1 (
        echo  ATTENZIONE: Python ancora non trovato nel PATH aggiornato.
        echo  Provo con il launcher py.exe...
        py --version >nul 2>&1
        if errorlevel 1 (
            echo  ERRORE: Python non raggiungibile. Riavvia il terminale e riesegui questo script.
            pause
            exit /b 1
        )
        echo  Launcher py.exe trovato. Uso py al posto di python.
        set PYTHON_CMD=py
    ) else (
        set PYTHON_CMD=python
    )
) else (
    for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo  Trovato: %%v
    set PYTHON_CMD=python
)

REM -----------------------------------------------
REM STEP 2: Controlla/installa pip
REM -----------------------------------------------
echo.
echo [2/4] Verifica pip...
%PYTHON_CMD% -m pip --version >nul 2>&1
if errorlevel 1 (
    echo  pip non trovato. Installazione in corso...
    %PYTHON_CMD% -m ensurepip --upgrade
    if errorlevel 1 (
        echo  ERRORE: impossibile installare pip.
        pause
        exit /b 1
    )
    echo  pip installato.
) else (
    for /f "tokens=*" %%v in ('%PYTHON_CMD% -m pip --version 2^>^&1') do echo  Trovato: %%v
)

REM -----------------------------------------------
REM STEP 3: Installa PyInstaller
REM -----------------------------------------------
echo.
echo [3/4] Installazione PyInstaller...
%PYTHON_CMD% -m pip install pyinstaller --quiet --disable-pip-version-check
if errorlevel 1 (
    echo  ERRORE: impossibile installare PyInstaller.
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('%PYTHON_CMD% -m PyInstaller --version 2^>^&1') do echo  PyInstaller versione: %%v

REM -----------------------------------------------
REM STEP 4: Build exe
REM -----------------------------------------------
echo.
echo [4/4] Compilazione exe...

REM Legge la versione da pyproject.toml automaticamente
for /f "delims=" %%v in ('powershell -Command "(Select-String -Path pyproject.toml -Pattern '^version = ').Line.Split(chr(34))[1]"') do set VERSION=%%v
if "%VERSION%"=="" (
    echo  ERRORE: versione non trovata in pyproject.toml
    pause
    exit /b 1
)
echo  Versione rilevata: %VERSION%

if exist assets\mt5_icon.ico (
    set "ICON_FLAG=--icon assets\mt5_icon.ico"
    echo  Icona trovata: assets\mt5_icon.ico
) else (
    set "ICON_FLAG="
    echo  Nessuna icona in assets\mt5_icon.ico - build senza icona personalizzata
)

echo  Avvio PyInstaller...
echo.

%PYTHON_CMD% -m PyInstaller --onefile --uac-admin --console ^
  --add-data "src\mt5_remote_reader_mcp\mt5_tool.py;." ^
  --name setup_mt5_vps_%VERSION% ^
  %ICON_FLAG% ^
  src\mt5_remote_reader_mcp\setup_vps_installer.py

echo.
if exist dist\setup_mt5_vps_%VERSION%.exe (
    echo ============================================
    echo  BUILD COMPLETATA con successo!
    echo  Output: dist\setup_mt5_vps_%VERSION%.exe
    echo ============================================
) else (
    echo ============================================
    echo  ERRORE: build fallita.
    echo  Controlla i messaggi di errore sopra.
    echo ============================================
)

echo.
pause
