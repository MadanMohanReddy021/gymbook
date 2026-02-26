# Python base image
FROM python:3.11-slim

# Install Chromium + driver + dependencies
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    wget \
    curl \
    unzip \
    fonts-liberation \
    libnss3 \
    libatk-bridge2.0-0 \
    libxkbcommon0 \
    libgtk-3-0 \
    libgbm1 \
    libasound2 \
    libxshmfence1 \
    && rm -rf /var/lib/apt/lists/*

# Set chrome path
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

# Working directory
WORKDIR /app

# Copy files
COPY . /app

# Install Python deps
RUN pip install --no-cache-dir -r requirements.txt

# Start server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]