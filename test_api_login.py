#!/usr/bin/env python3
"""
Script de prueba para endpoint de autenticación LDAP via API
Prueba los endpoints /auth/login y /auth/ldap
"""
import requests
import json
from datetime import datetime

# Configuración
API_BASE_URL = "http://172.21.82.2:8000"
USERNAME = "testuser1"
PASSWORD = "T3st$2025FG!."


def test_auth_endpoint(endpoint_path: str):
    """
    Prueba un endpoint de autenticación
    """
    url = f"{API_BASE_URL}{endpoint_path}"

    print("=" * 70)
    print(f"PRUEBA DE ENDPOINT: {endpoint_path}")
    print("=" * 70)
    print(f"URL: {url}")
    print(f"Usuario: {USERNAME}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 70)

    # Preparar datos de login
    payload = {
        "username": USERNAME,
        "password": PASSWORD
    }

    headers = {
        "Content-Type": "application/json"
    }

    try:
        # Realizar petición POST
        print("\n📤 Enviando petición POST...")
        print(
            f"   Payload: {json.dumps({'username': USERNAME, 'password': '***'})}")

        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=10
        )

        # Mostrar respuesta
        print(f"\n📥 Respuesta recibida:")
        print(f"   Status Code: {response.status_code}")
        print(f"   Reason: {response.reason}")

        # Intentar parsear JSON
        try:
            response_data = response.json()
            print(f"\n📄 Contenido de respuesta:")
            print(json.dumps(response_data, indent=2, ensure_ascii=False))

            # Validar estructura de respuesta exitosa
            if response.status_code == 200:
                print("\n✅ AUTENTICACIÓN EXITOSA")

                # Validar tokens
                if "access_token" in response_data:
                    access_token = response_data["access_token"]
                    print(f"\n🔑 Access Token recibido:")
                    print(f"   Longitud: {len(access_token)} caracteres")
                    print(f"   Preview: {access_token[:50]}...")

                if "refresh_token" in response_data:
                    refresh_token = response_data["refresh_token"]
                    print(f"\n🔄 Refresh Token recibido:")
                    print(f"   Longitud: {len(refresh_token)} caracteres")
                    print(f"   Preview: {refresh_token[:50]}...")

                if "user" in response_data:
                    print(f"\n👤 Información de usuario:")
                    user_info = response_data["user"]
                    for key, value in user_info.items():
                        print(f"   {key}: {value}")

                return True, response_data

            else:
                print(f"\n❌ AUTENTICACIÓN FALLIDA")
                print(f"   Código de error: {response.status_code}")
                if "detail" in response_data:
                    print(f"   Detalle: {response_data['detail']}")
                return False, response_data

        except json.JSONDecodeError:
            print(f"\n⚠️  Respuesta no es JSON válido:")
            print(f"   {response.text[:500]}")
            return False, None

    except requests.exceptions.ConnectionError as e:
        print(f"\n❌ ERROR DE CONEXIÓN:")
        print(f"   No se pudo conectar al servidor {API_BASE_URL}")
        print(f"   Error: {str(e)}")
        print(f"\n   Verifica que:")
        print(f"   1. El servidor esté corriendo")
        print(f"   2. La URL sea correcta: {API_BASE_URL}")
        print(f"   3. No haya firewall bloqueando la conexión")
        return False, None

    except requests.exceptions.Timeout:
        print(f"\n❌ ERROR: Timeout")
        print(f"   El servidor no respondió en 10 segundos")
        return False, None

    except Exception as e:
        print(f"\n❌ ERROR INESPERADO:")
        print(f"   {type(e).__name__}: {str(e)}")
        return False, None


def test_with_access_token(access_token: str):
    """
    Prueba usar el access token para acceder a un endpoint protegido
    """
    print("\n" + "=" * 70)
    print("PRUEBA DE ACCESS TOKEN")
    print("=" * 70)

    # Intentar acceder a un endpoint protegido (ejemplo: /planchas/disponibles)
    test_url = f"{API_BASE_URL}/planchas/disponibles"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    try:
        print(f"\n📤 Probando endpoint protegido: {test_url}")
        response = requests.get(test_url, headers=headers, timeout=10)

        print(f"📥 Status Code: {response.status_code}")

        if response.status_code == 200:
            print("✅ Token válido - Acceso autorizado")
            data = response.json()
            print(f"   Datos recibidos: {len(data)} registro(s)")
        else:
            print(f"⚠️  Status: {response.status_code}")
            print(f"   Respuesta: {response.text[:200]}")

    except Exception as e:
        print(f"❌ Error al probar token: {str(e)}")


def main():
    """
    Ejecuta las pruebas de autenticación
    """
    print("\n🚀 INICIANDO PRUEBAS DE AUTENTICACIÓN LDAP VIA API")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Probar /auth/login
    success_login, data_login = test_auth_endpoint("/auth/login")

    print("\n" + "=" * 70)

    # Probar /auth/ldap
    success_ldap, data_ldap = test_auth_endpoint("/auth/ldap")

    # Si alguno fue exitoso, probar el access token
    if success_login and data_login and "access_token" in data_login:
        test_with_access_token(data_login["access_token"])
    elif success_ldap and data_ldap and "access_token" in data_ldap:
        test_with_access_token(data_ldap["access_token"])

    # Resumen final
    print("\n" + "=" * 70)
    print("RESUMEN DE PRUEBAS")
    print("=" * 70)
    print(f"/auth/login: {'✅ EXITOSO' if success_login else '❌ FALLIDO'}")
    print(f"/auth/ldap:  {'✅ EXITOSO' if success_ldap else '❌ FALLIDO'}")
    print("=" * 70)

    return success_login or success_ldap


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
