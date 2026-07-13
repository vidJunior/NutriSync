# administracion/views/auth.py
# Gestión de cierre de sesión para administradores de la plataforma.

from django.shortcuts import redirect
from django.contrib.auth import logout
from django.contrib import messages
from django.views.decorators.http import require_http_methods


@require_http_methods(["GET", "POST"])
def admin_logout_view(request):
    """Cierra sesión de administrador y redirige a la página principal."""
    logout(request)
    messages.info(request, "Has cerrado sesión correctamente de la administración.")
    return redirect("core:landing")

