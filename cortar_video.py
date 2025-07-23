import subprocess
import os
import sys


def get_video_duration(input_file):
    """Obtener la duración del video en segundos"""
    try:
        result = subprocess.run([
            'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
            '-of', 'csv=p=0', input_file
        ], capture_output=True, text=True, check=True)

        duration = float(result.stdout.strip())
        return duration
    except subprocess.CalledProcessError as e:
        print(f"❌ Error obteniendo duración: {e}")
        return None
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return None


def cortar_video(input_file, output_prefix="parte", duration_minutes=1):
    """Cortar video en partes de 1 minuto"""

    # Verificar que el archivo existe
    if not os.path.exists(input_file):
        print(f"❌ Error: El archivo '{input_file}' no existe")
        return False

    # Verificar que ffmpeg está disponible
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
    except subprocess.CalledProcessError:
        print("❌ Error: ffmpeg no está instalado")
        print("💡 Instalar con: brew install ffmpeg")
        return False

    # Obtener duración total del video
    total_duration = get_video_duration(input_file)
    if total_duration is None:
        return False

    print(f"📹 Video: {input_file}")
    print(
        f"⏱️ Duración total: {total_duration:.2f} segundos ({total_duration/60:.2f} minutos)")

    # Calcular número de partes
    duration_seconds = duration_minutes * 60
    total_parts = int(total_duration / duration_seconds) + \
        (1 if total_duration % duration_seconds > 0 else 0)

    print(
        f"🔢 Se crearán {total_parts} partes de {duration_minutes} minuto(s) cada una")
    print()

    # Cortar video en partes
    success_count = 0

    for part in range(total_parts):
        start_time = part * duration_seconds
        output_file = f"{output_prefix}_{part + 1:02d}.mp4"

        print(f"✂️ Cortando parte {part + 1}/{total_parts}: {output_file}")
        print(f"   Desde {start_time//60:02.0f}:{start_time%60:02.0f}")

        try:
            # Comando ffmpeg para cortar
            cmd = [
                'ffmpeg',
                '-i', input_file,
                '-ss', str(start_time),
                '-t', str(duration_seconds),
                '-c', 'copy',
                '-y',
                output_file
            ]

            result = subprocess.run(
                cmd, capture_output=True, text=True, check=True)

            if os.path.exists(output_file):
                file_size = os.path.getsize(output_file) / (1024 * 1024)  # MB
                print(f"   ✅ Creado: {output_file} ({file_size:.2f} MB)")
                success_count += 1
            else:
                print(f"   ❌ Error: No se pudo crear {output_file}")

        except subprocess.CalledProcessError as e:
            print(f"   ❌ Error cortando parte {part + 1}: {e}")
        except Exception as e:
            print(f"   ❌ Error inesperado en parte {part + 1}: {e}")

    print()
    print(
        f"🎬 Proceso completado: {success_count}/{total_parts} partes creadas")

    return success_count > 0


def main():
    print("🎬 Script para cortar video2.mp4 en partes de 1 minuto")
    print("=" * 50)

    # Archivo de entrada
    input_file = "video2.mp4"

    # Verificar si se especificó otro archivo
    if len(sys.argv) > 1:
        input_file = sys.argv[1]

    # Ejecutar corte
    success = cortar_video(
        input_file=input_file,
        output_prefix="parte",
        duration_minutes=1
    )

    if success:
        print("✅ ¡Video cortado exitosamente!")
    else:
        print("❌ El proceso falló")


if __name__ == "__main__":
    main()
