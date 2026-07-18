# administracion/views/notifications.py
# Alertas globales.

from django.shortcuts import render, redirect
from django.contrib import messages

from administracion.mixins import admin_requerido
from administracion.models import NotificacionSistema, LogAuditoriaAdmin
from facturacion.models import PlanSuscripcion


@admin_requerido
def notificaciones_crear_view(request):
    """Crea una nueva alerta/notificación global del sistema para nutricionistas."""
    if request.method == "POST":
        titulo = request.POST.get("titulo", "").strip()
        mensaje = request.POST.get("mensaje", "").strip()
        tipo = request.POST.get("tipo", "info").strip()
        plan_destino = request.POST.get("plan_destino", "").strip()
        tipo_valido = tipo in dict(NotificacionSistema.TIPO_CHOICES)
        plan_valido = (
            not plan_destino
            or PlanSuscripcion.objects.filter(nombre=plan_destino).exists()
        )
        
        if len(titulo) > 200 or len(mensaje) > 10000:
            messages.error(request, "La notificación supera el tamaño permitido.")
        elif not tipo_valido or not plan_valido:
            messages.error(request, "El tipo o plan de destino no es válido.")
        elif not titulo or not mensaje:
            messages.error(request, "Por favor completa el título y mensaje de la notificación.")
        else:
            notificacion = NotificacionSistema.objects.create(
                titulo=titulo,
                mensaje=mensaje,
                tipo=tipo,
                plan_destino=plan_destino if plan_destino else None,
                activo=True
            )
            
            # Registrar auditoría
            LogAuditoriaAdmin.objects.create(
                administrador=request.user,
                accion="Enviar Alerta",
                detalle=f"Creó una alerta del sistema '{titulo}' de tipo '{tipo}' dirigida a: {'Todos los planes' if not plan_destino else plan_destino}."
            )
            
            messages.success(request, f"La alerta del sistema '{titulo}' ha sido enviada con éxito.")
            return redirect("administracion:dashboard")
            
    planes = PlanSuscripcion.objects.all()
    context = {
        "planes": planes,
        "tipos": NotificacionSistema.TIPO_CHOICES,
    }
    return render(request, "administracion/notifications/create.html", context)
