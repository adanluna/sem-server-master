#!/usr/bin/env python3
"""
Script de prueba para conexión LDAP
Prueba la autenticación con el servidor LDAP configurado
"""
import os
from ldap3 import Server, Connection, ALL
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Credenciales de prueba
TEST_USERNAME = "testuser1"
TEST_PASSWORD = "Test$2025!."


def test_ldap_connection():
    """
    Prueba la conexión y autenticación con el servidor LDAP
    """
    # Obtener configuración del entorno (con valores por defecto actualizados)
    LDAP_HOST = os.getenv("LDAP_SERVER_IP", "192.168.115.8")
    LDAP_PORT = int(os.getenv("LDAP_PORT", 389))
    LDAP_DOMAIN = os.getenv("LDAP_DOMAIN", "fiscalianl.gob")

    print("=" * 60)
    print("PRUEBA DE CONEXIÓN LDAP")
    print("=" * 60)
    print(f"Servidor LDAP: {LDAP_HOST}")
    print(f"Puerto: {LDAP_PORT}")
    print(f"Dominio: {LDAP_DOMAIN}")
    print(f"Usuario: {TEST_USERNAME}")
    print("=" * 60)

    if not LDAP_HOST or not LDAP_DOMAIN:
        print("❌ ERROR: Variables de entorno no configuradas")
        print("   Asegúrate de configurar LDAP_SERVER_IP y LDAP_DOMAIN")
        return False

    # Construir el User Principal Name (UPN)
    user_principal = f"{TEST_USERNAME}@{LDAP_DOMAIN}"
    print(f"\nIntentando autenticar: {user_principal}")
    print("-" * 60)

    try:
        # Conectar al servidor LDAP
        print("1. Conectando al servidor LDAP...")
        server = Server(LDAP_HOST, port=LDAP_PORT, get_info=ALL)
        print(f"   ✓ Servidor creado: {server}")

        # Crear conexión con autenticación SIMPLE
        print("\n2. Creando conexión con autenticación SIMPLE...")
        conn = Connection(
            server,
            user=user_principal,
            password=TEST_PASSWORD,
            authentication="SIMPLE",
            auto_bind=False
        )
        print("   ✓ Conexión creada")

        # Intentar TLS (opcional)
        print("\n3. Intentando establecer TLS...")
        try:
            conn.start_tls()
            print("   ✓ TLS establecido")
        except Exception as tls_error:
            print(f"   ⚠ TLS no disponible: {tls_error}")
            print("   → Continuando sin TLS...")

        # Realizar bind (autenticación)
        print("\n4. Autenticando usuario...")
        if not conn.bind():
            print("   ❌ Autenticación fallida")
            print(f"   Resultado: {conn.result}")
            return False

        print("   ✓ Autenticación exitosa!")

        # Buscar información del usuario
        print("\n5. Buscando información del usuario...")
        search_base = "DC=fiscalianl,DC=gob"

        conn.search(
            search_base,
            f"(sAMAccountName={TEST_USERNAME})",
            attributes=["displayName", "mail", "memberOf", "distinguishedName"]
        )

        if conn.entries:
            print(f"   ✓ Usuario encontrado: {len(conn.entries)} resultado(s)")
            print("\n   Información del usuario:")
            print("   " + "-" * 56)
            entry = conn.entries[0]

            if hasattr(entry, 'displayName') and entry.displayName:
                print(f"   Nombre: {entry.displayName}")

            if hasattr(entry, 'mail') and entry.mail:
                print(f"   Email: {entry.mail}")

            if hasattr(entry, 'distinguishedName') and entry.distinguishedName:
                print(f"   DN: {entry.distinguishedName}")

            if hasattr(entry, 'memberOf') and entry.memberOf:
                print(f"   Grupos: {len(entry.memberOf)} grupo(s)")
                for group in entry.memberOf:
                    # Extraer solo el nombre del grupo (CN)
                    group_name = str(group).split(',')[0].replace('CN=', '')
                    print(f"     - {group_name}")
        else:
            print("   ⚠ No se encontró información adicional del usuario")

        # Cerrar conexión
        print("\n6. Cerrando conexión...")
        conn.unbind()
        print("   ✓ Conexión cerrada")

        print("\n" + "=" * 60)
        print("✅ PRUEBA EXITOSA - Conexión LDAP funcionando correctamente")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\n❌ ERROR durante la prueba:")
        print(f"   {type(e).__name__}: {str(e)}")
        print("=" * 60)
        return False


if __name__ == "__main__":
    success = test_ldap_connection()
    exit(0 if success else 1)
