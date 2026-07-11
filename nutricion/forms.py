# nutricion/forms.py
# Formularios para Alimento, PlanNutricional y ComidaPlan.
# Las validaciones de reglas de negocio van en clean() — no en la vista.

from django import forms
from django.core.exceptions import ValidationError
from .models import Alimento, PlanNutricional, ComidaPlan, CategoriaAlimento, Receta, IngredienteReceta
from config.choices import DiaSemana, TipoComida, Objetivo


# ─── Clases CSS reutilizables ────────────────────────────────────────────────
# Centralizamos los attrs de Tailwind para no repetirlos en cada campo.
INPUT_CLASSES = (
    "w-full border border-slate-200 rounded-lg px-3 py-2 text-sm "
    "focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent "
    "transition-all duration-200"
)
SELECT_CLASSES = INPUT_CLASSES
TEXTAREA_CLASSES = INPUT_CLASSES + " resize-none"


# ─── AlimentoForm ─────────────────────────────────────────────────────────────

class AlimentoForm(forms.ModelForm):
    """Formulario para crear y editar alimentos del catálogo nutricional."""

    class Meta:
        model = Alimento
        fields = [
            "nombre", "categoria", "porcion_referencia",
            "calorias_100g", "proteinas_100g", "carbohidratos_100g",
            "grasas_100g", "fibra_100g", "estado",
        ]
        widgets = {
            "nombre": forms.TextInput(attrs={
                "class": INPUT_CLASSES,
                "placeholder": "Ej: Arroz blanco cocido",
            }),
            "categoria": forms.Select(attrs={"class": SELECT_CLASSES}),
            "porcion_referencia": forms.TextInput(attrs={
                "class": INPUT_CLASSES,
                "placeholder": "Ej: 1 taza (240g)",
            }),
            "calorias_100g": forms.NumberInput(attrs={
                "class": INPUT_CLASSES, "step": "0.01", "min": "0",
            }),
            "proteinas_100g": forms.NumberInput(attrs={
                "class": INPUT_CLASSES, "step": "0.01", "min": "0",
            }),
            "carbohidratos_100g": forms.NumberInput(attrs={
                "class": INPUT_CLASSES, "step": "0.01", "min": "0",
            }),
            "grasas_100g": forms.NumberInput(attrs={
                "class": INPUT_CLASSES, "step": "0.01", "min": "0",
            }),
            "fibra_100g": forms.NumberInput(attrs={
                "class": INPUT_CLASSES, "step": "0.01", "min": "0",
            }),
        }
        labels = {
            "calorias_100g": "Calorías (kcal/100g)",
            "proteinas_100g": "Proteínas (g/100g)",
            "carbohidratos_100g": "Carbohidratos (g/100g)",
            "grasas_100g": "Grasas (g/100g)",
            "fibra_100g": "Fibra (g/100g)",
        }

    def clean_nombre(self):
        """Normalizamos el nombre para evitar duplicados por mayúsculas/minúsculas."""
        nombre = self.cleaned_data.get("nombre", "").strip()
        # Verificar duplicados excluyendo el mismo objeto en edición
        qs = Alimento.objects.filter(nombre__iexact=nombre)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError(
                f"Ya existe un alimento con el nombre «{nombre}». "
                "Verifica el catálogo antes de agregar uno nuevo."
            )
        return nombre


# ─── PlanNutricionalForm ──────────────────────────────────────────────────────

