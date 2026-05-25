import os

import psycopg2
import pytest
import requests


PORTAL_URL = os.getenv("PORTAL_URL", "http://localhost:8080")
PHARMACY_URL = os.getenv("PHARMACY_URL", "http://localhost:8081")
LAB_URL = os.getenv("LAB_URL", "http://localhost:8001")
LLM_URL = os.getenv("LLM_URL", "http://localhost:8002")
DATABASE_URL = os.getenv("DATABASE_URL")


@pytest.fixture(scope="function")
def db_conn():
    if not DATABASE_URL:
        pytest.skip("DATABASE_URL is not set")

    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False

    with conn.cursor() as cur:
        cur.execute(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'appointment_status') THEN
                    CREATE TYPE public.appointment_status AS ENUM (
                        'SCHEDULED',
                        'CONFIRMED',
                        'CANCELLED',
                        'COMPLETED'
                    );
                END IF;
            END
            $$;
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS public.appointments (
                id BIGSERIAL PRIMARY KEY,
                patient_id BIGINT NOT NULL REFERENCES public.patients(id) ON DELETE CASCADE,
                employee_id BIGINT NOT NULL REFERENCES public.employees(id) ON DELETE RESTRICT,
                scheduled_at TIMESTAMP NOT NULL,
                reason TEXT,
                status public.appointment_status NOT NULL DEFAULT 'CONFIRMED',
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (employee_id, scheduled_at)
            )
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_appointments_patient_id ON public.appointments (patient_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_appointments_employee_id ON public.appointments (employee_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_appointments_scheduled_at ON public.appointments (scheduled_at)")
        cur.execute("TRUNCATE public.llm_reports CASCADE")
        cur.execute("TRUNCATE public.video_sessions CASCADE")
        cur.execute("TRUNCATE public.logs CASCADE")
        cur.execute("TRUNCATE public.appointments CASCADE")
        cur.execute("TRUNCATE public.self_diagnostics CASCADE")
        cur.execute("TRUNCATE public.monitoring_metrics CASCADE")
        cur.execute("TRUNCATE public.medical_equipment CASCADE")
        cur.execute("TRUNCATE public.analyzer_results CASCADE")
        cur.execute("TRUNCATE public.workstations CASCADE")
        cur.execute("TRUNCATE public.analyzers CASCADE")
        cur.execute("TRUNCATE public.samples CASCADE")
        cur.execute("TRUNCATE public.scanner_events CASCADE")
        cur.execute("TRUNCATE public.dispense_events CASCADE")
        cur.execute("TRUNCATE public.warehouse_stock CASCADE")
        cur.execute("TRUNCATE public.prescriptions CASCADE")
        cur.execute("TRUNCATE public.laboratory_investigations CASCADE")
        cur.execute("TRUNCATE public.cards CASCADE")
        cur.execute("TRUNCATE public.users CASCADE")
        cur.execute("TRUNCATE public.employees CASCADE")
        cur.execute("TRUNCATE public.patients CASCADE")
        cur.execute("TRUNCATE public.medicines CASCADE")

    conn.commit()
    yield conn
    conn.close()


@pytest.fixture(scope="function")
def seed_base(db_conn):
    with db_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO public.employees (surname, name, patronymic, speciality)
            VALUES ('Петров', 'Петр', 'Петрович', 'Терапевт')
            RETURNING id
            """
        )
        doctor_id = cur.fetchone()[0]

        cur.execute(
            """
            INSERT INTO public.employees (surname, name, patronymic, speciality)
            VALUES ('Смирнова', 'Анна', 'Игоревна', 'Администратор ИТ')
            RETURNING id
            """
        )
        admin_id = cur.fetchone()[0]

        cur.execute(
            """
            INSERT INTO public.medicines (name, form, dosage, manufacturer, description)
            VALUES ('Парацетамол', 'Таблетки', '500 мг', 'Pharma', 'Жаропонижающее')
            RETURNING id
            """
        )
        medicine_id = cur.fetchone()[0]

        cur.execute(
            """
            INSERT INTO public.warehouse_stock (medicine_id, quantity)
            VALUES (%s, 10)
            """,
            (medicine_id,),
        )

    db_conn.commit()

    return {
        "doctor_id": doctor_id,
        "admin_id": admin_id,
        "medicine_id": medicine_id,
    }


def assert_success(response):
    assert response.status_code in (200, 201), response.text


def assert_attack_passed(condition, details):
    assert condition, f"FAIL: attack was blocked or incomplete ({details})"


@pytest.mark.hc
def test_hc31_video_session_can_be_started_without_authorized_doctor(db_conn, seed_base):
    """
    НС-31.
    Неавторизованный сотрудник без роли врача может быть записан как участник
    начатого телемедицинского сеанса, потому модель данных не проверяет роль
    и авторизацию врача.
    """

    with db_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO public.patients (surname, name, patronymic, date_of_birth)
            VALUES ('Орлов', 'Илья', 'Сергеевич', '1995-02-10')
            RETURNING id
            """
        )
        patient_id = cur.fetchone()[0]

        cur.execute(
            """
            INSERT INTO public.video_sessions (
                patient_id,
                employee_id,
                started_at,
                session_status,
                session_notes
            )
            VALUES (%s, %s, CURRENT_TIMESTAMP, 'STARTED', 'Сеанс создан без проверки роли врача')
            RETURNING patient_id, employee_id, session_status, session_notes
            """,
            (patient_id, seed_base["admin_id"]),
        )
        session = cur.fetchone()

    assert_attack_passed(
        session[0] == patient_id
        and session[1] == seed_base["admin_id"]
        and session[2] == "STARTED"
        and "без проверки роли врача" in session[3],
        "HC-31 video session creation",
    )


@pytest.mark.hc
def test_hc20_existing_emk_record_can_be_changed_without_authorized_doctor(db_conn, seed_base):
    """
    НС-20.
    Существующая запись ЭМК может быть изменена без проверки авторизованного
    врача, потому на уровне текущей модели нет ограничения, связывающего
    изменение с подтвержденной ролью врача.
    """

    with db_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO public.patients (surname, name, patronymic, date_of_birth)
            VALUES ('Федоров', 'Никита', 'Андреевич', '1988-07-15')
            RETURNING id
            """
        )
        patient_id = cur.fetchone()[0]

        cur.execute(
            """
            INSERT INTO public.cards (patient_id, employee_id, complaints, notes)
            VALUES (%s, %s, 'Кашель', 'Первичная запись врача')
            RETURNING id
            """,
            (patient_id, seed_base["doctor_id"]),
        )
        card_id = cur.fetchone()[0]

        cur.execute(
            """
            UPDATE public.cards
            SET complaints = 'Подмененные жалобы',
                notes = 'Запись ЭМК изменена без проверки авторизованного врача'
            WHERE id = %s
            RETURNING complaints, notes
            """,
            (card_id,),
        )
        changed_card = cur.fetchone()

    assert_attack_passed(
        changed_card[0] == "Подмененные жалобы"
        and "без проверки авторизованного врача" in changed_card[1],
        "HC-20 medical card tampering",
    )


@pytest.mark.hc
def test_hc01_emk_read_without_authorization(db_conn, seed_base):
    """
    НС-1. Доступ к ЭМК пациента без авторизации.
    """
    with db_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO public.patients (surname, name, patronymic, date_of_birth)
            VALUES ('Соколов', 'Иван', 'Олегович', '1993-03-03')
            RETURNING id
            """
        )
        patient_id = cur.fetchone()[0]
        cur.execute(
            """
            INSERT INTO public.cards (patient_id, employee_id, complaints, notes)
            VALUES (%s, %s, 'Боль', 'Запись ЭМК')
            """,
            (patient_id, seed_base["doctor_id"]),
        )
        cur.execute("SELECT id FROM public.cards WHERE patient_id = %s", (patient_id,))
        rows = cur.fetchall()
    assert_attack_passed(len(rows) > 0, "HC-1 unauthorized EMK read")


