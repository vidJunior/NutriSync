# nutricion/views.py
# Vistas del módulo de planes nutricionales y catálogo de alimentos.
# Todas las queries de planes filtran por paciente__nutricionista=request.user
# para garantizar el aislamiento de datos entre nutricionistas (multi-tenant).

from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.views.generic import ListView, CreateView, DetailView, UpdateView, DeleteView, View
from django.urls import reverse_lazy, reverse
from django.db.models import Q
from django.db import transaction
from django.http import JsonResponse
from pacientes.models import Paciente
from .models import Alimento, PlanNutricional, ComidaPlan, CategoriaAlimento, Receta, IngredienteReceta
from .forms import AlimentoForm, PlanNutricionalForm, ComidaPlanForm, RecetaForm, IngredienteRecetaFormSet
from config.choices import DiaSemana, TipoComida



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
        context["comida_form"] = ComidaPlanForm(user=self.request.user, plan=plan)
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
    form = ComidaPlanForm(request.POST, user=request.user, plan=plan)

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
"fibra_100g": 7,
            "porcion_referencia": "1/2 unidad (100g)",
        },
    ]

    if not request.user.is_superuser:
        messages.error(
            request, "Esta acción solo está disponible para superusuarios."
        )
        return redirect("nutricion:alimentos")

    # Cargar alimentos si no existen
    cargados = 0
    for data in alimentos_iniciales:
        if not Alimento.objects.filter(nombre__iexact=data["nombre"]).exists():
            Alimento.objects.create(**data)
            cargados += 1

    messages.success(
        request,
        f"Se cargaron {cargados} alimentos de ejemplo en la base de datos.",
    )
    return redirect("nutricion:alimentos")


# ═══════════════════════════════════════════════════════════════════════════
#  CRUD DE RECETAS Y VISTAS DE INTERFAZ
# ═══════════════════════════════════════════════════════════════════════════

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
        # Solo mostramos las plantillas de recetas globales del nutricionista actual
        qs = Receta.objects.filter(
            creado_por=self.request.user, paciente__isnull=True
        )
            
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(nombre__icontains=q)
            
        categoria = self.request.GET.get("categoria", "")
        if categoria:
            qs = qs.filter(imagen_predeterminada=categoria)

        # Filtrar por rango de fechas de creación
        fecha_desde = self.request.GET.get("fecha_desde", "").strip()
        if fecha_desde:
            qs = qs.filter(fecha_creacion__date__gte=fecha_desde)
            
        fecha_hasta = self.request.GET.get("fecha_hasta", "").strip()
        if fecha_hasta:
            qs = qs.filter(fecha_creacion__date__lte=fecha_hasta)

        # Ordenar queryset (por defecto: más recientes primero)
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
    """Crea una nueva receta asociándole ingredientes a través del inline formset."""
    model = Receta
    form_class = RecetaForm
    template_name = "nutricion/receta_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_success_url(self):
        paciente_id = self.request.GET.get("paciente_id")
        if paciente_id:
            return reverse("pacientes:detalle", kwargs={"pk": paciente_id}) + "?tab=recetas"
        return reverse("nutricion:recetas")

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data["ingredientes_formset"] = IngredienteRecetaFormSet(self.request.POST)
        else:
            data["ingredientes_formset"] = IngredienteRecetaFormSet()
        
        paciente_id = self.request.GET.get("paciente_id")
        if paciente_id:
            from pacientes.models import Paciente
            paciente = get_object_or_404(Paciente, pk=paciente_id, nutricionista=self.request.user)
            data["paciente"] = paciente
            data["titulo"] = f"Crear receta para {paciente.nombre_completo}"
        else:
            data["titulo"] = "Crear nueva receta"
            
        data["accion"] = "Publicar receta"
        
        # Pasamos el catálogo completo de alimentos en JSON para el selector dinámico
        import json
        from django.core.serializers.json import DjangoJSONEncoder
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

        data["alimentos_json"] = json.dumps(alimentos_list, cls=DjangoJSONEncoder)
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context["ingredientes_formset"]
        paciente = context.get("paciente")
        
        if formset.is_valid():
            with transaction.atomic():
                form.instance.creado_por = self.request.user
                if paciente:
                    form.instance.paciente = paciente
                
                # Obtener las instrucciones dinámicas del POST (lista de strings)
                pasos = self.request.POST.getlist("pasos_instrucciones")
                pasos_limpios = [p.strip() for p in pasos if p.strip()]
                form.instance.instrucciones = pasos_limpios

                self.object = form.save()
                formset.instance = self.object
                formset.save()
                
            messages.success(self.request, f"Receta «{self.object.nombre}» creada correctamente.")
            return redirect(self.get_success_url())
        else:
            return self.form_invalid(form)


