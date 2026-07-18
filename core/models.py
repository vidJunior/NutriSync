# core/models.py
# Perfil profesional del nutricionista. Extiende el User de Django.

from django.db import models
from django.contrib.auth.models import User
from config.choices import EstadoNutricionista


class Rol(models.TextChoices):
    """
    Roles de usuario dentro de la plataforma NutriSync.
    - NUTRICIONISTA: profesional que usa el panel de gestión clínica.
    - ADMIN_PLATAFORMA: operador que administra la plataforma desde /administracion/.
    """

    NUTRICIONISTA = "nutricionista", "Nutricionista"
    ADMIN_PLATAFORMA = "admin_plataforma", "Administrador de Plataforma"


class PerfilNutricionista(models.Model):
    """
    Perfil profesional del nutricionista que usa el sistema.
    Se crea automáticamente vía signal cuando se crea un superusuario.
    El campo 'estado' permite deshabilitar el acceso sin borrar la cuenta ni sus datos.
    """

    # OneToOne garantiza que cada User tenga a lo sumo un perfil profesional
    usuario = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="perfil",
        verbose_name="Usuario",
    )
    nombre_completo = models.CharField(
        max_length=150,
        verbose_name="Nombre completo",
    )
    especialidad = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Especialidad",
        help_text="Ej: Nutrición clínica, deportiva, pediátrica",
    )
    telefono = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Teléfono",
    )
    email_profesional = models.EmailField(
        blank=True,
        verbose_name="Email profesional",
    )
    numero_colegiatura = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Número de colegiatura",
    )
    dni = models.CharField(
        max_length=8,
        blank=True,
        null=True,
        verbose_name="DNI",
    )
    ruc = models.CharField(
        max_length=11,
        blank=True,
        null=True,
        verbose_name="RUC",
    )
    direccion_consultorio = models.TextField(
        blank=True,
        verbose_name="Dirección del consultorio",
    )
    foto = models.ImageField(
        upload_to="perfiles/fotos/",
        blank=True,
        null=True,
        verbose_name="Foto de perfil",
    )
    # El campo estado permite al admin deshabilitar el acceso sin eliminar la cuenta.
    # La login_view valida que estado == 'habilitado' antes de permitir el ingreso.
    estado = models.CharField(
        max_length=20,
        choices=EstadoNutricionista.CHOICES,
        default=EstadoNutricionista.HABILITADO,
        verbose_name="Estado",
    )
    rol = models.CharField(
        max_length=30,
        choices=Rol.choices,
        default=Rol.NUTRICIONISTA,
        verbose_name="Rol",
    )
    fecha_registro = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de registro",
    )

    class Meta:
        verbose_name = "Perfil de Nutricionista"
        verbose_name_plural = "Perfiles de Nutricionistas"

    def __str__(self):
        return f"{self.nombre_completo or self.usuario.username}"

    @property
    def esta_habilitado(self):
        """Devuelve True si el nutricionista puede acceder al sistema."""
        return self.estado == EstadoNutricionista.HABILITADO
