# nutricion/views_auth.py

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm


def login_view(request):
    """Login de usuarios"""

    if request.user.is_authenticated:
        return redirect("nutricion:dashboard")

    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)

        if form.is_valid():
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")

            user = authenticate(username=username, password=password)

            if user:
                login(request, user)

                messages.success(
                    request,
                    f"Bienvenido, {user.get_full_name() or user.username}!",
                )

                next_page = request.GET.get("next", "nutricion:dashboard")
                return redirect(next_page)

            messages.error(request, "Usuario o contraseña incorrectos.")
        else:
            messages.error(request, "Corrige los errores del formulario.")
    else:
        form = AuthenticationForm()

    return render(request, "accounts/login.html", {"form": form})


def registro_view(request):
    """Registro básico de usuarios"""

    if request.user.is_authenticated:
        return redirect("nutricion:dashboard")

    if request.method == "POST":
        form = UserCreationForm(request.POST)

        if form.is_valid():
            user = form.save()

            messages.success(
                request,
                f"Cuenta creada para {user.username}. Inicia sesión.",
            )
            return redirect("nutricion:login")

        messages.error(request, "Corrige los errores.")
    else:
        form = UserCreationForm()

    return render(request, "registro.html", {"form": form})


def logout_view(request):
    logout(request)
    messages.info(request, "Sesión cerrada correctamente.")
    return redirect("nutricion:login")


@login_required
def perfil_view(request):
    return render(request, "nutricion/perfil.html", {"user": request.user})