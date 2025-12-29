#!/bin/bash
# ============================================================
#  SEMEFO - Montaje SMB del grabador Hanwha (PRODUCCIÓN REAL)
#  Autor: Adan Luna
# ============================================================

echo "=============================================="
echo "   Montaje SMB - Recurso Wisenet (FUNCIONAL). "
echo "   Cambiar credenciales en caso necesario.    "
echo "=============================================="

SMB_IP="172.21.82.4"
SMB_SHARE="Wisenet_WAVE_Media"
SMB_USER="semefo"
SMB_PASS="Semefo2025#"
MOUNT_POINT="/mnt/wave"

# -------------------------------
# 1. Crear carpeta de montaje
# -------------------------------
echo "[1/3] Creando carpeta ${MOUNT_POINT}..."

sudo mkdir -p ${MOUNT_POINT}
sudo chmod 755 ${MOUNT_POINT}

echo "   ✔ Carpeta creada"
echo ""

# -------------------------------
# 2. Montaje manual de prueba
# -------------------------------
echo "[2/3] Probando montaje manual..."

sudo mount -t cifs //${SMB_IP}/${SMB_SHARE} ${MOUNT_POINT} \
  -o username=${SMB_USER},password=${SMB_PASS},domain=.,uid=1000,gid=1000,file_mode=0777,dir_mode=0777,iocharset=utf8,nounix,noperm,soft,vers=3.0,_netdev

if [ $? -ne 0 ]; then
    echo "❌ ERROR: No se pudo montar manualmente."
    exit 1
fi

echo "   ✔ Montaje manual exitoso"
echo ""

# -------------------------------
# 3. Registrar entrada en /etc/fstab
# -------------------------------
echo "[3/3] Actualizando /etc/fstab..."

sudo sed -i '\|Wisenet_WAVE_Media|d' /etc/fstab

sudo bash -c "cat >> /etc/fstab <<EOF

# SEMEFO - Recurso SMB de
