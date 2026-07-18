# nutricion/urls.py
# Rutas de nutrición.
# Namespace: 'nutricion'

from django.urls import path
from . import views

app_name = "nutricion"

urlpatterns = [
    # -------------Catálogo de alimentos-------------
    path("alimentos/", views.AlimentoListView.as_view(), name="alimentos"),
    path("alimentos/nuevo/", views.AlimentoCreateView.as_view(), name="alimento_nuevo"),
    path("alimentos/<int:pk>/editar/", views.AlimentoUpdateView.as_view(), name="alimento_editar"),
    path("alimentos/cargar-ejemplos/", views.cargar_alimentos_ejemplo, name="cargar_ejemplos"),

    # -------------Catálogo de recetas-------------
    path("recetas/", views.RecetaListView.as_view(), name="recetas"),
    path("recetas/nueva/", views.RecetaCreateView.as_view(), name="receta_nueva"),
    path("recetas/<int:pk>/", views.RecetaDetailView.as_view(), name="receta_detalle"),
    path("recetas/<int:pk>/editar/", views.RecetaUpdateView.as_view(), name="receta_editar"),
    path("recetas/<int:pk>/eliminar/", views.RecetaDeleteView.as_view(), name="receta_eliminar"),
    path("recetas/<int:pk>/importar/", views.RecetaImportarView.as_view(), name="receta_importar"),
    path("api/buscar-alimentos/", views.api_buscar_alimentos, name="api_buscar_alimentos"),

    # -------------Planes nutricionales-------------
    path("planes/", views.PlanListView.as_view(), name="planes"),
    path("planes/nuevo/", views.PlanCreateView.as_view(), name="plan_nuevo"),
    path("planes/<int:pk>/", views.PlanDetailView.as_view(), name="plan_detalle"),
    path("planes/<int:pk>/editar/", views.PlanUpdateView.as_view(), name="plan_editar"),
    path("planes/<int:pk>/duplicar/", views.plan_duplicar, name="plan_duplicar"),
    path("planes/<int:pk>/toggle/", views.plan_toggle, name="plan_toggle"),
    path("planes/<int:pk>/archivar/", views.plan_archivar, name="plan_archivar"),
    path("planes/<int:pk>/eliminar/", views.plan_eliminar, name="plan_eliminar"),

    # -------------Comidas del plan-------------
    path("planes/<int:plan_pk>/comidas/nueva/", views.comida_crear, name="comida_nueva"),
    path("comidas/<int:pk>/eliminar/", views.comida_eliminar, name="comida_eliminar"),
]
