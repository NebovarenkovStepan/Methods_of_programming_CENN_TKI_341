from db import fetch_one


class MonitoringService:
    def add_metric(
        self,
        conn,
        equipment_id: int,
        metric_name: str,
        metric_value: str,
    ) -> dict:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.monitoring_metrics (equipment_id, metric_name, metric_value)
                VALUES (%s, %s, %s)
                RETURNING id, equipment_id, metric_name, metric_value, recorded_at
                """,
                (equipment_id, metric_name, metric_value),
            )
            return fetch_one(cur)