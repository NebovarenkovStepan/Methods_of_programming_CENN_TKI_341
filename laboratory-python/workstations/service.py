from db import fetch_one


ALLOWED_LAB_ROLES = {"lab_tech", "doctor", "admin"}


def _require_authorized_role(conn):
    role = getattr(conn, "caller_role", None)
    if role not in ALLOWED_LAB_ROLES:
        raise PermissionError("caller is not authorized for laboratory operations")


class WorkstationService:
    def create_workstation(self, conn, name: str, location: str | None = None) -> dict:
        _require_authorized_role(conn)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO workstations (name, location, status)
            VALUES (?, ?, 'ACTIVE')
            """,
            (name, location),
        )
        workstation_id = cur.lastrowid
        cur.execute(
            "SELECT id, name, location, status FROM workstations WHERE id = ?",
            (workstation_id,),
        )
        return fetch_one(cur)
