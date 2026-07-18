from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.views.generic import ListView, CreateView, DetailView, UpdateView
from django.urls import reverse
from django.db.models import Q
from pacientes.models import Paciente
from ..models import PlanNutricional, ComidaPlan, Alimento
from ..forms import PlanNutricionalForm, ComidaPlanForm
from config.choices import DiaSemana, TipoComida, Objetivo

ORDEN_DIAS = [
    DiaSemana.LUNES,
    DiaSemana.MARTES,
    DiaSemana.MIERCOLES,
    DiaSemana.JUEVES,
    DiaSemana.VIERNES,
    DiaSemana.SABADO,
    DiaSemana.DOMINGO,
]

class PlanFormFragmentMixin:
    """Mixin para CreateView y UpdateView de Plan: renderiza fragmento cuando ?fragment=1."""

    def get_template_names(self):
        if self.request.GET.get("fragment"):
            return ["nutricion/_plan_form_content.html"]
        return super().get_template_names()

    def form_valid(self, form):
        from django.http import HttpResponse
        response = super().form_valid(form)
        is_ajax = (
            self.request.headers.get("X-Requested-With") == "XMLHttpRequest"
            or self.request.GET.get("fragment")
        )
        if is_ajax:
            return HttpResponse(
                '<div id="plan-form-success" data-success="true" data-pk="{}"></div>'.format(
                    self.object.pk
                )
            )
        return response

    def form_invalid(self, form):
        is_ajax = (
            self.request.headers.get("X-Requested-With") == "XMLHttpRequest"
            or self.request.GET.get("fragment")
        )
        if is_ajax:
            return self.render_to_response(self.get_context_data(form=form))
        return super().form_invalid(form)


class PlanListView(LoginRequiredMixin, ListView):
    """
    Lista de todos los modelos de planes nutricionales del nutricionista.
    """
    model = PlanNutricional
    template_name = "nutricion/planes.html"
    context_name = "planes"
    paginate_by = 20

    def get_queryset(self):
        qs = PlanNutricional.objects.filter(nutricionista=self.request.user)
        estado = self.request.GET.get("estado", "")
        if estado:
            qs = qs.filter(estado=estado)

        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(nombre__icontains=q)
                | Q(tipo_paciente__icontains=q)
                | Q(objetivo__icontains=q)
            )
        return qs.order_by("-fecha_creacion")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["planes"] = self.get_queryset()
        context["q"] = self.request.GET.get("q", "")
        context["filtro_estado"] = self.request.GET.get("estado", "")
        return context


