@echo off
title Zaman Lafiya - Web app (keep this window open)
cd /d "%~dp0"
set PY=python
%PY% --version >nul 2>&1 || set PY=py
%PY% --version >nul 2>&1 || goto nopython
if not exist venv\Scripts\activate.bat (
  echo  Setup has not been done yet. Double-click 1_SETUP.bat first.
  pause
  exit /b 1
)
call venv\Scripts\activate.bat
if not exist keys.bat (
  echo  keys.bat is missing. Run 1_SETUP.bat first.
  pause
  exit /b 1
)
call keys.bat
echo Starting Zaman Lafiya. Your browser will open in a few seconds.
echo If the page does not load, wait 5 seconds and press F5 (refresh).
echo KEEP THIS WINDOW OPEN. Closing it stops the system.
start "" cmd /c "timeout /t 4 >nul & start http://127.0.0.1:5050"
python app.py
pause
exit /b 0

:nopython
echo.
echo  ERROR: Python was not found on this computer.
echo  Install Python 3.10 or newer from https://www.python.org/downloads/
echo  On the FIRST installer screen tick "Add python.exe to PATH", then run this file again.
echo.
pause
exit /b 1
