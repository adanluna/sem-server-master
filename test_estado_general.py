import requests
import json

# Configuración
API_URL = "http://172.21.82.2:8000"


def test_estado_general():
    """
    Prueba el endpoint POST /infra/estado_general
    """

    endpoint = f"{API_URL}/infra/estado_general"

    payload = {
        "camaras": [
            {"id": "camera1", "ip": "172.21.82.121"},
            {"id": "camera2", "ip": "172.21.82.238"}
        ]
    }

    print(f"\n{'='*60}")
    print(f"Probando: {endpoint}")
    print(f"{'='*60}\n")

    print("📤 Enviando payload:")
    print(json.dumps(payload, indent=2))
    print()

    try:
        response = requests.post(endpoint, json=payload)

        print(f"📊 Status Code: {response.status_code}")
        print()

        if response.status_code == 200:
            print("✅ Respuesta exitosa:")
            print(json.dumps(response.json(), indent=2, default=str))
        else:
            print("❌ Error en la respuesta:")
            print(response.text)

    except requests.exceptions.ConnectionError:
        print("❌ Error: No se pudo conectar al servidor API")
        print(f"   Asegúrate de que el servidor esté corriendo en {API_URL}")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")


if __name__ == "__main__":
    test_estado_general()
