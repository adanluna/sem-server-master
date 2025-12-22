from fastapi import APIRouter, HTTPException
import os
import json
import pika

router = APIRouter()


@router.post("/enviar")
def enviar_a_whisper(data: dict):
    sesion_id = data.get("sesion_id")
    expediente = data.get("expediente")

    if not sesion_id or not expediente:
        raise HTTPException(400, "Datos incompletos")

    credentials = pika.PlainCredentials(
        os.getenv("RABBITMQ_USER"),
        os.getenv("RABBITMQ_PASS")
    )

    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host=os.getenv("RABBITMQ_HOST", "rabbitmq"),
            credentials=credentials
        )
    )

    channel = connection.channel()
    channel.queue_declare(queue="transcripciones", durable=True)

    channel.basic_publish(
        exchange="",
        routing_key="transcripciones",
        body=json.dumps(data)
    )

    connection.close()

    return {"status": "whisper_job_enviado"}
