from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from ..validators import validate_tiempo_preparacion, validate_porciones, validate_cantidad_ingrediente
from .alimentos import Alimento

class Receta(models.Model):
    """
    Receta culinaria creada por un nutricionista utilizando alimentos del catálogo.
    """
    nombre = models.CharField(
        max_length=150,
        verbose_name="Nombre de la receta",
        db_index=True,
    )
    descripcion = models.TextField(
        blank=True,
        verbose_name="Descripción",
    )
    instrucciones = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Instrucciones de preparación",
        help_text="Lista de pasos en formato JSON (ej: ['Paso 1', 'Paso 2'])",
    )
    tiempo_preparacion = models.PositiveIntegerField(
        default=15,
        validators=[validate_tiempo_preparacion],
        verbose_name="Tiempo de preparación (min)",
        help_text="Tiempo total estimado de preparación en minutos",
    )
    porciones = models.PositiveIntegerField(
        default=1,
        validators=[validate_porciones],
        verbose_name="Porciones",
        help_text="Número de porciones que rinde la receta",
    )
    creado_por = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="recetas",
        verbose_name="Creado por",
    )
    paciente = models.ForeignKey(
        "pacientes.Paciente",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="recetas_especificas",
        verbose_name="Paciente específico",
        help_text="Dejar en blanco si es una plantilla de receta global.",
    )
    es_sistema = models.BooleanField(
        default=False,
        verbose_name="Receta del sistema",
        help_text="Marcar si es una receta predeterminada y compartida para todos",
    )
    imagen_predeterminada = models.CharField(
        max_length=50,
        default="salad",
        verbose_name="Imagen predeterminada",
        help_text="Nombre de la ilustración a renderizar (ej: salad, soup, chicken, dessert)",
    )
    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de creación",
    )

    class Meta:
        ordering = ["nombre"]
        verbose_name = "Receta"
        verbose_name_plural = "Recetas"

    def __str__(self):
        return self.nombre

    def clean(self):
        super().clean()
        errors = {}
        if not isinstance(self.instrucciones, list):
            errors["instrucciones"] = "Las instrucciones deben ser una lista."
        else:
            if len(self.instrucciones) > 50:
                errors["instrucciones"] = "La receta no puede superar 50 pasos."
            elif any(
                not isinstance(step, str) or not step.strip() or len(step.strip()) > 1000
                for step in self.instrucciones
            ):
                errors["instrucciones"] = (
                    "Cada paso debe tener entre 1 y 1000 caracteres."
                )
        if (
            self.paciente_id
            and self.creado_por_id
            and self.paciente.nutricionista_id != self.creado_por_id
        ):
            errors["paciente"] = "El paciente no pertenece al profesional."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def calorias_totales(self):
        return sum(
            (ing.alimento.calorias_100g * ing.cantidad / 100)
            for ing in self.ingredientes.all()
        )

    @property
    def proteinas_totales(self):
        return sum(
            (ing.alimento.proteinas_100g * ing.cantidad / 100)
            for ing in self.ingredientes.all()
        )

    @property
    def carbohidratos_totales(self):
        return sum(
            (ing.alimento.carbohidratos_100g * ing.cantidad / 100)
            for ing in self.ingredientes.all()
        )

    @property
    def grasas_totales(self):
        return sum(
            (ing.alimento.grasas_100g * ing.cantidad / 100)
            for ing in self.ingredientes.all()
        )

    @property
    def fibra_totales(self):
        return sum(
            (ing.alimento.fibra_100g * ing.cantidad / 100)
            for ing in self.ingredientes.all()
        )

    @property
    def calorias_por_porcion(self):
        if self.porciones:
            return round(self.calorias_totales / self.porciones, 1)
        return 0

    @property
    def proteinas_por_porcion(self):
        if self.porciones:
            return round(self.proteinas_totales / self.porciones, 1)
        return 0

    @property
    def carbohidratos_por_porcion(self):
        if self.porciones:
            return round(self.carbohidratos_totales / self.porciones, 1)
        return 0

    @property
    def grasas_por_porcion(self):
        if self.porciones:
            return round(self.grasas_totales / self.porciones, 1)
        return 0

    @property
    def fibra_por_porcion(self):
        if self.porciones:
            return round(self.fibra_totales / self.porciones, 1)
        return 0


class IngredienteReceta(models.Model):
    """
    Relación de alimentos que componen una receta con sus cantidades específicas en gramos.
    """
    receta = models.ForeignKey(
        Receta,
        on_delete=models.CASCADE,
        related_name="ingredientes",
        verbose_name="Receta",
    )
    alimento = models.ForeignKey(
        Alimento,
        on_delete=models.CASCADE,
        related_name="ingredientes_recetas",
        verbose_name="Alimento",
    )
    cantidad = models.DecimalField(
        max_digits=6,
        decimal_places=1,
        validators=[validate_cantidad_ingrediente],
        verbose_name="Cantidad (g)",
        help_text="Cantidad exacta en gramos (g)",
    )
    nota = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Nota / Medida casera",
        help_text="Ej: 1 taza, picada en cubos, opcional",
    )

    class Meta:
        verbose_name = "Ingrediente de Receta"
        verbose_name_plural = "Ingredientes de Receta"
        unique_together = [["receta", "alimento"]]

    def __str__(self):
        return f"{self.cantidad}g de {self.alimento.nombre} en {self.receta.nombre}"

    def clean(self):
        super().clean()
        if self.alimento_id and not self.alimento.estado:
            raise ValidationError(
                {"alimento": "No se puede usar un alimento inactivo."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
