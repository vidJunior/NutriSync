# core/context_processors.py
# Añade el perfil y las alertas al contexto.

from .models import PerfilNutricionista
from administracion.models import NotificacionSistema


def perfil_nutricionista(request):
    """
    Agrega el perfil del nutricionista autenticado y las alertas del sistema
    al contexto global de templates.
    """
    context = {"perfil": None, "notificaciones_sistema": []}
    
    if request.user.is_authenticated:
        try:
            context["perfil"] = request.user.perfil
        except PerfilNutricionista.DoesNotExist:
            pass
            
        # Filtrar alertas del sistema activas
        try:
            from administracion.models import NotificacionLeida
            alertas_validas = NotificacionSistema.para_usuario(request.user)
            leidas_ids = NotificacionLeida.objects.filter(usuario=request.user).values_list("notificacion_id", flat=True)
            alertas_restantes = alertas_validas.exclude(id__in=leidas_ids)
            context["notificaciones_sistema"] = alertas_restantes
            context["alertas_pendientes_count"] = alertas_restantes.count()
        except Exception:
            pass

    return context
