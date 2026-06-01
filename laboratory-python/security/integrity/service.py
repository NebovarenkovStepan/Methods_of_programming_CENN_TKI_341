import hashlib
import hmac


class IntegrityService:
    def __init__(self, enforce: bool = False, secret: str = ""):
        self._enforce = enforce
        self._secret = secret.encode()

    def verify_payload(self, payload: bytes, signature: str) -> None:
        if not self._enforce:
            return
        if not self._secret:
            raise ValueError("integrity secret is not configured")
        if not signature or not signature.strip():
            raise ValueError("missing signature")

        expected = hmac.new(self._secret, payload, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature.strip()):
            raise ValueError("signature mismatch")
