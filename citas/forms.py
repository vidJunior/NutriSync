# citas/forms.py
# Formulario de registro y edición de Citas.
# Filtra dinámicamente los pacientes del nutricionista autenticado y aplica el sistema de diseño.

from django import forms
from django.utils import timezone
from .models import Cita
from pacientes.models import Paciente


class CitaForm(forms.ModelForm):
    """
    Formulario para crear y actualizar Citas.
    Filtra los pacientes para mostrar únicamente los del nutricionista logueado y que estén activos.
    """

    class Meta:
        model = Cita
        fields = [
            "paciente",
            "fecha_hora",
            "duracion_minutos",
            "tipo",
            "estado",
            "motivo",
            "notas_consulta",
            "costo",
        ]
        widgets = {
            "fecha_hora": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={
                    "type": "datetime-local",
                    "placeholder": "Selecciona fecha y hora",
                }
            ),
            "motivo": forms.Textarea(attrs={"rows": 2, "placeholder": "Motivo de la consulta"}),
            "notas_consulta": forms.Textarea(attrs={"rows": 4, "placeholder": "Notas clínicas de la evolución"}),
            "duracion_minutos": forms.NumberInput(attrs={"min": 10, "max": 180, "step": 5}),
            "costo": forms.NumberInput(attrs={"min": 0, "step": "0.01", "placeholder": "0.00"}),
        }

    def __init__(self, *args, **kwargs):
        # Extraemos el usuario (nutricionista) de los kwargs pasados por la vista
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # 1. Filtrado dinámico de pacientes: solo los del nutricionista logueado y activos
        if self.user:
            # Mostramos únicamente los pacientes que pertenecen a este profesional y que estén activos (estado=True)
            self.fields["paciente"].queryset = Paciente.objects.filter(
                nutricionista=self.user,
                estado=True,
            ).order_by("nombre", "apellido")
        else:
            # Fallback seguro en caso de que no se pase usuario
            self.fields["paciente"].queryset = Paciente.objects.none()

        # 2. Restringir selección de fechas pasadas en el navegador para citas nuevas
        if not self.instance.pk:
            ahora_local = timezone.localtime(timezone.now())
            # Formato requerido por el input HTML5 datetime-local: YYYY-MM-DDTHH:MM
            self.fields["fecha_hora"].widget.attrs["min"] = ahora_local.strftime("%Y-%m-%dT%H:%M")

        # 3. Manejo condicional de la edición del estado del paciente
        if not self.instance.pk:
            # En creación: el estado se maneja automáticamente como 'programada' (por defecto en el modelo)
            # y se remueve del formulario para evitar que sea alterado por el usuario.
            if "estado" in self.fields:
                del self.fields["estado"]
        else:
            # En edición: restringir los estados de cambio a: Completada, Cancelada, No asistió.
            # Conservamos 'programada' como opción seleccionable SOLAMENTE si la cita está actualmente en ese estado.
            if "estado" in self.fields:
                from config.choices import EstadoCita
                
                opciones = [
                    (EstadoCita.COMPLETADA, "Completada"),
                    (EstadoCita.CANCELADA, "Cancelada"),
                ]
                
                # "No asistió" solo debe estar disponible si la cita ya inició o pasó en el tiempo
                ahora = timezone.now()
                if self.instance.fecha_hora and self.instance.fecha_hora < ahora:
                    opciones.append((EstadoCita.NO_ASISTIO, "No asistió"))
                elif self.instance.estado == EstadoCita.NO_ASISTIO:
                    # Si ya estaba en No asistió por alguna razón, se mantiene en la lista
                    opciones.append((EstadoCita.NO_ASISTIO, "No asistió"))
                    
                if self.instance.estado == EstadoCita.PROGRAMADA:
                    opciones.insert(0, (EstadoCita.PROGRAMADA, "Programada"))
                self.fields["estado"].choices = opciones

            # Bloqueo del cambio de tipo y de paciente si la cita ya es de tipo 'Primera Consulta'
            from config.choices import TipoCita
            if self.instance.tipo == TipoCita.PRIMERA_CONSULTA:
                if "tipo" in self.fields:
                    self.fields["tipo"].disabled = True
                    self.fields["tipo"].help_text = "El tipo de una 'Primera Consulta' no puede ser modificado."
                if "paciente" in self.fields:
                    self.fields["paciente"].disabled = True
                    self.fields["paciente"].help_text = "El paciente de una 'Primera Consulta' no puede ser modificado."


        # 3. Aplicar clases CSS del sistema de diseño (Tailwind) a todos los campos
        for field_name, field in self.fields.items():
            if field_name == "fecha_hora":
                # Dejamos espacio para el icono a la izquierda (pl-10)
                base_classes = (
                    "mt-1 block w-full rounded-lg border border-slate-200 pl-10 pr-3 py-2 text-slate-800 "
                    "placeholder-slate-400 focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500 "
                    "transition duration-150"
                )
            else:
                base_classes = (
                    "mt-1 block w-full rounded-lg border border-slate-200 px-3 py-2 text-slate-800 "
                    "placeholder-slate-400 focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500 "
                    "transition duration-150"
                )

            # Si es un checkbox (no lo hay en este form por defecto, pero por robustez)
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "rounded text-teal-600 focus:ring-teal-500 border-slate-300"
            else:
                existing_classes = field.widget.attrs.get("class", "")
                field.widget.attrs["class"] = f"{base_classes} {existing_classes}".strip()

    def clean(self):
        cleaned_data = super().clean()
        paciente = cleaned_data.get("paciente")
        tipo = cleaned_data.get("tipo")

        if paciente and tipo:
            from config.choices import TipoCita
            if tipo == TipoCita.PRIMERA_CONSULTA:
                citas_previas = Cita.objects.filter(
                    paciente=paciente,
                    tipo=TipoCita.PRIMERA_CONSULTA
                )
                if self.instance.pk:
                    citas_previas = citas_previas.exclude(pk=self.instance.pk)
                
                if citas_previas.exists():
                    self.add_error(
                        "tipo",
                        "El paciente seleccionado ya cuenta con una cita registrada de tipo 'Primera Consulta'. Seleccione Seguimiento, Control o Evaluación."
                    )
        return cleaned_data
