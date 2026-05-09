from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import PerfilForm, RegistroHabitoForm, ItemRegistroForm
from .models import PerfilUsuario, MetaNutricional, RegistroComida, RegistroHabito, Logro, LogroUsuario
from django.contrib import messages
from datetime import date
from django.db.models import Sum


def verificar_logros(usuario, fecha=None):
    if fecha is None:
        fecha = date.today()
    logros_disponibles = Logro.objects.all()
    nuevos = []

    for logro in logros_disponibles:
        if LogroUsuario.objects.filter(usuario=usuario, logro=logro).exists():
            continue

        cumple = False
        cond = logro.condicion

        if logro.tipo == "agua":
            min_vasos = cond.get("min_vasos_agua", 0)
            r = RegistroHabito.objects.filter(usuario=usuario, fecha=fecha).first()
            if r and r.vasos_agua >= min_vasos:
                cumple = True

        elif logro.tipo == "pasos":
            min_pasos = cond.get("min_pasos", 0)
            r = RegistroHabito.objects.filter(usuario=usuario, fecha=fecha).first()
            if r and r.pasos >= min_pasos:
                cumple = True

        elif logro.tipo == "ejercicio":
            min_min = cond.get("min_minutos", 0)
            r = RegistroHabito.objects.filter(usuario=usuario, fecha=fecha).first()
            if r and r.minutos_ejercicio >= min_min:
                cumple = True

        elif logro.tipo == "sueno":
            min_horas = cond.get("min_horas_sueno", 0)
            r = RegistroHabito.objects.filter(usuario=usuario, fecha=fecha).first()
            if r and r.horas_sueno >= min_horas:
                cumple = True

        elif logro.tipo == "calorias":
            min_cal = cond.get("min_calorias", 0)
            total = RegistroComida.objects.filter(usuario=usuario, fecha=fecha).aggregate(
                total=Sum("items__total_calorias")
            )["total"] or 0
            if total >= min_cal:
                cumple = True

        elif logro.tipo == "comidas":
            min_comidas = cond.get("min_comidas", 0)
            count = RegistroComida.objects.filter(usuario=usuario, fecha=fecha).count()
            if count >= min_comidas:
                cumple = True

        if cumple:
            LogroUsuario.objects.create(usuario=usuario, logro=logro)
            nuevos.append(logro)

    return nuevos


@login_required
def dashboard(request):
    perfil = PerfilUsuario.objects.filter(usuario=request.user).first()
    meta = MetaNutricional.objects.filter(perfil=perfil).first() if perfil else None
    today = date.today()
    comidas_fecha = RegistroComida.objects.filter(usuario=request.user, fecha=today)
    total_calorias = sum(c.total_calorias for c in comidas_fecha)
    contexto = {
        "perfil": perfil,
        "meta": meta,
        "comidas_fecha": comidas_fecha,
        "total_calorias": total_calorias,
    }
    return render(request, "nutricion/dashboard.html", contexto)


@login_required
def lista_comidas(request):
    comidas = RegistroComida.objects.filter(usuario=request.user)
    return render(request, "nutricion/lista_comidas.html", {"comidas": comidas})


@login_required
def crear_comida(request):
    if request.method == "POST":
        form = ItemRegistroForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Comida registrada correctamente.")
            return redirect("nutricion:lista_comidas")
    else:
        form = ItemRegistroForm()
    return render(request, "nutricion/crear_comida.html", {"form": form})


@login_required
def lista_habitos(request):
    habitos = RegistroHabito.objects.filter(usuario=request.user)
    return render(request, "nutricion/lista_habitos.html", {"habitos": habitos})


@login_required
def logros_view(request):
    nuevos = verificar_logros(request.user)
    if nuevos:
        messages.success(request, f"¡Nuevos logros desbloqueados: {', '.join(l.nombre for l in nuevos)}!")
    logros = LogroUsuario.objects.filter(usuario=request.user)
    return render(request, "nutricion/logros.html", {"logros": logros})
