# LeadForce Document Generator

Сервис для генерации коммерческих документов (PDF/DOCX) на основе шаблона `.docx`, с динамической подстановкой данных, включая форматированную дату, сумму прописью и реквизиты заказчика.

---

## 🚀 Возможности

- 📄 Генерация DOCX и PDF-документов по шаблону
- 🔁 Подстановка параметров из GET-запроса (например, `{{ID}}`, `{{CUSTOMER}}`, `{{PRODUCT}}`)
- 💬 Автоматическая генерация суммы прописью (`num2words`)
- 🗓 Форматирование даты счёта в виде `23 июля 2025 г.`
- 📦 Генерация архивов (ZIP) с файлами
- 🖨 Поддержка PDF-конвертации:
  - Windows: `win32com`
  - Linux: `libreoffice --headless`

---

## 📂 Структура проекта

```bash
LeadForce/
├── app.py                  # Основной Flask-приложение
├── Templates/              # Папка с шаблоном Word
│   └── LeadsForce_v0.docx
├── deploy/                 # Шаблоны для автоматического деплоя
│   └── leadforce.service
├── output/                 # Генерируемые файлы
├── requirements.txt        # Зависимости
└── README.md               # Документация
```

---

## 📥 Поддерживаемые параметры запроса

| Параметр       | Описание                         |
|----------------|----------------------------------|
| `deal`         | ID сделки (также используется как номер счёта) |
| `service`      | Наименование услуги              |
| `city`         | Город                            |
| `lead_sum`     | Кол-во лидов                     |
| `lead_cost`    | Стоимость одного лида           |
| `revenue`      | Доход клиента                    |
| `price`        | Общая сумма                      |
| `price_text`   | Сумма прописью (необязательно)   |
| `email`        | Email заказчика                  |
| `phone`        | Телефон заказчика                |
| `name`         | Имя контактного лица             |
| `inn`          | ИНН организации или ИП           |
| `companyName`  | Название организации             |
| `bill_date`    | Дата счёта (`дд.мм.гггг чч:мм:сс`) |

### Дополнительные параметры для банковского QR-кода

| Параметр                | Описание                                               |
|-------------------------|--------------------------------------------------------|
| `qr_name`               | Получатель платежа (`Name`)                            |
| `qr_personal_account`   | Расчётный счёт (`PersonalAcc`)                         |
| `qr_bank_name`          | Наименование банка (`BankName`)                        |
| `qr_bic`                | БИК (`BIC`)                                            |
| `qr_correspondent_account` | Корреспондентский счёт (`CorrespAcc`)              |
| `qr_inn`                | ИНН получателя (`PayeeINN`)                            |
| `qr_kpp`                | КПП (опционально, `PayeeKPP`)                          |
| `qr_payer_address`      | Адрес плательщика (`PayerAddress`)                     |
| `qr_sum`                | Сумма платежа в копейках (`Sum`)                       |
| `qr_purpose`            | Назначение платежа (`Purpose`)                         |
| `qr_width_mm`           | Ширина QR-кода при встраивании в шаблон (мм)           |

Если параметры не переданы, используются значения по умолчанию:

```
Name=ИП Абакумова Наталья Александровна
PersonalAcc=40802810200006322048
BankName=АО «Тинькофф Банк»
BIC=044525974
CorrespAcc=30101810145250000974
PayeeINN=720206359451
Purpose=Оплата по счету №{{ID}}
```

---

## 📌 Шаблон Word

Для замены используются плейсхолдеры в формате `{{NAME}}`. Поддерживаются:

- `{{ID}}` — номер счёта (из `deal`)
- `{{INVOICE_DATE}}` — дата в формате `23 июля 2025 г.`
- `{{CUSTOMER}}` — заказчик: ФИО, телефоны, email, ИНН, организация
- `{{PRODUCT}}` — услуга в формате `Система привлечения клиентов / ...`
- `{{SUM}}` — сумма
- `{{AMOUNT_IN_WORDS}}` — сумма прописью
- `{{PAYMENT_QR_PAYLOAD}}` — текст, зашитый в QR-код (формат `ST00012|...`)
- `{{PAYMENT_QR_BASE64}}` — PNG-изображение QR-кода в base64 (для внешних интеграций)
- `{{QR_CODE}}` — маркер для встраивания изображения QR-кода прямо в шаблон DOCX

