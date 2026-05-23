# pacientes/forms.py
# Formulario para crear y editar pacientes con validaciones de negocio.
# Usa widgets Tailwind para mantener la consistencia visual del sistema.

from django import forms
from config.choices import Sexo
from .models import Paciente


class PacienteForm(forms.ModelForm):
    """Formulario para crear/editar la ficha de un paciente."""

    class Meta:
        model = Paciente
        # Excluimos nutricionista (se asigna en la vista) y fechas automáticas
        fields = [
            "nombre",
            "apellido",
            "dni",
            "fecha_nacimiento",
            "sexo",
            "peso",
            "talla",
            "ocupacion",
            "telefono",
            "email",
            "direccion",
            "condiciones_medicas",
            "alergias",
            "notas_generales",
        ]
        widgets = {
            "nombre": forms.TextInput(
                attrs={
                    "class": "w-full border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-teal-500 text-slate-800",
                    "placeholder": "Nombre del paciente",
                }
            ),
            "apellido": forms.TextInput(
                attrs={
                    "class": "w-full border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-teal-500 text-slate-800",
                    "placeholder": "Apellido del paciente",
                }
            ),
            "dni": forms.TextInput(
                attrs={
                    "class": "w-full border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-teal-500 text-slate-800",
                    "placeholder": "DNI del paciente (8 dígitos)",
                    "maxlength": "8",
                }
            ),
            "fecha_nacimiento": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "w-full border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-teal-500 text-slate-800",
                },
                format="%Y-%m-%d",
            ),
            "sexo": forms.Select(
                attrs={
                    "class": "w-full border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-teal-500 text-slate-800 bg-white",
                }
            ),
            "peso": forms.NumberInput(
                attrs={
                    "class": "w-full border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-teal-500 text-slate-800",
                    "placeholder": "Ej: 70.5",
                    "step": "0.1",
                }
            ),
            "talla": forms.NumberInput(
                attrs={
                    "class": "w-full border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-teal-500 text-slate-800",
                    "placeholder": "Ej: 165.0",
                    "step": "0.1",
                }
            ),
            "ocupacion": forms.TextInput(
                attrs={
                    "class": "w-full border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-teal-500 text-slate-800",
                    "placeholder": "Ej: Ingeniero, Estudiante, Ama de casa",
                }
            ),
            "telefono": forms.TextInput(
                attrs={
                    "class": "w-full border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-teal-500 text-slate-800",
                    "placeholder": "Ej: 999000000",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "w-full border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-teal-500 text-slate-800",
                    "placeholder": "correo@ejemplo.com",
                }
            ),
            "direccion": forms.Textarea(
                attrs={
                    "class": "w-full border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-teal-500 text-slate-800",
                    "rows": 2,
                    "placeholder": "Dirección del domicilio",
                }
            ),
            "condiciones_medicas": forms.Textarea(
                attrs={
                    "class": "w-full border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-teal-500 text-slate-800",
                    "rows": 3,
                    "placeholder": "Condiciones médicas relevantes del paciente",
                }
            ),
            "alergias": forms.Textarea(
                attrs={
                    "class": "w-full border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-teal-500 text-slate-800",
                    "rows": 3,
                    "placeholder": "Alergias conocidas (alimentos, medicamentos, etc.)",
                }
            ),
            "notas_generales": forms.Textarea(
                attrs={
                    "class": "w-full border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-teal-500 text-slate-800",
                    "rows": 3,
                    "placeholder": "Observaciones generales relevantes para el nutricionista",
                }
            ),
        }
        error_messages = {
            "sexo": {
                "required": "Debe seleccionar un género (Masculino o Femenino).",
                "invalid_choice": "Seleccione una opción válida (Masculino o Femenino).",
            }
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Reemplazar la opción por defecto --------- por una indicación clara
        self.fields["sexo"].choices = [("", "Seleccione género...")] + Sexo.CHOICES
        # Hacer obligatoria la talla en el formulario web
        if "talla" in self.fields:
            self.fields["talla"].required = True

    def clean_talla(self):
        """Si el usuario ingresa la talla en metros (ej: 1.80), la convertimos a centímetros (180)."""
        talla = self.cleaned_data.get("talla")
        if talla is not None:
            # Si se encuentra en un rango de metros razonable (0.5 a 2.5), multiplicar por 100
            if 0.5 <= talla <= 2.5:
                talla = talla * 100
        return talla

    def clean_nombre(self):
        """Normaliza el nombre: primera letra mayúscula, sin espacios extra."""
        nombre = self.cleaned_data.get("nombre", "")
        return nombre.strip().title()

    def clean_apellido(self):
        """Normaliza el apellido: primera letra mayúscula, sin espacios extra."""
        apellido = self.cleaned_data.get("apellido", "")
        return apellido.strip().title()

    def clean_dni(self):
        """Normaliza el DNI quitando espacios en blanco."""
        dni = self.cleaned_data.get("dni", "")
        return dni.strip() if dni else ""

    # Nota: clean_telefono y clean_fecha_nacimiento fueron eliminados porque Django ejecuta
    # automáticamente los validadores del modelo (validate_telefono y validate_fecha_nacimiento_edad)
    # durante la validación del formulario.

    def clean(self):
        cleaned_data = super().clean()
        nombre = cleaned_data.get("nombre")
        apellido = cleaned_data.get("apellido")
        dni = cleaned_data.get("dni")
        email = cleaned_data.get("email")

        # 1. Validación cruzada: Nombre y Apellido no pueden ser idénticos
        if nombre and apellido and nombre.strip().lower() == apellido.strip().lower():
            raise forms.ValidationError(
                "El nombre y el apellido del paciente no pueden ser idénticos."
            )

        # 2. Validación de unicidad de DNI y Email por Nutricionista (multi-tenant)
        nutricionista = getattr(self.instance, "nutricionista", None)
        if not nutricionista:
            try:
                from core.middleware import get_current_user

                nutricionista = get_current_user()
            except ImportError:
                pass

        if nutricionista:
            # Unicidad de DNI por nutricionista
            if dni:
                qs_dni = Paciente.objects.filter(nutricionista=nutricionista, dni=dni)
                if self.instance.pk:
                    qs_dni = qs_dni.exclude(pk=self.instance.pk)
                if qs_dni.exists():
                    self.add_error(
                        "dni", "Ya tienes registrado un paciente con este DNI."
                    )

            # Unicidad de Email por nutricionista (si se provee)
            if email:
                qs_email = Paciente.objects.filter(
                    nutricionista=nutricionista, email=email
                )
                if self.instance.pk:
                    qs_email = qs_email.exclude(pk=self.instance.pk)
                if qs_email.exists():
                    self.add_error(
                        "email",
                        "Ya tienes registrado un paciente con este correo electrónico.",
                    )

        return cleaned_data
