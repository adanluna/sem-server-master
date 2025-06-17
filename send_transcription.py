from celery import Celery
from dotenv import load_dotenv
import os

# Cargar variables del entorno
load_dotenv()

# Leer variables de entorno
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672//")
QUEUE_TASK = os.getenv("QUEUE_TASK", "tasks.transcribir")
QUEUE_NAME = os.getenv("QUEUE_NAME", "transcripciones")
FILENAME = "forense.m4a"  # Solo el nombre base

# Inicializar Celery
app = Celery('client', broker=RABBITMQ_URL)

# Enviar tarea
result = app.send_task(QUEUE_TASK, args=[FILENAME], queue=QUEUE_NAME)

print(f"📨 Tarea enviada para transcribir: {FILENAME}")
print(f"🆔 ID de la tarea: {result.id}")
