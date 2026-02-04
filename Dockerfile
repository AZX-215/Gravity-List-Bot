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

# This is a background worker (Discord bot). No HTTP server is required.
# EXPOSE is optional; keeping it does not affect execution.
EXPOSE 8080

# Start the bot
CMD ["python", "bot.py"]
