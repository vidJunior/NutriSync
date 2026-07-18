# facturacion/templatetags/facturacion_tags.py
# Etiquetas de facturación.

from django import template
from decimal import Decimal

register = template.Library()


@register.filter
def formatear_moneda(value):
    """Formatea un valor como moneda peruana: S/ 1,234.56"""
    try:
        valor = Decimal(str(value))
        return f"S/ {valor:,.2f}"
    except (ValueError, TypeError):
        return "S/ 0.00"


@register.filter
def calcular_igv(value):
    """Calcula el IGV (18%) de un valor."""
    try:
        valor = Decimal(str(value))
        return f"S/ {valor * Decimal('0.18'):,.2f}"
    except (ValueError, TypeError):
        return "S/ 0.00"


@register.filter
def calcular_total_con_igv(value):
    """Calcula el total incluyendo IGV."""
    try:
        valor = Decimal(str(value))
        total = valor + (valor * Decimal("0.18"))
        return f"S/ {total:,.2f}"
    except (ValueError, TypeError):
        return "S/ 0.00"


@register.filter
def color_estado_cobro(estado):
    """Retorna la clase CSS para el badge de estado del cobro."""
    colores = {
        "pendiente": "warning",
        "pagado": "success",
        "cancelado": "danger",
        "vencido": "dark",
    }
    return colores.get(estado, "secondary")


@register.filter
def color_estado_factura(estado):
    """Retorna la clase CSS para el badge de estado de la factura."""
    colores = {
        "borrador": "secondary",
        "emitida": "info",
        "pagada": "success",
        "vencida": "danger",
        "cancelada": "dark",
    }
    return colores.get(estado, "secondary")


@register.filter
def color_estado_suscripcion(estado):
    """Retorna la clase CSS para el badge de estado de la suscripción."""
    colores = {
        "activa": "success",
        "cancelada": "danger",
        "vencida": "warning",
        "pendiente_pago": "info",
    }
    return colores.get(estado, "secondary")


@register.filter
def icono_metodo_pago(metodo):
    """Retorna el ícono de Lucide para el método de pago."""
    iconos = {
        "stripe": "credit-card",
        "yape": "smartphone",
        "plin": "smartphone",
        "transferencia": "building-2",
        "efectivo": "banknotes",
    }
    return iconos.get(metodo, "currency-dollar")
