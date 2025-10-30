#!/usr/bin/env bash
set -euo pipefail

APP_DIR=${APP_DIR:-/root/LeadForcePython}
PYTHON_BIN=${PYTHON_BIN:-/usr/bin/python3}
SERVICE_NAME=${SERVICE_NAME:-leadforce}

if [ ! -d "$APP_DIR" ]; then
  echo "[deploy] Каталог $APP_DIR не найден" >&2
  exit 1
fi

cd "$APP_DIR"

echo "[deploy] Обновляем код до последней версии"
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
  git fetch --all --prune
  git reset --hard "origin/${CURRENT_BRANCH}"
else
  echo "[deploy] git-репозиторий не найден, пропускаем обновление через git"
fi

echo "[deploy] Обновляем зависимости"
$PYTHON_BIN -m pip install --upgrade pip
$PYTHON_BIN -m pip install -r requirements.txt

echo "[deploy] Применяем миграции отсутствуют, пропускаем"

echo "[deploy] Перезапускаем сервис $SERVICE_NAME"
systemctl daemon-reload
systemctl restart "$SERVICE_NAME"

echo "[deploy] Готово"
