import uuid
from pathlib import Path

from django.core.exceptions import ValidationError

MAX_EVIDENCE_BYTES = 5 * 1024 * 1024
EVIDENCE_SIGNATURES = {
    ".jpg": b"\xff\xd8\xff",
    ".jpeg": b"\xff\xd8\xff",
    ".png": b"\x89PNG\r\n\x1a\n",
    ".pdf": b"%PDF-",
}


def evidence_path(instance, filename):
    return f"evidence/{uuid.uuid4().hex}{Path(filename).suffix.lower()}"


def validate_evidence(upload):
    if not upload:
        return upload
    suffix = Path(upload.name).suffix.lower()
    if upload.size > MAX_EVIDENCE_BYTES:
        raise ValidationError("Choose a file no larger than 5 MB.")
    if suffix not in EVIDENCE_SIGNATURES:
        raise ValidationError("Choose a JPEG, PNG or PDF file.")
    position = upload.tell()
    header = upload.read(8)
    upload.seek(position)
    if not header.startswith(EVIDENCE_SIGNATURES[suffix]):
        raise ValidationError("This file does not match its JPEG, PNG or PDF extension.")
    return upload
