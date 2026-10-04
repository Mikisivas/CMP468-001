@echo off
title Zaman Lafiya - Setup
cd /d "%~dp0"
set PY=python
%PY% --version >nul 2>&1 || set PY=py
%PY% --version >nul 2>&1 || goto nopython
echo ============================================================
echo  Zaman Lafiya setup. This takes 3 to 8 minutes. Keep internet ON.
echo ============================================================
echo.
echo [1/6] Creating a private Python environment (venv)...
if not exist venv\Scripts\activate.bat %PY% -m venv venv || goto failed
call venv\Scripts\activate.bat
echo [2/6] Installing packages (flask, cryptography, scikit-learn, numpy). Please wait...
python -m pip install --upgrade pip >nul
python -m pip install -r requirements.txt || goto failed
echo [3/6] Creating secret keys (saved in keys.bat, keep it private)...
python manage.py genkey --save >nul || goto failed
call keys.bat
echo [4/6] Creating the database, map layers, contacts and users...
python manage.py init || goto failed
echo [5/6] Creating two years of training history...
python manage.py history || goto failed
echo [6/6] Training the risk prediction model...
python manage.py train || goto failed
echo.
echo ============================================================
echo  SETUP COMPLETE.
echo  Next: double-click 2_START_APP.bat
echo  Login: admin   Password: ChangeMe@468
echo ============================================================
pause
exit /b 0
:failed
echo.
echo  Something failed above. Read the last lines, then see the Troubleshooting page in the guide.
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
