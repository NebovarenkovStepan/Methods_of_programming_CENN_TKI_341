# API

Документ описывает HTTP API сервисов больничного кластера.

## Общие требования безопасности

Для всех endpoint, кроме `GET /health`, действуют guardrails-проверки.

Обязательные заголовки:

- `X-Subject-ID`: ID субъекта (user) для Authn/Authz;
- `X-Trusted-Channel: vpn`: признак доверенного канала;
- `X-Signature`: HMAC-SHA256 подпись тела запроса (обязательно для `portal`, `laboratory`, `llm`; для `pharmacy` используется в проверке кодов сканера);
- `X-Request-ID`: обязателен для `portal` и `pharmacy` (anti-replay).

Типовые ошибки preflight:

- `401` - ошибка аутентификации или отсутствует обязательный identity/request id;
- `403` - нарушение авторизации, недоверенный канал, replay, mismatch подписи;
- `400` - невалидный JSON/формат запроса.

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

Записывает пациента на прием к врачу. `scheduled_at` должен быть в RFC3339.

```json
{
  "patient_id": 1,
  "employee_id": 2,
  "scheduled_at": "2026-05-05T09:30:00Z",
  "reason": "Первичная консультация терапевта"
}
```

Успешный ответ: `201 Created`, статус записи `CONFIRMED`.

### `POST /cards`

Создает запись ЭМК.

### `POST /investigations`

Создает лабораторное назначение (статус `ORDERED`).

### `POST /prescriptions`

Создает электронный рецепт (статус `CREATED`).

## Pharmacy API

Базовый URL:

- Docker: `http://pharmacy:8081`
- Host: `http://localhost:8081`

### `GET /health`

Проверка состояния сервиса.

### `GET /prescriptions/{id}`

Получает рецепт по идентификатору.

Ошибки:

- `400 Bad Request` - неверный ID;
- `404 Not Found` - рецепт не найден.

### `POST /scanner/prescription`

Фиксирует сканирование рецепта.

```json
{
  "prescription_id": 1,
  "code": "<payloadHex>.<signatureHex>"
}
```

`payload` внутри кода должен соответствовать строке `prescription:{id}`.

### `POST /scanner/medicine`

Фиксирует сканирование лекарства.

```json
{
  "medicine_id": 1,
  "code": "<payloadHex>.<signatureHex>"
}
```

`payload` внутри кода должен соответствовать строке `medicine:{id}`.

### `POST /dispense`

Выдает лекарство по рецепту и списывает остаток со склада.

```json
{
  "prescription_id": 1,
  "quantity": 1
}
```

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

Возвращает список назначенных исследований.

### `GET /investigations/{investigation_id}`

Возвращает исследование по ID.

### `POST /samples/register`

Регистрирует образец для исследования.

### `POST /samples/{investigation_id}/to-storage`

Переводит образец в `IN_STORAGE`.

### `POST /samples/{investigation_id}/to-analysis`

Переводит образец в `IN_ANALYSIS`.

### `POST /analyzers`

Создает анализатор.

### `POST /workstations`

Создает рабочую станцию.

### `POST /analyzer-results`

Сохраняет сырой результат анализатора.

### `POST /investigations/complete`

Завершает лабораторное исследование.

### `POST /equipment`

Создает запись медицинского оборудования.

### `POST /monitoring/metrics`

Добавляет метрику мониторинга.

### `POST /diagnostics`

Добавляет результат самодиагностики.

## LLM API

Базовый URL:

- Docker: `http://llm:8000`
- Host: `http://localhost:8002`

### `GET /health`

Проверка состояния сервиса.

### `POST /generate`

Генерирует и сохраняет отчет по завершенному исследованию.

```json
{
  "investigation_id": 1
}
```

Успешный ответ: `201 Created`.

### `GET /reports/{investigation_id}`

Возвращает сохраненные LLM-отчеты по исследованию.
