# facturacion/views.py
# Vistas del módulo de Facturación y Cobros de NutriSync.
# Dashboard, CRUD de cobros, facturas, suscripciones y reportes de ingresos.

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.db.models import Q, Sum, Count, DecimalField
from django.db.models.functions import TruncMonth
from decimal import Decimal
from datetime import date, timedelta
import calendar

from facturacion.models import (
    PlanSuscripcion,
    SuscripcionNutricionista,
    Cobro,
    Factura,
    ItemFactura,
    Pago,
)
from facturacion.forms import (
    CobroForm,
    CobroPagoForm,
    FacturaFiltroForm,
    FacturaCrearForm,
    ItemFacturaForm,
    ItemFacturaCobroForm,
    CambiarPlanForm,
    IngresosFiltroForm,
)
from facturacion.choices import (
    EstadoCobro,
    EstadoFactura,
    EstadoPago,
    EstadoSuscripcion,
    MetodoPago,
    ConceptoCobro,
)
from facturacion.utils import (
    calcular_total_con_igv,
    calcular_comision_stripe,
    calcular_monto_net_stripe,
    calcular_fecha_vencimiento,
    generar_referencia_pago,
    generar_pdf_factura,
    generar_pdf_boleta_cobro,
    generar_pdf_boleta_suscripcion,
)


# ─── Mixin Base ───────────────────────────────────────────────────────────────

class NutricionistaFacturacionMixin(LoginRequiredMixin):
    """Mixin base para todas las vistas de facturación. Filtra por nutricionista."""

    def get_queryset(self):
        return self.model.objects.filter(nutricionista=self.request.user)


# ─── Dashboard de Facturación ─────────────────────────────────────────────────

@login_required
def facturacion_dashboard(request):
    """Dashboard principal del módulo de facturación."""
    user = request.user
    hoy = timezone.now().date()
    inicio_mes = hoy.replace(day=1)

    # Cobros del mes
    cobros_mes = Cobro.objects.filter(
        nutricionista=user, fecha_creacion__date__gte=inicio_mes
    )
    total_cobros_mes = cobros_mes.aggregate(total=Sum("total"))["total"] or Decimal("0")
    cobros_pagados = cobros_mes.filter(estado=EstadoCobro.PAGADO).count()
    cobros_pendientes = cobros_mes.filter(estado=EstadoCobro.PENDIENTE).count()

    # Boletas generadas (pagos completados del mes)
    pagos_completados_mes = Pago.objects.filter(
        Q(cobro__nutricionista=user) | Q(nutricionista=user),
        estado=EstadoPago.COMPLETADO,
        fecha_pago__date__gte=inicio_mes,
    ).count()

    # Ingresos reales (pagos completados)
    pagos_mes = Pago.objects.filter(
        Q(cobro__nutricionista=user) | Q(nutricionista=user),
        estado=EstadoPago.COMPLETADO,
        fecha_pago__date__gte=inicio_mes,
    )
    ingresos_mes = pagos_mes.aggregate(total=Sum("monto"))["total"] or Decimal("0")

    # Ingresos últimos 6 meses para gráfica
    meses_ingresos = []
    for i in range(5, -1, -1):
        fecha = hoy - timedelta(days=30 * i)
        mes_inicio = fecha.replace(day=1)
        _, ultimo_dia = calendar.monthrange(mes_inicio.year, mes_inicio.month)
        mes_fin = mes_inicio.replace(day=ultimo_dia)
        ingreso = (
            Pago.objects.filter(
                Q(cobro__nutricionista=user) | Q(nutricionista=user),
                estado=EstadoPago.COMPLETADO,
                fecha_pago__date__range=[mes_inicio, mes_fin],
            ).aggregate(total=Sum("monto"))["total"]
            or Decimal("0")
        )
        meses_ingresos.append(
            {"mes": mes_inicio.strftime("%b"), "ingreso": float(ingreso)}
        )

    # Cobros vencidos
    cobros_vencidos = Cobro.objects.filter(
        nutricionista=user,
        estado=EstadoCobro.PENDIENTE,
        fecha_creacion__date__lt=hoy - timedelta(days=30),
    ).count()

    # Suscripción
    try:
        suscripcion = SuscripcionNutricionista.objects.get(
            nutricionista=user, estado=EstadoSuscripcion.ACTIVA
        )
    except SuscripcionNutricionista.DoesNotExist:
        suscripcion = None

    # Últimos cobros
    ultimos_cobros = Cobro.objects.filter(nutricionista=user).select_related(
        "paciente"
    )[:5]

    context = {
        "total_cobros_mes": total_cobros_mes,
        "cobros_pagados": cobros_pagados,
        "cobros_pendientes": cobros_pendientes,
        "pagos_completados_mes": pagos_completados_mes,
        "ingresos_mes": ingresos_mes,
        "meses_ingresos": meses_ingresos,
        "cobros_vencidos": cobros_vencidos,
        "suscripcion": suscripcion,
        "ultimos_cobros": ultimos_cobros,
    }
    return render(request, "facturacion/dashboard.html", context)


# ─── Cobros a Pacientes ──────────────────────────────────────────────────────

