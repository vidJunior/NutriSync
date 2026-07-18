# facturacion/models.py
# Modelos del módulo de Facturación y Cobros de NutriSync.
# Gestiona cobros a pacientes, facturación con IGV, pagos y suscripciones.

from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
from pacientes.models import Paciente
from facturacion.choices import (
    MetodoPago,
    EstadoCobro,
    ConceptoCobro,
    EstadoFactura,
    EstadoPago,
    EstadoSuscripcion,
    TipoFacturacion,
)


class PlanSuscripcion(models.Model):
    """
    Define los planes de suscripción disponibles para los nutricionistas.
    Cada plan tiene límites, comisiones y un precio asociado en Stripe.
    """

    nombre = models.CharField(
        max_length=50,
        verbose_name="Nombre del plan",
    )
    descripcion = models.TextField(
        blank=True,
        verbose_name="Descripción",
    )
    precio_mensual = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        verbose_name="Precio mensual (S/)",
    )
    precio_anual = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        verbose_name="Precio anual (S/)",
        help_text="Precio con descuento por facturación anual",
    )
    limite_pacientes = models.IntegerField(
        verbose_name="Límite de pacientes",
        help_text="Número máximo de pacientes (-1 = ilimitado)",
        default=-1,
    )
    limite_citas_mes = models.IntegerField(
        verbose_name="Límite de citas por mes",
        help_text="Número máximo de citas al mes (-1 = ilimitado)",
        default=-1,
    )
    comision_cobros = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Comisión sobre cobros (%)",
        help_text="Porcentaje de comisión sobre cada cobro a pacientes",
    )
    comision_suscripcion = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Comisión sobre suscripción (%)",
        help_text="Porcentaje adicional sobre el cobro de la suscripción",
    )
    stripe_price_id_mensual = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Stripe Price ID (Mensual)",
    )
    stripe_price_id_anual = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Stripe Price ID (Anual)",
    )
    activo = models.BooleanField(
        default=True,
        verbose_name="Activo",
    )

    class Meta:
        verbose_name = "Plan de Suscripción"
        verbose_name_plural = "Planes de Suscripción"
        ordering = ["precio_mensual"]

    def __str__(self):
        return f"{self.nombre} - S/{self.precio_mensual}/mes"


class SuscripcionNutricionista(models.Model):
    """
    Registra la suscripción activa de un nutricionista a un plan.
    Vincula con Stripe para gestionar cobros recurrentes.
    """

    nutricionista = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="suscripcion",
        verbose_name="Nutricionista",
    )
    plan = models.ForeignKey(
        PlanSuscripcion,
        on_delete=models.PROTECT,
        verbose_name="Plan",
    )
    tipo_facturacion = models.CharField(
        max_length=10,
        choices=TipoFacturacion.CHOICES,
        default=TipoFacturacion.MENSUAL,
        verbose_name="Tipo de facturación",
    )
    precio_aplicado = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        verbose_name="Precio aplicado (S/)",
    )
    estado = models.CharField(
        max_length=20,
        choices=EstadoSuscripcion.CHOICES,
        default=EstadoSuscripcion.PENDIENTE,
        verbose_name="Estado",
    )
    fecha_inicio = models.DateField(
        verbose_name="Fecha de inicio",
    )
    fecha_fin = models.DateField(
        verbose_name="Fecha de fin",
    )
    stripe_subscription_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Stripe Subscription ID",
    )
    stripe_customer_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Stripe Customer ID",
    )
    renovacion_automatica = models.BooleanField(
        default=True,
        verbose_name="Renovación automática",
    )
    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de registro",
    )

    class Meta:
        verbose_name = "Suscripción"
        verbose_name_plural = "Suscripciones"

    def __str__(self):
        return f"{self.nutricionista.username} - {self.plan.nombre} ({self.get_estado_display()})"

    @property
    def esta_activa(self):
        return self.estado == EstadoSuscripcion.ACTIVA

    @property
    def dias_restantes(self):
        if self.fecha_fin:
            delta = self.fecha_fin - timezone.now().date()
            return max(0, delta.days)
        return 0


