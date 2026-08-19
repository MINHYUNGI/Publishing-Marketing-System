@echo off
setlocal EnableExtensions
title Publishing Marketing System

REM Always move to the folder containing this file.
pushd "%~dp0"
if errorlevel 1 (
    echo.
    echo [ERROR] Could not open the program folder.
    echo Folder: %~dp0
    echo.
    pause
    exit /b 1
)

REM Run the PowerShell launcher using an absolute path.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%CD%\run.ps1"
set "EXITCODE=%ERRORLEVEL%"

if not "%EXITCODE%"=="0" (
    echo.
    echo ============================================================
    echo The program could not be started. Error code: %EXITCODE%
    echo Please capture this window and send it for troubleshooting.
    echo ============================================================
    echo.
    pause
)

popd
exit /b %EXITCODE%
