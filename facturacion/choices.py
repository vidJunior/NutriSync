# facturacion/choices.py
# Choices centralizados para el módulo de Facturación.


class MetodoPago:
    STRIPE = "stripe"
    YAPE = "yape"
    PLIN = "plin"
    PAYPAL = "paypal"
    TRANSFERENCIA = "transferencia"
    EFECTIVO = "efectivo"
    CHOICES = [
        (STRIPE, "Tarjeta (Stripe)"),
        (YAPE, "Yape"),
        (PLIN, "Plin"),
        (PAYPAL, "PayPal"),
        (TRANSFERENCIA, "Transferencia Bancaria"),
        (EFECTIVO, "Efectivo"),
    ]
    # Métodos que requieren verificación manual
    MANUALES = [YAPE, PLIN, TRANSFERENCIA, EFECTIVO]


class EstadoCobro:
    PENDIENTE = "pendiente"
    PAGADO = "pagado"
    CANCELADO = "cancelado"
    VENCIDO = "vencido"
    CHOICES = [
        (PENDIENTE, "Pendiente"),
        (PAGADO, "Pagado"),
        (CANCELADO, "Cancelado"),
        (VENCIDO, "Vencido"),
    ]


class ConceptoCobro:
    CONSULTA = "consulta"
    PLAN_ALIMENTARIO = "plan_alimentario"
    SEGUIMIENTO = "seguimiento"
    PAQUETE = "paquete"
    OTRO = "otro"
    CHOICES = [
        (CONSULTA, "Consulta"),
        (PLAN_ALIMENTARIO, "Plan Alimentario"),
        (SEGUIMIENTO, "Seguimiento"),
        (PAQUETE, "Paquete"),
        (OTRO, "Otro"),
    ]


class EstadoFactura:
    BORRADOR = "borrador"
    EMITIDA = "emitida"
    PAGADA = "pagada"
    VENCIDA = "vencida"
    CANCELADA = "cancelada"
    CHOICES = [
        (BORRADOR, "Borrador"),
        (EMITIDA, "Emitida"),
        (PAGADA, "Pagada"),
        (VENCIDA, "Vencida"),
        (CANCELADA, "Cancelada"),
    ]


class EstadoPago:
    PENDIENTE = "pendiente"
    COMPLETADO = "completado"
    FALLIDO = "fallido"
    REEMBOLSADO = "reembolsado"
    CHOICES = [
        (PENDIENTE, "Pendiente"),
        (COMPLETADO, "Completado"),
        (FALLIDO, "Fallido"),
        (REEMBOLSADO, "Reembolsado"),
    ]


class EstadoSuscripcion:
    ACTIVA = "activa"
    CANCELADA = "cancelada"
    VENCIDA = "vencida"
    PENDIENTE = "pendiente_pago"
    CHOICES = [
        (ACTIVA, "Activa"),
        (CANCELADA, "Cancelada"),
        (VENCIDA, "Vencida"),
        (PENDIENTE, "Pendiente de pago"),
    ]


class TipoFacturacion:
    MENSUAL = "mensual"
    ANUAL = "anual"
    CHOICES = [
        (MENSUAL, "Mensual"),
        (ANUAL, "Anual"),
    ]


class PlanNutricionista:
    BASICO = "basico"
    PROFESIONAL = "profesional"
    CHOICES = [
        (BASICO, "Básico"),
        (PROFESIONAL, "Profesional"),
    ]
