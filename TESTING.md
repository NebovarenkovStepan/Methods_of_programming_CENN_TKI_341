# Тестирование

В проекте есть unit-тесты отдельных сервисов и системные end-to-end тесты. Основной набор функциональных проверок находится в [test/test_system_scenarios.py](test/test_system_scenarios.py).

## Цель тестирования

Системные тесты проверяют работоспособность всей программы, а не отдельные заглушки. Они:

- запускаются против реальных HTTP-сервисов;
- используют общую PostgreSQL базу данных;
- создают реальные записи пациента, врача, рецепта, анализа, оборудования и отчета;
- проверяют итоговое состояние в таблицах БД после выполнения действий;
- подтверждают взаимодействие между `portal-go`, `laboratory-python`, `llm-python`, `pharmacy-go` и PostgreSQL.

## Запуск системных тестов через Docker

Текущий запуск выполняется только в строгом режиме новой архитектуры (strict-only).

Из корня проекта:

```bash
docker compose -p hospital up --build --abort-on-container-exit test
```

Ключ `-p hospital` нужен, потому что путь проекта содержит кириллицу и пробел. Без явного имени проекта Docker Compose может завершиться ошибкой:

```text
project name must not be empty
```

Ожидаемый результат:

```text
test_hc29_video_session_can_be_started_without_authorized_doctor PASSED
test_hc19_existing_emk_record_can_be_changed_without_authorized_doctor PASSED
test_patient_views_medical_card_results_and_prescriptions PASSED
test_doctor_creates_orders_and_receives_lab_report PASSED
test_admin_monitors_services_equipment_and_stock PASSED

5 passed
```

Остановить сервисы после ручного запуска:

```bash
docker compose -p hospital down
```

## Запуск локально без Docker

Для локального запуска нужны поднятые сервисы и переменные окружения:

```bash
export PORTAL_URL=http://localhost:8080
export PHARMACY_URL=http://localhost:8081
export LAB_URL=http://localhost:8001
export LLM_URL=http://localhost:8002
export DATABASE_URL=postgresql://hospital:hospital_password@localhost:5432/hospital_db
export INTEGRITY_SECRET=test-secret
# либо приоритетно:
# export INTEGRITY_SECRET_FILE=/path/to/secret_file
```

Важно для strict-режима:

- тестовые запросы должны передавать `X-Subject-ID`, `X-Trusted-Channel: vpn`, `X-Signature`;
- тестовые запросы должны передавать уникальный `X-Request-ID` (anti-replay);
- для аптечного сканера код должен быть подписан (формат `payloadHex.signatureHex`);
- в системных сценариях лабораторные `sample:*` операции выполняются пользователем с ролью `admin/tech/lab_tech`.

