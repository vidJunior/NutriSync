# core/apps.py
# Configuración de core.

from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = "Core — Autenticación y Perfil"

    def ready(self):
        # Registra las señales al iniciar.
        # no se crea automáticamente al crear un superusuario.
        import core.signals  # noqa: F401
