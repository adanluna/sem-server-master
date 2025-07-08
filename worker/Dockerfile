FROM python:3.11-slim

# Crear usuario
RUN adduser --disabled-password --gecos '' celeryuser

WORKDIR /code

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Cambiar propietario
RUN chown -R celeryuser:celeryuser /code

# Cambiar a ese usuario
USER celeryuser

CMD ["celery", "-A", "celery_app", "worker", "--loglevel=info"]
