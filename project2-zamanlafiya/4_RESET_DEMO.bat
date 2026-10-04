@echo off
title Zaman Lafiya - Reset
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
echo This deletes the demo database and model and rebuilds them (your keys are kept).
echo First close the 2_START_APP window if it is open.
set /p ok=Type YES and press Enter to continue: 
if /i not "%ok%"=="YES" exit /b 0
call keys.bat
if exist data\zamanlafiya.db del /f /q data\zamanlafiya.db*
if exist data\risk_model.pkl del /f /q data\risk_model.pkl*
if exist data\model_metrics.json del /f /q data\model_metrics.json
python manage.py init && python manage.py history && python manage.py train
echo Reset complete. Double-click 2_START_APP.bat
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
