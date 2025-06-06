# ─────────────────────────────────────────────────────────────────────────────
# 1) Base image: Python 3.10 (slim) 
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.10-slim

# ─────────────────────────────────────────────────────────────────────────────
# 2) Set working directory
# ─────────────────────────────────────────────────────────────────────────────
WORKDIR /app

# ─────────────────────────────────────────────────────────────────────────────
# 3) Install all system dependencies in one RUN (including ffmpeg for Manim)
# ─────────────────────────────────────────────────────────────────────────────
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

# ─────────────────────────────────────────────────────────────────────────────
# 4) Copy requirements.txt first (leverage Docker cache)
# ─────────────────────────────────────────────────────────────────────────────
COPY requirements.txt /app/requirements.txt

# ─────────────────────────────────────────────────────────────────────────────
# 5) Install Python dependencies
# ─────────────────────────────────────────────────────────────────────────────
RUN pip install --no-cache-dir -r /app/requirements.txt

# ─────────────────────────────────────────────────────────────────────────────
# 6) Copy the rest of your application code
#    At this point, /app/src/app.py, prompt_expander.py, generator.py, executor.py, etc.
# ─────────────────────────────────────────────────────────────────────────────
COPY . /app

# ─────────────────────────────────────────────────────────────────────────────
# 7) Create media directory for storing generated videos and give write perms
# ─────────────────────────────────────────────────────────────────────────────
RUN mkdir -p /app/media/videos && \
    chmod -R 777 /app/media

# ─────────────────────────────────────────────────────────────────────────────
# 8) Create a non-root user and give ownership of /app to that user
# ─────────────────────────────────────────────────────────────────────────────
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# ─────────────────────────────────────────────────────────────────────────────
# 9) Switch to non-root user
# ─────────────────────────────────────────────────────────────────────────────
USER appuser

# ─────────────────────────────────────────────────────────────────────────────
# 10) Environment variables
#     - PYTHONPATH=/app so that "import src.app" works
#     - PORT=8000 (default) 
#     - Ensure unbuffered output to see logs in real time
# ─────────────────────────────────────────────────────────────────────────────
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# ─────────────────────────────────────────────────────────────────────────────
# 11) Expose port 8000 (will serve FastAPI on 0.0.0.0:8000)
# ─────────────────────────────────────────────────────────────────────────────
EXPOSE 8000

# ─────────────────────────────────────────────────────────────────────────────
# 12) Final command: run Uvicorn with 1 worker, proxy headers, and keep-alive
# ─────────────────────────────────────────────────────────────────────────────
CMD ["uvicorn", "src.app:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1", \
     "--proxy-headers", \
     "--forwarded-allow-ips", "*", \
     "--timeout-keep-alive", "75", \
     "--log-level", "info"]
