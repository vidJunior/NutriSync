# agendas/validators.py
from django.core.exceptions import ValidationError


def validate_duracion_minutos(value):
    """Valida que la duración de la consulta se ubique en un rango realista (entre 10 y 180 minutos)."""
    if value is not None:
        if value < 10:
            raise ValidationError("La duración mínima de la consulta es de 10 minutos.")
        if value > 180:
            raise ValidationError("La duración máxima de la consulta no puede superar los 180 minutos.")


def validate_costo_positivo(value):
    """Valida que el costo de la consulta no sea un valor negativo."""
    if value is not None and value < 0:
        raise ValidationError("El costo de la consulta no puede ser negativo.")
