from db import fetch_one

class WorkstationService:

    def create_workstation(self, conn, name: str, location: str | None = None) -> dict:

        with conn.cursor() as cur:

            cur.execute(

                """

                INSERT INTO public.workstations (name, location, status)

                VALUES (%s, %s, 'ACTIVE')

                RETURNING id, name, location, status

                """,

                (name, location),

            )

            return fetch_one(cur)