> `{{QR_CODE}}` должен находиться в отдельном параграфе или ячейке таблицы. Генератор удалит текст и вставит вместо него готовое PNG с шириной по умолчанию 40 мм (значение можно изменить параметром `qr_width_mm`).

---

## 🧪 Примеры запросов

**PDF-документ:**

```bash
GET http://<host>:12345/Document/GetPdf?deal=219418&price=29990.00&price_text=Двадцать+девять+тысяч+девятьсот+девяносто+рублей+ноль+копеек&bill_date=23.07.2025+16:53:27&name=Альбина&phone=+79165841624&email=albina@x2media.ru&inn=9718083987&companyName=ИП+Ляпина+Альбина+Ильдусовна&service=Продажа+оборудования
```

**ZIP с двумя файлами:**

```bash
GET http://<host>:12345/Document/GetAllZip?... (параметры те же)
```

В архив попадут `document.docx`, `document.pdf` и `payment_qr.png`.

**Только QR-код PNG:**

```bash
GET http://<host>:12345/Document/GetPaymentQr?deal=219418&price=29990.00
```

В ответ придёт `payment_qr.png`, а заголовок `X-Payment-QR-Payload-Base64` будет содержать
строку реквизитов в base64 (декодируйте её командой `echo "$HEADER" | base64 -d`).

---

## 🛠️ Запуск

### Локально (тестирование)

```bash
python3 app.py
```

После запуска сервис доступен по адресу `http://<host>:12345/`. Главная страница
возвращает JSON с перечнем доступных endpoint'ов и краткой инструкцией. Все
операции выполняются через GET-запросы.

### Swagger UI

- Swagger UI: `http://<host>:12345/apidocs/`
- JSON-спецификация (Swagger 2.0): `http://<host>:12345/openapi.json`

Интерфейс позволяет проверить доступные параметры, отправить тестовые запросы и
посмотреть ответы прямо в браузере. Для бинарных ответов (PDF/DOCX/ZIP/PNG)
после выполнения запроса появится кнопка **Download file** — она отправит на
клиент файл, который вернул сервис. Для успешной генерации документов не
забывайте установить зависимости из `requirements.txt` и, при необходимости,
LibreOffice (Linux) либо `pywin32` (Windows).

### Продакшн через Gunicorn

```bash
/srv/leadforce/venv/bin/gunicorn \
  --workers 3 --timeout 120 \
  --bind unix:/srv/leadforce/run/leadforce.sock \
  --access-logfile /srv/leadforce/logs/gunicorn.access.log \
  --error-logfile /srv/leadforce/logs/gunicorn.error.log \
  app:app
```

> Пример выше соответствует конфигурации systemd и предполагает, что код
> развёрнут в `/srv/leadforce/app`, а виртуальное окружение расположено в
> `/srv/leadforce/venv`.

---

## ⚙️ Systemd (Linux)

Файл: `/etc/systemd/system/leadforce.service`

