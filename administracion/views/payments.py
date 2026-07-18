# administracion/views/payments.py
# Revisión de pagos.

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db import transaction
from datetime import timedelta
from decimal import Decimal

from administracion.mixins import admin_requerido
from administracion.models import LogAuditoriaAdmin
from facturacion.models import Pago, PlanSuscripcion, SuscripcionNutricionista
from facturacion.choices import EstadoPago, EstadoSuscripcion


@admin_requerido
def pagos_verificar_lista_view(request):
    """Lista las solicitudes de pago de suscripciones pendientes de verificación manual."""
    # Listamos pagos con estado pendiente
    pagos = Pago.objects.select_related("nutricionista__perfil", "cobro").filter(
        estado=EstadoPago.PENDIENTE
    ).order_by("-fecha_pago")
    
    return render(request, "administracion/payments/list.html", {"pagos": pagos})


@admin_requerido
@require_POST
@transaction.atomic
def pago_aprobar_view(request, pk):
    """Aprueba un pago de suscripción y activa/extiende la suscripción del nutricionista."""
    pago = get_object_or_404(Pago.objects.select_for_update(), pk=pk)
    
    if pago.estado != EstadoPago.PENDIENTE:
        messages.error(request, "Este pago ya no está en estado pendiente.")
        return redirect("administracion:pagos_verificar_lista")
    if not pago.nutricionista_id or pago.cobro_id or pago.factura_id:
        messages.error(request, "Este pago no corresponde a una suscripción.")
        return redirect("administracion:pagos_verificar_lista")
    if not pago.referencia and not pago.comprobante:
        messages.error(request, "El pago necesita una referencia o comprobante verificable.")
        return redirect("administracion:pagos_verificar_lista")
    
    # Buscar o activar la suscripción del nutricionista
    suscripcion = (
        SuscripcionNutricionista.objects.select_for_update()
        .filter(nutricionista=pago.nutricionista)
        .first()
    )
    creada = suscripcion is None
    if creada:
        coincidencias = []
        for plan in PlanSuscripcion.objects.filter(activo=True):
            if plan.precio_mensual == pago.monto:
                coincidencias.append((plan, "mensual", 30))
            if plan.precio_anual == pago.monto:
                coincidencias.append((plan, "anual", 365))
        if len(coincidencias) != 1:
            messages.error(
                request,
                "No se pudo identificar de forma única el plan pagado.",
            )
            return redirect("administracion:pagos_verificar_lista")
        plan, tipo_facturacion, dias_extension = coincidencias[0]
        hoy = timezone.localdate()
        suscripcion = SuscripcionNutricionista.objects.create(
            nutricionista=pago.nutricionista,
            plan=plan,
            tipo_facturacion=tipo_facturacion,
            precio_aplicado=pago.monto,
            estado=EstadoSuscripcion.ACTIVA,
            fecha_inicio=hoy,
            fecha_fin=hoy + timedelta(days=dias_extension),
        )
    
    # Extiende la suscripción existente.
    if not creada:
        hoy = timezone.now().date()
        suscripcion.estado = EstadoSuscripcion.ACTIVA
        suscripcion.precio_aplicado = pago.monto
        
        # Determinar días a extender
        dias_extension = 365 if suscripcion.tipo_facturacion == "anual" else 30
        
        if suscripcion.fecha_fin and suscripcion.fecha_fin > hoy:
            suscripcion.fecha_fin = suscripcion.fecha_fin + timedelta(days=dias_extension)
        else:
            suscripcion.fecha_inicio = hoy
            suscripcion.fecha_fin = hoy + timedelta(days=dias_extension)
            
        suscripcion.save()

    pago.estado = EstadoPago.COMPLETADO
    pago.save()
        
    # Registrar auditoría
    LogAuditoriaAdmin.objects.create(
        administrador=request.user,
        accion="Aprobar Pago",
        detalle=f"Aprobó el pago manual #{pago.id} de S/ {pago.monto} para @{pago.nutricionista.username} y activó su suscripción."
    )
    
    messages.success(request, f"Pago #{pago.id} aprobado con éxito. La suscripción de @{pago.nutricionista.username} está activa.")
    return redirect("administracion:pagos_verificar_lista")


@admin_requerido
@require_POST
def pago_rechazar_view(request, pk):
    """Rechaza un pago de suscripción cambiándolo a fallido."""
    pago = get_object_or_404(Pago, pk=pk)
    
    if pago.estado != EstadoPago.PENDIENTE:
        messages.error(request, "Este pago ya no está en estado pendiente.")
        return redirect("administracion:pagos_verificar_lista")
        
    pago.estado = EstadoPago.FALLIDO
    pago.save()
    
    # Registrar auditoría
    LogAuditoriaAdmin.objects.create(
        administrador=request.user,
        accion="Rechazar Pago",
        detalle=f"Rechazó el pago manual #{pago.id} de S/ {pago.monto} para @{pago.nutricionista.username}."
    )
    
    messages.warning(request, f"Pago #{pago.id} rechazado correctamente.")
    return redirect("administracion:pagos_verificar_lista")
