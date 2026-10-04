@echo off
title VarsityShield - Setup
cd /d "%~dp0"
set PY=python
%PY% --version >nul 2>&1 || set PY=py
%PY% --version >nul 2>&1 || goto nopython
echo ============================================================
echo  VarsityShield setup. This takes 2 to 5 minutes. Keep internet ON.
echo ============================================================
echo.
echo [1/5] Creating a private Python environment (venv)...
if not exist venv\Scripts\activate.bat %PY% -m venv venv || goto failed
call venv\Scripts\activate.bat
echo [2/5] Installing required packages (flask, psutil, cryptography)...
python -m pip install --upgrade pip >nul
python -m pip install -r requirements.txt || goto failed
call env.bat
echo [3/5] Creating the encrypted backup store and users...
python cli.py init || goto failed
echo [4/5] Creating demo university data (students, fees, results)...
python simulate.py seed || goto failed
echo [5/5] Taking the first encrypted backup...
python cli.py backup || goto failed
echo.
echo ============================================================
echo  SETUP COMPLETE.
echo  Next: double-click 2_START_DASHBOARD.bat
echo  Login: admin   Password: ChangeMe@468
echo ============================================================
pause
exit /b 0
:failed
echo.
echo  Something failed above. Read the red or last lines, then see the Troubleshooting page in the guide.
pause
exit /b 1

:nopython
echo.
echo  ERROR: Python was not found on this computer.
echo  Install Python 3.10 or newer from https://www.python.org/downloads/
echo  On the FIRST installer screen tick "Add python.exe to PATH", then run this file again.
echo.
pause
exit /b 1
