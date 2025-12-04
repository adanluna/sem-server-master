#!/bin/bash
# ============================================================
#  SEMEFO - Montaje SMB del grabador Hanwha
#  Autor: Adan Luna
#  Objetivo:
#     - Crear credenciales SMB
#     - Crear carpeta /mnt/wave
#     - Montar manualmente el recurso SMB
#     - Registrar entrada definitiva en /etc/fstab
# ============================================================

echo "=============================================="
echo "   Montaje SMB - Recurso Wisenet"
echo "=============================================="

# -------------------------------
# CONFIGURACIÓN
# -------------------------------
SMB_IP="172.21.82.4"
SMB_SHARE="Wisenet_WAVE_Media"
SMB_USER="semefo"
SMB_PASS="Semefo2025#"
DOMAIN="."

CRED_FILE="/etc/smb-semefo"
MOUNT_POINT="/mnt/wave"

# -------------------------------
# 1. Crear archivo de credenciales
# -------------------------------
echo "[1/5] Creando archivo de credenciales..."

sudo bash -c "cat > ${CRED_FILE}" <<EOF
username=${SMB_USER}
password=${SMB_PASS}
domain=${DOMAIN}
EOF

sudo chmod 600 ${CRED_FILE}

echo "   ✔ Credenciales guardadas en ${CRED_FILE}"
echo ""

# -------------------------------
# 2. Crear carpeta de montaje
# -------------------------------
echo "[2/5] Creando carpeta ${MOUNT_POINT}..."

sudo mkdir -p ${MOUNT_POINT}
sudo chmod 755 ${MOUNT_POINT}

echo "   ✔ Carpeta creada"
echo ""

# -------------------------------
# 3. Montaje manual de prueba
# -------------------------------
echo "[3/5] Probando montaje manual..."

sudo mount -t cifs //${SMB_IP}/${SMB_SHARE} ${MOUNT_POINT} \
  -o username=${SMB_USER},password='${SMB_PASS}',domain=${DOMAIN},uid=1000,gid=1000,rw,iocharset=utf8,sec=ntlmssp,noperm,vers=3.0,_netdev

if [ $? -ne 0 ]; then
    echo "❌ ERROR: No se pudo montar manualmente."
    exit 1
fi

echo "   ✔ Montaje manual exitoso"
echo ""

# -------------------------------
# 4. Registrar entrada en /etc/fstab
# -------------------------------
echo "[4/5] Actualizando /etc/fstab..."

# eliminar entradas previas
sudo sed -i '\|Wisenet_WAVE_Media|d' /etc/fstab

# agregar entrada nueva
sudo bash -c "cat >> /etc/fstab <<EOF

# SEMEFO - Recurso SMB del grabador Hanwha
//${SMB_IP}/${SMB_SHARE} ${MOUNT_POINT} cifs credentials=${CRED_FILE},uid=1000,gid=1000,rw,iocharset=utf8,sec=ntlmssp,noperm,vers=3.0,_netdev 0 0

EOF"

echo "   ✔ Entrada añadida a /etc/fstab"
echo ""

# -------------------------------
# 5. Validación final
# -------------------------------
echo "[5/5] Validando montaje desde fstab..."

sudo umount ${MOUNT_POINT}
sudo mount ${MOUNT_POINT}

if [ $? -eq 0 ]; then
    echo "   ✔ Validación completada: /mnt/wave montado correctamente"
else
    echo "   ❌ ERROR: Falló el montaje desde /etc/fstab"
    exit 1
fi

echo ""
echo "=============================================="
echo "   ✔ Proceso completado con éxito"
echo "   El recurso SMB se montará automáticamente al iniciar el sistema."
echo "=============================================="
