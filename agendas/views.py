# agendas/views.py
# Vistas para la gestión de citas en NutriSync — CRUD completo con aislamiento multi-nutricionista.

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.views.generic import ListView, CreateView, DetailView, UpdateView
from django.urls import reverse_lazy
from django.utils import timezone
from datetime import datetime, date, timedelta
import calendar
from django.db.models import Q
from django.http import JsonResponse
from .models import Cita
from .forms import CitaForm
from config.choices import TipoCita, EstadoCita
from seguimiento.models import MedidaCorporal
from pacientes.models import PlanAlimentario, Paciente
from django.core.exceptions import ValidationError


class NutricionistaCitaMixin(LoginRequiredMixin):
    """Mixin base para todas las vistas de citas. Filtra datos por nutricionista."""

    def get_queryset(self):
        # Aislamiento multi-nutricionista seguro
        # Evitamos N+1 cargando paciente en la misma consulta
        return Cita.objects.filter(paciente__nutricionista=self.request.user).select_related("paciente")



class CitaFormFragmentMixin:
    """Mixin para CreateView y UpdateView de Cita: renderiza fragmento cuando ?fragment=1."""

    def get_template_names(self):
        if self.request.GET.get("fragment"):
            return ["agendas/_form_content.html"]
        return super().get_template_names()

    def form_valid(self, form):
        from django.http import HttpResponse
        response = super().form_valid(form)
        is_ajax = (
            self.request.headers.get("X-Requested-With") == "XMLHttpRequest"
            or self.request.GET.get("fragment")
        )
        if is_ajax:
            return HttpResponse(
                '<div id="cita-form-success" data-success="true" data-pk="{}"></div>'.format(
                    self.object.pk
                )
            )
        return response

    def form_invalid(self, form):
        is_ajax = (
            self.request.headers.get("X-Requested-With") == "XMLHttpRequest"
            or self.request.GET.get("fragment")
        )
        if is_ajax:
            return self.render_to_response(self.get_context_data(form=form))
        return super().form_invalid(form)


# ─── Agenda / Listado de Citas ───────────────────────────────────────────────

