import os


def load_stylesheet(widget):
    """Cargar estilos desde styles.qss"""
    try:
        # ✅ Buscar styles.qss en el directorio actual
        styles_path = os.path.join(os.getcwd(), "styles.qss")

        if os.path.exists(styles_path):
            with open(styles_path, "r", encoding="utf-8") as f:
                stylesheet = f.read()
                widget.setStyleSheet(stylesheet)
                print("✅ Estilos cargados desde styles.qss")
                return True
        else:
            print(f"⚠️ Archivo styles.qss no encontrado en: {styles_path}")
            return False

    except Exception as e:
        print(f"⚠️ Error cargando estilos: {e}")
        return False
