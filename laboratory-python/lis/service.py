from db import fetch_all, fetch_one


class LISService:
    def get_ordered_investigations(self, conn) -> list[dict]:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, patient_id, card_id, test_name, status, results, date_ordered, date_completed
            FROM laboratory_investigations
            WHERE status = 'ORDERED'
            ORDER BY id
            """
        )
        return fetch_all(cur)

    def get_investigation(self, conn, investigation_id: int) -> dict | None:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, patient_id, card_id, test_name, status, results, date_ordered, date_completed
            FROM laboratory_investigations
            WHERE id = ?
            """,
            (investigation_id,),
        )
        return fetch_one(cur)

    def complete_investigation(self, conn, investigation_id: int, results: str) -> dict | None:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE laboratory_investigations
            SET status = 'COMPLETED',
                results = ?,
                date_completed = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (results, investigation_id),
        )
        if cur.rowcount == 0:
            return None
        return self.get_investigation(conn, investigation_id)
