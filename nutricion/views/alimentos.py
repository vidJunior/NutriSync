from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import ListView, CreateView, UpdateView
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from ..models import Alimento, CategoriaAlimento
from ..forms import AlimentoForm

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

        estado = self.request.GET.get("estado", "activo")
        if estado == "activo":
            qs = qs.filter(estado=True)
        elif estado == "inactivo":
            qs = qs.filter(estado=False)

        categoria = self.request.GET.get("categoria", "")
        if categoria:
            qs = qs.filter(categoria=categoria)

        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(nombre__icontains=q)

        return qs.order_by("nombre")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["q"] = self.request.GET.get("q", "")
        context["filtro_categoria"] = self.request.GET.get("categoria", "")
        context["filtro_estado"] = self.request.GET.get("estado", "activo")
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


@login_required
@require_POST
def cargar_alimentos_ejemplo(request):
    """
    Vista de utilidad para cargar los 20+ alimentos de ejemplo en la BD.
    Solo disponible para superusuarios.
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