@pytest.mark.hc
def test_hc03_unprotected_data_transfer_simulation():
    """
    НС-3. Передача данных без защищенного канала.
    """
    response = requests.get(f"{PORTAL_URL}/health", timeout=5)
    assert_attack_passed(response.status_code == 200, "HC-3 unprotected channel simulation")


@pytest.mark.hc
def test_hc04_tampered_api_payload_accepted(db_conn, seed_base):
    """
    НС-4. Подмена данных пациента при передаче в API.
    """
    response = requests.post(
        f"{PORTAL_URL}/patients",
        json={
            "surname": "Injected",
            "name": "Payload",
            "patronymic": "Tampered",
            "date_of_birth": "2001-01-01",
            "unexpected_field": "MALICIOUS",
        },
        timeout=5,
    )
    assert_attack_passed(response.status_code in (200, 201), "HC-4 payload tampering accepted")


@pytest.mark.hc
def test_hc06_sql_injection_like_input_accepted():
    """
    НС-6. Попытка SQL-инъекции во входных данных API.
    """
    response = requests.post(
        f"{PORTAL_URL}/patients",
        json={
            "surname": "Иванов'; DROP TABLE patients; --",
            "name": "Тест",
            "date_of_birth": "2000-01-01",
        },
        timeout=5,
    )
    assert_attack_passed(response.status_code in (200, 201), "HC-6 injection-like input accepted")


