import os
import re
from urllib.parse import urlparse

from django.core.exceptions import ValidationError
from django.core.validators import validate_email


DEFAULT_DOCUMENT_EXTENSIONS = {
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".txt",
}
DEFAULT_DOCUMENT_MIME_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/plain",
    "application/octet-stream",
}


def validate_uploaded_file(
    uploaded_file,
    *,
    allowed_extensions=None,
    allowed_mime_types=None,
    max_size_mb=10,
):
    if not uploaded_file:
        raise ValidationError("Debes seleccionar un archivo.")

    allowed_extensions = allowed_extensions or DEFAULT_DOCUMENT_EXTENSIONS
    allowed_mime_types = allowed_mime_types or DEFAULT_DOCUMENT_MIME_TYPES
    extension = os.path.splitext(uploaded_file.name or "")[1].lower()
    if extension not in allowed_extensions:
        raise ValidationError("El formato del archivo no está permitido.")

    if uploaded_file.size > max_size_mb * 1024 * 1024:
        raise ValidationError(
            f"El archivo no puede superar los {max_size_mb} MB."
        )

    content_type = (getattr(uploaded_file, "content_type", "") or "").lower()
    if content_type and content_type not in allowed_mime_types:
        raise ValidationError("El tipo de contenido del archivo no está permitido.")


def validate_email_value(value, message="El correo electrónico no es válido."):
    try:
        validate_email((value or "").strip())
    except ValidationError as exc:
        raise ValidationError(message) from exc


def validate_hex_color(value):
    if value and not re.fullmatch(r"#[0-9a-fA-F]{6}", value.strip()):
        raise ValidationError("El color debe usar el formato hexadecimal #RRGGBB.")


def validate_http_url(value):
    if not value:
        return
    parsed = urlparse(value.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValidationError("La URL debe comenzar con http:// o https://.")


def validate_text_length(value, field_name, *, maximum, minimum=0):
    text = (value or "").strip()
    if len(text) < minimum:
        raise ValidationError(
            f"{field_name} debe tener al menos {minimum} caracteres."
        )
    if len(text) > maximum:
        raise ValidationError(
            f"{field_name} no puede superar los {maximum} caracteres."
        )
    return text
