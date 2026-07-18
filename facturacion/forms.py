# facturacion/forms.py
# Formularios del módulo de Facturación.

from django import forms
from django.utils import timezone
from facturacion.models import (
    Cobro,
    Factura,
    ItemFactura,
    Pago,
    SuscripcionNutricionista,
)
from facturacion.choices import MetodoPago, ConceptoCobro, TipoFacturacion
from facturacion.utils import calcular_total_con_igv
from facturacion.validators import validate_comprobante


class CobroForm(forms.ModelForm):
    """Formulario para crear y editar cobros a pacientes."""

    class Meta:
        model = Cobro
        fields = [
            "paciente",
            "cita",
            "concepto",
            "descripcion",
            "monto",
            "notas",
        ]
        widgets = {
            "paciente": forms.Select(attrs={"class": "form-select"}),
            "cita": forms.Select(attrs={"class": "form-select"}),
            "concepto": forms.Select(attrs={"class": "form-select"}),
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "monto": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": "0"}
            ),
            "notas": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }

    def __init__(self, *args, nutricionista=None, **kwargs):
        super().__init__(*args, **kwargs)
        if nutricionista:
            from pacientes.models import Paciente
            from agendas.models import Cita

            self.fields["paciente"].queryset = Paciente.objects.filter(
                nutricionista=nutricionista, estado=True
            )
            self.fields["cita"].queryset = Cita.objects.filter(
                paciente__nutricionista=nutricionista
            ).order_by("-fecha_hora")
            self.fields["cita"].required = False
        self.fields["notas"].required = False

    def clean(self):
        cleaned_data = super().clean()
        paciente = cleaned_data.get("paciente")
        cita = cleaned_data.get("cita")
        if paciente and cita and cita.paciente_id != paciente.id:
            self.add_error("cita", "La cita seleccionada no pertenece al paciente.")
        return cleaned_data


class CobroPagoForm(forms.Form):
    """Formulario para registrar el pago de un cobro."""

    metodo_pago = forms.ChoiceField(
        choices=MetodoPago.CHOICES,
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Método de pago",
    )
    referencia = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Código de transacción"}
        ),
        label="Referencia / N° de operación",
    )
    comprobante = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={"class": "form-control"}),
        label="Comprobante de pago",
    )
    notas = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        label="Notas",
    )

    def clean_comprobante(self):
        comprobante = self.cleaned_data.get("comprobante")
        if comprobante:
            validate_comprobante(comprobante)
        return comprobante


class FacturaFiltroForm(forms.Form):
    """Formulario de filtros para la lista de facturas."""

    paciente = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Nombre del paciente"}
        ),
    )
    estado = forms.ChoiceField(
        required=False,
        choices=[("", "Todos")] + [
            ("borrador", "Borrador"),
            ("emitida", "Emitida"),
            ("pagada", "Pagada"),
            ("vencida", "Vencida"),
            ("cancelada", "Cancelada"),
        ],
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    fecha_desde = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )
    fecha_hasta = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )


class FacturaCrearForm(forms.ModelForm):
    """Formulario para crear una factura desde cobros pendientes."""

    class Meta:
        model = Factura
        fields = ["paciente", "fecha_vencimiento", "notas"]
        widgets = {
            "paciente": forms.Select(attrs={"class": "form-select"}),
            "fecha_vencimiento": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "notas": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }

    def __init__(self, *args, nutricionista=None, **kwargs):
        super().__init__(*args, **kwargs)
        if nutricionista:
            from pacientes.models import Paciente

            self.fields["paciente"].queryset = Paciente.objects.filter(
                nutricionista=nutricionista, estado=True
            )
        self.fields["notas"].required = False

    def clean_fecha_vencimiento(self):
        fecha = self.cleaned_data.get("fecha_vencimiento")
        if fecha and fecha < timezone.localdate():
            raise forms.ValidationError(
                "La fecha de vencimiento no puede estar en el pasado."
            )
        return fecha


class ItemFacturaForm(forms.ModelForm):
    """Formulario para agregar ítems a una factura."""

    class Meta:
        model = ItemFactura
        fields = ["descripcion", "cantidad", "precio_unitario"]
        widgets = {
            "descripcion": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Descripción del servicio"}
            ),
            "cantidad": forms.NumberInput(
                attrs={"class": "form-control", "min": "1"}
            ),
            "precio_unitario": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": "0"}
            ),
        }


class ItemFacturaCobroForm(forms.Form):
    """Formulario para seleccionar cobros pendientes para agregar a una factura."""

    cobros_seleccionados = forms.MultipleChoiceField(
        choices=[],
        widget=forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"}),
        label="Cobros pendientes",
    )

    def __init__(self, *args, cobros=None, **kwargs):
        super().__init__(*args, **kwargs)
        if cobros:
            self.fields["cobros_seleccionados"].choices = [
                (c.id, f"Cobro #{c.id} - {c.paciente} - S/{c.total}")
                for c in cobros
            ]


class CambiarPlanForm(forms.Form):
    """Formulario para cambiar el plan de suscripción."""

    plan = forms.ChoiceField(
        choices=[],
        widget=forms.RadioSelect(attrs={"class": "form-check-input"}),
        label="Selecciona un plan",
    )
    tipo_facturacion = forms.ChoiceField(
        choices=TipoFacturacion.CHOICES,
        widget=forms.RadioSelect(attrs={"class": "form-check-input"}),
        initial=TipoFacturacion.MENSUAL,
        label="Tipo de facturación",
    )

    def __init__(self, *args, planes=None, **kwargs):
        super().__init__(*args, **kwargs)
        if planes:
            self.fields["plan"].choices = [
                (p.id, f"{p.nombre} - S/{p.precio_mensual}/mes")
                for p in planes
            ]


class IngresosFiltroForm(forms.Form):
    """Formulario de filtros para el reporte de ingresos."""

    fecha_desde = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        label="Fecha desde",
    )
    fecha_hasta = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        label="Fecha hasta",
    )
    paciente = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Nombre del paciente"}
        ),
    )
    concepto = forms.ChoiceField(
        required=False,
        choices=[("", "Todos")] + ConceptoCobro.CHOICES,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    metodo_pago = forms.ChoiceField(
        required=False,
        choices=[("", "Todos")] + MetodoPago.CHOICES,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
