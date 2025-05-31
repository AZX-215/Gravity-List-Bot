# Use the official Python 3.10 slim base image
FROM python:3.10-slim

# Set a working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files into the container
COPY . .

# (Optional) Expose port if your bot uses a web endpoint for keep-alive
EXPOSE 8080

# Set environment variable placeholder (Railway will inject the real BOT_TOKEN)
ENV BOT_TOKEN=""

# Default command to run your bot
CMD ["python", "bot.py"]
