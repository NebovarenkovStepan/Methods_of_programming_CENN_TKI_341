from dataclasses import dataclass
from typing import Protocol

ACTION_GENERATE_REPORT = "llm:generate_report"
ACTION_READ_REPORTS = "llm:read_reports"


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


class InputGuard(Protocol):
    def validate_investigation_payload(self, payload: dict) -> None: ...


class ChannelGuard(Protocol):
    def validate_source(self, headers: dict[str, str]) -> None: ...
