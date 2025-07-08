from PySide6.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QMessageBox
from PySide6.QtCore import Qt
import logging
from gui.base_window import BaseWindowWithHeader

logging.basicConfig(filename="app.log", level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


class SuccessWindow(BaseWindowWithHeader):
    def __init__(self, medico_nombre, numero_expediente, nombre_sesion, duracion, config_service):
        super().__init__(
            medico_nombre=medico_nombre,
            numero_expediente=numero_expediente,
            nombre_sesion=nombre_sesion,
            config_service=config_service,
            window_title="SEMEFO - Grabación Completada"
        )
        self.duracion = duracion
        self.init_ui()

    def init_ui(self):
        # Crear contenido
        content_widget = self.create_success_content()
        
        # Usar método de la clase base
        self.setup_content(content_widget)

    def create_success_content(self):
        """Crear el contenido de la ventana de éxito"""
        content = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)  # Márgenes para el contenido
        
        # Título de éxito
        success_label = QLabel("✅ Grabación completada exitosamente")
        success_label.setAlignment(Qt.AlignCenter)
        success_label.setProperty("class", "main-title")
        success_label.setStyleSheet("color: #28a745; font-size: 24px; font-weight: bold; margin: 20px;")
        
        # Detalles de la grabación
        details_text = f"""
        <div style="text-align: center; font-size: 16px; color: #333;">
            <p><strong>Expediente:</strong> {self.numero_expediente}</p>
            <p><strong>Sesión:</strong> {self.nombre_sesion}</p>
            <p><strong>Duración:</strong> {self.duracion}</p>
            <p><strong>Médico:</strong> {self.medico_nombre}</p>
        </div>
        """
        
        details_label = QLabel(details_text)
        details_label.setAlignment(Qt.AlignCenter)
        details_label.setTextFormat(Qt.RichText)
        details_label.setStyleSheet("margin: 20px;")
        
        # Mensaje adicional
        message_label = QLabel("La grabación ha sido guardada correctamente en el sistema.")
        message_label.setAlignment(Qt.AlignCenter)
        message_label.setStyleSheet("font-size: 14px; color: #666; margin: 10px;")
        
        # Botón terminar
        terminar_btn = QPushButton("Terminar Sesión")
        terminar_btn.setProperty("class", "action-button")
        terminar_btn.setFixedSize(200, 50)
        terminar_btn.clicked.connect(self.logout)
        
        # Botón nueva grabación (opcional)
        nueva_btn = QPushButton("Nueva Grabación")
        nueva_btn.setProperty("class", "cancel-button")
        nueva_btn.setFixedSize(200, 50)
        nueva_btn.clicked.connect(self.nueva_grabacion)
        
        # Layout de botones
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(nueva_btn)
        button_layout.addWidget(terminar_btn)
        button_layout.addStretch()
        
        # Agregar todo al layout
        layout.addStretch()
        layout.addWidget(success_label)
        layout.addWidget(details_label)
        layout.addWidget(message_label)
        layout.addStretch()
        layout.addLayout(button_layout)
        layout.addStretch()
        
        content.setLayout(layout)
        return content

    def nueva_grabacion(self):
        """Ir a una nueva grabación manteniendo la sesión"""
        try:
            from gui.expediente_window import ExpedienteWindow
            self.expediente_window = ExpedienteWindow(
                medico_nombre=self.medico_nombre,
                config_service=self.config_service
            )
            self.expediente_window.show()
            self.close()
            logging.info(f"Iniciando nueva grabación para {self.medico_nombre}")
        except Exception as e:
            logging.error(f"Error abriendo nueva grabación: {e}")
            QMessageBox.critical(self, "Error", f"Error al abrir nueva grabación: {str(e)}")

    def logout(self):
        """Terminar sesión y volver al login"""
        try:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Terminar Sesión")
            msg_box.setText(f"¿Está seguro que desea terminar la sesión de {self.medico_nombre}?")
            msg_box.setIcon(QMessageBox.Question)
            
            yes_button = msg_box.addButton("Sí", QMessageBox.YesRole)
            yes_button.setProperty("class", "action-button")
            
            no_button = msg_box.addButton("No", QMessageBox.NoRole)
            no_button.setProperty("class", "cancel-button")
            
            msg_box.setDefaultButton(no_button)
            
            # Aplicar estilos al mensaje
            from services.utils import load_stylesheet
            load_stylesheet(msg_box)
            
            reply = msg_box.exec()
            
            if msg_box.clickedButton() == yes_button:
                logging.info(f"Usuario {self.medico_nombre} terminó sesión desde SuccessWindow")
                
                from gui.login_window import LoginWindow
                self.login_window = LoginWindow(self.config_service)
                self.login_window.show()
                self.close()
                
        except Exception as e:
            logging.error(f"Error en logout desde SuccessWindow: {e}")
            QMessageBox.critical(self, "Error", f"Error al cerrar sesión: {str(e)}")
