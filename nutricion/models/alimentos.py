from django.db import models
from django.core.validators import MinValueValidator

class CategoriaAlimento(models.TextChoices):
    """Categorías para organizar la base de alimentos del catálogo."""
    CEREALES = "cereales", "Cereales y granos"
    LACTEOS = "lacteos", "Lácteos"
    CARNES = "carnes", "Carnes y aves"
    PESCADOS = "pescados", "Pescados y mariscos"
    HUEVOS = "huevos", "Huevos"
    LEGUMBRES = "legumbres", "Legumbres"
    VERDURAS = "verduras", "Verduras y hortalizas"
    FRUTAS = "frutas", "Frutas"
    GRASAS = "grasas", "Grasas y aceites"
    BEBIDAS = "bebidas", "Bebidas"
    SNACKS = "snacks", "Snacks y aperitivos"
    OTROS = "otros", "Otros"


class Alimento(models.Model):
    """
    Base de datos de alimentos con información nutricional por 100g.
    Sirve como catálogo compartido para todos los planes nutricionales.
    El campo 'estado' permite dar de baja un alimento sin borrarlo (soft-delete).
    """
    nombre = models.CharField(
        max_length=150,
        verbose_name="Nombre del alimento",
        db_index=True,
    )
    categoria = models.CharField(
        max_length=20,
        choices=CategoriaAlimento.choices,
        default=CategoriaAlimento.OTROS,
        verbose_name="Categoría",
        db_index=True,
    )

    # Valores por 100 g
    calorias_100g = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Calorías (kcal/100g)",
        default=0,
    )
    proteinas_100g = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Proteínas (g/100g)",
        default=0,
    )
    carbohidratos_100g = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Carbohidratos (g/100g)",
        default=0,
    )
    grasas_100g = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Grasas (g/100g)",
        default=0,
    )
    fibra_100g = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Fibra (g/100g)",
        default=0,
    )

    porcion_referencia = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Porción de referencia",
        help_text="Ej: 1 taza (240ml), 1 unidad mediana (150g)",
    )

    estado = models.BooleanField(
        default=True,
        verbose_name="Activo",
        help_text="Desmarcar para dar de baja el alimento del catálogo",
    )
    fecha_registro = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de registro")

    class Meta:
        ordering = ["nombre"]
        verbose_name = "Alimento"
        verbose_name_plural = "Alimentos"
        indexes = [
            models.Index(fields=["nombre", "categoria"]),
        ]

    def __str__(self):
        return f"{self.nombre} ({self.get_categoria_display()})"
