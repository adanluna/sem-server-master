FROM python:3.11-slim

WORKDIR /code

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar solo API y Worker
COPY api-server /code/api-server
COPY worker /code/worker
