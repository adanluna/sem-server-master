import sys
from worker.manifest_builder import generar_manifest


def main():
    if len(sys.argv) < 2:
        print("Uso: python reintentar_manifest.py <sesion_id>")
        sys.exit(1)

    sesion_id = int(sys.argv[1])

    print(f"Relanzando manifest para sesión {sesion_id}")

    generar_manifest.delay(sesion_id)

    print("Tarea enviada al worker.")


if __name__ == "__main__":
    main()
