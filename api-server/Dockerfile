FROM python:3.11-slim

WORKDIR /code

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar solo API y Worker
COPY api_server /code/api_server
COPY worker /code/worker
COPY .env /code/.env
