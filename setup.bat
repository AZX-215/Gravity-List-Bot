@echo off
REM Setup Gravity List Bot environment

REM Create virtual environment
if not exist venv (
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate

REM Upgrade pip and install dependencies

pip install -r requirements.txt
python.exe -m pip install --upgrade pip

echo.
echo Setup complete! You can now run run.bat to start the bot.
pause
