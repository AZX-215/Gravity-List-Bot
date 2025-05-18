# Use a slim Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy and install dependencies first
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the code
COPY . .

# Launch the bot
CMD ["python", "bot.py"]
