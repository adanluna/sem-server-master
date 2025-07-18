from celery import Celery
from dotenv import load_dotenv
import os

load_dotenv()

app = Celery(broker=os.getenv("RABBITMQ_URL"))

# Esto mandará una tarea ficticia al queue default "celery"
result = app.send_task("worker.tasks.dummy_task", args=["Hola SEMEFO"])

print(f"🚀 Dummy task enviada con ID: {result.id}")
