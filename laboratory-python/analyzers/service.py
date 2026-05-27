from db import fetch_one


ALLOWED_LAB_ROLES = {"lab_tech", "doctor", "admin"}


def _require_authorized_role(conn):
    role = getattr(conn, "caller_role", None)
    if role not in ALLOWED_LAB_ROLES:
        raise PermissionError("caller is not authorized for laboratory operations")


class AnalyzerService:
    def create_analyzer(self, conn, name: str, model: str | None = None) -> dict:
        _require_authorized_role(conn)
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
        _require_authorized_role(conn)
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
    
    
