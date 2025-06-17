# worker/celery_app.py
from celery import Celery

app = Celery('worker',
             broker='amqp://guest:guest@localhost:5672//',
             backend='rpc://',
             include=['worker.convertir_video'])  # Importa las tareas

app.conf.task_routes = {
    "worker.convertir_video.convertir_video": {"queue": "conversiones_video"},
}