class AgendaView(NutricionistaCitaMixin, ListView):
    """
    Lista las citas asociadas al nutricionista autenticado.
    Soporta filtros para visualización por Día, Semana, Mes y búsquedas.
    """

    model = Cita
    template_name = "agendas/agenda.html"
    context_object_name = "citas"

    def get_queryset(self):
        # Filtramos por citas asociadas al paciente del nutricionista logueado o directamente asociadas al nutricionista
        # (para bloqueos de horarios)
        qs = Cita.objects.filter(
            Q(paciente__nutricionista=self.request.user) | Q(nutricionista=self.request.user)
        ).select_related("paciente")
        
        # 1. Obtener fecha seleccionada
        fecha_str = self.request.GET.get("fecha")
        if fecha_str:
            try:
                self.selected_date = datetime.strptime(fecha_str, "%Y-%m-%d").date()
            except ValueError:
                self.selected_date = timezone.localtime(timezone.now()).date()
        else:
            self.selected_date = timezone.localtime(timezone.now()).date()

        # 2. Obtener filtro de tipo de vista (dia, semana, mes - por defecto: semana)
        self.vista = self.request.GET.get("vista", "semana")
        
        # 3. Aplicar filtros de fecha según vista
        if self.vista == "dia":
            qs = qs.filter(fecha_hora__date=self.selected_date)
        elif self.vista == "semana":
            # Obtener lunes de la semana de la fecha seleccionada
            lunes = self.selected_date - timedelta(days=self.selected_date.weekday())
            domingo = lunes + timedelta(days=6)
            qs = qs.filter(fecha_hora__date__range=[lunes, domingo])
        elif self.vista == "mes":
            # Rango del mes
            primer_dia = self.selected_date.replace(day=1)
            _, ult_dia_num = calendar.monthrange(self.selected_date.year, self.selected_date.month)
            ultimo_dia = self.selected_date.replace(day=ult_dia_num)
            qs = qs.filter(fecha_hora__date__range=[primer_dia, ultimo_dia])
        else:
            # Por defecto: todas las futuras
            hoy = timezone.localtime(timezone.now()).date()
            qs = qs.filter(fecha_hora__date__gte=hoy)

        # 4. Filtro de búsqueda por Paciente
        self.buscar = self.request.GET.get("buscar", "").strip()
        if self.buscar:
            qs = qs.filter(
                Q(paciente__nombre__icontains=self.buscar) | Q(paciente__apellido__icontains=self.buscar)
            )

        # 5. Filtros por Tipo y Estado
        self.filtro_tipo = self.request.GET.get("tipo", "").strip()
        if self.filtro_tipo:
            qs = qs.filter(tipo=self.filtro_tipo)

        self.filtro_estado = self.request.GET.get("estado", "").strip()
        if self.filtro_estado:
            qs = qs.filter(estado=self.filtro_estado)

        return qs.order_by("fecha_hora")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Pasar parámetros de búsqueda y filtros al contexto
        context["vista"] = self.vista
        context["selected_date"] = self.selected_date
        context["selected_date_str"] = self.selected_date.strftime("%Y-%m-%d")
        context["buscar"] = self.buscar
        context["filtro_tipo"] = self.filtro_tipo
        context["filtro_estado"] = self.filtro_estado
        
        # Choices para los filtros
        context["tipos_choices"] = TipoCita.CHOICES
        context["estados_choices"] = EstadoCita.CHOICES

        # Meses en español
        meses = {
            1: "enero", 2: "febrero", 3: "marzo", 4: "abril", 5: "mayo", 6: "junio",
            7: "julio", 8: "agosto", 9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"
        }
        
        # Días de la semana en español
        dias_semana_es = {
            0: "lunes", 1: "martes", 2: "miércoles", 3: "jueves", 4: "viernes", 5: "sábado", 6: "domingo"
        }

        # 1. Calcular fechas Anterior y Siguiente
        if self.vista == "dia":
            context["prev_date_str"] = (self.selected_date - timedelta(days=1)).strftime("%Y-%m-%d")
            context["next_date_str"] = (self.selected_date + timedelta(days=1)).strftime("%Y-%m-%d")
            # Label para vista Día
            context["semana_label"] = f"{dias_semana_es[self.selected_date.weekday()]}, {self.selected_date.day} de {meses[self.selected_date.month]} {self.selected_date.year}"
        elif self.vista == "semana":
            context["prev_date_str"] = (self.selected_date - timedelta(days=7)).strftime("%Y-%m-%d")
            context["next_date_str"] = (self.selected_date + timedelta(days=7)).strftime("%Y-%m-%d")
            # Label para vista Semana: e.g. "9 - 15 julio 2026"
            lunes = self.selected_date - timedelta(days=self.selected_date.weekday())
            domingo = lunes + timedelta(days=6)
            if lunes.month == domingo.month:
                context["semana_label"] = f"{lunes.day} - {domingo.day} {meses[lunes.month]} {lunes.year}"
            else:
                if lunes.year == domingo.year:
                    context["semana_label"] = f"{lunes.day} {meses[lunes.month]} - {domingo.day} {meses[domingo.month]} {lunes.year}"
                else:
                    context["semana_label"] = f"{lunes.day} {meses[lunes.month]} {lunes.year} - {domingo.day} {meses[domingo.month]} {domingo.year}"
        elif self.vista == "mes":
            # Mes anterior
            if self.selected_date.month == 1:
                prev_date = self.selected_date.replace(year=self.selected_date.year - 1, month=12, day=1)
            else:
                prev_date = self.selected_date.replace(month=self.selected_date.month - 1, day=1)
            # Mes siguiente
            if self.selected_date.month == 12:
                next_date = self.selected_date.replace(year=self.selected_date.year + 1, month=1, day=1)
            else:
                next_date = self.selected_date.replace(month=self.selected_date.month + 1, day=1)
            context["prev_date_str"] = prev_date.strftime("%Y-%m-%d")
            context["next_date_str"] = next_date.strftime("%Y-%m-%d")
            # Label para vista Mes: e.g. "Julio 2026"
            context["semana_label"] = f"{meses[self.selected_date.month]} {self.selected_date.year}".capitalize()

        # Indicador de hora actual
        ahora = timezone.localtime(timezone.now())
        context["ahora_date"] = ahora.date()
        lunes = self.selected_date - timedelta(days=self.selected_date.weekday())
        domingo = lunes + timedelta(days=6)
        
        if 7 <= ahora.hour < 24:
            mins = (ahora.hour - 7) * 60 + ahora.minute
            context["current_time_top_pct"] = (mins / 1020.0) * 100.0
        else:
            context["current_time_top_pct"] = None

        # 2. Generar datos del Calendario según vista
        citas_list = list(context["citas"])
        
        # Calcular posicionamiento vertical en grilla de horas (07:00 a 24:00 = 17 horas = 1020 minutos)
        for cita in citas_list:
            local_time = timezone.localtime(cita.fecha_hora)
            mins_since_start = (local_time.hour - 7) * 60 + local_time.minute
            if mins_since_start < 0:
                mins_since_start = 0
            elif mins_since_start > 1020:
                mins_since_start = 1020
                
            cita.top_pct = (mins_since_start / 1020.0) * 100.0
            
            dur = cita.duracion_minutos
            if mins_since_start + dur > 1020:
                dur = 1020 - mins_since_start
            cita.height_pct = (dur / 1020.0) * 100.0

        if self.vista == "dia":
            # Vista Día: Solo pasamos las citas del día, que ya están en context['citas']
            pass
            
        elif self.vista == "semana":
            # Vista Semana: Agrupar por día de la semana (Lunes a Domingo)
            lunes = self.selected_date - timedelta(days=self.selected_date.weekday())
            dias_semana = []
            for i in range(7):
                dia = lunes + timedelta(days=i)
                citas_dia = [c for c in citas_list if timezone.localtime(c.fecha_hora).date() == dia]
                dias_semana.append({
                    "fecha": dia,
                    "citas": citas_dia,
                })
            context["dias_semana"] = dias_semana
            
        elif self.vista == "mes":
            # Vista Mes: Retornar los días del mes en grilla (incluyendo padding de meses adyacentes)
            cal = calendar.Calendar(firstweekday=0)  # Lunes es 0
            grid_weeks = cal.monthdatescalendar(self.selected_date.year, self.selected_date.month)
            
            semanas_grid = []
            for week in grid_weeks:
                semana_dias = []
                for dia in week:
                    citas_dia = [c for c in citas_list if timezone.localtime(c.fecha_hora).date() == dia]
                    semana_dias.append({
                        "fecha": dia,
                        "es_mes_actual": dia.month == self.selected_date.month,
                        "citas": citas_dia,
                    })
                semanas_grid.append(semana_dias)
            context["semanas_grid"] = semanas_grid

        # 3. Estadísticas del Día (según la fecha seleccionada)
        # Excluimos los bloqueos de horario para las estadísticas
        qs_dia = Cita.objects.filter(
            Q(paciente__nutricionista=self.request.user) | Q(nutricionista=self.request.user),
            fecha_hora__date=self.selected_date
        ).exclude(tipo=TipoCita.BLOQUEO)
        
        context["consultas_dia"] = qs_dia.count()
        context["primeras_consultas"] = qs_dia.filter(tipo=TipoCita.PRIMERA_CONSULTA).count()
        context["seguimientos"] = qs_dia.filter(tipo=TipoCita.SEGUIMIENTO).count()
        context["completadas"] = qs_dia.filter(estado=EstadoCita.COMPLETADA).count()
        context["canceladas"] = qs_dia.filter(estado=EstadoCita.CANCELADA).count()
        
        # Pacientes únicos atendidos (con citas completadas ese día)
        context["pacientes_atendidos"] = qs_dia.filter(estado=EstadoCita.COMPLETADA).values("paciente").distinct().count()

        # 4. Próximas consultas del día (citas del día que aún no son canceladas, ordenadas por hora)
        # Se listan bajo el calendario
        context["citas_del_dia"] = qs_dia.exclude(estado=EstadoCita.CANCELADA).order_by("fecha_hora")

        # 5. Lista de todos los pacientes activos de este nutricionista (para el modal de Nueva Cita / Buscar)
        context["pacientes_activos"] = Paciente.objects.filter(
            nutricionista=self.request.user, estado=True
        ).order_by("nombre", "apellido")

        return context


