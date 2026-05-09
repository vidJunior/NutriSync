# nutricion/urls.py

from django.urls import path
from . import views, views_auth, views_cbv

app_name = "nutricion"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),

    path("login/", views_auth.login_view, name="login"),
    path("logout/", views_auth.logout_view, name="logout"),
    path("registro/", views_auth.registro_view, name="registro"),

    path("perfil/", views_auth.perfil_view, name="perfil"),
    path("perfil/editar/", views_cbv.PerfilUpdateView.as_view(), name="perfil_editar"),

    path("comidas/", views_cbv.RegistroListView.as_view(), name="lista_registros"),
    path("comidas/registrar/", views_cbv.RegistroCreateView.as_view(), name="registrar_comida"),

    path("habitos/", views.lista_habitos, name="lista_habitos"),
    path("habitos/nuevo/", views_cbv.HabitoCreateView.as_view(), name="nuevo_habito"),

    path("logros/", views.logros_view, name="logros"),
]