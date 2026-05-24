class InputGuardService:
    def __init__(self, enforce: bool = False):
        self._enforce = enforce

    def validate_investigation_payload(self, payload: dict) -> None:
        investigation_id = payload.get("investigation_id")
        if investigation_id is None:
            raise ValueError("missing investigation_id")
        if not isinstance(investigation_id, int) or investigation_id <= 0:
            raise ValueError("invalid investigation_id")

        if not self._enforce:
            return

        if len(payload) > 8:
            raise ValueError("payload has too many fields")

        forbidden_keys = {"password", "token", "session", "secret"}
        for key in payload.keys():
            if key.lower() in forbidden_keys:
                raise ValueError("forbidden field in payload")
