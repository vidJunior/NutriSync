# seguimiento/urls.py
# Rutas completas para seguimiento corporal y notas clínicas.
# Namespace: 'seguimiento'

from django.urls import path
from . import views

app_name = "seguimiento"

urlpatterns = [
    # ── Dashboards generales (desde el sidebar) ───────────────────────────
    path(
        "",
        views.seguimiento_dashboard,
        name="dashboard",
    ),
    path(
        "notas/",
        views.notas_dashboard,
        name="notas_dashboard",
    ),
    # ── Medidas Corporales ────────────────────────────────────────────────
    path(
        "medidas/nueva/<int:paciente_pk>/",
        views.MedidaCreateView.as_view(),
        name="medidas_nueva",
    ),
    path(
        "medidas/<int:paciente_pk>/",
        views.MedidaListView.as_view(),
        name="medidas_lista",
    ),
    # ── Notas Clínicas ────────────────────────────────────────────────────
    path(
        "notas/nueva/<int:paciente_pk>/",
        views.NotaCreateView.as_view(),
        name="notas_nueva",
    ),
    path(
        "notas/lista/<int:paciente_pk>/",
        views.NotaListView.as_view(),
        name="notas_lista",
    ),
    path(
        "notas/detalle/<int:pk>/",
        views.NotaDetailView.as_view(),
        name="notas_detalle",
    ),
    # ── Historial ─────────────────────────────────────────────────────────
    path(
        "historial/<int:paciente_pk>/",
        views.historial_paciente,
        name="historial",
    ),
]
