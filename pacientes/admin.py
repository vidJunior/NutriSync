# pacientes/admin.py
# Admin de pacientes.

from django.contrib import admin
from .models import Paciente


@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "apellido",
        "telefono",
        "email",
        "sexo",
        "estado",
        "talla",
        "nutricionista",
        "fecha_registro",
    )
    list_filter = ("estado", "sexo", "fecha_registro")
    search_fields = ("nombre", "apellido", "telefono", "email")
    # Cambia el estado desde la lista.
    list_editable = ("estado",)
    readonly_fields = ("fecha_registro", "fecha_actualizacion")
    date_hierarchy = "fecha_registro"
    fieldsets = (
        (
            "Nutricionista",
            {"fields": ("nutricionista", "estado")},
        ),
        (
            "Datos Personales",
            {
                "fields": (
                    "nombre",
                    "apellido",
                    "fecha_nacimiento",
                    "sexo",
                    "peso",
                    "talla",
                    "ocupacion",
                )
            },
        ),
        (
            "Contacto",
            {
                "fields": (
                    "telefono",
                    "email",
                    "direccion",
                )
            },
        ),
        (
            "Información de Salud",
            {
                "fields": (
                    "condiciones_medicas",
                    "alergias",
                    "notas_generales",
                )
            },
        ),
        (
            "Registro",
            {"fields": ("fecha_registro", "fecha_actualizacion")},
        ),
    )
