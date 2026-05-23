# pacientes/validators.py
import re
from datetime import date
from django.core.exceptions import ValidationError


def validate_dni(value):
    """Valida que el DNI conste exactamente de 8 dígitos numéricos."""
    if not re.match(r"^\d{8}$", str(value)):
        raise ValidationError("El DNI debe tener exactamente 8 dígitos numéricos.")


def validate_telefono(value):
    """Valida que el teléfono conste exactamente de 9 dígitos numéricos."""
    if not re.match(r"^\d{9}$", str(value)):
        raise ValidationError("El teléfono debe tener exactamente 9 dígitos numéricos.")


def validate_peso(value):
    """Valida que el peso sea mayor a 2 kg y menor a 500 kg."""
    if value is not None:
        if value <= 2:
            raise ValidationError("El peso debe ser mayor a 2 kg.")
        if value > 500:
            raise ValidationError("El peso no puede ser mayor a 500 kg.")


def validate_fecha_nacimiento_edad(value):
    """Valida que el paciente tenga al menos 1 año y que la fecha sea razonable (no futura, máx 120 años)."""
    if value:
        hoy = date.today()
        if value > hoy:
            raise ValidationError("La fecha de nacimiento no puede ser futura.")
        edad = hoy.year - value.year - ((hoy.month, hoy.day) < (value.month, value.day))
        if edad < 1:
            raise ValidationError("La edad del paciente debe ser de al menos 1 año.")
        if value.year < 1900 or edad > 120:
            raise ValidationError("La fecha de nacimiento no es válida.")


def validate_nombre_apellido(value):
    """Valida que el nombre o apellido solo contenga letras y caracteres alfabéticos válidos."""
    if not re.match(r"^[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s'\-]+$", str(value)):
        raise ValidationError("Este campo solo puede contener letras y espacios.")


def validate_talla(value):
    """Valida que la talla del paciente se ubique en un rango realista (entre 50 y 250 cm)."""
    if value is not None:
        if value < 50:
            raise ValidationError("La talla mínima es de 50 cm.")
        if value > 250:
            raise ValidationError("La talla máxima no puede superar los 250 cm.")
