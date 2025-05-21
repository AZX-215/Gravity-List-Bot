@echo off
REM Run Gravity List Bot locally

REM Create virtual environment if it doesn't exist
if not exist venv (
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate

REM Upgrade pip and install dependencies
pip install --upgrade pip
pip install -r requirements.txt

REM Run the bot
python bot.py
