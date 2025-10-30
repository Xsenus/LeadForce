#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

APP_DIR=${APP_DIR:-$PROJECT_ROOT}
PYTHON_BIN=${PYTHON_BIN:-/usr/bin/python3}
SERVICE_NAME=${SERVICE_NAME:-leadforce}
SYSTEMD_UNIT_PATH=${SYSTEMD_UNIT_PATH:-/etc/systemd/system/${SERVICE_NAME}.service}
SYSTEMD_UNIT_TEMPLATE=${SYSTEMD_UNIT_TEMPLATE:-${PROJECT_ROOT}/deploy/leadforce.service}

log() {
  echo "[deploy] $*"
}

APT_UPDATED=false

apt_update_once() {
  if [ "$APT_UPDATED" = true ]; then
    return
  fi

  if command -v apt-get >/dev/null 2>&1; then
    log "Обновляем список пакетов (apt-get update)"
    export DEBIAN_FRONTEND=noninteractive
    apt-get update
    APT_UPDATED=true
  fi
}

ensure_directory() {
  local dir="$1"
  if [ ! -d "$dir" ]; then
    log "Создаём каталог $dir"
    mkdir -p "$dir"
  fi
}

ensure_python() {
  if command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    return
  fi

  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN=$(command -v python3)
    return
  fi

  if command -v apt-get >/dev/null 2>&1; then
    log "Устанавливаем python3 и pip через apt"
    apt_update_once
    export DEBIAN_FRONTEND=noninteractive
    apt-get install -y python3 python3-pip
    PYTHON_BIN=$(command -v python3)
    return
  fi

  log "Не удалось найти интерпретатор Python. Установите python3 вручную." >&2
  exit 1
}

ensure_libreoffice() {
  if command -v soffice >/dev/null 2>&1; then
    return
  fi

  if command -v apt-get >/dev/null 2>&1; then
    log "Устанавливаем LibreOffice для PDF-конвертации"
    apt_update_once
    export DEBIAN_FRONTEND=noninteractive
    apt-get install -y libreoffice
  else
    log "LibreOffice не найден. PDF-конвертация может быть недоступна." >&2
  fi
}

ensure_python
ensure_directory "$APP_DIR"

if [ "$PROJECT_ROOT" != "$APP_DIR" ]; then
  log "Переключаемся в каталог приложения $APP_DIR"
  cd "$APP_DIR"
else
  cd "$PROJECT_ROOT"
fi

ensure_directory "$APP_DIR/output"

log "Обновляем зависимости"
"$PYTHON_BIN" -m pip install --upgrade pip
"$PYTHON_BIN" -m pip install -r requirements.txt

ensure_libreoffice

unit_updated=false
if [ -f "$SYSTEMD_UNIT_TEMPLATE" ]; then
  if [ ! -f "$SYSTEMD_UNIT_PATH" ] || ! cmp -s "$SYSTEMD_UNIT_TEMPLATE" "$SYSTEMD_UNIT_PATH"; then
    log "Обновляем systemd unit $SYSTEMD_UNIT_PATH"
    install -m 0644 "$SYSTEMD_UNIT_TEMPLATE" "$SYSTEMD_UNIT_PATH"
    unit_updated=true
  fi
else
  log "Шаблон systemd unit не найден по пути $SYSTEMD_UNIT_TEMPLATE"
fi

if command -v systemctl >/dev/null 2>&1; then
  log "Перезапускаем сервис $SERVICE_NAME"
  systemctl daemon-reload
  if ! systemctl is-enabled "$SERVICE_NAME" >/dev/null 2>&1; then
    log "Включаем автозапуск сервиса $SERVICE_NAME"
    systemctl enable "$SERVICE_NAME"
  fi
  systemctl restart "$SERVICE_NAME"
else
  log "systemctl не найден. Запустите сервис вручную: $PYTHON_BIN -m gunicorn ..." >&2
fi

log "Готово"