class CobrosListView(NutricionistaFacturacionMixin, ListView):
    """Lista de cobros con filtros por paciente, estado y fecha."""

    model = Cobro
    template_name = "facturacion/cobros/lista.html"
    context_object_name = "cobros"
    paginate_by = 15

    def get_queryset(self):
        qs = super().get_queryset().select_related("paciente", "cita")

        # Filtros
        paciente = self.request.GET.get("paciente")
        if paciente:
            qs = qs.filter(
                Q(paciente__nombre__icontains=paciente)
                | Q(paciente__apellido__icontains=paciente)
            )

        estado = self.request.GET.get("estado")
        if estado:
            qs = qs.filter(estado=estado)

        concepto = self.request.GET.get("concepto")
        if concepto:
            qs = qs.filter(concepto=concepto)

        metodo = self.request.GET.get("metodo")
        if metodo:
            qs = qs.filter(metodo_pago_usado=metodo)

        fecha_desde = self.request.GET.get("fecha_desde")
        if fecha_desde:
            qs = qs.filter(fecha_creacion__date__gte=fecha_desde)

        fecha_hasta = self.request.GET.get("fecha_hasta")
        if fecha_hasta:
            qs = qs.filter(fecha_creacion__date__lte=fecha_hasta)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filtro_form"] = {
            "paciente": self.request.GET.get("paciente", ""),
            "estado": self.request.GET.get("estado", ""),
            "concepto": self.request.GET.get("concepto", ""),
            "metodo": self.request.GET.get("metodo", ""),
            "fecha_desde": self.request.GET.get("fecha_desde", ""),
            "fecha_hasta": self.request.GET.get("fecha_hasta", ""),
        }
        context["estados_cobro"] = [
            ("pendiente", "Pendiente"),
            ("pagado", "Pagado"),
            ("cancelado", "Cancelado"),
            ("vencido", "Vencido"),
        ]
        context["conceptos_cobro"] = ConceptoCobro.CHOICES
        context["metodos_pago"] = MetodoPago.CHOICES

        # Estadísticas rápidas para la cabecera
        cobros_total = self.model.objects.filter(nutricionista=self.request.user)
        context["total_facturado"] = cobros_total.filter(estado="pagado").aggregate(total=Sum("total"))["total"] or Decimal("0.00")
        context["total_pendiente"] = cobros_total.filter(estado="pendiente").aggregate(total=Sum("total"))["total"] or Decimal("0.00")
        context["cantidad_pagados"] = cobros_total.filter(estado="pagado").count()
        context["cantidad_pendientes"] = cobros_total.filter(estado="pendiente").count()
        
        return context


