from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from db import fetch_all, get_connection
from service.llm_service import LLMService

app = FastAPI(title="llm-python")

llm_service = LLMService()


class GenerateReportRequest(BaseModel):
    investigation_id: int


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/generate")
def generate_report(req: GenerateReportRequest):
    with get_connection() as conn:
        report, err = llm_service.generate_and_save(conn, req.investigation_id)
        if err:
            raise HTTPException(status_code=404, detail=err)
        return report


@app.get("/reports/{investigation_id}")
def get_reports(investigation_id: int):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, patient_id, investigation_id, report_text, created_at
                FROM public.llm_reports
                WHERE investigation_id = %s
                ORDER BY created_at DESC
                """,
                (investigation_id,),
            )
            return fetch_all(cur)
