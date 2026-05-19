@echo off
setlocal enabledelayedexpansion

REM IDS Notifier - automatic installer
REM No menu, no user choices. It configures Supabase + email, starts the
REM background watcher, then inserts one test alert.

title IDS Notifier - Installation automatique

set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
set "NOTIFIER=%SCRIPT_DIR%\notifier.py"
set "ENV_SOURCE=%SCRIPT_DIR%\.env"
set "EMAIL_TEMPLATE=%SCRIPT_DIR%\email_config_template.json"
set "CONFIG_DIR=%APPDATA%\IDS_Notifier"
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "RUN_VBS=%SCRIPT_DIR%\run_notifier.vbs"
set "STOP_VBS=%SCRIPT_DIR%\stop_notifier.vbs"
set "EMAIL_CONFIG=%CONFIG_DIR%\email_config.json"
set "APP_ENV=%CONFIG_DIR%\.env"
set "TASK_NAME=IDS_Notifier"

cls
echo.
echo ============================================================
echo   IDS Alert Notifier - Installation automatique
echo   Base: Supabase PostgreSQL
echo   Email: admin + security_admin depuis la table utilisateur
echo ============================================================
echo.

echo [1/8] Verification de Python...
where python >nul 2>&1
if errorlevel 1 (
    echo ERREUR: Python est introuvable dans le PATH.
    echo Installez Python depuis https://www.python.org/downloads/
    echo et cochez "Add Python to PATH".
    pause
    exit /b 1
)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set "PY_VERSION=%%i"
echo OK: Python %PY_VERSION%

if not exist "%NOTIFIER%" (
    echo ERREUR: notifier.py introuvable dans %SCRIPT_DIR%.
    pause
    exit /b 1
)

echo.
echo [2/8] Installation des dependances Python...
python -m pip --version >nul 2>&1
if errorlevel 1 python -m ensurepip --upgrade
python -m pip install --upgrade pip --quiet
for %%P in (psycopg2-binary requests plyer winotify win10toast-persist) do (
    echo   - %%P
    python -m pip install --quiet %%P
)
echo OK: dependances installees.

echo.
echo [3/8] Preparation du dossier de configuration...
if not exist "%CONFIG_DIR%" mkdir "%CONFIG_DIR%"
if exist "%ENV_SOURCE%" (
    copy /Y "%ENV_SOURCE%" "%APP_ENV%" >nul
    echo OK: configuration Supabase copiee vers %APP_ENV%
) else (
    echo ERREUR: fichier .env introuvable dans %SCRIPT_DIR%.
    echo DATABASE_URL est obligatoire pour Supabase.
    pause
    exit /b 1
)

if exist "%EMAIL_TEMPLATE%" (
    copy /Y "%EMAIL_TEMPLATE%" "%EMAIL_CONFIG%" >nul
    echo OK: configuration email copiee vers %EMAIL_CONFIG%
) else (
    echo ERREUR: email_config_template.json introuvable.
    echo La configuration email automatique est obligatoire.
    pause
    exit /b 1
)

(
    echo # IDS Notifier runtime configuration
    echo POLL_INTERVAL=5
    echo SMTP_ENABLED=true
) > "%CONFIG_DIR%\notifier.conf"

echo.
echo [4/8] Test de connexion Supabase...
python "%NOTIFIER%" --check-db
if errorlevel 1 (
    echo ERREUR: Supabase inaccessible. Verifiez Internet et DATABASE_URL.
    pause
    exit /b 1
)

echo.
echo [5/8] Creation des lanceurs invisibles...
(
    echo ' IDS Notifier - launcher invisible
    echo Set oWS = WScript.CreateObject^("WScript.Shell"^)
    echo sCmd = "pythonw ""%NOTIFIER%"" --interval 5"
    echo oWS.Run sCmd, 0, False
) > "%RUN_VBS%"

(
    echo ' IDS Notifier - stop current notifier.py instances only
    echo Set oWS = WScript.CreateObject^("WScript.Shell"^)
    echo oWS.Run "powershell -NoProfile -ExecutionPolicy Bypass -Command ""Get-CimInstance Win32_Process -Filter 'name = ''pythonw.exe'' or name = ''python.exe''' ^| Where-Object { $_.CommandLine -like '*notifier.py*' } ^| ForEach-Object { Stop-Process -Id $_.ProcessId -Force }""", 0, True
) > "%STOP_VBS%"
echo OK: lanceurs crees.

echo.
echo [6/8] Installation au demarrage Windows...
if exist "%STARTUP%\IDS_Notifier.vbs" del /Q "%STARTUP%\IDS_Notifier.vbs"
copy /Y "%RUN_VBS%" "%STARTUP%\IDS_Notifier.vbs" >nul
echo OK: demarrage utilisateur configure.

schtasks /delete /tn "%TASK_NAME%" /f >nul 2>&1
schtasks /create /tn "%TASK_NAME%" /tr "wscript.exe ""%RUN_VBS%""" /sc onlogon /f >nul 2>&1
if errorlevel 1 (
    echo INFO: tache planifiee non creee, le dossier Demarrage suffit.
) else (
    echo OK: tache planifiee creee au logon utilisateur.
)

echo.
echo [7/8] Redemarrage du notifier en arriere-plan...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process -Filter \"name = 'pythonw.exe' or name = 'python.exe'\" | Where-Object { $_.CommandLine -like '*notifier.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >nul 2>&1
timeout /t 2 /nobreak >nul
wscript "%RUN_VBS%"
timeout /t 4 /nobreak >nul

powershell -NoProfile -ExecutionPolicy Bypass -Command "if (Get-CimInstance Win32_Process -Filter \"name = 'pythonw.exe' or name = 'python.exe'\" | Where-Object { $_.CommandLine -like '*notifier.py*' }) { exit 0 } else { exit 1 }" >nul 2>&1
if errorlevel 1 (
    echo ERREUR: notifier non demarre. Consultez %CONFIG_DIR%\notifier.log
    pause
    exit /b 1
) else (
    echo OK: notifier demarre.
)

echo.
echo [8/8] Termine.
echo.
echo ============================================================
echo   Installation terminee
echo   Logs:   %CONFIG_DIR%\notifier.log
echo   Config: %CONFIG_DIR%
echo   Le notifier surveille Supabase toutes les 5 secondes.
echo ============================================================
echo.
pause
exit /b 0