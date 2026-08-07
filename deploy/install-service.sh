#!/usr/bin/env bash
# Install xml2cli as a systemd service (boot auto-start).
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SERVICE_NAME="xml2cli"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
TEMPLATE="${PROJECT_DIR}/deploy/xml2cli.service"

if [[ "${EUID}" -ne 0 ]]; then
  echo "请使用 root 权限运行: sudo ${PROJECT_DIR}/deploy/install-service.sh"
  exit 1
fi

SERVICE_USER="${SUDO_USER:-phonix}"
if ! id "${SERVICE_USER}" &>/dev/null; then
  echo "用户 ${SERVICE_USER} 不存在，请设置: SUDO_USER=youruser sudo $0"
  exit 1
fi

PYTHON_BIN="$(command -v python3)"
if [[ -z "${PYTHON_BIN}" ]]; then
  echo "未找到 python3"
  exit 1
fi

sed \
  -e "s|__PROJECT_DIR__|${PROJECT_DIR}|g" \
  -e "s|__SERVICE_USER__|${SERVICE_USER}|g" \
  -e "s|__PYTHON__|${PYTHON_BIN}|g" \
  "${TEMPLATE}" > "${SERVICE_FILE}"

systemctl daemon-reload
systemctl enable "${SERVICE_NAME}.service"

if systemctl is-active --quiet "${SERVICE_NAME}.service"; then
  systemctl restart "${SERVICE_NAME}.service"
else
  systemctl start "${SERVICE_NAME}.service"
fi

echo "已安装并启用 ${SERVICE_NAME}.service"
echo "  用户: ${SERVICE_USER}"
echo "  目录: ${PROJECT_DIR}"
echo "  地址: http://0.0.0.0:8888"
systemctl --no-pager status "${SERVICE_NAME}.service"
