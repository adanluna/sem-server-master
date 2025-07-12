# Dockerfile para celery worker
FROM python:3.11-slim

# Crear el directorio de trabajo del worker
WORKDIR /app/worker

# Instalar dependencias del sistema (FFmpeg)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements específicos del worker e instalar dependencias Python
COPY worker/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copiar solo el código del worker
COPY worker/ ./

# Configurar variables de entorno
ENV PYTHONPATH=/app/worker
ENV PYTHONUNBUFFERED=1

# Comando por defecto para arrancar celery
CMD ["celery", "-A", "celery_app", "worker", "--loglevel=info"]
