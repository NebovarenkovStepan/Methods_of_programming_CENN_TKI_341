from db import fetch_one


class AnalyzerService:
    def create_analyzer(self, conn, name: str, model: str | None = None) -> dict:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.analyzers (name, model, status)
                VALUES (%s, %s, 'ACTIVE')
                RETURNING id, name, model, status
                """,
                (name, model),
            )
            return fetch_one(cur)

    def save_analyzer_result(
        self,
        conn,
        investigation_id: int,
        analyzer_id: int | None,
        workstation_id: int | None,
        raw_result: str,
    ) -> dict:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.analyzer_results (
                    investigation_id, analyzer_id, workstation_id, raw_result
                )
                VALUES (%s, %s, %s, %s)
                RETURNING id, investigation_id, analyzer_id, workstation_id, raw_result, created_at
                """,
                (investigation_id, analyzer_id, workstation_id, raw_result),
            )
            return fetch_one(cur)