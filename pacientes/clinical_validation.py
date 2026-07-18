import json
from datetime import date
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.utils.dateparse import parse_date


def parse_decimal_value(
    value,
    field_name,
    *,
    minimum=None,
    maximum=None,
    required=False,
):
    raw = "" if value is None else str(value).strip()
    if not raw:
        if required:
            raise ValidationError(f"{field_name} es obligatorio.")
        return None
    try:
        parsed = Decimal(raw)
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError(f"{field_name} debe ser un número válido.") from exc
    if minimum is not None and parsed < Decimal(str(minimum)):
        raise ValidationError(f"{field_name} debe ser igual o mayor a {minimum}.")
    if maximum is not None and parsed > Decimal(str(maximum)):
        raise ValidationError(f"{field_name} debe ser igual o menor a {maximum}.")
    return parsed


def parse_integer_value(
    value,
    field_name,
    *,
    minimum=None,
    maximum=None,
    required=False,
):
    parsed = parse_decimal_value(
        value,
        field_name,
        minimum=minimum,
        maximum=maximum,
        required=required,
    )
    if parsed is None:
        return None
    if parsed != parsed.to_integral_value():
        raise ValidationError(f"{field_name} debe ser un número entero.")
    return int(parsed)


def parse_date_value(value, field_name, *, required=False, allow_future=False):
    raw = "" if value is None else str(value).strip()
    if not raw:
        if required:
            raise ValidationError(f"{field_name} es obligatoria.")
        return None
    parsed = parse_date(raw)
    if parsed is None:
        raise ValidationError(f"{field_name} no tiene un formato válido.")
    if not allow_future and parsed > date.today():
        raise ValidationError(f"{field_name} no puede ser futura.")
    return parsed


def require_section(section, allowed_sections):
    if section not in allowed_sections:
        raise ValidationError("La sección solicitada no es válida.")
    return section


def parse_json_body(request, *, max_bytes=128 * 1024):
    content_type = (request.content_type or "").split(";", 1)[0].strip().lower()
    if content_type != "application/json":
        raise ValidationError("La petición debe usar application/json.")
    if len(request.body) > max_bytes:
        raise ValidationError("La petición supera el tamaño permitido.")
    try:
        data = json.loads(request.body)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValidationError("El contenido JSON no es válido.") from exc
    if not isinstance(data, dict):
        raise ValidationError("El contenido JSON debe ser un objeto.")
    return data


def validate_plan_for_publication(plan):
    errors = []
    if not plan.nombre.strip():
        errors.append("El plan debe tener un nombre.")
    if not plan.comidas:
        errors.append("El plan debe incluir al menos una comida.")
    for index, comida in enumerate(plan.comidas, start=1):
        if not isinstance(comida, dict):
            errors.append(f"La comida {index} no tiene una estructura válida.")
            continue
        if not str(comida.get("tipo", "")).strip():
            errors.append(f"La comida {index} debe indicar un tipo.")
        if not str(comida.get("receta_id", "")).strip() and not comida.get("alimentos"):
            errors.append(f"La comida {index} debe incluir una receta o alimentos.")
    if errors:
        raise ValidationError(errors)
