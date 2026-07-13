# administracion/urls.py
# Rutas del panel de administración.

from django.urls import path
from administracion.views import auth, dashboard, users, subscriptions

app_name = "administracion"

urlpatterns = [
    path("login/",    auth.admin_login_view,    name="login"),
    path("register/", auth.admin_register_view, name="register"),
    path("logout/",   auth.admin_logout_view,   name="logout"),
    path("",          dashboard.dashboard_view, name="dashboard"),

    # Nutricionistas
    path("usuarios/",             users.usuarios_lista_view,   name="usuarios_lista"),
    path("usuarios/<int:pk>/",    users.usuario_detalle_view,  name="usuario_detalle"),
    path("usuarios/<int:pk>/estado/", users.usuario_toggle_estado, name="usuario_toggle_estado"),

    # Suscripciones
    path("suscripciones/",                    subscriptions.suscripciones_lista_view, name="suscripciones_lista"),
    path("suscripciones/<int:pk>/",           subscriptions.suscripcion_detalle_view, name="suscripcion_detalle"),
    path("suscripciones/<int:pk>/plan/",      subscriptions.suscripcion_cambiar_plan, name="suscripcion_cambiar_plan"),
    path("suscripciones/<int:pk>/cancelar/",  subscriptions.suscripcion_cancelar,     name="suscripcion_cancelar"),
    path("suscripciones/<int:pk>/reactivar/", subscriptions.suscripcion_reactivar,    name="suscripcion_reactivar"),
]

