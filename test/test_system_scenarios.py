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


def test_patient_views_medical_card_results_and_prescriptions(db_conn, seed_base):
    """
    Сценарий пациента.
    Пациент получает запись ЭМК, лабораторный результат, LLM-отчет и рецепт.
    Тест проверяет, что данные из портала, лаборатории, LLM и аптеки сходятся
    в общей медицинской карте пациента.
    """

    for url in (PORTAL_URL, LAB_URL, LLM_URL, PHARMACY_URL):
        assert_success(requests.get(f"{url}/health", timeout=5))

    patient_id = create_patient()
    appointment_id = create_appointment(
        patient_id,
        seed_base["doctor_id"],
        "2026-05-05T09:30:00Z",
        "Первичная консультация терапевта",
    )
    card_id = create_card(
        patient_id,
        seed_base["doctor_id"],
        "Слабость и температура",
        "Назначены анализ крови и жаропонижающий препарат",
    )
    investigation_id = create_investigation(patient_id, card_id, "Общий анализ крови")
    prescription_id = create_prescription(
        patient_id,
        seed_base["doctor_id"],
        card_id,
        seed_base["medicine_id"],
    )

    lab_results = "Hemoglobin=135; Leukocytes=6.2"
    complete_lab_analysis(investigation_id, lab_results)

    report_response = requests.post(
        f"{LLM_URL}/generate",
        json={"investigation_id": investigation_id},
        timeout=5,
    )
    assert_success(report_response)

    prescription_response = requests.get(f"{PHARMACY_URL}/prescriptions/{prescription_id}", timeout=5)
    assert_success(prescription_response)

    with db_conn.cursor() as cur:
        cur.execute(
            """
            SELECT p.surname, p.name, c.complaints, c.notes, li.test_name,
                   li.status, li.results, pr.medicine_name, pr.dosage_instructions,
                   lr.report_text, a.status, a.reason
            FROM public.patients p
            JOIN public.appointments a ON a.patient_id = p.id
            JOIN public.cards c ON c.patient_id = p.id
            JOIN public.laboratory_investigations li ON li.card_id = c.id
            JOIN public.prescriptions pr ON pr.card_id = c.id
            JOIN public.llm_reports lr ON lr.investigation_id = li.id
            WHERE p.id = %s AND a.id = %s
            """,
            (patient_id, appointment_id),
        )
        medical_card_view = cur.fetchone()

    assert medical_card_view is not None
    assert medical_card_view[0:2] == ("Иванов", "Иван")
    assert medical_card_view[2] == "Слабость и температура"
    assert medical_card_view[4] == "Общий анализ крови"
    assert medical_card_view[5] == "COMPLETED"
    assert medical_card_view[6] == lab_results
    assert medical_card_view[7] == "Парацетамол"
    assert "после еды" in medical_card_view[8]
    assert "Hemoglobin" in medical_card_view[9]
    assert medical_card_view[10] == "CONFIRMED"
    assert medical_card_view[11] == "Первичная консультация терапевта"


def test_doctor_creates_orders_and_receives_lab_report(db_conn, seed_base):
    """
    Сценарий врача.
    Врач открывает ЭМК пациента, добавляет запись, назначает анализ и лекарство.
    Лаборатория выполняет анализ, LLM формирует отчет, аптека получает рецепт.
    """

    for url in (PORTAL_URL, LAB_URL, LLM_URL, PHARMACY_URL):
        assert_success(requests.get(f"{url}/health", timeout=5))

    patient_id = create_patient("Сидоров", "Алексей")
    card_id = create_card(
        patient_id,
        seed_base["doctor_id"],
        "Головокружение",
        "Врач назначил анализ крови и медикаментозную терапию",
    )
    investigation_id = create_investigation(patient_id, card_id, "Биохимический анализ крови")
    prescription_id = create_prescription(
        patient_id,
        seed_base["doctor_id"],
        card_id,
        seed_base["medicine_id"],
    )

    ordered_response = requests.get(f"{LAB_URL}/investigations/ordered", timeout=5)
    assert_success(ordered_response)
    ordered_ids = {item["id"] for item in ordered_response.json()}
    assert investigation_id in ordered_ids

    doctor_lab_response = requests.get(f"{LAB_URL}/investigations/{investigation_id}", timeout=5)
    assert_success(doctor_lab_response)
    assert doctor_lab_response.json()["status"] == "ORDERED"

    lab_results = "Glucose=5.1; ALT=22; AST=20"
    complete_lab_analysis(investigation_id, lab_results)

    report_response = requests.post(
        f"{LLM_URL}/generate",
        json={"investigation_id": investigation_id},
        timeout=5,
    )
    assert_success(report_response)

    reports_response = requests.get(f"{LLM_URL}/reports/{investigation_id}", timeout=5)
    assert_success(reports_response)
    assert len(reports_response.json()) == 1

    pharmacy_response = requests.get(f"{PHARMACY_URL}/prescriptions/{prescription_id}", timeout=5)
    assert_success(pharmacy_response)
    assert pharmacy_response.json()["status"] == "CREATED"

    with db_conn.cursor() as cur:
        cur.execute(
            """
            SELECT c.employee_id, li.status, li.results, pr.employee_id,
                   COUNT(ar.id), COUNT(lr.id)
            FROM public.cards c
            JOIN public.laboratory_investigations li ON li.card_id = c.id
            JOIN public.prescriptions pr ON pr.card_id = c.id
            LEFT JOIN public.analyzer_results ar ON ar.investigation_id = li.id
            LEFT JOIN public.llm_reports lr ON lr.investigation_id = li.id
            WHERE c.id = %s
            GROUP BY c.employee_id, li.status, li.results, pr.employee_id
            """,
            (card_id,),
        )
        doctor_workflow = cur.fetchone()

    assert doctor_workflow[0] == seed_base["doctor_id"]
    assert doctor_workflow[1] == "COMPLETED"
    assert doctor_workflow[2] == lab_results
    assert doctor_workflow[3] == seed_base["doctor_id"]
    assert doctor_workflow[4] == 1
    assert doctor_workflow[5] == 1


