from ..contracts import Subject


class IdentityCheckService:
    def __init__(self, enforce: bool = False):
        self._enforce = enforce

    def verify_patient_identity(self, subject: Subject, patient_id: int) -> None:
        if not self._enforce:
            return
        if patient_id <= 0:
            raise ValueError("invalid patient id")
        if subject.id in ("", "anonymous"):
            raise PermissionError("anonymous subject is not allowed")
