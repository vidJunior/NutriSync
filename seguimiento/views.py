# seguimiento/views.py
# Vistas de seguimiento corporal y notas clínicas.
# Todas las vistas filtran por nutricionista.

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import ListView, CreateView, DetailView
from django.urls import reverse_lazy
from django.db.models import Q, Count
from django.utils import timezone
from itertools import chain

from .models import MedidaCorporal, NotaClinica
from .forms import MedidaCorporalForm, NotaClinicaForm
from pacientes.models import Paciente
from config.choices import TipoNota


# Aislamiento por nutricionista
# Medidas y notas se filtran mediante el paciente.


class NutricionistaSeguimientoMixin(LoginRequiredMixin):
    """
    Mixin que filtra las queries por el nutricionista autenticado.
    Como MedidaCorporal y NotaClinica tienen FK a Paciente (que tiene FK a User),
    el filtro atraviesa la relación: paciente__nutricionista.
    """

    def get_queryset(self):
        return super().get_queryset().filter(
            paciente__nutricionista=self.request.user
        )

    def get_paciente(self):
        """Obtiene el paciente asegurando que pertenece al nutricionista."""
        paciente_pk = self.kwargs.get("paciente_pk")
        return get_object_or_404(
            Paciente, pk=paciente_pk, nutricionista=self.request.user
        )


class MedidaCreateView(NutricionistaSeguimientoMixin, CreateView):
    """Registra una nueva medida corporal para un paciente específico."""

    model = MedidaCorporal
    form_class = MedidaCorporalForm
    template_name = "seguimiento/medida_form.html"

    def dispatch(self, request, *args, **kwargs):
        # Verifica que el paciente pertenezca al nutricionista.
        self.paciente = self.get_paciente()
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["paciente"] = self.paciente
        return context

    def form_valid(self, form):
        form.instance.paciente = self.paciente
        from datetime import date
        form.instance.fecha = date.today()
        messages.success(
            self.request,
            f"Medidas registradas para {self.paciente.nombre_completo}.",
        )
        return super().form_valid(form)

    def get_initial(self):
        initial = super().get_initial()
        # Precarga la última medida del paciente.
        ultima_medida = self.paciente.medidas.order_by("-fecha", "-fecha_registro").first()
        
        if ultima_medida:
            initial["talla_cm"] = ultima_medida.talla_cm
            initial["peso_kg"] = ultima_medida.peso_kg
        else:
            # Usa los datos de referencia si no hay medidas.
            if self.paciente.talla:
                initial["talla_cm"] = self.paciente.talla
            if self.paciente.peso:
                initial["peso_kg"] = self.paciente.peso
        return initial

    def get_success_url(self):
        return reverse_lazy("seguimiento:medidas_lista", kwargs={"paciente_pk": self.paciente.pk})


