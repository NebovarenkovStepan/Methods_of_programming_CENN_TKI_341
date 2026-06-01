import hashlib
import hmac
import json
import os
import time

import pytest
import requests


PORTAL_URL = os.getenv("PORTAL_URL", "http://localhost:8080")
PHARMACY_URL = os.getenv("PHARMACY_URL", "http://localhost:8081")
LAB_URL = os.getenv("LAB_URL", "http://localhost:8001")
INTEGRITY_SECRET = os.getenv("INTEGRITY_SECRET", "test-secret")

DOCTOR_SUBJECT_ID = "123"
DOCTOR_ID = 1
MEDICINE_ID = 1


def _json_bytes(payload):
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def _signature(payload):
    return hmac.new(INTEGRITY_SECRET.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def _secure_headers(payload, subject_id=DOCTOR_SUBJECT_ID, roles="doctor"):
    return {
        "Content-Type": "application/json",
        "X-Trusted-Channel": "vpn",
        "X-Subject-ID": subject_id,
        "X-Roles": roles,
        "X-Request-ID": f"system-test-{time.time_ns()}",
        "X-Signature": _signature(payload),
    }


def assert_success(response):
    assert response.status_code in (200, 201), response.text


def assert_health(url):
    response = requests.get(f"{url}/health", timeout=5)
    assert_success(response)


def post_json(url, payload, subject_id=DOCTOR_SUBJECT_ID, roles="doctor"):
    body = _json_bytes(payload)
    response = requests.post(
        url,
        data=body,
        headers=_secure_headers(body, subject_id=subject_id, roles=roles),
        timeout=5,
    )
    assert_success(response)
    return response.json()


def create_patient(surname, name):
    patient = post_json(
        f"{PORTAL_URL}/patients",
        {
            "surname": surname,
            "name": name,
            "patronymic": "Иванович",
            "date_of_birth": "2000-01-01",
        },
    )
    assert patient["id"] > 0
    return patient["id"]


def create_card(patient_id, complaints, notes):
    card = post_json(
        f"{PORTAL_URL}/cards",
        {
            "patient_id": patient_id,
            "employee_id": DOCTOR_ID,
            "complaints": complaints,
            "notes": notes,
        },
    )
    assert card["id"] > 0
    return card["id"]


def create_appointment(patient_id, scheduled_at, reason):
    appointment = post_json(
        f"{PORTAL_URL}/appointments",
        {
            "patient_id": patient_id,
            "employee_id": DOCTOR_ID,
            "scheduled_at": scheduled_at,
            "reason": reason,
        },
    )
    assert appointment["id"] > 0
    assert appointment["status"] == "CONFIRMED"
    return appointment["id"]


def create_investigation(patient_id, card_id, test_name):
    investigation = post_json(
        f"{PORTAL_URL}/investigations",
        {
            "patient_id": patient_id,
            "card_id": card_id,
            "test_name": test_name,
        },
    )
    assert investigation["id"] > 0
    assert investigation["status"] == "ORDERED"
    return investigation["id"]


def create_prescription(patient_id, card_id):
    prescription = post_json(
        f"{PORTAL_URL}/prescriptions",
        {
            "patient_id": patient_id,
            "employee_id": DOCTOR_ID,
            "card_id": card_id,
            "medicine_id": MEDICINE_ID,
            "medicine_name": "Парацетамол",
            "dosage_instructions": "По 1 таблетке 2 раза в день после еды",
        },
    )
    assert prescription["id"] > 0
    assert prescription["status"] == "CREATED"
    return prescription["id"]


@pytest.mark.e2e
def test_patient_doctor_scenario_via_portal():
    """
    Сценарий "пациент -> врач -> портал":
    пациент создается в портале, врач создает запись ЭМК и запись на прием.
    """
    assert_health(PORTAL_URL)

    patient_id = create_patient("Егоров", "Дмитрий")
    card_id = create_card(
        patient_id,
        "Боль в горле",
        "Рекомендовано наблюдение и повторный осмотр",
    )
    appointment_id = create_appointment(
        patient_id,
        "2026-06-10T08:00:00Z",
        "Консультация врача",
    )

    assert patient_id > 0
    assert card_id > 0
    assert appointment_id > 0


@pytest.mark.e2e
def test_patient_laboratory_portal_scenario():
    """
    Сценарий "пациент -> лаборатория -> портал":
    врач оформляет назначение анализа в портале, лабораторный сервис доступен.
    """
    assert_health(PORTAL_URL)
    assert_health(LAB_URL)

    patient_id = create_patient("Савин", "Игорь")
    card_id = create_card(
        patient_id,
        "Слабость",
        "Назначен общий анализ крови",
    )
    investigation_id = create_investigation(patient_id, card_id, "Общий анализ крови")

    assert patient_id > 0
    assert card_id > 0
    assert investigation_id > 0


@pytest.mark.e2e
def test_patient_pharmacy_portal_scenario():
    """
    Сценарий "пациент -> аптека -> портал":
    врач создает рецепт пациенту в портале, аптечный сервис доступен.
    """
    assert_health(PORTAL_URL)
    assert_health(PHARMACY_URL)

    patient_id = create_patient("Орехов", "Павел")
    card_id = create_card(
        patient_id,
        "Температура и озноб",
        "Назначен жаропонижающий препарат",
    )
    prescription_id = create_prescription(patient_id, card_id)

    assert patient_id > 0
    assert card_id > 0
    assert prescription_id > 0
