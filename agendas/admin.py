from django.contrib import admin
from .models import Cita


@admin.register(Cita)
class CitaAdmin(admin.ModelAdmin):
    """Configuración del panel de administración para el modelo Cita."""

    list_display = (
        "paciente",
        "fecha_hora",
        "duracion_minutos",
        "tipo",
        "estado",
        "costo",
        "fecha_creacion",
    )
    list_filter = (
        "estado",
        "tipo",
        "fecha_hora",
        "paciente__nutricionista",
    )
    search_fields = (
        "paciente__nombre",
        "paciente__apellido",
        "motivo",
        "notas_consulta",
    )
    date_hierarchy = "fecha_hora"
    ordering = ("-fecha_hora",)

    def get_queryset(self, request):
        # Optimizamos queries en el admin agregando select_related para evitar N+1 queries
        return super().get_queryset(request).select_related("paciente", "paciente__nutricionista")

