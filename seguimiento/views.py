# seguimiento/views.py
# Vistas de seguimiento corporal y notas clínicas.
# Todas filtran por paciente__nutricionista=request.user para aislamiento de datos.

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import ListView, CreateView, DetailView
from django.urls import reverse_lazy
from django.db.models import Q
from itertools import chain

from .models import MedidaCorporal, NotaClinica
from .forms import MedidaCorporalForm, NotaClinicaForm
from pacientes.models import Paciente
from config.choices import TipoNota


# ─── Mixin de aislamiento multi-nutricionista ────────────────────────────────
# Filtra por paciente__nutricionista en lugar de un FK directo a User,
# ya que MedidaCorporal y NotaClinica se relacionan con Paciente, no con User.


class NutricionistaSeguimientoMixin(LoginRequiredMixin):
    """
    Mixin que filtra las queries por el nutricionista autenticado.
    Como MedidaCorporal y NotaClinica tienen FK a Paciente (que tiene FK a User),
    el filtro atraviesa la relación: paciente__nutricionista.
    """

    def get_queryset(self):
        return super().get_queryset().filter(
            paciente__nutricionista=self.request.user
        )

    def get_paciente(self):
        """Obtiene el paciente asegurando que pertenece al nutricionista."""
        paciente_pk = self.kwargs.get("paciente_pk")
        return get_object_or_404(
            Paciente, pk=paciente_pk, nutricionista=self.request.user
        )


# ═══════════════════════════════════════════════════════════════════════════════
# MEDIDAS CORPORALES
# ═══════════════════════════════════════════════════════════════════════════════


class MedidaCreateView(NutricionistaSeguimientoMixin, CreateView):
    """Registra una nueva medida corporal para un paciente específico."""

    model = MedidaCorporal
    form_class = MedidaCorporalForm
    template_name = "seguimiento/medida_form.html"

    def dispatch(self, request, *args, **kwargs):
        # Validamos que el paciente exista y pertenezca al nutricionista antes de continuar
        self.paciente = self.get_paciente()
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["paciente"] = self.paciente
        return context

    def form_valid(self, form):
        form.instance.paciente = self.paciente
        messages.success(
            self.request,
            f"Medidas registradas para {self.paciente.nombre_completo}.",
        )
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("seguimiento:medidas_lista", kwargs={"paciente_pk": self.paciente.pk})


