from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from ..models import PlanNutricional, ComidaPlan, Receta
from config.choices import Objetivo

INPUT_CLASSES = (
    "w-full border border-slate-200 rounded-lg px-3 py-2 text-sm "
    "focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent "
    "transition-all duration-200"
)
SELECT_CLASSES = INPUT_CLASSES
TEXTAREA_CLASSES = INPUT_CLASSES + " resize-none"

class PlanNutricionalForm(forms.ModelForm):
    """
    Formulario para crear y editar un modelo/plantilla de plan nutricional.
    """

    class Meta:
        model = PlanNutricional
        fields = [
            "nombre", "descripcion", "objetivo", "tipo_paciente",
            "calorias_diarias", "proteinas_g", "carbohidratos_g", "grasas_g",
            "fibra_g", "agua_recomendada", "num_comidas", "estado",
        ]
        widgets = {
            "nombre": forms.TextInput(attrs={
                "class": INPUT_CLASSES,
                "placeholder": "Ej: Plan hiperproteico de definición",
            }),
            "descripcion": forms.Textarea(attrs={
                "class": TEXTAREA_CLASSES, "rows": 3,
                "placeholder": "Describe el enfoque del plan, recomendaciones generales...",
            }),
            "objetivo": forms.Select(attrs={"class": SELECT_CLASSES}),
            "tipo_paciente": forms.TextInput(attrs={
                "class": INPUT_CLASSES,
                "placeholder": "Ej: Deportista, Adulto activo",
            }),
            "calorias_diarias": forms.NumberInput(attrs={
                "class": INPUT_CLASSES, "min": "500",
            }),
            "proteinas_g": forms.NumberInput(attrs={
                "class": INPUT_CLASSES, "step": "0.1", "min": "0",
            }),
            "carbohidratos_g": forms.NumberInput(attrs={
                "class": INPUT_CLASSES, "step": "0.1", "min": "0",
            }),
            "grasas_g": forms.NumberInput(attrs={
                "class": INPUT_CLASSES, "step": "0.1", "min": "0",
            }),
            "fibra_g": forms.NumberInput(attrs={
                "class": INPUT_CLASSES, "min": "0",
            }),
            "agua_recomendada": forms.NumberInput(attrs={
                "class": INPUT_CLASSES, "step": "0.1", "min": "0",
            }),
            "num_comidas": forms.NumberInput(attrs={
                "class": INPUT_CLASSES, "min": "1",
            }),
            "estado": forms.Select(attrs={"class": SELECT_CLASSES}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class ComidaPlanForm(forms.ModelForm):
    """Formulario para agregar o editar una comida dentro de un modelo de plan nutricional."""

    class Meta:
        model = ComidaPlan
        fields = [
            "tipo_comida", "hora_sugerida", "receta", "observaciones",
        ]
        widgets = {
            "tipo_comida": forms.TextInput(attrs={
                "class": INPUT_CLASSES,
                "placeholder": "Ej: Desayuno, Merienda, Almuerzo",
            }),
            "hora_sugerida": forms.TimeInput(attrs={
                "class": INPUT_CLASSES, "type": "time",
            }),
            "receta": forms.Select(attrs={"class": SELECT_CLASSES}),
            "observaciones": forms.Textarea(attrs={
                "class": TEXTAREA_CLASSES, "rows": 3,
                "placeholder": "Indicaciones adicionales para esta comida...",
            }),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        
        # Muestra recetas propias y del sistema.
        if user:
            self.fields["receta"].queryset = Receta.objects.filter(
                (Q(creado_por=user) & Q(paciente__isnull=True)) | Q(es_sistema=True)
            ).order_by("nombre")
        else:
            self.fields["receta"].queryset = Receta.objects.filter(es_sistema=True).order_by("nombre")

