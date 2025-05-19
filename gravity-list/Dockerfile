# Use the official Python slim image
FROM python:3.11-slim

# Set working dir
WORKDIR /app

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all your source code
COPY . .

# after COPY . .
RUN echo "---- bot.py contents: ----" && sed -n '1,5p' bot.py

# When the container launches, start your bot
CMD ["python", "bot.py"]