Создать виртуальное окружение:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r test/requirements-test.txt
```

Запустить системные тесты:

```bash
.venv/bin/python -m pytest test/test_system_scenarios.py -v
```

Если `DATABASE_URL` не задан, системные тесты будут пропущены, потому что они должны проверять реальную БД.

## Сценарий 1: пациент

Тест:

```text
test_patient_views_medical_card_results_and_prescriptions
```

Назначение:

Проверяет путь пациента от записи на прием до просмотра данных, которые должны попасть в его электронную медицинскую карту.

Проверяемый процесс:

1. Проверяется доступность всех сервисов через `/health`.
2. Через портал создается пациент.
3. Через портал создается запись пациента на прием к врачу: `POST /appointments`.
4. Через портал создается запись ЭМК: `POST /cards`.
5. Через портал создается назначение лабораторного исследования: `POST /investigations`.
6. Через портал создается электронный рецепт: `POST /prescriptions`.
7. Лаборатория регистрирует образец, переводит его на хранение и анализ.
8. Лаборатория сохраняет результат анализатора.
9. Лаборатория завершает исследование.
10. LLM-сервис формирует отчет по результату анализа.
11. Аптека получает рецепт.
12. Тест проверяет в PostgreSQL, что у пациента есть запись на прием, ЭМК, завершенный анализ, LLM-отчет и рецепт.

Ключевые проверки:

- запись на прием имеет статус `CONFIRMED`;
- лабораторное исследование имеет статус `COMPLETED`;
- результат анализа сохранен в `laboratory_investigations`;
- LLM-отчет сохранен в `llm_reports`;
- рецепт содержит назначенный препарат и инструкцию.

## Сценарий 2: врач / медперсонал

Тест:

```text
test_doctor_creates_orders_and_receives_lab_report
```

Назначение:

Проверяет работу врача: врач ведет ЭМК пациента, назначает анализ и лекарство, получает лабораторный результат и LLM-отчет.

Проверяемый процесс:

1. Создается пациент.
2. Врач создает запись ЭМК.
3. Врач назначает лабораторное исследование.
4. Врач создает рецепт.
5. Лабораторный сервис показывает назначение в списке `/investigations/ordered`.
6. Лабораторный сервис возвращает назначение по ID.
7. Лаборатория выполняет анализ и завершает исследование.
8. LLM-сервис генерирует отчет.
9. Врач получает список отчетов через `/reports/{investigation_id}`.
10. Аптека получает созданный врачом рецепт.
11. Тест проверяет, что все записи связаны с одним врачом и одним пациентским случаем.

Ключевые проверки:

- назначение появляется в списке лаборатории;
- до выполнения исследования статус равен `ORDERED`;
- после выполнения статус равен `COMPLETED`;
- результат анализа сохранен;
- создан один результат анализатора;
- создан один LLM-отчет;
- рецепт остается в статусе `CREATED` до выдачи.

## Сценарий 3: администратор / ИТ

Тест:

```text
test_admin_monitors_services_equipment_and_stock
```

Назначение:

Проверяет административный сценарий: контроль доступности сервисов, мониторинг оборудования, самодиагностика и контроль складских остатков после выдачи лекарства.

Проверяемый процесс:

1. Проверяется `/health` у портала, аптеки, лаборатории и LLM.
2. В лабораторном сервисе создается оборудование.
3. Добавляется метрика мониторинга оборудования.
4. Добавляется запись самодиагностики.
5. Создается пациентская запись и рецепт.
6. Аптека сканирует рецепт.
7. Аптека сканирует лекарство.
8. Аптека выдает лекарство и списывает его со склада.
9. Тест проверяет состояние оборудования, метрики, диагностику, статус рецепта и остаток на складе.

Ключевые проверки:

- все сервисы отвечают `{"status": "ok"}`;
- оборудование имеет статус `ACTIVE`;
- метрика мониторинга сохранена;
- самодиагностика сохранена;
- рецепт переходит в статус `DISPENSED`;
- остаток лекарства уменьшается с `10` до `8`;
- создаются события сканирования и выдачи.

## Карта тестов

| Файл | Тип | Что проверяет |
| --- | --- | --- |
| `test/test_system_scenarios.py` | System / e2e | Три сквозных сценария всей системы: пациент, врач, администратор |
| `portal-go/internal/api/handler_test.go` | Unit | HTTP handlers портала: пациенты, ЭМК, запись на прием, анализы, рецепты |
| `pharmacy-go/internal/api/handler_test.go` | Unit | HTTP handlers аптеки: рецепты, сканер, выдача лекарств, ошибки выдачи |
| `laboratory-python/test_laboratory_services.py` | Unit | Сервисный слой лаборатории: ЛИС, образцы, анализаторы, оборудование, мониторинг |
| `llm-python/test_llm_service.py` | Unit | Сервис LLM-отчетов: получение исследования, генерация, сохранение, ошибки |

## Unit-тесты Go-сервисов

Go unit-тесты портала:

```bash
cd portal-go
go test ./...
```

Go unit-тесты аптеки:

```bash
cd pharmacy-go
go test ./...
```

### Portal unit-тесты

Файл:

```text
portal-go/internal/api/handler_test.go
```

Эти тесты не подключаются к настоящей базе данных. Вместо этого используется `mockPortalRepository`, который имитирует репозиторий портала и сохраняет созданные сущности в памяти. Это позволяет проверить HTTP-слой быстро и независимо от PostgreSQL.

Проверяется:

- `GET /health` возвращает `200 OK`;
- `POST /patients` создает пациента;
- некорректный формат `date_of_birth` возвращает `400 Bad Request`;
- `POST /cards` создает запись ЭМК;
- `POST /appointments` создает запись пациента на прием со статусом `CONFIRMED`;
- некорректный формат `scheduled_at` при записи на прием возвращает `400 Bad Request`;
- `POST /investigations` создает лабораторное назначение со статусом `ORDERED`;
- `POST /prescriptions` создает рецепт со статусом `CREATED`;
- некорректный JSON возвращает `400 Bad Request`;
- ошибка репозитория преобразуется в `500 Internal Server Error`.

Что важно:

Часть тестов специально фиксирует текущие ограничения безопасности, например создание записей без полноценной авторизации. Такие тесты описывают текущее поведение системы и показывают места, которые можно усилить в будущем.

### Pharmacy unit-тесты

Файл:

```text
pharmacy-go/internal/api/handler_test.go
```

Эти тесты используют `mockPharmacyRepository` и проверяют связку HTTP handler -> AIS service -> Scanner service -> repository interface.

Проверяется:

- `GET /health` возвращает `200 OK`;
- `GET /prescriptions/{id}` возвращает существующий рецепт;
- запрос несуществующего рецепта возвращает `404 Not Found`;
- `POST /scanner/prescription` сохраняет событие сканирования рецепта;
- `POST /scanner/medicine` сохраняет событие сканирования лекарства;
- `POST /dispense` создает событие выдачи лекарства;
- выдача с количеством `0` отклоняется на уровне API с `400 Bad Request`;
- ошибки репозитория корректно преобразуются в HTTP-статусы:
  `404 Not Found` для отсутствующего рецепта и `409 Conflict` для конфликтов склада или статуса рецепта.

Покрываемые ошибки:

- рецепт не найден;
- недостаточно лекарства на складе;
- рецепт уже выдан;
- рецепт отменен;
- рецепт не связан с `medicine_id`.

## Unit-тесты Python-сервисов

Python unit-тесты лабораторного сервиса и LLM-сервиса:

```bash
.venv/bin/python -m pytest laboratory-python/test_laboratory_services.py llm-python/test_llm_service.py -v
```

### Laboratory unit-тесты

Файл:

```text
laboratory-python/test_laboratory_services.py
```

Тесты используют `Mock`, `MagicMock` и `patch`, поэтому не требуют настоящего PostgreSQL. Они проверяют сервисный слой лаборатории, то есть бизнес-операции до FastAPI-слоя.

Проверяемые сервисы:

- `LISService`;
- `SampleStorageService`;
- `AnalyzerService`;
- `WorkstationService`;
- `MedicalEquipmentService`;
- `MonitoringService`;
- `SelfDiagnosticsService`.

Проверяется:

- получение списка назначенных исследований;
- получение исследования по ID;
- завершение лабораторного исследования;
- регистрация образца;
- перевод образца в хранение и в анализ;
- создание анализатора;
- сохранение результата анализатора;
- создание рабочей станции;
- создание медицинского оборудования;
- добавление метрик мониторинга;
- добавление записей самодиагностики.

Особенность:

В файле есть позитивные и негативные проверки. Негативные проверки не всегда ожидают отказ операции; часть из них демонстрирует текущие уязвимости системы, например отсутствие проверки роли или авторизации. Поэтому такие тесты могут проходить именно потому, что фиксируют существующее небезопасное поведение.

### LLM unit-тесты

Файл:

```text
llm-python/test_llm_service.py
```

Тесты проверяют сервис `LLMService` без реального подключения к базе данных. Доступ к БД подменяется через mock-объекты и `patch`.

Проверяется:

- получение лабораторного исследования;
- генерация текста отчета по завершенному исследованию;
- поведение при незавершенном исследовании;
- сохранение LLM-отчета;
- полный workflow `get_investigation -> generate_report_text -> save_report`;
- обработка отсутствующего исследования;
- воспроизводимость текста отчета;
- отсутствие проверки роли при генерации отчета как зафиксированное текущее ограничение.

Ключевые ожидаемые результаты:

- если исследование найдено и завершено, отчет создается;
- если исследование не найдено, возвращается ошибка `investigation not found`;
- если исследование не завершено, текст отчета сообщает, что исследование не завершено;
- сохраненный отчет содержит переданный текст.

## Важные замечания

- Системные тесты очищают таблицы перед каждым сценарием через `TRUNCATE ... CASCADE`.
- В фикстуре тестов создаются базовые данные: врач, администратор, лекарство и складской остаток.
- Тесты используют реальные HTTP-запросы через библиотеку `requests`.
- Проверка результата выполняется SQL-запросами напрямую к PostgreSQL.

## Реестр всех 83 тестов

Итоговая разбивка текущего набора:

- Go: 30 тестов
- Python: 53 теста
- Всего: 83 теста

Проверка Python-части выполнена через `pytest --collect-only`:

```bash
.venv/bin/python -m pytest --collect-only -q test/test_system_scenarios.py laboratory-python/test_laboratory_services.py llm-python/test_llm_service.py
```

Результат: `53 tests collected`.

### Go (30)

`pharmacy-go/internal/api/handler_test.go` (11):

- `TestHealth_ReturnsOK` — health endpoint аптеки отвечает `200`.
- `TestHC28GetPrescription_ReturnsPrescriptionForAuthorizedPharmacist` — чтение рецепта авторизованным субъектом.
- `TestGetPrescription_NotFound` — несуществующий рецепт возвращает `404`.
- `TestHC27ScanPrescription_RejectsFakeQRWithoutAuthenticityValidation` — проверка отклонения поддельного QR рецепта.
- `TestScanMedicine_RejectsMedicineCodeWithoutAuthenticityValidation` — проверка отклонения неподписанного кода лекарства.
- `TestDispensePrescription_DispensesCreatedPrescription` — успешная выдача рецепта и запись события.
- `TestDispensePrescription_RejectsInvalidQuantityAtAPILevel` — API отклоняет некорректное количество.
- `TestDispensePrescription_MapsRepositoryErrors` — ошибки репозитория корректно мапятся в HTTP-коды.
- `TestScanPrescription_StrictModeRejectsUnsignedCode` — strict-mode блокирует неподписанный код рецепта.
- `TestScanPrescription_StrictModeAcceptsSignedCode` — strict-mode принимает валидно подписанный код.
- `TestGetPrescription_StrictModeRejectsReplay` — strict-mode блокирует replay по `X-Request-ID`.

`portal-go/internal/api/handler_test.go` (15):

- `TestHealth_ReturnsOK` — health endpoint портала отвечает `200`.
- `TestCreatePatient_CreatesPatientWithValidSecurityHeaders` — создание пациента с валидными заголовками.
- `TestCreatePatient_InvalidDateReturnsBadRequest` — неверный формат даты дает `400`.
- `TestHC18CreateCard_CreatesRecordForAuthorizedDoctorSubject` — создание записи ЭМК для авторизованного субъекта.
- `TestCreateAppointment_ConfirmsPatientVisit` — создание записи на прием со статусом `CONFIRMED`.
- `TestCreateAppointment_InvalidDateReturnsBadRequest` — неверный `scheduled_at` дает `400`.
- `TestHC32CreateInvestigation_CreatesOrderForAuthorizedDoctorSubject` — создание лабораторного назначения.
- `TestCreatePrescription_CreatesPrescriptionForAuthorizedDoctorSubject` — создание рецепта с корректными полями.
- `TestCreatePrescription_InvalidJSONReturnsBadRequest` — невалидный JSON дает `400`.
- `TestRepositoryErrorReturnsInternalServerError` — ошибка репозитория возвращает `500`.
- `TestCreatePatient_StrictModeRejectsMissingSecurityHeaders` — strict-mode отклоняет запрос без security-заголовков.
- `TestCreatePatient_StrictModeAcceptsValidHeadersAndSignature` — strict-mode пропускает валидный подписанный запрос.
- `TestCreatePatient_StrictModeRejectsReplay` — strict-mode блокирует повтор запроса.
- `TestCreatePatient_StrictModeRejectsMissingSubjectWith401` — strict-mode возвращает `401` без `X-Subject-ID`.
- `TestCreatePatient_StrictModeRejectsSignatureMismatchWith403` — strict-mode возвращает `403` при неверной подписи.

`portal-go/internal/db/postgres_test.go` (1):

- `TestNewPoolDisabledInZeroDependencyMode` — в zero-dependency режиме внешний DB pool не создается.

`portal-go/internal/repository/repository_test.go` (2):

- `TestResolveSubjectRoles` — корректное определение ролей известных субъектов.
- `TestResolveSubjectNotFound` — неизвестный субъект возвращает ошибку.

`portal-go/internal/security/guardrails_test.go` (1):

- `TestGuardrailsReady` — `Guardrails.Ready()` ложно на пустой конфигурации и истинно на полной.

### Python (53)

`test/test_system_scenarios.py` (43):

- `TestScenarioRegistry.test_registry_contains_all_33_negative_scenarios` — реестр содержит HC-1..HC-33.
- `TestScenarioRegistry.test_expected_code_contains_all_33_negative_scenarios` — коды ожидаемых ответов заданы для HC-1..HC-33.
- `TestStrictSecuritySystemScenarios.test_hc12_401_missing_subject` — HC-12: отсутствие субъекта.
- `TestStrictSecuritySystemScenarios.test_hc18_403_authz_denied` — HC-18: отказ авторизации.
- `TestStrictSecuritySystemScenarios.test_hc04_403_signature_mismatch` — HC-04: mismatch подписи.
- `TestStrictSecuritySystemScenarios.test_hc22_403_replay_detected` — HC-22: replay по `X-Request-ID`.
- `TestDeepInputSecurityProbes.test_hc06_sqli_with_valid_signature_reaches_application_layer` — SQLi-пейлоад с валидным preflight.
- `TestDeepInputSecurityProbes.test_hc20_xss_with_valid_signature_not_reflected` — XSS-пейлоад не отражается в ответе.
- `TestDeepInputSecurityProbes.test_hc06_sqli_payload_set_with_valid_signature` — набор SQLi-пейлоадов с валидной подписью.
- `TestDeepInputSecurityProbes.test_hc20_xss_payload_set_with_valid_signature_not_reflected` — набор XSS-пейлоадов без HTML-рефлексии.
- `TestAllNegativeScenariosExecutable.test_hc01_vulnerability_probe_expected_code` — исполнимый probe сценария HC-01.
- `TestAllNegativeScenariosExecutable.test_hc02_vulnerability_probe_expected_code` — исполнимый probe сценария HC-02.
- `TestAllNegativeScenariosExecutable.test_hc03_vulnerability_probe_expected_code` — исполнимый probe сценария HC-03.
- `TestAllNegativeScenariosExecutable.test_hc04_vulnerability_probe_expected_code` — исполнимый probe сценария HC-04.
- `TestAllNegativeScenariosExecutable.test_hc05_vulnerability_probe_expected_code` — исполнимый probe сценария HC-05.
- `TestAllNegativeScenariosExecutable.test_hc06_vulnerability_probe_expected_code` — исполнимый probe сценария HC-06.
- `TestAllNegativeScenariosExecutable.test_hc07_vulnerability_probe_expected_code` — исполнимый probe сценария HC-07.
- `TestAllNegativeScenariosExecutable.test_hc08_vulnerability_probe_expected_code` — исполнимый probe сценария HC-08.
- `TestAllNegativeScenariosExecutable.test_hc09_vulnerability_probe_expected_code` — исполнимый probe сценария HC-09.
- `TestAllNegativeScenariosExecutable.test_hc10_vulnerability_probe_expected_code` — исполнимый probe сценария HC-10.
- `TestAllNegativeScenariosExecutable.test_hc11_vulnerability_probe_expected_code` — исполнимый probe сценария HC-11.
- `TestAllNegativeScenariosExecutable.test_hc12_vulnerability_probe_expected_code` — исполнимый probe сценария HC-12.
- `TestAllNegativeScenariosExecutable.test_hc13_vulnerability_probe_expected_code` — исполнимый probe сценария HC-13.
- `TestAllNegativeScenariosExecutable.test_hc14_vulnerability_probe_expected_code` — исполнимый probe сценария HC-14.
- `TestAllNegativeScenariosExecutable.test_hc15_vulnerability_probe_expected_code` — исполнимый probe сценария HC-15.
- `TestAllNegativeScenariosExecutable.test_hc16_vulnerability_probe_expected_code` — исполнимый probe сценария HC-16.
- `TestAllNegativeScenariosExecutable.test_hc17_vulnerability_probe_expected_code` — исполнимый probe сценария HC-17.
- `TestAllNegativeScenariosExecutable.test_hc18_vulnerability_probe_expected_code` — исполнимый probe сценария HC-18.
- `TestAllNegativeScenariosExecutable.test_hc19_vulnerability_probe_expected_code` — исполнимый probe сценария HC-19.
- `TestAllNegativeScenariosExecutable.test_hc20_vulnerability_probe_expected_code` — исполнимый probe сценария HC-20.
- `TestAllNegativeScenariosExecutable.test_hc21_vulnerability_probe_expected_code` — исполнимый probe сценария HC-21.
- `TestAllNegativeScenariosExecutable.test_hc22_vulnerability_probe_expected_code` — исполнимый probe сценария HC-22.
- `TestAllNegativeScenariosExecutable.test_hc23_vulnerability_probe_expected_code` — исполнимый probe сценария HC-23.
- `TestAllNegativeScenariosExecutable.test_hc24_vulnerability_probe_expected_code` — исполнимый probe сценария HC-24.
- `TestAllNegativeScenariosExecutable.test_hc25_vulnerability_probe_expected_code` — исполнимый probe сценария HC-25.
- `TestAllNegativeScenariosExecutable.test_hc26_vulnerability_probe_expected_code` — исполнимый probe сценария HC-26.
- `TestAllNegativeScenariosExecutable.test_hc27_vulnerability_probe_expected_code` — исполнимый probe сценария HC-27.
- `TestAllNegativeScenariosExecutable.test_hc28_vulnerability_probe_expected_code` — исполнимый probe сценария HC-28.
- `TestAllNegativeScenariosExecutable.test_hc29_vulnerability_probe_expected_code` — исполнимый probe сценария HC-29.
- `TestAllNegativeScenariosExecutable.test_hc30_vulnerability_probe_expected_code` — исполнимый probe сценария HC-30.
- `TestAllNegativeScenariosExecutable.test_hc31_vulnerability_probe_expected_code` — исполнимый probe сценария HC-31.
- `TestAllNegativeScenariosExecutable.test_hc32_vulnerability_probe_expected_code` — исполнимый probe сценария HC-32.
- `TestAllNegativeScenariosExecutable.test_hc33_vulnerability_probe_expected_code` — исполнимый probe сценария HC-33.

`laboratory-python/test_laboratory_services.py` (6):

- `TestLISService.test_get_ordered_investigations` — получение списка назначенных исследований.
- `TestLISService.test_get_investigation` — получение одного исследования по ID.
- `TestLISService.test_complete_investigation_not_found` — завершение отсутствующего исследования возвращает `None`.
- `TestSampleStorageService.test_register_sample` — регистрация образца и возврат сохраненной записи.
- `TestSampleStorageService.test_move_sample_to_storage_not_found` — перенос отсутствующего образца возвращает `None`.
- `TestAnalyzerService.test_create_analyzer` — создание анализатора с возвратом данных.

`llm-python/test_llm_service.py` (4):

- `TestLLMService.test_generate_report_completed` — генерация текста для завершенного исследования.
- `TestLLMService.test_generate_report_incomplete` — генерация текста для незавершенного исследования.
- `TestLLMService.test_get_investigation` — чтение исследования по ID из сервиса.
- `TestLLMService.test_generate_and_save_not_found` — корректная ошибка при отсутствии исследования.
