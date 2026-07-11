# nutricion/models.py
# Modelos del módulo de Planes Nutricionales y Base de Alimentos.
# Estructura: Alimento (catálogo) → ComidaPlan (ManyToMany) → PlanNutricional (asignado a paciente).

from django.db import models
from django.core.validators import MinValueValidator
from django.contrib.auth.models import User
from pacientes.models import Paciente
from config.choices import DiaSemana, TipoComida, Objetivo
from .validators import validate_tiempo_preparacion, validate_porciones, validate_cantidad_ingrediente



# ─── Categorías de alimentos ─────────────────────────────────────────────────

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


# ─── Alimento ─────────────────────────────────────────────────────────────────

class Alimento(models.Model):
    """
    Base de datos de alimentos con información nutricional por 100g.
    Sirve como catálogo compartido para todos los planes nutricionales.
    El campo 'estado' permite dar de baja un alimento sin borrarlo (soft-delete).
    """

    nombre = models.CharField(
        max_length=150,
        verbose_name="Nombre del alimento",
        db_index=True,  # Índice para acelerar búsquedas por nombre (operación frecuente)
    )
    categoria = models.CharField(
        max_length=20,
        choices=CategoriaAlimento.choices,
        default=CategoriaAlimento.OTROS,
        verbose_name="Categoría",
        db_index=True,  # Índice para filtrado por categoría en el catálogo
    )

    # ─── Información nutricional por 100g ────────────────────────────────────
    # Valores por 100g como convención estándar nutricional (facilita comparaciones)
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

    # Soft-delete: baja el alimento del catálogo activo sin eliminarlo
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
            # Búsqueda combinada nombre + categoría: operación más frecuente en el catálogo
            models.Index(fields=["nombre", "categoria"]),
        ]

    def __str__(self):
        return f"{self.nombre} ({self.get_categoria_display()})"


# ─── PlanNutricional ──────────────────────────────────────────────────────────

class PlanNutricional(models.Model):
    """
    Plan de alimentación asignado a un paciente por el nutricionista.
    Un paciente puede tener múltiples planes (histórico) pero solo uno activo.
    La regla 'un solo plan activo' se valida en el formulario y en la vista.
    """

    # FK a Paciente (que ya tiene FK a nutricionista): aislamiento de datos en cascada.
    # Al filtrar por paciente__nutricionista=request.user, se garantiza el aislamiento.
    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.CASCADE,
        related_name="planes",
        verbose_name="Paciente",
    )
    nombre = models.CharField(
        max_length=200,
        verbose_name="Nombre del plan",
        help_text="Ej: Plan de pérdida de peso - Enero 2025",
    )
    fecha_inicio = models.DateField(verbose_name="Fecha de inicio")
    fecha_fin = models.DateField(
        blank=True,
        null=True,
        verbose_name="Fecha de fin",
        help_text="Dejar en blanco si el plan no tiene fecha de término definida",
    )
    objetivo = models.CharField(
        max_length=30,
        choices=Objetivo.CHOICES,
        verbose_name="Objetivo",
    )

    # ─── Macros objetivo diario ──────────────────────────────────────────────
    # Se registran como meta diaria para que el nutricionista pueda hacer seguimiento
    calorias_diarias = models.PositiveIntegerField(
        default=2000,
        verbose_name="Calorías diarias (kcal)",
        validators=[MinValueValidator(500)],
    )
    proteinas_g = models.DecimalField(
        max_digits=6,
        decimal_places=1,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Proteínas diarias (g)",
    )
    carbohidratos_g = models.DecimalField(
        max_digits=6,
        decimal_places=1,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Carbohidratos diarios (g)",
    )
    grasas_g = models.DecimalField(
        max_digits=6,
        decimal_places=1,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Grasas diarias (g)",
    )

    observaciones = models.TextField(blank=True, verbose_name="Observaciones")

    # Soft-delete: un plan inactivo se conserva en el historial
    estado = models.BooleanField(
        default=True,
        verbose_name="Activo",
        help_text="Solo puede haber un plan activo por paciente",
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")

    class Meta:
        ordering = ["-fecha_creacion"]
        verbose_name = "Plan Nutricional"
        verbose_name_plural = "Planes Nutricionales"
        indexes = [
            # Búsqueda de planes activos de un paciente: operación más frecuente
            models.Index(fields=["paciente", "estado"]),
            models.Index(fields=["fecha_inicio"]),
        ]

    def __str__(self):
        return f"{self.nombre} — {self.paciente.nombre_completo}"

    @property
    def duracion_dias(self):
        """Calcula la duración del plan en días si tiene fecha de fin definida."""
        if self.fecha_fin:
            return (self.fecha_fin - self.fecha_inicio).days
        return None

    @property
    def objetivo_display(self):
        """Devuelve el label del objetivo para uso en templates."""
        return dict(Objetivo.CHOICES).get(self.objetivo, self.objetivo)


# ─── ComidaPlan ──────────────────────────────────────────────────────────────

class ComidaPlan(models.Model):
    """
    Una comida específica dentro de un plan nutricional (ej: 'Lunes - Desayuno').
    Tiene ManyToMany con Alimento para sugerir alimentos concretos.
    Se agrupa por día_semana al mostrar el plan organizado lunes→domingo.
    """

    plan = models.ForeignKey(
        PlanNutricional,
        on_delete=models.CASCADE,
        related_name="comidas",
        verbose_name="Plan nutricional",
    )
    dia_semana = models.CharField(
        max_length=10,
        choices=DiaSemana.CHOICES,
        verbose_name="Día de la semana",
        db_index=True,  # Índice para agrupar comidas por día al mostrar el plan
    )
    tipo_comida = models.CharField(
        max_length=10,
        choices=TipoComida.CHOICES,
        verbose_name="Tipo de comida",
    )
    descripcion = models.TextField(
        blank=True,
        verbose_name="Descripción",
        help_text="Descripción libre de la comida para el paciente",
    )
    # ManyToMany con Alimento: sugiere alimentos del catálogo para esta comida.
    # Usamos through=None (tabla implícita) porque no se necesitan campos extra en la relación.
    alimentos_sugeridos = models.ManyToManyField(
        Alimento,
        blank=True,
        related_name="comidas_plan",
        verbose_name="Alimentos sugeridos",
    )
    recetas_sugeridas = models.ManyToManyField(
        "Receta",
        blank=True,
        related_name="comidas_plan",
        verbose_name="Recetas sugeridas",
    )
    calorias_estimadas = models.PositiveIntegerField(
        default=0,
        verbose_name="Calorías estimadas (kcal)",
    )

    class Meta:
        ordering = ["dia_semana", "tipo_comida"]
        verbose_name = "Comida del plan"
        verbose_name_plural = "Comidas del plan"
        # Un plan no debería tener la misma comida dos veces el mismo día
        unique_together = [["plan", "dia_semana", "tipo_comida"]]

    def __str__(self):
        return f"{self.get_dia_semana_display()} - {self.get_tipo_comida_display()} ({self.plan.nombre})"


# ─── Receta ───────────────────────────────────────────────────────────────────

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


# ─── IngredienteReceta ────────────────────────────────────────────────────────

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

