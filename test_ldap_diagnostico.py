#!/usr/bin/env python3
"""
Script de diagnóstico completo para LDAP
Verifica configuración del servidor y prueba autenticación
"""
import requests
import json
from datetime import datetime

# Configuración
API_BASE_URL = "http://172.21.82.2:8000"
USERNAME = "testuser1"
PASSWORD = "T3st$2025FG!."


def check_server_health():
    """
    Verifica que el servidor API esté respondiendo
    """
    print("=" * 70)
    print("1. VERIFICANDO SALUD DEL SERVIDOR")
    print("=" * 70)

    try:
        response = requests.get(f"{API_BASE_URL}/docs", timeout=5)
        print(f"✅ Servidor respondiendo (Status: {response.status_code})")
        return True
    except Exception as e:
        print(f"❌ Servidor no responde: {str(e)}")
        return False


def check_ldap_config():
    """
    Intenta obtener información sobre la configuración LDAP del servidor
    Esto nos ayudará a ver si las variables de entorno están configuradas
    """
    print("\n" + "=" * 70)
    print("2. VERIFICANDO CONFIGURACIÓN LDAP EN EL SERVIDOR")
    print("=" * 70)

    # Intentamos hacer login con credenciales inválidas para ver el error
    url = f"{API_BASE_URL}/auth/login"

    # Primero con credenciales obviamente incorrectas
    payload = {"username": "test_invalid_user_12345", "password": "invalid"}

    try:
        response = requests.post(url, json=payload, timeout=10)

        if response.status_code == 401:
            data = response.json()
            error_msg = data.get("detail", "")

            print(f"\n📋 Mensaje de error del servidor:")
            print(f"   {error_msg}")

            # Analizar el mensaje de error
            if "Configuración LDAP incompleta" in error_msg:
                print("\n❌ PROBLEMA DETECTADO:")
                print(
                    "   Las variables de entorno LDAP NO están configuradas en el contenedor")
                print("\n   Variables faltantes en el mensaje:")
                print(f"   {error_msg}")
                return False
            elif "invalidCredentials" in error_msg or "Credenciales inválidas" in error_msg:
                print("\n✅ Configuración LDAP parece estar OK")
                print("   El servidor está intentando autenticar contra LDAP")
                return True
            elif "Error LDAP" in error_msg:
                print(f"\n⚠️  Error de conexión LDAP:")
                print(f"   {error_msg}")
                return False
            else:
                print(f"\n⚠️  Respuesta inesperada: {error_msg}")
                return None

    except Exception as e:
        print(f"❌ Error en prueba: {str(e)}")
        return None


def test_authentication():
    """
    Prueba la autenticación con las credenciales reales
    """
    print("\n" + "=" * 70)
    print("3. PROBANDO AUTENTICACIÓN CON CREDENCIALES")
    print("=" * 70)

    url = f"{API_BASE_URL}/auth/ldap"

    payload = {
        "username": USERNAME,
        "password": PASSWORD
    }

    print(f"\n🔐 Intentando autenticar:")
    print(f"   URL: {url}")
    print(f"   Usuario: {USERNAME}")
    print(f"   Password: {'*' * len(PASSWORD)}")

    try:
        response = requests.post(url, json=payload, timeout=10)

        print(f"\n📥 Respuesta:")
        print(f"   Status Code: {response.status_code}")

        data = response.json()
        print(
            f"   Contenido: {json.dumps(data, indent=2, ensure_ascii=False)}")

        if response.status_code == 200:
            print("\n✅ AUTENTICACIÓN EXITOSA")
            return True, data
        else:
            print("\n❌ AUTENTICACIÓN FALLIDA")

            error_detail = data.get("detail", "")

            # Análisis del error
            if "invalidCredentials" in error_detail:
                print("\n🔍 ANÁLISIS DEL ERROR:")
                print("   - El servidor LDAP rechazó las credenciales")
                print("   - Posibles causas:")
                print("     1. Usuario o contraseña incorrectos")
                print("     2. El usuario no existe en el dominio 'fiscalianl.gob'")
                print("     3. La cuenta está bloqueada o deshabilitada")
                print("     4. El formato del username es incorrecto")
                print(
                    f"\n   Usuario que se está intentando: {USERNAME}@fiscalianl.gob")

            return False, data

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return False, None


def suggest_next_steps(ldap_configured, auth_success):
    """
    Sugiere los siguientes pasos basados en los resultados
    """
    print("\n" + "=" * 70)
    print("4. DIAGNÓSTICO Y RECOMENDACIONES")
    print("=" * 70)

    if not ldap_configured:
        print("\n❌ PROBLEMA: Variables LDAP no configuradas en el contenedor")
        print("\n📝 SOLUCIÓN:")
        print("   1. Verifica que el archivo .env tenga:")
        print("      LDAP_SERVER_IP=192.168.115.8")
        print("      LDAP_PORT=389")
        print("      LDAP_DOMAIN=fiscalianl.gob")
        print("\n   2. Reinicia el contenedor:")
        print("      docker-compose restart fastapi")
        print("\n   3. Verifica que las variables estén en el contenedor:")
        print("      docker exec fastapi_app env | grep LDAP")

    elif not auth_success:
        print("\n⚠️  PROBLEMA: Credenciales rechazadas por LDAP")
        print("\n📝 PASOS PARA VERIFICAR:")
        print("\n   1. Verifica las credenciales en Active Directory:")
        print(f"      - Usuario: {USERNAME}")
        print(f"      - Dominio: fiscalianl.gob")
        print(f"      - UPN completo: {USERNAME}@fiscalianl.gob")

        print("\n   2. Prueba conectividad desde el contenedor al servidor LDAP:")
        print("      docker exec fastapi_app ping -c 3 192.168.115.8")
        print("      docker exec fastapi_app nc -zv 192.168.115.8 389")

        print("\n   3. Revisa los logs del contenedor:")
        print("      docker logs fastapi_app | grep -i ldap")

        print("\n   4. Verifica en el servidor AD que:")
        print("      - El usuario existe")
        print("      - La cuenta no está bloqueada")
        print("      - La contraseña es correcta")
        print("      - El usuario puede hacer login")

    else:
        print("\n✅ TODO FUNCIONANDO CORRECTAMENTE")


def main():
    print("\n🔍 DIAGNÓSTICO COMPLETO DE LDAP")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # 1. Verificar servidor
    server_ok = check_server_health()
    if not server_ok:
        print("\n❌ No se puede continuar sin conexión al servidor")
        return False

    # 2. Verificar configuración LDAP
    ldap_configured = check_ldap_config()

    # 3. Probar autenticación
    auth_success, data = test_authentication()

    # 4. Sugerencias
    suggest_next_steps(ldap_configured, auth_success)

    print("\n" + "=" * 70)

    return auth_success


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
