# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your bot code
COPY . .

# Debug: show the first 5 lines of bot.py
RUN echo "---- bot.py preview ----" && head -n5 bot.py

# Finally start your bot
CMD ["python", "bot.py"]
