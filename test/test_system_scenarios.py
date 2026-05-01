

import os

import psycopg2
import pytest
import requests


PORTAL_URL = os.getenv("PORTAL_URL", "http://localhost:8080")
PHARMACY_URL = os.getenv("PHARMACY_URL", "http://localhost:8081")
LAB_URL = os.getenv("LAB_URL", "http://localhost:8082")
LLM_URL = os.getenv("LLM_URL", "http://localhost:8083")
DATABASE_URL = os.getenv("DATABASE_URL")


@pytest.fixture(scope="function")
def db_conn():
    if not DATABASE_URL:
        pytest.skip("DATABASE_URL is not set")

    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False

    with conn.cursor() as cur:
        cur.execute("TRUNCATE public.llm_reports CASCADE")
        cur.execute("TRUNCATE public.video_sessions CASCADE")
        cur.execute("TRUNCATE public.logs CASCADE")
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
        "medicine_id": medicine_id,
    }


def assert_success(response):
    assert response.status_code in (200, 201), response.text


def test_patient_portal_medical_card_workflow(db_conn, seed_base):
    """
    Сценарий 1.
    Пациент взаимодействует с порталом, после чего врач через портал создает запись ЭМК.

    Проверяется связь:
    пациент -> портал -> центральная БД -> врач -> портал -> ЭМК.
    """

    health = requests.get(f"{PORTAL_URL}/health", timeout=5)
    assert_success(health)

    patient_response = requests.post(
        f"{PORTAL_URL}/patients",
        json={
            "surname": "Иванов",
            "name": "Иван",
            "patronymic": "Иванович",
            "date_of_birth": "2000-01-01",
        },
        timeout=5,
    )
    assert_success(patient_response)
    patient_id = patient_response.json()["id"]

    card_response = requests.post(
        f"{PORTAL_URL}/cards",
        json={
            "patient_id": patient_id,
            "employee_id": seed_base["doctor_id"],
            "complaints": "Головная боль",
            "notes": "Первичный прием через портал",
        },
        timeout=5,
    )
    assert_success(card_response)
    card_id = card_response.json()["id"]

    with db_conn.cursor() as cur:
        cur.execute("SELECT surname, name FROM public.patients WHERE id = %s", (patient_id,))
        patient = cur.fetchone()

        cur.execute(
            """
            SELECT patient_id, employee_id, complaints, notes
            FROM public.cards
            WHERE id = %s
            """,
            (card_id,),
        )
        card = cur.fetchone()

    assert patient == ("Иванов", "Иван")
    assert card[0] == patient_id
    assert card[1] == seed_base["doctor_id"]
    assert card[2] == "Головная боль"
    assert card[3] == "Первичный прием через портал"


def test_patient_portal_laboratory_workflow(db_conn, seed_base):
    """
    Сценарий 2.
    Пациент получает результат лабораторного исследования.
    Портал создает назначение, лаборатория регистрирует образец,
    анализатор передает результат, ЛИС завершает исследование, LLM формирует отчет.

    Проверяется связь:
    пациент -> портал -> лаборатория -> ЛИС -> LLM -> центральная БД.
    """

    for url in (PORTAL_URL, LAB_URL, LLM_URL):
        assert_success(requests.get(f"{url}/health", timeout=5))

    patient_response = requests.post(
        f"{PORTAL_URL}/patients",
        json={
            "surname": "Сидоров",
            "name": "Алексей",
            "patronymic": "Игоревич",
            "date_of_birth": "1999-05-10",
        },
        timeout=5,
    )
    assert_success(patient_response)
    patient_id = patient_response.json()["id"]

    card_response = requests.post(
        f"{PORTAL_URL}/cards",
        json={
            "patient_id": patient_id,
            "employee_id": seed_base["doctor_id"],
            "complaints": "Слабость",
            "notes": "Назначить общий анализ крови",
        },
        timeout=5,
    )
    assert_success(card_response)
    card_id = card_response.json()["id"]

    investigation_response = requests.post(
        f"{PORTAL_URL}/investigations",
        json={
            "patient_id": patient_id,
            "card_id": card_id,
            "test_name": "Общий анализ крови",
        },
        timeout=5,
    )
    assert_success(investigation_response)
    investigation_id = investigation_response.json()["id"]

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
            "raw_result": "Hemoglobin=135; Leukocytes=6.2",
        },
        timeout=5,
    )
    assert_success(analyzer_result_response)

    complete_response = requests.post(
        f"{LAB_URL}/investigations/complete",
        json={
            "investigation_id": investigation_id,
            "results": "Hemoglobin=135; Leukocytes=6.2",
        },
        timeout=5,
    )
    assert_success(complete_response)

    llm_response = requests.post(
        f"{LLM_URL}/generate",
        json={"investigation_id": investigation_id},
        timeout=5,
    )
    assert_success(llm_response)

    with db_conn.cursor() as cur:
        cur.execute(
            """
            SELECT status, results
            FROM public.laboratory_investigations
            WHERE id = %s
            """,
            (investigation_id,),
        )
        investigation = cur.fetchone()

        cur.execute("SELECT COUNT(*) FROM public.samples WHERE investigation_id = %s", (investigation_id,))
        samples_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM public.analyzer_results WHERE investigation_id = %s", (investigation_id,))
        analyzer_results_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM public.llm_reports WHERE investigation_id = %s", (investigation_id,))
        reports_count = cur.fetchone()[0]

    assert investigation[0] == "COMPLETED"
    assert investigation[1] == "Hemoglobin=135; Leukocytes=6.2"
    assert samples_count == 1
    assert analyzer_results_count == 1
    assert reports_count == 1


