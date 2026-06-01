from db import fetch_one


ALLOWED_LAB_ROLES = {"lab_tech", "doctor", "admin"}


def _require_authorized_role(conn):
    role = getattr(conn, "caller_role", None)
    if role not in ALLOWED_LAB_ROLES:
        raise PermissionError("caller is not authorized for laboratory operations")


class MonitoringService:
    def add_metric(
        self,
        conn,
        equipment_id: int,
        metric_name: str,
        metric_value: str,
    ) -> dict:
        _require_authorized_role(conn)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO monitoring_metrics (equipment_id, metric_name, metric_value)
            VALUES (?, ?, ?)
            """,
            (equipment_id, metric_name, metric_value),
        )
        metric_id = cur.lastrowid
        cur.execute(
            """
            SELECT id, equipment_id, metric_name, metric_value, recorded_at
            FROM monitoring_metrics
            WHERE id = ?
            """,
            (metric_id,),
        )
        return fetch_one(cur)
