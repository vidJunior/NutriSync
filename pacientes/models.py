# pacientes/models.py
# Modelo Paciente — ficha clínica de la persona atendida por el nutricionista.
# El FK nutricionista aísla los datos entre profesionales (arquitectura multi-tenant).

from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
import random
import string
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

    # Relación opcional con el User que representa la cuenta móvil del Paciente.
    usuario = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="paciente_perfil",
        verbose_name="Usuario de Acceso Móvil",
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
        # ─── Sincronización de Objetivo de Tratamiento ───
        def get_motivo_from_notas(notas):
            if notas and "Motivo de Consulta:" in notas:
                parts = notas.split("Motivo de Consulta:")
                if len(parts) > 1:
                    return parts[1].split("\nObservaciones Iniciales:\n")[0].strip()
            return None

        # Valores actuales en memoria
        current_in_eval = self.evaluacion.get("objetivo_principal") if self.evaluacion else None
        current_in_info = self.informacion_clinica.get("objetivo_principal") if self.informacion_clinica else None
        current_in_notas = get_motivo_from_notas(self.notas_generales)

        # Buscar el valor antiguo de la base de datos para ver cuál cambió
        db_obj = None
        if self.pk:
            try:
                db_obj = Paciente.objects.get(pk=self.pk)
            except Paciente.DoesNotExist:
                pass

        nuevo_objetivo = None
        if db_obj:
            old_in_eval = db_obj.evaluacion.get("objetivo_principal") if db_obj.evaluacion else None
            old_in_info = db_obj.informacion_clinica.get("objetivo_principal") if db_obj.informacion_clinica else None
            old_in_notas = get_motivo_from_notas(db_obj.notas_generales)

            if current_in_eval != old_in_eval:
                nuevo_objetivo = current_in_eval
            elif current_in_info != old_in_info:
                nuevo_objetivo = current_in_info
            elif current_in_notas != old_in_notas:
                nuevo_objetivo = current_in_notas
        
        # Si es un paciente nuevo o no se detectó cambio diferencial, usar el primero no nulo
        if not nuevo_objetivo:
            nuevo_objetivo = current_in_eval or current_in_info or current_in_notas or "Pérdida de peso"

        # Sincronizar todos al valor ganador
        if self.evaluacion is None:
            self.evaluacion = {}
        self.evaluacion["objetivo_principal"] = nuevo_objetivo

        if self.informacion_clinica is None:
            self.informacion_clinica = {}
        self.informacion_clinica["objetivo_principal"] = nuevo_objetivo

        observaciones = ""
        if self.notas_generales and "Observaciones Iniciales:\n" in self.notas_generales:
            parts = self.notas_generales.split("Observaciones Iniciales:\n")
            if len(parts) > 1:
                observaciones = parts[1].strip()
        self.notas_generales = f"Motivo de Consulta: {nuevo_objetivo}\nObservaciones Iniciales:\n{observaciones}"

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


class Consulta(models.Model):
    paciente = models.ForeignKey(
        "Paciente",
        on_delete=models.CASCADE,
        related_name="consultas",
        verbose_name="Paciente",
    )
    numero_consulta = models.PositiveIntegerField(
        verbose_name="Número de consulta",
    )
    
    TIPOS = [
        ("primera_consulta", "Primera consulta"),
        ("seguimiento", "Seguimiento"),
        ("reevaluacion", "Reevaluación"),
        ("control", "Control"),
        ("deportiva", "Consulta deportiva"),
        ("clinica", "Consulta clínica"),
        ("otro", "Otro"),
    ]
    tipo = models.CharField(
        max_length=50,
        choices=TIPOS,
        default="seguimiento",
        verbose_name="Tipo de consulta",
    )
    
    fecha = models.DateField(
        default=timezone.now,
        verbose_name="Fecha",
    )
    hora_inicio = models.TimeField(
        default=timezone.now,
        verbose_name="Hora de inicio",
    )
    hora_fin = models.TimeField(
        null=True,
        blank=True,
        verbose_name="Hora de fin",
    )
    
    ESTADOS = [
        ("en_curso", "En curso"),
        ("finalizada", "Finalizada"),
        ("cancelada", "Cancelada"),
    ]
    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default="en_curso",
        verbose_name="Estado",
    )
    
    profesional = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="consultas_atendidas",
        verbose_name="Nutricionista",
    )
    cita = models.ForeignKey(
        "agendas.Cita",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="consultas",
        verbose_name="Cita originaria",
    )
    consulta_anterior = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="consultas_siguientes",
        verbose_name="Consulta anterior",
    )
    observaciones = models.TextField(
        blank=True,
        verbose_name="Observaciones de la consulta",
    )
    
    informacion_clinica = models.JSONField(
        default=dict,
        blank=True,
        null=True,
        verbose_name="Información Clínica de la Consulta",
    )
    evaluacion = models.JSONField(
        default=dict,
        blank=True,
        null=True,
        verbose_name="Evaluación y Diagnóstico de la Consulta",
    )
    seguimiento = models.JSONField(
        default=dict,
        blank=True,
        null=True,
        verbose_name="Seguimiento de la Consulta",
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Consulta"
        verbose_name_plural = "Consultas"
        ordering = ["paciente", "numero_consulta"]
        unique_together = ("paciente", "numero_consulta")

    def __str__(self):
        return f"Consulta #{self.numero_consulta} ({self.tipo}) — {self.paciente}"


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
    consulta = models.ForeignKey(
        'Consulta',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='planes_alimentarios'
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

    version = models.PositiveIntegerField(default=1, verbose_name="Versión")
    plan_anterior = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='versiones_posteriores',
        verbose_name="Plan anterior/origen"
    )

    class Meta:
        ordering = ['-fecha_creacion', '-version']
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
    consulta = models.ForeignKey(
        'Consulta',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='archivos',
        verbose_name="Consulta"
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


class CodigoVinculacion(models.Model):
    """
    Código temporal generado por el nutricionista para vincular
    el expediente de un Paciente con un usuario de Django (User) en la app móvil.
    """
    paciente = models.OneToOneField(
        Paciente,
        on_delete=models.CASCADE,
        related_name="codigo_vinculacion",
        verbose_name="Paciente",
    )
    codigo = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="Código de Vinculación",
    )
    creado_en = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Creado en",
    )
    expira_en = models.DateTimeField(
        verbose_name="Expira en",
    )
    utilizado = models.BooleanField(
        default=False,
        verbose_name="Utilizado",
    )

    class Meta:
        verbose_name = "Código de Vinculación"
        verbose_name_plural = "Códigos de Vinculación"

    def __str__(self):
        return f"{self.codigo} — {self.paciente.nombre_completo} ({'Utilizado' if self.utilizado else 'Activo'})"

    def esta_valido(self):
        """Verifica si el código es vigente y no ha sido utilizado y el paciente está activo."""
        return not self.utilizado and self.expira_en > timezone.now() and self.paciente.esta_activo

    def save(self, *args, **kwargs):
        if not self.codigo:
            # Generar código de vinculación de 6 caracteres alfanuméricos
            caracteres = string.ascii_uppercase + string.digits
            while True:
                nuevo_codigo = "".join(random.choices(caracteres, k=6))
                if not CodigoVinculacion.objects.filter(codigo=nuevo_codigo).exists():
                    self.codigo = nuevo_codigo
                    break
        if not self.expira_en:
            # Expira por defecto en 24 horas
            self.expira_en = timezone.now() + timezone.timedelta(hours=24)
        super().save(*args, **kwargs)

