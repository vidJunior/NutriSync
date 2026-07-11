# nutricion/validators.py
from django.core.exceptions import ValidationError

def validate_tiempo_preparacion(value):
    """Valida que el tiempo de preparación esté en un rango lógico (1 - 480 minutos)."""
    if value is not None:
        if value < 1:
            raise ValidationError("El tiempo de preparación mínimo es de 1 minuto.")
        if value > 480:
            raise ValidationError("El tiempo de preparación no puede superar los 480 minutos (8 horas).")

def validate_porciones(value):
    """Valida que el número de porciones sea razonable (1 - 100 porciones)."""
    if value is not None:
        if value < 1:
            raise ValidationError("La receta debe rendir al menos 1 porción.")
        if value > 100:
            raise ValidationError("Las porciones no pueden ser mayores a 100.")

def validate_cantidad_ingrediente(value):
    """Valida que la cantidad de ingrediente esté en un rango realista (0.1g - 10000g)."""
    if value is not None:
        if value < 0.1:
            raise ValidationError("La cantidad del ingrediente debe ser de al menos 0.1 gramos.")
        if value > 10000:
            raise ValidationError("La cantidad del ingrediente no puede superar los 10,000 gramos (10 kg).")
