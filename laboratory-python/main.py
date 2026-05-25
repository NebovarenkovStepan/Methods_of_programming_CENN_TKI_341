import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from analyzers.service import AnalyzerService
from db import get_connection
from lis.service import LISService
from med_equipment.service import MedicalEquipmentService
from monitoring.service import MonitoringService
from sample_storage.service import SampleStorageService
from security.audit.service import AuditService
from security.authn.service import AuthnService
from security.authz.service import AuthzService
from security.channel_guard.service import ChannelGuardService
from security.contracts import (
    ACTION_ADD_DIAGNOSTIC,
    ACTION_ADD_METRIC,
    ACTION_COMPLETE_INVESTIGATION,
    ACTION_CREATE_ANALYZER,
    ACTION_CREATE_EQUIPMENT,
    ACTION_CREATE_WORKSTATION,
    ACTION_GET_INVESTIGATION,
    ACTION_GET_ORDERED_INVESTIGATIONS,
    ACTION_MOVE_SAMPLE_TO_ANALYSIS,
    ACTION_MOVE_SAMPLE_TO_STORAGE,
    ACTION_REGISTER_SAMPLE,
    ACTION_SAVE_ANALYZER_RESULT,
    Action,
    AuditEvent,
    Subject,
)
from security.identity_check.service import IdentityCheckService
from security.integrity.service import IntegrityService
from self_diagnostics.service import SelfDiagnosticsService
from workstations.service import WorkstationService

lis_service = LISService()
sample_service = SampleStorageService()
analyzer_service = AnalyzerService()
workstation_service = WorkstationService()
equipment_service = MedicalEquipmentService()
monitoring_service = MonitoringService()
diagnostics_service = SelfDiagnosticsService()


def _load_integrity_secret() -> str:
    secret_file = (os.getenv("INTEGRITY_SECRET_FILE") or "").strip()
    if secret_file:
        with open(secret_file, "r", encoding="utf-8") as f:
            return f.read().strip()
    return (os.getenv("INTEGRITY_SECRET") or "").strip()


integrity_secret = _load_integrity_secret()
if not integrity_secret:
    raise RuntimeError("INTEGRITY_SECRET is required in strict mode")


def _role_from_speciality(speciality: str | None) -> str:
    value = (speciality or "").strip().lower()
    if "админ" in value:
        return "admin"
    if "врач" in value or "doctor" in value or "терап" in value:
        return "doctor"
    if "тех" in value or "tech" in value:
        return "tech"
    return "lab_tech"


def resolve_subject_from_db(subject_id: str):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT u.patient_id, e.speciality
            FROM users u
            LEFT JOIN employees e ON e.id = u.employee_id
            WHERE u.id = ?
            """,
            (int(subject_id),),
        )
        row = cur.fetchone()
        if row is None:
            raise ValueError("subject not found")
        patient_id, speciality = row
        if patient_id is not None:
            return Subject(id=subject_id, roles=["patient"])
        return Subject(id=subject_id, roles=[_role_from_speciality(speciality)])


def write_audit_to_db(event: AuditEvent):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO logs (service_name, log_level, action, details)
            VALUES (?, ?, ?, ?)
            """,
            (
                event.service,
                "WARNING" if event.result == "deny" else "INFO",
                event.action,
                event.details,
            ),
        )


authn_service = AuthnService(require_identity=True, resolver=resolve_subject_from_db)
authz_service = AuthzService(enforce=True)
audit_service = AuditService(writer=write_audit_to_db)
integrity_service = IntegrityService(enforce=True, secret=integrity_secret)
identity_service = IdentityCheckService(enforce=True)
channel_guard_service = ChannelGuardService(enforce=True)


def _json_response(handler: BaseHTTPRequestHandler, status: int, payload):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _preflight(handler: BaseHTTPRequestHandler, action_name: str, resource: str, body: bytes, patient_id=None, investigation_id=None):
    action = Action(name=action_name, resource=resource, patient_id=patient_id, investigation_id=investigation_id)
    headers = {k.lower(): v for k, v in handler.headers.items()}
    channel_guard_service.validate_source(headers)
    subject = authn_service.authenticate(headers)
    authz_service.authorize(subject, action)
    integrity_service.verify_payload(body or b"{}", headers.get("x-signature", ""))
    audit_service.write_event(AuditEvent(service="laboratory", action=action_name, result="allow", details=f"subject={subject.id}"))
    return subject


class LaboratoryHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            return _json_response(self, 200, {"status": "ok"})
        try:
            body = b"{}"
            if parsed.path == "/investigations/ordered":
                subject = _preflight(self, ACTION_GET_ORDERED_INVESTIGATIONS, "investigations", body)
                with get_connection() as conn:
                    conn.caller_role = subject.roles[0] if subject.roles else None
                    return _json_response(self, 200, lis_service.get_ordered_investigations(conn))
            if parsed.path.startswith("/investigations/"):
                inv_id = int(parsed.path.split("/")[-1])
                subject = _preflight(self, ACTION_GET_INVESTIGATION, "investigations", body, investigation_id=inv_id)
                with get_connection() as conn:
                    conn.caller_role = subject.roles[0] if subject.roles else None
                    result = lis_service.get_investigation(conn, inv_id)
                    if result is None:
                        return _json_response(self, 404, {"detail": "investigation not found"})
                    return _json_response(self, 200, result)
            return _json_response(self, 404, {"error": "not found"})
        except PermissionError as exc:
            return _json_response(self, 403, {"detail": str(exc)})
        except ValueError as exc:
            return _json_response(self, 401, {"detail": str(exc)})

    def do_POST(self):
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length > 0 else b"{}"
        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
            with get_connection() as conn:
                if parsed.path == "/samples/register":
                    subject = _preflight(self, ACTION_REGISTER_SAMPLE, "samples", body, investigation_id=payload["investigation_id"])
                    conn.caller_role = subject.roles[0] if subject.roles else None
                    inv = lis_service.get_investigation(conn, payload["investigation_id"])
                    if inv is not None:
                        identity_service.verify_patient_identity(subject, inv["patient_id"])
                    return _json_response(self, 201, sample_service.register_sample(conn, payload["investigation_id"], payload["sample_type"], payload.get("storage_location")))
                if parsed.path.startswith("/samples/") and parsed.path.endswith("/to-storage"):
                    inv_id = int(parsed.path.split("/")[2])
                    subject = _preflight(self, ACTION_MOVE_SAMPLE_TO_STORAGE, "samples", body, investigation_id=inv_id)
                    conn.caller_role = subject.roles[0] if subject.roles else None
                    result = sample_service.move_sample_to_storage(conn, inv_id)
                    return _json_response(self, 201 if result else 404, result or {"detail": "sample not found"})
                if parsed.path.startswith("/samples/") and parsed.path.endswith("/to-analysis"):
                    inv_id = int(parsed.path.split("/")[2])
                    subject = _preflight(self, ACTION_MOVE_SAMPLE_TO_ANALYSIS, "samples", body, investigation_id=inv_id)
                    conn.caller_role = subject.roles[0] if subject.roles else None
                    result = sample_service.move_sample_to_analysis(conn, inv_id)
                    return _json_response(self, 201 if result else 404, result or {"detail": "sample not found"})
                if parsed.path == "/analyzers":
                    subject = _preflight(self, ACTION_CREATE_ANALYZER, "analyzers", body)
                    conn.caller_role = subject.roles[0] if subject.roles else None
                    return _json_response(self, 201, analyzer_service.create_analyzer(conn, payload["name"], payload.get("model")))
                if parsed.path == "/workstations":
                    subject = _preflight(self, ACTION_CREATE_WORKSTATION, "workstations", body)
                    conn.caller_role = subject.roles[0] if subject.roles else None
                    return _json_response(self, 201, workstation_service.create_workstation(conn, payload["name"], payload.get("location")))
                if parsed.path == "/analyzer-results":
                    subject = _preflight(self, ACTION_SAVE_ANALYZER_RESULT, "analyzer_results", body, investigation_id=payload["investigation_id"])
                    conn.caller_role = subject.roles[0] if subject.roles else None
                    return _json_response(self, 201, analyzer_service.save_analyzer_result(conn, payload["investigation_id"], payload.get("analyzer_id"), payload.get("workstation_id"), payload["raw_result"]))
                if parsed.path == "/investigations/complete":
                    subject = _preflight(self, ACTION_COMPLETE_INVESTIGATION, "investigations", body, investigation_id=payload["investigation_id"])
                    conn.caller_role = subject.roles[0] if subject.roles else None
                    result = lis_service.complete_investigation(conn, payload["investigation_id"], payload["results"])
                    return _json_response(self, 201 if result else 404, result or {"detail": "investigation not found"})
                if parsed.path == "/equipment":
                    subject = _preflight(self, ACTION_CREATE_EQUIPMENT, "equipment", body)
                    conn.caller_role = subject.roles[0] if subject.roles else None
                    return _json_response(self, 201, equipment_service.create_equipment(conn, payload["name"], payload["equipment_type"], payload.get("location")))
                if parsed.path == "/monitoring/metrics":
                    subject = _preflight(self, ACTION_ADD_METRIC, "monitoring", body)
                    conn.caller_role = subject.roles[0] if subject.roles else None
                    return _json_response(self, 201, monitoring_service.add_metric(conn, payload["equipment_id"], payload["metric_name"], payload["metric_value"]))
                if parsed.path == "/diagnostics":
                    subject = _preflight(self, ACTION_ADD_DIAGNOSTIC, "diagnostics", body)
                    conn.caller_role = subject.roles[0] if subject.roles else None
                    return _json_response(self, 201, diagnostics_service.add_diagnostic(conn, payload["equipment_id"], payload["diagnostic_status"], payload.get("details")))
            return _json_response(self, 404, {"error": "not found"})
        except PermissionError as exc:
            return _json_response(self, 403, {"detail": str(exc)})
        except ValueError as exc:
            return _json_response(self, 401, {"detail": str(exc)})
        except Exception as exc:
            return _json_response(self, 400, {"error": str(exc)})


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), LaboratoryHandler)
    server.serve_forever()
