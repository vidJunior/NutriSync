# nutricion/views.py
# Vistas del módulo de planes nutricionales y catálogo de alimentos.
# Todas las queries de planes filtran por paciente__nutricionista=request.user
# para garantizar el aislamiento de datos entre nutricionistas (multi-tenant).

from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.views.generic import ListView, CreateView, DetailView, UpdateView
from django.urls import reverse_lazy, reverse
from django.db.models import Q
from pacientes.models import Paciente
from .models import Alimento, PlanNutricional, ComidaPlan, CategoriaAlimento
from .forms import AlimentoForm, PlanNutricionalForm, ComidaPlanForm
from config.choices import DiaSemana


# ─── Orden canónico de días de semana ────────────────────────────────────────
# Definimos el orden lunes→domingo para organizar la vista del plan correctamente.
# Django ordena por el campo (alfabético), no por el orden lógico de la semana.
ORDEN_DIAS = [
    DiaSemana.LUNES,
    DiaSemana.MARTES,
    DiaSemana.MIERCOLES,
    DiaSemana.JUEVES,
    DiaSemana.VIERNES,
    DiaSemana.SABADO,
    DiaSemana.DOMINGO,
]


# ═══════════════════════════════════════════════════════════════════════════
#  CATÁLOGO DE ALIMENTOS
# ═══════════════════════════════════════════════════════════════════════════


class AlimentoListView(LoginRequiredMixin, ListView):
    """
    Catálogo de alimentos con búsqueda por nombre y filtro por categoría.
    No requiere filtro por nutricionista — el catálogo es compartido.
    Paginado a 30 para mostrar más alimentos sin romper la tabla.
    """

    model = Alimento
    template_name = "nutricion/alimentos.html"
    context_object_name = "alimentos"
    paginate_by = 30

    def get_queryset(self):
        qs = Alimento.objects.all()

        # Filtro por estado activo/inactivo
        estado = self.request.GET.get("estado", "activo")
        if estado == "activo":
            qs = qs.filter(estado=True)
        elif estado == "inactivo":
            qs = qs.filter(estado=False)

        # Filtro por categoría
        categoria = self.request.GET.get("categoria", "")
        if categoria:
            qs = qs.filter(categoria=categoria)

        # Búsqueda por nombre
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(nombre__icontains=q)

        return qs.order_by("nombre")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["q"] = self.request.GET.get("q", "")
        context["filtro_categoria"] = self.request.GET.get("categoria", "")
        context["filtro_estado"] = self.request.GET.get("estado", "activo")
        # Pasamos las categorías para el selector de filtro
        context["categorias"] = CategoriaAlimento.choices
        context["total_alimentos"] = Alimento.objects.filter(estado=True).count()
        return context


class AlimentoCreateView(LoginRequiredMixin, CreateView):
    """Vista para agregar un nuevo alimento al catálogo."""

    model = Alimento
    form_class = AlimentoForm
    template_name = "nutricion/alimento_form.html"
    success_url = reverse_lazy("nutricion:alimentos")

    def form_valid(self, form):
        messages.success(
            self.request,
            f"Alimento «{form.instance.nombre}» agregado al catálogo correctamente.",
        )
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["titulo"] = "Agregar Alimento"
        context["accion"] = "Agregar"
        return context


class AlimentoUpdateView(LoginRequiredMixin, UpdateView):
    """Vista para editar los datos nutricionales de un alimento."""

    model = Alimento
    form_class = AlimentoForm
    template_name = "nutricion/alimento_form.html"
    success_url = reverse_lazy("nutricion:alimentos")

    def form_valid(self, form):
        messages.success(
            self.request,
            f"Alimento «{form.instance.nombre}» actualizado correctamente.",
        )
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["titulo"] = "Editar Alimento"
        context["accion"] = "Guardar cambios"
        return context


# ═══════════════════════════════════════════════════════════════════════════
#  PLANES NUTRICIONALES
# ═══════════════════════════════════════════════════════════════════════════