class Cobro(models.Model):
    """
    Representa un cobro a un paciente por servicios prestados.
    Puede estar vinculado a una cita o ser un cobro manual.
    """

    nutricionista = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="cobros",
        verbose_name="Nutricionista",
    )
    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.CASCADE,
        related_name="cobros",
        verbose_name="Paciente",
    )
    cita = models.ForeignKey(
        "agendas.Cita",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cobros",
        verbose_name="Cita asociada",
    )
    concepto = models.CharField(
        max_length=30,
        choices=ConceptoCobro.CHOICES,
        default=ConceptoCobro.CONSULTA,
        verbose_name="Concepto",
    )
    descripcion = models.TextField(
        verbose_name="Descripción",
        help_text="Detalle del servicio facturado",
    )
    monto = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        verbose_name="Monto (S/)",
    )
    igv = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="IGV (18%)",
    )
    total = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Total (S/)",
    )
    comision_plataforma = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Comisión plataforma (S/)",
    )
    monto_neto = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Monto neto (S/)",
    )
    estado = models.CharField(
        max_length=20,
        choices=EstadoCobro.CHOICES,
        default=EstadoCobro.PENDIENTE,
        verbose_name="Estado",
    )
    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de creación",
    )
    fecha_pago = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de pago",
    )
    metodo_pago_usado = models.CharField(
        max_length=20,
        choices=MetodoPago.CHOICES,
        blank=True,
        verbose_name="Método de pago utilizado",
    )
    referencia_pago = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Referencia de pago",
        help_text="Código de transacción o referencia del pago",
    )
    comprobante_pago = models.FileField(
        upload_to="comprobantes/%Y/%m/",
        blank=True,
        verbose_name="Comprobante de pago",
        help_text="Captura o comprobante del pago realizado",
    )
    stripe_payment_intent_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Stripe Payment Intent ID",
    )
    notas = models.TextField(
        blank=True,
        verbose_name="Notas internas",
    )

    class Meta:
        verbose_name = "Cobro"
        verbose_name_plural = "Cobros"
        ordering = ["-fecha_creacion"]
        indexes = [
            models.Index(fields=["estado", "fecha_creacion"]),
            models.Index(fields=["paciente", "estado"]),
        ]

    def __str__(self):
        return f"Cobro #{self.pk} - {self.paciente} - S/{self.total}"

    def save(self, *args, **kwargs):
        # Calcular IGV, total y monto neto automáticamente
        if not (self.descripcion or "").strip():
            self.descripcion = self.get_concepto_display()
        if self.monto:
            monto_dec = Decimal(str(self.monto))
            if self.nutricionista_id:
                try:
                    suscripcion = self.nutricionista.suscripcion
                except Exception:
                    suscripcion = None
                if suscripcion and suscripcion.estado == "activa":
                    comision_pct = suscripcion.plan.comision_cobros
                else:
                    comision_pct = Decimal("3.00")
                self.comision_plataforma = round((monto_dec * comision_pct) / Decimal("100.00"), 2)
            else:
                self.comision_plataforma = Decimal("0.00")

            from facturacion.utils import calcular_igv, calcular_total_con_igv, calcular_monto_neto
            self.igv = calcular_igv(monto_dec)
            self.total = calcular_total_con_igv(monto_dec)
            self.monto_neto = calcular_monto_neto(self.total, self.comision_plataforma)
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def esta_pagado(self):
        return self.estado == EstadoCobro.PAGADO

    @property
    def esta_pendiente(self):
        return self.estado == EstadoCobro.PENDIENTE

    @property
    def es_pago_manual(self):
        return self.metodo_pago_usado in MetodoPago.MANUALES if self.metodo_pago_usado else False

    @property
    def requiere_verificacion(self):
        return self.es_pago_manual and self.comprobante_pago and self.estado == EstadoCobro.PENDIENTE