class PlanNutricionalForm(forms.ModelForm):
    """
    Formulario para crear y editar un plan nutricional.
    La validación de 'un solo plan activo por paciente' se hace en clean()
    para que funcione tanto en el form web como en el admin de Django.
    """

    class Meta:
        model = PlanNutricional
        fields = [
            "nombre", "objetivo", "fecha_inicio", "fecha_fin",
            "calorias_diarias", "proteinas_g", "carbohidratos_g", "grasas_g",
            "observaciones", "estado",
        ]
        widgets = {
            "nombre": forms.TextInput(attrs={
                "class": INPUT_CLASSES,
                "placeholder": "Ej: Plan pérdida de peso — Enero 2025",
            }),
            "objetivo": forms.Select(attrs={"class": SELECT_CLASSES}),
            "fecha_inicio": forms.DateInput(
                attrs={"class": INPUT_CLASSES, "type": "date"},
                format="%Y-%m-%d",
            ),
            "fecha_fin": forms.DateInput(
                attrs={"class": INPUT_CLASSES, "type": "date"},
                format="%Y-%m-%d",
            ),
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
            "observaciones": forms.Textarea(attrs={
                "class": TEXTAREA_CLASSES, "rows": 3,
                "placeholder": "Indicaciones adicionales, restricciones, observaciones clínicas...",
            }),
        }

    def __init__(self, *args, **kwargs):
        # Recibimos el paciente desde la vista para poder aplicar validaciones
        self.paciente = kwargs.pop("paciente", None)
        super().__init__(*args, **kwargs)

    def clean(self):
        """
        Valida reglas de negocio del plan:
        1. fecha_fin debe ser posterior a fecha_inicio.
        2. Un paciente solo puede tener un plan activo a la vez.
        """
        cleaned_data = super().clean()
        fecha_inicio = cleaned_data.get("fecha_inicio")
        fecha_fin = cleaned_data.get("fecha_fin")
        estado = cleaned_data.get("estado")

        # Regla: fecha_fin debe ser posterior a fecha_inicio
        if fecha_inicio and fecha_fin and fecha_fin < fecha_inicio:
            raise ValidationError(
                "La fecha de fin debe ser posterior a la fecha de inicio del plan."
            )

        # Regla de negocio: un solo plan activo por paciente.
        # Se valida aquí (en clean) para que funcione tanto en el form web como en el admin.
        if estado and self.paciente:
            planes_activos = PlanNutricional.objects.filter(
                paciente=self.paciente, estado=True
            )
            # Excluimos el plan actual en caso de edición
            if self.instance.pk:
                planes_activos = planes_activos.exclude(pk=self.instance.pk)
            if planes_activos.exists():
                raise ValidationError(
                    "Este paciente ya tiene un plan nutricional activo. "
                    "Desactiva el plan actual antes de crear uno nuevo."
                )

        return cleaned_data


# ─── ComidaPlanForm ───────────────────────────────────────────────────────────

