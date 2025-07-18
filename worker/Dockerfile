# Dockerfile para celery worker
FROM python:3.11-slim

WORKDIR /app/worker

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependencias Python
COPY worker/requirements.txt /app/worker/requirements.txt
RUN pip install --no-cache-dir -r /app/worker/requirements.txt

# Copiar el código fuente del worker
COPY worker/ /app/worker/

# Configurar entorno
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/worker

CMD ["celery", "-A", "celery_app", "worker", "--loglevel=info"]
