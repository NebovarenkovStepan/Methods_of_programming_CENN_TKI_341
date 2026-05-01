from db import fetch_one


class SampleStorageService:
    def register_sample(
        self,
        conn,
        investigation_id: int,
        sample_type: str,
        storage_location: str | None = None,
    ) -> dict:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.samples (investigation_id, sample_type, storage_location, status)
                VALUES (%s, %s, %s, 'REGISTERED')
                RETURNING id, investigation_id, sample_type, storage_location, status, created_at
                """,
                (investigation_id, sample_type, storage_location),
            )
            return fetch_one(cur)

    def move_sample_to_storage(self, conn, investigation_id: int) -> dict | None:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE public.samples
                SET status = 'IN_STORAGE'
                WHERE investigation_id = %s
                RETURNING id, investigation_id, sample_type, storage_location, status, created_at
                """,
                (investigation_id,),
            )
            return fetch_one(cur)

    def move_sample_to_analysis(self, conn, investigation_id: int) -> dict | None:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE public.samples
                SET status = 'IN_ANALYSIS'
                WHERE investigation_id = %s
                RETURNING id, investigation_id, sample_type, storage_location, status, created_at
                """,
                (investigation_id,),
            )
            return fetch_one(cur)