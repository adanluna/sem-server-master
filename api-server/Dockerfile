FROM python:3.11-slim

WORKDIR /code

# Copiar requirements desde api-server
COPY api-server/requirements.txt /code/requirements.txt

# Instalar dependencias
RUN pip install --no-cache-dir -r /code/requirements.txt

# Copiar solo el contenido de api-server
COPY api-server /code/api-server

# Copiar el worker para que FastAPI pueda importarlo
COPY worker /code/worker
