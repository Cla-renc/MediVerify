@echo off
REM ============================================================
REM  MediVerify Frontend Setup — runs in standard CMD
REM ============================================================

SET "PROJDIR=%~dp0"
cd /d "%PROJDIR%frontend"

echo [MediVerify Frontend Setup]
echo Working directory: %CD%
echo.

REM ---- Try to find node.exe in common install paths ----
SET "NODE="
IF EXIST "C:\Program Files\nodejs\node.exe" SET "NODE=C:\Program Files\nodejs\node.exe"
IF EXIST "C:\Program Files (x86)\nodejs\node.exe" SET "NODE=C:\Program Files (x86)\nodejs\node.exe"
IF EXIST "%APPDATA%\nvm\v20.12.2\node.exe" SET "NODE=%APPDATA%\nvm\v20.12.2\node.exe"
IF EXIST "C:\Tools\nodejs\node.exe" SET "NODE=C:\Tools\nodejs\node.exe"

FOR /F "tokens=*" %%i IN ('where node 2^>nul') DO (
    IF "!NODE!"=="" SET "NODE=%%i"
)

IF "%NODE%"=="" (
    echo ERROR: Node.js not found. Please install from https://nodejs.org
    echo Then re-run this script.
    exit /b 1
)

echo Node.js found: %NODE%
FOR /F %%v IN ('"%NODE%" --version') DO echo Node version: %%v

SET "NPM=%NODE%\..\npm.cmd"
IF NOT EXIST "%NPM%" SET "NPM=npm"

echo.
echo [1/2] Installing npm packages...
"%NODE%" "%NODE%\..\node_modules\npm\bin\npm-cli.js" install
IF ERRORLEVEL 1 (
    echo Trying npm directly...
    npm install
)

echo.
echo [2/2] Starting development server...
echo Frontend will be available at http://localhost:3000
echo Make sure backend is running at http://localhost:8000
echo Press Ctrl+C to stop.
echo.
"%NODE%" "%NODE%\..\node_modules\npm\bin\npm-cli.js" run dev