class PlanCreateView(LoginRequiredMixin, PlanFormFragmentMixin, CreateView):
    """
    Crea un nuevo modelo de plan nutricional.
    """
    model = PlanNutricional
    form_class = PlanNutricionalForm
    template_name = "nutricion/plan_form.html"

    def form_valid(self, form):
        form.instance.nutricionista = self.request.user
        response = super().form_valid(form)
        messages.success(
            self.request,
            f"Modelo de plan «{self.object.nombre}» creado correctamente.",
        )
        return response

    def get_success_url(self):
        return reverse("nutricion:plan_detalle", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["titulo"] = "Nuevo Modelo de Plan"
        context["accion"] = "Crear modelo"
        return context


class PlanDetailView(LoginRequiredMixin, DetailView):
    """
    Vista detallada de un modelo de plan nutricional y sus comidas sugeridas.
    """
    model = PlanNutricional
    template_name = "nutricion/plan_detalle.html"
    context_object_name = "plan"

    def get_queryset(self):
        return PlanNutricional.objects.filter(nutricionista=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        plan = self.object
        comidas = plan.comidas.select_related("receta").order_by("hora_sugerida", "id")

        context["comidas"] = comidas
        context["total_comidas"] = comidas.count()
        context["comida_form"] = ComidaPlanForm(user=self.request.user)
        return context


class PlanUpdateView(LoginRequiredMixin, PlanFormFragmentMixin, UpdateView):
    """Edición de los datos generales de un modelo de plan."""
    model = PlanNutricional
    form_class = PlanNutricionalForm
    template_name = "nutricion/plan_form.html"

    def get_queryset(self):
        return PlanNutricional.objects.filter(nutricionista=self.request.user)

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request, f"Modelo de plan «{self.object.nombre}» actualizado correctamente."
        )
        return response

    def get_success_url(self):
        return reverse("nutricion:plan_detalle", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["titulo"] = "Editar Modelo de Plan"
        context["accion"] = "Guardar cambios"
        return context


@login_required
def plan_duplicar(request, pk):
    """
    Duplica un modelo de plan existente y todas sus comidas asociadas.
    """
    plan_orig = get_object_or_404(PlanNutricional, pk=pk, nutricionista=request.user)
    
    # Clonar metadatos del plan
    plan_orig.pk = None
    plan_orig.nombre = f"Copia de {plan_orig.nombre}"
    plan_orig.estado = 'Borrador'
    plan_orig.save()
    
    # Clonar comidas
    comidas_orig = ComidaPlan.objects.filter(plan_id=pk)
    for c in comidas_orig:
        c.pk = None
        c.plan = plan_orig
        c.save()
        
    messages.success(request, f"Modelo de plan duplicado como «{plan_orig.nombre}» en estado Borrador.")
    return redirect("nutricion:plan_detalle", pk=plan_orig.pk)


@login_required
@require_POST
def plan_toggle(request, pk):
    """
    Alterna el estado de un modelo de plan entre Activo y Borrador.
    """
    plan = get_object_or_404(PlanNutricional, pk=pk, nutricionista=request.user)
    if plan.estado == 'Activo':
        plan.estado = 'Borrador'
        messages.success(request, f"Modelo de plan «{plan.nombre}» desactivado.")
    else:
        plan.estado = 'Activo'
        messages.success(request, f"Modelo de plan «{plan.nombre}» activado.")
    plan.save()
    return redirect("nutricion:plan_detalle", pk=plan.pk)


@login_required
@require_POST
def plan_archivar(request, pk):
    """
    Archiva un modelo de plan nutricional.
    """
    plan = get_object_or_404(PlanNutricional, pk=pk, nutricionista=request.user)
    plan.estado = 'Archivado'
    plan.save()
    messages.success(request, f"Modelo de plan «{plan.nombre}» archivado correctamente.")
    return redirect("nutricion:plan_detalle", pk=plan.pk)



@login_required
@require_POST
def plan_eliminar(request, pk):
    """
    Elimina un modelo de plan nutricional.
    """
    plan = get_object_or_404(PlanNutricional, pk=pk, nutricionista=request.user)
    nombre = plan.nombre
    plan.delete()
    messages.success(request, f"Modelo de plan «{nombre}» eliminado correctamente.")
    return redirect("nutricion:planes")


@login_required
@require_POST
def comida_crear(request, plan_pk):
    """
    Agrega una nueva comida sugerida a un modelo de plan nutricional.
    """
    plan = get_object_or_404(PlanNutricional, pk=plan_pk, nutricionista=request.user)
    form = ComidaPlanForm(request.POST, user=request.user)

    if form.is_valid():
        comida = form.save(commit=False)
        comida.plan = plan
        comida.save()
        messages.success(
            request,
            f"Comida «{comida.tipo_comida}» agregada correctamente al modelo.",
        )
    else:
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"{error}")

    return redirect("nutricion:plan_detalle", pk=plan_pk)


@login_required
@require_POST
def comida_eliminar(request, pk):
    """Elimina una comida sugerida de un modelo de plan."""
    comida = get_object_or_404(ComidaPlan, pk=pk, plan__nutricionista=request.user)
    plan_pk = comida.plan.pk
    nombre = comida.tipo_comida
    comida.delete()
    messages.success(request, f"Comida «{nombre}» eliminada correctamente.")
    return redirect("nutricion:plan_detalle", pk=plan_pk)
