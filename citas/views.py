# citas/views.py
# Vistas para la gestión de citas en NutriSync — CRUD completo con aislamiento multi-nutricionista.

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.views.generic import ListView, CreateView, DetailView, UpdateView
from django.urls import reverse_lazy
from django.utils import timezone
from datetime import timedelta
from .models import Cita
from .forms import CitaForm
from config.choices import EstadoCita


class NutricionistaCitaMixin(LoginRequiredMixin):
    """Mixin base para todas las vistas de citas. Filtra datos por nutricionista."""

    def get_queryset(self):
        # Aislamiento multi-nutricionista seguro
        # Evitamos N+1 cargando paciente en la misma consulta
        return Cita.objects.filter(paciente__nutricionista=self.request.user).select_related("paciente")


# ─── Agenda / Listado de Citas ───────────────────────────────────────────────

class AgendaView(NutricionistaCitaMixin, ListView):
    """
    Lista las citas asociadas al nutricionista autenticado.
    Soporta filtros para visualización por Día, Semana y Próximas.
    """

    model = Cita
    template_name = "citas/agenda.html"
    context_object_name = "citas"

    def get_queryset(self):
        qs = super().get_queryset()
        hoy = timezone.localtime(timezone.now())
        fecha_hoy = hoy.date()
        
        # Filtro de tipo de vista
        self.vista = self.request.GET.get("vista", "proximas")

        if self.vista == "dia":
            # Solo citas de hoy
            qs = qs.filter(fecha_hora__date=fecha_hoy)
        elif self.vista == "semana":
            # Citas desde el inicio del día de hoy hasta dentro de 7 días
            fin_semana = fecha_hoy + timedelta(days=7)
            qs = qs.filter(fecha_hora__date__range=[fecha_hoy, fin_semana])
        else:
            # Por defecto: todas las citas futuras (de hoy en adelante)
            # o citas pendientes de hoy.
            inicio_hoy = hoy.replace(hour=0, minute=0, second=0, microsecond=0)
            qs = qs.filter(fecha_hora__gte=inicio_hoy)

        return qs.order_by("fecha_hora")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["vista"] = self.vista
        
        # Totales para los tabs / indicadores rápidos
        hoy = timezone.localtime(timezone.now()).date()
        qs_base = Cita.objects.filter(paciente__nutricionista=self.request.user)
        
        context["total_hoy"] = qs_base.filter(fecha_hora__date=hoy).count()
        context["total_semana"] = qs_base.filter(
            fecha_hora__date__range=[hoy, hoy + timedelta(days=7)]
        ).count()
        context["total_proximas"] = qs_base.filter(
            fecha_hora__gte=timezone.localtime(timezone.now()).replace(hour=0, minute=0, second=0, microsecond=0)
        ).count()
        
        return context


# ─── Crear Cita ──────────────────────────────────────────────────────────────

class CitaCreateView(LoginRequiredMixin, CreateView):
    """Permite agendar una nueva cita."""

    model = Cita
    form_class = CitaForm
    template_name = "citas/form.html"

    def get_form_kwargs(self):
        # Pasamos el usuario logueado al formulario para filtrar sus pacientes activos
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_success_url(self):
        messages.success(
            self.request,
            f"Cita con {self.object.paciente.nombre_completo} programada con éxito."
        )
        return reverse_lazy("citas:agenda")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from config.choices import TipoCita
        import json
        
        # Filtramos citas de tipo Primera Consulta para los pacientes de este nutricionista
        qs_primera = Cita.objects.filter(
            paciente__nutricionista=self.request.user,
            tipo=TipoCita.PRIMERA_CONSULTA
        )
        pacientes_con_primera = set(qs_primera.values_list("paciente_id", flat=True))
        context["tiene_primera_consulta_json"] = json.dumps({
            p_id: True for p_id in pacientes_con_primera
        })
        return context


# ─── Detalle de Cita ─────────────────────────────────────────────────────────

class CitaDetailView(NutricionistaCitaMixin, DetailView):
    """Muestra la ficha informativa y opciones rápidas para una cita específica."""

    model = Cita
    template_name = "citas/detalle.html"
    context_object_name = "cita"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Opciones de estados para el cambio rápido en el detalle
        context["estados"] = EstadoCita.CHOICES
        # "No asistió" solo debe estar disponible si la cita ya inició o pasó en el tiempo
        context["puede_marcar_no_asistio"] = self.object.fecha_hora and self.object.fecha_hora < timezone.now()
        return context


# ─── Editar Cita ─────────────────────────────────────────────────────────────

class CitaUpdateView(NutricionistaCitaMixin, UpdateView):
    """Permite modificar los datos de una cita existente."""

    model = Cita
    form_class = CitaForm
    template_name = "citas/form.html"

    def get_form_kwargs(self):
        # Pasamos el usuario logueado al formulario
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_success_url(self):
        messages.success(
            self.request,
            f"Cita con {self.object.paciente.nombre_completo} actualizada correctamente."
        )
        return reverse_lazy("citas:agenda")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from config.choices import TipoCita
        import json
        
        # Filtramos citas de tipo Primera Consulta para los pacientes de este nutricionista,
        # excluyendo la cita actual que estamos editando.
        qs_primera = Cita.objects.filter(
            paciente__nutricionista=self.request.user,
            tipo=TipoCita.PRIMERA_CONSULTA
        )
        if self.object and self.object.pk:
            qs_primera = qs_primera.exclude(pk=self.object.pk)
            
        pacientes_con_primera = set(qs_primera.values_list("paciente_id", flat=True))
        context["tiene_primera_consulta_json"] = json.dumps({
            p_id: True for p_id in pacientes_con_primera
        })
        return context


# ─── Cambio Rápido de Estado ──────────────────────────────────────────────────

@login_required
@require_POST
def cita_cambiar_estado(request, pk):
    """
    Permite cambiar rápidamente el estado de una cita (Completada, Cancelada, No asistió)
    desde botones de acción rápidos en la UI.
    """
    # Aislamiento multi-nutricionista: Solo puede modificar citas de sus pacientes
    cita = get_object_or_404(Cita, pk=pk, paciente__nutricionista=request.user)
    nuevo_estado = request.POST.get("estado")
    
    if nuevo_estado in dict(EstadoCita.CHOICES):
        # Validación de negocio: 'no_asistio' solo si ya pasó la fecha de inicio
        if nuevo_estado == EstadoCita.NO_ASISTIO and cita.fecha_hora > timezone.now():
            messages.error(request, "No se puede marcar como 'No asistió' una cita futura.")
            return redirect("citas:detalle", pk=cita.pk)

        cita.estado = nuevo_estado
        # Validamos y guardamos
        try:
            cita.save()
            messages.success(
                request,
                f"El estado de la cita ha sido cambiado a '{cita.get_estado_display()}'."
            )
        except Exception as e:
            messages.error(request, f"Error al actualizar el estado: {str(e)}")
    else:
        messages.error(request, "Estado de cita no válido.")
        
    return redirect("citas:detalle", pk=cita.pk)