class Factura(models.Model):
    """
    Documento fiscal que agrupa uno o varios cobros de un paciente.
    Incluye IGV (18%) y genera un PDF descargable.
    """

    numero_factura = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="Número de factura",
    )
    nutricionista = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="facturas",
        verbose_name="Nutricionista",
    )
    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.CASCADE,
        related_name="facturas",
        verbose_name="Paciente",
    )
    fecha_emision = models.DateField(
        default=timezone.now,
        verbose_name="Fecha de emisión",
    )
    fecha_vencimiento = models.DateField(
        verbose_name="Fecha de vencimiento",
    )
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Subtotal (S/)",
    )
    igv = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="IGV 18% (S/)",
    )
    total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Total (S/)",
    )
    estado = models.CharField(
        max_length=20,
        choices=EstadoFactura.CHOICES,
        default=EstadoFactura.BORRADOR,
        verbose_name="Estado",
    )
    notas = models.TextField(
        blank=True,
        verbose_name="Notas",
    )
    archivo_pdf = models.FileField(
        upload_to="facturas/%Y/%m/",
        blank=True,
        verbose_name="Archivo PDF",
    )
    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de creación",
    )

    class Meta:
        verbose_name = "Factura"
        verbose_name_plural = "Facturas"
        ordering = ["-fecha_emision"]
        indexes = [
            models.Index(fields=["numero_factura"]),
            models.Index(fields=["estado", "fecha_emision"]),
        ]

    def __str__(self):
        return f"Factura {self.numero_factura} - S/{self.total}"

    def save(self, *args, **kwargs):
        if not self.numero_factura:
            self.numero_factura = self._generar_numero_factura()
        super().save(*args, **kwargs)

    def _generar_numero_factura(self):
        """Genera el número de factura incremental: NX-YYYY-000001"""
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

    def calcular_totales(self):
        """Recalcula los totales basándose en los items de la factura."""
        from facturacion.utils import IGV_PORCENTAJE
        items = self.items.all()
        self.subtotal = sum(item.subtotal for item in items)
        self.igv = self.subtotal * IGV_PORCENTAJE
        self.total = self.subtotal + self.igv
        self.save(update_fields=["subtotal", "igv", "total"])


class ItemFactura(models.Model):
    """
    Línea individual dentro de una factura.
    Vincula con un cobro específico o es un ítem manual.
    """

    factura = models.ForeignKey(
        Factura,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Factura",
    )
    cobro = models.ForeignKey(
        Cobro,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="items_factura",
        verbose_name="Cobro asociado",
    )
    descripcion = models.CharField(
        max_length=200,
        verbose_name="Descripción",
    )
    cantidad = models.PositiveIntegerField(
        default=1,
        verbose_name="Cantidad",
    )
    precio_unitario = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        verbose_name="Precio unitario (S/)",
    )
    subtotal = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Subtotal (S/)",
    )

    class Meta:
        verbose_name = "Ítem de Factura"
        verbose_name_plural = "Ítems de Factura"

    def __str__(self):
        return f"{self.descripcion} x{self.cantidad} - S/{self.subtotal}"

    def save(self, *args, **kwargs):
        self.subtotal = Decimal(str(self.cantidad)) * self.precio_unitario
        super().save(*args, **kwargs)


class Pago(models.Model):
    """
    Registra un pago realizado por un paciente.
    Puede estar vinculado a un cobro o factura específica.
    """

    nutricionista = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pagos_facturacion",
        verbose_name="Nutricionista",
    )
    cobro = models.ForeignKey(
        Cobro,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pagos",
        verbose_name="Cobro",
    )
    factura = models.ForeignKey(
        Factura,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pagos",
        verbose_name="Factura",
    )
    monto = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        verbose_name="Monto (S/)",
    )
    metodo_pago = models.CharField(
        max_length=20,
        choices=MetodoPago.CHOICES,
        verbose_name="Método de pago",
    )
    stripe_payment_intent_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Stripe Payment Intent ID",
    )
    stripe_charge_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Stripe Charge ID",
    )
    referencia = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Referencia",
    )
    comprobante = models.FileField(
        upload_to="comprobantes_pago/%Y/%m/",
        blank=True,
        verbose_name="Comprobante",
    )
    fecha_pago = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de pago",
    )
    estado = models.CharField(
        max_length=20,
        choices=EstadoPago.CHOICES,
        default=EstadoPago.PENDIENTE,
        verbose_name="Estado",
    )
    comision_stripe = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Comisión Stripe (S/)",
    )
    monto_neto = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Monto neto recibido (S/)",
    )
    notas = models.TextField(
        blank=True,
        verbose_name="Notas",
    )

    class Meta:
        verbose_name = "Pago"
        verbose_name_plural = "Pagos"
        ordering = ["-fecha_pago"]

    def __str__(self):
        return f"Pago #{self.pk} - S/{self.monto} - {self.get_metodo_pago_display()}"
