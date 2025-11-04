@echo off
REM Run Tool Launcher in a Python virtual environment
REM Usage: double-click this file or run from PowerShell/CMD in the project folder.

:: Move to the batch file directory so relative paths work
cd /d "%~dp0"

if not exist "%~dp0tool_launcher_fixed.py" (
    echo Error: ToolLauncer.py not found!
    pause
    exit /b 1
)

echo Checking for Python...
python --version || (
    echo Python not found on PATH. Please install Python 3.8+ and try again.
    pause
    exit /b 1
)

echo Creating (if needed) and activating virtual environment 'venv'...
if not exist venv (
    python -m venv venv
)

echo Activating venv...
call venv\Scripts\activate

echo Installing requirements (will skip if already satisfied)...
pip install -r requirements.txt

echo Launching ToolLauncher.py...
python "%~dp0tool_launcher_fixed.py"

echo Done. Press any key to close.
pause
