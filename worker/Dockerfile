# Dockerfile para celery (en ./worker/Dockerfile)
FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements del worker e instalar dependencias Python
COPY worker/requirements.txt ./worker/
RUN pip install --no-cache-dir -r worker/requirements.txt

# Copiar todo el proyecto
COPY . .

# Configurar variables de entorno
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Comando por defecto
CMD ["celery", "-A", "worker.celery_app", "worker", "--loglevel=info"]
