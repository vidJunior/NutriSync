import json
from django.core.serializers.json import DjangoJSONEncoder
from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import ListView, CreateView, DetailView, UpdateView, DeleteView, View
from django.urls import reverse
from django.db.models import Q
from django.db import transaction
from django.http import JsonResponse
from pacientes.models import Paciente
from ..models import Receta, IngredienteReceta, Alimento
from ..forms import RecetaForm, IngredienteRecetaFormSet

class RecetaListView(LoginRequiredMixin, ListView):
    """
    Catálogo de recetas globales creadas por el nutricionista.
    Aislamiento multi-tenant garantizado.
    """
    model = Receta
    template_name = "nutricion/recetas.html"
    context_object_name = "recetas"
    paginate_by = 12

    def get_queryset(self):
        qs = Receta.objects.filter(
            creado_por=self.request.user, paciente__isnull=True
        )
            
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(nombre__icontains=q)
            
        categoria = self.request.GET.get("categoria", "")
        if categoria:
            qs = qs.filter(imagen_predeterminada=categoria)

        fecha_desde = self.request.GET.get("fecha_desde", "").strip()
        if fecha_desde:
            qs = qs.filter(fecha_creacion__date__gte=fecha_desde)
            
        fecha_hasta = self.request.GET.get("fecha_hasta", "").strip()
        if fecha_hasta:
            qs = qs.filter(fecha_creacion__date__lte=fecha_hasta)

        ordenar = self.request.GET.get("ordenar", "-fecha_creacion").strip()
        if ordenar in ["nombre", "fecha_creacion", "-fecha_creacion"]:
            qs = qs.order_by(ordenar)
        else:
            qs = qs.order_by("-fecha_creacion")

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["q"] = self.request.GET.get("q", "")
        context["filtro_categoria"] = self.request.GET.get("categoria", "")
        context["fecha_desde"] = self.request.GET.get("fecha_desde", "")
        context["fecha_hasta"] = self.request.GET.get("fecha_hasta", "")
        context["ordenar"] = self.request.GET.get("ordenar", "-fecha_creacion")
        context["total_recetas"] = Receta.objects.filter(
            creado_por=self.request.user, paciente__isnull=True
        ).count()
        return context


class RecetaCreateView(LoginRequiredMixin, CreateView):
    """Vista para crear una nueva receta con ingredientes dinámicos en formset."""
    model = Receta
    form_class = RecetaForm
    template_name = "nutricion/receta_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        paciente_id = self.request.GET.get("paciente_id")
        if paciente_id:
            paciente = get_object_or_404(Paciente, pk=paciente_id, nutricionista=self.request.user)
            context["paciente"] = paciente
            context["titulo"] = f"Crear receta para {paciente.nombre_completo}"
        else:
            context["titulo"] = "Crear Plantilla de Receta"

        if self.request.POST:
            context["ingredientes_formset"] = IngredienteRecetaFormSet(self.request.POST)
        else:
            context["ingredientes_formset"] = IngredienteRecetaFormSet()

        # Carga el catálogo para el selector.
        alimentos_list = list(
            Alimento.objects.filter(estado=True).values(
                "id", "nombre", "categoria", "calorias_100g", "proteinas_100g", "carbohidratos_100g", "grasas_100g", "fibra_100g"
            )
        )
        for a in alimentos_list:
            a["calorias_100g"] = float(a["calorias_100g"])
            a["proteinas_100g"] = float(a["proteinas_100g"])
            a["carbohidratos_100g"] = float(a["carbohidratos_100g"])
            a["grasas_100g"] = float(a["grasas_100g"])
            a["fibra_100g"] = float(a["fibra_100g"])

        context["alimentos_json"] = json.dumps(alimentos_list, cls=DjangoJSONEncoder)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        ingredientes_formset = context["ingredientes_formset"]

        if ingredientes_formset.is_valid():
            form.instance.creado_por = self.request.user
            
            paciente_id = self.request.GET.get("paciente_id")
            if paciente_id:
                paciente = get_object_or_404(Paciente, pk=paciente_id, nutricionista=self.request.user)
                form.instance.paciente = paciente
            
            # Obtiene las instrucciones del POST.
            pasos = self.request.POST.getlist("pasos_instrucciones")
            pasos_limpios = [p.strip() for p in pasos if p.strip()]
            form.instance.instrucciones = pasos_limpios

            with transaction.atomic():
                self.object = form.save()
                ingredientes_formset.instance = self.object
                ingredientes_formset.save()

            messages.success(
                self.request,
                f"Receta «{self.object.nombre}» creada correctamente.",
            )
            
            if form.instance.paciente:
                return redirect(reverse("pacientes:detalle", kwargs={"pk": form.instance.paciente.pk}) + "?tab=recetas")
            return redirect(reverse("nutricion:recetas"))
        else:
            return self.render_to_response(self.get_context_data(form=form))


