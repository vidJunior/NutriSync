# administracion/views/dashboard.py
# Vista del dashboard del administrador con métricas financieras y operativas.

from django.shortcuts import render
from django.db.models import Sum
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from administracion.mixins import admin_requerido
from facturacion.models import SuscripcionNutricionista, Pago, PlanSuscripcion


@admin_requerido
def dashboard_view(request):
    """Vista principal del panel de administración."""
    # 1. Suscripciones activas
    suscripciones_activas = SuscripcionNutricionista.objects.filter(estado="activa")
    
    # 2. MRR (Ingreso Mensual Recurrente)
    mrr = Decimal("0.00")
    for s in suscripciones_activas:
        if s.tipo_facturacion == "anual":
            mrr += s.precio_aplicado / Decimal("12.00")
        else:
            mrr += s.precio_aplicado

    # 3. Nutricionistas totales y nuevos
    nutricionistas_totales = User.objects.filter(is_staff=False, is_superuser=False).count()
    este_mes_inicio = timezone.now().date().replace(day=1)
    nutricionistas_nuevos_mes = User.objects.filter(
        is_staff=False, 
        is_superuser=False, 
        date_joined__date__gte=este_mes_inicio
    ).count()

    # 4. Tasa de conversión
    nutricionistas_pago = suscripciones_activas.filter(precio_aplicado__gt=0).count()
    tasa_conversion = (nutricionistas_pago / nutricionistas_totales * 100) if nutricionistas_totales > 0 else 0

    # 5. Churn Rate (Cancelaciones en los últimos 30 días)
    hace_30_dias = timezone.now() - timedelta(days=30)
    cancelaciones_30_dias = SuscripcionNutricionista.objects.filter(
        estado="cancelada", 
        fecha_creacion__gte=hace_30_dias
    ).count()
    total_suscripciones = SuscripcionNutricionista.objects.count()
    churn_rate = (cancelaciones_30_dias / total_suscripciones * 100) if total_suscripciones > 0 else 0

    # 6. Historial de cobros recientes (últimos 5 pagos de suscripción)
    pagos_recientes = Pago.objects.select_related("nutricionista__perfil").order_by("-fecha_pago")[:5]

    # 7. Datos de facturación mensual (últimos 6 meses) para el gráfico
    ingresos_meses = []
    labels_meses = []
    
    # Para evitar problemas con zonas horarias o meses con menos de 30 días,
    # calcularemos los últimos 6 meses calendarios
    hoy = timezone.now().date()
    for i in range(5, -1, -1):
        # Retroceder i meses
        mes_offset = hoy.month - i
        anio_offset = hoy.year
        while mes_offset <= 0:
            mes_offset += 12
            anio_offset -= 1
            
        suma = Pago.objects.filter(
            estado="completado",
            fecha_pago__month=mes_offset,
            fecha_pago__year=anio_offset
        ).aggregate(total=Sum("monto"))["total"] or Decimal("0.00")
        
        ingresos_meses.append(float(suma))
        nombres_meses = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
        labels_meses.append(f"{nombres_meses[mes_offset - 1]} {anio_offset}")

    context = {
        "mrr": mrr,
        "nutricionistas_totales": nutricionistas_totales,
        "nutricionistas_nuevos_mes": nutricionistas_nuevos_mes,
        "tasa_conversion": round(tasa_conversion, 1),
        "churn_rate": round(churn_rate, 1),
        "pagos_recientes": pagos_recientes,
        "labels_meses": labels_meses,
        "ingresos_meses": ingresos_meses,
        "suscripciones_activas_count": suscripciones_activas.count(),
    }
    
    return render(request, "administracion/dashboard/index.html", context)
