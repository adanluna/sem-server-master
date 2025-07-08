from PySide6.QtWidgets import QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, QMessageBox, QScrollArea, QGridLayout
from PySide6.QtCore import Qt
from services.utils import load_stylesheet


class ConfigWindow(QWidget):
    def __init__(self, config_service):
        super().__init__()
        self.config_service = config_service
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Configuración del Sistema")
        self.resize(600, 400)

        # Layout principal con más espacio para el botón
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)  # Reducido un poco
        main_layout.setContentsMargins(20, 20, 20, 30)  # Más margen inferior

        # Título principal (que se oculta desde ConfigPageWrapper)
        title_label = QLabel("Configuración del Sistema")
        title_label.setProperty("class", "main-title")
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)

        # Crear scroll area para el contenido del formulario
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setMinimumHeight(400)  # Altura mínima para el scroll

        # Widget de contenido del scroll
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(15)
        scroll_layout.setContentsMargins(10, 10, 10, 20)  # Márgenes internos

        # Inputs
        self.input_planch = QLineEdit()
        self.input_camera1 = QLineEdit()
        self.input_camera2 = QLineEdit()
        self.input_api = QLineEdit()
        self.input_ldap_server = QLineEdit()
        self.input_ldap_port = QLineEdit()
        self.input_ldap_domain = QLineEdit()

        # Layout de 2 columnas
        grid_layout = QGridLayout()
        grid_layout.setSpacing(15)
        grid_layout.setColumnStretch(0, 1)
        grid_layout.setColumnStretch(1, 1)

        # COLUMNA IZQUIERDA - Configuración de Plancha
        row = 0

        plancha_title = QLabel("Configuración de Plancha")
        plancha_title.setProperty("class", "section-title")
        grid_layout.addWidget(plancha_title, row, 0)
        row += 1

        grid_layout.addWidget(QLabel("Nombre de Plancha:"), row, 0)
        grid_layout.addWidget(self.input_planch, row + 1, 0)
        row += 2

        grid_layout.addWidget(QLabel("IP Cámara 1:"), row, 0)
        grid_layout.addWidget(self.input_camera1, row + 1, 0)
        row += 2

        grid_layout.addWidget(QLabel("IP Cámara 2:"), row, 0)
        grid_layout.addWidget(self.input_camera2, row + 1, 0)
        row += 2

        grid_layout.addWidget(QLabel("IP API Server:"), row, 0)
        grid_layout.addWidget(self.input_api, row + 1, 0)

        # COLUMNA DERECHA - Configuración LDAP
        row = 0

        ldap_title = QLabel("Configuración LDAP")
        ldap_title.setProperty("class", "section-title")
        grid_layout.addWidget(ldap_title, row, 1)
        row += 1

        grid_layout.addWidget(QLabel("Servidor LDAP:"), row, 1)
        grid_layout.addWidget(self.input_ldap_server, row + 1, 1)
        row += 2

        grid_layout.addWidget(QLabel("Puerto LDAP:"), row, 1)
        grid_layout.addWidget(self.input_ldap_port, row + 1, 1)
        row += 2

        grid_layout.addWidget(QLabel("Dominio LDAP:"), row, 1)
        grid_layout.addWidget(self.input_ldap_domain, row + 1, 1)

        # Agregar grid al layout del scroll
        scroll_layout.addLayout(grid_layout)
        scroll_layout.addStretch()  # Espacio adicional al final

        # Configurar el scroll
        scroll.setWidget(scroll_content)

        # Espaciador entre scroll y botón
        spacer_layout = QVBoxLayout()
        spacer_layout.addSpacing(20)  # 20px de espacio

        # Botón guardar FUERA del scroll area con más espacio
        btn_save = QPushButton("Guardar")
        btn_save.setProperty("class", "action-button")
        btn_save.setFixedSize(120, 40)
        btn_save.clicked.connect(self.save)

        # Layout del botón centrado con más margen
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 15, 0, 15)  # Margen arriba y abajo
        button_layout.addStretch()
        button_layout.addWidget(btn_save)
        button_layout.addStretch()

        # Agregar todo al layout principal
        # El scroll toma la mayor parte (stretch=1)
        main_layout.addWidget(scroll, 1)
        main_layout.addSpacing(10)  # Espacio antes del botón
        main_layout.addLayout(button_layout, 0)  # El botón sin stretch

        self.setLayout(main_layout)

        # Aplicar estilos
        load_stylesheet(self)

        # Cargar configuración existente
        self.load_config()

    def load_config(self):
        """Cargar configuración desde config.enc"""
        try:
            config = self.config_service.load_config()
            if config:
                # Configuración existente
                self.input_planch.setText(config.get('planch', ''))
                self.input_camera1.setText(config.get('camera1', ''))
                self.input_camera2.setText(config.get('camera2', ''))
                self.input_api.setText(config.get('api', ''))

                # Configuración LDAP
                self.input_ldap_server.setText(config.get('ldap_server', ''))
                self.input_ldap_port.setText(
                    str(config.get('ldap_port', '389')))
                self.input_ldap_domain.setText(config.get('ldap_domain', ''))

                print("✅ Configuración cargada desde config.enc")
            else:
                # Valores por defecto
                self.input_ldap_port.setText('389')
                print(
                    "⚠️ No se encontró configuración en config.enc - usando valores por defecto")
        except Exception as e:
            print(f"❌ Error cargando configuración: {e}")
            # Valores por defecto en caso de error
            self.input_ldap_port.setText('389')

    def save(self):
        """Guardar configuración en config.enc"""
        try:
            data = {
                'planch': self.input_planch.text(),
                'camera1': self.input_camera1.text(),
                'camera2': self.input_camera2.text(),
                'api': self.input_api.text(),
                'ldap_server': self.input_ldap_server.text(),
                'ldap_port': self.input_ldap_port.text(),
                'ldap_domain': self.input_ldap_domain.text()
            }

            self.config_service.save_config(data)
            QMessageBox.information(
                self, "Guardado", "Configuración guardada exitosamente.")
            print("✅ Configuración guardada en config.enc")

        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Error guardando configuración: {str(e)}")
            print(f"❌ Error guardando configuración: {e}")
