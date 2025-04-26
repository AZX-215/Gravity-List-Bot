@echo off
REM Navigate to the bot folder
cd /d "C:\Users\Antho\OneDrive\Desktop\gravity-tribe-bot"

REM Activate the virtual environment
call .venv\Scripts\Activate.bat

REM (Optional) Install dependencies if not already
pip install -r requirements.txt

REM Run the bot
python bot.py

REM Keep window open after bot exits
pause
