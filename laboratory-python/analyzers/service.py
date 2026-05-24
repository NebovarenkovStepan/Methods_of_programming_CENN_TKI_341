from db import fetch_one


class AnalyzerService:
    def create_analyzer(self, conn, name: str, model: str | None = None) -> dict:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO analyzers (name, model, status)
            VALUES (?, ?, 'ACTIVE')
            """,
            (name, model),
        )
        analyzer_id = cur.lastrowid
        cur.execute("SELECT id, name, model, status FROM analyzers WHERE id = ?", (analyzer_id,))
        return fetch_one(cur)

    def save_analyzer_result(
        self,
        conn,
        investigation_id: int,
        analyzer_id: int | None,
        workstation_id: int | None,
        raw_result: str,
    ) -> dict:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO analyzer_results (
                investigation_id, analyzer_id, workstation_id, raw_result
            )
            VALUES (?, ?, ?, ?)
            """,
            (investigation_id, analyzer_id, workstation_id, raw_result),
        )
        result_id = cur.lastrowid
        cur.execute(
            """
            SELECT id, investigation_id, analyzer_id, workstation_id, raw_result, created_at
            FROM analyzer_results
            WHERE id = ?
            """,
            (result_id,),
        )
        return fetch_one(cur)
