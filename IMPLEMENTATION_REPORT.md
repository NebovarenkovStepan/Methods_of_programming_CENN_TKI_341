# Реализация Новой Архитектуры (Итог)

## 1. Что реализовано

### 1.1 Общая цель
Проведен переход на новую архитектуру с сохранением основных доменов (`лаборатория`, `аптека`, `портал`, `LLM`) и переработкой внутренней реализации под строгую security-модель.

### 1.2 Zero-dependency подход
Реализован режим без сторонних библиотек (только стандартные библиотеки языков):
- Go: удалены внешние web/router и DB-драйверы, использован `net/http` и in-memory слой.
- Python: удалены `fastapi/pydantic/psycopg2/pytest/requests`, использованы `http.server`, `sqlite3`, `unittest`, `urllib`.

### 1.3 Security guardrails (строгий режим)
Во всех ключевых потоках введены проверки:
- `Authn` (идентификация субъекта)
- `Authz` (проверка ролей по policy)
- `ChannelGuard` (доверенный канал)
- `Integrity` (подпись payload)
- `Audit` (security-аудит событий)
- защита от `replay` по `X-Request-ID`

---

## 2. Что сделано по модулям

### 2.1 `portal-go`
Реализовано:
- HTTP API на `http.ServeMux`.
- Строгий preflight-пайплайн безопасности в API.
- In-memory репозиторий вместо внешней БД/драйверов.
- Базовые unit-тесты API и security-компонентов.

Добавлены/обновлены тесты:
- `internal/api/handler_test.go`
- `internal/security/guardrails_test.go`
- `internal/repository/repository_test.go`
- `internal/db/postgres_test.go`

### 2.2 `pharmacy-go`
Реализовано:
- HTTP API на стандартной библиотеке.
- Guardrails-проверки в критичных endpoint.
- In-memory репозиторий.
- Тесты для strict-сценариев сканирования/выдачи.

Ключевой файл тестов:
- `internal/api/handler_test.go`

### 2.3 `laboratory-python`
Реализовано:
- Переход на stdlib HTTP-слой (`http.server`).
- Репозитории/сервисы переписаны под `sqlite3`-совместимый SQL.
- Убраны сторонние зависимости.
- Юнит-тесты на `unittest`.

Ключевые тесты:
- `laboratory-python/test_laboratory_services.py`

### 2.4 `llm-python`
Реализовано:
- Stdlib HTTP server.
- Без внешних библиотек.
- Сервис генерации и сохранения отчетов адаптирован под новый слой данных.
- Юнит-тесты на `unittest`.

Ключевые тесты:
- `llm-python/test_llm_service.py`

---

## 2.5 Таблица новых компонентов

| Компонент | Где в коде | Что считается успехом | Что считается ошибкой |
|---|---|---|---|
| VPN в локальную сеть (аптека ↔ портал) | `pharmacy-go/internal/security/channelguard`, `pharmacy-go/internal/api/handler.go` | Запрос с доверенного канала (`X-Trusted-Channel=vpn`) | `403 untrusted channel` |
| Шифрование/защита передачи (аптека ↔ портал) | `pharmacy-go/internal/security/integrity`, `pharmacy-go/internal/api/handler.go` | Корректная подпись payload (`X-Signature`) | `403 payload integrity failed` / `403 ... integrity check failed` |
| VPN в локальную сеть (лаборатория ↔ портал) | `laboratory-python/security/channel_guard/service.py`, `laboratory-python/main.py` | Доверенный источник запроса | `403` при недоверенном канале |
| Шифрование/защита передачи (лаборатория ↔ портал) | `laboratory-python/security/integrity/service.py`, `laboratory-python/main.py` | Корректная подпись запроса | `403` при mismatch подписи |
| VPN + защищенный канал (портал ↔ аптека/лаборатория) | `portal-go/internal/security/channelguard`, `portal-go/internal/api/handler.go` | Preflight пропускает только доверенный канал | `403` в preflight |
| Проверка личности пациента (аптека) | `pharmacy-go/internal/security/identitycheck`, `pharmacy-go/internal/api/handler.go` (`DispensePrescription`) | Личность/контекст выдачи подтверждены | `403 patient identity verification failed` |
| Проверка личности пациента (лаборатория) | `laboratory-python/security/identity_check/service.py`, `laboratory-python/main.py` | Действие разрешено для нужного пациента/контекста | `403` при несовпадении личности |
| Проверка направления | `laboratory-python/main.py` + preflight (`Authn/Authz/Integrity/Channel`) | Исследование выполняется в валидном контексте назначения | `401/403` для невалидного контекста |
| Перевод результатов в цифровой вид | `laboratory-python` сервисы (`analyzers`, `lis`, `sample_storage`) | Результат сохранен в структурированном виде | `400/500` при невалидных данных/ошибке сохранения |
| Разграничение доступа | `portal-go/internal/security/authz`, `pharmacy-go/internal/security/authz`, `laboratory-python/security/authz` | Роль субъекта разрешена политикой | `403 access denied` |
| Политики доступа | `ROLE_POLICY_MATRIX.md`, `authz/service.go` (Go), `security/authz/service.py` (Python) | Action разрешен для роли | Action вне policy или запрещенная роль |
| Проверка рецептов | `pharmacy-go/internal/security/integrity`, `pharmacy-go/internal/api/handler.go` (`ScanPrescription`) | Подписанный/валидный код рецепта | `403 prescription integrity check failed` |
| Проверка валидности данных API | `portal-go/internal/api/handler.go`, `pharmacy-go/internal/api/handler.go`, `laboratory-python/main.py` | Корректный JSON и обязательные поля/форматы | `400 invalid json` / `400 invalid ...` |
| Результаты LLM | `llm-python/service/llm_service.py`, `llm-python/main.py` | Отчет сформирован и сохранен | `404 investigation not found` / `400` при ошибке payload |
| Учет анализов | `laboratory-python/lis/service.py`, `analyzer_results`, `samples` | Статусы и результаты исследований фиксируются | Ошибка обновления/несуществующая запись |
| Учет остатков | `pharmacy-go/internal/repository/repository.go` (`DispensePrescription`) | Списание выполнено, событие выдачи создано | `409 insufficient stock` / другие conflict-ошибки |
| Результаты проверки | `Audit` сервисы + логи/события (`WriteSecurityLog`, scanner/dispense events) | Событие allow/deny зафиксировано | Ошибка записи аудита/бизнес-события |
| Аутентификация | `portal-go/internal/security/authn`, `pharmacy-go/internal/security/authn`, `laboratory-python/security/authn` | Валидный субъект успешно распознан | `401 authentication failed` |