class MedidaListView(NutricionistaSeguimientoMixin, ListView):
    """
    Historial de medidas corporales con indicadores de cambio.
    Cada fila muestra ▲ (mejora) o ▼ (empeora) respecto a la medición anterior.
    """

    model = MedidaCorporal
    template_name = "seguimiento/medidas.html"
    context_object_name = "medidas"
    paginate_by = 15

    def dispatch(self, request, *args, **kwargs):
        self.paciente = self.get_paciente()
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        # Traemos todas las medidas del paciente ordenadas por fecha descendente
        # Usamos select_related para evitar N+1 en la relación paciente
        return (
            super()
            .get_queryset()
            .filter(paciente=self.paciente)
            .select_related("paciente")
            .order_by("-fecha", "-fecha_registro")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["paciente"] = self.paciente

        # Generamos indicadores de cambio comparando cada medición con la anterior
        # Esto permite al nutricionista ver la evolución de un vistazo
        medidas = list(context["medidas"])
        cambios = []
        anterior = None
        for m in medidas:
            cambio = {
                "peso": self._comparar(m.peso_kg, anterior.peso_kg if anterior else None),
                "imc": self._comparar(m.imc, anterior.imc if anterior else None),
                "grasa": self._comparar(
                    m.grasa_corporal_pct, anterior.grasa_corporal_pct if anterior else None
                ),
                "cintura": self._comparar(m.cintura_cm, anterior.cintura_cm if anterior else None),
                "cadera": self._comparar(m.cadera_cm, anterior.cadera_cm if anterior else None),
            }
            cambios.append(cambio)
            anterior = m
        context["cambios"] = cambios

        # Última medida para resumen
        context["ultima_medida"] = medidas[0] if medidas else None
        # Primera medida para ver cambio total
        context["primera_medida"] = medidas[-1] if len(medidas) > 1 else None

        return context

    @staticmethod
    def _comparar(actual, anterior):
        """
        Compara dos valores y devuelve un indicador.
        None si no hay dato anterior. 'subio' o 'bajo' si hay cambio.
        En medidas corporales, subir peso/IMC/grasa generalmente es negativo
        y bajar es positivo, pero mostramos el dato objetivo sin juzgar.
        """
        if anterior is None or actual is None:
            return None
        if actual > anterior:
            return "subio"
        elif actual < anterior:
            return "bajo"
        return "igual"


# ═══════════════════════════════════════════════════════════════════════════════
# NOTAS CLÍNICAS
# ═══════════════════════════════════════════════════════════════════════════════


class NotaCreateView(NutricionistaSeguimientoMixin, CreateView):
    """Crea una nueva nota clínica para un paciente, opcionalmente vinculada a una cita."""

    model = NotaClinica
    form_class = NotaClinicaForm
    template_name = "seguimiento/nota_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.paciente = self.get_paciente()
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["paciente"] = self.paciente
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Pasamos el paciente al formulario para filtrar las citas disponibles
        kwargs["paciente"] = self.paciente
        return kwargs

    def form_valid(self, form):
        form.instance.paciente = self.paciente
        messages.success(
            self.request,
            f"Nota clínica '{form.instance.titulo}' creada para {self.paciente.nombre_completo}.",
        )
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("seguimiento:notas_lista", kwargs={"paciente_pk": self.paciente.pk})


class NotaListView(NutricionistaSeguimientoMixin, ListView):
    """Lista de notas clínicas de un paciente con filtro por tipo."""

    model = NotaClinica
    template_name = "seguimiento/notas.html"
    context_object_name = "notas"
    paginate_by = 15

    def dispatch(self, request, *args, **kwargs):
        self.paciente = self.get_paciente()
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        qs = super().get_queryset().filter(paciente=self.paciente)
        qs = qs.select_related("paciente", "cita")

        # Filtro opcional por tipo de nota
        tipo = self.request.GET.get("tipo", "")
        if tipo:
            qs = qs.filter(tipo=tipo)

        return qs.order_by("-fecha", "-fecha_creacion")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["paciente"] = self.paciente
        context["tipo_seleccionado"] = self.request.GET.get("tipo", "")
        context["tipos_nota"] = TipoNota.CHOICES
        return context


class NotaDetailView(NutricionistaSeguimientoMixin, DetailView):
    """Muestra el detalle completo de una nota clínica."""

    model = NotaClinica
    template_name = "seguimiento/nota_detalle.html"
    context_object_name = "nota"

    def get_queryset(self):
        # select_related para evitar N+1 queries al mostrar paciente y cita
        return super().get_queryset().select_related("paciente", "cita")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Si la nota está vinculada a una cita, pasamos datos extra
        if self.object.cita:
            context["cita"] = self.object.cita
        return context


# ═══════════════════════════════════════════════════════════════════════════════
# HISTORIAL DEL PACIENTE (Timeline)
# ═══════════════════════════════════════════════════════════════════════════════


@login_required
def historial_paciente(request, paciente_pk):
    """
    Timeline cronológico que unifica medidas, notas y citas del paciente.
    Muestra todo el historial ordenado por fecha descendente para una visión
    integral de la evolución del paciente.
    """
    # Verificar que el paciente pertenece al nutricionista
    paciente = get_object_or_404(
        Paciente, pk=paciente_pk, nutricionista=request.user
    )

    # Obtenemos medidas, notas y citas con type hint para el template
    medidas = MedidaCorporal.objects.filter(paciente=paciente).order_by("-fecha", "-fecha_registro")
    notas = NotaClinica.objects.filter(paciente=paciente).select_related("cita").order_by("-fecha", "-fecha_creacion")
    citas = paciente.citas.select_related("paciente").order_by("-fecha_hora")

    # Construimos una lista unificada de eventos para el timeline
    # Cada evento tiene: fecha, tipo, objeto, y datos de visualización
    eventos = []

    for m in medidas:
        eventos.append({
            "fecha": m.fecha,
            "fecha_display": m.fecha.strftime("%d/%m/%Y"),
            "tipo": "medida",
            "icono": "activity",
            "color": "teal",
            "titulo": f"Medidas: {m.peso_kg} kg — IMC {m.imc}",
            "detalle": f"Cintura: {m.cintura_cm or '—'} cm | Cadera: {m.cadera_cm or '—'} cm",
            "url": None,
            "objeto": m,
        })

    for n in notas:
        eventos.append({
            "fecha": n.fecha,
            "fecha_display": n.fecha.strftime("%d/%m/%Y"),
            "tipo": "nota",
            "icono": "clipboard-list",
            "color": "indigo",
            "titulo": n.titulo,
            "detalle": n.get_tipo_display(),
            "url": reverse_lazy("seguimiento:notas_detalle", kwargs={"pk": n.pk}),
            "objeto": n,
        })

    for c in citas:
        eventos.append({
            "fecha": c.fecha_hora.date(),
            "fecha_display": c.fecha_hora.strftime("%d/%m/%Y %H:%M"),
            "tipo": "cita",
            "icono": "calendar",
            "color": "amber",
            "titulo": f"Cita: {c.get_tipo_display()}",
            "detalle": f"{c.get_estado_display()} · {c.duracion_minutos} min",
            "url": reverse_lazy("citas:detalle", kwargs={"pk": c.pk}),
            "objeto": c,
        })

    # Ordenar todos los eventos por fecha descendente
    eventos.sort(key=lambda e: e["fecha"], reverse=True)

    context = {
        "paciente": paciente,
        "eventos": eventos,
        "total_medidas": len(medidas),
        "total_notas": len(notas),
        "total_citas": len(citas),
    }
    return render(request, "seguimiento/historial.html", context)


# ═══════════════════════════════════════════════════════════════════════════════
# DASHBOARDS (vistas generales para el sidebar)
# ═══════════════════════════════════════════════════════════════════════════════


@login_required
def seguimiento_dashboard(request):
    """
    Vista general de seguimiento: lista todos los pacientes del nutricionista
    con su última medición registrada. Accesible desde el sidebar.
    """
    pacientes = Paciente.objects.filter(
        nutricionista=request.user, estado=True
    ).order_by("nombre", "apellido")

    # Para cada paciente, obtenemos la última medida
    pacientes_con_medidas = []
    for p in pacientes:
        ultima = MedidaCorporal.objects.filter(paciente=p).order_by("-fecha", "-fecha_registro").first()
        pacientes_con_medidas.append({
            "paciente": p,
            "ultima_medida": ultima,
        })

    context = {
        "pacientes_con_medidas": pacientes_con_medidas,
        "total_medidas": MedidaCorporal.objects.filter(
            paciente__nutricionista=request.user
        ).count(),
    }
    return render(request, "seguimiento/dashboard.html", context)


@login_required
def notas_dashboard(request):
    """
    Vista general de notas clínicas: muestra todas las notas del nutricionista,
    ordenadas por fecha descendente. Accesible desde el sidebar.
    """
    notas = NotaClinica.objects.filter(
        paciente__nutricionista=request.user
    ).select_related("paciente").order_by("-fecha", "-fecha_creacion")

    # Filtro por tipo
    tipo = request.GET.get("tipo", "")
    if tipo:
        notas = notas.filter(tipo=tipo)

    context = {
        "notas": notas,
        "tipo_seleccionado": tipo,
    }
    return render(request, "seguimiento/notas_dashboard.html", context)
