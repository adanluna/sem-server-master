
import os
import logging

logging.basicConfig(filename="app.log", level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_stylesheet(widget):
    try:
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        styles_path = os.path.join(root_dir, "styles.qss")
        with open(styles_path, "r") as f:
            widget.setStyleSheet(f.read())
            logging.info(f"✅ Estilos cargados correctamente en {widget.__class__.__name__}")
    except FileNotFoundError:
        logging.warning(f"❌ Archivo styles.qss no encontrado en: {styles_path}")
