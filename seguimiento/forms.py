# seguimiento/forms.py
# Formularios de medidas y notas.
# Configura los formularios de seguimiento.

from django import forms
from decimal import Decimal
from .models import MedidaCorporal, NotaClinica

# Clases CSS de los campos
INPUT_CLASSES = (
    "border border-slate-200 rounded-lg px-3 py-2 w-full "
    "focus:ring-2 focus:ring-teal-500 focus:border-teal-500 "
    "text-sm text-slate-800 transition-all duration-200"
)
SELECT_CLASSES = INPUT_CLASSES
TEXTAREA_CLASSES = (
    "border border-slate-200 rounded-lg px-3 py-2 w-full "
    "focus:ring-2 focus:ring-teal-500 focus:border-teal-500 "
    "text-sm text-slate-800 transition-all duration-200 resize-y"
)


class MedidaCorporalForm(forms.ModelForm):
    talla_cm = forms.DecimalField(
        min_value=Decimal("0.5"),
        max_value=Decimal("250"),
        decimal_places=1,
        widget=forms.NumberInput(
            attrs={
                "class": INPUT_CLASSES,
                "step": "0.1",
                "placeholder": "Ej: 165.0",
            }
        ),
    )

    class Meta:
        model = MedidaCorporal
        fields = [
            "peso_kg",
            "talla_cm",
            "grasa_corporal_pct",
            "cintura_cm",
            "cadera_cm",
            "notas",
        ]
        widgets = {
            "peso_kg": forms.NumberInput(
                attrs={
                    "class": INPUT_CLASSES,
                    "step": "0.1",
                    "placeholder": "Ej: 70.5",
                }
            ),
            "talla_cm": forms.NumberInput(
                attrs={
                    "class": INPUT_CLASSES,
                    "step": "0.1",
                    "placeholder": "Ej: 165.0",
                }
            ),
            "grasa_corporal_pct": forms.NumberInput(
                attrs={
                    "class": INPUT_CLASSES,
                    "step": "0.1",
                    "placeholder": "Opcional",
                }
            ),
            "cintura_cm": forms.NumberInput(
                attrs={
                    "class": INPUT_CLASSES,
                    "step": "0.1",
                    "placeholder": "Opcional",
                }
            ),
            "cadera_cm": forms.NumberInput(
                attrs={
                    "class": INPUT_CLASSES,
                    "step": "0.1",
                    "placeholder": "Opcional",
                }
            ),
            "notas": forms.Textarea(
                attrs={
                    "class": TEXTAREA_CLASSES,
                    "rows": 3,
                    "placeholder": "Observaciones adicionales...",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Muestra el IMC actual sin editarlo.
        if self.instance and self.instance.pk and self.instance.imc:
            self.fields["imc_display"] = forms.DecimalField(
                label="IMC (calculado)",
                initial=self.instance.imc,
                disabled=True,
                required=False,
                widget=forms.NumberInput(
                    attrs={"class": INPUT_CLASSES, "readonly": "readonly"}
                ),
            )
            # Insertarlo después de talla_cm
            campo_imc = self.fields.pop("imc_display")
            self.fields.insert(
                list(self.fields.keys()).index("talla_cm") + 1,
                "imc_display",
                campo_imc,
            )

    def clean_talla_cm(self):
        """Si el usuario ingresa la talla en metros (ej: 1.80), la convertimos a centímetros (180)."""
        talla_cm = self.cleaned_data.get("talla_cm")
        if talla_cm is not None:
            # Convierte metros a centímetros.
            if 0.5 <= talla_cm <= 2.5:
                talla_cm = talla_cm * 100
        return talla_cm


class NotaClinicaForm(forms.ModelForm):
    class Meta:
        model = NotaClinica
        fields = [
            "fecha",
            "titulo",
            "tipo",
            "cita",
            "motivo_consulta",
            "resumen_consulta",
            "objetivos_acordados",
            "plan_accion",
            "observaciones_clinicas",
        ]
        widgets = {
            "fecha": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": INPUT_CLASSES,
                }
            ),
            "titulo": forms.TextInput(
                attrs={
                    "class": INPUT_CLASSES,
                    "placeholder": "Ej: Evaluación inicial",
                }
            ),
            "tipo": forms.Select(attrs={"class": SELECT_CLASSES}),
            "cita": forms.Select(attrs={"class": SELECT_CLASSES}),
            "motivo_consulta": forms.Textarea(
                attrs={
                    "class": TEXTAREA_CLASSES,
                    "rows": 2,
                    "placeholder": "Motivo por el que asiste el paciente...",
                }
            ),
            "resumen_consulta": forms.Textarea(
                attrs={
                    "class": TEXTAREA_CLASSES,
                    "rows": 4,
                    "placeholder": "Resumen de la valoración, mediciones y plan...",
                }
            ),
            "objetivos_acordados": forms.Textarea(
                attrs={
                    "class": TEXTAREA_CLASSES,
                    "rows": 2,
                    "placeholder": "Metas a corto y mediano plazo...",
                }
            ),
            "plan_accion": forms.Textarea(
                attrs={
                    "class": TEXTAREA_CLASSES,
                    "rows": 3,
                    "placeholder": "Acuerdos, cambios y tareas para el paciente...",
                }
            ),
            "observaciones_clinicas": forms.Textarea(
                attrs={
                    "class": TEXTAREA_CLASSES,
                    "rows": 3,
                    "placeholder": "Notas exclusivas para el profesional...",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        # Muestra solo las citas del paciente.
        paciente = kwargs.pop("paciente", None)
        super().__init__(*args, **kwargs)
        if paciente:
            self.fields["cita"].queryset = paciente.citas.all()
            self.fields["cita"].empty_label = "Sin cita asociada"
        else:
            self.fields["cita"].queryset = self.fields["cita"].queryset.none()
            self.fields["cita"].empty_label = "Selecciona un paciente primero"