# ─── Crear Cita ──────────────────────────────────────────────────────────────

class CitaCreateView(LoginRequiredMixin, CitaFormFragmentMixin, CreateView):
    """Permite agendar una nueva cita."""

    model = Cita
    form_class = CitaForm
    template_name = "agendas/form.html"

    def get_form_kwargs(self):
        # Pasamos el usuario logueado al formulario para filtrar sus pacientes activos
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        fecha_str = self.request.GET.get("fecha")
        hora_str = self.request.GET.get("hora")
        duracion = self.request.GET.get("duracion")
        if fecha_str and hora_str:
            initial["fecha_hora"] = f"{fecha_str}T{hora_str}"
        if duracion:
            initial["duracion_minutos"] = duracion
        return initial

    def get_success_url(self):
        from django.urls import reverse
        messages.success(
            self.request,
            f"Cita con {self.object.paciente.nombre_completo} programada con éxito."
        )
        paciente_id = self.request.GET.get("paciente") or self.request.POST.get("paciente")
        if paciente_id:
            return reverse("pacientes:detalle", kwargs={"pk": paciente_id})
        return reverse_lazy("agendas:agenda")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from config.choices import TipoCita
        import json
        
        # Guardamos de qué paciente viene si está en GET
        paciente_id = self.request.GET.get("paciente")
        context["from_paciente_id"] = paciente_id
        if paciente_id:
            context["paciente_obj"] = Paciente.objects.filter(pk=paciente_id, nutricionista=self.request.user).first()

        # Filtramos citas de tipo Primera Consulta para los pacientes de este nutricionista
        qs_primera = Cita.objects.filter(
            paciente__nutricionista=self.request.user,
            tipo=TipoCita.PRIMERA_CONSULTA
        )
        pacientes_con_primera = set(qs_primera.values_list("paciente_id", flat=True))
        context["tiene_primera_consulta_json"] = json.dumps({
            p_id: True for p_id in pacientes_con_primera
        })
        return context


