# LeadForce Document Generator

LeadForce — это Flask-сервис, который принимает параметры сделки через HTTP и
по шаблону Word формирует коммерческие документы: заполненный DOCX,
конвертированный PDF и банковский QR-код. Все операции выполняются на лету, без
необходимости ручной подготовки файлов.

## Возможности

- Генерация DOCX-документа по заранее настроенному шаблону.
- Конвертация результата в PDF (LibreOffice на Linux, Microsoft Word на Windows).
- Формирование архива ZIP с любым набором файлов (DOCX, PDF, QR).
- Создание банковского QR-кода в формате СБП и автоматическая подстановка
  реквизитов в документ.
- Swagger-документация, доступная из коробки по адресу `/apidocs/`.

## Требования

- Python 3.10+
- LibreOffice для конвертации DOCX → PDF в Linux-среде.
- Дополнительные Python-зависимости указаны в `requirements.txt`.

Установка зависимостей:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Для корректной работы QR-кодов установите пакеты `qrcode` и `Pillow` (они уже
задекларированы в `requirements.txt`).

## Запуск локально

```bash
export FLASK_APP=app.py
flask --app app.py run --host 0.0.0.0 --port 12345
```

После запуска откройте `http://localhost:12345/apidocs/`, чтобы посмотреть
описание всех маршрутов и отправить тестовые запросы через Swagger UI.

## Структура проекта

```
LeadForce/
├── app.py                  # Flask-приложение и бизнес-логика генерации
├── Templates/              # DOCX-шаблоны
│   └── LeadsForce_v0.docx
├── deploy/                 # Системный unit-файл для продакшена
├── scripts/                # Скрипты автоматизации (деплой на VPS)
├── requirements.txt        # Python-зависимости
└── README.md               # Документация (этот файл)
```

При первом запуске приложение создаёт каталог `output/`, куда складываются
временные файлы (DOCX/PDF/QR). Его можно безопасно очищать между генерациями.

## Плейсхолдеры шаблона

Документ Word должен содержать текстовые маркеры вида `{{PLACEHOLDER}}`. Основные
из них:

| Плейсхолдер              | Источник данных                                   |
|--------------------------|---------------------------------------------------|
| `{{ID}}`                 | Значение query-параметра `deal` или авто-UUID     |
| `{{INVOICE_DATE}}`      | Форматированная дата счёта                        |
| `{{CUSTOMER}}`          | Имя, телефон, e-mail, ИНН и компания              |
| `{{PRODUCT}}`           | Название услуги (`service`)                       |
| `{{SUM}}`               | Сумма числом (`price`)                            |
| `{{AMOUNT_IN_WORDS}}`   | Сумма прописью                                    |
| `{{PAYMENT_QR_PAYLOAD}}`| Строка payload для банковского QR                 |
| `{{PAYMENT_QR_BASE64}}` | Base64-код PNG-файла QR-кода                      |
| `{{QR_CODE}}`           | Маркер для прямой вставки изображения QR          |

Для успешной вставки изображения поместите `{{QR_CODE}}` в отдельный параграф
или ячейку таблицы. Ширина QR регулируется параметром `qr_width_mm` и по
умолчанию равна 36 мм.

## API

### Общие параметры

Все маршруты принимают query-параметры. Часть из них универсальна:

- `deal` — номер сделки/счёта.
- `service` — название услуги.
- `city`, `lead_sum`, `lead_cost`, `revenue` — произвольные показатели для
  шаблона.
- `price` — сумма числом.
- `price_text` — сумма прописью (если не передана, вычисляется автоматически).
- `bill_date` или `invoiceDate` — дата счёта (`дд.мм.гггг` либо с временем).
- `name`, `phone`, `email`, `inn`, `companyName` — данные клиента.

### Параметры банковского QR

