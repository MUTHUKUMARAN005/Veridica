import hashlib
import os
import re
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, Request

MAX_ASSET_SIZE = 10 * 1024 * 1024
ASSET_SIGNATURES = {
    "application/pdf": ((".pdf",), b"%PDF-"),
    "image/png": ((".png",), b"\x89PNG\r\n\x1a\n"),
    "image/jpeg": ((".jpg", ".jpeg"), b"\xff\xd8\xff"),
}


async def store_private_asset(
    request: Request, filename: str, storage_dir: Path
) -> tuple[str, str, int, str, str]:
    safe_name = _validate_filename(filename)
    content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    signature = ASSET_SIGNATURES.get(content_type)
    if signature is None or not safe_name.lower().endswith(signature[0]):
        raise HTTPException(status_code=415, detail="Only PDF, PNG, and JPG files are supported.")

    expected_size = request.headers.get("content-length")
    if expected_size is not None:
        try:
            if int(expected_size) > MAX_ASSET_SIZE:
                raise HTTPException(status_code=413, detail="Files must be 10 MB or smaller.")
        except ValueError as error:
            raise HTTPException(status_code=400, detail="Invalid Content-Length header.") from error

    content = bytearray()
    async for chunk in request.stream():
        if len(content) + len(chunk) > MAX_ASSET_SIZE:
            raise HTTPException(status_code=413, detail="Files must be 10 MB or smaller.")
        content.extend(chunk)
    if not content.startswith(signature[1]):
        raise HTTPException(
            status_code=415, detail="The file contents do not match its media type."
        )

    storage_key = str(uuid4())
    storage_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    path = storage_dir / storage_key
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as asset_file:
            asset_file.write(content)
            asset_file.flush()
            os.fsync(asset_file.fileno())
    except OSError:
        path.unlink(missing_ok=True)
        raise

    return safe_name, content_type, len(content), hashlib.sha256(content).hexdigest(), storage_key


def _validate_filename(filename: str) -> str:
    if (
        not filename
        or len(filename) > 255
        or "/" in filename
        or "\\" in filename
        or any(ord(character) < 32 or ord(character) == 127 for character in filename)
        or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._ -]*", filename)
    ):
        raise HTTPException(status_code=422, detail="Provide a safe filename without a path.")
    return filename.strip()
