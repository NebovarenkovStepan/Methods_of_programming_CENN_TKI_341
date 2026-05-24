from db import fetch_one


class SampleStorageService:
    def register_sample(
        self,
        conn,
        investigation_id: int,
        sample_type: str,
        storage_location: str | None = None,
    ) -> dict:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO samples (investigation_id, sample_type, storage_location, status)
            VALUES (?, ?, ?, 'REGISTERED')
            """,
            (investigation_id, sample_type, storage_location),
        )
        sample_id = cur.lastrowid
        cur.execute(
            """
            SELECT id, investigation_id, sample_type, storage_location, status, created_at
            FROM samples
            WHERE id = ?
            """,
            (sample_id,),
        )
        return fetch_one(cur)

    def move_sample_to_storage(self, conn, investigation_id: int) -> dict | None:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE samples
            SET status = 'IN_STORAGE'
            WHERE investigation_id = ?
            """,
            (investigation_id,),
        )
        if cur.rowcount == 0:
            return None
        cur.execute(
            """
            SELECT id, investigation_id, sample_type, storage_location, status, created_at
            FROM samples
            WHERE investigation_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (investigation_id,),
        )
        return fetch_one(cur)

    def move_sample_to_analysis(self, conn, investigation_id: int) -> dict | None:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE samples
            SET status = 'IN_ANALYSIS'
            WHERE investigation_id = ?
            """,
            (investigation_id,),
        )
        if cur.rowcount == 0:
            return None
        cur.execute(
            """
            SELECT id, investigation_id, sample_type, storage_location, status, created_at
            FROM samples
            WHERE investigation_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (investigation_id,),
        )
        return fetch_one(cur)
