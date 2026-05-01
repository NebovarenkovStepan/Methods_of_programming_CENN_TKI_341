BEGIN;

DROP TABLE IF EXISTS public.llm_reports CASCADE;
DROP TABLE IF EXISTS public.video_sessions CASCADE;
DROP TABLE IF EXISTS public.logs CASCADE;
DROP TABLE IF EXISTS public.self_diagnostics CASCADE;
DROP TABLE IF EXISTS public.monitoring_metrics CASCADE;
DROP TABLE IF EXISTS public.medical_equipment CASCADE;
DROP TABLE IF EXISTS public.analyzer_results CASCADE;
DROP TABLE IF EXISTS public.workstations CASCADE;
DROP TABLE IF EXISTS public.analyzers CASCADE;
DROP TABLE IF EXISTS public.samples CASCADE;
DROP TABLE IF EXISTS public.scanner_events CASCADE;
DROP TABLE IF EXISTS public.dispense_events CASCADE;
DROP TABLE IF EXISTS public.warehouse_stock CASCADE;
DROP TABLE IF EXISTS public.medicines CASCADE;

DROP TABLE IF EXISTS public.prescriptions CASCADE;
DROP TABLE IF EXISTS public.laboratory_investigations CASCADE;
DROP TABLE IF EXISTS public.cards CASCADE;
DROP TABLE IF EXISTS public.users CASCADE;
DROP TABLE IF EXISTS public.employees CASCADE;
DROP TABLE IF EXISTS public.patients CASCADE;

DROP TYPE IF EXISTS public.log_level CASCADE;
DROP TYPE IF EXISTS public.video_session_status CASCADE;
DROP TYPE IF EXISTS public.scanner_event_type CASCADE;
DROP TYPE IF EXISTS public.sample_status CASCADE;
DROP TYPE IF EXISTS public.equipment_status CASCADE;
DROP TYPE IF EXISTS public.lab_status CASCADE;
DROP TYPE IF EXISTS public.prescription_status CASCADE;

CREATE TYPE public.lab_status AS ENUM ('ORDERED', 'COMPLETED');
CREATE TYPE public.prescription_status AS ENUM ('CREATED', 'DISPENSED', 'CANCELLED');
CREATE TYPE public.equipment_status AS ENUM ('ACTIVE', 'INACTIVE', 'ERROR', 'MAINTENANCE');
CREATE TYPE public.sample_status AS ENUM ('REGISTERED', 'IN_STORAGE', 'IN_ANALYSIS', 'COMPLETED', 'ARCHIVED');
CREATE TYPE public.scanner_event_type AS ENUM ('PRESCRIPTION_SCAN', 'MEDICINE_SCAN');
CREATE TYPE public.video_session_status AS ENUM ('CREATED', 'STARTED', 'ENDED', 'CANCELLED');
CREATE TYPE public.log_level AS ENUM ('INFO', 'WARNING', 'ERROR');

CREATE TABLE public.patients (
    id BIGSERIAL PRIMARY KEY,
    surname VARCHAR(50) NOT NULL,
    name VARCHAR(50) NOT NULL,
    patronymic VARCHAR(50),
    date_of_birth DATE
);

CREATE TABLE public.employees (
    id BIGSERIAL PRIMARY KEY,
    surname VARCHAR(50) NOT NULL,
    name VARCHAR(50) NOT NULL,
    patronymic VARCHAR(50),
    speciality VARCHAR(100) NOT NULL
);

CREATE TABLE public.users (
    id BIGSERIAL PRIMARY KEY,
    login VARCHAR(100) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    patient_id BIGINT UNIQUE REFERENCES public.patients(id) ON DELETE CASCADE,
    employee_id BIGINT UNIQUE REFERENCES public.employees(id) ON DELETE CASCADE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (
        (patient_id IS NOT NULL AND employee_id IS NULL)
        OR
        (patient_id IS NULL AND employee_id IS NOT NULL)
    )
);

CREATE TABLE public.cards (
    id BIGSERIAL PRIMARY KEY,
    patient_id BIGINT NOT NULL REFERENCES public.patients(id) ON DELETE CASCADE,
    employee_id BIGINT NOT NULL REFERENCES public.employees(id) ON DELETE RESTRICT,
    date_of_visit TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    complaints TEXT,
    notes TEXT
);

