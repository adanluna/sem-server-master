import shutil
import os

# Copiar styles.qss desde el directorio raíz
source = "../styles.qss"
destination = "styles.qss"

try:
    shutil.copy2(source, destination)
    print("✅ styles.qss copiado correctamente")
except FileNotFoundError:
    print("❌ No se encontró styles.qss en el directorio padre")
except Exception as e:
    print(f"❌ Error copiando styles.qss: {e}")
