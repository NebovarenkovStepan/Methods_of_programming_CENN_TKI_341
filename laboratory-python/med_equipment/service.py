from db import fetch_one


class MedicalEquipmentService:
    def create_equipment(
        self,
        conn,
        name: str,
        equipment_type: str,
        location: str | None = None,
    ) -> dict:
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
