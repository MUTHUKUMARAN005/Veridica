import base64
import binascii
import hashlib
import hmac
import json
import secrets
import time


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    encoded_salt = base64.urlsafe_b64encode(salt).decode()
    encoded_digest = base64.urlsafe_b64encode(digest).decode()
    return f"scrypt${encoded_salt}${encoded_digest}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, salt, expected = encoded.split("$")
        if algorithm != "scrypt":
            return False
        actual = hashlib.scrypt(
            password.encode(), salt=base64.urlsafe_b64decode(salt), n=2**14, r=8, p=1
        )
        return hmac.compare_digest(actual, base64.urlsafe_b64decode(expected))
    except (ValueError, TypeError):
        return False


def create_access_token(subject: str, role: str, secret: str, minutes: int) -> str:
    header = _encode({"alg": "HS256", "typ": "JWT"})
    payload = _encode({"sub": subject, "role": role, "exp": int(time.time()) + minutes * 60})
    signature = _sign(f"{header}.{payload}", secret)
    return f"{header}.{payload}.{signature}"


def decode_access_token(token: str, secret: str) -> dict[str, object] | None:
    try:
        header, payload, signature = token.split(".")
        if not hmac.compare_digest(signature, _sign(f"{header}.{payload}", secret)):
            return None
        data = json.loads(base64.urlsafe_b64decode(payload + "==="))
        if int(data["exp"]) < int(time.time()):
            return None
        return data
    except (ValueError, KeyError, TypeError, binascii.Error, json.JSONDecodeError):
        return None


def _encode(value: dict[str, object]) -> str:
    raw = json.dumps(value, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _sign(value: str, secret: str) -> str:
    signature = hmac.new(secret.encode(), value.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(signature).decode().rstrip("=")
