# core/urls.py
# URLs de la app core: autenticación, dashboard y perfil.

from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("register/", views.register_view, name="register"),
    path("", views.landing_view, name="landing"),
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("perfil/", views.perfil_view, name="perfil"),
    path("soporte/", views.soporte_view, name="soporte"),
    path("notificaciones/", views.notificaciones_view, name="notificaciones"),
    path("api/alertas/", views.api_alertas, name="api_alertas"),
    path("api/alertas/<int:alert_id>/leer/", views.api_alertar_leer, name="api_alertar_leer"),
]
