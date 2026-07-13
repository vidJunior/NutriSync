# administracion/views/subscriptions.py
# Gestión de suscripciones del panel de administración.

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta

from administracion.mixins import admin_requerido
from facturacion.models import SuscripcionNutricionista, PlanSuscripcion
from facturacion.choices import EstadoSuscripcion


@admin_requerido
def suscripciones_lista_view(request):
    """Lista todas las suscripciones de los nutricionistas."""
    queryset = SuscripcionNutricionista.objects.select_related('nutricionista__perfil', 'plan').order_by('-fecha_creacion')

    estado = request.GET.get('estado', '').strip()
    plan_id = request.GET.get('plan', '').strip()
    q = request.GET.get('q', '').strip()

    if q:
        queryset = queryset.filter(
            Q(nutricionista__username__icontains=q) |
            Q(nutricionista__perfil__nombre_completo__icontains=q)
        )
    if estado:
        queryset = queryset.filter(estado=estado)
    if plan_id:
        queryset = queryset.filter(plan_id=plan_id)

    paginator = Paginator(queryset, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'estado_filtro': estado,
        'plan_filtro': plan_id,
        'q': q,
        'estados': EstadoSuscripcion.CHOICES,
        'planes': PlanSuscripcion.objects.all(),
    }
    return render(request, 'administracion/subscriptions/list.html', context)


@admin_requerido
def suscripcion_detalle_view(request, pk):
    """Detalle de una suscripción y sus opciones de gestión."""
    suscripcion = get_object_or_404(SuscripcionNutricionista, pk=pk)
    cobros = suscripcion.nutricionista.cobros.all().order_by('-fecha_creacion')
    planes_disponibles = PlanSuscripcion.objects.exclude(id=suscripcion.plan_id)

    context = {
        'suscripcion': suscripcion,
        'cobros': cobros,
        'planes': planes_disponibles,
    }
    return render(request, 'administracion/subscriptions/detail.html', context)


@admin_requerido
@require_POST
def suscripcion_cambiar_plan(request, pk):
    """Modifica el plan activo de la suscripción."""
    suscripcion = get_object_or_404(SuscripcionNutricionista, pk=pk)
    plan_id = request.POST.get('plan_id')
    plan = get_object_or_404(PlanSuscripcion, pk=plan_id)

    plan_anterior = suscripcion.plan.nombre
    suscripcion.plan = plan
    suscripcion.precio_aplicado = plan.precio_mensual if suscripcion.tipo_facturacion == 'mensual' else plan.precio_anual
    suscripcion.save()

    messages.success(request, f"Plan cambiado con éxito de {plan_anterior} a {plan.nombre}.")
    return redirect('administracion:suscripcion_detalle', pk=pk)


@admin_requerido
@require_POST
def suscripcion_cancelar(request, pk):
    """Cancela la renovación de la suscripción."""
    suscripcion = get_object_or_404(SuscripcionNutricionista, pk=pk)
    suscripcion.estado = EstadoSuscripcion.CANCELADA
    suscripcion.renovacion_automatica = False
    suscripcion.save()

    messages.warning(request, f"La suscripción de @{suscripcion.nutricionista.username} ha sido cancelada.")
    return redirect('administracion:suscripcion_detalle', pk=pk)


@admin_requerido
@require_POST
def suscripcion_reactivar(request, pk):
    """Reactiva la suscripción extendiendo el periodo por 30 días."""
    suscripcion = get_object_or_404(SuscripcionNutricionista, pk=pk)
    suscripcion.estado = EstadoSuscripcion.ACTIVA
    suscripcion.renovacion_automatica = True

    hoy = timezone.now().date()
    if suscripcion.fecha_fin and suscripcion.fecha_fin > hoy:
        suscripcion.fecha_fin = suscripcion.fecha_fin + timedelta(days=30)
    else:
        suscripcion.fecha_inicio = hoy
        suscripcion.fecha_fin = hoy + timedelta(days=30)

    suscripcion.save()
    messages.success(request, f"La suscripción ha sido reactivada hasta el {suscripcion.fecha_fin.strftime('%d/%m/%Y')}.")
    return redirect('administracion:suscripcion_detalle', pk=pk)
