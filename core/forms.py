# core/forms.py
# Formulario para editar el perfil profesional del nutricionista.

from django import forms
from .models import PerfilNutricionista


class PerfilNutricionistaForm(forms.ModelForm):
    """Formulario para que el nutricionista edite sus datos profesionales."""

    class Meta:
        model = PerfilNutricionista
        fields = [
            "nombre_completo",
            "especialidad",
            "telefono",
            "email_profesional",
            "numero_colegiatura",
            "direccion_consultorio",
        ]
        widgets = {
            # Aplicamos clases de diseño premium de alta gama para los inputs
            "nombre_completo": forms.TextInput(
                attrs={
                    "class": "w-full bg-slate-50/50 border border-slate-200 rounded-2xl px-5 py-3.5 focus:outline-none focus:ring-2 focus:ring-teal-500/25 focus:border-teal-500 focus:bg-white text-slate-800 font-medium placeholder-slate-400/80 transition-all duration-300",
                    "placeholder": "Nombre Completo",
                }
            ),
            "especialidad": forms.TextInput(
                attrs={
                    "class": "w-full bg-slate-50/50 border border-slate-200 rounded-2xl px-5 py-3.5 focus:outline-none focus:ring-2 focus:ring-teal-500/25 focus:border-teal-500 focus:bg-white text-slate-800 font-medium placeholder-slate-400/80 transition-all duration-300",
                    "placeholder": "Especialidad",
                }
            ),
            "telefono": forms.TextInput(
                attrs={
                    "class": "w-full bg-slate-50/50 border border-slate-200 rounded-2xl px-5 py-3.5 focus:outline-none focus:ring-2 focus:ring-teal-500/25 focus:border-teal-500 focus:bg-white text-slate-800 font-medium placeholder-slate-400/80 transition-all duration-300",
                    "placeholder": "Teléfono",
                }
            ),
            "email_profesional": forms.EmailInput(
                attrs={
                    "class": "w-full bg-slate-50/50 border border-slate-200 rounded-2xl px-5 py-3.5 focus:outline-none focus:ring-2 focus:ring-teal-500/25 focus:border-teal-500 focus:bg-white text-slate-800 font-medium placeholder-slate-400/80 transition-all duration-300",
                    "placeholder": "Correo Electrónico Profesional",
                }
            ),
            "numero_colegiatura": forms.TextInput(
                attrs={
                    "class": "w-full bg-slate-50/50 border border-slate-200 rounded-2xl px-5 py-3.5 focus:outline-none focus:ring-2 focus:ring-teal-500/25 focus:border-teal-500 focus:bg-white text-slate-800 font-medium placeholder-slate-400/80 transition-all duration-300",
                    "placeholder": "C.N.P. (Colegiatura)",
                }
            ),
            "direccion_consultorio": forms.Textarea(
                attrs={
                    "class": "w-full bg-slate-50/50 border border-slate-200 rounded-2xl px-5 py-3.5 focus:outline-none focus:ring-2 focus:ring-teal-500/25 focus:border-teal-500 focus:bg-white text-slate-800 font-medium placeholder-slate-400/80 transition-all duration-300",
                    "rows": 3,
                    "placeholder": "Dirección del Consultorio",
                }
            ),
        }

    def clean_numero_colegiatura(self):
        numero_colegiatura = self.cleaned_data.get("numero_colegiatura", "").strip()
        if numero_colegiatura:
            import re
            if not re.match(r"^\d{3,6}$", numero_colegiatura):
                raise forms.ValidationError("El C.N.P. debe ser un número de 3 a 6 dígitos.")
            qs = PerfilNutricionista.objects.filter(numero_colegiatura=numero_colegiatura)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("Este número de colegiatura C.N.P. ya está registrado.")
        return numero_colegiatura
