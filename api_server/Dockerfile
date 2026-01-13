FROM python:3.11-slim

WORKDIR /code

# --------------------------------------------------
# Dependencias nativas OBLIGATORIAS (ARM + psutil)
# --------------------------------------------------
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    build-essential \
    procps \
    && apt-get install -y --no-install-recommends iputils-ping \
    && rm -rf /var/lib/apt/lists/*

# --------------------------------------------------
# Dependencias Python
# --------------------------------------------------
COPY api_server/requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir -r /code/requirements.txt

# --------------------------------------------------
# Código fuente
# --------------------------------------------------
COPY api_server /code/api_server
COPY worker /code/worker

# --------------------------------------------------
# PYTHONPATH explícito
# --------------------------------------------------
ENV PYTHONPATH=/code
