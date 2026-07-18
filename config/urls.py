# config/urls.py
# URLs raíz del proyecto NutriSync.
# Rutas principales.

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from config.api import api

urlpatterns = [
    path("admin/", admin.site.urls),

    # Endpoints de la API móvil (Django Ninja)
    path("api/", api.urls),

    # Panel de administración
    path("administracion/", include("administracion.urls")),

    # App core: login, logout, dashboard, perfil
    path("", include("core.urls")),

    # Gestión de pacientes (Parte 2)
    path("pacientes/", include("pacientes.urls")),
    # Agenda de citas (Parte 3)
    path("", include("agendas.urls")),
    # Planes nutricionales y alimentos (Parte 4)
    path("", include("nutricion.urls")),
    # Seguimiento corporal y notas clínicas (Parte 5)
    path("seguimiento/", include("seguimiento.urls")),
    # Reportes clínicos, operativos y financieros
    path("reportes/", include("reportes.urls")),
    # Facturación, cobros y suscripciones
    path("facturacion/", include("facturacion.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Páginas de error
handler404 = "core.views.error_404"
handler500 = "core.views.error_500"

# Personalización del panel de administración Django
admin.site.site_header = "NutriSync"
admin.site.site_title = "NutriSync Admin"
admin.site.index_title = "Administración de NutriSync"