class ComidaPlanForm(forms.ModelForm):
    """Formulario para agregar o editar una comida dentro de un plan nutricional."""

    class Meta:
        model = ComidaPlan
        fields = [
            "dia_semana", "tipo_comida", "descripcion",
            "alimentos_sugeridos", "recetas_sugeridas", "calorias_estimadas",
        ]
        widgets = {
            "dia_semana": forms.Select(attrs={"class": SELECT_CLASSES}),
            "tipo_comida": forms.Select(attrs={"class": SELECT_CLASSES}),
            "descripcion": forms.Textarea(attrs={
                "class": TEXTAREA_CLASSES, "rows": 3,
                "placeholder": "Ej: Avena con frutas y miel, vaso de leche descremada",
            }),
            "alimentos_sugeridos": forms.CheckboxSelectMultiple(),
            "recetas_sugeridas": forms.CheckboxSelectMultiple(),
            "calorias_estimadas": forms.NumberInput(attrs={
                "class": INPUT_CLASSES, "min": "0",
            }),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        plan = kwargs.pop("plan", None)
        super().__init__(*args, **kwargs)
        if plan:
            self.plan = plan

        # Solo mostramos alimentos activos en el selector
        self.fields["alimentos_sugeridos"].queryset = (
            Alimento.objects.filter(estado=True).order_by("nombre")
        )
        
        # Solo mostramos recetas del sistema o del nutricionista actual
        from django.db.models import Q
        from .models import Receta
        if user:
            self.fields["recetas_sugeridas"].queryset = (
                Receta.objects.filter(Q(es_sistema=True) | Q(creado_por=user)).order_by("nombre")
            )
        else:
            self.fields["recetas_sugeridas"].queryset = (
                Receta.objects.filter(es_sistema=True).order_by("nombre")
            )

    def clean(self):
        """
        Valida unicidad día+tipo_comida dentro del plan.
        """
        cleaned_data = super().clean()
        dia = cleaned_data.get("dia_semana")
        tipo = cleaned_data.get("tipo_comida")

        if dia and tipo and hasattr(self, "plan"):
            qs = ComidaPlan.objects.filter(plan=self.plan, dia_semana=dia, tipo_comida=tipo)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError(
                    f"Ya existe una entrada de {dict(TipoComida.CHOICES).get(tipo, tipo)} "
                    f"para el {dict(DiaSemana.CHOICES).get(dia, dia)} en este plan."
                )
        return cleaned_data


# ─── RecetaForm ───────────────────────────────────────────────────────────────

class RecetaForm(forms.ModelForm):
    """Formulario para crear y editar recetas (datos básicos)."""

    class Meta:
        model = Receta
        fields = ["nombre", "descripcion", "tiempo_preparacion", "porciones", "imagen_predeterminada"]
        widgets = {
            "nombre": forms.TextInput(attrs={
                "class": INPUT_CLASSES,
                "placeholder": "Ej: Ensalada César Saludable",
            }),
            "descripcion": forms.Textarea(attrs={
                "class": TEXTAREA_CLASSES,
                "rows": 2,
                "placeholder": "Breve descripción de la receta (opcional)...",
            }),
            "tiempo_preparacion": forms.NumberInput(attrs={
                "class": INPUT_CLASSES,
                "min": "1",
                "max": "480",
            }),
            "porciones": forms.NumberInput(attrs={
                "class": INPUT_CLASSES,
                "min": "1",
                "max": "100",
            }),
            "imagen_predeterminada": forms.Select(
                choices=[
                    ("salad", "Ensalada / Verde"),
                    ("soup", "Sopa / Crema"),
                    ("chicken", "Carnes / Pollo / Pescado"),
                    ("dessert", "Postres / Dulces"),
                    ("beverage", "Bebidas / Batidos"),
                    ("breakfast", "Desayuno / Avena / Huevo"),
                    ("snack", "Snack / Frutos secos"),
                ],
                attrs={"class": SELECT_CLASSES}
            ),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

    def clean_nombre(self):
        nombre = self.cleaned_data.get("nombre", "").strip()
        if not nombre:
            raise ValidationError("El nombre de la receta es obligatorio.")
        
        # Validación de unicidad de nombre de receta por nutricionista y paciente específico
        from .models import Receta
        if self.user:
            paciente = getattr(self.instance, "paciente", None)
            qs = Receta.objects.filter(nombre__iexact=nombre, creado_por=self.user, paciente=paciente)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                if paciente:
                    raise ValidationError(f"Ya tienes una receta registrada con el nombre «{nombre}» para este paciente.")
                else:
                    raise ValidationError(f"Ya tienes una plantilla de receta registrada con el nombre «{nombre}».")
        return nombre


# ─── IngredienteRecetaForm & FormSet ──────────────────────────────────────────

class IngredienteRecetaForm(forms.ModelForm):
    """Formulario individual para un ingrediente dentro de una receta."""
    from .models import IngredienteReceta

    class Meta:
        model = IngredienteReceta
        fields = ["alimento", "cantidad", "nota"]
        widgets = {
            "alimento": forms.Select(attrs={"class": SELECT_CLASSES}),
            "cantidad": forms.NumberInput(attrs={
                "class": INPUT_CLASSES,
                "step": "0.1",
                "min": "0.1",
                "placeholder": "Cantidad en gramos (g)",
            }),
            "nota": forms.TextInput(attrs={
                "class": INPUT_CLASSES,
                "placeholder": "Ej: 1 taza, picada en cubos",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["alimento"].queryset = Alimento.objects.filter(estado=True).order_by("nombre")


class BaseIngredienteRecetaFormSet(forms.BaseInlineFormSet):
    """Formset personalizado para validar los ingredientes de una receta."""

    def clean(self):
        super().clean()
        if any(self.errors):
            return

        ingredientes_validos = 0
        alimentos_seleccionados = set()

        for form in self.forms:
            # Si el form está marcado para borrado o vacío/sin cambios, lo ignoramos
            if self._should_delete_form(form):
                continue
            
            alimento = form.cleaned_data.get("alimento")
            cantidad = form.cleaned_data.get("cantidad")

            if alimento:
                # Comprobar duplicados
                if alimento in alimentos_seleccionados:
                    form.add_error("alimento", f"El alimento «{alimento.nombre}» ya está en la lista.")
                alimentos_seleccionados.add(alimento)
                
                # Comprobar cantidad positiva
                if not cantidad or cantidad <= 0:
                    form.add_error("cantidad", "La cantidad debe ser mayor a 0.")
                
                ingredientes_validos += 1

        if ingredientes_validos < 1:
            raise ValidationError("Debes agregar al menos un ingrediente válido a la receta.")


from django.forms import inlineformset_factory
from .models import Receta, IngredienteReceta

IngredienteRecetaFormSet = inlineformset_factory(
    Receta,
    IngredienteReceta,
    form=IngredienteRecetaForm,
    formset=BaseIngredienteRecetaFormSet,
    extra=0,
    can_delete=True,
)

