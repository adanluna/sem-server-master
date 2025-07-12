import json
import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QMessageBox, QTabWidget, QFormLayout,
    QGroupBox, QSpacerItem, QSizePolicy, QApplication
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from services.utils import load_stylesheet


class ConfigWindow(QWidget):
    def __init__(self, config_service):
        """Inicializar ventana de configuración"""
        super().__init__()
        self.config_service = config_service

        self.setWindowTitle("⚙️ Configuración del Sistema")
        self.setFixedSize(800, 600)
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint)

        # Centrar en pantalla
        self.center_window()

        # Configurar UI
        self.setup_ui()

        # Cargar configuración actual
        self.load_current_config()

    def center_window(self):
        """Centrar ventana en la pantalla"""
        screen = QApplication.primaryScreen().geometry()
        window = self.geometry()
        x = (screen.width() - window.width()) // 2
        y = (screen.height() - window.height()) // 2
        self.move(x, y)

    def setup_ui(self):
        """Configurar la interfaz de usuario"""
        layout = QVBoxLayout()

        # Título
        title_label = QLabel("⚙️ Configuración del Sistema SEMEFO")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #2c3e50; margin: 20px;")
        layout.addWidget(title_label)

        # Crear tabs
        self.tab_widget = QTabWidget()

        # Tab 1: Configuración de Dispositivo
        self.device_tab = self.create_device_tab()
        self.tab_widget.addTab(self.device_tab, "📱 Dispositivo")

        # Tab 2: Configuración de Cámaras
        self.cameras_tab = self.create_cameras_tab()
        self.tab_widget.addTab(self.cameras_tab, "📷 Cámaras")

        # Tab 3: Configuración de API
        self.api_tab = self.create_api_tab()
        self.tab_widget.addTab(self.api_tab, "🌐 API Server")

        # Tab 4: Configuración de LDAP
        self.ldap_tab = self.create_ldap_tab()
        self.tab_widget.addTab(self.ldap_tab, "🔐 LDAP")

        layout.addWidget(self.tab_widget)

        # Botones
        button_layout = QHBoxLayout()

        # Spacer
        button_layout.addItem(QSpacerItem(
            40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        # Botón Guardar
        self.save_button = QPushButton("💾 Guardar Configuración")
        self.save_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #219a52;
            }
        """)
        self.save_button.clicked.connect(self.save_config)
        button_layout.addWidget(self.save_button)

        # Botón Cancelar
        self.cancel_button = QPushButton("❌ Cancelar")
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        self.cancel_button.clicked.connect(self.close)
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def create_device_tab(self):
        """Crear tab de configuración de dispositivo"""
        widget = QWidget()
        layout = QVBoxLayout()

        # Grupo Dispositivo
        device_group = QGroupBox("Identificación del Dispositivo")
        device_layout = QFormLayout()

        self.tablet_id_input = QLineEdit()
        self.tablet_id_input.setPlaceholderText("Ej: Tablet-001")
        device_layout.addRow("📱 ID de Tablet:", self.tablet_id_input)

        self.plancha_input = QLineEdit()
        self.plancha_input.setPlaceholderText("Ej: Plancha-A")
        device_layout.addRow("🏥 Plancha:", self.plancha_input)

        device_group.setLayout(device_layout)
        layout.addWidget(device_group)

        layout.addItem(QSpacerItem(
            20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        widget.setLayout(layout)
        return widget

    def create_cameras_tab(self):
        """Crear tab de configuración de cámaras"""
        widget = QWidget()
        layout = QVBoxLayout()

        # Grupo Cámaras
        cameras_group = QGroupBox("Direcciones IP de las Cámaras")
        cameras_layout = QFormLayout()

        self.camera1_ip_input = QLineEdit()
        self.camera1_ip_input.setPlaceholderText("Ej: 192.168.1.100")
        cameras_layout.addRow("📷 Cámara 1 IP:", self.camera1_ip_input)

        self.camera2_ip_input = QLineEdit()
        self.camera2_ip_input.setPlaceholderText("Ej: 192.168.1.101")
        cameras_layout.addRow("📷 Cámara 2 IP:", self.camera2_ip_input)

        cameras_group.setLayout(cameras_layout)
        layout.addWidget(cameras_group)

        layout.addItem(QSpacerItem(
            20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        widget.setLayout(layout)
        return widget

    def create_api_tab(self):
        """Crear tab de configuración de API"""
        widget = QWidget()
        layout = QVBoxLayout()

        # Grupo API
        api_group = QGroupBox("Servidor de API")
        api_layout = QFormLayout()

        self.api_server_input = QLineEdit()
        self.api_server_input.setPlaceholderText("Ej: 192.168.1.220:8000")
        api_layout.addRow("🌐 Servidor API:", self.api_server_input)

        api_group.setLayout(api_layout)
        layout.addWidget(api_group)

        layout.addItem(QSpacerItem(
            20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        widget.setLayout(layout)
        return widget

    def create_ldap_tab(self):
        """Crear tab de configuración de LDAP"""
        widget = QWidget()
        layout = QVBoxLayout()

        # Grupo LDAP
        ldap_group = QGroupBox("Servidor LDAP (Active Directory)")
        ldap_layout = QFormLayout()

        self.ldap_server_input = QLineEdit()
        self.ldap_server_input.setPlaceholderText("Ej: 192.168.1.211")
        ldap_layout.addRow("🖥️ Servidor LDAP:", self.ldap_server_input)

        self.ldap_port_input = QLineEdit()
        self.ldap_port_input.setPlaceholderText("389")
        self.ldap_port_input.setText("389")
        ldap_layout.addRow("🔌 Puerto LDAP:", self.ldap_port_input)

        self.ldap_domain_input = QLineEdit()
        self.ldap_domain_input.setPlaceholderText("Ej: empresa.local")
        ldap_layout.addRow("🌐 Dominio:", self.ldap_domain_input)

        ldap_group.setLayout(ldap_layout)
        layout.addWidget(ldap_group)

        layout.addItem(QSpacerItem(
            20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        widget.setLayout(layout)
        return widget

    def load_current_config(self):
        """Cargar la configuración actual en los campos"""
        try:
            config = self.config_service.load_config()
            if not config:
                return

            # Cargar dispositivo
            device_config = config.get('dispositivo', {})
            self.tablet_id_input.setText(device_config.get('tablet_id', ''))
            self.plancha_input.setText(device_config.get('plancha', ''))

            # Cargar cámaras
            cameras_config = config.get('camaras', {})
            self.camera1_ip_input.setText(cameras_config.get('camera1_ip', ''))
            self.camera2_ip_input.setText(cameras_config.get('camera2_ip', ''))

            # Cargar API
            api_config = config.get('api', {})
            self.api_server_input.setText(api_config.get('server_ip', ''))

            # Cargar LDAP
            ldap_config = config.get('ldap', {})
            self.ldap_server_input.setText(ldap_config.get('server', ''))
            self.ldap_port_input.setText(str(ldap_config.get('port', '389')))
            self.ldap_domain_input.setText(ldap_config.get('domain', ''))

        except Exception as e:
            logging.error(f"Error cargando configuración: {e}")
            QMessageBox.warning(
                self, "Error", f"Error cargando configuración: {str(e)}")

    def save_config(self):
        """Guardar la configuración"""
        try:
            # Validar campos requeridos
            if not self.tablet_id_input.text().strip():
                QMessageBox.warning(self, "Campo requerido",
                                    "El ID de Tablet es requerido")
                return

            if not self.plancha_input.text().strip():
                QMessageBox.warning(self, "Campo requerido",
                                    "La Plancha es requerida")
                return

            if not self.api_server_input.text().strip():
                QMessageBox.warning(self, "Campo requerido",
                                    "El Servidor API es requerido")
                return

            if not self.ldap_server_input.text().strip():
                QMessageBox.warning(self, "Campo requerido",
                                    "El Servidor LDAP es requerido")
                return

            if not self.ldap_domain_input.text().strip():
                QMessageBox.warning(self, "Campo requerido",
                                    "El Dominio LDAP es requerido")
                return

            # Crear estructura de configuración
            config = {
                'dispositivo': {
                    'tablet_id': self.tablet_id_input.text().strip(),
                    'plancha': self.plancha_input.text().strip()
                },
                'camaras': {
                    'camera1_ip': self.camera1_ip_input.text().strip(),
                    'camera2_ip': self.camera2_ip_input.text().strip()
                },
                'api': {
                    'server_ip': self.api_server_input.text().strip()
                },
                'ldap': {
                    'server': self.ldap_server_input.text().strip(),
                    'port': self.ldap_port_input.text().strip() or '389',
                    'domain': self.ldap_domain_input.text().strip()
                },
                'version': '1.0.0'
            }

            # Guardar configuración
            if self.config_service.save_config(config):
                QMessageBox.information(
                    self, "Éxito", "Configuración guardada correctamente")
                self.close()
            else:
                QMessageBox.critical(
                    self, "Error", "Error al guardar la configuración")

        except Exception as e:
            logging.error(f"Error guardando configuración: {e}")
            QMessageBox.critical(self, "Error", f"Error al guardar: {str(e)}")
