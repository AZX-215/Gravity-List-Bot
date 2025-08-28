# Use the official Python 3.11 slim base image
FROM python:3.11-slim

# Python runtime behavior (set early so it applies to all later layers)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set a working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN python -m pip install -U pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files into the container
COPY . .

# (Optional) Expose port if your bot uses a web endpoint for keep-alive
EXPOSE 8080

# (Optional) Placeholder; Railway will inject the real value
# ENV BOT_TOKEN=""

# Default command to run your bot
CMD ["python", "bot.py"]
