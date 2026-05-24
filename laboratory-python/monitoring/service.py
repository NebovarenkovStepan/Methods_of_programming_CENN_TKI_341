from db import fetch_one


class MonitoringService:
    def add_metric(
        self,
        conn,
        equipment_id: int,
        metric_name: str,
        metric_value: str,
    ) -> dict:
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
