import os
from dotenv import load_dotenv
from kombu import Connection

# Cargar variables del .env
load_dotenv()

rabbit_url = os.getenv("RABBITMQ_URL")
print(f"🚀 Intentando conexión con RabbitMQ usando: {rabbit_url}")

try:
    with Connection(rabbit_url) as conn:
        print("✅ Conexión exitosa a RabbitMQ")
except Exception as e:
    print(f"💥 Error al conectar con RabbitMQ: {e}")
