# ────────────────────────────────────────────────────────────────────────────
# 1) Base image: Python 3.10-slim
# ────────────────────────────────────────────────────────────────────────────
FROM python:3.10-slim

# ────────────────────────────────────────────────────────────────────────────
# 2) Set working directory
# ────────────────────────────────────────────────────────────────────────────
WORKDIR /app

# ────────────────────────────────────────────────────────────────────────────
# 3) Install system dependencies (including ffmpeg for Manim)
# ────────────────────────────────────────────────────────────────────────────
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      build-essential \
      python3-dev \
      python3-pip \
      python3-setuptools \
      python3-wheel \
      libcairo2-dev \
      libpango1.0-dev \
      libpangocairo-1.0-0 \
      libgdk-pixbuf2.0-dev \
      libffi-dev \
      shared-mime-info \
      curl \
      ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# ────────────────────────────────────────────────────────────────────────────
# 4) Copy requirements.txt (to leverage Docker layer caching)
# ────────────────────────────────────────────────────────────────────────────
COPY requirements.txt /app/requirements.txt

# ────────────────────────────────────────────────────────────────────────────
# 5) Install Python dependencies
# ────────────────────────────────────────────────────────────────────────────
RUN pip install --no-cache-dir -r /app/requirements.txt

# ────────────────────────────────────────────────────────────────────────────
# 6) Copy the rest of the application code
# ────────────────────────────────────────────────────────────────────────────
COPY . /app

# ────────────────────────────────────────────────────────────────────────────
# 7) Create media/videos folder and give write permissions
# ────────────────────────────────────────────────────────────────────────────
RUN mkdir -p /app/media/videos && \
    chmod -R 777 /app/media

# ────────────────────────────────────────────────────────────────────────────
# 8) Create non-root user and chown /app
# ────────────────────────────────────────────────────────────────────────────
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# ────────────────────────────────────────────────────────────────────────────
# 9) Switch to non-root user
# ────────────────────────────────────────────────────────────────────────────
USER appuser

# ────────────────────────────────────────────────────────────────────────────
# 10) Environment variables
#     - PYTHONPATH so that "src.app" is importable
#     - Unbuffered stdout so logs appear immediately
# ────────────────────────────────────────────────────────────────────────────
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# ────────────────────────────────────────────────────────────────────────────
# 11) Expose port 8000 (platform will override $PORT if provided)
# ────────────────────────────────────────────────────────────────────────────
EXPOSE 8000

# ────────────────────────────────────────────────────────────────────────────
# 12) Final command (shell‐form) so $PORT expands at runtime
# ────────────────────────────────────────────────────────────────────────────
CMD sh -c "uvicorn src.app:app \
    --host 0.0.0.0 \
    --port ${PORT:-8000} \
    --workers 1 \
    --proxy-headers \
    --forwarded-allow-ips='*' \
    --timeout-keep-alive 75 \
    --log-level info"