CREATE TABLE public.medicines (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    form VARCHAR(100),
    dosage VARCHAR(100),
    manufacturer VARCHAR(255),
    description TEXT
);

CREATE TABLE public.laboratory_investigations (
    id BIGSERIAL PRIMARY KEY,
    patient_id BIGINT NOT NULL REFERENCES public.patients(id) ON DELETE CASCADE,
    card_id BIGINT NOT NULL REFERENCES public.cards(id) ON DELETE CASCADE,
    test_name VARCHAR(255) NOT NULL,
    status public.lab_status NOT NULL DEFAULT 'ORDERED',
    results TEXT,
    date_ordered TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    date_completed TIMESTAMP,
    CHECK (
        (status = 'ORDERED' AND date_completed IS NULL)
        OR
        (status = 'COMPLETED')
    )
);

CREATE TABLE public.prescriptions (
    id BIGSERIAL PRIMARY KEY,
    patient_id BIGINT NOT NULL REFERENCES public.patients(id) ON DELETE CASCADE,
    employee_id BIGINT NOT NULL REFERENCES public.employees(id) ON DELETE RESTRICT,
    card_id BIGINT NOT NULL REFERENCES public.cards(id) ON DELETE CASCADE,
    medicine_id BIGINT REFERENCES public.medicines(id) ON DELETE SET NULL,
    medicine_name VARCHAR(255) NOT NULL,
    dosage_instructions TEXT NOT NULL,
    status public.prescription_status NOT NULL DEFAULT 'CREATED',
    date_of_receipt TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE public.warehouse_stock (
    id BIGSERIAL PRIMARY KEY,
    medicine_id BIGINT NOT NULL UNIQUE REFERENCES public.medicines(id) ON DELETE CASCADE,
    quantity INT NOT NULL DEFAULT 0 CHECK (quantity >= 0),
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE public.dispense_events (
    id BIGSERIAL PRIMARY KEY,
    prescription_id BIGINT NOT NULL REFERENCES public.prescriptions(id) ON DELETE CASCADE,
    medicine_id BIGINT NOT NULL REFERENCES public.medicines(id) ON DELETE RESTRICT,
    quantity INT NOT NULL DEFAULT 1 CHECK (quantity > 0),
    dispensed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE public.scanner_events (
    id BIGSERIAL PRIMARY KEY,
    event_type public.scanner_event_type NOT NULL,
    scanned_code VARCHAR(255) NOT NULL,
    prescription_id BIGINT REFERENCES public.prescriptions(id) ON DELETE SET NULL,
    medicine_id BIGINT REFERENCES public.medicines(id) ON DELETE SET NULL,
    scanned_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (
        (event_type = 'PRESCRIPTION_SCAN' AND prescription_id IS NOT NULL)
        OR
        (event_type = 'MEDICINE_SCAN' AND medicine_id IS NOT NULL)
    )
);

CREATE TABLE public.samples (
    id BIGSERIAL PRIMARY KEY,
    investigation_id BIGINT NOT NULL UNIQUE REFERENCES public.laboratory_investigations(id) ON DELETE CASCADE,
    sample_type VARCHAR(100) NOT NULL,
    storage_location VARCHAR(255),
    status public.sample_status NOT NULL DEFAULT 'REGISTERED',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE public.analyzers (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    model VARCHAR(255),
    status public.equipment_status NOT NULL DEFAULT 'ACTIVE'
);

CREATE TABLE public.workstations (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    location VARCHAR(255),
    status public.equipment_status NOT NULL DEFAULT 'ACTIVE'
);

CREATE TABLE public.analyzer_results (
    id BIGSERIAL PRIMARY KEY,
    investigation_id BIGINT NOT NULL REFERENCES public.laboratory_investigations(id) ON DELETE CASCADE,
    analyzer_id BIGINT REFERENCES public.analyzers(id) ON DELETE SET NULL,
    workstation_id BIGINT REFERENCES public.workstations(id) ON DELETE SET NULL,
    raw_result TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE public.medical_equipment (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    equipment_type VARCHAR(100) NOT NULL,
    location VARCHAR(255),
    status public.equipment_status NOT NULL DEFAULT 'ACTIVE'
);

CREATE TABLE public.monitoring_metrics (
    id BIGSERIAL PRIMARY KEY,
    equipment_id BIGINT NOT NULL REFERENCES public.medical_equipment(id) ON DELETE CASCADE,
    metric_name VARCHAR(100) NOT NULL,
    metric_value VARCHAR(100) NOT NULL,
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE public.self_diagnostics (
    id BIGSERIAL PRIMARY KEY,
    equipment_id BIGINT NOT NULL REFERENCES public.medical_equipment(id) ON DELETE CASCADE,
    diagnostic_status VARCHAR(100) NOT NULL,
    details TEXT,
    checked_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE public.logs (
    id BIGSERIAL PRIMARY KEY,
    service_name VARCHAR(100) NOT NULL,
    log_level public.log_level NOT NULL DEFAULT 'INFO',
    action VARCHAR(255) NOT NULL,
    details TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE public.video_sessions (
    id BIGSERIAL PRIMARY KEY,
    patient_id BIGINT NOT NULL REFERENCES public.patients(id) ON DELETE CASCADE,
    employee_id BIGINT NOT NULL REFERENCES public.employees(id) ON DELETE RESTRICT,
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    session_status public.video_session_status NOT NULL DEFAULT 'CREATED',
    session_notes TEXT,
    CHECK (ended_at IS NULL OR started_at IS NULL OR ended_at >= started_at)
);

CREATE TABLE public.llm_reports (
    id BIGSERIAL PRIMARY KEY,
    patient_id BIGINT NOT NULL REFERENCES public.patients(id) ON DELETE CASCADE,
    investigation_id BIGINT REFERENCES public.laboratory_investigations(id) ON DELETE CASCADE,
    report_text TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_cards_patient_id ON public.cards (patient_id);
CREATE INDEX idx_cards_employee_id ON public.cards (employee_id);

CREATE INDEX idx_lab_patient_id ON public.laboratory_investigations (patient_id);
CREATE INDEX idx_lab_card_id ON public.laboratory_investigations (card_id);

CREATE INDEX idx_presc_patient_id ON public.prescriptions (patient_id);
CREATE INDEX idx_presc_employee_id ON public.prescriptions (employee_id);
CREATE INDEX idx_presc_card_id ON public.prescriptions (card_id);
CREATE INDEX idx_presc_medicine_id ON public.prescriptions (medicine_id);

CREATE INDEX idx_warehouse_stock_medicine_id ON public.warehouse_stock(medicine_id);

CREATE INDEX idx_dispense_events_prescription_id ON public.dispense_events(prescription_id);
CREATE INDEX idx_dispense_events_medicine_id ON public.dispense_events(medicine_id);

CREATE INDEX idx_scanner_events_prescription_id ON public.scanner_events(prescription_id);
CREATE INDEX idx_scanner_events_medicine_id ON public.scanner_events(medicine_id);

CREATE INDEX idx_samples_investigation_id ON public.samples(investigation_id);

CREATE INDEX idx_analyzer_results_investigation_id ON public.analyzer_results(investigation_id);
CREATE INDEX idx_analyzer_results_analyzer_id ON public.analyzer_results(analyzer_id);
CREATE INDEX idx_analyzer_results_workstation_id ON public.analyzer_results(workstation_id);

CREATE INDEX idx_monitoring_metrics_equipment_id ON public.monitoring_metrics(equipment_id);
CREATE INDEX idx_self_diagnostics_equipment_id ON public.self_diagnostics(equipment_id);

CREATE INDEX idx_logs_service_name ON public.logs(service_name);

CREATE INDEX idx_video_sessions_patient_id ON public.video_sessions(patient_id);
CREATE INDEX idx_video_sessions_employee_id ON public.video_sessions(employee_id);

CREATE INDEX idx_llm_reports_patient_id ON public.llm_reports(patient_id);
CREATE INDEX idx_llm_reports_investigation_id ON public.llm_reports(investigation_id);

COMMIT;