from db import fetch_one


ALLOWED_LAB_ROLES = {"lab_tech", "doctor", "admin"}


def _require_authorized_role(conn):
    role = getattr(conn, "caller_role", None)
    if role not in ALLOWED_LAB_ROLES:
        raise PermissionError("caller is not authorized for laboratory operations")


class SelfDiagnosticsService:
    def add_diagnostic(
        self,
        conn,
        equipment_id: int,
        diagnostic_status: str,
        details: str | None = None,
    ) -> dict:
        _require_authorized_role(conn)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO self_diagnostics (equipment_id, diagnostic_status, details)
            VALUES (?, ?, ?)
            """,
            (equipment_id, diagnostic_status, details),
        )
        diagnostic_id = cur.lastrowid
        cur.execute(
            """
            SELECT id, equipment_id, diagnostic_status, details, checked_at
            FROM self_diagnostics
            WHERE id = ?
            """,
            (diagnostic_id,),
        )
        return fetch_one(cur)