```ini
[Unit]
Description=LeadForce (Flask) via gunicorn (unix socket)
After=network.target

[Service]
User=leadforce
Group=leadforce
WorkingDirectory=/srv/leadforce/app
Environment="PYTHONUNBUFFERED=1"
#EnvironmentFile=/srv/leadforce/.env
ExecStartPre=/usr/bin/mkdir -p /srv/leadforce/run
ExecStartPre=/usr/bin/chown leadforce:leadforce /srv/leadforce/run
ExecStart=/srv/leadforce/venv/bin/gunicorn \
  --workers 3 --timeout 120 \
  --bind unix:/srv/leadforce/run/leadforce.sock \
  --access-logfile /srv/leadforce/logs/gunicorn.access.log \
  --error-logfile /srv/leadforce/logs/gunicorn.error.log \
  app:app
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Запуск сервиса:

```bash
sudo systemctl daemon-reload
sudo systemctl enable leadforce
sudo systemctl restart leadforce
```

---

## 🤖 Автоматическое развёртывание на VPS

Workflow `.github/workflows/deploy.yml` копирует свежий код на сервер,
подготавливает окружение и обновляет сервис, даже если перед деплоем на VPS
нет ни пользователей, ни директорий.

1. Создайте на GitHub Secrets:
   - `VPS_HOST` — IP или доменное имя сервера.
   - `VPS_USER` — пользователь с правами `root` (workflow выполняет
     административные действия).
   - `VPS_SSH_KEY` — приватный SSH-ключ (формат OpenSSH).
   - `VPS_PORT` — (опционально) SSH-порт, если отличается от `22`.
2. При запуске workflow:
   - создаётся системный пользователь `leadforce` с домашней директорией
     `/srv/leadforce`;
   - формируются каталоги `/srv/leadforce/app`, `/srv/leadforce/logs`,
     `/srv/leadforce/run` и виртуальное окружение `/srv/leadforce/venv`;
   - устанавливаются пакеты `python3-venv`, `nginx`, `certbot`,
     `python3-certbot-nginx`, `rsync` и LibreOffice (для PDF-конвертации);
   - проект синхронизируется в `/srv/leadforce/app` (каталог очищается перед
     загрузкой);
   - зависимости ставятся внутри окружения, после чего обновляется systemd
     unit `/etc/systemd/system/leadforce.service` и перезапускается сервис.
3. Workflow можно запустить вручную через **Run workflow** или просто сделать
   push в ветку `main` — деплой выполняется автоматически.

### Ручной запуск скрипта развёртывания

На сервере также можно выполнить скрипт вручную:

```bash
sudo BASE_DIR=/srv/leadforce SERVICE_NAME=leadforce scripts/deploy.sh
```

Скрипт создаст пользователя и каталоги (если их ещё нет), настроит окружение
`/srv/leadforce/venv`, установит зависимости, обновит unit-файл и перезапустит
сервис. При повторных запусках он аккуратно обновит код и зависимости без
необходимости ручного вмешательства.

### Ручная подготовка VPS (если автоматизация временно недоступна)

Последовательность команд соответствует тому, что выполняет скрипт и workflow:

1. **Базовые пакеты**
   ```bash
   sudo apt update
   sudo apt install -y python3-venv nginx certbot python3-certbot-nginx rsync
   ```
2. **Пользователь и директории**
   ```bash
   sudo useradd -r -m -d /srv/leadforce -s /usr/sbin/nologin leadforce || true
   sudo mkdir -p /srv/leadforce/app /srv/leadforce/logs /srv/leadforce/run
   sudo python3 -m venv /srv/leadforce/venv
   sudo chown -R leadforce:leadforce /srv/leadforce
   sudo chmod -R u=rwX,g=rX,o= /srv/leadforce
   sudo touch /srv/leadforce/logs/gunicorn.access.log /srv/leadforce/logs/gunicorn.error.log
   sudo chown -R leadforce:leadforce /srv/leadforce/logs
   ```
3. **Загрузка приложения**
   ```bash
   sudo rsync -a --delete <путь_к_проекту>/ /srv/leadforce/app/
   sudo chown -R leadforce:leadforce /srv/leadforce/app
   ```
4. **Зависимости**
   ```bash
   sudo -u leadforce /srv/leadforce/venv/bin/pip install --upgrade pip wheel
   sudo -u leadforce /srv/leadforce/venv/bin/pip install -r /srv/leadforce/app/requirements.txt
   ```
5. **systemd-юнит** — содержимое совпадает с `deploy/leadforce.service`.
   ```bash
   sudo cp deploy/leadforce.service /etc/systemd/system/leadforce.service
   sudo systemctl daemon-reload
   sudo systemctl enable --now leadforce
   sudo systemctl status leadforce --no-pager
   ```

При следующем деплое достаточно обновить код (например, через `rsync` или git)
и выполнить пункты 4–5, чтобы подтянуть зависимости и перезапустить сервис.

---

## 📦 Зависимости

```bash
pip install -r requirements.txt
```

**Debian/Ubuntu:**

```bash
sudo apt install libreoffice
```

**Windows:**

```bash
pip install pywin32
```

---

## 📝 Лицензия

MIT License
