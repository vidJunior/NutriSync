# administracion/mixins.py
# Restringe el acceso a administradores.

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect


class AdminRequeridoMixin(LoginRequiredMixin):
    """Verifica autenticación y rol admin_plataforma."""
    login_url = "/?login=true"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(self.login_url)

        perfil = getattr(request.user, "perfil", None)
        es_admin = perfil and perfil.rol == "admin_plataforma"

        if not es_admin:
            raise PermissionDenied("No tienes acceso a esta sección.")

        return super().dispatch(request, *args, **kwargs)


def admin_requerido(view_func):
    """Decorador equivalente a AdminRequeridoMixin."""
    from functools import wraps

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("/?login=true")

        perfil = getattr(request.user, "perfil", None)
        es_admin = perfil and perfil.rol == "admin_plataforma"

        if not es_admin:
            raise PermissionDenied("No tienes acceso a esta sección.")

        return view_func(request, *args, **kwargs)

    return wrapper

