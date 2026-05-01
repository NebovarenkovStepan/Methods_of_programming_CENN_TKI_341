from db import fetch_one


class MedicalEquipmentService:
    def create_equipment(
        self,
        conn,
        name: str,
        equipment_type: str,
        location: str | None = None,
    ) -> dict:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.medical_equipment (name, equipment_type, location, status)
                VALUES (%s, %s, %s, 'ACTIVE')
                RETURNING id, name, equipment_type, location, status
                """,
                (name, equipment_type, location),
            )
            return fetch_one(cur)