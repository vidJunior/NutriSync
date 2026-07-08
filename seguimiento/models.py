# seguimiento/models.py
# Modelos de MedidaCorporal y NotaClinica para el seguimiento de pacientes.
# MedidaCorporal registra datos antropométricos con IMC calculado automáticamente.
# NotaClinica almacena apuntes del nutricionista vinculados opcionalmente a una cita.

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from config.choices import TipoNota


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
        # Índice compuesto para búsquedas frecuentes por paciente + fecha
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
        # Se calcula en save() en lugar de en cada request para consistencia de datos
        if self.peso_kg is not None and self.talla_cm is not None and self.talla_cm > 0:
            talla_m = self.talla_cm / 100
            self.imc = round(self.peso_kg / (talla_m**2), 1)
        super().save(*args, **kwargs)

        # Sincronización inteligente de base de datos con el peso y la talla de referencia del paciente
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
    cita = models.ForeignKey(
        "citas.Cita",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notas",
        verbose_name="Cita relacionada",
    )
    fecha = models.DateField(verbose_name="Fecha")
    titulo = models.CharField(max_length=200, verbose_name="Título")
    contenido = models.TextField(verbose_name="Contenido")
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
        # Índice compuesto para búsquedas frecuentes por paciente + tipo
        indexes = [
            models.Index(fields=["paciente", "tipo"]),
        ]

    def __str__(self):
        return f"{self.titulo} — {self.paciente} ({self.get_tipo_display()})"
