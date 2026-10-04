@echo off
title VarsityShield - Reset
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
echo This deletes ALL demo data, backups and users, so you can start fresh.
echo First close the dashboard window if it is open.
set /p ok=Type YES and press Enter to continue: 
if /i not "%ok%"=="YES" exit /b 0
taskkill /f /im python.exe >nul 2>&1
call venv\Scripts\activate.bat
python cli.py reset-demo
echo Now double-click 1_SETUP.bat again.
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
