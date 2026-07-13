# administracion/views/payments.py
# Vistas para la verificación y aprobación de pagos de suscripciones.

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from administracion.mixins import admin_requerido
from administracion.models import LogAuditoriaAdmin
from facturacion.models import Pago, SuscripcionNutricionista
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
def pago_aprobar_view(request, pk):
    """Aprueba un pago de suscripción y activa/extiende la suscripción del nutricionista."""
    pago = get_object_or_404(Pago, pk=pk)
    
    if pago.estado != EstadoPago.PENDIENTE:
        messages.error(request, "Este pago ya no está en estado pendiente.")
        return redirect("administracion:pagos_verificar_lista")
        
    pago.estado = EstadoPago.COMPLETADO
    pago.save()
    
    # Buscar o activar la suscripción del nutricionista
    suscripcion, creada = SuscripcionNutricionista.objects.get_or_create(
        nutricionista=pago.nutricionista,
        defaults={
            "plan_id": 1, # ID por defecto o el plan en pago
            "tipo_facturacion": "mensual",
            "precio_aplicado": pago.monto,
            "estado": EstadoSuscripcion.ACTIVA,
            "fecha_inicio": timezone.now().date(),
            "fecha_fin": timezone.now().date() + timedelta(days=30),
        }
    )
    
    # Si la suscripción ya existía, la actualizamos y extendemos
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
