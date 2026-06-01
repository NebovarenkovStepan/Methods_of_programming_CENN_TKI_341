# Реализация архитектуры и security-контур (актуализация)

Дата актуализации: 2026-05-27.

## 1. Что реализовано

- Микросервисный контур: `portal-go`, `pharmacy-go`, `laboratory-python`, `llm-python`, PostgreSQL.
- Базовые бизнес-потоки: пациент, ЭМК, приемы, лабораторные назначения, рецепты, выдача, LLM-отчеты.
- Security-guardrails в runtime сервисах:
  - `Authn`
  - `Authz`
  - `ChannelGuard`
  - `Integrity`
  - `Audit`
  - anti-replay (`X-Request-ID`) в Go-сервисах `portal` и `pharmacy`.

## 2. Статус по сервисам

### 2.1 portal-go

- HTTP API на `net/http`.
- Preflight-проверки в handler.
- Покрытие unit-тестами API (`internal/api/handler_test.go`).

### 2.2 pharmacy-go

- HTTP API на `net/http`.
- Guardrails + проверка подписанных scanner-кодов.
- Покрытие unit-тестами API (`internal/api/handler_test.go`).

### 2.3 laboratory-python

- HTTP API на `http.server`.
- Guardrails в preflight для всех endpoint, кроме `/health`.
- Unit-тесты сервисного слоя: `laboratory-python/test_laboratory_services.py`.

### 2.4 llm-python

- HTTP API на `http.server`.
- Генерация/чтение отчетов с guardrails-проверками.
- Отдельного unit-файла `llm-python/test_llm_service.py` в текущем репозитории нет.

## 3. Тестовый контур (факт)

- Системные и HC-сценарии: `test/test_system_scenarios.py`.
- Каталог НС 1..33: `test/test_negative_scenarios_hc_1_33.py` (текущее состояние: намеренный `pytest.fail` для каждого сценария).
- Unit:
  - `portal-go/internal/api/handler_test.go`
  - `pharmacy-go/internal/api/handler_test.go`
  - `laboratory-python/test_laboratory_services.py`

## 4. Важные уточнения

- Текущий тестовый стек **не** zero-dependency: используются `pytest`, `requests`, `psycopg2` в `test/requirements-test.txt`.
- Формулировка «strict-only + все НС блокируются» не соответствует содержимому `test/test_system_scenarios.py`: HC-тесты там фиксируют успешность ряда атакующих действий (`assert_attack_passed`).
- Команды запуска должны выполняться из текущего корня репозитория `/Users/anastasia/Documents/hospital-cluster`, без жесткой привязки к старому пути.

## 5. Команды запуска тестов

Системные сценарии (локально):

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r test/requirements-test.txt
.venv/bin/python -m pytest test/test_system_scenarios.py -v
```

Go unit:

```bash
cd portal-go && go test ./...
cd ../pharmacy-go && go test ./...
```

Laboratory unit:

```bash
.venv/bin/python -m pytest laboratory-python/test_laboratory_services.py -v
```
