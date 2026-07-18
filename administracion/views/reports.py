# administracion/views/reports.py
# Reportes y exportación CSV.

import csv
from django.http import HttpResponse
from django.shortcuts import render
from django.contrib.auth.models import User
from django.db.models import Count, Sum
from decimal import Decimal
from django.utils import timezone

from administracion.mixins import admin_requerido
from administracion.models import LogAuditoriaAdmin
from facturacion.models import SuscripcionNutricionista, Pago, PlanSuscripcion


from datetime import timedelta

@admin_requerido
def reportes_dashboard_view(request):
    """Muestra estadísticas avanzadas, listado mensual de pagos y descargas."""
    hoy = timezone.now()
    
    # Mes y año del reporte.
    try:
        mes_filtro = int(request.GET.get("mes", hoy.month))
        anio_filtro = int(request.GET.get("anio", hoy.year))
    except ValueError:
        mes_filtro = hoy.month
        anio_filtro = hoy.year
    if not 1 <= mes_filtro <= 12 or not 2000 <= anio_filtro <= hoy.year + 1:
        mes_filtro = hoy.month
        anio_filtro = hoy.year

    # 1. Distribución de nutricionistas por plan
    planes_dist = SuscripcionNutricionista.objects.filter(estado="activa")\
        .values("plan__nombre")\
        .annotate(total=Count("id"))\
        .order_by("-total")
        
    labels_planes = [item["plan__nombre"] for item in planes_dist]
    valores_planes = [item["total"] for item in planes_dist]

    # 2. Facturación por método.
    metodos_dist = Pago.objects.filter(estado="completado")\
        .values("metodo_pago")\
        .annotate(total_monto=Sum("monto"))\
        .order_by("-total_monto")

    # 3. Resumen acumulado total
    ingresos_totales = Pago.objects.filter(estado="completado").aggregate(total=Sum("monto"))["total"] or Decimal("0.00")
    total_usuarios = User.objects.filter(is_staff=False, is_superuser=False).count()
    suscripciones_activas = SuscripcionNutricionista.objects.filter(estado="activa").count()

    # 4. Pagos detallados del mes seleccionado
    q_nutricionista = request.GET.get("q_nutricionista", "").strip()
    plan_pago = request.GET.get("plan_pago", "").strip()

    pagos_mes = Pago.objects.filter(
        fecha_pago__month=mes_filtro,
        fecha_pago__year=anio_filtro
    ).select_related("nutricionista__perfil", "nutricionista__suscripcion__plan").order_by("-fecha_pago")
    
    if q_nutricionista:
        from django.db.models import Q
        pagos_mes = pagos_mes.filter(
            Q(nutricionista__perfil__nombre_completo__icontains=q_nutricionista) |
            Q(nutricionista__username__icontains=q_nutricionista) |
            Q(nutricionista__email__icontains=q_nutricionista)
        )
        
    if plan_pago:
        pagos_mes = pagos_mes.filter(nutricionista__suscripcion__plan_id=plan_pago)
        
    total_mes_seleccionado = pagos_mes.filter(estado="completado").aggregate(total=Sum("monto"))["total"] or Decimal("0.00")

    # 5. Últimos doce meses.
    meses_opciones = []
    nombres_meses = [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]
    for i in range(12):
        # Desplazamiento aproximado de meses
        fecha_temp = hoy - timedelta(days=i * 30.4)
        opt = {
            "anio": fecha_temp.year,
            "mes": fecha_temp.month,
            "nombre": f"{nombres_meses[fecha_temp.month - 1]} {fecha_temp.year}"
        }
        if opt not in meses_opciones:
            meses_opciones.append(opt)

    # 6. Todos los planes para el filtro
    todos_planes = PlanSuscripcion.objects.all()

    context = {
        "labels_planes": labels_planes,
        "valores_planes": valores_planes,
        "metodos_dist": metodos_dist,
        "ingresos_totales": ingresos_totales,
        "total_usuarios": total_usuarios,
        "suscripciones_activas": suscripciones_activas,
        "pagos_mes": pagos_mes,
        "total_mes_seleccionado": total_mes_seleccionado,
        "mes_filtro": mes_filtro,
        "anio_filtro": anio_filtro,
        "meses_opciones": meses_opciones,
        "todos_planes": todos_planes,
        "q_nutricionista": q_nutricionista,
        "plan_pago_filtro": plan_pago,
    }
    return render(request, "administracion/reports/index.html", context)


