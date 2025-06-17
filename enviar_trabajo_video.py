from celery import Celery
from dotenv import load_dotenv
import os
import time
import threading
import itertools
import sys

# Cargar variables de entorno
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672//")
RESULT_BACKEND = os.getenv("RESULT_BACKEND", "rpc://")
QUEUE_TASK = "worker.convertir_video.convertir_video"
QUEUE_NAME = "conversiones_video"

# Inicializar Celery con backend habilitado
app = Celery('client', broker=RABBITMQ_URL, backend=RESULT_BACKEND)

archivo = "video_prueba.avi"

result = app.send_task(QUEUE_TASK, args=[archivo], queue=QUEUE_NAME)

print(f"📨 Tarea enviada para convertir: {archivo}")
print(f"🆔 ID de la tarea: {result.id}")

# Spinner de espera
done = False


def loading_spinner():
    for c in itertools.cycle(['|', '/', '-', '\\']):
        if done:
            break
        sys.stdout.write(f'\r⏳ Esperando resultado... {c}')
        sys.stdout.flush()
        time.sleep(0.1)


t = threading.Thread(target=loading_spinner)
t.start()

# Esperar resultado (hasta 10 minutos)
response = result.get(timeout=600)
done = True
t.join()

print(f"\n✅ Resultado: {response}")
