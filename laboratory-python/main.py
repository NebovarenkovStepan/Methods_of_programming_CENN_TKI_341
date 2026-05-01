from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from analyzers.service import AnalyzerService
from db import get_connection
from lis.service import LISService
from med_equipment.service import MedicalEquipmentService
from monitoring.service import MonitoringService
from sample_storage.service import SampleStorageService
from self_diagnostics.service import SelfDiagnosticsService
from workstations.service import WorkstationService

app = FastAPI(title="laboratory-python")

lis_service = LISService()
sample_service = SampleStorageService()
analyzer_service = AnalyzerService()
workstation_service = WorkstationService()
equipment_service = MedicalEquipmentService()
monitoring_service = MonitoringService()
diagnostics_service = SelfDiagnosticsService()


class RegisterSampleRequest(BaseModel):
    investigation_id: int
    sample_type: str
    storage_location: str | None = None


class CreateAnalyzerRequest(BaseModel):
    name: str
    model: str | None = None


class CreateWorkstationRequest(BaseModel):
    name: str
    location: str | None = None


class SaveAnalyzerResultRequest(BaseModel):
    investigation_id: int
    analyzer_id: int | None = None
    workstation_id: int | None = None
    raw_result: str


class CompleteInvestigationRequest(BaseModel):
    investigation_id: int
    results: str


class CreateEquipmentRequest(BaseModel):
    name: str
    equipment_type: str
    location: str | None = None


class AddMetricRequest(BaseModel):
    equipment_id: int
    metric_name: str
    metric_value: str


class AddDiagnosticRequest(BaseModel):
    equipment_id: int
    diagnostic_status: str
    details: str | None = None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/investigations/ordered")
def get_ordered_investigations():
    with get_connection() as conn:
        result = lis_service.get_ordered_investigations(conn)
        return result


@app.get("/investigations/{investigation_id}")
def get_investigation(investigation_id: int):
    with get_connection() as conn:
        result = lis_service.get_investigation(conn, investigation_id)
        if result is None:
            raise HTTPException(status_code=404, detail="investigation not found")
        return result


@app.post("/samples/register")
def register_sample(req: RegisterSampleRequest):
    with get_connection() as conn:
        result = sample_service.register_sample(
            conn,
            req.investigation_id,
            req.sample_type,
            req.storage_location,
        )
        return result


@app.post("/samples/{investigation_id}/to-storage")
def move_sample_to_storage(investigation_id: int):
    with get_connection() as conn:
        result = sample_service.move_sample_to_storage(conn, investigation_id)
        if result is None:
            raise HTTPException(status_code=404, detail="sample not found")
        return result


@app.post("/samples/{investigation_id}/to-analysis")
def move_sample_to_analysis(investigation_id: int):
    with get_connection() as conn:
        result = sample_service.move_sample_to_analysis(conn, investigation_id)
        if result is None:
            raise HTTPException(status_code=404, detail="sample not found")
        return result


@app.post("/analyzers")
def create_analyzer(req: CreateAnalyzerRequest):
    with get_connection() as conn:
        result = analyzer_service.create_analyzer(conn, req.name, req.model)
        return result


@app.post("/workstations")
def create_workstation(req: CreateWorkstationRequest):
    with get_connection() as conn:
        result = workstation_service.create_workstation(conn, req.name, req.location)
        return result


@app.post("/analyzer-results")
def save_analyzer_result(req: SaveAnalyzerResultRequest):
    with get_connection() as conn:
        result = analyzer_service.save_analyzer_result(
            conn,
            req.investigation_id,
            req.analyzer_id,
            req.workstation_id,
            req.raw_result,
        )
        return result


@app.post("/investigations/complete")
def complete_investigation(req: CompleteInvestigationRequest):
    with get_connection() as conn:
        result = lis_service.complete_investigation(conn, req.investigation_id, req.results)
        if result is None:
            raise HTTPException(status_code=404, detail="investigation not found")
        return result


@app.post("/equipment")
def create_equipment(req: CreateEquipmentRequest):
    with get_connection() as conn:
        result = equipment_service.create_equipment(
            conn,
            req.name,
            req.equipment_type,
            req.location,
        )
        return result


@app.post("/monitoring/metrics")
def add_metric(req: AddMetricRequest):
    with get_connection() as conn:
        result = monitoring_service.add_metric(
            conn,
            req.equipment_id,
            req.metric_name,
            req.metric_value,
        )
        return result


@app.post("/diagnostics")
def add_diagnostic(req: AddDiagnosticRequest):
    with get_connection() as conn:
        result = diagnostics_service.add_diagnostic(
            conn,
            req.equipment_id,
            req.diagnostic_status,
            req.details,
        )
        return result