@admin_requerido
def exportar_nutricionistas_csv(request):
    """Exporta un reporte CSV con el listado completo de nutricionistas y sus perfiles/suscripciones."""
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="nutricionistas_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    # Escribir BOM para Excel
    response.write(b'\xef\xbb\xbf')

    writer = csv.writer(response)
    writer.writerow([
        "ID Usuario", 
        "Nombre Completo", 
        "Usuario (Username)", 
        "Email", 
        "Colegiatura", 
        "Especialidad", 
        "Teléfono", 
        "Estado Cuenta", 
        "Plan Suscrito", 
        "Ciclo Facturación", 
        "Precio Aplicado (S/)", 
        "Fecha Registro"
    ])

    nutricionistas = User.objects.filter(perfil__rol="nutricionista").select_related("perfil", "suscripcion__plan").order_by("-date_joined")
    
    for u in nutricionistas:
        perfil = u.perfil
        suscripcion = getattr(u, "suscripcion", None)
        
        plan_nombre = suscripcion.plan.nombre if suscripcion else "Sin plan"
        tipo_facturacion = suscripcion.get_tipo_facturacion_display() if suscripcion else "—"
        precio = suscripcion.precio_aplicado if suscripcion else 0.00
        
        writer.writerow([
            u.id,
            perfil.nombre_completo,
            u.username,
            u.email,
            perfil.numero_colegiatura,
            perfil.especialidad,
            perfil.telefono,
            perfil.get_estado_display(),
            plan_nombre,
            tipo_facturacion,
            precio,
            u.date_joined.strftime("%d/%m/%Y %H:%M")
        ])

    # Registrar en auditoría
    LogAuditoriaAdmin.objects.create(
        administrador=request.user,
        accion="Exportar CSV",
        detalle="Exportó la lista de nutricionistas registrados en formato CSV."
    )

    return response


@admin_requerido
def exportar_finanzas_csv(request):
    """Exporta un reporte CSV de los pagos y cobros históricos registrados en la plataforma."""
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="reporte_financiero_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    # Escribir BOM para Excel
    response.write(b'\xef\xbb\xbf')

    writer = csv.writer(response)
    writer.writerow([
        "ID Pago", 
        "Nutricionista", 
        "Usuario", 
        "Monto (S/)", 
        "Método de Pago", 
        "Referencia", 
        "Estado Pago", 
        "Fecha de Pago", 
        "Comisión Stripe (S/)", 
        "Monto Neto (S/)"
    ])

    pagos = Pago.objects.select_related("nutricionista__perfil").order_by("-fecha_pago")
    
    for p in pagos:
        nombre_nutricionista = p.nutricionista.perfil.nombre_completo if p.nutricionista else "Usuario Eliminado"
        username = p.nutricionista.username if p.nutricionista else "—"
        
        writer.writerow([
            p.id,
            nombre_nutricionista,
            username,
            p.monto,
            p.get_metodo_pago_display(),
            p.referencia or "Ninguna",
            p.get_estado_display(),
            p.fecha_pago.strftime("%d/%m/%Y %H:%M") if p.fecha_pago else "—",
            p.comision_stripe,
            p.monto_neto
        ])

    # Registrar en auditoría
    LogAuditoriaAdmin.objects.create(
        administrador=request.user,
        accion="Exportar CSV",
        detalle="Exportó el historial financiero general en formato CSV."
    )

    return response


@admin_requerido
def exportar_pagos_mensuales_csv(request):
    """Exporta los pagos de suscripciones del mes y año seleccionados aplicando filtros."""
    try:
        mes = int(request.GET.get("mes", timezone.now().month))
        anio = int(request.GET.get("anio", timezone.now().year))
    except ValueError:
        mes = timezone.now().month
        anio = timezone.now().year
    if not 1 <= mes <= 12 or not 2000 <= anio <= timezone.now().year + 1:
        mes = timezone.now().month
        anio = timezone.now().year

    q_nutricionista = request.GET.get("q_nutricionista", "").strip()
    plan_pago = request.GET.get("plan_pago", "").strip()

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="pagos_suscripcion_{anio}_{mes}.csv"'
    response.write(b'\xef\xbb\xbf')

    writer = csv.writer(response)
    writer.writerow([
        "ID Pago",
        "Nutricionista",
        "Usuario",
        "Plan",
        "Monto Pagado (S/)",
        "Método de Pago",
        "Referencia",
        "Estado",
        "Fecha Pago"
    ])

    pagos = Pago.objects.filter(
        fecha_pago__month=mes,
        fecha_pago__year=anio
    ).select_related("nutricionista__perfil", "nutricionista__suscripcion__plan").order_by("-fecha_pago")

    if q_nutricionista:
        from django.db.models import Q
        pagos = pagos.filter(
            Q(nutricionista__perfil__nombre_completo__icontains=q_nutricionista) |
            Q(nutricionista__username__icontains=q_nutricionista) |
            Q(nutricionista__email__icontains=q_nutricionista)
        )
        
    if plan_pago:
        pagos = pagos.filter(nutricionista__suscripcion__plan_id=plan_pago)

    for p in pagos:
        nombre = p.nutricionista.perfil.nombre_completo if p.nutricionista else "Eliminado"
        username = p.nutricionista.username if p.nutricionista else "—"
        plan = p.nutricionista.suscripcion.plan.nombre if p.nutricionista and hasattr(p.nutricionista, 'suscripcion') else "—"
        
        writer.writerow([
            p.id,
            nombre,
            username,
            plan,
            p.monto,
            p.get_metodo_pago_display(),
            p.referencia or "Ninguna",
            p.get_estado_display(),
            p.fecha_pago.strftime("%d/%m/%Y %H:%M") if p.fecha_pago else "—"
        ])

    # Registrar en auditoría
    LogAuditoriaAdmin.objects.create(
        administrador=request.user,
        accion="Exportar CSV Mensual",
        detalle=f"Exportó los pagos de suscripción del mes {mes}/{anio} con filtros en formato CSV."
    )

    return response
