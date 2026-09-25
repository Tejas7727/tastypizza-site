@echo off
setlocal
cd /d "%~dp0"
title Tasty Pizza - publish the website
color 0F

echo.
echo   ================================================
echo     TASTY PIZZA - PUBLISHING THE WEBSITE
echo   ================================================
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo   Python is not installed on this computer.
  echo   Install it from python.org, tick "Add Python to PATH",
  echo   then run this again.
  echo.
  pause
  exit /b 1
)

echo   [1 of 4]  Reading your changes from the Excel sheet...
echo.
python scripts\control_sheet.py import
if errorlevel 1 (
  echo.
  echo   ------------------------------------------------
  echo     STOPPED. Nothing was published.
  echo     The problems are listed above, with the sheet
  echo     and the cell. Fix them, save, CLOSE Excel,
  echo     and run this again.
  echo   ------------------------------------------------
  echo.
  pause
  exit /b 1
)

echo.
echo   [2 of 4]  Rebuilding the website...
echo.
python build.py
if errorlevel 1 goto broke

echo.
echo   [3 of 4]  Checking nothing is broken...
echo.
python audit.py
if errorlevel 1 (
  echo.
  echo   ------------------------------------------------
  echo     STOPPED. Nothing was published.
  echo     The check above found a problem. The live site
  echo     has NOT changed, so customers still see the
  echo     old one. Send the message above to Tejas.
  echo   ------------------------------------------------
  echo.
  pause
  exit /b 1
)

echo.
echo   [4 of 4]  Sending it to the website...
echo.
git add data docs "TastyPizza-Control.xlsx" >nul 2>nul
git diff --staged --quiet
if not errorlevel 1 (
  echo   Nothing had changed - the website is already up to date.
  echo.
  pause
  exit /b 0
)
git commit -m "Update from the control sheet" >nul
if errorlevel 1 goto broke
git push
if errorlevel 1 (
  echo.
  echo   ------------------------------------------------
  echo     Could not reach the website.
  echo     Check the internet connection and run this
  echo     again. Your changes are saved either way.
  echo   ------------------------------------------------
  echo.
  pause
  exit /b 1
)

echo.
echo   ================================================
echo     DONE.
echo.
echo     The website updates in about a minute.
echo     tejas7727.github.io/tastypizza-site
echo   ================================================
echo.
pause
exit /b 0

:broke
echo.
echo   ------------------------------------------------
echo     Something went wrong and nothing was published.
echo     Send the message above to Tejas.
echo   ------------------------------------------------
echo.
pause
exit /b 1
