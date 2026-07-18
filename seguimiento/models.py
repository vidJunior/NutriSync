# seguimiento/models.py
# Medidas corporales y notas clínicas.

from django.db import models
from decimal import Decimal, ROUND_HALF_UP
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from config.choices import TipoNota
from django.contrib.auth.models import User
from core.validation import validate_uploaded_file


class MedidaCorporal(models.Model):
    """
    Registro de medidas corporales de un paciente.
    El IMC se calcula automáticamente en save() usando la fórmula OMS:
    peso(kg) / talla(m)². Se almacena en BD para evitar recalcular en cada consulta
    y permitir ordenamiento/histórico eficiente.
    """

    paciente = models.ForeignKey(
        "pacientes.Paciente",
        on_delete=models.CASCADE,
        related_name="medidas",
        verbose_name="Paciente",
    )
    consulta = models.ForeignKey(
        "pacientes.Consulta",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="medidas_corporales",
        verbose_name="Consulta",
    )
    fecha = models.DateField(verbose_name="Fecha de medición")
    peso_kg = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(1), MaxValueValidator(500)],
        verbose_name="Peso (kg)",
    )
    talla_cm = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        validators=[MinValueValidator(50), MaxValueValidator(250)],
        verbose_name="Talla (cm)",
    )
    imc = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        editable=False,
        verbose_name="IMC",
        help_text="Calculado automáticamente: peso / (talla en m)²",
    )
    grasa_corporal_pct = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="Grasa corporal (%)",
    )
    cintura_cm = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(20), MaxValueValidator(200)],
        verbose_name="Cintura (cm)",
    )
    cadera_cm = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(20), MaxValueValidator(200)],
        verbose_name="Cadera (cm)",
    )
    # Nuevos campos solicitados
    peso_objetivo_kg = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(500)],
        verbose_name="Peso objetivo (kg)",
    )
    cuello_cm = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(10), MaxValueValidator(150)],
        verbose_name="Cuello (cm)",
    )
    pecho_cm = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(20), MaxValueValidator(250)],
        verbose_name="Pecho (cm)",
    )
    brazo_cm = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(5), MaxValueValidator(100)],
        verbose_name="Brazo (cm)",
    )
    muslo_cm = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(10), MaxValueValidator(150)],
        verbose_name="Muslo (cm)",
    )
    pantorrilla_cm = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(10), MaxValueValidator(100)],
        verbose_name="Pantorrilla (cm)",
    )
    masa_grasa_kg = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(500)],
        verbose_name="Masa grasa (kg)",
    )
    masa_muscular_kg = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(500)],
        verbose_name="Masa muscular (kg)",
    )
    masa_muscular_pct = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="% masa muscular",
    )
    agua_corporal_pct = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="Agua corporal (%)",
    )
    grasa_visceral = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(60)],
        verbose_name="Grasa visceral",
    )
    masa_osea_kg = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(50)],
        verbose_name="Masa ósea (kg)",
    )
    tmb = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(100), MaxValueValidator(10000)],
        verbose_name="Tasa metabólica basal (TMB)",
    )
    notas = models.TextField(blank=True, verbose_name="Notas")
    fecha_registro = models.DateTimeField(
        auto_now_add=True, verbose_name="Fecha de registro"
    )

    class Meta:
        verbose_name = "Medida Corporal"
        verbose_name_plural = "Medidas Corporales"
        ordering = ["-fecha", "-fecha_registro"]
        # Índice por paciente y fecha.
        indexes = [
            models.Index(fields=["paciente", "fecha"]),
        ]

    def __str__(self):
        return f"{self.paciente} — {self.fecha}: {self.peso_kg} kg (IMC: {self.imc})"

    def save(self, *args, **kwargs):
        from datetime import date
        if not self.fecha:
            self.fecha = date.today()
        # Fórmula estándar OMS: IMC = peso(kg) / (talla(m))²
        # Calcula el IMC al guardar.
        if self.peso_kg is not None and self.talla_cm is not None and self.talla_cm > 0:
            talla_m = Decimal(self.talla_cm) / Decimal("100")
            self.imc = (Decimal(self.peso_kg) / (talla_m**2)).quantize(
                Decimal("0.1"),
                rounding=ROUND_HALF_UP,
            )
        self.full_clean()
        super().save(*args, **kwargs)

        # Sincroniza peso y talla de referencia.
        paciente = self.paciente
        need_save = False

        if self.talla_cm and paciente.talla != self.talla_cm:
            paciente.talla = self.talla_cm
            need_save = True

        if self.peso_kg and paciente.peso != self.peso_kg:
            paciente.peso = self.peso_kg
            need_save = True

        if need_save:
            paciente.save()

    def clean(self):
        super().clean()
        errors = {}
        if self.fecha and self.fecha > timezone.localdate():
            errors["fecha"] = "La fecha de medición no puede ser futura."
        if (
            self.consulta_id
            and self.paciente_id
            and self.consulta.paciente_id != self.paciente_id
        ):
            errors["consulta"] = "La consulta no pertenece al paciente."
        if errors:
            raise ValidationError(errors)


