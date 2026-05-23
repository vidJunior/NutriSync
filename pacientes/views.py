# pacientes/views.py
# Vistas de gestión de pacientes — CRUD completo con aislamiento multi-nutricionista.
# Soporta renderizado de fragmentos (modal) vía ?fragment=1 para peticiones AJAX.

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.views.generic import ListView, CreateView, DetailView, UpdateView
from django.urls import reverse_lazy
from django.db.models import Q
from django.http import HttpResponse
from .models import Paciente
from .forms import PacienteForm


# ─── Mixin de aislamiento multi-nutricionista ────────────────────────────────
# Todas las vistas filtran por request.user para garantizar que un nutricionista
# NUNCA vea ni modifique pacientes de otro profesional.
# Si se elimina la arquitectura multi-tenant, basta con remover el filtro.

# Templates de fragmentos para el modal — sin extender base.html
FORM_FRAGMENT_TEMPLATE = "pacientes/_form_content.html"
DETAIL_FRAGMENT_TEMPLATE = "pacientes/_detalle_content.html"


class NutricionistaPacienteMixin(LoginRequiredMixin):
    """Mixin base para todas las vistas de pacientes. Aísla datos por nutricionista."""

    def get_queryset(self):
        # Filtramos por el nutricionista autenticado para aislamiento de datos.
        # Cada profesional solo ve sus propios pacientes.
        return super().get_queryset().filter(nutricionista=self.request.user)

    def get_template_names(self):
        # Si la petición trae ?fragment=1, renderizamos solo el fragmento (sin base.html)
        # para que el modal pueda inyectar el contenido vía fetch.
        if self.request.GET.get("fragment"):
            return [DETAIL_FRAGMENT_TEMPLATE]
        return super().get_template_names()


# ─── Lista de pacientes ──────────────────────────────────────────────────────


class PacienteListView(NutricionistaPacienteMixin, ListView):
    """Lista paginada (20 por página) con búsqueda por nombre, apellido o teléfono."""

    model = Paciente
    template_name = "pacientes/lista.html"
    context_object_name = "pacientes"
    paginate_by = 20  # Evita cargar todos los pacientes en memoria

    def get_queryset(self):
        qs = super().get_queryset()
        # Usamos .only() para traer solo los campos que la tabla necesita mostrar.
        # Reduce memoria y acelera la query.
        qs = qs.only("nombre", "apellido", "telefono", "email", "estado", "sexo")

        # Filtro por estado activo/inactivo
        estado = self.request.GET.get("estado", "")
        if estado == "activo":
            qs = qs.filter(estado=True)
        elif estado == "inactivo":
            qs = qs.filter(estado=False)

        # Búsqueda por nombre, apellido o teléfono
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(nombre__icontains=q)
                | Q(apellido__icontains=q)
                | Q(telefono__icontains=q)
            )

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["q"] = self.request.GET.get("q", "")
        context["filtro_estado"] = self.request.GET.get("estado", "")
        context["total_activos"] = (
            Paciente.objects.filter(nutricionista=self.request.user, estado=True)
            .only("id")
            .count()
        )
        context["total_inactivos"] = (
            Paciente.objects.filter(nutricionista=self.request.user, estado=False)
            .only("id")
            .count()
        )
        return context


# ─── Mixin para formularios (crear / editar) con soporte de fragmento ────────


class FormFragmentMixin:
    """Mixin para CreateView y UpdateView: renderiza fragmento cuando ?fragment=1."""

    def get_template_names(self):
        if self.request.GET.get("fragment"):
            return [FORM_FRAGMENT_TEMPLATE]
        return super().get_template_names()

    def form_valid(self, form):
        # Guardamos el objeto y notificamos éxito
        response = super().form_valid(form)
        # Si es petición AJAX (modal), devolvemos un marcador de éxito en lugar de redirect.
        # El JS del modal detecta este marcador y cierra el modal + refresca la lista.
        is_ajax = (
            self.request.headers.get("X-Requested-With") == "XMLHttpRequest"
            or self.request.GET.get("fragment")
        )
        if is_ajax:
            return HttpResponse(
                '<div id="paciente-form-success" data-success="true" data-pk="{}"></div>'.format(
                    self.object.pk
                )
            )
        return response

    def form_invalid(self, form):
        # Si el formulario tiene errores en modal, re-renderizamos el fragmento
        is_ajax = (
            self.request.headers.get("X-Requested-With") == "XMLHttpRequest"
            or self.request.GET.get("fragment")
        )
        if is_ajax:
            return render(
                self.request,
                FORM_FRAGMENT_TEMPLATE,
                {"form": form},
            )
        return super().form_invalid(form)