def test_admin_monitors_services_equipment_and_stock(db_conn, seed_base):
    """
    Сценарий администратора / ИТ.
    Администратор проверяет доступность сервисов, мониторинг оборудования,
    самодиагностику и изменение аптечного склада после выдачи лекарства.
    """

    for url in (PORTAL_URL, LAB_URL, LLM_URL, PHARMACY_URL):
        health = requests.get(f"{url}/health", timeout=5)
        assert_success(health)
        assert health.json()["status"] == "ok"

    equipment_response = requests.post(
        f"{LAB_URL}/equipment",
        json={
            "name": "Analyzer Rack A",
            "equipment_type": "analyzer",
            "location": "Laboratory room 2",
        },
        timeout=5,
    )
    assert_success(equipment_response)
    equipment_id = equipment_response.json()["id"]

    metric_response = requests.post(
        f"{LAB_URL}/monitoring/metrics",
        json={
            "equipment_id": equipment_id,
            "metric_name": "temperature",
            "metric_value": "36.6",
        },
        timeout=5,
    )
    assert_success(metric_response)

    diagnostic_response = requests.post(
        f"{LAB_URL}/diagnostics",
        json={
            "equipment_id": equipment_id,
            "diagnostic_status": "OK",
            "details": "Плановая самодиагностика завершена без ошибок",
        },
        timeout=5,
    )
    assert_success(diagnostic_response)

    patient_id = create_patient("Кузнецов", "Максим")
    card_id = create_card(
        patient_id,
        seed_base["doctor_id"],
        "Температура",
        "Назначен препарат, администратор контролирует склад",
    )
    prescription_id = create_prescription(
        patient_id,
        seed_base["doctor_id"],
        card_id,
        seed_base["medicine_id"],
    )

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
        json={"prescription_id": prescription_id, "quantity": 2},
        timeout=5,
    )
    assert_success(dispense_response)

    with db_conn.cursor() as cur:
        cur.execute(
            """
            SELECT me.status, mm.metric_name, mm.metric_value,
                   sd.diagnostic_status, sd.details
            FROM public.medical_equipment me
            JOIN public.monitoring_metrics mm ON mm.equipment_id = me.id
            JOIN public.self_diagnostics sd ON sd.equipment_id = me.id
            WHERE me.id = %s
            """,
            (equipment_id,),
        )
        equipment_state = cur.fetchone()

        cur.execute(
            """
            SELECT pr.status, ws.quantity, COUNT(DISTINCT se.id), COUNT(DISTINCT de.id)
            FROM public.prescriptions pr
            JOIN public.warehouse_stock ws ON ws.medicine_id = pr.medicine_id
            LEFT JOIN public.scanner_events se
                ON se.prescription_id = pr.id OR se.medicine_id = pr.medicine_id
            LEFT JOIN public.dispense_events de ON de.prescription_id = pr.id
            WHERE pr.id = %s
            GROUP BY pr.status, ws.quantity
            """,
            (prescription_id,),
        )
        stock_state = cur.fetchone()

    assert equipment_state[0] == "ACTIVE"
    assert equipment_state[1:4] == ("temperature", "36.6", "OK")
    assert "без ошибок" in equipment_state[4]
    assert stock_state[0] == "DISPENSED"
    assert stock_state[1] == 8
    assert stock_state[2] == 2
    assert stock_state[3] == 1
