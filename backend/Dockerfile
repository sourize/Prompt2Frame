# Use Python 3.10 as base image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies required for Manim
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    python3-pip \
    python3-setuptools \
    python3-wheel \
    python3-cffi \
    libcairo2-dev \
    libpango1.0-dev \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-dev \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create media directory for video storage
RUN mkdir -p media/videos && chmod 777 media/videos

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Expose the port the app runs on
EXPOSE ${PORT}

# Command to run the application with production settings
CMD uvicorn src.app:app --host 0.0.0.0 --port ${PORT} --workers 4 --proxy-headers --forwarded-allow-ips='*' 