# ─── Crear paciente ──────────────────────────────────────────────────────────


class PacienteCreateView(FormFragmentMixin, LoginRequiredMixin, CreateView):
    """Formulario para registrar un nuevo paciente. Asigna automáticamente el nutricionista."""

    model = Paciente
    form_class = PacienteForm
    template_name = "pacientes/form.html"

    def get_success_url(self):
        messages.success(
            self.request, f"Paciente {self.object.nombre_completo} registrado correctamente."
        )
        return reverse_lazy("pacientes:detalle", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        # Asignamos el nutricionista autenticado automáticamente antes de guardar.
        # Esto evita que el usuario pueda asignar el paciente a otro profesional.
        form.instance.nutricionista = self.request.user
        return super().form_valid(form)


# ─── Ver detalle del paciente ────────────────────────────────────────────────


class PacienteDetailView(NutricionistaPacienteMixin, DetailView):
    """Ficha completa del paciente con todos sus datos personales y de salud."""

    model = Paciente
    template_name = "pacientes/detalle.html"
    context_object_name = "paciente"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        paciente = self.object

        # ─── Medidas Corporales ───
        try:
            from seguimiento.models import MedidaCorporal
            medidas_qs = MedidaCorporal.objects.filter(paciente=paciente).order_by('-fecha', '-fecha_registro')
            context['ultima_medida'] = medidas_qs.first()
            context['medidas_recientes'] = list(medidas_qs[:5])
        except Exception:
            context['ultima_medida'] = None
            context['medidas_recientes'] = []

        # ─── Plan Nutricional Activo ───
        try:
            from nutricion.models import PlanNutricional
            planes = PlanNutricional.objects.filter(paciente=paciente)
            context['plan_activo'] = planes.filter(estado=True).first()
            context['planes_count'] = planes.count()
        except Exception:
            context['plan_activo'] = None
            context['planes_count'] = 0

        # ─── Próxima Cita Programada ───
        try:
            from citas.models import Cita
            context['proxima_cita'] = Cita.objects.filter(
                paciente=paciente,
                estado='programada'
            ).order_by('fecha_hora').first()
        except Exception:
            context['proxima_cita'] = None

        # ─── Notas Clínicas Recientes ───
        try:
            from seguimiento.models import NotaClinica
            context['notas_recientes'] = list(
                NotaClinica.objects.filter(paciente=paciente).order_by('-fecha', '-fecha_creacion')[:5]
            )
        except Exception:
            context['notas_recientes'] = []

        return context


# ─── Editar paciente ─────────────────────────────────────────────────────────


class PacienteUpdateView(FormFragmentMixin, NutricionistaPacienteMixin, UpdateView):
    """Formulario para editar los datos de un paciente existente."""

    model = Paciente
    form_class = PacienteForm
    template_name = "pacientes/form.html"

    def get_initial(self):
        initial = super().get_initial()
        # Precargamos los campos de peso y talla con la medición física más reciente de su historial
        ultima_medida = self.object.medidas.order_by("-fecha", "-fecha_registro").first()
        if ultima_medida:
            initial["peso"] = ultima_medida.peso_kg
            initial["talla"] = ultima_medida.talla_cm
        return initial

    def get_success_url(self):
        messages.success(
            self.request,
            f"Datos de {self.object.nombre_completo} actualizados correctamente.",
        )
        return reverse_lazy("pacientes:detalle", kwargs={"pk": self.object.pk})


# ─── Activar / Desactivar paciente (soft-delete) ─────────────────────────────


@login_required
@require_POST
def paciente_toggle_estado(request, pk):
    """
    Activa o desactiva un paciente sin borrar sus datos (soft-delete).
    Un paciente inactivo no se muestra en búsquedas pero conserva todo su historial.
    """
    # get_object_or_404 con filtro de nutricionista: devuelve 404 si el paciente
    # no existe o no pertenece al profesional autenticado.
    paciente = get_object_or_404(Paciente, pk=pk, nutricionista=request.user)
    paciente.estado = not paciente.estado
    paciente.save()

    accion = "activado" if paciente.estado else "desactivado"
    messages.success(request, f"Paciente {paciente.nombre_completo} {accion} correctamente.")

    # Si es petición AJAX (desde modal), devolver respuesta simple
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return HttpResponse('<div id="paciente-toggle-success" data-success="true"></div>')

    return redirect("pacientes:detalle", pk=paciente.pk)
