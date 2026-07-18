# core/admin.py
# Admin de nutricionistas.

from django.contrib import admin
from .models import PerfilNutricionista


@admin.register(PerfilNutricionista)
class PerfilNutricionistaAdmin(admin.ModelAdmin):
    list_display = (
        "nombre_completo",
        "usuario",
        "especialidad",
        "telefono",
        "estado",
        "fecha_registro",
    )
    list_filter = ("estado", "especialidad")
    search_fields = ("nombre_completo", "usuario__username", "numero_colegiatura")
    # Cambia el estado desde la lista.
    list_editable = ("estado",)
    readonly_fields = ("fecha_registro",)
    fieldsets = (
        ("Datos del Usuario", {"fields": ("usuario", "estado")}),
        (
            "Información Profesional",
            {
                "fields": (
                    "nombre_completo",
                    "especialidad",
                    "numero_colegiatura",
                    "email_profesional",
                    "telefono",
                    "direccion_consultorio",
                )
            },
        ),
        ("Registro", {"fields": ("fecha_registro",)}),
    )