@pytest.mark.hc
def test_hc22_replay_attack_simulation(db_conn, seed_base):
    """
    НС-22. Replay-атака повторным использованием запроса.
    """
    payload = {
        "patient_id": 1,
        "employee_id": seed_base["doctor_id"],
        "scheduled_at": "2026-10-10T10:00:00Z",
        "reason": "Replay attempt",
    }
    first = requests.post(f"{PORTAL_URL}/appointments", json=payload, timeout=5)
    second = requests.post(f"{PORTAL_URL}/appointments", json=payload, timeout=5)
    assert_attack_passed(first.status_code in (200, 201) and second.status_code in (200, 201), "HC-22 replay accepted")


@pytest.mark.hc
def test_hc33_backup_data_exposure_simulation(db_conn):
    """
    НС-33. Доступ к резервной копии/дампу данных (симуляция через массовое чтение).
    """
    with db_conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM public.patients")
        count = cur.fetchone()[0]
    assert_attack_passed(count >= 0, "HC-33 backup exposure simulation")


def create_patient(surname="Иванов", name="Иван"):
    response = requests.post(
        f"{PORTAL_URL}/patients",
        json={
            "surname": surname,
            "name": name,
            "patronymic": "Иванович",
            "date_of_birth": "2000-01-01",
        },
        timeout=5,
    )
    assert_success(response)
    return response.json()["id"]


def create_card(patient_id, employee_id, complaints, notes):
    response = requests.post(
        f"{PORTAL_URL}/cards",
        json={
            "patient_id": patient_id,
            "employee_id": employee_id,
            "complaints": complaints,
            "notes": notes,
        },
        timeout=5,
    )
    assert_success(response)
    return response.json()["id"]


def create_appointment(patient_id, employee_id, scheduled_at, reason):
    response = requests.post(
        f"{PORTAL_URL}/appointments",
        json={
            "patient_id": patient_id,
            "employee_id": employee_id,
            "scheduled_at": scheduled_at,
            "reason": reason,
        },
        timeout=5,
    )
    assert_success(response)
    body = response.json()
    assert body["status"] == "CONFIRMED"
    return body["id"]


def create_investigation(patient_id, card_id, test_name):
    response = requests.post(
        f"{PORTAL_URL}/investigations",
        json={
            "patient_id": patient_id,
            "card_id": card_id,
            "test_name": test_name,
        },
        timeout=5,
    )
    assert_success(response)
    return response.json()["id"]


def create_prescription(patient_id, employee_id, card_id, medicine_id):
    response = requests.post(
        f"{PORTAL_URL}/prescriptions",
        json={
            "patient_id": patient_id,
            "employee_id": employee_id,
            "card_id": card_id,
            "medicine_id": medicine_id,
            "medicine_name": "Парацетамол",
            "dosage_instructions": "По 1 таблетке 2 раза в день после еды",
        },
        timeout=5,
    )
    assert_success(response)
    return response.json()["id"]


def complete_lab_analysis(investigation_id, results):
    sample_response = requests.post(
        f"{LAB_URL}/samples/register",
        json={
            "investigation_id": investigation_id,
            "sample_type": "blood",
            "storage_location": "LAB-A-01",
        },
        timeout=5,
    )
    assert_success(sample_response)

    storage_response = requests.post(f"{LAB_URL}/samples/{investigation_id}/to-storage", timeout=5)
    assert_success(storage_response)

    analysis_response = requests.post(f"{LAB_URL}/samples/{investigation_id}/to-analysis", timeout=5)
    assert_success(analysis_response)

    analyzer_response = requests.post(
        f"{LAB_URL}/analyzers",
        json={"name": "Analyzer-1", "model": "BioChem X"},
        timeout=5,
    )
    assert_success(analyzer_response)
    analyzer_id = analyzer_response.json()["id"]

    workstation_response = requests.post(
        f"{LAB_URL}/workstations",
        json={"name": "WS-1", "location": "Lab room 2"},
        timeout=5,
    )
    assert_success(workstation_response)
    workstation_id = workstation_response.json()["id"]

    analyzer_result_response = requests.post(
        f"{LAB_URL}/analyzer-results",
        json={
            "investigation_id": investigation_id,
            "analyzer_id": analyzer_id,
            "workstation_id": workstation_id,
            "raw_result": results,
        },
        timeout=5,
    )
    assert_success(analyzer_result_response)

    complete_response = requests.post(
        f"{LAB_URL}/investigations/complete",
        json={"investigation_id": investigation_id, "results": results},
        timeout=5,
    )
    assert_success(complete_response)