class RecetaUpdateView(LoginRequiredMixin, UpdateView):
    """Edita una receta y sus ingredientes usando inline formsets."""
    model = Receta
    form_class = RecetaForm
    template_name = "nutricion/receta_form.html"

    def get_queryset(self):
        return Receta.objects.filter(creado_por=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        receta = self.get_object()
        
        paciente_id = self.request.GET.get("paciente_id") or (receta.paciente.pk if receta.paciente else None)
        if paciente_id:
            paciente = get_object_or_404(Paciente, pk=paciente_id, nutricionista=self.request.user)
            context["paciente"] = paciente
            context["titulo"] = f"Editar receta de {paciente.nombre_completo}"
        else:
            context["titulo"] = f"Editar Plantilla «{receta.nombre}»"

        if self.request.POST:
            context["ingredientes_formset"] = IngredienteRecetaFormSet(
                self.request.POST, instance=self.object
            )
        else:
            context["ingredientes_formset"] = IngredienteRecetaFormSet(
                instance=self.object
            )

        # Carga el catálogo para el selector.
        alimentos_list = list(
            Alimento.objects.filter(estado=True).values(
                "id", "nombre", "categoria", "calorias_100g", "proteinas_100g", "carbohidratos_100g", "grasas_100g", "fibra_100g"
            )
        )
        for a in alimentos_list:
            a["calorias_100g"] = float(a["calorias_100g"])
            a["proteinas_100g"] = float(a["proteinas_100g"])
            a["carbohidratos_100g"] = float(a["carbohidratos_100g"])
            a["grasas_100g"] = float(a["grasas_100g"])
            a["fibra_100g"] = float(a["fibra_100g"])

        context["alimentos_json"] = json.dumps(alimentos_list, cls=DjangoJSONEncoder)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        ingredientes_formset = context["ingredientes_formset"]

        if ingredientes_formset.is_valid():
            paciente_id = self.request.GET.get("paciente_id")
            if paciente_id:
                paciente = get_object_or_404(Paciente, pk=paciente_id, nutricionista=self.request.user)
                form.instance.paciente = paciente

            # Obtiene las instrucciones del POST.
            pasos = self.request.POST.getlist("pasos_instrucciones")
            pasos_limpios = [p.strip() for p in pasos if p.strip()]
            form.instance.instrucciones = pasos_limpios
                
            with transaction.atomic():
                self.object = form.save()
                ingredientes_formset.save()

            messages.success(
                self.request,
                f"Receta «{self.object.nombre}» actualizada correctamente.",
            )
            
            if form.instance.paciente:
                return redirect(reverse("pacientes:detalle", kwargs={"pk": form.instance.paciente.pk}) + "?tab=recetas")
            return redirect(reverse("nutricion:recetas"))
        else:
            return self.form_invalid(form)


class RecetaDetailView(LoginRequiredMixin, DetailView):
    """Muestra la receta, ingredientes con porciones y desglose de macros."""
    model = Receta
    template_name = "nutricion/receta_detalle.html"
    context_object_name = "receta"

    def get_queryset(self):
        return Receta.objects.filter(
            Q(es_sistema=True) | Q(creado_por=self.request.user)
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["ingredientes_list"] = self.object.ingredientes.select_related("alimento").all()
        paciente_id = self.request.GET.get("paciente_id") or (self.object.paciente.pk if self.object.paciente else None)
        if paciente_id:
            context["paciente_id"] = paciente_id
        return context


class RecetaDeleteView(LoginRequiredMixin, DeleteView):
    """Elimina una receta del catálogo del nutricionista."""
    model = Receta

    def get_queryset(self):
        return Receta.objects.filter(creado_por=self.request.user, es_sistema=False)

    def get_success_url(self):
        paciente = self.object.paciente
        if paciente:
            return reverse("pacientes:detalle", kwargs={"pk": paciente.pk}) + "?tab=recetas"
        return reverse("nutricion:recetas")

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        nombre = self.object.nombre
        success_url = self.get_success_url()
        self.object.delete()
        messages.success(request, f"Receta «{nombre}» eliminada correctamente.")
        return redirect(success_url)


class RecetaImportarView(LoginRequiredMixin, View):
    """Clona una receta global (plantilla) para convertirla en una receta específica de un paciente."""
    def post(self, request, pk, *args, **kwargs):
        paciente_id = request.POST.get("paciente_id") or request.GET.get("paciente_id")
        if not paciente_id:
            messages.error(request, "Se requiere especificar un paciente para importar la receta.")
            return redirect("nutricion:recetas")
            
        paciente = get_object_or_404(Paciente, pk=paciente_id, nutricionista=request.user)
        receta_original = get_object_or_404(
            Receta,
            Q(pk=pk) & (Q(es_sistema=True) | Q(creado_por=request.user)) & Q(paciente__isnull=True)
        )
        
        with transaction.atomic():
            receta_clon = Receta.objects.create(
                nombre=receta_original.nombre,
                descripcion=receta_original.descripcion,
                instrucciones=receta_original.instrucciones,
                tiempo_preparacion=receta_original.tiempo_preparacion,
                porciones=receta_original.porciones,
                creado_por=request.user,
                paciente=paciente,
                es_sistema=False,
                imagen_predeterminada=receta_original.imagen_predeterminada
            )
            for ing in receta_original.ingredientes.all():
                IngredienteReceta.objects.create(
                    receta=receta_clon,
                    alimento=ing.alimento,
                    cantidad=ing.cantidad,
                    nota=ing.nota
                )
                
        messages.success(request, f"Plantilla «{receta_original.nombre}» importada correctamente para {paciente.nombre_completo}.")
        return redirect(reverse("pacientes:detalle", kwargs={"pk": paciente.pk}) + "?tab=recetas")


@login_required
def api_buscar_alimentos(request):
    """Endpoint JSON para la búsqueda rápida de alimentos con autocompletado en el frontend."""
    q = request.GET.get("q", "").strip()
    if len(q) < 2:
        return JsonResponse({"success": True, "resultados": []})

    alimentos = Alimento.objects.filter(
        estado=True, nombre__icontains=q
    )[:10]

    resultados = []
    for a in alimentos:
        resultados.append({
            "id": a.id,
            "nombre": a.nombre,
            "categoria": a.get_categoria_display(),
            "calorias_100g": float(a.calorias_100g),
            "proteinas_100g": float(a.proteinas_100g),
            "carbohidratos_100g": float(a.carbohidratos_100g),
            "grasas_100g": float(a.grasas_100g),
            "fibra_100g": float(a.fibra_100g),
        })

    return JsonResponse({"success": True, "resultados": resultados})
