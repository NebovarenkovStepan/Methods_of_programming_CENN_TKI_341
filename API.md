# API

Документ описывает HTTP API сервисов больничного кластера. При запуске через Docker Compose сервисы внутри сети доступны по именам контейнеров, а с хоста - через проброшенные порты.

## Portal API

Базовый URL:

- Docker: `http://portal:8080`
- Host: `http://localhost:8080`

### `GET /health`

Проверка состояния сервиса.

Ответ:

```json
{
  "status": "ok"
}
```

### `POST /patients`

Создает пациента.

Тело запроса:

```json
{
  "surname": "Иванов",
  "name": "Иван",
  "patronymic": "Иванович",
  "date_of_birth": "2000-01-01"
}
```

Успешный ответ: `201 Created`.

### `POST /appointments`

Записывает пациента на прием к врачу. Время передается в формате RFC3339.

Тело запроса:

```json
{
  "patient_id": 1,
  "employee_id": 2,
  "scheduled_at": "2026-05-05T09:30:00Z",
  "reason": "Первичная консультация терапевта"
}
```

Успешный ответ:

```json
{
  "id": 1,
  "patient_id": 1,
  "employee_id": 2,
  "scheduled_at": "2026-05-05T09:30:00Z",
  "reason": "Первичная консультация терапевта",
  "status": "CONFIRMED",
  "created_at": "2026-05-03T..."
}
```

Ошибки:

- `400 Bad Request` - неверный JSON или неверный формат `scheduled_at`;
- `500 Internal Server Error` - ошибка базы данных, например конфликт слота врача.

### `POST /cards`

Создает запись электронной медицинской карты.

Тело запроса:

```json
{
  "patient_id": 1,
  "employee_id": 2,
  "complaints": "Слабость и температура",
  "notes": "Назначены анализ крови и жаропонижающий препарат"
}
```

Успешный ответ: `201 Created`.

### `POST /investigations`

Создает лабораторное назначение.

Тело запроса:

```json
{
  "patient_id": 1,
  "card_id": 1,
  "test_name": "Общий анализ крови"
}
```

Успешный ответ содержит статус `ORDERED`.

### `POST /prescriptions`

Создает электронный рецепт.

Тело запроса:

```json
{
  "patient_id": 1,
  "employee_id": 2,
  "card_id": 1,
  "medicine_id": 1,
  "medicine_name": "Парацетамол",
  "dosage_instructions": "По 1 таблетке 2 раза в день после еды"
}
```

Успешный ответ содержит статус `CREATED`.

## Pharmacy API

Базовый URL:

- Docker: `http://pharmacy:8081`
- Host: `http://localhost:8081`

### `GET /health`

Проверка состояния сервиса.

### `GET /prescriptions/{id}`

Получает рецепт по идентификатору.

Успешный ответ: `200 OK`.

Ошибки:

- `400 Bad Request` - неверный идентификатор;
- `404 Not Found` - рецепт не найден.

### `POST /scanner/prescription`

Фиксирует сканирование рецепта.

Тело запроса:

```json
{
  "prescription_id": 1,
  "code": "RX-1"
}
```

Успешный ответ: `201 Created`.

### `POST /scanner/medicine`

Фиксирует сканирование лекарства.

Тело запроса:

```json
{
  "medicine_id": 1,
  "code": "MED-1"
}
```

Успешный ответ: `201 Created`.

### `POST /dispense`

Выдает лекарство по рецепту и списывает остаток со склада.

Тело запроса:

```json
{
  "prescription_id": 1,
  "quantity": 1
}
```

Успешный ответ: `201 Created`.

Ошибки:

- `400 Bad Request` - количество меньше или равно нулю;
- `404 Not Found` - рецепт не найден;
- `409 Conflict` - недостаточно остатков, рецепт уже выдан, рецепт отменен или не привязан `medicine_id`.

## Laboratory API

Базовый URL:

- Docker: `http://laboratory:8000`
- Host: `http://localhost:8001`

### `GET /health`

Проверка состояния сервиса.

### `GET /investigations/ordered`

Возвращает список назначенных, но еще не завершенных исследований.

### `GET /investigations/{investigation_id}`

Возвращает лабораторное исследование по идентификатору.

### `POST /samples/register`

Регистрирует образец для исследования.

```json
{
  "investigation_id": 1,
  "sample_type": "blood",
  "storage_location": "LAB-A-01"
}
```

### `POST /samples/{investigation_id}/to-storage`

Переводит образец в статус `IN_STORAGE`.

### `POST /samples/{investigation_id}/to-analysis`

Переводит образец в статус `IN_ANALYSIS`.

### `POST /analyzers`

Создает анализатор.

```json
{
  "name": "Analyzer-1",
  "model": "BioChem X"
}
```

### `POST /workstations`

Создает рабочую станцию.

```json
{
  "name": "WS-1",
  "location": "Lab room 2"
}
```

### `POST /analyzer-results`

Сохраняет сырой результат анализатора.

```json
{
  "investigation_id": 1,
  "analyzer_id": 1,
  "workstation_id": 1,
  "raw_result": "Hemoglobin=135; Leukocytes=6.2"
}
```

### `POST /investigations/complete`

Завершает лабораторное исследование.

```json
{
  "investigation_id": 1,
  "results": "Hemoglobin=135; Leukocytes=6.2"
}
```

### `POST /equipment`

Создает запись медицинского оборудования.

```json
{
  "name": "Analyzer Rack A",
  "equipment_type": "analyzer",
  "location": "Laboratory room 2"
}
```

### `POST /monitoring/metrics`

Добавляет метрику мониторинга оборудования.

```json
{
  "equipment_id": 1,
  "metric_name": "temperature",
  "metric_value": "36.6"
}
```

### `POST /diagnostics`

Добавляет результат самодиагностики оборудования.

```json
{
  "equipment_id": 1,
  "diagnostic_status": "OK",
  "details": "Плановая самодиагностика завершена без ошибок"
}
```

## LLM API

Базовый URL:

- Docker: `http://llm:8000`
- Host: `http://localhost:8002`

### `GET /health`

Проверка состояния сервиса.

### `POST /generate`

Генерирует и сохраняет отчет по завершенному лабораторному исследованию.

```json
{
  "investigation_id": 1
}
```

Успешный ответ: `200 OK`.

### `GET /reports/{investigation_id}`

Возвращает сохраненные LLM-отчеты по исследованию.

Успешный ответ:

```json
[
  {
    "id": 1,
    "patient_id": 1,
    "investigation_id": 1,
    "report_text": "Анализ: ...",
    "created_at": "2026-05-03T..."
  }
]
```

