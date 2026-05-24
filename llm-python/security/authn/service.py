from collections.abc import Callable

from ..contracts import Subject


class AuthnService:
    def __init__(self, require_identity: bool = False, resolver: Callable[[str], Subject] | None = None):
        self._require_identity = require_identity
        self._resolver = resolver

    def authenticate(self, headers: dict[str, str]) -> Subject:
        subject_id = (headers.get("x-subject-id") or "").strip()
        roles_raw = (headers.get("x-roles") or "").strip()

        if not subject_id:
            if self._require_identity:
                raise ValueError("missing x-subject-id")
            subject_id = "anonymous"

        if self._resolver is not None and subject_id != "anonymous":
            return self._resolver(subject_id)

        roles = ["guest"]
        if roles_raw:
            parsed = [item.strip() for item in roles_raw.split(",") if item.strip()]
            if parsed:
                roles = parsed

        return Subject(id=subject_id, roles=roles)
