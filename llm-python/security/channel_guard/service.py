class ChannelGuardService:
    def __init__(self, enforce: bool = False):
        self._enforce = enforce

    def validate_source(self, headers: dict[str, str]) -> None:
        if not self._enforce:
            return
        if (headers.get("x-trusted-channel") or "").strip() != "vpn":
            raise PermissionError("untrusted source channel")
