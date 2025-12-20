FROM python:3.11-slim

WORKDIR /code

# ------------------------------
# Instalar dependencias
# ------------------------------
COPY api-server/requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir -r /code/requirements.txt

# ------------------------------
# Copiar código
# ------------------------------
COPY api-server /code/api_server
COPY worker /code/worker

# ------------------------------
# PYTHONPATH explícito
# ------------------------------
ENV PYTHONPATH=/code
