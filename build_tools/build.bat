@echo off
REM AERA Agent build helper for Windows.
REM
REM Usage:
REM   build_tools\build.bat                standalone bundle (dist\AERA\)
REM   build_tools\build.bat --onefile      single file exe (dist\AERA.exe)
REM   build_tools\build.bat --installer    + Setup.exe + MSI (if WiX)
REM   build_tools\build.bat --all          onedir + onefile + pyz + zip + installer

setlocal
cd /d "%~dp0\.."

set PYTHON=python
where %PYTHON% >nul 2>&1 || set PYTHON=py

echo ================================
echo   Building AERA Agent (Windows)
%PYTHON% --version
echo   Args: %*
echo ================================

REM Forward all args
%PYTHON% build_tools\build.py %*

echo.
echo Outputs in dist\:
dir dist 2>nul
echo.
echo Run AERA with:
echo   dist\AERA\AERA.exe
if exist dist\AERA.exe echo   or single file: dist\AERA.exe
if exist dist\AERA.pyz echo   or pyz: python dist\AERA.pyz
if exist dist\AERA-Setup-*.exe echo   Installer: dist\AERA-Setup-*.exe
if exist dist\AERA-*.msi echo   MSI: dist\AERA-*.msi
pause