class NotaClinica(models.Model):
    """
    Nota clínica asociada a un paciente.
    Puede vincularse opcionalmente a una cita específica (cuando se escribe
    durante o después de la consulta). El tipo clasifica la naturaleza de la nota.
    """

    paciente = models.ForeignKey(
        "pacientes.Paciente",
        on_delete=models.CASCADE,
        related_name="notas_clinicas",
        verbose_name="Paciente",
    )
    consulta = models.ForeignKey(
        "pacientes.Consulta",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notas_clinicas_consulta",
        verbose_name="Consulta",
    )
    cita = models.ForeignKey(
        "agendas.Cita",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notas",
        verbose_name="Cita relacionada",
    )
    fecha = models.DateField(verbose_name="Fecha")
    titulo = models.CharField(max_length=200, verbose_name="Título")
    motivo_consulta = models.TextField(blank=True, verbose_name="Motivo de la consulta")
    resumen_consulta = models.TextField(blank=True, verbose_name="Resumen de la consulta")
    objetivos_acordados = models.TextField(blank=True, verbose_name="Objetivos acordados")
    plan_accion = models.TextField(blank=True, verbose_name="Plan de acción / Acuerdos")
    observaciones_clinicas = models.TextField(blank=True, verbose_name="Observaciones clínicas")
    tipo = models.CharField(
        max_length=20,
        choices=TipoNota.CHOICES,
        default=TipoNota.CONSULTA,
        verbose_name="Tipo",
    )
    fecha_creacion = models.DateTimeField(
        auto_now_add=True, verbose_name="Fecha de creación"
    )

    class Meta:
        verbose_name = "Nota Clínica"
        verbose_name_plural = "Notas Clínicas"
        ordering = ["-fecha", "-fecha_creacion"]
        # Índice por paciente y tipo.
        indexes = [
            models.Index(fields=["paciente", "tipo"]),
        ]

    def __str__(self):
        return f"{self.titulo} — {self.paciente} ({self.get_tipo_display()})"

    def clean(self):
        super().clean()
        errors = {}
        if self.fecha and self.fecha > timezone.localdate():
            errors["fecha"] = "La fecha de la nota no puede ser futura."
        if self.cita_id and self.paciente_id and self.cita.paciente_id != self.paciente_id:
            errors["cita"] = "La cita no pertenece al paciente."
        if (
            self.consulta_id
            and self.paciente_id
            and self.consulta.paciente_id != self.paciente_id
        ):
            errors["consulta"] = "La consulta no pertenece al paciente."
        contenido = (
            self.motivo_consulta,
            self.resumen_consulta,
            self.objetivos_acordados,
            self.plan_accion,
            self.observaciones_clinicas,
        )
        if not any((valor or "").strip() for valor in contenido):
            errors["resumen_consulta"] = (
                "La nota debe incluir al menos un contenido clínico."
            )
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class Recomendacion(models.Model):
    """
    Recomendación e indicaciones clínicas entregadas al paciente durante una consulta.
    Cada registro está asociado a una categoría (hidratación, actividad física, etc.),
    vinculado a un paciente, una cita (consulta) y el nutricionista responsable.
    """

    paciente = models.ForeignKey(
        "pacientes.Paciente",
        on_delete=models.CASCADE,
        related_name="recomendaciones",
        verbose_name="Paciente",
    )
    consulta = models.ForeignKey(
        "pacientes.Consulta",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recomendaciones_consulta",
        verbose_name="Consulta",
    )
    cita = models.ForeignKey(
        "agendas.Cita",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recomendaciones",
        verbose_name="Consulta / Cita",
    )
    nutricionista = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="recomendaciones_creadas",
        verbose_name="Profesional responsable",
    )
    categoria = models.CharField(
        max_length=50,
        verbose_name="Categoría",
    )  # e.g. 'hidratacion', 'actividad_fisica', 'alimentos_recomendados', 'alimentos_limitar', 'generales'

    descripcion = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Descripción/Detalles",
    )

    fecha = models.DateField(
        verbose_name="Fecha de recomendación",
    )

    ESTADOS_CUMPLIMIENTO = [
        ("pendiente", "Pendiente"),
        ("cumplida", "Cumplida"),
        ("parcial", "Parcialmente cumplida"),
        ("no_cumplida", "No cumplida"),
    ]
    estado_cumplimiento = models.CharField(
        max_length=20,
        choices=ESTADOS_CUMPLIMIENTO,
        default="pendiente",
        verbose_name="Estado de Cumplimiento",
    )

    fecha_registro = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de registro",
    )

    class Meta:
        verbose_name = "Recomendación"
        verbose_name_plural = "Recomendaciones"
        ordering = ["-fecha", "-fecha_registro"]

    def __str__(self):
        return f"{self.paciente} — {self.categoria} ({self.fecha})"

    CATEGORIAS_VALIDAS = {
        "hidratacion",
        "actividad_fisica",
        "alimentos_recomendados",
        "alimentos_limitar",
        "generales",
    }

    def clean(self):
        super().clean()
        errors = {}
        if self.categoria not in self.CATEGORIAS_VALIDAS:
            errors["categoria"] = "La categoría de recomendación no es válida."
        if not isinstance(self.descripcion, dict):
            errors["descripcion"] = "La descripción debe ser un objeto estructurado."
        if self.fecha and self.fecha > timezone.localdate():
            errors["fecha"] = "La fecha de recomendación no puede ser futura."
        if (
            self.consulta_id
            and self.paciente_id
            and self.consulta.paciente_id != self.paciente_id
        ):
            errors["consulta"] = "La consulta no pertenece al paciente."
        if self.cita_id and self.paciente_id and self.cita.paciente_id != self.paciente_id:
            errors["cita"] = "La cita no pertenece al paciente."
        if (
            self.nutricionista_id
            and self.paciente_id
            and self.paciente.nutricionista_id != self.nutricionista_id
        ):
            errors["nutricionista"] = "El profesional no corresponde al paciente."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class Entregable(models.Model):
    """
    Entregable y recurso compartido con el paciente desde la plataforma.
    Puede representar planes alimentarios, recomendaciones, reportes clínicos,
    material educativo en PDF/videos, listas de compras o resúmenes de consultas.
    """

    TIPOS = [
        ("plan_alimentario", "Plan Alimentario"),
        ("recomendaciones", "Recomendaciones"),
        ("reporte", "Reporte de Evolución"),
        ("material_educativo", "Material Educativo"),
        ("lista_compras", "Lista de Compras"),
        ("resumen_consulta", "Resumen de Consulta"),
    ]
    ESTADOS = [
        ("borrador", "Borrador"),
        ("publicado", "Publicado"),
        ("archivado", "Archivado"),
    ]

    paciente = models.ForeignKey(
        "pacientes.Paciente",
        on_delete=models.CASCADE,
        related_name="entregables",
        verbose_name="Paciente",
    )
    consulta = models.ForeignKey(
        "pacientes.Consulta",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="entregables_consulta",
        verbose_name="Consulta",
    )
    cita = models.ForeignKey(
        "agendas.Cita",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="entregables",
        verbose_name="Consulta / Cita",
    )
    nutricionista = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="entregables_creados",
        verbose_name="Profesional responsable",
    )

    tipo = models.CharField(
        max_length=50,
        choices=TIPOS,
        verbose_name="Tipo",
    )
    titulo = models.CharField(
        max_length=200,
        verbose_name="Título",
    )
    descripcion = models.TextField(
        blank=True,
        verbose_name="Descripción",
    )
    fecha_publicacion = models.DateField(
        verbose_name="Fecha de publicación",
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default="borrador",
        verbose_name="Estado",
    )

    archivo = models.FileField(
        upload_to="entregables/",
        null=True,
        blank=True,
        verbose_name="Archivo o recurso asociado",
    )

    recurso_asociado = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Metadatos de recurso asociado",
    )

    fecha_registro = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de registro",
    )

    class Meta:
        verbose_name = "Entregable"
        verbose_name_plural = "Entregables"
        ordering = ["-fecha_publicacion", "-fecha_registro"]

    def __str__(self):
        return f"{self.titulo} ({self.get_tipo_display()}) — {self.paciente}"

    def clean(self):
        super().clean()
        errors = {}
        if (
            self.consulta_id
            and self.paciente_id
            and self.consulta.paciente_id != self.paciente_id
        ):
            errors["consulta"] = "La consulta no pertenece al paciente."
        if self.cita_id and self.paciente_id and self.cita.paciente_id != self.paciente_id:
            errors["cita"] = "La cita no pertenece al paciente."
        if (
            self.nutricionista_id
            and self.paciente_id
            and self.paciente.nutricionista_id != self.nutricionista_id
        ):
            errors["nutricionista"] = "El profesional no corresponde al paciente."
        if self.archivo and hasattr(self.archivo, "content_type"):
            try:
                validate_uploaded_file(self.archivo)
            except ValidationError as exc:
                errors["archivo"] = exc.messages
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
