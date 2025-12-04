FROM python:3.11-slim

WORKDIR /code

COPY api-server/requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir -r /code/requirements.txt

COPY api-server /code/api-server
COPY worker /code/worker
