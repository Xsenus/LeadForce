# LeadForce Document Generator

Сервис для генерации коммерческих документов (PDF/DOCX) на основе шаблона `.docx`, с динамической подстановкой данных, включая форматированную дату, сумму прописью и реквизиты заказчика.

---

## 🚀 Возможности

- 📄 Генерация DOCX и PDF-документов по шаблону
- 🔁 Подстановка параметров из GET-запроса (например, `{{ID}}`, `{{CUSTOMER}}`, `{{PRODUCT}}`)
- 💬 Автоматическая генерация суммы прописью (`num2words`)
- 🗓 Форматирование даты счёта в виде `23 июля 2025 г.`
- 📦 Генерация архивов (ZIP) с файлами
- 📱 Подготовка QR-кода для оплаты по стандарту `ST00012` и автоматическая вставка в шаблон
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
| `qr_enabled`   | Включить генерацию QR (по умолчанию `1`) |
| `qr_name`      | Получатель платежа               |
| `qr_account`   | Номер расчётного счёта           |
| `qr_bank`      | Наименование банка               |
| `qr_bik`       | БИК банка                        |
| `qr_correspondent_account` | Корр. счёт банка (необязательно) |
| `qr_inn`       | ИНН получателя (по умолчанию из `inn`) |
| `qr_kpp`       | КПП получателя (если есть)       |
| `qr_purpose`   | Назначение платежа (по умолчанию название услуги) |
| `bill_date`    | Дата счёта (`дд.мм.гггг чч:мм:сс`) |

---

## 📌 Шаблон Word

Для замены используются плейсхолдеры в формате `{{NAME}}`. Поддерживаются:

- `{{ID}}` — номер счёта (из `deal`)
- `{{INVOICE_DATE}}` — дата в формате `23 июля 2025 г.`
- `{{CUSTOMER}}` — заказчик: ФИО, телефоны, email, ИНН, организация
- `{{PRODUCT}}` — услуга в формате `Система привлечения клиентов / ...`
- `{{SUM}}` — сумма
- `{{AMOUNT_IN_WORDS}}` — сумма прописью
- `{{PAYMENT_QR}}` — QR-код оплаты (подставляется автоматически при наличии реквизитов)

QR-код формируется по формату `ST00012`. Для генерации достаточно передать параметры `qr_name`, `qr_account`, `qr_bank`, `qr_bik` и `price` (для суммы). Остальные поля — необязательные.

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

---

## 🛠️ Запуск

### Локально (тестирование)

```bash
python3 app.py
```

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
