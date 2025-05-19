# Dockerfile (temporary for debugging)

FROM python:3.11-slim

WORKDIR /app

# Install deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all code
COPY . .

# —— DEBUG: print the first 5 lines of bot.py so we know what’s in here
RUN echo "---- bot.py preview in container ----" \
 && head -n5 bot.py || true

# Finally, run the bot
CMD ["python", "bot.py"]
