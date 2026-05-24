from db import fetch_one


class WorkstationService:
    def create_workstation(self, conn, name: str, location: str | None = None) -> dict:
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
