from PySide6.QtWidgets import (QWidget, QTabWidget, QFormLayout, QGroupBox,
                               QLineEdit, QVBoxLayout, QSpacerItem, QSizePolicy)
from PySide6.QtCore import Signal


class ConfigTabsWidget(QWidget):
    def __init__(self, config_service):
        super().__init__()
        self.config_service = config_service
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        # Crear tabs
        self.tab_widget = QTabWidget()

        # Tabs individuales
        self.device_tab = self.create_device_tab()
        self.cameras_tab = self.create_cameras_tab()
        self.api_tab = self.create_api_tab()
        self.ldap_tab = self.create_ldap_tab()

        self.tab_widget.addTab(self.device_tab, "📱 Dispositivo")
        self.tab_widget.addTab(self.cameras_tab, "📷 Cámaras")
        self.tab_widget.addTab(self.api_tab, "🌐 API Server")
        self.tab_widget.addTab(self.ldap_tab, "🔐 LDAP")

        layout.addWidget(self.tab_widget)
        self.setLayout(layout)

    def create_device_tab(self):
        """Crear tab de configuración de dispositivo"""
        widget = QWidget()
        layout = QVBoxLayout()

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

    def get_config_data(self):
        """Obtener datos de configuración de todos los tabs"""
        return {
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

    def load_config_data(self, config):
        """Cargar datos en los campos"""
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

    def get_required_fields(self):
        """Obtener diccionario de campos requeridos para validación"""
        return {
            'ID de Tablet': self.tablet_id_input.text(),
            'Plancha': self.plancha_input.text(),
            'Servidor API': self.api_server_input.text(),
            'Servidor LDAP': self.ldap_server_input.text(),
            'Dominio LDAP': self.ldap_domain_input.text()
        }

    def clear_all_fields(self):
        """Limpiar todos los campos"""
        self.tablet_id_input.clear()
        self.plancha_input.clear()
        self.camera1_ip_input.clear()
        self.camera2_ip_input.clear()
        self.api_server_input.clear()
        self.ldap_server_input.clear()
        self.ldap_port_input.setText("389")
        self.ldap_domain_input.clear()
