# facturacion/validators.py
# Validadores del módulo de Facturación.

import re
from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError

from core.validation import validate_email_value, validate_uploaded_file


def validate_monto_positivo(value):
    """Valida que el monto sea un valor positivo."""
    if value is not None and value <= 0:
        raise ValidationError("El monto debe ser mayor a cero.")


def validate_monto_maximo(value):
    """Valida que el monto no supere el límite razonable."""
    if value is not None and value > 999999.99:
        raise ValidationError("El monto no puede superar S/ 999,999.99.")


def validate_porcentaje(value):
    """Valida que el porcentaje esté entre 0 y 100."""
    if value is not None:
        if value < 0 or value > 100:
            raise ValidationError("El porcentaje debe estar entre 0 y 100.")


def normalizar_numero_tarjeta(value):
    return re.sub(r"[\s-]", "", value or "")


def validate_numero_tarjeta(value):
    numero = normalizar_numero_tarjeta(value)
    if not numero.isdigit() or not 13 <= len(numero) <= 19:
        raise ValidationError("El número de tarjeta debe tener entre 13 y 19 dígitos.")

    total = 0
    paridad = len(numero) % 2
    for indice, caracter in enumerate(numero):
        digito = int(caracter)
        if indice % 2 == paridad:
            digito *= 2
            if digito > 9:
                digito -= 9
        total += digito
    if total % 10 != 0:
        raise ValidationError("El número de tarjeta no es válido.")
    return numero


def validate_vencimiento_tarjeta(value):
    match = re.fullmatch(r"\s*(0[1-9]|1[0-2])\s*/\s*(\d{2}|\d{4})\s*", value or "")
    if not match:
        raise ValidationError("El vencimiento debe usar el formato MM/AA.")
    mes = int(match.group(1))
    anio = int(match.group(2))
    if anio < 100:
        anio += 2000
    hoy = date.today()
    if (anio, mes) < (hoy.year, hoy.month):
        raise ValidationError("La tarjeta está vencida.")
    if anio > hoy.year + 20:
        raise ValidationError("El vencimiento de la tarjeta no es válido.")
    return f"{mes:02d}/{anio % 100:02d}"


def validate_cvv(value):
    cvv = (value or "").strip()
    if not re.fullmatch(r"\d{3,4}", cvv):
        raise ValidationError("El código de seguridad debe tener 3 o 4 dígitos.")
    return cvv


def validate_datos_tarjeta(numero, vencimiento, cvv, titular=""):
    numero_limpio = validate_numero_tarjeta(numero)
    validate_vencimiento_tarjeta(vencimiento)
    validate_cvv(cvv)
    if titular and not re.fullmatch(r"[A-Za-zÁÉÍÓÚáéíóúÑñÜü .'-]{3,100}", titular.strip()):
        raise ValidationError("El nombre del titular no es válido.")
    return numero_limpio


def validate_datos_yape(celular, codigo):
    celular_limpio = re.sub(r"\s", "", celular or "")
    if not re.fullmatch(r"9\d{8}", celular_limpio):
        raise ValidationError("El celular Yape debe tener 9 dígitos y comenzar con 9.")
    if not re.fullmatch(r"\d{6}", (codigo or "").strip()):
        raise ValidationError("El código de aprobación Yape debe tener 6 dígitos.")
    return celular_limpio


def validate_email_paypal(value):
    validate_email_value(value, "El correo electrónico de PayPal no es válido.")
    return value.strip().lower()


def validate_comprobante(uploaded_file):
    validate_uploaded_file(
        uploaded_file,
        allowed_extensions={".pdf", ".png", ".jpg", ".jpeg"},
        allowed_mime_types={
            "application/pdf",
            "image/png",
            "image/jpeg",
            "application/octet-stream",
        },
        max_size_mb=5,
    )
