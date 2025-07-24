from celery.backends.database.models import Task, TaskSet
from worker.celery_app import celery_app
import time
import sys
import os

# Agregar path para importar worker
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))


def wait_for_db(max_retries=10, delay=2):
    """Esperar a que la base de datos esté disponible"""
    print("🔍 Verificando conexión a la base de datos...")

    for attempt in range(max_retries):
        try:
            backend = celery_app.backend

            # Forzar la inicialización del engine usando el backend
            backend.get_result('dummy-task-id')

            # Crear engine manualmente usando la URL del backend
            from sqlalchemy import create_engine
            engine = create_engine(backend.url)

            # Probar conexión
            with engine.connect() as conn:
                print("✅ Base de datos disponible")
                return engine

        except Exception as e:
            print(
                f"⏳ Intento {attempt + 1}/{max_retries}: Esperando base de datos... ({str(e)[:50]})")
            if attempt < max_retries - 1:
                time.sleep(delay)
            else:
                raise Exception(
                    f"❌ No se pudo conectar a la base de datos: {e}")


def crear_tablas_celery():
    print("🔧 Recreando tablas de Celery...")
    print("=" * 50)

    try:
        # Esperar a que la DB esté lista
        engine = wait_for_db()

        print(f"🔗 Conectado a: {engine.url}")

        print("\n📦 Creando tablas de Celery:")

        print("  → celery_taskmeta (resultados de tareas)...")
        Task.__table__.create(bind=engine, checkfirst=True)
        print("    ✅ Tabla celery_taskmeta creada")

        print("  → celery_tasksetmeta (grupos de tareas)...")
        TaskSet.__table__.create(bind=engine, checkfirst=True)
        print("    ✅ Tabla celery_tasksetmeta creada")

        print("\n🎉 ¡Tablas de Celery recreadas exitosamente!")

        # Verificar que las tablas existen
        print("\n🔍 Verificando tablas creadas...")
        with engine.connect() as conn:
            from sqlalchemy import text
            result = conn.execute(text(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename LIKE 'celery%'"
            ))
            tables = [row[0] for row in result]

            if tables:
                print("✅ Tablas encontradas:")
                for table in tables:
                    print(f"  - {table}")
            else:
                print("⚠️ No se encontraron tablas de Celery")

        return True

    except Exception as e:
        print(f"❌ Error creando tablas: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("🗃️ Script para recrear tablas de Celery")
    print("=" * 50)

    success = crear_tablas_celery()

    if success:
        print("\n✅ Proceso completado exitosamente")
        print("💡 Ahora puedes usar Celery normalmente")
    else:
        print("\n❌ El proceso falló")
        print("\n🔧 Posibles soluciones:")
        print("1. Verificar que PostgreSQL esté ejecutándose:")
        print("   docker-compose ps")
        print("2. Verificar configuración en .env:")
        print("   DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASS")
        print("3. Reiniciar servicios:")
        print("   docker-compose restart db")
        sys.exit(1)
