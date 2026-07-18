# facturacion/admin.py
# Admin de facturación.

from django.contrib import admin
from facturacion.models import (
    PlanSuscripcion,
    SuscripcionNutricionista,
    Cobro,
    Factura,
    ItemFactura,
    Pago,
)


@admin.register(PlanSuscripcion)
class PlanSuscripcionAdmin(admin.ModelAdmin):
    list_display = [
        "nombre",
        "precio_mensual",
        "precio_anual",
        "limite_pacientes",
        "limite_citas_mes",
        "comision_cobros",
        "activo",
    ]
    list_filter = ["activo"]
    search_fields = ["nombre"]


@admin.register(SuscripcionNutricionista)
class SuscripcionNutricionistaAdmin(admin.ModelAdmin):
    list_display = [
        "nutricionista",
        "plan",
        "tipo_facturacion",
        "precio_aplicado",
        "estado",
        "fecha_inicio",
        "fecha_fin",
    ]
    list_filter = ["estado", "tipo_facturacion", "plan"]
    search_fields = ["nutricionista__username", "nutricionista__email"]
    raw_id_fields = ["nutricionista", "plan"]


@admin.register(Cobro)
class CobroAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "paciente",
        "nutricionista",
        "concepto",
        "monto",
        "igv",
        "total",
        "estado",
        "metodo_pago_usado",
        "fecha_creacion",
    ]
    list_filter = ["estado", "concepto", "metodo_pago_usado", "fecha_creacion"]
    search_fields = [
        "paciente__nombre",
        "paciente__apellido",
        "nutricionista__username",
        "referencia_pago",
    ]
    raw_id_fields = ["paciente", "nutricionista", "cita"]
    readonly_fields = ["igv", "total", "monto_neto", "fecha_creacion"]
    date_hierarchy = "fecha_creacion"


@admin.register(Factura)
class FacturaAdmin(admin.ModelAdmin):
    list_display = [
        "numero_factura",
        "nutricionista",
        "paciente",
        "subtotal",
        "igv",
        "total",
        "estado",
        "fecha_emision",
        "fecha_vencimiento",
    ]
    list_filter = ["estado", "fecha_emision"]
    search_fields = [
        "numero_factura",
        "paciente__nombre",
        "paciente__apellido",
        "nutricionista__username",
    ]
    raw_id_fields = ["nutricionista", "paciente"]
    readonly_fields = ["numero_factura", "subtotal", "igv", "total", "fecha_creacion"]
    date_hierarchy = "fecha_emision"


@admin.register(ItemFactura)
class ItemFacturaAdmin(admin.ModelAdmin):
    list_display = [
        "factura",
        "descripcion",
        "cantidad",
        "precio_unitario",
        "subtotal",
    ]
    raw_id_fields = ["factura", "cobro"]
    readonly_fields = ["subtotal"]


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "monto",
        "metodo_pago",
        "estado",
        "comision_stripe",
        "monto_neto",
        "fecha_pago",
    ]
    list_filter = ["estado", "metodo_pago", "fecha_pago"]
    search_fields = ["referencia", "stripe_payment_intent_id"]
    raw_id_fields = ["cobro", "factura"]
    readonly_fields = ["fecha_pago", "comision_stripe", "monto_neto"]
    date_hierarchy = "fecha_pago"
