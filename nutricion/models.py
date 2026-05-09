from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal
from config.choices import (
    TipoComida,
    NivelActividad,
    Objetivo,
    TipoEjercicio,
    Sexo,
)
from .validators import validar_cantidad_positiva
from .querysets import RegistroQuerySet
from alimentos.models import Alimento


class PerfilUsuario(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name="perfil")
    peso_kg = models.DecimalField(
        max_digits=5, decimal_places=2, validators=[validar_cantidad_positiva]
    )
    talla_cm = models.IntegerField(validators=[validar_cantidad_positiva])
    edad = models.IntegerField(validators=[validar_cantidad_positiva])
    sexo = models.CharField(max_length=1, choices=Sexo.choices)
    nivel_actividad = models.CharField(max_length=2, choices=NivelActividad.choices)
    objetivo = models.CharField(max_length=2, choices=Objetivo.choices)

    class Meta:
        db_table = "perfiles_usuarios"
        verbose_name = "Perfil de Usuario"
        verbose_name_plural = "Perfiles de Usuarios"

    def __str__(self):
        return f"Perfil de {self.usuario.username}"

    @property
    def harris_benedict(self):
        """Calcula la Tasa Metabólica Basal usando la fórmula de Harris-Benedict revisada"""
        peso = float(self.peso_kg)
        talla = float(self.talla_cm)
        edad = float(self.edad)

        if self.sexo == Sexo.MASCULINO:
            bmr = 88.362 + (13.397 * peso) + (4.799 * talla) - (5.677 * edad)
        else:
            bmr = 447.593 + (9.247 * peso) + (3.098 * talla) - (4.330 * edad)

        # Factores de actividad
        factores = {
            NivelActividad.SEDENTARIO: 1.2,
            NivelActividad.LIGERO: 1.375,
            NivelActividad.MODERADO: 1.55,
            NivelActividad.INTENSO: 1.725,
            NivelActividad.MUY_INTENSO: 1.9,
        }

        tdee = bmr * factores.get(self.nivel_actividad, 1.2)

        # Ajuste por objetivo
        if self.objetivo == Objetivo.PERDER_PESO:
            tdee -= 500
        elif self.objetivo == Objetivo.GANAR_MASA:
            tdee += 300

        return round(tdee, 2)


class MetaNutricional(models.Model):
    perfil = models.ForeignKey(
        PerfilUsuario, on_delete=models.CASCADE, related_name="metas"
    )
    calorias_meta = models.IntegerField()
    proteinas_g = models.IntegerField()
    carbohidratos_g = models.IntegerField()
    grasas_g = models.IntegerField()
    agua_ml = models.IntegerField(default=2000)

    class Meta:
        db_table = "metas_nutricionales"
        verbose_name = "Meta Nutricional"
        verbose_name_plural = "Metas Nutricionales"


class RegistroComida(models.Model):
    objects = RegistroQuerySet.as_manager()

    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name="comidas")
    fecha = models.DateField()
    tipo_comida = models.CharField(max_length=2, choices=TipoComida.choices)

    class Meta:
        db_table = "registros_comidas"
        unique_together = ["usuario", "fecha", "tipo_comida"]
        verbose_name = "Registro de Comida"
        verbose_name_plural = "Registros de Comidas"
        ordering = ["-fecha", "tipo_comida"]

    def __str__(self):
        return f"{self.usuario.username} - {self.fecha} ({self.get_tipo_comida_display()})"

    @property
    def total_calorias(self):
        return sum(item.total_calorias for item in self.items.all())


class ItemRegistro(models.Model):
    registro = models.ForeignKey(
        RegistroComida, on_delete=models.CASCADE, related_name="items"
    )
    alimento = models.ForeignKey(Alimento, on_delete=models.PROTECT)
    cantidad_g = models.DecimalField(
        max_digits=7, decimal_places=2, validators=[validar_cantidad_positiva]
    )

    # Campos calculados persistentes
    total_calorias = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    total_proteinas = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    total_carbohidratos = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    total_grasas = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    class Meta:
        db_table = "items_registros"
        verbose_name = "Ítem de Registro"
        verbose_name_plural = "Ítems de Registros"

    def __str__(self):
        return f"{self.alimento.nombre} ({self.cantidad_g}g)"

    def calcular_macros(self):
        """Calcula los macros proporcionales a la cantidad en gramos"""
        factor = self.cantidad_g / Decimal("100.0")
        self.total_calorias = (self.alimento.calorias_100g * factor).quantize(Decimal("0.01"))
        self.total_proteinas = (self.alimento.proteinas_100g * factor).quantize(Decimal("0.01"))
        self.total_carbohidratos = (self.alimento.carbohidratos_100g * factor).quantize(Decimal("0.01"))
        self.total_grasas = (self.alimento.grasas_100g * factor).quantize(Decimal("0.01"))

    def save(self, *args, **kwargs):
        self.calcular_macros()
        self.full_clean()  # Ejecuta validaciones (incluyendo validators=[...])
        super().save(*args, **kwargs)


class RegistroHabito(models.Model):
    objects = RegistroQuerySet.as_manager()

    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name="habitos")
    fecha = models.DateField()
    vasos_agua = models.IntegerField(default=0)
    horas_sueno = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    pasos = models.IntegerField(default=0)
    minutos_ejercicio = models.IntegerField(default=0)
    tipo_ejercicio = models.CharField(
        max_length=2, choices=TipoEjercicio.choices, blank=True, null=True
    )

    class Meta:
        db_table = "registros_habitos"
        unique_together = ["usuario", "fecha"]
        verbose_name = "Registro de Hábito"
        verbose_name_plural = "Registros de Hábitos"
        ordering = ["-fecha"]


class Logro(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField()
    tipo = models.CharField(max_length=50)  # Ej: 'calorias', 'agua', 'ejercicio'
    icono = models.CharField(max_length=50)  # Clase de icono o emoji
    condicion = models.JSONField()  # Parámetros para desbloquearlo

    class Meta:
        db_table = "logros"

    def __str__(self):
        return self.nombre


class LogroUsuario(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name="logros")
    logro = models.ForeignKey(Logro, on_delete=models.CASCADE)
    fecha_obtenido = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "logros_usuarios"
        unique_together = ["usuario", "logro"]