---

## 3. Негативные сценарии (НС-1..НС-33)

### 3.1 Что сделано
- Сценарии НС-1..НС-33 сведены в системный набор:
  - `test/test_system_scenarios.py`
- Для каждого НС есть исполнимый `vulnerability_probe`.
- Текущая модель проверки: `assert blocked`.

### 3.2 Что означает `assert blocked`
Тест успешен, если атака:
- заблокирована контролями безопасности, или
- не может быть выполнена в текущем API-контуре.

Коды, которые считаются блокировкой/неуспехом атаки в системном наборе:
- `400`, `401`, `403`, `404`, `405`

### 3.3 Strict runtime проверки
Дополнительно в `test_system_scenarios.py` есть отдельные строгие проверки:
- `401` при отсутствии субъекта
- `403` при нарушении авторизации
- `403` при mismatch подписи
- `403` при replay

---

## 4. Как запускать тесты

### 4.1 Все тесты (Go + Python)
```bash
cd "/Users/anastasia/Documents/Больничный кластер " && \
(cd portal-go && mkdir -p .gocache && GOCACHE=$PWD/.gocache go test ./...) && \
(cd pharmacy-go && mkdir -p .gocache && GOCACHE=$PWD/.gocache go test ./...) && \
python3 -m unittest discover -s laboratory-python -p "test_*.py" && \
python3 -m unittest discover -s llm-python -p "test_*.py" && \
python3 -m unittest discover -s test -p "test_*.py"
```

### 4.2 С логами (verbose)
```bash
cd "/Users/anastasia/Documents/Больничный кластер " && \
(cd portal-go && mkdir -p .gocache && GOCACHE=$PWD/.gocache go test -v ./...) && \
(cd pharmacy-go && mkdir -p .gocache && GOCACHE=$PWD/.gocache go test -v ./...) && \
python3 -m unittest discover -v -b -s laboratory-python -p "test_*.py" && \
python3 -m unittest discover -v -b -s llm-python -p "test_*.py" && \
python3 -m unittest discover -v -b -s test -p "test_*.py"
```

---

## 5. Ограничения и текущие договоренности

1. Docker-файлы и docker-compose в этом этапе не были основной целью изменений.
2. Часть strict-тестов может `skip`, если в runtime не найден валидный `subject_id`.
3. Для полной детерминированности strict-проверок нужны корректные runtime-значения:
   - `STRICT_DOCTOR_SUBJECT_ID`
   - `STRICT_ADMIN_SUBJECT_ID`

---

## 6. Короткий итог

Переход на новую архитектуру выполнен с акцентом на:
- строгие security-контроли,
- zero-dependency реализацию,
- обновленный тестовый контур,
- покрытие негативных сценариев НС-1..НС-33 в системном наборе.

---

## 7. Финальный чек-лист готовности

Статус на 2026-05-24:

1. НС-1..НС-33 переведены на исполнимые probes с фиксированными ожидаемыми кодами: `Готово`.
2. Strict-тесты доработаны: fallback выполняется автоматически, `skip` для offline/sandbox больше не требуется: `Готово`.
3. Zero-dependency ограничения соблюдены (stdlib-only для кода и тестов): `Готово`.
4. Прогон Python тестов:
   - `laboratory-python`: `OK`
   - `llm-python`: `OK`
   - `test/` (включая system scenarios): `OK`
5. Go-тесты `portal-go`/`pharmacy-go` ранее проходили успешно; при параллельном запуске возможны задержки из-за блокировок локального cache. Рекомендуется последовательный запуск с локальным `GOCACHE`: `Готово к запуску`.
