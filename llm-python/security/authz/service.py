from ..contracts import Action, Subject


class AuthzService:
    def __init__(self, enforce: bool = False):
        self._enforce = enforce
        self._policy: dict[str, set[str]] = {
            "llm:generate_report": {"admin", "doctor", "lab_tech"},
            "llm:read_reports": {"admin", "doctor", "patient"},
        }

    def authorize(self, subject: Subject, action: Action) -> None:
        if not self._enforce:
            return
        allowed_roles = self._policy.get(action.name)
        if not allowed_roles:
            raise PermissionError("action is not allowed by policy")
        for role in subject.roles:
            if role in allowed_roles:
                return
        raise PermissionError("access denied")
