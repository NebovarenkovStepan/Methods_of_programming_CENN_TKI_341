from db import fetch_one


class LLMService:
    def get_investigation(self, conn, investigation_id: int):
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, patient_id, test_name, results, status
                FROM public.laboratory_investigations
                WHERE id = %s
                """,
                (investigation_id,),
            )
            return fetch_one(cur)

    def generate_report_text(self, investigation: dict) -> str:
        # простая "LLM" логика
        if investigation["status"] != "COMPLETED":
            return "Исследование не завершено, анализ невозможен"

        results = investigation["results"] or ""

        # имитация анализа
        if "Hemoglobin" in results:
            return f"Анализ: показатели крови в пределах нормы. Детали: {results}"

        if "Leukocytes" in results:
            return f"Анализ: уровень лейкоцитов требует внимания. Детали: {results}"

        return f"Анализ выполнен. Результаты: {results}"

    def save_report(self, conn, patient_id: int, investigation_id: int, text: str):
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.llm_reports (patient_id, investigation_id, report_text)
                VALUES (%s, %s, %s)
                RETURNING id, patient_id, investigation_id, report_text, created_at
                """,
                (patient_id, investigation_id, text),
            )
            return fetch_one(cur)

    def generate_and_save(self, conn, investigation_id: int):
        inv = self.get_investigation(conn, investigation_id)
        if not inv:
            return None, "investigation not found"

        text = self.generate_report_text(inv)

        report = self.save_report(
            conn,
            patient_id=inv["patient_id"],
            investigation_id=investigation_id,
            text=text,
        )

        return report, None