# ─── Detalle de Cita ─────────────────────────────────────────────────────────

class CitaDetailView(NutricionistaCitaMixin, DetailView):
    """Muestra la ficha informativa y opciones rápidas para una cita específica."""

    model = Cita
    template_name = "agendas/detalle.html"
    context_object_name = "cita"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Opciones de estados para el cambio rápido en el detalle
        context["estados"] = EstadoCita.CHOICES
        # "No asistió" solo debe estar disponible si la cita ya inició o pasó en el tiempo
        context["puede_marcar_no_asistio"] = self.object.fecha_hora and self.object.fecha_hora < timezone.now()
        return context


# ─── Editar Cita ─────────────────────────────────────────────────────────────

class CitaUpdateView(NutricionistaCitaMixin, CitaFormFragmentMixin, UpdateView):
    """Permite modificar los datos de una cita existente."""

    model = Cita
    form_class = CitaForm
    template_name = "agendas/form.html"

    def get_form_kwargs(self):
        # Pasamos el usuario logueado al formulario
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_success_url(self):
        from django.urls import reverse
        messages.success(
            self.request,
            f"Cita con {self.object.paciente.nombre_completo} actualizada correctamente."
        )
        paciente_id = self.request.GET.get("paciente") or self.request.POST.get("paciente") or (self.object.paciente_id if self.object else None)
        if paciente_id:
            return reverse("pacientes:detalle", kwargs={"pk": paciente_id})
        return reverse_lazy("agendas:agenda")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from config.choices import TipoCita
        import json
        
        # Guardamos de qué paciente viene
        paciente_id = self.request.GET.get("paciente") or (self.object.paciente_id if self.object else None)
        context["from_paciente_id"] = paciente_id
        if paciente_id:
            context["paciente_obj"] = Paciente.objects.filter(pk=paciente_id, nutricionista=self.request.user).first()

        # Filtramos citas de tipo Primera Consulta para los pacientes de este nutricionista,
        # excluyendo la cita actual que estamos editando.
        qs_primera = Cita.objects.filter(
            paciente__nutricionista=self.request.user,
            tipo=TipoCita.PRIMERA_CONSULTA
        )
        if self.object and self.object.pk:
            qs_primera = qs_primera.exclude(pk=self.object.pk)
            
        pacientes_con_primera = set(qs_primera.values_list("paciente_id", flat=True))
        context["tiene_primera_consulta_json"] = json.dumps({
            p_id: True for p_id in pacientes_con_primera
        })
        return context


# ─── Cambio Rápido de Estado ──────────────────────────────────────────────────

