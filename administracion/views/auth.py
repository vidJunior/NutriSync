# administracion/views/auth.py
# Login, registro y logout para administradores.

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.conf import settings
from django.views.decorators.http import require_http_methods

from core.models import PerfilNutricionista, Rol


# ─── Login ───────────


def admin_login_view(request):
    """Login para administradores (rol admin_plataforma)."""
    if request.user.is_authenticated:
        perfil = getattr(request.user, "perfil", None)
        if perfil and perfil.rol == Rol.ADMIN_PLATAFORMA:
            return redirect("administracion:dashboard")
        logout(request)

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        if not username or not password:
            messages.error(request, "Completa todos los campos.")
            return render(request, "administracion/auth/login.html")

        user = authenticate(request, username=username, password=password)

        if user is None:
            messages.error(request, "Usuario o contraseña incorrectos.")
            return render(request, "administracion/auth/login.html")

        perfil = getattr(user, "perfil", None)
        if not perfil or perfil.rol != Rol.ADMIN_PLATAFORMA:
            messages.error(request, "Esta cuenta no tiene acceso de administrador.")
            return render(request, "administracion/auth/login.html")

        login(request, user)
        messages.success(
            request, f"Bienvenido, {perfil.nombre_completo or user.username}."
        )
        next_url = request.GET.get("next", "") or "/administracion/"
        return redirect(next_url)

    return render(request, "administracion/auth/login.html")


# ─── Registro ────────


def admin_register_view(request):
    """Registro deshabilitado por seguridad."""
    messages.error(request, "El registro público de administradores está deshabilitado por seguridad.")
    return redirect("administracion:login")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        nombre = request.POST.get("nombre_completo", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        password2 = request.POST.get("password_confirm", "")
        clave_reg = request.POST.get("clave_registro", "").strip()

        clave_esperada = getattr(settings, "ADMIN_REGISTER_KEY", "nutrisync-admin-2025")
        errors = []

        if not username:
            errors.append("El nombre de usuario es obligatorio.")
        if not nombre:
            errors.append("El nombre completo es obligatorio.")
        if not email:
            errors.append("El email es obligatorio.")
        if not password:
            errors.append("La contraseña es obligatoria.")
        if password != password2:
            errors.append("Las contraseñas no coinciden.")
        if len(password) < 8:
            errors.append("La contraseña debe tener al menos 8 caracteres.")
        if clave_reg != clave_esperada:
            errors.append("La clave de registro es incorrecta.")
        if User.objects.filter(username=username).exists():
            errors.append(f"El nombre de usuario '{username}' ya está en uso.")
        if email and User.objects.filter(email=email).exists():
            errors.append("Ya existe una cuenta con ese email.")

        if errors:
            return render(
                request,
                "administracion/auth/register.html",
                {
                    "errors": errors,
                    "data": request.POST,
                },
            )

        partes_nombre = nombre.split(" ", 1)
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=partes_nombre[0],
            last_name=partes_nombre[1] if len(partes_nombre) > 1 else "",
        )

        perfil = user.perfil
        perfil.nombre_completo = nombre
        perfil.email_profesional = email
        perfil.rol = Rol.ADMIN_PLATAFORMA
        perfil.save()

        login(request, user)
        messages.success(
            request, f"Cuenta de administrador creada. ¡Bienvenido, {nombre}!"
        )
        return redirect("administracion:dashboard")

    return render(request, "administracion/auth/register.html")


# ─── Logout ─────────


@require_http_methods(["GET", "POST"])
def admin_logout_view(request):
    """Cierra sesión y redirige al login."""
    logout(request)
    messages.info(request, "Has cerrado sesión correctamente.")
    return redirect("administracion:login")