class PlanListView(LoginRequiredMixin, ListView):
    """
    Lista de todos los planes nutricionales del nutricionista.
    Filtramos por paciente__nutricionista para aislamiento de datos.
    """

    model = PlanNutricional
    template_name = "nutricion/planes.html"
    context_object_name = "planes"
    paginate_by = 20

    def get_queryset(self):
        # select_related evita N+1 al mostrar paciente y sus datos en la lista
        qs = PlanNutricional.objects.select_related("paciente").filter(
            paciente__nutricionista=self.request.user
        )
        estado = self.request.GET.get("estado", "")
        if estado == "activo":
            qs = qs.filter(estado=True)
        elif estado == "inactivo":
            qs = qs.filter(estado=False)

        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(nombre__icontains=q)
                | Q(paciente__nombre__icontains=q)
                | Q(paciente__apellido__icontains=q)
            )
        return qs.order_by("-fecha_creacion")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["q"] = self.request.GET.get("q", "")
        context["filtro_estado"] = self.request.GET.get("estado", "")
        # Pasamos los pacientes activos del nutricionista para el empty state
        # Permite crear un plan directamente desde esta página sin ir a la ficha
        context["pacientes_disponibles"] = Paciente.objects.filter(
            nutricionista=self.request.user, estado=True
        ).order_by("apellido", "nombre")
        return context


