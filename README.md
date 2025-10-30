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
GET http://<host>:12346/Document/GetPdf?deal=219418&price=29990.00&price_text=Двадцать+девять+тысяч+девятьсот+девяносто+рублей+ноль+копеек&bill_date=23.07.2025+16:53:27&name=Альбина&phone=+79165841624&email=albina@x2media.ru&inn=9718083987&companyName=ИП+Ляпина+Альбина+Ильдусовна&service=Продажа+оборудования
```

**ZIP с двумя файлами:**

```bash
GET http://<host>:12346/Document/GetAllZip?... (параметры те же)
```

В архив попадут `document.docx`, `document.pdf` и `payment_qr.png`.

**Только QR-код PNG:**

```bash
GET http://<host>:12346/Document/GetPaymentQr?deal=219418&price=29990.00
```

В ответ придёт `payment_qr.png`, а в заголовке `X-Payment-QR-Payload` — строка с реквизитами в формате `ST00012|...`.

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
посмотреть ответы прямо в браузере. Для успешной генерации документов не
забывайте установить зависимости из `requirements.txt` и, при необходимости,
LibreOffice (Linux) либо `pywin32` (Windows).

### Продакшн через Gunicorn

```bash
gunicorn -w 1 -b 0.0.0.0:12346 --timeout 120 app:app
```

---

## ⚙️ Systemd (Linux)

Файл: `/etc/systemd/system/leadforce.service`

```ini
[Unit]
Description=LeadForce Flask Service
After=network.target

[Service]
User=root
WorkingDirectory=/root/LeadForcePython
ExecStart=/usr/bin/python3 -m gunicorn -w 1 -b 0.0.0.0:12346 --timeout 120 app:app
Restart=always

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
