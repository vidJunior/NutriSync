# seguimiento/admin.py
# Admin de medidas y notas.

from django.contrib import admin
from .models import MedidaCorporal, NotaClinica


@admin.register(MedidaCorporal)
class MedidaCorporalAdmin(admin.ModelAdmin):
    list_display = [
        "paciente",
        "fecha",
        "peso_kg",
        "talla_cm",
        "imc",
        "grasa_corporal_pct",
        "cintura_cm",
    ]
    list_filter = ["fecha", "paciente"]
    search_fields = ["paciente__nombre", "paciente__apellido", "notas"]
    readonly_fields = ["imc"]  # IMC se calcula automáticamente en save()
    date_hierarchy = "fecha"

    # Evita consultas N+1.
    def get_queryset(self, request):
        return super().get_queryset(request).select_related("paciente")


@admin.register(NotaClinica)
class NotaClinicaAdmin(admin.ModelAdmin):
    list_display = ["titulo", "paciente", "fecha", "tipo", "cita_link"]
    list_filter = ["tipo", "fecha", "paciente"]
    search_fields = ["titulo", "contenido", "paciente__nombre", "paciente__apellido"]
    date_hierarchy = "fecha"

    def get_queryset(self, request):
        # select_related para evitar N+1 en paciente y cita
        return super().get_queryset(request).select_related("paciente", "cita")

    def cita_link(self, obj):
        """Muestra un enlace a la cita relacionada si existe."""
        if obj.cita:
            from django.utils.html import format_html
            from django.urls import reverse
            url = reverse("admin:agendas_cita_change", args=[obj.cita.pk])
            return format_html('<a href="{}">Cita #{}</a>', url, obj.cita.pk)
        return "—"

    cita_link.short_description = "Cita relacionada"