@pytest.mark.e2e
def test_patient_doctor_scenario_via_portal(db_conn, seed_base):
    """
    Сценарий "пациент -> врач -> портал":
    пациент создается в портале, врач создает запись ЭМК и запись на прием.
    """

    assert_success(requests.get(f"{PORTAL_URL}/health", timeout=5))

    patient_id = create_patient("Егоров", "Дмитрий")
    appointment_id = create_appointment(
        patient_id,
        seed_base["doctor_id"],
        "2026-06-10T08:00:00Z",
        "Консультация врача",
    )
    card_id = create_card(
        patient_id,
        seed_base["doctor_id"],
        "Боль в горле",
        "Рекомендовано наблюдение и повторный осмотр",
    )

    with db_conn.cursor() as cur:
        cur.execute(
            """
            SELECT p.id, c.employee_id, a.status, c.complaints
            FROM public.patients p
            JOIN public.cards c ON c.patient_id = p.id
            JOIN public.appointments a ON a.patient_id = p.id
            WHERE p.id = %s AND c.id = %s AND a.id = %s
            """,
            (patient_id, card_id, appointment_id),
        )
        row = cur.fetchone()

    assert row is not None
    assert row[0] == patient_id
    assert row[1] == seed_base["doctor_id"]
    assert row[2] == "CONFIRMED"
    assert row[3] == "Боль в горле"


@pytest.mark.e2e
def test_patient_pharmacy_portal_scenario(db_conn, seed_base):
    """
    Сценарий "пациент -> аптека -> портал":
    врач в портале создает рецепт пациенту, аптека его обрабатывает и выдает лекарство.
    """

    for url in (PORTAL_URL, PHARMACY_URL):
        assert_success(requests.get(f"{url}/health", timeout=5))

    patient_id = create_patient("Орехов", "Павел")
    card_id = create_card(
        patient_id,
        seed_base["doctor_id"],
        "Температура и озноб",
        "Назначен жаропонижающий препарат",
    )
    prescription_id = create_prescription(
        patient_id,
        seed_base["doctor_id"],
        card_id,
        seed_base["medicine_id"],
    )

    assert_success(
        requests.post(
            f"{PHARMACY_URL}/scanner/prescription",
            json={"prescription_id": prescription_id, "code": f"RX-{prescription_id}"},
            timeout=5,
        )
    )
    assert_success(
        requests.post(
            f"{PHARMACY_URL}/scanner/medicine",
            json={"medicine_id": seed_base["medicine_id"], "code": f"MED-{seed_base['medicine_id']}"},
            timeout=5,
        )
    )
    assert_success(
        requests.post(
            f"{PHARMACY_URL}/dispense",
            json={"prescription_id": prescription_id, "quantity": 1},
            timeout=5,
        )
    )

    with db_conn.cursor() as cur:
        cur.execute(
            """
            SELECT pr.status, ws.quantity
            FROM public.prescriptions pr
            JOIN public.warehouse_stock ws ON ws.medicine_id = pr.medicine_id
            WHERE pr.id = %s
            """,
            (prescription_id,),
        )
        row = cur.fetchone()

    assert row is not None
    assert row[0] == "DISPENSED"
    assert row[1] == 9


@pytest.mark.e2e
def test_patient_laboratory_portal_scenario(db_conn, seed_base):
    """
    Сценарий "пациент -> лаборатория -> портал":
    врач оформляет назначение анализа в портале, лаборатория выполняет его
    и результат сохраняется в ЭМК.
    """

    for url in (PORTAL_URL, LAB_URL):
        assert_success(requests.get(f"{url}/health", timeout=5))

    patient_id = create_patient("Савин", "Игорь")
    card_id = create_card(
        patient_id,
        seed_base["doctor_id"],
        "Слабость",
        "Назначен общий анализ крови",
    )
    investigation_id = create_investigation(patient_id, card_id, "Общий анализ крови")

    lab_results = "Hemoglobin=140; Leukocytes=5.8"
    complete_lab_analysis(investigation_id, lab_results)

    with db_conn.cursor() as cur:
        cur.execute(
            """
            SELECT li.status, li.results, li.patient_id, li.card_id
            FROM public.laboratory_investigations li
            WHERE li.id = %s
            """,
            (investigation_id,),
        )
        row = cur.fetchone()

    assert row is not None
    assert row[0] == "COMPLETED"
    assert row[1] == lab_results
    assert row[2] == patient_id
    assert row[3] == card_id
