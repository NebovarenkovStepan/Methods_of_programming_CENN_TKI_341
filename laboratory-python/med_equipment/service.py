from db import fetch_one


ALLOWED_LAB_ROLES = {"lab_tech", "doctor", "admin"}


def _require_authorized_role(conn):
    role = getattr(conn, "caller_role", None)
    if role not in ALLOWED_LAB_ROLES:
        raise PermissionError("caller is not authorized for laboratory operations")


class MedicalEquipmentService:
    def create_equipment(
        self,
        conn,
        name: str,
        equipment_type: str,
        location: str | None = None,
    ) -> dict:
        _require_authorized_role(conn)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO medical_equipment (name, equipment_type, location, status)
            VALUES (?, ?, ?, 'ACTIVE')
            """,
            (name, equipment_type, location),
        )
        equipment_id = cur.lastrowid
        cur.execute(
            """
            SELECT id, name, equipment_type, location, status
            FROM medical_equipment
            WHERE id = ?
            """,
            (equipment_id,),
        )
        return fetch_one(cur)
