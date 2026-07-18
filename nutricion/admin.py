# nutricion/admin.py
# Admin de nutrición.

from django.contrib import admin
from .models import Alimento, PlanNutricional, ComidaPlan


# Comidas del plan

class ComidaPlanInline(admin.TabularInline):
    """
    Inline de ComidaPlan dentro de PlanNutricional.
    Permite agregar/editar comidas directamente desde el plan en el admin.
    """
    model = ComidaPlan
    extra = 1
    fields = ("tipo_comida", "hora_sugerida", "receta", "observaciones")


# Alimentos

@admin.register(Alimento)
class AlimentoAdmin(admin.ModelAdmin):
    """
    Administración del catálogo de alimentos.
    Permite buscar, filtrar por categoría y ordenar por nombre.
    """
    list_display = ("nombre", "categoria", "calorias_100g", "proteinas_100g",
                    "carbohidratos_100g", "grasas_100g", "estado", "fecha_registro")
    list_filter = ("categoria", "estado")
    search_fields = ("nombre",)
    list_editable = ("estado",)
    ordering = ("nombre",)
    fieldsets = (
        ("Información general", {
            "fields": ("nombre", "categoria", "porcion_referencia", "estado")
        }),
        ("Valores nutricionales por 100g", {
            "fields": ("calorias_100g", "proteinas_100g", "carbohidratos_100g", "grasas_100g", "fibra_100g"),
            "description": "Todos los valores son por cada 100 gramos del alimento.",
        }),
    )


# Planes nutricionales

@admin.register(PlanNutricional)
class PlanNutricionalAdmin(admin.ModelAdmin):
    """
    Administración de modelos de planes nutricionales.
    """
    list_display = ("nombre", "nutricionista", "objetivo", "tipo_paciente", "calorias_diarias", "estado", "fecha_creacion")
    list_filter = ("estado", "objetivo", "fecha_creacion")
    search_fields = ("nombre", "tipo_paciente")
    list_select_related = ("nutricionista",)
    ordering = ("-fecha_creacion",)
    inlines = [ComidaPlanInline]
    fieldsets = (
        ("Información del plan", {
            "fields": ("nutricionista", "nombre", "objetivo", "tipo_paciente", "estado")
        }),
        ("Metas del modelo", {
            "fields": ("calorias_diarias", "proteinas_g", "carbohidratos_g", "grasas_g", "fibra_g", "agua_recomendada", "num_comidas"),
            "description": "Valores diarios objetivo para este modelo de plan.",
        }),
        ("Descripción", {
            "fields": ("descripcion",),
        }),
    )


# Administración de comidas

@admin.register(ComidaPlan)
class ComidaPlanAdmin(admin.ModelAdmin):
    """
    Administración independiente de comidas del plan.
    También accesible desde el inline en PlanNutricionalAdmin.
    """
    list_display = ("__str__", "plan", "tipo_comida", "hora_sugerida", "receta")
    list_filter = ("tipo_comida",)
    search_fields = ("plan__nombre", "tipo_comida", "receta__nombre")
    list_select_related = ("plan", "receta")
