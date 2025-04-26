# Use the official Python base image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the code
COPY . /app

# Expose no ports; this is an outgoing bot
# Define the command to run the bot
CMD ["python", "bot.py"]
