# administracion/views/users.py
# Gestión de nutricionistas (usuarios) del panel de administración.

from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.models import User
from django.views.decorators.http import require_POST
from administracion.mixins import admin_requerido
from core.models import Rol
from config.choices import EstadoNutricionista


@admin_requerido
def usuarios_lista_view(request):
    """Lista de nutricionistas con filtros y búsqueda."""
    queryset = User.objects.filter(perfil__rol=Rol.NUTRICIONISTA).select_related('perfil', 'suscripcion__plan').order_by('-date_joined')

    # Búsqueda y filtrado
    q = request.GET.get('q', '').strip()
    estado = request.GET.get('estado', '').strip()

    if q:
        queryset = queryset.filter(
            Q(username__icontains=q) |
            Q(perfil__nombre_completo__icontains=q) |
            Q(email__icontains=q)
        )
    if estado:
        queryset = queryset.filter(perfil__estado=estado)

    paginator = Paginator(queryset, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'q': q,
        'estado_filtro': estado,
        'estados': EstadoNutricionista.CHOICES,
    }
    return render(request, 'administracion/users/list.html', context)


@admin_requerido
def usuario_detalle_view(request, pk):
    """Detalle de perfil, suscripción y métricas del nutricionista con uso de límites y cuotas."""
    usuario = get_object_or_404(User, pk=pk, perfil__rol=Rol.NUTRICIONISTA)
    from django.utils import timezone
    from administracion.models import LimiteOverride
    
    # Recuperar o crear el override de límites para el nutricionista
    override, _ = LimiteOverride.objects.get_or_create(nutricionista=usuario)

    # Suscripción y plan actual
    suscripcion = getattr(usuario, 'suscripcion', None)
    plan = suscripcion.plan if suscripcion else None
    
    limite_pacientes = plan.limite_pacientes if plan else -1
    limite_citas = plan.limite_citas_mes if plan else -1

    # Cantidad total de pacientes activos y citas del mes actual
    pacientes_activos = usuario.pacientes.filter(estado=True).count()
    
    hoy = timezone.now()
    citas_mes = usuario.citas_creadas.filter(
        fecha_hora__month=hoy.month, 
        fecha_hora__year=hoy.year
    ).count()

    # Calcular barras de progreso e indicadores de cuotas
    # Pacientes
    if limite_pacientes == -1:
        pct_pacientes = 0
        total_permitido_pacientes = "Ilimitado"
    else:
        total_permitido_pacientes = limite_pacientes + override.pacientes_adicionales
        pct_pacientes = min(100, int((pacientes_activos / total_permitido_pacientes) * 100)) if total_permitido_pacientes > 0 else 100
        
    # Citas
    if limite_citas == -1:
        pct_citas = 0
        total_permitido_citas = "Ilimitado"
    else:
        total_permitido_citas = limite_citas + override.citas_adicionales_mes
        pct_citas = min(100, int((citas_mes / total_permitido_citas) * 100)) if total_permitido_citas > 0 else 100

    # Últimos 5 cobros del nutricionista
    ultimos_cobros = usuario.cobros.all().order_by('-fecha_creacion')[:5]

    context = {
        'usuario': usuario,
        'pacientes_activos': pacientes_activos,
        'citas_mes': citas_mes,
        'total_permitido_pacientes': total_permitido_pacientes,
        'total_permitido_citas': total_permitido_citas,
        'pct_pacientes': pct_pacientes,
        'pct_citas': pct_citas,
        'override': override,
        'ultimos_cobros': ultimos_cobros,
    }
    return render(request, 'administracion/users/detail.html', context)


@admin_requerido
@require_POST
def usuario_override_limites(request, pk):
    """Configura cuotas de recursos adicionales excepcionales para un nutricionista."""
    usuario = get_object_or_404(User, pk=pk, perfil__rol=Rol.NUTRICIONISTA)
    from administracion.models import LimiteOverride, LogAuditoriaAdmin
    
    try:
        pacientes = int(request.POST.get("pacientes_adicionales", 0))
        citas = int(request.POST.get("citas_adicionales_mes", 0))
    except ValueError:
        pacientes = 0
        citas = 0
        
    notas = request.POST.get("notas", "").strip()
    
    override, _ = LimiteOverride.objects.get_or_create(nutricionista=usuario)
    override.pacientes_adicionales = pacientes
    override.citas_adicionales_mes = citas
    override.notas = notas
    override.save()
    
    # Registrar auditoría
    LogAuditoriaAdmin.objects.create(
        administrador=request.user,
        accion="Override Límites",
        detalle=f"Estableció límites adicionales para @{usuario.username}: +{pacientes} pacientes y +{citas} citas al mes."
    )
    
    messages.success(request, f"Límites adicionales asignados correctamente a @{usuario.username}.")
    return redirect('administracion:usuario_detalle', pk=pk)


@admin_requerido
@require_POST
def usuario_toggle_estado(request, pk):
    """Activa o suspende temporalmente el acceso del nutricionista."""
    usuario = get_object_or_404(User, pk=pk, perfil__rol=Rol.NUTRICIONISTA)
    perfil = usuario.perfil
    from administracion.models import LogAuditoriaAdmin

    if perfil.estado == EstadoNutricionista.HABILITADO:
        perfil.estado = EstadoNutricionista.DESHABILITADO
        estado_str = "Suspendió"
        messages.warning(request, f"La cuenta de {perfil.nombre_completo} ha sido suspendida.")
    else:
        perfil.estado = EstadoNutricionista.HABILITADO
        estado_str = "Habilitó"
        messages.success(request, f"La cuenta de {perfil.nombre_completo} ha sido habilitada.")

    perfil.save()
    
    # Registrar auditoría
    LogAuditoriaAdmin.objects.create(
        administrador=request.user,
        accion=f"{estado_str} Acceso",
        detalle=f"{estado_str} la cuenta del nutricionista '{perfil.nombre_completo}' (ID: {usuario.id})."
    )
    
    return redirect('administracion:usuario_detalle', pk=pk)
