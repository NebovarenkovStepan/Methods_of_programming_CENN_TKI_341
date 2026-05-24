from dataclasses import dataclass
from typing import Protocol

ACTION_GET_ORDERED_INVESTIGATIONS = "investigation:list_ordered"
ACTION_GET_INVESTIGATION = "investigation:read"
ACTION_REGISTER_SAMPLE = "sample:register"
ACTION_MOVE_SAMPLE_TO_STORAGE = "sample:to_storage"
ACTION_MOVE_SAMPLE_TO_ANALYSIS = "sample:to_analysis"
ACTION_CREATE_ANALYZER = "analyzer:create"
ACTION_CREATE_WORKSTATION = "workstation:create"
ACTION_SAVE_ANALYZER_RESULT = "analyzer_result:create"
ACTION_COMPLETE_INVESTIGATION = "investigation:complete"
ACTION_CREATE_EQUIPMENT = "equipment:create"
ACTION_ADD_METRIC = "monitoring:add_metric"
ACTION_ADD_DIAGNOSTIC = "diagnostic:add"


@dataclass
class Subject:
    id: str
    roles: list[str]


@dataclass
class Action:
    name: str
    resource: str
    patient_id: int | None = None
    investigation_id: int | None = None


@dataclass
class AuditEvent:
    service: str
    action: str
    result: str
    details: str = ""


class Authenticator(Protocol):
    def authenticate(self, headers: dict[str, str]) -> Subject: ...


class Authorizer(Protocol):
    def authorize(self, subject: Subject, action: Action) -> None: ...


class Auditor(Protocol):
    def write_event(self, event: AuditEvent) -> None: ...


class IntegrityChecker(Protocol):
    def verify_payload(self, payload: bytes, signature: str) -> None: ...


class IdentityChecker(Protocol):
    def verify_patient_identity(self, subject: Subject, patient_id: int) -> None: ...


class ChannelGuard(Protocol):
    def validate_source(self, headers: dict[str, str]) -> None: ...
