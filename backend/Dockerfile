FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev build-essential curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Create non-root user
RUN useradd --create-home appuser

# Copy requirements first for better caching
COPY requirements.txt ./
RUN pip install --upgrade pip

RUN pip install --default-timeout=1000 --no-cache-dir -r requirements.txt

# Copy application code
COPY . /app

RUN mkdir -p /app/logs /app/data /app/rag/vector_store

# Ensure permissions
RUN chown -R appuser:appuser /app

USER appuser

ENV PATH="/home/appuser/.local/bin:$PATH"

# Expose app port
EXPOSE 8000

# Copy and use entrypoint that waits for dependent services
COPY --chown=appuser:appuser entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Production-ready start command using gunicorn + uvicorn workers
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "api.main:app", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "120"]
