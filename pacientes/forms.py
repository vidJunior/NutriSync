# pacientes/forms.py
# Formulario de pacientes.

import random
from django import forms
from config.choices import Sexo
from .models import Paciente


class PacienteForm(forms.ModelForm):
    """Formulario para el registro rápido y simplificado de pacientes."""

    motivo_consulta = forms.ChoiceField(
        choices=[
            ("Pérdida de peso", "Pérdida de peso"),
            ("Aumento de masa muscular", "Aumento de masa muscular"),
            ("Nutrición deportiva", "Nutrición deportiva"),
            ("Embarazo", "Embarazo"),
            ("Control clínico", "Control clínico"),
            ("Diabetes", "Diabetes"),
            ("Mejora de hábitos", "Mejora de hábitos"),
            ("Otro", "Otro"),
        ],
        required=True,
        widget=forms.Select(
            attrs={
                "class": "w-full border border-slate-200 rounded-lg px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-teal-500 text-slate-800 bg-white",
            }
        ),
        label="Motivo de Consulta",
    )

    observaciones_iniciales = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "w-full border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-teal-500 text-slate-800",
                "rows": 2,
                "placeholder": "Paciente desea perder 8 kg y mejorar hábitos alimenticios...",
            }
        ),
        label="Observaciones Iniciales",
    )

    class Meta:
        model = Paciente
        # Incluye los campos del registro rápido.
        fields = [
            "nombre",
            "apellido",
            "dni",
            "fecha_nacimiento",
            "sexo",
            "peso",
            "talla",
            "telefono",
            "email",
            "direccion",
        ]
        error_messages = {
            "sexo": {
                "required": "Debe seleccionar un género (Masculino o Femenino).",
            }
        }
        widgets = {
            "nombre": forms.TextInput(
                attrs={
                    "class": "w-full border border-slate-200 rounded-lg px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-teal-500 text-slate-800",
                    "placeholder": "Nombre del paciente",
                }
            ),
            "apellido": forms.TextInput(
                attrs={
                    "class": "w-full border border-slate-200 rounded-lg px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-teal-500 text-slate-800",
                    "placeholder": "Apellido del paciente",
                }
            ),
            "dni": forms.TextInput(
                attrs={
                    "class": "w-full border border-slate-200 rounded-lg px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-teal-500 text-slate-800",
                    "placeholder": "DNI (8 dígitos)",
                    "maxlength": "8",
                }
            ),
            "fecha_nacimiento": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "w-full border border-slate-200 rounded-lg px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-teal-500 text-slate-800",
                    "id": "id_fecha_nacimiento",
                },
                format="%Y-%m-%d",
            ),
            "sexo": forms.Select(
                attrs={
                    "class": "w-full border border-slate-200 rounded-lg pl-3 pr-10 py-2.5 focus:outline-none focus:ring-2 focus:ring-teal-500 text-slate-800 bg-white appearance-none",
                }
            ),
            "peso": forms.NumberInput(
                attrs={
                    "class": "w-full border border-slate-200 rounded-lg px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-teal-500 text-slate-800",
                    "placeholder": "Ej: 70.5",
                    "step": "0.1",
                    "id": "id_peso",
                }
            ),
            "talla": forms.NumberInput(
                attrs={
                    "class": "w-full border border-slate-200 rounded-lg px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-teal-500 text-slate-800",
                    "placeholder": "Ej: 165.0",
                    "step": "0.1",
                    "id": "id_talla",
                }
            ),
            "telefono": forms.TextInput(
                attrs={
                    "class": "w-full border border-slate-200 rounded-lg px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-teal-500 text-slate-800",
                    "placeholder": "Ej: 999000000",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "w-full border border-slate-200 rounded-lg px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-teal-500 text-slate-800",
                    "placeholder": "correo@ejemplo.com",
                }
            ),
            "direccion": forms.TextInput(
                attrs={
                    "class": "w-full border border-slate-200 rounded-lg px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-teal-500 text-slate-800",
                    "placeholder": "Dirección del domicilio (Opcional)",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["sexo"].choices = [("", "Seleccionar")] + Sexo.CHOICES
        self.fields["talla"].required = True
        self.fields["dni"].required = True
        self.fields["email"].required = True
        self.fields["telefono"].required = True

        # Carga notas guardadas al editar.
        if self.instance and self.instance.pk:
            notas = self.instance.notas_generales or ""
            if "Motivo de Consulta:" in notas:
                parts = notas.split("Motivo de Consulta:")
                if len(parts) > 1:
                    subparts = parts[1].split("\nObservaciones Iniciales:\n")
                    motivo = subparts[0].strip()
                    observaciones = subparts[1].strip() if len(subparts) > 1 else ""
                    self.initial["motivo_consulta"] = motivo
                    self.initial["observaciones_iniciales"] = observaciones

    def clean_talla(self):
        """Convierte talla en metros a centímetros si es necesario."""
        talla = self.cleaned_data.get("talla")
        if talla is not None:
            if 0.5 <= talla <= 2.5:
                talla = talla * 100
        return talla

    def clean_nombre(self):
        return self.cleaned_data.get("nombre", "").strip().title()

    def clean_apellido(self):
        return self.cleaned_data.get("apellido", "").strip().title()

    def clean_dni(self):
        """Hace opcional el DNI autogenerando uno único si se deja vacío."""
        dni = self.cleaned_data.get("dni", "")
        if not dni:
            while True:
                mock_dni = "".join(random.choices("0123456789", k=8))
                if not Paciente.objects.filter(dni=mock_dni).exists():
                    return mock_dni
        return dni.strip()

    def clean(self):
        cleaned_data = super().clean()
        nombre = cleaned_data.get("nombre")
        apellido = cleaned_data.get("apellido")
        dni = cleaned_data.get("dni")
        email = cleaned_data.get("email")

        if nombre and apellido and nombre.lower() == apellido.lower():
            raise forms.ValidationError(
                "El nombre y el apellido del paciente no pueden ser idénticos."
            )

        # Validación multi-tenant de unicidad
        nutricionista = getattr(self.instance, "nutricionista", None)
        if not nutricionista:
            try:
                from core.middleware import get_current_user
                nutricionista = get_current_user()
            except ImportError:
                pass

        if nutricionista:
            if dni:
                qs_dni = Paciente.objects.filter(nutricionista=nutricionista, dni=dni)
                if self.instance.pk:
                    qs_dni = qs_dni.exclude(pk=self.instance.pk)
                if qs_dni.exists():
                    self.add_error("dni", "Ya tienes registrado un paciente con este DNI.")

            if email:
                qs_email = Paciente.objects.filter(nutricionista=nutricionista, email=email)
                if self.instance.pk:
                    qs_email = qs_email.exclude(pk=self.instance.pk)
                if qs_email.exists():
                    self.add_error("email", "Ya tienes registrado un paciente con este correo electrónico.")

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        motivo = self.cleaned_data.get("motivo_consulta")
        observaciones = self.cleaned_data.get("observaciones_iniciales")

        # Guarda motivo y observaciones en notas.
        instance.notas_generales = f"Motivo de Consulta: {motivo}\nObservaciones Iniciales:\n{observaciones}"

        if commit:
            instance.save()
        return instance

