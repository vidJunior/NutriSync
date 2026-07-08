# pacientes/models.py
# Modelo Paciente — ficha clínica de la persona atendida por el nutricionista.
# El FK nutricionista aísla los datos entre profesionales (arquitectura multi-tenant).

from django.db import models
from django.utils import timezone
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

    edad = models.IntegerField(null=True, blank=True, verbose_name="Edad")
    imc_inicial = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
        verbose_name="IMC Inicial",
    )
    imc_clasificacion = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="Clasificación IMC",
    )
    informacion_clinica = models.JSONField(
        default=dict,
        blank=True,
        null=True,
        verbose_name="Información Clínica y Hábitos",
    )
    evaluacion = models.JSONField(
        default=dict,
        blank=True,
        null=True,
        verbose_name="Evaluación Nutricional",
    )
    seguimiento = models.JSONField(
        default=dict,
        blank=True,
        null=True,
        verbose_name="Seguimiento Nutricional",
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
        # Calcular edad
        if self.fecha_nacimiento:
            from datetime import date
            fecha_nac = self.fecha_nacimiento
            if isinstance(fecha_nac, str):
                from django.utils.dateparse import parse_date
                fecha_nac = parse_date(fecha_nac)
            if fecha_nac:
                hoy = date.today()
                cumplio_este_ano = (hoy.month, hoy.day) >= (fecha_nac.month, fecha_nac.day)
                self.edad = hoy.year - fecha_nac.year - (0 if cumplio_este_ano else 1)
            else:
                self.edad = None
        else:
            self.edad = None

        # Calcular IMC inicial
        if self.peso and self.talla and self.talla > 0:
            from decimal import Decimal
            talla_m = Decimal(str(self.talla)) / 100
            val_imc = Decimal(str(self.peso)) / (talla_m ** 2)
            self.imc_inicial = val_imc.quantize(Decimal('0.1'))
        else:
            self.imc_inicial = None

        # Calcular Clasificación IMC
        if self.imc_inicial is not None:
            if self.imc_inicial < 18.5:
                self.imc_clasificacion = "Bajo peso"
            elif self.imc_inicial < 25.0:
                self.imc_clasificacion = "Normal"
            elif self.imc_inicial < 30.0:
                self.imc_clasificacion = "Sobrepeso"
            elif self.imc_inicial < 35.0:
                self.imc_clasificacion = "Obesidad I"
            elif self.imc_inicial < 40.0:
                self.imc_clasificacion = "Obesidad II"
            else:
                self.imc_clasificacion = "Obesidad III"
        else:
            self.imc_clasificacion = None

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


class PlanAlimentario(models.Model):
    ESTADOS = [
        ('Borrador', 'Borrador'),
        ('Activo', 'Activo'),
        ('Finalizado', 'Finalizado'),
        ('Suspendido', 'Suspendido'),
    ]

    paciente = models.ForeignKey(
        'Paciente',
        on_delete=models.CASCADE,
        related_name='planes_alimentarios_sync'
    )
    nombre = models.CharField(max_length=200, default="Plan Alimentario Basal")
    tipo_plan = models.CharField(max_length=100, default="Estándar")
    calorias = models.PositiveIntegerField(default=2000)
    proteinas = models.PositiveIntegerField(default=150) # grams
    carbohidratos = models.PositiveIntegerField(default=200) # grams
    grasas = models.PositiveIntegerField(default=65) # grams
    fibra = models.PositiveIntegerField(default=25) # grams
    agua_recomendada = models.DecimalField(max_digits=3, decimal_places=1, default=2.5) # liters
    estado = models.CharField(max_length=20, choices=ESTADOS, default='Borrador')
    fecha_inicio = models.DateField(default=timezone.now)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    enviado_al_paciente = models.BooleanField(default=False)
    fecha_envio = models.DateTimeField(null=True, blank=True)
    
    # JSON fields for sections
    comidas = models.JSONField(default=list, blank=True)
    sustituciones = models.JSONField(default=list, blank=True)
    recomendaciones = models.JSONField(default=list, blank=True)
    suplementacion = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['-fecha_creacion']
        verbose_name = "Plan Alimentario Sync"
        verbose_name_plural = "Planes Alimentarios Sync"

    def __str__(self):
        return f"{self.nombre} — {self.paciente.nombre_completo} ({self.estado})"


class ArchivoPaciente(models.Model):
    CATEGORIAS = [
        ('Documentos', 'Documentos'),
        ('Laboratorios', 'Laboratorios'),
        ('Fotos de Progreso', 'Fotos de Progreso'),
        ('Informes', 'Informes'),
        ('Otros', 'Otros'),
    ]

    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.CASCADE,
        related_name='archivos',
        verbose_name="Paciente"
    )
    nutricionista = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='archivos_subidos',
        verbose_name="Profesional Responsable"
    )
    nombre = models.CharField(max_length=255, verbose_name="Nombre del Archivo")
    archivo = models.FileField(upload_to="pacientes/archivos/", verbose_name="Archivo")
    categoria = models.CharField(max_length=50, choices=CATEGORIAS, verbose_name="Categoría")
    subcategoria = models.CharField(max_length=100, blank=True, verbose_name="Subcategoría")
    observaciones = models.TextField(blank=True, verbose_name="Observaciones")
    fecha_registro = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Carga")

    class Meta:
        ordering = ['-fecha_registro']
        verbose_name = "Archivo de Paciente"
        verbose_name_plural = "Archivos de Pacientes"

    def __str__(self):
        return f"{self.nombre} ({self.categoria}) — {self.paciente.nombre_completo}"

