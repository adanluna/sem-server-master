#!/bin/bash
# ============================================================
#  Script oficial SEMEFO
#  Montaje automático de evidencia desde el servidor Grabador
#  Autor: Adan Luna / Arquitectura SEMEFO
# ============================================================

echo "=============================================="
echo "   Montaje automático SMB - SEMEFO"
echo "=============================================="

# --- Variables (puedes editarlas si cambia la IP o usuario) ---
SMB_IP="172.21.82.4"
SMB_USER="wave"
SMB_PASS="Semefo2025#"
CRED_FILE="/etc/smb-semefo"

MOUNT_SEMEFO="/mnt/semefo"
MOUNT_WAVE="/mnt/wave"

SHARE_SEMEFO="//${SMB_IP}/D/archivos_sistema_semefo"
SHARE_WAVE="//${SMB_IP}/D/Wisenet WAVE Media"

# ============================================================
# 1. Crear archivo de credenciales
# ============================================================
echo "[1/6] Creando archivo de credenciales SMB..."

sudo bash -c "cat > ${CRED_FILE}" <<EOF
username=${SMB_USER}
password=${SMB_PASS}
EOF

sudo chmod 600 ${CRED_FILE}

echo "   Archivo de credenciales creado: ${CRED_FILE}"
echo ""

# ============================================================
# 2. Crear carpetas de montaje
# ============================================================
echo "[2/6] Creando carpetas de montaje..."

sudo mkdir -p ${MOUNT_SEMEFO}
sudo mkdir -p ${MOUNT_WAVE}

sudo chmod 755 ${MOUNT_SEMEFO} ${MOUNT_WAVE}

echo "   Carpetas creadas:"
echo "   - ${MOUNT_SEMEFO}"
echo "   - ${MOUNT_WAVE}"
echo ""

# ============================================================
# 3. Actualizar /etc/fstab
# ============================================================
echo "[3/6] Configurando /etc/fstab..."

FSTAB_ENTRY=$(cat <<EOF
# ============================================================
# SEMEFO - Montaje automático de evidencia
# ============================================================

//${SMB_IP}/D/archivos_sistema_semefo ${MOUNT_SEMEFO} cifs credentials=${CRED_FILE},iocharset=utf8,file_mode=0777,dir_mode=0777,vers=3.0,x-systemd.automount,_netdev 0 0
//${SMB_IP}/D/Wisenet\040WAVE\040Media ${MOUNT_WAVE} cifs credentials=${CRED_FILE},iocharset=utf8,file_mode=0555,dir_mode=0555,vers=3.0,x-systemd.automount,_netdev 0 0

EOF
)

# Eliminar entradas previas para evitar duplicados
sudo sed -i '\|archivos_sistema_semefo|d' /etc/fstab
sudo sed -i '\|Wisenet\\040WAVE\\040Media|d' /etc/fstab

# Agregar nuevas
echo "${FSTAB_ENTRY}" | sudo tee -a /etc/fstab > /dev/null

echo "   Entradas agregadas correctamente."
echo ""

# ============================================================
# 4. Montar SMB
# ============================================================
echo "[4/6] Montando recursos SMB..."

sudo mount -a

echo "   Montaje ejecutado."
echo ""

# ============================================================
# 5. Validar acceso
# ============================================================
echo "[5/6] Validando acceso..."

if [ -d "${MOUNT_SEMEFO}" ] && ls ${MOUNT_SEMEFO} >/dev/null 2>&1; then
    echo "   ✔ SEMEFO OK: ${MOUNT_SEMEFO}"
else
    echo "   ❌ ERROR: No se pudo acceder a ${MOUNT_SEMEFO}"
fi

if [ -d "${MOUNT_WAVE}" ] && ls ${MOUNT_WAVE} >/dev/null 2>&1; then
    echo "   ✔ WISENET OK: ${MOUNT_WAVE}"
else
    echo "   ❌ ERROR: No se pudo acceder a ${MOUNT_WAVE}"
fi

echo ""

# ============================================================
# 6. Final
# ============================================================
echo "[6/6] Proceso finalizado."
echo "El sistema SEMEFO ya puede leer videos del grabador y escribir evidencia."
echo "=============================================="
