#!/usr/bin/env bash
# Install xml2cli as a user systemd service (no root for daily ops).
# Boot without login: once run  sudo loginctl enable-linger "$USER"
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SERVICE_NAME="xml2cli"
USER_SYSTEMD_DIR="${HOME}/.config/systemd/user"
SERVICE_PATH="${USER_SYSTEMD_DIR}/${SERVICE_NAME}.service"
TEMPLATE="${PROJECT_DIR}/deploy/xml2cli.user.service"
PYTHON_BIN="$(command -v python3)"

if [[ -z "${PYTHON_BIN}" ]]; then
  echo "未找到 python3"
  exit 1
fi

mkdir -p "${USER_SYSTEMD_DIR}"

sed \
  -e "s|__PROJECT_DIR__|${PROJECT_DIR}|g" \
  -e "s|__PYTHON__|${PYTHON_BIN}|g" \
  "${TEMPLATE}" > "${SERVICE_PATH}"

systemctl --user daemon-reload
systemctl --user enable "${SERVICE_NAME}.service"

if systemctl --user is-active --quiet "${SERVICE_NAME}.service"; then
  systemctl --user restart "${SERVICE_NAME}.service"
else
  systemctl --user start "${SERVICE_NAME}.service"
fi

echo "已安装用户服务: ${SERVICE_PATH}"
echo "  地址: http://0.0.0.0:8888"
systemctl --user --no-pager status "${SERVICE_NAME}.service"

if loginctl show-user "${USER}" -p Linger 2>/dev/null | grep -q 'Linger=no'; then
  echo ""
  echo "提示: 若需开机自动启动（无需登录），请执行一次:"
  echo "  sudo loginctl enable-linger ${USER}"
fi
