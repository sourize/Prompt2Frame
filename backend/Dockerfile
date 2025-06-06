# Use Python 3.10 as base image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies required for Manim in smaller chunks
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    python3-pip \
    python3-setuptools \
    python3-wheel \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    python3-cffi \
    libcairo2-dev \
    libpango1.0-dev \
    libpangocairo-1.0-0 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libgdk-pixbuf2.0-dev \
    libffi-dev \
    shared-mime-info \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create media directory for video storage and set permissions
RUN mkdir -p media/videos && \
    chmod -R 777 media && \
    chown -R nobody:nogroup media

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PORT=8000
ENV LOG_LEVEL=debug

# Expose the port the app runs on
EXPOSE ${PORT}

# Create startup script with health check
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
echo "Starting application..."\n\
\n\
# Start the application in the background\n\
uvicorn src.app:app --host 0.0.0.0 --port ${PORT} --workers 1 --proxy-headers --forwarded-allow-ips="*" --timeout-keep-alive 75 --log-level debug &\n\
\n\
# Wait for the application to start\n\
echo "Waiting for application to start..."\n\
for i in $(seq 1 30); do\n\
    if curl -s http://localhost:${PORT}/health > /dev/null; then\n\
        echo "Application is healthy!"\n\
        break\n\
    fi\n\
    echo "Attempt $i: Application not ready yet..."\n\
    sleep 2\n\
done\n\
\n\
# Keep the container running\n\
wait\n\
' > /app/start.sh && \
    chmod +x /app/start.sh

# Create a non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Command to run the application with production settings
CMD ["/app/start.sh"] 