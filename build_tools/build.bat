@echo off
REM AERA Agent build helper for Windows.
REM
REM Usage:   build_tools\build.bat              standalone bundle
REM          build_tools\build.bat installer    also build Inno Setup .exe

setlocal
cd /d "%~dp0\.."

set PYTHON=python
where %PYTHON% >nul 2>&1 || set PYTHON=py

echo ================================
echo   Building AERA Agent
%PYTHON% --version
echo ================================

if "%1"=="installer" (
    %PYTHON% build_tools\build.py --installer
) else (
    %PYTHON% build_tools\build.py
)

echo.
echo Run AERA with:   dist\AERA\AERA.exe
pause
