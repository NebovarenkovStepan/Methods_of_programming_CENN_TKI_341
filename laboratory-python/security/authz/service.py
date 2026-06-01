from ..contracts import Action, Subject


class AuthzService:
    def __init__(self, enforce: bool = False):
        self._enforce = enforce
        self._policy: dict[str, set[str]] = {
            "investigation:list_ordered": {"admin", "lab_tech", "doctor"},
            "investigation:read": {"admin", "lab_tech", "doctor"},
            "sample:register": {"admin", "lab_tech"},
            "sample:to_storage": {"admin", "lab_tech"},
            "sample:to_analysis": {"admin", "lab_tech"},
            "analyzer:create": {"admin", "tech"},
            "workstation:create": {"admin", "tech"},
            "analyzer_result:create": {"admin", "lab_tech"},
            "investigation:complete": {"admin", "lab_tech", "doctor"},
            "equipment:create": {"admin", "tech"},
            "monitoring:add_metric": {"admin", "tech"},
            "diagnostic:add": {"admin", "tech"},
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
