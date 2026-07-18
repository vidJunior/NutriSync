# administracion/forms.py
# Formularios administrativos.

from django import forms
from facturacion.models import PlanSuscripcion

class PlanSuscripcionForm(forms.ModelForm):
    class Meta:
        model = PlanSuscripcion
        fields = [
            "nombre",
            "descripcion",
            "precio_mensual",
            "precio_anual",
            "limite_pacientes",
            "limite_citas_mes",
            "comision_cobros",
            "comision_suscripcion",
            "stripe_price_id_mensual",
            "stripe_price_id_anual",
            "activo",
        ]
        widgets = {
            "nombre": forms.TextInput(attrs={
                "class": "w-full px-3.5 py-2.5 rounded-xl text-sm bg-slate-50 border border-slate-200 text-slate-800 outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-500/20 transition-all",
                "placeholder": "Ej. Plan Profesional"
            }),
            "descripcion": forms.Textarea(attrs={
                "class": "w-full px-3.5 py-2.5 rounded-xl text-sm bg-slate-50 border border-slate-200 text-slate-800 outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-500/20 transition-all h-24",
                "placeholder": "Detalla las características del plan..."
            }),
            "precio_mensual": forms.NumberInput(attrs={
                "class": "w-full px-3.5 py-2.5 rounded-xl text-sm bg-slate-50 border border-slate-200 text-slate-800 outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-500/20 transition-all",
                "step": "0.01"
            }),
            "precio_anual": forms.NumberInput(attrs={
                "class": "w-full px-3.5 py-2.5 rounded-xl text-sm bg-slate-50 border border-slate-200 text-slate-800 outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-500/20 transition-all",
                "step": "0.01"
            }),
            "limite_pacientes": forms.NumberInput(attrs={
                "class": "w-full px-3.5 py-2.5 rounded-xl text-sm bg-slate-50 border border-slate-200 text-slate-800 outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-500/20 transition-all",
                "help_text": "-1 para ilimitados"
            }),
            "limite_citas_mes": forms.NumberInput(attrs={
                "class": "w-full px-3.5 py-2.5 rounded-xl text-sm bg-slate-50 border border-slate-200 text-slate-800 outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-500/20 transition-all"
            }),
            "comision_cobros": forms.NumberInput(attrs={
                "class": "w-full px-3.5 py-2.5 rounded-xl text-sm bg-slate-50 border border-slate-200 text-slate-800 outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-500/20 transition-all",
                "step": "0.01"
            }),
            "comision_suscripcion": forms.NumberInput(attrs={
                "class": "w-full px-3.5 py-2.5 rounded-xl text-sm bg-slate-50 border border-slate-200 text-slate-800 outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-500/20 transition-all",
                "step": "0.01"
            }),
            "stripe_price_id_mensual": forms.TextInput(attrs={
                "class": "w-full px-3.5 py-2.5 rounded-xl text-sm bg-slate-50 border border-slate-200 text-slate-800 outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-500/20 transition-all",
                "placeholder": "price_..."
            }),
            "stripe_price_id_anual": forms.TextInput(attrs={
                "class": "w-full px-3.5 py-2.5 rounded-xl text-sm bg-slate-50 border border-slate-200 text-slate-800 outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-500/20 transition-all",
                "placeholder": "price_..."
            }),
            "activo": forms.CheckboxInput(attrs={
                "class": "rounded border-slate-300 text-teal-600 focus:ring-teal-500 h-4 w-4"
            }),
        }
