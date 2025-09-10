# Python image (small, stable)
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Railway will route to this; our app binds to $PORT (or 8080)
EXPOSE 8080

# Start the bot (FastAPI server is started in-process by bot.py)
CMD ["python", "bot.py"]
