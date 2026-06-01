import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from db import fetch_all, get_connection
from security.audit.service import AuditService
from security.authn.service import AuthnService
from security.authz.service import AuthzService
from security.channel_guard.service import ChannelGuardService
from security.contracts import ACTION_GENERATE_REPORT, ACTION_READ_REPORTS, Action, AuditEvent, Subject
from security.input_guard.service import InputGuardService
from security.integrity.service import IntegrityService
from service.llm_service import LLMService

llm_service = LLMService()


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
    if "тех" in value or "lab" in value:
        return "lab_tech"
    return "staff"


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


def resolve_patient_id_for_subject(subject_id: str) -> int | None:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT patient_id FROM users WHERE id = ?", (int(subject_id),))
        row = cur.fetchone()
        if row is None:
            raise ValueError("subject not found")
        return row[0]


def get_investigation_patient_id(investigation_id: int) -> int | None:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT patient_id FROM laboratory_investigations WHERE id = ?", (investigation_id,))
        row = cur.fetchone()
        if row is None:
            return None
        return row[0]


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
input_guard_service = InputGuardService(enforce=True)
channel_guard_service = ChannelGuardService(enforce=True)


def _json_response(handler: BaseHTTPRequestHandler, status: int, payload):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _preflight(handler: BaseHTTPRequestHandler, action_name: str, resource: str, body: bytes, investigation_id=None):
    action = Action(name=action_name, resource=resource, investigation_id=investigation_id)
    headers = {k.lower(): v for k, v in handler.headers.items()}
    channel_guard_service.validate_source(headers)
    subject = authn_service.authenticate(headers)
    authz_service.authorize(subject, action)
    integrity_service.verify_payload(body or b"{}", headers.get("x-signature", ""))
    audit_service.write_event(AuditEvent(service="llm", action=action_name, result="allow", details=f"subject={subject.id}"))
    return subject


def _enforce_patient_owns_investigation(subject: Subject, investigation_id: int):
    if "patient" not in subject.roles:
        return
    subject_patient_id = resolve_patient_id_for_subject(subject.id)
    investigation_patient_id = get_investigation_patient_id(investigation_id)
    if subject_patient_id is None or investigation_patient_id is None:
        raise PermissionError("patient identity verification failed")
    if subject_patient_id != investigation_patient_id:
        raise PermissionError("patient identity verification failed")


class LLMHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/health":
                return _json_response(self, 200, {"status": "ok"})
            if parsed.path.startswith("/reports/"):
                inv_id = int(parsed.path.split("/")[-1])
                body = b"{}"
                subject = _preflight(self, ACTION_READ_REPORTS, "reports", body, investigation_id=inv_id)
                _enforce_patient_owns_investigation(subject, inv_id)
                input_guard_service.validate_investigation_payload({"investigation_id": inv_id})
                with get_connection() as conn:
                    cur = conn.cursor()
                    cur.execute(
                        """
                        SELECT id, patient_id, investigation_id, report_text, created_at
                        FROM llm_reports
                        WHERE investigation_id = ?
                        ORDER BY created_at DESC
                        """,
                        (inv_id,),
                    )
                    return _json_response(self, 200, fetch_all(cur))
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
            if parsed.path == "/generate":
                payload = json.loads(body.decode("utf-8")) if body else {}
                inv_id = payload.get("investigation_id")
                subject = _preflight(self, ACTION_GENERATE_REPORT, "reports", body, investigation_id=inv_id)
                _enforce_patient_owns_investigation(subject, inv_id)
                input_guard_service.validate_investigation_payload({"investigation_id": inv_id})
                with get_connection() as conn:
                    report, err = llm_service.generate_and_save(conn, inv_id)
                    if err:
                        return _json_response(self, 404, {"detail": err})
                    return _json_response(self, 201, report)
            return _json_response(self, 404, {"error": "not found"})
        except PermissionError as exc:
            return _json_response(self, 403, {"detail": str(exc)})
        except ValueError as exc:
            return _json_response(self, 401, {"detail": str(exc)})
        except Exception as exc:
            return _json_response(self, 400, {"error": str(exc)})


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), LLMHandler)
    server.serve_forever()