class MedidaListView(NutricionistaSeguimientoMixin, ListView):
    """
    Historial de medidas corporales con indicadores de cambio.
    Cada fila muestra ▲ (mejora) o ▼ (empeora) respecto a la medición anterior.
    """

    model = MedidaCorporal
    template_name = "seguimiento/medidas.html"
    context_object_name = "medidas"
    paginate_by = 15

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        self.paciente = self.get_paciente()
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        # Carga las medidas recientes sin consultas N+1.
        return (
            super()
            .get_queryset()
            .filter(paciente=self.paciente)
            .select_related("paciente")
            .order_by("-fecha", "-fecha_registro")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["paciente"] = self.paciente

        # Compara cada medida con la anterior.
        historial = self.get_queryset()
        medidas_pagina = list(context["medidas"])
        medida_siguiente = None
        if context["page_obj"].has_next():
            inicio_siguiente = context["page_obj"].end_index()
            siguiente = list(historial[inicio_siguiente:inicio_siguiente + 1])
            medida_siguiente = siguiente[0] if siguiente else None

        registros = []
        for indice, medida in enumerate(medidas_pagina):
            anterior = (
                medidas_pagina[indice + 1]
                if indice + 1 < len(medidas_pagina)
                else medida_siguiente
            )
            registros.append({
                "medida": medida,
                "anterior": anterior,
                "cambio_peso": self._comparar(
                    medida.peso_kg,
                    anterior.peso_kg if anterior else None,
                ),
                "cambio_imc": self._comparar(
                    medida.imc,
                    anterior.imc if anterior else None,
                ),
                "variacion_peso": (
                    medida.peso_kg - anterior.peso_kg
                    if anterior and medida.peso_kg is not None and anterior.peso_kg is not None
                    else None
                ),
                "variacion_imc": (
                    medida.imc - anterior.imc
                    if anterior and medida.imc is not None and anterior.imc is not None
                    else None
                ),
            })
        context["registros"] = registros

        total_medidas = context["paginator"].count
        ultima_medida = historial.first()
        primera_medida = historial.last() if total_medidas > 1 else None

        context["total_medidas"] = total_medidas
        context["ultima_medida"] = ultima_medida
        context["primera_medida"] = primera_medida
        context["variacion_total_peso"] = (
            ultima_medida.peso_kg - primera_medida.peso_kg
            if ultima_medida and primera_medida
            else None
        )
        context["variacion_total_imc"] = (
            ultima_medida.imc - primera_medida.imc
            if ultima_medida and primera_medida
            else None
        )
        context["dias_seguimiento"] = (
            (ultima_medida.fecha - primera_medida.fecha).days
            if ultima_medida and primera_medida
            else 0
        )

        return context

    @staticmethod
    def _comparar(actual, anterior):
        """
        Compara dos valores y devuelve un indicador.
        None si no hay dato anterior. 'subio' o 'bajo' si hay cambio.
        En medidas corporales, subir peso/IMC/grasa generalmente es negativo
        y bajar es positivo, pero mostramos el dato objetivo sin juzgar.
        """
        if anterior is None or actual is None:
            return None
        if actual > anterior:
            return "subio"
        elif actual < anterior:
            return "bajo"
        return "igual"


class NotaCreateView(NutricionistaSeguimientoMixin, CreateView):
    """Crea una nueva nota clínica para un paciente, opcionalmente vinculada a una cita."""

    model = NotaClinica
    form_class = NotaClinicaForm
    template_name = "seguimiento/nota_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.paciente = self.get_paciente()
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["paciente"] = self.paciente
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Filtra las citas por paciente.
        kwargs["paciente"] = self.paciente
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        from django.utils import timezone

        hoy = timezone.now().date()
        p = self.paciente

        # Número de consulta
        num_consulta = p.notas_clinicas.count() + 1
        initial["titulo"] = f"Consulta #{num_consulta} — {hoy.strftime('%d/%m/%Y')}"
        initial["fecha"] = hoy

        # Motivo de consulta
        info = p.informacion_clinica or {}
        objetivo = info.get("objetivo_principal") or p.notas_generales or "No especificado"
        # Quita el prefijo del motivo.
        if "Motivo de Consulta:" in objetivo:
            objetivo = objetivo.split("Motivo de Consulta:")[-1].split("\n")[0].strip()
        initial["motivo_consulta"] = objetivo

        # Resumen automático
        lineas = []

        # Sección 1: Información del paciente
        lineas.append("═══ INFORMACIÓN DEL PACIENTE ═══")
        lineas.append(f"• Edad: {p.edad} años  |  Sexo: {p.get_sexo_display() if hasattr(p, 'get_sexo_display') else p.sexo}")
        if p.ocupacion:
            lineas.append(f"• Ocupación: {p.ocupacion}")
        lineas.append(f"• Objetivo principal: {objetivo}")

        # Condiciones médicas y alergias
        if p.condiciones_medicas:
            lineas.append(f"• Condiciones: {p.condiciones_medicas}")
        if p.alergias:
            lineas.append(f"• Alergias: {p.alergias}")

        # Hábitos desde informacion_clinica JSON
        if info:
            if info.get("nivel_actividad"):
                lineas.append(f"• Nivel de actividad: {info.get('nivel_actividad')}")
            if info.get("horas_sueno"):
                lineas.append(f"• Horas de sueño: {info.get('horas_sueno')}")

        # Sección 2: Últimas mediciones
        ultima_medida = p.medidas.order_by("-fecha", "-fecha_registro").first()
        if ultima_medida:
            lineas.append("")
            lineas.append("═══ ÚLTIMAS MEDICIONES ═══")
            lineas.append(f"• Fecha: {ultima_medida.fecha.strftime('%d/%m/%Y')}")
            lineas.append(f"• Peso: {ultima_medida.peso_kg} kg  |  Talla: {ultima_medida.talla_cm} cm  |  IMC: {ultima_medida.imc}")
            if ultima_medida.grasa_corporal_pct:
                lineas.append(f"• Grasa corporal: {ultima_medida.grasa_corporal_pct}%")
            if ultima_medida.masa_muscular_pct:
                lineas.append(f"• Masa muscular: {ultima_medida.masa_muscular_pct}%")
            if ultima_medida.cintura_cm:
                lineas.append(f"• Cintura: {ultima_medida.cintura_cm} cm", )
            if ultima_medida.cadera_cm:
                lineas[-1] += f"  |  Cadera: {ultima_medida.cadera_cm} cm"

        # Sección 3: Evaluación nutricional
        evaluacion = p.evaluacion or {}
        if evaluacion:
            lineas.append("")
            lineas.append("═══ EVALUACIÓN NUTRICIONAL ═══")
            if evaluacion.get("diagnostico"):
                lineas.append(f"• Diagnóstico: {evaluacion.get('diagnostico')}")
            if evaluacion.get("calorias_recomendadas"):
                lineas.append(f"• Calorías recomendadas: {evaluacion.get('calorias_recomendadas')} kcal")
            if p.imc_inicial and p.imc_clasificacion:
                lineas.append(f"• IMC inicial: {p.imc_inicial} ({p.imc_clasificacion})")

        # Sección 4: Plan alimentario activo
        plan_activo = p.planes_alimentarios_sync.filter(estado="Activo").order_by("-fecha_inicio").first()
        if plan_activo:
            lineas.append("")
            lineas.append("═══ PLAN ALIMENTARIO ACTIVO ═══")
            lineas.append(f"• Plan: {plan_activo.nombre}")
            lineas.append(f"• Calorías: {plan_activo.calorias} kcal  |  Proteínas: {plan_activo.proteinas}g  |  Carbs: {plan_activo.carbohidratos}g  |  Grasas: {plan_activo.grasas}g")
            if plan_activo.fecha_inicio:
                lineas.append(f"• Inicio: {plan_activo.fecha_inicio.strftime('%d/%m/%Y')}")

        # Sección 5: Seguimiento de adherencia
        seguimiento_data = p.seguimiento or {}
        if seguimiento_data:
            lineas.append("")
            lineas.append("═══ SEGUIMIENTO ═══")
            if seguimiento_data.get("adherencia"):
                lineas.append(f"• Adherencia al plan: {seguimiento_data.get('adherencia')}")
            if seguimiento_data.get("nivel_hambre"):
                lineas.append(f"• Nivel de hambre: {seguimiento_data.get('nivel_hambre')}")
            if seguimiento_data.get("dificultades"):
                lineas.append(f"• Dificultades: {seguimiento_data.get('dificultades')}")

        initial["resumen_consulta"] = "\n".join(lineas)

        # Cargar objetivos acordados de la última nota clínica
        ultima_nota = p.notas_clinicas.order_by("-fecha", "-fecha_creacion").first()
        if ultima_nota and ultima_nota.objetivos_acordados:
            initial["objetivos_acordados"] = ultima_nota.objetivos_acordados
        if ultima_nota and ultima_nota.plan_accion:
            initial["plan_accion"] = f"[Revisión de acuerdos previos]\n{ultima_nota.plan_accion}"

        return initial


    def form_valid(self, form):
        form.instance.paciente = self.paciente
        messages.success(
            self.request,
            f"Nota clínica '{form.instance.titulo}' creada para {self.paciente.nombre_completo}.",
        )
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("seguimiento:notas_lista", kwargs={"paciente_pk": self.paciente.pk})


class NotaListView(NutricionistaSeguimientoMixin, ListView):
    """Lista de notas clínicas de un paciente con filtro por tipo."""

    model = NotaClinica
    template_name = "seguimiento/notas.html"
    context_object_name = "notas"
    paginate_by = 15

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        self.paciente = self.get_paciente()
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        qs = super().get_queryset().filter(paciente=self.paciente)
        qs = qs.select_related("paciente", "cita")

        # Filtro opcional por tipo de nota
        tipo = self.request.GET.get("tipo", "")
        if tipo:
            qs = qs.filter(tipo=tipo)

        return qs.order_by("-fecha", "-fecha_creacion")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["paciente"] = self.paciente
        context["tipo_seleccionado"] = self.request.GET.get("tipo", "")

        notas_expediente = self.paciente.notas_clinicas.all()
        conteos = {
            fila["tipo"]: fila["total"]
            for fila in notas_expediente.order_by()
            .values("tipo")
            .annotate(total=Count("id"))
        }
        total_notas = sum(conteos.values())
        context["total_notas"] = total_notas
        context["ultima_nota"] = notas_expediente.order_by(
            "-fecha", "-fecha_creacion"
        ).first()
        context["filtros_nota"] = [
            {"valor": "", "etiqueta": "Todas", "total": total_notas},
            *[
                {
                    "valor": valor,
                    "etiqueta": etiqueta,
                    "total": conteos.get(valor, 0),
                }
                for valor, etiqueta in TipoNota.CHOICES
            ],
        ]
        return context


class NotaDetailView(NutricionistaSeguimientoMixin, DetailView):
    """Muestra el detalle completo de una nota clínica."""

    model = NotaClinica
    template_name = "seguimiento/nota_detalle.html"
    context_object_name = "nota"

    def get_queryset(self):
        # Precarga paciente y cita.
        return super().get_queryset().select_related("paciente", "cita")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Añade datos de la cita vinculada.
        if self.object.cita:
            context["cita"] = self.object.cita
        return context


@login_required
def historial_paciente(request, paciente_pk):
    """
    Timeline cronológico que unifica medidas, notas y citas del paciente.
    Muestra todo el historial ordenado por fecha descendente para una visión
    integral de la evolución del paciente.
    """
    # Verificar que el paciente pertenece al nutricionista
    paciente = get_object_or_404(
        Paciente, pk=paciente_pk, nutricionista=request.user
    )

    # Reúne medidas, notas y citas para la plantilla.
    medidas = MedidaCorporal.objects.filter(paciente=paciente).order_by("-fecha", "-fecha_registro")
    notas = NotaClinica.objects.filter(paciente=paciente).select_related("cita").order_by("-fecha", "-fecha_creacion")
    citas = paciente.citas.select_related("paciente").order_by("-fecha_hora")

    # Unifica los eventos del historial.
    eventos = []

    for m in medidas:
        eventos.append({
            "fecha": m.fecha,
            "fecha_display": m.fecha.strftime("%d/%m/%Y"),
            "tipo": "medida",
            "icono": "activity",
            "color": "teal",
            "titulo": f"Medidas: {m.peso_kg} kg — IMC {m.imc}",
            "detalle": f"Cintura: {m.cintura_cm or '—'} cm | Cadera: {m.cadera_cm or '—'} cm",
            "url": None,
            "objeto": m,
        })

    for n in notas:
        eventos.append({
            "fecha": n.fecha,
            "fecha_display": n.fecha.strftime("%d/%m/%Y"),
            "tipo": "nota",
            "icono": "clipboard-list",
            "color": "indigo",
            "titulo": n.titulo,
            "detalle": n.get_tipo_display(),
            "url": reverse_lazy("seguimiento:notas_detalle", kwargs={"pk": n.pk}),
            "objeto": n,
        })

    for c in citas:
        eventos.append({
            "fecha": c.fecha_hora.date(),
            "fecha_display": c.fecha_hora.strftime("%d/%m/%Y %H:%M"),
            "tipo": "cita",
            "icono": "calendar",
            "color": "amber",
            "titulo": f"Cita: {c.get_tipo_display()}",
            "detalle": f"{c.get_estado_display()} · {c.duracion_minutos} min",
            "url": reverse_lazy("agendas:detalle", kwargs={"pk": c.pk}),
            "objeto": c,
        })

    # Ordenar todos los eventos por fecha descendente
    eventos.sort(key=lambda e: e["fecha"], reverse=True)

    context = {
        "paciente": paciente,
        "eventos": eventos,
        "total_medidas": len(medidas),
        "total_notas": len(notas),
        "total_citas": len(citas),
    }
    return render(request, "seguimiento/historial.html", context)


# Paneles de seguimiento


@login_required
def seguimiento_dashboard(request):
    """
    Vista general de seguimiento: lista todos los pacientes del nutricionista
    con su última medición registrada. Accesible desde el sidebar.
    """
    pacientes = Paciente.objects.filter(
        nutricionista=request.user, estado=True
    ).order_by("nombre", "apellido")

    hoy = timezone.localdate()
    inicio_mes = hoy.replace(day=1)

    # Compara las dos últimas medidas.
    pacientes_con_medidas = []
    pacientes_con_medicion = 0
    controles_al_dia = 0
    for p in pacientes:
        medidas_recientes = list(
            MedidaCorporal.objects.filter(paciente=p)
            .order_by("-fecha", "-fecha_registro")[:2]
        )
        ultima = medidas_recientes[0] if medidas_recientes else None
        anterior = medidas_recientes[1] if len(medidas_recientes) > 1 else None
        variacion_peso = None
        variacion_imc = None
        dias_desde_medicion = None
        control_al_dia = False

        if ultima:
            pacientes_con_medicion += 1
            dias_desde_medicion = (hoy - ultima.fecha).days
            control_al_dia = 0 <= dias_desde_medicion <= 30
            if control_al_dia:
                controles_al_dia += 1
            if anterior:
                variacion_peso = ultima.peso_kg - anterior.peso_kg
                variacion_imc = ultima.imc - anterior.imc

        pacientes_con_medidas.append({
            "paciente": p,
            "ultima_medida": ultima,
            "medida_anterior": anterior,
            "variacion_peso": variacion_peso,
            "variacion_imc": variacion_imc,
            "dias_desde_medicion": dias_desde_medicion,
            "control_al_dia": control_al_dia,
        })

    total_pacientes = pacientes.count()
    medidas_qs = MedidaCorporal.objects.filter(
        paciente__nutricionista=request.user,
        paciente__estado=True,
    )
    context = {
        "pacientes_con_medidas": pacientes_con_medidas,
        "total_pacientes": total_pacientes,
        "pacientes_con_medicion": pacientes_con_medicion,
        "pacientes_sin_medicion": total_pacientes - pacientes_con_medicion,
        "controles_al_dia": controles_al_dia,
        "total_medidas": medidas_qs.count(),
        "medidas_este_mes": medidas_qs.filter(fecha__gte=inicio_mes).count(),
    }
    return render(request, "seguimiento/dashboard.html", context)


@login_required
def notas_dashboard(request):
    """
    Vista general de notas clínicas: muestra la lista de pacientes del nutricionista
    con el total de notas clínicas y la última nota registrada.
    Análogo a seguimiento_dashboard pero para notas.
    """
    pacientes = Paciente.objects.filter(
        nutricionista=request.user, estado=True
    ).order_by("nombre", "apellido")

    hoy = timezone.localdate()
    inicio_mes = hoy.replace(day=1)
    pacientes_con_notas = []
    pacientes_con_historial = 0
    notas_qs = NotaClinica.objects.filter(
        paciente__nutricionista=request.user,
        paciente__estado=True,
    )

    for p in pacientes:
        ultima_nota = p.notas_clinicas.order_by("-fecha", "-fecha_creacion").first()
        total_notas_paciente = p.notas_clinicas.count()
        dias_desde_nota = None
        if ultima_nota:
            pacientes_con_historial += 1
            dias_desde_nota = (hoy - ultima_nota.fecha).days
        pacientes_con_notas.append({
            "paciente": p,
            "ultima_nota": ultima_nota,
            "total_notas": total_notas_paciente,
            "dias_desde_nota": dias_desde_nota,
        })

    total_pacientes = pacientes.count()
    context = {
        "pacientes_con_notas": pacientes_con_notas,
        "total_pacientes": total_pacientes,
        "pacientes_con_historial": pacientes_con_historial,
        "pacientes_sin_notas": total_pacientes - pacientes_con_historial,
        "total_notas": notas_qs.count(),
        "notas_este_mes": notas_qs.filter(fecha__gte=inicio_mes).count(),
    }
    return render(request, "seguimiento/notas_dashboard.html", context)


