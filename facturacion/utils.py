# facturacion/utils.py
# Utilidades de facturación.

from decimal import Decimal
from django.utils import timezone
from datetime import timedelta


# Constantes

IGV_PORCENTAJE = Decimal("0.18")  # 18% IGV en Perú
COMISION_STRIPE_PORCENTAJE = Decimal("0.0375")  # 3.75% comisión Stripe Perú
COMISION_STRIPE_FIJA = Decimal("0.50")  # S/0.50 fija por transacción


# IGV

def calcular_igv(monto):
    """Calcula el IGV (18%) sobre un monto base."""
    return round(Decimal(str(monto)) * IGV_PORCENTAJE, 2)


def calcular_total_con_igv(monto):
    """Calcula el total incluyendo IGV."""
    monto_decimal = Decimal(str(monto))
    igv = round(monto_decimal * IGV_PORCENTAJE, 2)
    return monto_decimal + igv


def calcular_subtotal_de_total(total_con_igv):
    """Extrae el subtotal de un monto que ya incluye IGV."""
    total = Decimal(str(total_con_igv))
    subtotal = total / (1 + IGV_PORCENTAJE)
    return round(subtotal, 2)


def calcular_monto_neto(total, comision_plataforma=Decimal("0.00")):
    """Calcula el monto neto después de comisiones."""
    return round(Decimal(str(total)) - Decimal(str(comision_plataforma)), 2)


# Stripe

def calcular_comision_stripe(monto):
    """Calcula la comisión de Stripe para Perú: 3.75% + S/0.50"""
    monto_decimal = Decimal(str(monto))
    comision_porcentaje = round(monto_decimal * COMISION_STRIPE_PORCENTAJE, 2)
    comision_total = comision_porcentaje + COMISION_STRIPE_FIJA
    return round(comision_total, 2)


def calcular_monto_net_stripe(monto):
    """Calcula el monto neto después de comisión de Stripe."""
    comision = calcular_comision_stripe(monto)
    return round(Decimal(str(monto)) - comision, 2)


# Referencias

def generar_numero_factura():
    """Genera el siguiente número de factura incremental: NX-YYYY-000001"""
    from facturacion.models import Factura

    anio = timezone.now().year
    prefijo = f"NX-{anio}-"
    ultima = (
        Factura.objects.filter(numero_factura__startswith=prefijo)
        .order_by("-numero_factura")
        .first()
    )
    if ultima:
        ultimo_numero = int(ultima.numero_factura.split("-")[-1])
        nuevo_numero = ultimo_numero + 1
    else:
        nuevo_numero = 1
    return f"{prefijo}{nuevo_numero:06d}"


def generar_referencia_pago(metodo_pago):
    """Genera una referencia única para pagos manuales."""
    timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
    prefijos = {
        "yape": "YAP",
        "plin": "PLN",
        "transferencia": "TRF",
        "efectivo": "EFE",
    }
    prefijo = prefijos.get(metodo_pago, "PAG")
    return f"{prefijo}-{timestamp}"


# Fechas

def calcular_fecha_vencimiento(dias=30):
    """Calcula la fecha de vencimiento de una factura."""
    return timezone.now().date() + timedelta(days=dias)


def calcular_fecha_fin_suscripcion(tipo_facturacion, fecha_inicio=None):
    """Calcula la fecha de fin de una suscripción."""
    if fecha_inicio is None:
        fecha_inicio = timezone.now().date()
    if tipo_facturacion == "anual":
        return fecha_inicio + timedelta(days=365)
    return fecha_inicio + timedelta(days=30)


# Formato

def formatear_moneda(monto):
    """Formatea un monto como moneda peruana."""
    return f"S/ {Decimal(str(monto)):,.2f}"


def formatear_numero_documento(numero):
    """Formatea un número de factura para impresión."""
    return numero.upper().replace(" ", "")


# PDF

def generar_pdf_factura(factura):
    """Genera un PDF de una factura usando xhtml2pdf. Retorna el PDF como bytes."""
    from io import BytesIO
    from django.template.loader import render_to_string
    from xhtml2pdf import pisa

    html_string = render_to_string(
        "facturacion/facturas/pdf_factura.html",
        {
            "factura": factura,
            "items": factura.items.all(),
            "nutricionista": factura.nutricionista,
            "paciente": factura.paciente,
        },
    )

    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html_string.encode("utf-8")), result)
    if pdf.err:
        raise RuntimeError(f"Error al generar PDF: {pdf.err}")
    return result.getvalue()


def generar_pdf_boleta_cobro(cobro):
    """Genera un PDF de boleta para un cobro a paciente."""
    from io import BytesIO
    from django.template.loader import render_to_string
    from xhtml2pdf import pisa

    html_string = render_to_string(
        "facturacion/cobros/pdf_boleta.html",
        {"cobro": cobro},
    )

    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html_string.encode("utf-8")), result)
    if pdf.err:
        raise RuntimeError(f"Error al generar PDF: {pdf.err}")
    return result.getvalue()


def generar_pdf_boleta_suscripcion(suscripcion, pago):
    """Genera un PDF de boleta para el pago de una suscripción."""
    from io import BytesIO
    from django.template.loader import render_to_string
    from xhtml2pdf import pisa

    html_string = render_to_string(
        "facturacion/suscripcion/pdf_boleta.html",
        {"suscripcion": suscripcion, "pago": pago},
    )

    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html_string.encode("utf-8")), result)
    if pdf.err:
        raise RuntimeError(f"Error al generar PDF: {pdf.err}")
    return result.getvalue()


def calcular_fecha_fin(fecha_inicio, tipo_facturacion):

    import calendar
    
    if tipo_facturacion == "anual":
        try:
            return fecha_inicio.replace(year=fecha_inicio.year + 1)
        except ValueError:
            # Año bisiesto (29 de febrero)
            return fecha_inicio.replace(year=fecha_inicio.year + 1, day=28)
    else:
        # Sumar 1 mes (mensual)
        month = fecha_inicio.month
        year = fecha_inicio.year
        
        month += 1
        if month > 12:
            month = 1
            year += 1
            
        ultimo_dia = calendar.monthrange(year, month)[1]
        day = min(fecha_inicio.day, ultimo_dia)
        
        return fecha_inicio.replace(year=year, month=month, day=day)

