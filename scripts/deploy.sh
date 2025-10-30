#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

BASE_DIR=${BASE_DIR:-/srv/leadforce}
APP_DIR=${APP_DIR:-${BASE_DIR}/app}
VENV_DIR=${VENV_DIR:-${BASE_DIR}/venv}
LOG_DIR=${LOG_DIR:-${BASE_DIR}/logs}
RUN_DIR=${RUN_DIR:-${BASE_DIR}/run}
SERVICE_NAME=${SERVICE_NAME:-leadforce}
SERVICE_USER=${SERVICE_USER:-leadforce}
SERVICE_GROUP=${SERVICE_GROUP:-$SERVICE_USER}
SYSTEMD_UNIT_PATH=${SYSTEMD_UNIT_PATH:-/etc/systemd/system/${SERVICE_NAME}.service}
SYSTEMD_UNIT_TEMPLATE=${SYSTEMD_UNIT_TEMPLATE:-${PROJECT_ROOT}/deploy/leadforce.service}
REQUIREMENTS_FILE=${REQUIREMENTS_FILE:-${APP_DIR}/requirements.txt}
APT_PACKAGES=(python3-venv nginx certbot python3-certbot-nginx rsync)

log() {
  echo "[deploy] $*"
}

if [[ ${EUID:-0} -ne 0 ]]; then
  log "Скрипт нужно запускать от root" >&2
  exit 1
fi

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

ensure_apt_packages() {
  if ! command -v apt-get >/dev/null 2>&1; then
    return
  fi

  local missing=()
  for pkg in "$@"; do
    if ! dpkg -s "$pkg" >/dev/null 2>&1; then
      missing+=("$pkg")
    fi
  done

  if [ ${#missing[@]} -gt 0 ]; then
    log "Устанавливаем пакеты: ${missing[*]}"
    apt_update_once
    export DEBIAN_FRONTEND=noninteractive
    apt-get install -y "${missing[@]}"
  fi
}

ensure_directory() {
  local dir="$1"
  if [ ! -d "$dir" ]; then
    log "Создаём каталог $dir"
    mkdir -p "$dir"
  fi
}

run_as_service_user() {
  if command -v runuser >/dev/null 2>&1; then
    runuser -u "$SERVICE_USER" -- "$@"
  elif command -v sudo >/dev/null 2>&1; then
    sudo -u "$SERVICE_USER" -- "$@"
  else
    local cmd
    printf -v cmd '%q ' "$@"
    su -s /bin/bash "$SERVICE_USER" -c "$cmd"
  fi
}

ensure_service_user() {
  if ! id "$SERVICE_USER" >/dev/null 2>&1; then
    log "Создаём системного пользователя $SERVICE_USER"
    useradd -r -m -d "$BASE_DIR" -s /usr/sbin/nologin "$SERVICE_USER"
  fi

  if [ ! -d "$BASE_DIR" ]; then
    mkdir -p "$BASE_DIR"
  fi

  chown "$SERVICE_USER":"$SERVICE_GROUP" "$BASE_DIR"
  chmod 750 "$BASE_DIR"
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

ensure_apt_packages "${APT_PACKAGES[@]}"
ensure_service_user
ensure_directory "$APP_DIR"
ensure_directory "$LOG_DIR"
ensure_directory "$RUN_DIR"
chmod 750 "$LOG_DIR" "$RUN_DIR"

SYSTEM_PYTHON=${SYSTEM_PYTHON:-$(command -v python3 || true)}
if [ -z "$SYSTEM_PYTHON" ]; then
  log "Не удалось найти системный python3" >&2
  exit 1
fi

if [ ! -d "$VENV_DIR/bin" ]; then
  log "Создаём виртуальное окружение в $VENV_DIR"
  "$SYSTEM_PYTHON" -m venv "$VENV_DIR"
fi

chown -R "$SERVICE_USER":"$SERVICE_GROUP" "$BASE_DIR"

if [ "$PROJECT_ROOT" != "$APP_DIR" ]; then
  log "Синхронизируем код из $PROJECT_ROOT в $APP_DIR"
  rsync -a --delete "$PROJECT_ROOT"/ "$APP_DIR"/
fi

run_as_service_user mkdir -p "$APP_DIR/output"
touch "$LOG_DIR/gunicorn.access.log" "$LOG_DIR/gunicorn.error.log"
chown -R "$SERVICE_USER":"$SERVICE_GROUP" "$APP_DIR" "$LOG_DIR" "$RUN_DIR"

PIP_BIN="$VENV_DIR/bin/pip"
if [ -x "$PIP_BIN" ]; then
  log "Обновляем pip и wheel"
  run_as_service_user "$PIP_BIN" install --upgrade pip wheel
fi

if [ -f "$REQUIREMENTS_FILE" ]; then
  log "Устанавливаем зависимости из $REQUIREMENTS_FILE"
  run_as_service_user "$PIP_BIN" install -r "$REQUIREMENTS_FILE"
else
  log "requirements.txt не найден по пути $REQUIREMENTS_FILE"
fi

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
  log "systemctl не найден. Запустите сервис вручную: $VENV_DIR/bin/gunicorn ..." >&2
fi

log "Готово"
