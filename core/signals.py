# core/signals.py
# Los perfiles profesionales se crean de forma explícita en el registro web.

from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
@receiver(post_save, sender=User)
def crear_perfil_nutricionista(sender, instance, created, **kwargs):
    """Reserva la señal para compatibilidad sin clasificar pacientes como profesionales."""
    return None
