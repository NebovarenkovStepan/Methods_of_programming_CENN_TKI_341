# Тестирование

В проекте есть unit-тесты отдельных сервисов и системные тесты в `test/test_system_scenarios.py`.

## Что покрывается

- e2e-сценарии через реальные HTTP-сервисы и PostgreSQL;
- HC-сценарии (negative/vulnerability probes), фиксирующие текущее поведение и уязвимые места;
- unit-тесты API-слоя Go-сервисов и сервисного слоя лаборатории.

## Запуск системных тестов через Docker

Из корня проекта:

```bash
docker compose -p hospital up --build --abort-on-container-exit test
```

Остановить сервисы:

```bash
docker compose -p hospital down
```

## Запуск локально без Docker

Нужны поднятые сервисы и переменные окружения:

```bash
export PORTAL_URL=http://localhost:8080
export PHARMACY_URL=http://localhost:8081
export LAB_URL=http://localhost:8001
export LLM_URL=http://localhost:8002
export DATABASE_URL=postgresql://hospital:hospital_password@localhost:5432/hospital_db
export INTEGRITY_SECRET=test-secret
```

Создать окружение и установить зависимости:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r test/requirements-test.txt
```

Запустить системные сценарии:

```bash
.venv/bin/python -m pytest test/test_system_scenarios.py -v
```

Если `DATABASE_URL` не задан, часть тестов будет `skipped`.

## Актуальные системные тесты

Файл: `test/test_system_scenarios.py`

HC-сценарии:

- `test_hc31_video_session_can_be_started_without_authorized_doctor`
- `test_hc20_existing_emk_record_can_be_changed_without_authorized_doctor`
- `test_hc01_emk_read_without_authorization`
- `test_hc03_unprotected_data_transfer_simulation`
- `test_hc04_tampered_api_payload_accepted`
- `test_hc06_sql_injection_like_input_accepted`
- `test_hc22_replay_attack_simulation`
- `test_hc33_backup_data_exposure_simulation`

E2E-сценарии:

- `test_patient_doctor_scenario_via_portal`
- `test_patient_pharmacy_portal_scenario`
- `test_patient_laboratory_portal_scenario`

## Карта unit-тестов

| Файл | Тип | Что проверяет |
| --- | --- | --- |
| `portal-go/internal/api/handler_test.go` | Unit | API портала: health, пациенты, ЭМК, прием, назначения, рецепты, ошибки |
| `pharmacy-go/internal/api/handler_test.go` | Unit | API аптеки: рецепты, сканирование, выдача, негативные кейсы |
| `laboratory-python/test_laboratory_services.py` | Unit | Сервисы лаборатории: LIS, sample storage, analyzer, workstation, monitoring |

## Запуск unit-тестов

Go:

```bash
cd portal-go && go test ./...
cd ../pharmacy-go && go test ./...
```

Python (лаборатория):

```bash
.venv/bin/python -m pytest laboratory-python/test_laboratory_services.py -v
```

## Важные замечания

- Системные тесты используют `pytest`, `requests`, `psycopg2` (см. `test/requirements-test.txt`).
- Перед тестами таблицы очищаются через `TRUNCATE ... CASCADE`.
- Security-guardrails включены в runtime сервисов; в тестах без правильных заголовков часть вызовов может завершаться `401/403`.
