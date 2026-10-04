@echo off
title VarsityShield - Demo menu
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
call env.bat
:menu
cls
echo ============================================================
echo  VarsityShield DEMO MENU  (dashboard must be running)
echo ============================================================
echo  1. Crash the Student Portal (watch it come back by itself)
echo  2. Stealth ransomware: encrypt 5 result files without renaming
echo  3. Take a backup now (it should REFUSE after step 2 or 4)
echo  4. Full ransomware attack (files renamed to .locked + ransom note)
echo  5. RESTORE everything from the last clean backup
echo  6. Verify all backups (integrity check)
echo  7. Run the full automatic drill (prints RTO, RPO, byte_identical)
echo  8. Open the sample_data folder (to show the damage or the recovery)
echo  0. Exit
echo.
set /p c=Type a number and press Enter: 
if "%c%"=="1" python simulate.py outage
if "%c%"=="2" python simulate.py tamper
if "%c%"=="3" python cli.py backup
if "%c%"=="4" python simulate.py attack
if "%c%"=="5" python cli.py restore --snapshot latest --clean
if "%c%"=="6" python cli.py verify
if "%c%"=="7" python simulate.py drill
if "%c%"=="8" start "" explorer sample_data
if "%c%"=="0" exit /b 0
echo.
pause
goto menu

:nopython
echo.
echo  ERROR: Python was not found on this computer.
echo  Install Python 3.10 or newer from https://www.python.org/downloads/
echo  On the FIRST installer screen tick "Add python.exe to PATH", then run this file again.
echo.
pause
exit /b 1