def test_patient_portal_pharmacy_workflow(db_conn, seed_base):
    """
    Сценарий 3.
    Пациент получает лекарство по электронному рецепту.
    Портал создает рецепт, аптека получает рецепт,
    QR-сканер фиксирует рецепт и препарат, затем склад списывает лекарство.

    Проверяется связь:
    пациент -> портал -> аптека -> АИС -> QR-сканер -> склад лекарств.
    """

    for url in (PORTAL_URL, PHARMACY_URL):
        assert_success(requests.get(f"{url}/health", timeout=5))

    patient_response = requests.post(
        f"{PORTAL_URL}/patients",
        json={
            "surname": "Кузнецов",
            "name": "Максим",
            "patronymic": "Олегович",
            "date_of_birth": "1998-03-15",
        },
        timeout=5,
    )
    assert_success(patient_response)
    patient_id = patient_response.json()["id"]

    card_response = requests.post(
        f"{PORTAL_URL}/cards",
        json={
            "patient_id": patient_id,
            "employee_id": seed_base["doctor_id"],
            "complaints": "Температура",
            "notes": "Назначить препарат",
        },
        timeout=5,
    )
    assert_success(card_response)
    card_id = card_response.json()["id"]

    prescription_response = requests.post(
        f"{PORTAL_URL}/prescriptions",
        json={
            "patient_id": patient_id,
            "employee_id": seed_base["doctor_id"],
            "card_id": card_id,
            "medicine_id": seed_base["medicine_id"],
            "medicine_name": "Парацетамол",
            "dosage_instructions": "По 1 таблетке 2 раза в день",
        },
        timeout=5,
    )
    assert_success(prescription_response)
    prescription_id = prescription_response.json()["id"]

    get_prescription_response = requests.get(f"{PHARMACY_URL}/prescriptions/{prescription_id}", timeout=5)
    assert_success(get_prescription_response)
    assert get_prescription_response.json()["id"] == prescription_id

    scan_prescription_response = requests.post(
        f"{PHARMACY_URL}/scanner/prescription",
        json={"prescription_id": prescription_id, "code": f"RX-{prescription_id}"},
        timeout=5,
    )
    assert_success(scan_prescription_response)

    scan_medicine_response = requests.post(
        f"{PHARMACY_URL}/scanner/medicine",
        json={"medicine_id": seed_base["medicine_id"], "code": f"MED-{seed_base['medicine_id']}"},
        timeout=5,
    )
    assert_success(scan_medicine_response)

    dispense_response = requests.post(
        f"{PHARMACY_URL}/dispense",
        json={"prescription_id": prescription_id, "quantity": 1},
        timeout=5,
    )
    assert_success(dispense_response)

    with db_conn.cursor() as cur:
        cur.execute("SELECT status FROM public.prescriptions WHERE id = %s", (prescription_id,))
        prescription_status = cur.fetchone()[0]

        cur.execute("SELECT quantity FROM public.warehouse_stock WHERE medicine_id = %s", (seed_base["medicine_id"],))
        stock_quantity = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM public.scanner_events WHERE prescription_id = %s", (prescription_id,))
        prescription_scan_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM public.scanner_events WHERE medicine_id = %s", (seed_base["medicine_id"],))
        medicine_scan_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM public.dispense_events WHERE prescription_id = %s", (prescription_id,))
        dispense_count = cur.fetchone()[0]

    assert prescription_status == "DISPENSED"
    assert stock_quantity == 9
    assert prescription_scan_count == 1
    assert medicine_scan_count == 1
    assert dispense_count == 1