FROM python:3.11-slim

WORKDIR /app

# 🔧 Dependencias necesarias para psutil (y futuras libs nativas)
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    build-essential \
    procps \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY worker/requirements.txt /app/worker/requirements.txt

# Instalar dependencias Python
RUN pip install --no-cache-dir -r /app/worker/requirements.txt

# Copiar código del worker
COPY worker /app/worker

CMD ["celery", "-A", "worker.tasks", "worker"]
