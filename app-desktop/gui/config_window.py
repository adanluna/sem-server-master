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
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content_widget = QWidget()
        self.input_tablet_id = QLineEdit()
        self.input_planch = QLineEdit()
        self.input_camera1 = QLineEdit()
        self.input_camera2 = QLineEdit()
        self.input_api = QLineEdit()
        self.input_ldap_server = QLineEdit()
        self.input_ldap_port = QLineEdit()
        self.input_ldap_domain = QLineEdit()
        btn_save = QPushButton("Guardar")
        btn_save.setProperty("class", "action-button")
        btn_save.setFixedSize(120, 40)
        btn_save.clicked.connect(self.save)
        main_layout = QVBoxLayout()
        main_layout.setSpacing(20)
        grid_layout = QGridLayout()
        grid_layout.setSpacing(15)
        grid_layout.setColumnStretch(0, 1)
        grid_layout.setColumnStretch(1, 1)
        row = 0
        tablet_title = QLabel("Configuración del Dispositivo")
        tablet_title.setProperty("class", "section-title")
        grid_layout.addWidget(tablet_title, row, 0)
        row += 1
        grid_layout.addWidget(
            QLabel("Nombre de la Tablet:"), row, 0)
        grid_layout.addWidget(self.input_tablet_id, row + 1, 0)
        row += 2
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
        main_layout.addLayout(grid_layout)
        main_layout.addStretch()
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(btn_save)
        button_layout.addStretch()
        main_layout.addLayout(button_layout)
        content_widget.setLayout(main_layout)
        scroll.setWidget(content_widget)
        window_layout = QVBoxLayout()
        window_layout.addWidget(scroll)
        self.setLayout(window_layout)
        load_stylesheet(self)
        self.load_config()

    def load_config(self):
        """Cargar configuración desde config.json"""
        try:
            config = self.config_service.load_config()
            if config:
                # Configuración del dispositivo
                dispositivo = config.get('dispositivo', {})
                self.input_tablet_id.setText(dispositivo.get('tablet_id', ''))
                self.input_planch.setText(dispositivo.get('plancha', ''))

                # Configuración de cámaras
                camaras = config.get('camaras', {})
                self.input_camera1.setText(camaras.get('camera1_ip', ''))
                self.input_camera2.setText(camaras.get('camera2_ip', ''))

                # Configuración de API
                api = config.get('api', {})
                self.input_api.setText(api.get('server_ip', ''))

                # Configuración LDAP - CORREGIR LAS CLAVES
                ldap = config.get('ldap', {})
                self.input_ldap_server.setText(ldap.get('server', ''))
                self.input_ldap_port.setText(str(ldap.get('port', '389')))
                self.input_ldap_domain.setText(ldap.get('domain', ''))

                print("✅ Configuración cargada desde config.json")
            else:
                # Valores por defecto
                self.input_ldap_port.setText('389')
                print("⚠️ Usando valores por defecto")
        except Exception as e:
            print(f"❌ Error cargando configuración: {e}")
            self.input_ldap_port.setText('389')

    def save(self):
        """Guardar configuración en config.json"""
        try:
            data = {
                "dispositivo": {
                    "tablet_id": self.input_tablet_id.text(),
                    "plancha": self.input_planch.text()
                },
                "camaras": {
                    "camera1_ip": self.input_camera1.text(),
                    "camera2_ip": self.input_camera2.text()
                },
                "api": {
                    "server_ip": self.input_api.text()
                },
                "ldap": {
                    "server": self.input_ldap_server.text(),
                    "port": self.input_ldap_port.text(),
                    "domain": self.input_ldap_domain.text()
                },
                "version": "1.0.0"
            }

            if self.config_service.save_config(data):
                QMessageBox.information(
                    self, "Guardado", "Configuración guardada exitosamente.")
                print("✅ Configuración guardada en config.json")
            else:
                QMessageBox.critical(
                    self, "Error", "Error guardando configuración.")
        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Error guardando configuración: {str(e)}")
            print(f"❌ Error guardando configuración: {e}")
