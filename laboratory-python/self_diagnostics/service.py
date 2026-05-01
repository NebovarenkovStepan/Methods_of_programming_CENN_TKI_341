from db import fetch_one


class SelfDiagnosticsService:
    def add_diagnostic(
        self,
        conn,
        equipment_id: int,
        diagnostic_status: str,
        details: str | None = None,
    ) -> dict:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.self_diagnostics (equipment_id, diagnostic_status, details)
                VALUES (%s, %s, %s)
                RETURNING id, equipment_id, diagnostic_status, details, checked_at
                """,
                (equipment_id, diagnostic_status, details),
            )
            return fetch_one(cur)