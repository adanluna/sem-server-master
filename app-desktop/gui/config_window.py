from PySide6.QtWidgets import QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, QMessageBox
from PySide6.QtCore import Qt


class ConfigWindow(QWidget):
    def __init__(self, config_service):
        super().__init__()
        self.config_service = config_service
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Configuración de la Plancha")
        self.resize(400, 300)

        # Hacer que la ventana aparezca al frente y se pueda mover
        self.setAttribute(Qt.WA_ShowWithoutActivating, False)
        self.setWindowFlags(
            Qt.Window | Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint)

        self.input_planch = QLineEdit()
        self.input_camera1 = QLineEdit()
        self.input_camera2 = QLineEdit()
        self.input_api = QLineEdit()

        btn_save = QPushButton("Guardar")
        btn_save.clicked.connect(self.save)

        # Layout principal con elementos centrados
        main_layout = QHBoxLayout()

        # Layout vertical para los elementos del formulario
        form_layout = QVBoxLayout()
        form_layout.setAlignment(Qt.AlignCenter)
        form_layout.setSpacing(15)  # Espaciado entre elementos

        # Agregar elementos al layout del formulario
        form_layout.addWidget(QLabel("Nombre de Plancha:"))
        form_layout.addWidget(self.input_planch)
        form_layout.addWidget(QLabel("IP Cámara 1:"))
        form_layout.addWidget(self.input_camera1)
        form_layout.addWidget(QLabel("IP Cámara 2:"))
        form_layout.addWidget(self.input_camera2)
        form_layout.addWidget(QLabel("IP API Server:"))
        form_layout.addWidget(self.input_api)
        form_layout.addWidget(btn_save)

        # Centrar el formulario en el layout principal
        main_layout.addStretch()
        main_layout.addLayout(form_layout)
        main_layout.addStretch()

        self.setLayout(main_layout)

        # Cargar estilos CSS desde la raíz del proyecto
        import os
        styles_path = os.path.join(os.path.dirname(
            __file__), "..", "..", "styles.qss")
        try:
            with open(styles_path, "r") as f:
                self.setStyleSheet(f.read())
                print("✅ Estilos cargados correctamente en ConfigWindow")
        except FileNotFoundError:
            print(f"❌ Archivo de estilos no encontrado en: {styles_path}")

        config = self.config_service.load_config()
        if config:
            self.input_planch.setText(config.get('planch', ''))
            self.input_camera1.setText(config.get('camera1', ''))
            self.input_camera2.setText(config.get('camera2', ''))
            self.input_api.setText(config.get('api', ''))

    def save(self):
        data = {
            'planch': self.input_planch.text(),
            'camera1': self.input_camera1.text(),
            'camera2': self.input_camera2.text(),
            'api': self.input_api.text()
        }
        self.config_service.save_config(data)
        QMessageBox.information(
            self, "Guardado", "Configuración guardada exitosamente.")
        self.close()
