@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

echo ============================================
echo   Open-KroWork Installer
echo ============================================
echo.

set "SCRIPT_DIR=%~dp0"

:: Step 1: Check Python
echo [1/4] Checking Python...
where python >nul 2>&1
if errorlevel 1 (
    echo   Error: Python not found. Please install Python 3.9+ first.
    echo   Download: https://www.python.org/downloads/
    pause
    exit /b 1
)

for /f "tokens=*" %%v in ('python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"') do set PY_VERSION=%%v
echo   Python version: %PY_VERSION%

python -c "import sys; exit(0 if sys.version_info >= (3, 9) else 1)"
if errorlevel 1 (
    echo   Error: Python 3.9+ required, found %PY_VERSION%
    pause
    exit /b 1
)
echo   OK

:: Step 2: Install dependencies
echo.
echo [2/4] Installing Python dependencies...
python -m pip install -r "%SCRIPT_DIR%requirements.txt" --quiet
if errorlevel 1 (
    echo   Warning: pip install failed. Trying with --user flag...
    python -m pip install -r "%SCRIPT_DIR%requirements.txt" --quiet --user
)
echo   OK

:: Step 3: Verify installation
echo.
echo [3/4] Verifying installation...
python -c "import requests, bs4, PIL; print('  All dependencies verified')"
if errorlevel 1 (
    echo   Dependency verification failed.
    echo   Try manually: pip install requests beautifulsoup4 Pillow
    pause
    exit /b 1
)

:: Step 4: Create directories
echo.
echo [4/4] Setting up directories...
if not exist "%USERPROFILE%\.krowork\apps" mkdir "%USERPROFILE%\.krowork\apps"
echo   Created %USERPROFILE%\.krowork\apps\
echo   OK

:: Done
echo.
echo ============================================
echo   Installation complete!
echo ============================================
echo.
echo Next steps:
echo.
echo   Mode 1 (Plugin):
echo     claude --plugin-dir "%SCRIPT_DIR%."
echo.
echo   Mode 2 (Global MCP):
echo     claude mcp add krowork -s user -- python "%SCRIPT_DIR%server\main.py"
echo     claude
echo.
echo   Then create your first app:
echo     ^> /krowork:create "My first app - describe what it does"
echo.
pause