| Параметр                    | Назначение                          |
|----------------------------|-------------------------------------|
| `qr_name`                  | Получатель (`Name`)                 |
| `qr_personal_account`      | Расчётный счёт (`PersonalAcc`)      |
| `qr_bank_name`             | Банк (`BankName`)                   |
| `qr_bic`                   | БИК (`BIC`)                         |
| `qr_correspondent_account` | Корреспондентский счёт (`CorrespAcc`)|
| `qr_inn`                   | ИНН (`PayeeINN`)                    |
| `qr_kpp`                   | КПП (`PayeeKPP`)                    |
| `qr_payer_address`         | Адрес плательщика (`PayerAddress`)  |
| `qr_sum`                   | Сумма в копейках (`Sum`)            |
| `qr_purpose`               | Назначение платежа (`Purpose`)      |
| `qr_width_mm`              | Ширина QR в документе (20–45 мм)    |

Если параметры не переданы, используются значения из словаря
`DEFAULT_PAYMENT_DETAILS` внутри `app.py`.

### Маршруты

| Метод | URL                        | Описание                                    |
|-------|---------------------------|---------------------------------------------|
| GET   | `/Document/GetPdf`        | Скачивание PDF-файла                        |
| GET   | `/Document/GetDocx`       | Скачивание DOCX-файла                       |
| GET   | `/Document/GetPdfZip`     | ZIP-архив с PDF                             |
| GET   | `/Document/GetDocxZip`    | ZIP-архив с DOCX                            |
| GET   | `/Document/GetAllZip`     | ZIP-архив с DOCX, PDF и QR                  |
| GET   | `/Document/GetPaymentQr`  | PNG-файл QR-кода + заголовок с payload      |
| GET   | `/` и `/docs`             | JSON-описание сервиса                       |

Каждый маршрут задокументирован в Swagger и поддерживает полный список
параметров, перечисленных выше.

### Пример запроса

```bash
curl -G \
  'http://localhost:12345/Document/GetAllZip' \
  --data-urlencode 'deal=219418' \
  --data-urlencode 'price=29990.00' \
  --data-urlencode 'service=Продажа оборудования' \
  --data-urlencode 'name=Альбина' \
  --data-urlencode 'phone=+79160000000' \
  --data-urlencode 'email=client@example.com'
```

Ответом будет архив `documents_full.zip` с готовыми файлами.

## Деплой

В репозитории присутствуют:

- `deploy/leadforce.service` — systemd-unit для запуска Gunicorn на порту 12345.
- `scripts/deploy.sh` — idempotent-скрипт, который готовит окружение на сервере,
  устанавливает зависимости и перезапускает сервис.
- GitHub Actions workflow (в директории `.github/`) для автоматического деплоя на
  VPS при пуше в основную ветку.

Минимальные шаги для ручного деплоя на Ubuntu:

```bash
sudo apt update
sudo apt install -y python3-venv libreoffice rsync nginx
sudo useradd -r -m -d /srv/leadforce -s /usr/sbin/nologin leadforce || true
sudo mkdir -p /srv/leadforce/app /srv/leadforce/logs /srv/leadforce/run
sudo python3 -m venv /srv/leadforce/venv
sudo rsync -a --delete ./ /srv/leadforce/app/
sudo /srv/leadforce/venv/bin/pip install -r /srv/leadforce/app/requirements.txt
sudo cp deploy/leadforce.service /etc/systemd/system/leadforce.service
sudo systemctl daemon-reload
sudo systemctl enable --now leadforce
```

## Разработка

- Для повторной генерации QR-кода достаточно удалить временные файлы из
  каталога `output/`.
- Внесли изменения в шаблон? Просто замените файл `Templates/LeadsForce_v0.docx`.
- Чтобы увидеть параметры, с которыми был создан QR, смотрите заголовок
  `X-Payment-QR-Payload-Base64` в ответе `/Document/GetPaymentQr`.
- Логика генерации QR и заполнения документа сосредоточена в `app.py` —
  каждая функция снабжена docstring-комментарием для быстрой навигации.

## Лицензия

Проект распространяется по лицензии MIT. Свободно используйте и
модифицируйте под свои задачи.
