@echo off
REM build_exe.bat — Compila MT5RemoteReader_Setup_X.X.X.exe
REM Esegui da qualsiasi posizione: si sposta automaticamente alla root del repo

cd /d "%~dp0.."

echo.
echo ============================================
echo  MT5 Remote Reader -- Build Installer
echo ============================================
echo.

REM -----------------------------------------------
REM STEP 1: Python
REM -----------------------------------------------
echo [1/5] Verifica Python...
python --version >nul 2>&1
if not errorlevel 1 goto PYTHON_OK

echo  Python non trovato. Download in corso...
powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe' -OutFile '%TEMP%\python_installer.exe'"
"%TEMP%\python_installer.exe" /quiet InstallAllUsers=1 PrependPath=1 Include_pip=1 Include_launcher=1
if errorlevel 1 ( echo  ERRORE installazione Python. & pause & exit /b 1 )

set "PYTHON_CMD="
if exist "C:\Program Files\Python311\python.exe" set "PYTHON_CMD=C:\Program Files\Python311\python.exe"
if exist "C:\Python311\python.exe"               set "PYTHON_CMD=C:\Python311\python.exe"
if "%PYTHON_CMD%"=="" ( echo  Python non trovato nel PATH. Riapri il terminale. & pause & exit /b 1 )
goto STEP2

:PYTHON_OK
for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo  Trovato: %%v
set "PYTHON_CMD=python"

REM -----------------------------------------------
REM STEP 2: pip
REM -----------------------------------------------
:STEP2
echo.
echo [2/5] Verifica pip...
"%PYTHON_CMD%" -m pip --version >nul 2>&1
if errorlevel 1 "%PYTHON_CMD%" -m ensurepip --upgrade
for /f "tokens=*" %%v in ('"%PYTHON_CMD%" -m pip --version 2^>^&1') do echo  Trovato: %%v

REM -----------------------------------------------
REM STEP 3: PyInstaller
REM -----------------------------------------------
echo.
echo [3/5] PyInstaller...
"%PYTHON_CMD%" -m pip install pyinstaller --quiet --disable-pip-version-check
for /f "tokens=*" %%v in ('"%PYTHON_CMD%" -m PyInstaller --version 2^>^&1') do echo  Versione: %%v

REM -----------------------------------------------
REM STEP 4: Build exe
REM -----------------------------------------------
echo.
echo [4/5] Build MT5RemoteReader.exe...

for /f "delims=" %%v in ('powershell -Command "(Select-String -Path pyproject.toml -Pattern '^version = ').Line.Split(chr(34))[1]"') do set VERSION=%%v
if "%VERSION%"=="" ( echo  ERRORE: versione non trovata in pyproject.toml & pause & exit /b 1 )
echo  Versione: %VERSION%

set "ICON_FLAG="
if exist assets\mt5_icon.ico set "ICON_FLAG=--icon assets\mt5_icon.ico"

"%PYTHON_CMD%" -m PyInstaller --onefile --uac-admin --console ^
  --add-data "src\mt5_remote_reader_mcp\mt5_tool.py;." ^
  --name MT5RemoteReader ^
  %ICON_FLAG% ^
  src\mt5_remote_reader_mcp\setup_vps_installer.py

if not exist dist\MT5RemoteReader.exe ( echo  ERRORE PyInstaller. & pause & exit /b 1 )

REM -----------------------------------------------
REM STEP 5: Inno Setup
REM -----------------------------------------------
echo.
echo [5/5] Creazione installer...

set "ISCC="
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist "C:\Program Files\Inno Setup 6\ISCC.exe"       set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"
if "%ISCC%"=="" (
    winget install JRSoftware.InnoSetup --silent
    if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
)
if "%ISCC%"=="" ( echo  ERRORE: Inno Setup non trovato. & pause & exit /b 1 )

"%ISCC%" /DMyAppVersion=%VERSION% vps-installer\installer.iss

echo.
if exist Output\MT5RemoteReader_Setup_%VERSION%.exe (
    echo ============================================
    echo  BUILD COMPLETATA!
    echo  Output\MT5RemoteReader_Setup_%VERSION%.exe
    echo ============================================
) else (
    echo  ERRORE: installer non creato.
)
echo.
pause
