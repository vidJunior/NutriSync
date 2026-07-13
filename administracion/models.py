# administracion/models.py
# Modelos del módulo de administración de NutriSync.

from django.db import models
from django.contrib.auth.models import User

class LogAuditoriaAdmin(models.Model):
    """Registra las acciones críticas realizadas por los administradores de la plataforma."""
    administrador = models.ForeignKey(User, on_delete=models.CASCADE, related_name="logs_auditoria")
    accion = models.CharField(max_length=100)
    detalle = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha"]
        verbose_name = "Log de Auditoría"
        verbose_name_plural = "Logs de Auditoría"

    def __str__(self):
        return f"{self.administrador.username} - {self.accion} ({self.fecha.strftime('%d/%m/%Y %H:%M')})"


class NotificacionSistema(models.Model):
    """Banners de alertas globales o segmentadas para los nutricionistas creadas por el soporte."""
    TIPO_CHOICES = [
        ("info", "Informativa"),
        ("warning", "Advertencia"),
        ("critical", "Crítica"),
    ]
    titulo = models.CharField(max_length=200)
    mensaje = models.TextField()
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES, default="info")
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    plan_destino = models.CharField(
        max_length=50, 
        blank=True, 
        null=True, 
        help_text="Plan específico al que va dirigida (vacío para todos)"
    )

    class Meta:
        ordering = ["-fecha_creacion"]
        verbose_name = "Notificación de Sistema"
        verbose_name_plural = "Notificaciones de Sistema"

    def __str__(self):
        return f"{self.titulo} ({self.tipo})"


class LimiteOverride(models.Model):
    """Establece límites de recursos adicionales para un nutricionista específico."""
    nutricionista = models.OneToOneField(User, on_delete=models.CASCADE, related_name="override_limite")
    pacientes_adicionales = models.IntegerField(default=0, help_text="Tope adicional de pacientes")
    citas_adicionales_mes = models.IntegerField(default=0, help_text="Tope adicional de citas al mes")
    notas = models.TextField(blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_expiracion = models.DateField(blank=True, null=True, help_text="Fecha de vencimiento del beneficio (opcional)")

    class Meta:
        verbose_name = "Override de Límite"
        verbose_name_plural = "Overrides de Límites"

    def __str__(self):
        return f"Override para @{self.nutricionista.username} (+{self.pacientes_adicionales} pac, +{self.citas_adicionales_mes} citas)"


class TicketSoporte(models.Model):
    """Registra y gestiona las solicitudes de soporte técnico hechas por nutricionistas."""
    ESTADO_CHOICES = [
        ("abierto", "Abierto (Pendiente)"),
        ("proceso", "En Proceso"),
        ("resuelto", "Resuelto"),
    ]
    nutricionista = models.ForeignKey(User, on_delete=models.CASCADE, related_name="tickets")
    asunto = models.CharField(max_length=150)
    mensaje = models.TextField()
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default="abierto")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    respuesta_admin = models.TextField(blank=True, null=True)
    fecha_respuesta = models.DateTimeField(blank=True, null=True)
    respondido_por = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="respuestas_tickets"
    )

    class Meta:
        verbose_name = "Ticket de Soporte"
        verbose_name_plural = "Tickets de Soporte"
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return f"Ticket #{self.pk}: {self.asunto} (@{self.nutricionista.username}) - {self.get_estado_display()}"
