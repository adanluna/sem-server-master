import pyaudio
import wave
import threading
import time
from PySide6.QtCore import QObject, Signal
import logging


class AudioRecorder(QObject):
    """Servicio para grabar audio usando PyAudio"""

    # Señales para comunicar estados
    recording_started = Signal()
    recording_stopped = Signal()
    recording_error = Signal(str)
    audio_level_changed = Signal(float)  # Para mostrar niveles de audio

    def __init__(self):
        super().__init__()
        self.is_recording = False
        self.audio_thread = None
        self.frames = []

        # Configuración de audio por defecto
        self.chunk = 1024
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 44100

        self.audio = None
        self.stream = None

    def initialize_audio(self):
        """Inicializar PyAudio"""
        try:
            self.audio = pyaudio.PyAudio()
            return True
        except Exception as e:
            logging.error(f"Error inicializando audio: {e}")
            self.recording_error.emit(f"Error inicializando audio: {e}")
            return False

    def start_recording(self, filename):
        """Iniciar grabación de audio"""
        if self.is_recording:
            logging.warning("Ya se está grabando audio")
            return False

        if not self.initialize_audio():
            return False

        try:
            self.filename = filename
            self.frames = []
            self.is_recording = True

            # Crear stream de audio
            self.stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.rate,
                input=True,
                frames_per_buffer=self.chunk
            )

            # Iniciar hilo de grabación
            self.audio_thread = threading.Thread(target=self._record_audio)
            self.audio_thread.daemon = True
            self.audio_thread.start()

            self.recording_started.emit()
            logging.info(f"Iniciando grabación: {filename}")
            return True

        except Exception as e:
            logging.error(f"Error iniciando grabación: {e}")
            self.recording_error.emit(f"Error iniciando grabación: {e}")
            self.cleanup()
            return False

    def stop_recording(self):
        """Detener grabación de audio"""
        if not self.is_recording:
            logging.warning("No se está grabando audio")
            return False

        try:
            self.is_recording = False

            # Esperar a que termine el hilo de grabación
            if self.audio_thread and self.audio_thread.is_alive():
                self.audio_thread.join(timeout=2.0)

            # Cerrar stream
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()

            # Guardar archivo
            self._save_audio_file()

            self.cleanup()
            self.recording_stopped.emit()
            logging.info(f"Grabación detenida: {self.filename}")
            return True

        except Exception as e:
            logging.error(f"Error deteniendo grabación: {e}")
            self.recording_error.emit(f"Error deteniendo grabación: {e}")
            self.cleanup()
            return False

    def _record_audio(self):
        """Hilo para grabar audio"""
        try:
            while self.is_recording and self.stream:
                data = self.stream.read(
                    self.chunk, exception_on_overflow=False)
                self.frames.append(data)

                # Calcular nivel de audio para visualización
                if len(data) > 0:
                    import struct
                    values = struct.unpack(f'{len(data)//2}h', data)
                    level = max(abs(v) for v in values) / 32768.0
                    self.audio_level_changed.emit(level)

        except Exception as e:
            logging.error(f"Error en hilo de grabación: {e}")
            self.recording_error.emit(f"Error grabando: {e}")

    def _save_audio_file(self):
        """Guardar archivo de audio"""
        try:
            if not self.frames:
                logging.warning("No hay datos de audio para guardar")
                return

            with wave.open(self.filename, 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(self.audio.get_sample_size(self.format))
                wf.setframerate(self.rate)
                wf.writeframes(b''.join(self.frames))

            logging.info(f"Archivo de audio guardado: {self.filename}")

        except Exception as e:
            logging.error(f"Error guardando archivo de audio: {e}")
            self.recording_error.emit(f"Error guardando audio: {e}")

    def cleanup(self):
        """Limpiar recursos de audio"""
        try:
            if self.stream:
                self.stream.close()
                self.stream = None

            if self.audio:
                self.audio.terminate()
                self.audio = None

        except Exception as e:
            logging.error(f"Error en cleanup de audio: {e}")

    def get_audio_devices(self):
        """Obtener lista de dispositivos de audio disponibles"""
        devices = []
        try:
            if not self.audio:
                self.initialize_audio()

            if self.audio:
                for i in range(self.audio.get_device_count()):
                    device_info = self.audio.get_device_info_by_index(i)
                    if device_info['maxInputChannels'] > 0:
                        devices.append({
                            'index': i,
                            'name': device_info['name'],
                            'channels': device_info['maxInputChannels']
                        })

        except Exception as e:
            logging.error(f"Error obteniendo dispositivos de audio: {e}")

        return devices

    def set_audio_device(self, device_index):
        """Establecer dispositivo de audio"""
        try:
            # Esta funcionalidad se puede implementar si es necesario
            # modificando el stream para usar un dispositivo específico
            pass
        except Exception as e:
            logging.error(f"Error estableciendo dispositivo de audio: {e}")