class RecetaUpdateView(LoginRequiredMixin, UpdateView):
    """Edita los datos básicos e ingredientes de una receta existente."""
    model = Receta
    form_class = RecetaForm
    template_name = "nutricion/receta_form.html"

    def get_queryset(self):
        # Aislamiento: Solo puede editar sus propias recetas, no las de otros ni las de sistema
        return Receta.objects.filter(creado_por=self.request.user, es_sistema=False)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_success_url(self):
        paciente = self.object.paciente
        if paciente:
            return reverse("pacientes:detalle", kwargs={"pk": paciente.pk}) + "?tab=recetas"
        return reverse("nutricion:recetas")

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data["ingredientes_formset"] = IngredienteRecetaFormSet(self.request.POST, instance=self.object)
        else:
            data["ingredientes_formset"] = IngredienteRecetaFormSet(instance=self.object)
        
        paciente = self.object.paciente
        if paciente:
            data["paciente"] = paciente
            data["titulo"] = f"Editar receta de {paciente.nombre_completo}"
        else:
            data["titulo"] = "Editar receta"
            
        data["accion"] = "Guardar cambios"
        
        # Pasamos el catálogo completo de alimentos en JSON para el selector dinámico
        import json
        from django.core.serializers.json import DjangoJSONEncoder
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

        data["alimentos_json"] = json.dumps(alimentos_list, cls=DjangoJSONEncoder)
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context["ingredientes_formset"]
        
        if formset.is_valid():
            with transaction.atomic():
                # Obtener las instrucciones dinámicas del POST
                pasos = self.request.POST.getlist("pasos_instrucciones")
                pasos_limpios = [p.strip() for p in pasos if p.strip()]
                form.instance.instrucciones = pasos_limpios

                self.object = form.save()
                formset.instance = self.object
                formset.save()
                
            messages.success(self.request, f"Receta «{self.object.nombre}» actualizada correctamente.")
            return redirect(self.get_success_url())
        else:
            return self.form_invalid(form)


class RecetaDetailView(LoginRequiredMixin, DetailView):
    """Muestra la receta, ingredientes con porciones y desglose de macros."""
    model = Receta
    template_name = "nutricion/receta_detalle.html"
    context_object_name = "receta"

    def get_queryset(self):
        # Aislamiento: Puede ver recetas del sistema o las suyas propias (incluyendo las de sus pacientes)
        return Receta.objects.filter(
            Q(es_sistema=True) | Q(creado_por=self.request.user)
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Prefetch de los alimentos asociados a los ingredientes para evitar queries N+1
        context["ingredientes_list"] = self.object.ingredientes.select_related("alimento").all()
        # Pasar paciente_id si viene en los query params para volver a su ficha
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
        from pacientes.models import Paciente
        paciente_id = request.POST.get("paciente_id") or request.GET.get("paciente_id")
        if not paciente_id:
            messages.error(request, "Se requiere especificar un paciente para importar la receta.")
            return redirect("nutricion:recetas")
            
        paciente = get_object_or_404(Paciente, pk=paciente_id, nutricionista=request.user)
        # Buscar la receta global (ya sea del sistema o propia del nutricionista y que sea global)
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
            # Copiar ingredientes
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
    """
    Endpoint JSON para la búsqueda rápida de alimentos con autocompletado en el frontend.
    """
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

