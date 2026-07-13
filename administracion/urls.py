# administracion/urls.py
# Rutas del panel de administración.

from django.urls import path
from django.views.generic import RedirectView
from administracion.views import auth, dashboard, users, subscriptions, plans, payments, auditoria, notifications, reports, soporte

app_name = "administracion"

urlpatterns = [
    path("login/",    RedirectView.as_view(url="/?login=true", permanent=False), name="login"),
    path("logout/",   auth.admin_logout_view,   name="logout"),
    path("",          dashboard.dashboard_view, name="dashboard"),

    # Nutricionistas
    path("usuarios/",             users.usuarios_lista_view,   name="usuarios_lista"),
    path("usuarios/<int:pk>/",    users.usuario_detalle_view,  name="usuario_detalle"),
    path("usuarios/<int:pk>/estado/", users.usuario_toggle_estado, name="usuario_toggle_estado"),
    path("usuarios/<int:pk>/override/", users.usuario_override_limites, name="usuario_override_limites"),

    # Suscripciones
    path("suscripciones/",                    subscriptions.suscripciones_lista_view, name="suscripciones_lista"),
    path("suscripciones/<int:pk>/",           subscriptions.suscripcion_detalle_view, name="suscripcion_detalle"),
    path("suscripciones/<int:pk>/plan/",      subscriptions.suscripcion_cambiar_plan, name="suscripcion_cambiar_plan"),
    path("suscripciones/<int:pk>/cancelar/",  subscriptions.suscripcion_cancelar,     name="suscripcion_cancelar"),
    path("suscripciones/<int:pk>/reactivar/", subscriptions.suscripcion_reactivar,    name="suscripcion_reactivar"),

    # Planes
    path("planes/",                 plans.planes_lista_view,    name="planes_lista"),
    path("planes/crear/",           plans.plan_crear_view,      name="plan_crear"),
    path("planes/<int:pk>/editar/", plans.plan_editar_view,     name="plan_editar"),
    path("planes/<int:pk>/toggle/", plans.plan_toggle_view,     name="plan_toggle"),

    # Verificación de pagos
    path("pagos/",                  payments.pagos_verificar_lista_view, name="pagos_verificar_lista"),
    path("pagos/<int:pk>/aprobar/",  payments.pago_aprobar_view,          name="pago_aprobar"),
    path("pagos/<int:pk>/rechazar/", payments.pago_rechazar_view,         name="pago_rechazar"),

    # Auditoría
    path("auditoria/",              auditoria.logs_lista_view,  name="logs_lista"),

    # Notificaciones
    path("notificaciones/crear/",   notifications.notificaciones_crear_view, name="notificaciones_crear"),

    # Reportes
    path("reportes/",               reports.reportes_dashboard_view, name="reportes"),
    path("reportes/exportar/nutricionistas/", reports.exportar_nutricionistas_csv, name="exportar_nutricionistas_csv"),
    path("reportes/exportar/finanzas/", reports.exportar_finanzas_csv, name="exportar_finanzas_csv"),
    path("reportes/exportar/mensual/", reports.exportar_pagos_mensuales_csv, name="exportar_pagos_mensuales_csv"),

    # Soporte técnico
    path("soporte/",                soporte.soporte_lista_view,    name="soporte_lista"),
    path("soporte/<int:pk>/responder/", soporte.soporte_responder_view, name="soporte_responder"),
]

