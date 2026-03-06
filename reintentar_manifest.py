import sys
from worker.manifest_builder import generar_manifest


def main():
    if len(sys.argv) < 4:
        print("Uso: python /app/reintentar_manifest.py <sesion_id> <fecha_iso> <job_id>")
        sys.exit(1)

    sesion_id = int(sys.argv[1])
    fecha_iso = sys.argv[2]
    job_id = int(sys.argv[3])

    print(
        f"Relanzando manifest para sesión={sesion_id}, fecha_iso={fecha_iso}, job_id={job_id}")
    result = generar_manifest.delay(sesion_id, fecha_iso, job_id)
    print(f"Tarea enviada correctamente. task_id={result.id}")


if __name__ == "__main__":
    main()
