# config/urls.py
# URLs raíz del proyecto NutriSync.
# Incluye las rutas de todas las apps y personaliza el panel de administración.

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),

    # App core: login, logout, dashboard, perfil
    path("", include("core.urls")),

    # Gestión de pacientes (Parte 2)
    path("pacientes/", include("pacientes.urls")),
    # Agenda de citas (Parte 3)
    path("", include("citas.urls")),
    # Planes nutricionales y alimentos (Parte 4)
    path("", include("nutricion.urls")),
    # Seguimiento corporal y notas clínicas (Parte 5)
    path("seguimiento/", include("seguimiento.urls")),
]

# Handlers de error personalizados con diseño consistente al resto del sistema
handler404 = "core.views.error_404"
handler500 = "core.views.error_500"

# Personalización del panel de administración Django
admin.site.site_header = "NutriSync"
admin.site.site_title = "NutriSync Admin"
admin.site.index_title = "Administración de NutriSync"
