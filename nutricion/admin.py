# nutricion/admin.py

from django.contrib import admin
from .models import (
    PerfilUsuario,
    MetaNutricional,
    RegistroComida,
    ItemRegistro,
    RegistroHabito,
    Logro,
    LogroUsuario,
)


# =========================
# PERFIL
# =========================
@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    list_display = ("usuario", "peso_kg", "talla_cm", "edad", "nivel_actividad", "objetivo")
    search_fields = ("usuario__username",)
    fieldsets = (
        ("Usuario", {
            "fields": ("usuario",)
        }),
        ("Datos físicos", {
            "fields": ("peso_kg", "talla_cm", "edad", "sexo")
        }),
        ("Objetivos", {
            "fields": ("nivel_actividad", "objetivo")
        }),
    )


# =========================
# META
# =========================
@admin.register(MetaNutricional)
class MetaNutricionalAdmin(admin.ModelAdmin):
    list_display = ("perfil", "calorias_meta", "proteinas_g", "carbohidratos_g", "grasas_g", "agua_ml")
    fieldsets = (
        ("Perfil", {"fields": ("perfil",)}),
        ("Macronutrientes", {"fields": ("calorias_meta", "proteinas_g", "carbohidratos_g", "grasas_g")}),
        ("Otros", {"fields": ("agua_ml",)}),
    )


# =========================
# ITEM INLINE
# =========================
class ItemRegistroInline(admin.TabularInline):
    model = ItemRegistro
    extra = 1


# =========================
# REGISTRO COMIDA
# =========================
@admin.register(RegistroComida)
class RegistroComidaAdmin(admin.ModelAdmin):
    list_display = ("usuario", "fecha", "tipo_comida", "total_calorias")
    list_filter = ("fecha", "tipo_comida")
    inlines = [ItemRegistroInline]

    fieldsets = (
        ("Información", {
            "fields": ("usuario", "fecha", "tipo_comida")
        }),
    )


# =========================
# ITEM REGISTRO
# =========================
@admin.register(ItemRegistro)
class ItemRegistroAdmin(admin.ModelAdmin):
    list_display = ("registro", "alimento", "cantidad_g", "total_calorias")
    list_filter = ("alimento",)


# =========================
# HÁBITOS
# =========================
@admin.register(RegistroHabito)
class RegistroHabitoAdmin(admin.ModelAdmin):
    list_display = ("usuario", "fecha", "vasos_agua", "horas_sueno", "pasos", "minutos_ejercicio")
    list_filter = ("fecha",)

    fieldsets = (
        ("Usuario", {"fields": ("usuario", "fecha")}),
        ("Salud", {"fields": ("vasos_agua", "horas_sueno")}),
        ("Actividad", {"fields": ("pasos", "minutos_ejercicio", "tipo_ejercicio")}),
    )


# =========================
# LOGROS
# =========================
@admin.register(Logro)
class LogroAdmin(admin.ModelAdmin):
    list_display = ("nombre", "tipo")
    search_fields = ("nombre",)

    fieldsets = (
        ("General", {"fields": ("nombre", "descripcion", "tipo", "icono")}),
        ("Condición", {"fields": ("condicion",)}),
    )


# =========================
# LOGROS USUARIO
# =========================
@admin.register(LogroUsuario)
class LogroUsuarioAdmin(admin.ModelAdmin):
    list_display = ("usuario", "logro", "fecha_obtenido")
    list_filter = ("fecha_obtenido",)