@login_required
@require_POST
def cita_cambiar_estado(request, pk):
    """
    Permite cambiar rápidamente el estado de una cita (Completada, Cancelada, No asistió)
    desde botones de acción rápidos en la UI.
    """
    # Aislamiento multi-nutricionista: Solo puede modificar citas de sus pacientes
    cita = get_object_or_404(Cita, pk=pk, paciente__nutricionista=request.user)
    nuevo_estado = request.POST.get("estado")
    
    if nuevo_estado in dict(EstadoCita.CHOICES):
        # Validación de negocio: 'no_asistio' solo si ya pasó la fecha de inicio
        if nuevo_estado == EstadoCita.NO_ASISTIO and cita.fecha_hora > timezone.now():
            messages.error(request, "No se puede marcar como 'No asistió' una cita futura.")
            return redirect("agendas:detalle", pk=cita.pk)

        cita.estado = nuevo_estado
        # Validamos y guardamos
        try:
            cita.save()
            messages.success(
                request,
                f"El estado de la cita ha sido cambiado a '{cita.get_estado_display()}'."
            )
        except Exception as e:
            messages.error(request, f"Error al actualizar el estado: {str(e)}")
    else:
        messages.error(request, "Estado de cita no válido.")
        
    return redirect("agendas:detalle", pk=cita.pk)


# ─── Bloquear Horario ────────────────────────────────────────────────────────

@login_required
@require_POST
def cita_bloquear(request):
    """
    Crea un bloqueo de horario para el nutricionista autenticado.
    El bloqueo se almacena como una Cita sin paciente asociado.
    """
    fecha_str = request.POST.get("fecha")
    hora_str = request.POST.get("hora")
    duracion = request.POST.get("duracion", "45")
    motivo = request.POST.get("motivo", "Bloqueo de horario")

    if not fecha_str or not hora_str:
        messages.error(request, "Debe especificar la fecha y la hora de inicio del bloqueo.")
        return redirect("agendas:agenda")

    try:
        # Combinar fecha y hora
        fecha_hora_str = f"{fecha_str} {hora_str}"
        fecha_hora = datetime.strptime(fecha_hora_str, "%Y-%m-%d %H:%M")
        
        # Hacerla aware de timezone para cumplir con Django settings
        from django.utils.timezone import make_aware
        fecha_hora = make_aware(fecha_hora)

        bloqueo = Cita(
            paciente=None,
            nutricionista=request.user,
            fecha_hora=fecha_hora,
            duracion_minutos=int(duracion),
            tipo=TipoCita.BLOQUEO,
            estado=EstadoCita.BLOQUEADA,
            motivo=motivo,
            costo=0.00
        )
        bloqueo.save()
        messages.success(request, f"Horario bloqueado con éxito para el {fecha_hora.strftime('%d/%m/%Y %H:%M')}.")
    except ValidationError as ve:
        # Extraer mensajes de error amigables
        msg = ""
        if hasattr(ve, 'message_dict'):
            msg = "; ".join([f"{k}: {', '.join(v)}" for k, v in ve.message_dict.items()])
        else:
            msg = str(ve)
        messages.error(request, f"Error al bloquear horario: {msg}")
    except Exception as e:
        messages.error(request, f"Error inesperado al bloquear horario: {str(e)}")

    # Redirigir conservando la fecha de la vista
    return redirect(f"/agenda/?vista=semana&fecha={fecha_str}")


# ─── Detalle AJAX en JSON de Cita ────────────────────────────────────────────

