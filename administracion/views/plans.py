# administracion/views/plans.py
# Vistas para la gestión (CRUD) de planes de suscripción.

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.views.decorators.http import require_POST

from administracion.mixins import admin_requerido
from administracion.forms import PlanSuscripcionForm
from administracion.models import LogAuditoriaAdmin
from facturacion.models import PlanSuscripcion


@admin_requerido
def planes_lista_view(request):
    """Lista todos los planes de suscripción de la plataforma."""
    planes = PlanSuscripcion.objects.all().order_by('precio_mensual')
    return render(request, "administracion/plans/list.html", {"planes": planes})


@admin_requerido
def plan_crear_view(request):
    """Formulario para la creación de un nuevo plan de suscripción."""
    if request.method == "POST":
        form = PlanSuscripcionForm(request.POST)
        if form.is_valid():
            plan = form.save()
            # Registrar auditoría
            LogAuditoriaAdmin.objects.create(
                administrador=request.user,
                accion="Crear Plan",
                detalle=f"Creó el plan de suscripción '{plan.nombre}' con costo mensual de S/ {plan.precio_mensual}."
            )
            messages.success(request, f"El plan '{plan.nombre}' ha sido creado exitosamente.")
            return redirect("administracion:planes_lista")
    else:
        form = PlanSuscripcionForm()
        
    return render(request, "administracion/plans/form.html", {"form": form, "action": "Crear"})


@admin_requerido
def plan_editar_view(request, pk):
    """Formulario para editar un plan de suscripción existente."""
    plan = get_object_or_404(PlanSuscripcion, pk=pk)
    if request.method == "POST":
        form = PlanSuscripcionForm(request.POST, instance=plan)
        if form.is_valid():
            plan = form.save()
            # Registrar auditoría
            LogAuditoriaAdmin.objects.create(
                administrador=request.user,
                accion="Editar Plan",
                detalle=f"Modificó el plan de suscripción '{plan.nombre}' (ID: {plan.id})."
            )
            messages.success(request, f"El plan '{plan.nombre}' ha sido actualizado exitosamente.")
            return redirect("administracion:planes_lista")
    else:
        form = PlanSuscripcionForm(instance=plan)
        
    return render(request, "administracion/plans/form.html", {"form": form, "action": "Editar", "plan": plan})


@admin_requerido
@require_POST
def plan_toggle_view(request, pk):
    """Activa o desactiva un plan de suscripción."""
    plan = get_object_or_404(PlanSuscripcion, pk=pk)
    plan.activo = not plan.activo
    plan.save()
    
    estado_str = "activó" if plan.activo else "desactivó"
    # Registrar auditoría
    LogAuditoriaAdmin.objects.create(
        administrador=request.user,
        accion=f"{estado_str.capitalize()} Plan",
        detalle=f"Cambió el estado del plan '{plan.nombre}' (ID: {plan.id}) a {'Activo' if plan.activo else 'Inactivo'}."
    )
    
    messages.info(request, f"Se {estado_str} el plan '{plan.nombre}' correctamente.")
    return redirect("administracion:planes_lista")
