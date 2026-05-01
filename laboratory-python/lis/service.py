from db import fetch_all, fetch_one


class LISService:
    def get_ordered_investigations(self, conn) -> list[dict]:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, patient_id, card_id, test_name, status, results, date_ordered, date_completed
                FROM public.laboratory_investigations
                WHERE status = 'ORDERED'
                ORDER BY id
                """
            )
            return fetch_all(cur)

    def get_investigation(self, conn, investigation_id: int) -> dict | None:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, patient_id, card_id, test_name, status, results, date_ordered, date_completed
                FROM public.laboratory_investigations
                WHERE id = %s
                """,
                (investigation_id,),
            )
            return fetch_one(cur)

    def complete_investigation(self, conn, investigation_id: int, results: str) -> dict | None:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE public.laboratory_investigations
                SET status = 'COMPLETED',
                    results = %s,
                    date_completed = CURRENT_TIMESTAMP
                WHERE id = %s
                RETURNING id, patient_id, card_id, test_name, status, results, date_ordered, date_completed
                """,
                (results, investigation_id),
            )
            return fetch_one(cur)