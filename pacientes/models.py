# pacientes/models.py
# Modelo Paciente — ficha clínica de la persona atendida por el nutricionista.
# El FK nutricionista aísla los datos entre profesionales (arquitectura multi-tenant).

from django.db import models
from django.contrib.auth.models import User
from config.choices import Sexo
from pacientes.validators import (
    validate_dni,
    validate_telefono,
    validate_peso,
    validate_fecha_nacimiento_edad,
    validate_nombre_apellido,
    validate_talla,
)


class Paciente(models.Model):
    """
    Representa a una persona atendida por el nutricionista.
    El paciente NO tiene cuenta en el sistema; es un registro gestionado íntegramente
    por el profesional. El campo 'estado' permite soft-delete (inactivar sin borrar).
    """

    # FK al nutricionista que gestiona este paciente.
    # Garantiza que cada profesional solo vea sus propios pacientes (aislamiento multi-tenant).
    nutricionista = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="pacientes",
        verbose_name="Nutricionista",
    )

    # ─── Datos personales ────────────────────────────────────────────────────
    nombre = models.CharField(
        max_length=100,
        validators=[validate_nombre_apellido],
        verbose_name="Nombre",
    )
    apellido = models.CharField(
        max_length=100,
        validators=[validate_nombre_apellido],
        verbose_name="Apellido",
    )
    dni = models.CharField(
        max_length=8,
        validators=[validate_dni],
        verbose_name="DNI",
    )
    fecha_nacimiento = models.DateField(
        validators=[validate_fecha_nacimiento_edad],
        verbose_name="Fecha de nacimiento",
    )
    sexo = models.CharField(
        max_length=1,
        choices=Sexo.CHOICES,
        verbose_name="Sexo",
    )
    ocupacion = models.CharField(max_length=100, blank=True, verbose_name="Ocupación")
    peso = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[validate_peso],
        verbose_name="Peso (kg)",
        help_text="Peso inicial o de referencia del paciente",
    )
    talla = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[validate_talla],
        null=True,
        blank=True,
        verbose_name="Talla (cm)",
        help_text="Estatura inicial o de referencia del paciente",
    )

    # ─── Contacto ────────────────────────────────────────────────────────────
    telefono = models.CharField(
        max_length=20,
        validators=[validate_telefono],
        verbose_name="Teléfono",
    )
    email = models.EmailField(blank=True, verbose_name="Email")
    direccion = models.TextField(blank=True, verbose_name="Dirección")

    # ─── Información de salud ────────────────────────────────────────────────
    condiciones_medicas = models.TextField(
        blank=True,
        verbose_name="Condiciones médicas",
        help_text="Ej: Diabetes tipo 2, hipertensión, hipotiroidismo",
    )
    alergias = models.TextField(
        blank=True,
        verbose_name="Alergias",
        help_text="Ej: Maní, lácteos, gluten, mariscos",
    )
    notas_generales = models.TextField(
        blank=True,
        verbose_name="Notas generales",
        help_text="Observaciones adicionales relevantes para el nutricionista",
    )

    # ─── Control ─────────────────────────────────────────────────────────────
    # Soft-delete: inactivar en lugar de borrar. Preserva el historial del paciente.
    estado = models.BooleanField(
        default=True,
        verbose_name="Activo",
        help_text="Desmarcar para inactivar al paciente sin borrar sus datos",
    )
    fecha_registro = models.DateTimeField(
        auto_now_add=True, verbose_name="Fecha de registro"
    )
    fecha_actualizacion = models.DateTimeField(
        auto_now=True, verbose_name="Última actualización"
    )

    class Meta:
        ordering = ["-fecha_registro"]
        verbose_name = "Paciente"
        verbose_name_plural = "Pacientes"
        unique_together = [["nutricionista", "dni"]]
        # Índices para acelerar las búsquedas más frecuentes:
        # - nombre/apellido: búsqueda de pacientes por nombre
        # - telefono: búsqueda por teléfono (común en consultorios)
        indexes = [
            models.Index(fields=["nombre", "apellido"]),
            models.Index(fields=["telefono"]),
        ]

    def save(self, *args, **kwargs):
        # Forzar validaciones completas antes de persistir en base de datos
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nombre} {self.apellido}"

    @property
    def nombre_completo(self):
        """Nombre completo del paciente para uso en templates y reportes."""
        return f"{self.nombre} {self.apellido}"

    @property
    def esta_activo(self):
        """Devuelve True si el paciente está activo."""
        return self.estado

    @property
    def edad(self):
        """Calcula la edad actual del paciente en base a su fecha de nacimiento."""
        if self.fecha_nacimiento:
            from datetime import date

            hoy = date.today()
            cumplio_este_ano = (hoy.month, hoy.day) >= (self.fecha_nacimiento.month, self.fecha_nacimiento.day)
            return hoy.year - self.fecha_nacimiento.year - (0 if cumplio_este_ano else 1)
        return None

    @property
    def imc_inicial(self):
        """Calcula dinámicamente el IMC inicial en base al peso y talla de registro."""
        if self.peso and self.talla and self.talla > 0:
            talla_m = self.talla / 100
            return round(self.peso / (talla_m ** 2), 1)
        return None