@login_required
def cita_detalle_json(request, pk):
    """
    Endpoint AJAX que retorna en JSON toda la información requerida de una cita
    o de un bloqueo, incluyendo la información de evolución de paciente desde la base de datos.
    """
    # Aislamiento multi-nutricionista
    cita = get_object_or_404(
        Cita.objects.filter(
            Q(paciente__nutricionista=request.user) | Q(nutricionista=request.user)
        ),
        pk=pk
    )

    data = {
        "id": cita.pk,
        "fecha": timezone.localtime(cita.fecha_hora).strftime("%d/%m/%Y"),
        "fecha_iso": timezone.localtime(cita.fecha_hora).strftime("%Y-%m-%d"),
        "hora": timezone.localtime(cita.fecha_hora).strftime("%H:%M"),
        "duracion": cita.duracion_minutos,
        "tipo": cita.get_tipo_display(),
        "tipo_raw": cita.tipo,
        "estado": cita.get_estado_display(),
        "estado_raw": cita.estado,
        "motivo": cita.motivo,
        "is_bloqueo": cita.tipo == TipoCita.BLOQUEO,
    }

    if cita.paciente:
        paciente = cita.paciente
        # Calcular edad si no está guardada
        edad = paciente.edad
        
        # 1. Obtener último peso e IMC registrado en MedidasCorporales
        ultima_medida = MedidaCorporal.objects.filter(paciente=paciente).order_by('-fecha', '-fecha_registro').first()
        if ultima_medida:
            ultimo_peso = f"{ultima_medida.peso_kg} kg"
            imc_actual = str(ultima_medida.imc)
        else:
            ultimo_peso = f"{paciente.peso} kg" if paciente.peso else "—"
            imc_actual = str(paciente.imc_inicial) if paciente.imc_inicial else "—"

        # 2. Obtener última consulta completada (antes de la actual)
        ultima_cita_completada = Cita.objects.filter(
            paciente=paciente,
            estado=EstadoCita.COMPLETADA,
            fecha_hora__lt=cita.fecha_hora
        ).order_by('-fecha_hora').first()

        if ultima_cita_completada:
            fecha_u = timezone.localtime(ultima_cita_completada.fecha_hora).strftime("%d/%m/%Y")
            ultima_consulta = f"{fecha_u} — {ultima_cita_completada.get_tipo_display()}"
        else:
            ultima_consulta = "Sin consultas previas"

        # 3. Obtener plan alimentario activo
        plan_activo = PlanAlimentario.objects.filter(paciente=paciente, estado="Activo").first()
        plan_activo_str = plan_activo.nombre if plan_activo else "Ninguno activo"

        # Agregar datos de paciente a la respuesta
        data.update({
            "paciente_id": paciente.pk,
            "paciente_nombre": paciente.nombre_completo,
            "paciente_edad": f"{edad} años" if edad else "—",
            "paciente_sexo": paciente.get_sexo_display() or "—",
            "paciente_telefono": paciente.telefono or "—",
            "paciente_email": paciente.email or "—",
            "paciente_objetivo": paciente.informacion_clinica.get("objetivo_principal") or cita.motivo or "—",
            "ultimo_peso": ultimo_peso,
            "imc_actual": imc_actual,
            "ultima_consulta": ultima_consulta,
            "plan_activo": plan_activo_str,
        })
    else:
        # Datos vacíos para el bloqueo
        data.update({
            "paciente_id": None,
            "paciente_nombre": "Horario Bloqueado",
            "paciente_edad": "—",
            "paciente_telefono": "—",
            "paciente_objetivo": "—",
            "ultimo_peso": "—",
            "imc_actual": "—",
            "ultima_consulta": "—",
            "plan_activo": "—",
        })

    return JsonResponse(data)


@login_required
def check_disponibilidad(request):
    """
    API para verificar si un horario está libre de conflictos para el nutricionista actual.
    """
    fecha_str = request.GET.get("fecha")
    hora_str = request.GET.get("hora")
    duracion_str = request.GET.get("duracion", "60")
    
    if not fecha_str or not hora_str:
        return JsonResponse({
            "status": "error",
            "message": "Fecha y hora son requeridas."
        }, status=400)
        
    try:
        duracion = int(duracion_str)
        naive_dt = datetime.strptime(f"{fecha_str} {hora_str}", "%Y-%m-%d %H:%M")
        proposed_start = timezone.make_aware(naive_dt, timezone.get_current_timezone())
        proposed_end = proposed_start + timedelta(minutes=duracion)
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": f"Formato inválido de fecha, hora o duración: {str(e)}"
        }, status=400)

    # Buscar todas las citas del nutricionista para ese día específico
    citas_dia = Cita.objects.filter(
        Q(paciente__nutricionista=request.user) | Q(nutricionista=request.user),
        fecha_hora__date=proposed_start.date()
    ).exclude(estado=EstadoCita.CANCELADA)

    conflicto = None
    for cita in citas_dia:
        cita_start = cita.fecha_hora
        cita_end = cita_start + timedelta(minutes=cita.duracion_minutos)
        if cita_start < proposed_end and proposed_start < cita_end:
            conflicto = cita
            break

    if conflicto:
        hora_conflicto = timezone.localtime(conflicto.fecha_hora).strftime("%H:%M")
        tipo_conflicto = "bloqueo" if conflicto.tipo == TipoCita.BLOQUEO else "cita"
        mensaje = f"Se cruza con un {tipo_conflicto} a las {hora_conflicto}."
        if conflicto.paciente:
            mensaje = f"Se cruza con una cita de {conflicto.paciente.nombre_completo} a las {hora_conflicto}."
            
        return JsonResponse({
            "status": "success",
            "disponible": False,
            "mensaje": mensaje
        })
        
    return JsonResponse({
        "status": "success",
        "disponible": True,
        "mensaje": "¡El horario está disponible!"
    })