class CobroCreateView(NutricionistaFacturacionMixin, CreateView):
    """Crear un nuevo cobro a un paciente."""

    model = Cobro
    form_class = CobroForm
    template_name = "facturacion/cobros/crear.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["nutricionista"] = self.request.user
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        concepto = self.request.GET.get("concepto")
        if concepto:
            initial["concepto"] = concepto
        return initial

    def form_valid(self, form):
        form.instance.nutricionista = self.request.user
        messages.success(self.request, "Cobro creado exitosamente.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("facturacion:cobro_detalle", kwargs={"pk": self.object.pk})


class CobroDetailView(NutricionistaFacturacionMixin, DetailView):
    """Detalle de un cobro."""

    model = Cobro
    template_name = "facturacion/cobros/detalle.html"
    context_object_name = "cobro"

    def get_queryset(self):
        return Cobro.objects.filter(nutricionista=self.request.user).select_related(
            "paciente", "cita"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pago_form"] = CobroPagoForm()
        context["pago_form"].fields["metodo_pago"].choices = MetodoPago.CHOICES
        return context


@login_required
def cobro_registrar_pago(request, pk):
    """Registra el pago de un cobro (manual oStripe)."""
    cobro = get_object_or_404(Cobro, pk=pk, nutricionista=request.user)

    if request.method == "POST":
        form = CobroPagoForm(request.POST, request.FILES)
        if form.is_valid():
            metodo = form.cleaned_data["metodo_pago"]
            referencia = form.cleaned_data["referencia"]
            comprobante = form.cleaned_data.get("comprobante")
            notas = form.cleaned_data.get("notas", "")

            # Crear el pago
            comision = Decimal("0.00")
            monto_neto = cobro.total

            if metodo == MetodoPago.STRIPE:
                comision = calcular_comision_stripe(cobro.total)
                monto_neto = cobro.total - comision

            pago = Pago.objects.create(
                cobro=cobro,
                monto=cobro.total,
                metodo_pago=metodo,
                referencia=referencia or generar_referencia_pago(metodo),
                comprobante=comprobante,
                estado=EstadoPago.COMPLETADO,
                comision_stripe=comision,
                monto_neto=monto_neto,
                notas=notas,
            )

            # Actualizar cobro
            cobro.estado = EstadoCobro.PAGADO
            cobro.fecha_pago = timezone.now()
            cobro.metodo_pago_usado = metodo
            cobro.referencia_pago = pago.referencia
            if comprobante:
                cobro.comprobante_pago = comprobante
            cobro.save()

            messages.success(request, f"Pago de S/{cobro.total} registrado exitosamente.")
            return redirect("facturacion:cobro_detalle", pk=cobro.pk)
    else:
        form = CobroPagoForm()

    return render(
        request,
        "facturacion/cobros/registrar_pago.html",
        {"form": form, "cobro": cobro},
    )


@login_required
def cobro_crear_desde_cita(request, cita_pk):
    """Crea un cobro automático desde el costo de una cita."""
    from agendas.models import Cita

    cita = get_object_or_404(
        Cita, pk=cita_pk, paciente__nutricionista=request.user
    )

    if cita.costo <= 0:
        messages.warning(request, "La cita no tiene un costo definido.")
        return redirect("agendas:detalle", pk=cita.pk)

    cobro = Cobro.objects.create(
        nutricionista=request.user,
        paciente=cita.paciente,
        cita=cita,
        concepto=ConceptoCobro.CONSULTA,
        descripcion=f"Consulta - {cita.get_tipo_display()} - {cita.fecha_hora.strftime('%d/%m/%Y %H:%M')}",
        monto=cita.costo,
    )

    messages.success(request, f"Cobro #{cobro.pk} creado exitosamente desde la cita.")
    return redirect("facturacion:cobro_detalle", pk=cobro.pk)


# ─── Facturas ─────────────────────────────────────────────────────────────────

class FacturasListView(NutricionistaFacturacionMixin, ListView):
    """Lista de facturas con filtros."""

    model = Factura
    template_name = "facturacion/facturas/lista.html"
    context_object_name = "facturas"
    paginate_by = 15

    def get_queryset(self):
        qs = super().get_queryset().select_related("paciente")

        paciente = self.request.GET.get("paciente")
        if paciente:
            qs = qs.filter(
                Q(paciente__nombre__icontains=paciente)
                | Q(paciente__apellido__icontains=paciente)
            )

        estado = self.request.GET.get("estado")
        if estado:
            qs = qs.filter(estado=estado)

        fecha_desde = self.request.GET.get("fecha_desde")
        if fecha_desde:
            qs = qs.filter(fecha_emision__gte=fecha_desde)

        fecha_hasta = self.request.GET.get("fecha_hasta")
        if fecha_hasta:
            qs = qs.filter(fecha_emision__lte=fecha_hasta)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filtro_form"] = {
            "paciente": self.request.GET.get("paciente", ""),
            "estado": self.request.GET.get("estado", ""),
            "fecha_desde": self.request.GET.get("fecha_desde", ""),
            "fecha_hasta": self.request.GET.get("fecha_hasta", ""),
        }
        context["estados_factura"] = [
            ("borrador", "Borrador"),
            ("emitida", "Emitida"),
            ("pagada", "Pagada"),
            ("vencida", "Vencida"),
            ("cancelada", "Cancelada"),
        ]
        return context


class FacturaCreateView(NutricionistaFacturacionMixin, CreateView):
    """Crear una factura."""

    model = Factura
    form_class = FacturaCrearForm
    template_name = "facturacion/facturas/crear.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["nutricionista"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.nutricionista = self.request.user
        form.instance.fecha_emision = timezone.now().date()
        if not form.instance.fecha_vencimiento:
            form.instance.fecha_vencimiento = calcular_fecha_vencimiento(30)
        messages.success(self.request, "Factura creada exitosamente.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("facturacion:factura_detalle", kwargs={"pk": self.object.pk})


class FacturaDetailView(NutricionistaFacturacionMixin, DetailView):
    """Detalle de una factura con sus ítems."""

    model = Factura
    template_name = "facturacion/facturas/detalle.html"
    context_object_name = "factura"

    def get_queryset(self):
        return Factura.objects.filter(nutricionista=self.request.user).select_related(
            "paciente"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["items"] = self.object.items.all()
        context["item_form"] = ItemFacturaForm()
        context["pago_form"] = CobroPagoForm()
        context["pago_form"].fields["metodo_pago"].choices = MetodoPago.CHOICES
        context["cobros_pendientes"] = Cobro.objects.filter(
            nutricionista=self.request.user,
            paciente=self.object.paciente,
            estado=EstadoCobro.PENDIENTE,
        )
        return context


@login_required
def factura_agregar_item(request, pk):
    """Agrega un ítem manual a una factura."""
    factura = get_object_or_404(Factura, pk=pk, nutricionista=request.user)

    if request.method == "POST":
        form = ItemFacturaForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.factura = factura
            item.save()
            factura.calcular_totales()
            messages.success(request, "Ítem agregado a la factura.")
            return redirect("facturacion:factura_detalle", pk=factura.pk)
    else:
        form = ItemFacturaForm()

    return render(
        request,
        "facturacion/facturas/agregar_item.html",
        {"form": form, "factura": factura},
    )


@login_required
def factura_agregar_cobros(request, pk):
    """Agrega cobros pendientes a una factura como ítems."""
    factura = get_object_or_404(Factura, pk=pk, nutricionista=request.user)

    if request.method == "POST":
        cobros_ids = request.POST.getlist("cobros_seleccionados")
        for cobro_id in cobros_ids:
            cobro = get_object_or_404(
                Cobro, pk=cobro_id, nutricionista=request.user, estado=EstadoCobro.PENDIENTE
            )
            ItemFactura.objects.create(
                factura=factura,
                cobro=cobro,
                descripcion=f"{cobro.get_concepto_display()} - {cobro.paciente}",
                cantidad=1,
                precio_unitario=cobro.total,
            )
        factura.calcular_totales()
        messages.success(request, f"{len(cobros_ids)} cobro(s) agregado(s) a la factura.")
        return redirect("facturacion:factura_detalle", pk=factura.pk)

    cobros = Cobro.objects.filter(
        nutricionista=request.user,
        paciente=factura.paciente,
        estado=EstadoCobro.PENDIENTE,
    )
    return render(
        request,
        "facturacion/facturas/agregar_cobros.html",
        {"factura": factura, "cobros": cobros},
    )


@login_required
def factura_emitir(request, pk):
    """Cambia el estado de una factura a 'emitida'."""
    factura = get_object_or_404(
        Factura, pk=pk, nutricionista=request.user, estado=EstadoFactura.BORRADOR
    )
    if factura.items.count() == 0:
        messages.warning(request, "No se puede emitir una factura sin ítems.")
        return redirect("facturacion:factura_detalle", pk=factura.pk)

    factura.estado = EstadoFactura.EMITIDA
    factura.save(update_fields=["estado"])
    messages.success(request, f"Factura {factura.numero_factura} emitida exitosamente.")
    return redirect("facturacion:factura_detalle", pk=factura.pk)


@login_required
def factura_registrar_pago(request, pk):
    """Registra el pago de una factura."""
    factura = get_object_or_404(
        Factura, pk=pk, nutricionista=request.user
    )

    if request.method == "POST":
        form = CobroPagoForm(request.POST, request.FILES)
        if form.is_valid():
            metodo = form.cleaned_data["metodo_pago"]
            referencia = form.cleaned_data["referencia"]
            comprobante = form.FILES.get("comprobante")

            comision = Decimal("0.00")
            monto_neto = factura.total

            if metodo == MetodoPago.STRIPE:
                comision = calcular_comision_stripe(factura.total)
                monto_neto = factura.total - comision

            Pago.objects.create(
                factura=factura,
                monto=factura.total,
                metodo_pago=metodo,
                referencia=referencia or generar_referencia_pago(metodo),
                comprobante=comprobante,
                estado=EstadoPago.COMPLETADO,
                comision_stripe=comision,
                monto_neto=monto_neto,
            )

            factura.estado = EstadoFactura.PAGADA
            factura.save(update_fields=["estado"])

            # Marcar cobros pendientes como pagados
            cobros_ids = factura.items.filter(cobro__isnull=False).values_list(
                "cobro_id", flat=True
            )
            Cobro.objects.filter(id__in=cobros_ids, estado=EstadoCobro.PENDIENTE).update(
                estado=EstadoCobro.PAGADO,
                fecha_pago=timezone.now(),
                metodo_pago_usado=metodo,
            )

            messages.success(request, f"Pago de S/{factura.total} registrado exitosamente.")
            return redirect("facturacion:factura_detalle", pk=factura.pk)
    else:
        form = CobroPagoForm()

    return render(
        request,
        "facturacion/facturas/registrar_pago.html",
        {"form": form, "factura": factura},
    )


# ─── Suscripción ──────────────────────────────────────────────────────────────

@login_required
def suscripcion_detalle(request):
    """Muestra el plan actual del nutricionista y su método de pago vinculado."""
    try:
        suscripcion = SuscripcionNutricionista.objects.get(
            nutricionista=request.user
        )
    except SuscripcionNutricionista.DoesNotExist:
        suscripcion = None

    # Obtener el método de pago guardado analizando las notas del último pago de suscripción
    ultimo_pago = request.user.pagos_facturacion.filter(estado="completado").filter(Q(notas__contains="Tarjeta terminada en") | Q(notas__contains="Celular Yape:") | Q(notas__contains="PayPal Email:") | Q(notas__contains="Suscripción plan")).order_by("-fecha_pago").first()

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "quitar_metodo":
            if ultimo_pago:
                ultimo_pago.notas += " - removido"
                ultimo_pago.save()
                messages.success(request, "Método de pago removido correctamente.")
            return redirect("facturacion:suscripcion_detalle")

    metodo_guardado = None
    if ultimo_pago and "removido" not in ultimo_pago.notas:
        if "Tarjeta terminada en" in ultimo_pago.notas:
            digitos = ultimo_pago.notas.split("terminada en")[-1].strip()
            metodo_guardado = {
                "tipo": "tarjeta",
                "detalle": f"Tarjeta terminada en {digitos}"
            }
        elif "Celular Yape:" in ultimo_pago.notas:
            partes = ultimo_pago.notas.split("Celular Yape:")[-1].strip().split(" - Código:")
            celular = partes[0].strip()
            metodo_guardado = {
                "tipo": "yape",
                "detalle": f"Celular: {celular}"
            }
        elif "PayPal Email:" in ultimo_pago.notas:
            email_paypal = ultimo_pago.notas.split("PayPal Email:")[-1].strip()
            metodo_guardado = {
                "tipo": "paypal",
                "detalle": f"PayPal ({email_paypal})"
            }

    planes = PlanSuscripcion.objects.filter(activo=True)
    
    # Obtener historial de pagos de suscripción del nutricionista
    pagos_suscripcion = request.user.pagos_facturacion.filter(
        estado="completado"
    ).filter(
        Q(notas__contains="Tarjeta terminada en") | 
        Q(notas__contains="Celular Yape:") | 
        Q(notas__contains="PayPal Email:") | 
        Q(notas__contains="Suscripción plan")
    ).order_by("-fecha_pago")
    
    total_gastado = pagos_suscripcion.aggregate(total=Sum("monto"))["total"] or Decimal("0.00")

    return render(
        request,
        "facturacion/suscripcion/plan_actual.html",
        {
            "suscripcion": suscripcion, 
            "planes": planes,
            "metodo_guardado": metodo_guardado,
            "pagos_suscripcion": pagos_suscripcion,
            "total_gastado": total_gastado,
        },
    )


@login_required
def suscripcion_cambiar_plan(request):
    """Permite cambiar el plan de suscripción."""
    planes = PlanSuscripcion.objects.filter(activo=True).exclude(nombre="Prueba Gratis")

    if request.method == "POST":
        form = CambiarPlanForm(request.POST, planes=planes)
        if form.is_valid():
            plan_id = form.cleaned_data["plan"]
            tipo = form.cleaned_data["tipo_facturacion"]
            plan = PlanSuscripcion.objects.get(pk=plan_id)

            precio = (
                plan.precio_anual if tipo == "anual" else plan.precio_mensual
            )

            # Crear o actualizar suscripción
            from facturacion.utils import calcular_fecha_fin
            suscripcion, _ = SuscripcionNutricionista.objects.update_or_create(
                nutricionista=request.user,
                defaults={
                    "plan": plan,
                    "tipo_facturacion": tipo,
                    "precio_aplicado": precio,
                    "estado": EstadoSuscripcion.PENDIENTE,
                    "fecha_inicio": timezone.now().date(),
                    "fecha_fin": calcular_fecha_fin(timezone.now().date(), tipo),
                },
            )

            messages.success(
                request,
                f"Plan cambiado a {plan.nombre}. Completa el pago para activarlo.",
            )
            return redirect("facturacion:suscripcion_detalle")
    else:
        form = CambiarPlanForm(planes=planes)

    # Buscar el método de pago guardado del nutricionista
    ultimo_pago = request.user.pagos_facturacion.filter(estado="completado").filter(Q(notas__contains="Tarjeta terminada en") | Q(notas__contains="Celular Yape:") | Q(notas__contains="PayPal Email:") | Q(notas__contains="Suscripción plan")).order_by("-fecha_pago").first()
    metodo_guardado = None
    if ultimo_pago and "removido" not in ultimo_pago.notas:
        if "Tarjeta terminada en" in ultimo_pago.notas:
            digitos = ultimo_pago.notas.split("terminada en")[-1].strip()
            metodo_guardado = {
                "tipo": "tarjeta",
                "detalle": f"Tarjeta terminada en {digitos}"
            }
        elif "Celular Yape:" in ultimo_pago.notas:
            partes = ultimo_pago.notas.split("Celular Yape:")[-1].strip().split(" - Código:")
            celular = partes[0].strip()
            metodo_guardado = {
                "tipo": "yape",
                "detalle": f"Celular: {celular}"
            }
        elif "PayPal Email:" in ultimo_pago.notas:
            email_paypal = ultimo_pago.notas.split("PayPal Email:")[-1].strip()
            metodo_guardado = {
                "tipo": "paypal",
                "detalle": f"PayPal ({email_paypal})"
            }

    return render(
        request,
        "facturacion/suscripcion/cambiar_plan.html",
        {
            "form": form, 
            "planes": planes,
            "metodo_guardado": metodo_guardado
        },
    )


# ─── Reporte de Ingresos ─────────────────────────────────────────────────────

@login_required
def ingresos_reporte(request):
    """Reporte de ingresos con filtros y exportación."""
    user = request.user
    hoy = timezone.now().date()

    # Filtros por defecto: mes actual
    fecha_desde = request.GET.get("fecha_desde") or hoy.replace(day=1)
    fecha_hasta = request.GET.get("fecha_hasta") or hoy
    paciente_filtro = request.GET.get("paciente", "")
    concepto_filtro = request.GET.get("concepto", "")
    metodo_filtro = request.GET.get("metodo", "")

    pagos = Pago.objects.filter(
        Q(cobro__nutricionista=user) | Q(nutricionista=user),
        estado=EstadoPago.COMPLETADO,
        fecha_pago__date__range=[fecha_desde, fecha_hasta],
    ).select_related("cobro", "cobro__paciente", "factura")

    if paciente_filtro:
        pagos = pagos.filter(
            Q(cobro__paciente__nombre__icontains=paciente_filtro)
            | Q(cobro__paciente__apellido__icontains=paciente_filtro)
        )

    if concepto_filtro:
        pagos = pagos.filter(cobro__concepto=concepto_filtro)

    if metodo_filtro:
        pagos = pagos.filter(metodo_pago=metodo_filtro)

    # Resumen
    total_ingresos = pagos.aggregate(total=Sum("monto"))["total"] or Decimal("0")
    total_comisiones = pagos.aggregate(total=Sum("comision_stripe"))[
        "total"
    ] or Decimal("0")
    total_neto = pagos.aggregate(total=Sum("monto_neto"))["total"] or Decimal("0")

    # Ingresos por paciente
    ingresos_por_paciente = (
        pagos.values("cobro__paciente__nombre", "cobro__paciente__apellido")
        .annotate(total=Sum("monto"), cantidad=Count("id"))
        .order_by("-total")[:10]
    )

    # Ingresos por concepto
    ingresos_por_concepto = (
        pagos.values("cobro__concepto")
        .annotate(total=Sum("monto"), cantidad=Count("id"))
        .order_by("-total")
    )

    # Ingresos por método de pago
    ingresos_por_metodo = (
        pagos.values("metodo_pago")
        .annotate(total=Sum("monto"), cantidad=Count("id"))
        .order_by("-total")
    )

    # Ingresos mensuales (últimos 6 meses)
    ingresos_mensuales = []
    for i in range(5, -1, -1):
        fecha = hoy - timedelta(days=30 * i)
        mes_inicio = fecha.replace(day=1)
        _, ultimo_dia = calendar.monthrange(mes_inicio.year, mes_inicio.month)
        mes_fin = mes_inicio.replace(day=ultimo_dia)
        ingreso = (
            Pago.objects.filter(
                Q(cobro__nutricionista=user) | Q(nutricionista=user),
                estado=EstadoPago.COMPLETADO,
                fecha_pago__date__range=[mes_inicio, mes_fin],
            ).aggregate(total=Sum("monto"))["total"]
            or Decimal("0")
        )
        ingresos_mensuales.append(
            {"mes": mes_inicio.strftime("%b %Y"), "total": float(ingreso)}
        )

    context = {
        "pagos": pagos,
        "total_ingresos": total_ingresos,
        "total_comisiones": total_comisiones,
        "total_neto": total_neto,
        "ingresos_por_paciente": ingresos_por_paciente,
        "ingresos_por_concepto": ingresos_por_concepto,
        "ingresos_por_metodo": ingresos_por_metodo,
        "ingresos_mensuales": ingresos_mensuales,
        "fecha_desde": fecha_desde,
        "fecha_hasta": fecha_hasta,
        "paciente_filtro": paciente_filtro,
        "concepto_filtro": concepto_filtro,
        "metodo_filtro": metodo_filtro,
        "conceptos_cobro": ConceptoCobro.CHOICES,
        "metodos_pago": MetodoPago.CHOICES,
    }
    return render(request, "facturacion/ingresos/reporte.html", context)


@login_required
def ingresos_exportar_csv(request):
    """Exporta el reporte de ingresos a CSV."""
    import csv

    user = request.user
    fecha_desde = request.GET.get("fecha_desde")
    fecha_hasta = request.GET.get("fecha_hasta")

    pagos = Pago.objects.filter(
        cobro__nutricionista=user, estado=EstadoPago.COMPLETADO
    ).select_related("cobro", "cobro__paciente")

    if fecha_desde:
        pagos = pagos.filter(fecha_pago__date__gte=fecha_desde)
    if fecha_hasta:
        pagos = pagos.filter(fecha_pago__date__lte=fecha_hasta)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = (
        f'attachment; filename="ingresos_{timezone.now().strftime("%Y%m%d")}.csv"'
    )

    writer = csv.writer(response)
    writer.writerow(
        [
            "Fecha",
            "Paciente",
            "Concepto",
            "Monto",
            "IGV",
            "Método Pago",
            "Referencia",
            "Comisión",
            "Monto Neto",
        ]
    )

    for pago in pagos:
        writer.writerow(
            [
                pago.fecha_pago.strftime("%d/%m/%Y %H:%M"),
                f"{pago.cobro.paciente.nombre} {pago.cobro.paciente.apellido}"
                if pago.cobro
                else "N/A",
                pago.cobro.get_concepto_display() if pago.cobro else "N/A",
                pago.monto,
                pago.cobro.igv if pago.cobro else 0,
                pago.get_metodo_pago_display(),
                pago.referencia,
                pago.comision_stripe,
                pago.monto_neto,
            ]
        )

    return response


# ─── Descarga de PDF ──────────────────────────────────────────────────────────

@login_required
def factura_descargar_pdf(request, pk):
    """Genera y descarga el PDF de una factura."""
    factura = get_object_or_404(
        Factura, pk=pk, nutricionista=request.user
    )

    if factura.estado == EstadoFactura.BORRADOR:
        messages.warning(request, "No se puede descargar PDF de una factura en borrador.")
        return redirect("facturacion:factura_detalle", pk=factura.pk)

    try:
        pdf_bytes = generar_pdf_factura(factura)

        # Guardar el PDF en la factura si no existe
        if not factura.archivo_pdf:
            from django.core.files.base import ContentFile
            filename = f"factura_{factura.numero_factura}.pdf"
            factura.archivo_pdf.save(filename, ContentFile(pdf_bytes), save=True)

        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="factura_{factura.numero_factura}.pdf"'
        )
        return response
    except Exception as e:
        messages.error(request, f"Error al generar el PDF: {str(e)}")
        return redirect("facturacion:factura_detalle", pk=factura.pk)


# ─── Stripe Checkout ──────────────────────────────────────────────────────────

@login_required
def crear_checkout_cobro(request, pk):
    """Registra el pago de un cobro (simulado, sin Stripe real)."""
    cobro = get_object_or_404(Cobro, pk=pk, nutricionista=request.user)

    if cobro.estado != EstadoCobro.PENDIENTE:
        messages.warning(request, "Este cobro ya no está pendiente de pago.")
        return redirect("facturacion:cobro_detalle", pk=cobro.pk)

    from django.conf import settings
    if not getattr(settings, "PAYMENT_SANDBOX", True):
        messages.error(request, "El checkout simulado no está disponible en producción.")
        return redirect("facturacion:cobro_detalle", pk=cobro.pk)

    # Marcar cobro como pagado
    cobro.estado = EstadoCobro.PAGADO
    cobro.fecha_pago = timezone.now()
    cobro.metodo_pago_usado = MetodoPago.EFECTIVO
    cobro.save()

    # Crear registro de pago
    comision = calcular_comision_stripe(cobro.total)
    Pago.objects.create(
        nutricionista=request.user,
        cobro=cobro,
        monto=cobro.total,
        metodo_pago=MetodoPago.EFECTIVO,
        referencia=generar_referencia_pago(MetodoPago.EFECTIVO),
        estado=EstadoPago.COMPLETADO,
        comision_stripe=comision,
        monto_neto=cobro.total - comision,
    )

    messages.success(request, "Pago registrado exitosamente.")
    return redirect("facturacion:cobro_detalle", pk=cobro.pk)


@login_required
def crear_checkout_suscripcion(request):
    """Activa la suscripción del nutricionista (simulado, con validación de método de pago)."""
    if request.method == "GET":
        plan_id = request.GET.get("plan")
        tipo = request.GET.get("tipo_facturacion", "mensual")

        if not plan_id:
            messages.error(request, "Selecciona un plan.")
            return redirect("facturacion:suscripcion_cambiar")

        plan = get_object_or_404(PlanSuscripcion, pk=plan_id, activo=True)
        precio = plan.precio_anual if tipo == "anual" else plan.precio_mensual

        # Si el plan es gratuito (Prueba Gratis), activarlo directamente sin mostrar checkout
        if precio == 0:
            from facturacion.utils import calcular_fecha_fin
            suscripcion, _ = SuscripcionNutricionista.objects.update_or_create(
                nutricionista=request.user,
                defaults={
                    "plan": plan,
                    "tipo_facturacion": tipo,
                    "precio_aplicado": precio,
                    "estado": EstadoSuscripcion.ACTIVA,
                    "fecha_inicio": timezone.now().date(),
                    "fecha_fin": calcular_fecha_fin(timezone.now().date(), tipo),
                },
            )

            Pago.objects.create(
                nutricionista=request.user,
                monto=precio,
                metodo_pago=MetodoPago.EFECTIVO,
                referencia=f"SUS-{request.user.pk}-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                estado=EstadoPago.COMPLETADO,
                comision_stripe=Decimal("0.00"),
                monto_neto=precio,
                notas=f"Registro de plan {plan.nombre} (Gratuito)",
            )

            messages.success(
                request,
                f"Plan {plan.nombre} activado exitosamente.",
            )
            return redirect("facturacion:suscripcion_detalle")

        # Buscar el método de pago guardado del nutricionista
        ultimo_pago = request.user.pagos_facturacion.filter(estado="completado").order_by("-fecha_pago").first()
        metodo_guardado = None
        if ultimo_pago and "removido" not in ultimo_pago.notas:
            if "Tarjeta terminada en" in ultimo_pago.notas:
                digitos = ultimo_pago.notas.split("terminada en")[-1].strip()
                metodo_guardado = {
                    "tipo": "tarjeta",
                    "detalle": f"Tarjeta terminada en {digitos}"
                }
            elif "Celular Yape:" in ultimo_pago.notas:
                partes = ultimo_pago.notas.split("Celular Yape:")[-1].strip().split(" - Código:")
                celular = partes[0].strip()
                codigo = partes[1].strip() if len(partes) > 1 else ""
                detalle = f"Celular: {celular}"
                if codigo:
                    detalle += f" (Código: {codigo})"
                metodo_guardado = {
                    "tipo": "yape",
                    "detalle": detalle
                }
            elif "PayPal Email:" in ultimo_pago.notas:
                email_paypal = ultimo_pago.notas.split("PayPal Email:")[-1].strip()
                metodo_guardado = {
                    "tipo": "paypal",
                    "detalle": f"PayPal ({email_paypal})"
                }

        # Renderizar la pasarela de pagos intermedia dedicada
        return render(
            request,
            "facturacion/suscripcion/checkout_suscripcion.html",
            {
                "plan": plan,
                "tipo_facturacion": tipo,
                "precio": precio,
                "metodo_guardado": metodo_guardado
            }
        )

    # Si es POST, procesamos el pago
    plan_id = request.POST.get("plan")
    tipo = request.POST.get("tipo_facturacion", "mensual")

    if not plan_id:
        messages.error(request, "Selecciona un plan.")
        return redirect("facturacion:suscripcion_cambiar")

    plan = get_object_or_404(PlanSuscripcion, pk=plan_id, activo=True)
    precio = plan.precio_anual if tipo == "anual" else plan.precio_mensual

    # 1. Comprobar si el usuario ya tiene un método de pago guardado
    ultimo_pago = request.user.pagos_facturacion.filter(estado="completado").order_by("-fecha_pago").first()
    tiene_metodo = False
    if ultimo_pago and "removido" not in ultimo_pago.notas:
        if "Tarjeta terminada en" in ultimo_pago.notas or "Celular Yape:" in ultimo_pago.notas or "PayPal Email:" in ultimo_pago.notas:
            tiene_metodo = True

    # 2. Si el plan es de pago (precio > 0) y no tiene método guardado (o decidió usar uno nuevo), validar y guardar
    notas_pago = f"Cobro inicial plan {plan.nombre} ({tipo})"
    metodo_usado = MetodoPago.EFECTIVO # Default
    
    # Comprobamos si explícitamente se envió un payment_method en el POST
    nuevo_metodo_enviado = "payment_method" in request.POST

    if precio > 0:
        if not tiene_metodo or nuevo_metodo_enviado:
            payment_method = request.POST.get("payment_method")
            if not payment_method:
                messages.error(request, "Por favor, selecciona un método de pago para activar tu plan de pago.")
                return redirect(f"/facturacion/suscripcion/checkout/?plan={plan.pk}&tipo_facturacion={tipo}")
                
            if payment_method == "tarjeta":
                nro_tarjeta = request.POST.get("nro_tarjeta")
                if not nro_tarjeta or len(nro_tarjeta.strip()) < 15:
                    messages.error(request, "Número de tarjeta inválido.")
                    return redirect(f"/facturacion/suscripcion/checkout/?plan={plan.pk}&tipo_facturacion={tipo}")
                notas_pago += f" - Tarjeta terminada en {nro_tarjeta.strip()[-4:]}"
                metodo_usado = MetodoPago.STRIPE # Se mapea como tarjeta
            elif payment_method == "yape":
                celular_yape = request.POST.get("celular_yape")
                codigo_yape = request.POST.get("codigo_yape")
                if not celular_yape or len(celular_yape.strip()) != 9:
                    messages.error(request, "El número de celular de Yape debe tener 9 dígitos.")
                    return redirect(f"/facturacion/suscripcion/checkout/?plan={plan.pk}&tipo_facturacion={tipo}")
                if not codigo_yape or len(codigo_yape.strip()) != 6 or not codigo_yape.strip().isdigit():
                    messages.error(request, "El código de aprobación de Yape debe tener 6 dígitos numéricos.")
                    return redirect(f"/facturacion/suscripcion/checkout/?plan={plan.pk}&tipo_facturacion={tipo}")
                notas_pago += f" - Celular Yape: {celular_yape.strip()} - Código: {codigo_yape.strip()}"
                metodo_usado = MetodoPago.YAPE
            elif payment_method == "paypal":
                email_paypal = request.POST.get("email_paypal")
                if not email_paypal or "@" not in email_paypal:
                    messages.error(request, "Correo electrónico de PayPal inválido.")
                    return redirect(f"/facturacion/suscripcion/checkout/?plan={plan.pk}&tipo_facturacion={tipo}")
                notas_pago += f" - PayPal Email: {email_paypal.strip()}"
                metodo_usado = MetodoPago.PAYPAL
        else:
            # Reutilizar el método de pago guardado anterior
            metodo_usado = ultimo_pago.metodo_pago
            if "Tarjeta terminada en" in ultimo_pago.notas:
                digitos = ultimo_pago.notas.split("terminada en")[-1].strip()
                notas_pago += f" - Tarjeta terminada en {digitos}"
            elif "Celular Yape:" in ultimo_pago.notas:
                celular = ultimo_pago.notas.split("Celular Yape:")[-1].strip()
                notas_pago += f" - Celular Yape: {celular}"
            elif "PayPal Email:" in ultimo_pago.notas:
                email = ultimo_pago.notas.split("PayPal Email:")[-1].strip()
                notas_pago += f" - PayPal Email: {email}"
    else:
        # Plan gratuito
        notas_pago = f"Registro de plan {plan.nombre} (Gratuito)"

    # 3. Activar suscripción directamente
    from facturacion.utils import calcular_fecha_fin
    suscripcion, _ = SuscripcionNutricionista.objects.update_or_create(
        nutricionista=request.user,
        defaults={
            "plan": plan,
            "tipo_facturacion": tipo,
            "precio_aplicado": precio,
            "estado": EstadoSuscripcion.ACTIVA,
            "fecha_inicio": timezone.now().date(),
            "fecha_fin": calcular_fecha_fin(timezone.now().date(), tipo),
        },
    )

    # 4. Crear registro de pago para que figure en ingresos
    Pago.objects.create(
        nutricionista=request.user,
        monto=precio,
        metodo_pago=metodo_usado,
        referencia=f"SUS-{request.user.pk}-{timezone.now().strftime('%Y%m%d%H%M%S')}",
        estado=EstadoPago.COMPLETADO,
        comision_stripe=Decimal("0.00"),
        monto_neto=precio,
        notas=notas_pago,
    )

    messages.success(
        request,
        f"Plan {plan.nombre} activado exitosamente.",
    )
    return redirect("facturacion:suscripcion_detalle")


@login_required
def checkout_exito(request):
    """Página de éxito post-pago en Stripe Checkout."""
    from django.conf import settings
    if not getattr(settings, "PAYMENT_SANDBOX", True):
        messages.error(request, "El callback de simulación no está disponible en producción.")
        return redirect("facturacion:cobros_lista")

    tipo = request.GET.get("type", "")

    if tipo == "cobro":
        cobro_id = request.GET.get("id")
        session_id = request.GET.get("session_id")
        if cobro_id:
            try:
                if not session_id:
                    messages.warning(request, "Solicitud de pago incompleta o inválida.")
                    return redirect("facturacion:cobro_detalle", pk=cobro_id)

                cobro = Cobro.objects.get(pk=cobro_id, nutricionista=request.user)
                if cobro.estado == EstadoCobro.PENDIENTE:
                    # Marcar como pagado (el webhook también lo hará)
                    cobro.estado = EstadoCobro.PAGADO
                    cobro.fecha_pago = timezone.now()
                    cobro.metodo_pago_usado = MetodoPago.STRIPE
                    cobro.save()

                    Pago.objects.create(
                        cobro=cobro,
                        monto=cobro.total,
                        metodo_pago=MetodoPago.STRIPE,
                        referencia=f"CHECKOUT-{cobro.pk}",
                        estado=EstadoPago.COMPLETADO,
                        comision_stripe=calcular_comision_stripe(cobro.total),
                        monto_neto=cobro.total - calcular_comision_stripe(cobro.total),
                    )
            except Cobro.DoesNotExist:
                pass
        messages.success(request, "Pago procesado exitosamente.")
        return redirect("facturacion:cobro_detalle", pk=cobro_id)

    elif tipo == "suscripcion":
        plan_id = request.GET.get("plan")
        tipo_fact = request.GET.get("tipo", "mensual")
        if plan_id:
            try:
                plan = PlanSuscripcion.objects.get(pk=plan_id)
                precio = plan.precio_anual if tipo_fact == "anual" else plan.precio_mensual
                from facturacion.utils import calcular_fecha_fin
                SuscripcionNutricionista.objects.update_or_create(
                    nutricionista=request.user,
                    defaults={
                        "plan": plan,
                        "tipo_facturacion": tipo_fact,
                        "precio_aplicado": precio,
                        "estado": EstadoSuscripcion.ACTIVA,
                        "fecha_inicio": timezone.now().date(),
                        "fecha_fin": calcular_fecha_fin(timezone.now().date(), tipo_fact),
                    },
                )
            except PlanSuscripcion.DoesNotExist:
                pass
        messages.success(request, "Suscripción activada exitosamente.")
        return redirect("facturacion:suscripcion_detalle")

    messages.success(request, "Pago procesado exitosamente.")
    return redirect("facturacion:facturacion_dashboard")


@login_required
def checkout_cancelado(request):
    """Página de cancelación del pago."""
    tipo = request.GET.get("type", "")
    if tipo == "cobro":
        cobro_id = request.GET.get("id")
        if cobro_id:
            messages.info(request, "El pago fue cancelado. Puedes intentar de nuevo.")
            return redirect("facturacion:cobro_detalle", pk=cobro_id)
    elif tipo == "suscripcion":
        messages.info(request, "El pago fue cancelado. Puedes elegir otro plan.")
        return redirect("facturacion:suscripcion_cambiar")

    messages.info(request, "El pago fue cancelado.")
    return redirect("facturacion:facturacion_dashboard")


# ─── AJAX para información de plan ────────────────────────────────────────────

@login_required
def ajax_info_plan(request, plan_id):
    """Retorna la información de un plan de suscripción (AJAX)."""
    try:
        plan = PlanSuscripcion.objects.get(pk=plan_id, activo=True)
        return JsonResponse({
            "nombre": plan.nombre,
            "descripcion": plan.descripcion,
            "precio_mensual": float(plan.precio_mensual),
            "precio_anual": float(plan.precio_anual),
            "limite_pacientes": plan.limite_pacientes,
            "limite_citas_mes": plan.limite_citas_mes,
            "comision_cobros": float(plan.comision_cobros),
        })
    except PlanSuscripcion.DoesNotExist:
        return JsonResponse({"error": "Plan no encontrado"}, status=404)


# ─── AJAX Endpoints ───────────────────────────────────────────────────────────

@login_required
def ajax_calcular_igv(request):
    """Calcula IGV y total para un monto dado (AJAX)."""
    monto = request.GET.get("monto", 0)
    try:
        monto = Decimal(monto)
        igv = monto * Decimal("0.18")
        total = monto + igv
        return JsonResponse(
            {
                "monto": float(monto),
                "igv": float(round(igv, 2)),
                "total": float(round(total, 2)),
            }
        )
    except (ValueError, TypeError):
        return JsonResponse({"error": "Monto inválido"}, status=400)


@login_required
def ajax_cobros_pendientes_paciente(request, paciente_id):
    """Lista los cobros pendientes de un paciente (AJAX)."""
    cobros = Cobro.objects.filter(
        nutricionista=request.user,
        paciente_id=paciente_id,
        estado=EstadoCobro.PENDIENTE,
    ).values("id", "concepto", "total", "fecha_creacion")

    return JsonResponse({"cobros": list(cobros)})


# ─── Boletas PDF ────────────────────────────────────────────────────────────

@login_required
def cobro_descargar_boleta(request, pk):
    """Genera y descarga una boleta PDF para un cobro."""
    cobro = get_object_or_404(Cobro, pk=pk, nutricionista=request.user)

    pdf_bytes = generar_pdf_boleta_cobro(cobro)

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    filename = f"boleta_cobro_{cobro.pk}.pdf"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@login_required
def suscripcion_descargar_boleta(request):
    """Genera y descarga una boleta PDF para la suscripción."""
    try:
        suscripcion = SuscripcionNutricionista.objects.get(
            nutricionista=request.user
        )
    except SuscripcionNutricionista.DoesNotExist:
        messages.error(request, "No tienes una suscripción activa.")
        return redirect("facturacion:suscripcion_detalle")

    pago = Pago.objects.filter(
        nutricionista=request.user,
        notas__icontains="Suscripción",
    ).order_by("-fecha_pago").first()

    if not pago:
        messages.error(request, "No se encontró un pago de suscripción para generar boleta.")
        return redirect("facturacion:suscripcion_detalle")

    pdf_bytes = generar_pdf_boleta_suscripcion(suscripcion, pago)

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    filename = f"boleta_suscripcion_{suscripcion.pk}.pdf"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