class PlanCreateView(LoginRequiredMixin, CreateView):
    """
    Crea un plan nutricional para un paciente específico.
    El paciente_pk viene de la URL, garantizando que la vista
    siempre sabe a qué paciente pertenece el plan.
    """

    model = PlanNutricional
    form_class = PlanNutricionalForm
    template_name = "nutricion/plan_form.html"

    def get_paciente(self):
        """Obtiene el paciente y verifica que pertenezca al nutricionista autenticado."""
        # get_object_or_404 con filtro de nutricionista: devuelve 404 si el paciente
        # no existe o no pertenece al profesional autenticado.
        return get_object_or_404(
            Paciente, pk=self.kwargs["paciente_pk"], nutricionista=self.request.user
        )

    def get_form_kwargs(self):
        """Pasa el paciente al formulario para validar la regla de un solo plan activo."""
        kwargs = super().get_form_kwargs()
        kwargs["paciente"] = self.get_paciente()
        return kwargs

    def form_valid(self, form):
        # Asignamos el paciente automáticamente — no puede ser modificado por el usuario
        form.instance.paciente = self.get_paciente()
        response = super().form_valid(form)
        messages.success(
            self.request,
            f"Plan «{self.object.nombre}» creado correctamente para {self.object.paciente.nombre_completo}.",
        )
        return response

    def get_success_url(self):
        return reverse("nutricion:plan_detalle", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["paciente"] = self.get_paciente()
        context["titulo"] = "Nuevo Plan Nutricional"
        context["accion"] = "Crear plan"
        return context


class PlanDetailView(LoginRequiredMixin, DetailView):
    """
    Vista detallada del plan nutricional organizada por días de la semana.
    Prefetch de comidas y alimentos para evitar múltiples queries.
    """

    model = PlanNutricional
    template_name = "nutricion/plan_detalle.html"
    context_object_name = "plan"

    def get_queryset(self):
        # Aislamiento: solo planes de pacientes del nutricionista autenticado
        return PlanNutricional.objects.select_related("paciente").filter(
            paciente__nutricionista=self.request.user
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        plan = self.object

        # prefetch_related evita N+1 al cargar todas las comidas y sus alimentos
        comidas = plan.comidas.prefetch_related("alimentos_sugeridos").order_by(
            "dia_semana", "tipo_comida"
        )

        # Organizamos las comidas por día (lunes→domingo) para la template
        # Usamos el orden canónico definido en ORDEN_DIAS
        comidas_por_dia = {}
        for dia_key in ORDEN_DIAS:
            comidas_dia = [c for c in comidas if c.dia_semana == dia_key]
            if comidas_dia:
                # Obtenemos el label del día desde los choices
                dia_label = dict(DiaSemana.CHOICES).get(dia_key, dia_key)
                comidas_por_dia[dia_label] = comidas_dia

        context["comidas_por_dia"] = comidas_por_dia
        context["total_comidas"] = comidas.count()

        # Calorías totales estimadas (suma de todas las comidas del plan)
        calorias_total = sum(c.calorias_estimadas for c in comidas)
        context["calorias_total_plan"] = calorias_total

        # Formulario para agregar comidas directamente desde el detalle del plan
        context["comida_form"] = ComidaPlanForm()
        return context


class PlanUpdateView(LoginRequiredMixin, UpdateView):
    """Edición de los datos generales del plan nutricional."""

    model = PlanNutricional
    form_class = PlanNutricionalForm
    template_name = "nutricion/plan_form.html"

    def get_queryset(self):
        # Aislamiento: solo planes de pacientes del nutricionista autenticado
        return PlanNutricional.objects.select_related("paciente").filter(
            paciente__nutricionista=self.request.user
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["paciente"] = self.object.paciente
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request, f"Plan «{self.object.nombre}» actualizado correctamente."
        )
        return response

    def get_success_url(self):
        return reverse("nutricion:plan_detalle", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["paciente"] = self.object.paciente
        context["titulo"] = "Editar Plan Nutricional"
        context["accion"] = "Guardar cambios"
        return context


# ─── Activar / desactivar plan ───────────────────────────────────────────────


@login_required
@require_POST
def plan_toggle_estado(request, pk):
    """
    Activa o desactiva un plan nutricional.
    Al activar, desactiva automáticamente los otros planes activos del paciente
    para garantizar la regla: un solo plan activo por paciente.
    """
    # get_object_or_404 con filtro de nutricionista en cascada via paciente
    plan = get_object_or_404(
        PlanNutricional, pk=pk, paciente__nutricionista=request.user
    )

    if not plan.estado:
        # Activando: primero desactivamos todos los planes activos del paciente
        # Regla de negocio: un paciente solo puede tener un plan activo a la vez
        PlanNutricional.objects.filter(paciente=plan.paciente, estado=True).update(
            estado=False
        )
        plan.estado = True
        plan.save()
        messages.success(
            request,
            f"Plan «{plan.nombre}» activado. Los otros planes del paciente fueron desactivados.",
        )
    else:
        plan.estado = False
        plan.save()
        messages.success(request, f"Plan «{plan.nombre}» desactivado correctamente.")

    return redirect("nutricion:plan_detalle", pk=plan.pk)


# ─── Agregar comida al plan ───────────────────────────────────────────────────


@login_required
@require_POST
def comida_crear(request, plan_pk):
    """
    Agrega una nueva comida a un plan nutricional existente.
    FBV porque la lógica es simple y no requiere el overhead de una CBV.
    """
    plan = get_object_or_404(
        PlanNutricional, pk=plan_pk, paciente__nutricionista=request.user
    )
    form = ComidaPlanForm(request.POST)

    if form.is_valid():
        comida = form.save(commit=False)
        comida.plan = plan
        comida.save()
        # Guardamos las relaciones ManyToMany después del save
        form.save_m2m()
        messages.success(
            request,
            f"Comida «{comida.get_tipo_comida_display()}» del {comida.get_dia_semana_display()} agregada correctamente.",
        )
    else:
        # Enviamos errores como mensaje para mostrarlos en la template
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"{error}")

    return redirect("nutricion:plan_detalle", pk=plan_pk)


@login_required
@require_POST
def comida_eliminar(request, pk):
    """Elimina una comida de un plan nutricional."""
    comida = get_object_or_404(
        ComidaPlan, pk=pk, plan__paciente__nutricionista=request.user
    )
    plan_pk = comida.plan.pk
    nombre = f"{comida.get_tipo_comida_display()} del {comida.get_dia_semana_display()}"
    comida.delete()
    messages.success(request, f"Comida «{nombre}» eliminada correctamente.")
    return redirect("nutricion:plan_detalle", pk=plan_pk)


# ─── Fixtures: cargar alimentos de ejemplo ───────────────────────────────────


@login_required
def cargar_alimentos_ejemplo(request):
    """
    Vista de utilidad para cargar los 20+ alimentos de ejemplo en la BD.
    Solo disponible para superusuarios.
    Alternativa al fixture JSON para simplificar el proceso de setup.
    """
    if not request.user.is_superuser:
        messages.error(
            request, "Solo el superusuario puede cargar los datos de ejemplo."
        )
        return redirect("nutricion:alimentos")

    alimentos_iniciales = [
        # Cereales
        {
            "nombre": "Arroz blanco cocido",
            "categoria": "cereales",
            "calorias_100g": 130,
            "proteinas_100g": 2.7,
            "carbohidratos_100g": 28.2,
            "grasas_100g": 0.3,
            "fibra_100g": 0.4,
            "porcion_referencia": "1 taza (186g)",
        },
        {
            "nombre": "Avena cocida",
            "categoria": "cereales",
            "calorias_100g": 71,
            "proteinas_100g": 2.5,
            "carbohidratos_100g": 12,
            "grasas_100g": 1.5,
            "fibra_100g": 1.7,
            "porcion_referencia": "1 taza (234g)",
        },
        {
            "nombre": "Pan integral",
            "categoria": "cereales",
            "calorias_100g": 247,
            "proteinas_100g": 9,
            "carbohidratos_100g": 47,
            "grasas_100g": 3.4,
            "fibra_100g": 6.4,
            "porcion_referencia": "1 rebanada (28g)",
        },
        {
            "nombre": "Quinoa cocida",
            "categoria": "cereales",
            "calorias_100g": 120,
            "proteinas_100g": 4.4,
            "carbohidratos_100g": 21.3,
            "grasas_100g": 1.9,
            "fibra_100g": 2.8,
            "porcion_referencia": "1 taza (185g)",
        },
        # Lácteos
        {
            "nombre": "Leche descremada",
            "categoria": "lacteos",
            "calorias_100g": 35,
            "proteinas_100g": 3.4,
            "carbohidratos_100g": 4.9,
            "grasas_100g": 0.1,
            "fibra_100g": 0,
            "porcion_referencia": "1 vaso (240ml)",
        },
        {
            "nombre": "Yogur natural sin azúcar",
            "categoria": "lacteos",
            "calorias_100g": 59,
            "proteinas_100g": 3.5,
            "carbohidratos_100g": 4.7,
            "grasas_100g": 3.3,
            "fibra_100g": 0,
            "porcion_referencia": "1 porción (150g)",
        },
        {
            "nombre": "Queso fresco",
            "categoria": "lacteos",
            "calorias_100g": 98,
            "proteinas_100g": 11,
            "carbohidratos_100g": 2,
            "grasas_100g": 5,
            "fibra_100g": 0,
            "porcion_referencia": "1 rebanada (30g)",
        },
        # Carnes
        {
            "nombre": "Pechuga de pollo cocida",
            "categoria": "carnes",
            "calorias_100g": 165,
            "proteinas_100g": 31,
            "carbohidratos_100g": 0,
            "grasas_100g": 3.6,
            "fibra_100g": 0,
            "porcion_referencia": "1 porción (120g)",
        },
        {
            "nombre": "Carne de res magra",
            "categoria": "carnes",
            "calorias_100g": 218,
            "proteinas_100g": 26,
            "carbohidratos_100g": 0,
            "grasas_100g": 12,
            "fibra_100g": 0,
            "porcion_referencia": "1 porción (100g)",
        },
        {
            "nombre": "Pavo molido cocido",
            "categoria": "carnes",
            "calorias_100g": 189,
            "proteinas_100g": 27,
            "carbohidratos_100g": 0,
            "grasas_100g": 8.5,
            "fibra_100g": 0,
            "porcion_referencia": "1 porción (100g)",
        },
        # Pescados
        {
            "nombre": "Salmón cocido",
            "categoria": "pescados",
            "calorias_100g": 208,
            "proteinas_100g": 20,
            "carbohidratos_100g": 0,
            "grasas_100g": 13,
            "fibra_100g": 0,
            "porcion_referencia": "1 filete (180g)",
        },
        {
            "nombre": "Atún en agua (lata)",
            "categoria": "pescados",
            "calorias_100g": 116,
            "proteinas_100g": 25.5,
            "carbohidratos_100g": 0,
            "grasas_100g": 1,
            "fibra_100g": 0,
            "porcion_referencia": "1 lata (140g)",
        },
        # Huevos
        {
            "nombre": "Huevo entero cocido",
            "categoria": "huevos",
            "calorias_100g": 155,
            "proteinas_100g": 13,
            "carbohidratos_100g": 1.1,
            "grasas_100g": 11,
            "fibra_100g": 0,
            "porcion_referencia": "1 unidad grande (50g)",
        },
        # Legumbres
        {
            "nombre": "Lentejas cocidas",
            "categoria": "legumbres",
            "calorias_100g": 116,
            "proteinas_100g": 9,
            "carbohidratos_100g": 20,
            "grasas_100g": 0.4,
            "fibra_100g": 7.9,
            "porcion_referencia": "1 taza (198g)",
        },
        {
            "nombre": "Garbanzos cocidos",
            "categoria": "legumbres",
            "calorias_100g": 164,
            "proteinas_100g": 8.9,
            "carbohidratos_100g": 27,
            "grasas_100g": 2.6,
            "fibra_100g": 7.6,
            "porcion_referencia": "1 taza (164g)",
        },
        # Verduras
        {
            "nombre": "Brócoli cocido",
            "categoria": "verduras",
            "calorias_100g": 35,
            "proteinas_100g": 2.4,
            "carbohidratos_100g": 7.2,
            "grasas_100g": 0.4,
            "fibra_100g": 3.3,
            "porcion_referencia": "1 taza (156g)",
        },
        {
            "nombre": "Espinaca cruda",
            "categoria": "verduras",
            "calorias_100g": 23,
            "proteinas_100g": 2.9,
            "carbohidratos_100g": 3.6,
            "grasas_100g": 0.4,
            "fibra_100g": 2.2,
            "porcion_referencia": "1 taza (30g)",
        },
        {
            "nombre": "Zanahoria cruda",
            "categoria": "verduras",
            "calorias_100g": 41,
            "proteinas_100g": 0.9,
            "carbohidratos_100g": 9.6,
            "grasas_100g": 0.2,
            "fibra_100g": 2.8,
            "porcion_referencia": "1 unidad mediana (61g)",
        },
        # Frutas
        {
            "nombre": "Plátano",
            "categoria": "frutas",
            "calorias_100g": 89,
            "proteinas_100g": 1.1,
            "carbohidratos_100g": 23,
            "grasas_100g": 0.3,
            "fibra_100g": 2.6,
            "porcion_referencia": "1 unidad mediana (118g)",
        },
        {
            "nombre": "Manzana",
            "categoria": "frutas",
            "calorias_100g": 52,
            "proteinas_100g": 0.3,
            "carbohidratos_100g": 14,
            "grasas_100g": 0.2,
            "fibra_100g": 2.4,
            "porcion_referencia": "1 unidad mediana (182g)",
        },
        {
            "nombre": "Naranja",
            "categoria": "frutas",
            "calorias_100g": 47,
            "proteinas_100g": 0.9,
            "carbohidratos_100g": 12,
            "grasas_100g": 0.1,
            "fibra_100g": 2.4,
            "porcion_referencia": "1 unidad mediana (131g)",
        },
        # Grasas saludables
        {
            "nombre": "Aceite de oliva",
            "categoria": "grasas",
            "calorias_100g": 884,
            "proteinas_100g": 0,
            "carbohidratos_100g": 0,
            "grasas_100g": 100,
            "fibra_100g": 0,
            "porcion_referencia": "1 cucharada (14g)",
        },
        {
            "nombre": "Palta / Aguacate",
            "categoria": "grasas",
            "calorias_100g": 160,
            "proteinas_100g": 2,
            "carbohidratos_100g": 9,
            "grasas_100g": 15,
            "fibra_100g": 7,
            "porcion_referencia": "1/2 unidad (100g)",
        },
    ]

    creados = 0
    for data in alimentos_iniciales:
        # Evitamos duplicados — solo creamos si no existe con ese nombre
        if not Alimento.objects.filter(nombre__iexact=data["nombre"]).exists():
            Alimento.objects.create(**data)
            creados += 1

    if creados > 0:
        messages.success(
            request,
            f"{creados} alimentos de ejemplo cargados correctamente en el catálogo.",
        )
    else:
        messages.info(
            request, "Todos los alimentos de ejemplo ya estaban en el catálogo."
        )

    return redirect("nutricion:alimentos")
