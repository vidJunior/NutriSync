# core/views.py
# Vistas de autenticación, dashboard y perfil del nutricionista.

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from config.choices import EstadoNutricionista
from .forms import PerfilNutricionistaForm
from agendas.models import Cita
from django.contrib.auth.models import User
from facturacion.models import PlanSuscripcion, SuscripcionNutricionista
from facturacion.choices import EstadoSuscripcion
from pacientes.models import Paciente
from nutricion.models import PlanNutricional


def login_view(request):
    """
    Vista de login con redirecciones al modal de la página principal.
    Cualquier petición GET redirige a la página principal con el modal abierto.
    """
    # Si ya está autenticado, redirige al panel correspondiente directamente
    if request.user.is_authenticated:
        perfil = getattr(request.user, "perfil", None)
        if perfil and perfil.rol == "admin_plataforma":
            return redirect("administracion:dashboard")
        elif perfil and perfil.rol == "nutricionista":
            return redirect("core:dashboard")
        else:
            if request.user.is_superuser:
                return redirect("administracion:dashboard")
            return redirect("core:dashboard")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            # Validamos que el perfil esté habilitado antes de permitir el acceso
            try:
                perfil = user.perfil
                if perfil.estado != EstadoNutricionista.HABILITADO:
                    messages.error(
                        request,
                        "Tu cuenta está deshabilitada. Contacta al administrador.",
                    )
                    return redirect("/?login=true")
            except Exception:
                # Si es superusuario y no tiene perfil, se lo creamos con rol de administrador
                if user.is_superuser:
                    from core.models import PerfilNutricionista, Rol
                    nombre = f"{user.first_name} {user.last_name}".strip() or user.username
                    PerfilNutricionista.objects.get_or_create(
                        usuario=user,
                        defaults={
                            "nombre_completo": nombre,
                            "rol": Rol.ADMIN_PLATAFORMA
                        }
                    )
                pass

            login(request, user)
            messages.success(
                request, f"Bienvenido, {user.first_name or user.username}."
            )
            
            # Redirección inteligente de rol
            perfil = getattr(user, "perfil", None)
            if perfil and perfil.rol == "admin_plataforma":
                next_url = request.POST.get("next", "") or request.GET.get("next", "") or "/administracion/"
            elif perfil and perfil.rol == "nutricionista":
                next_url = request.POST.get("next", "") or request.GET.get("next", "") or "/dashboard/"
            else:
                if user.is_superuser:
                    next_url = request.POST.get("next", "") or request.GET.get("next", "") or "/administracion/"
                else:
                    next_url = request.POST.get("next", "") or request.GET.get("next", "") or "/dashboard/"
                
            return redirect(next_url)
        else:
            messages.error(request, "Usuario o contraseña incorrectos.")
            next_param = request.GET.get("next", "") or request.POST.get("next", "")
            redirect_url = "/?login=true"
            if next_param:
                redirect_url += f"&next={next_param}"
            return redirect(redirect_url)

    # Si es GET, redirigir a la página principal con el modal abierto
    next_param = request.GET.get("next", "")
    redirect_url = "/?login=true"
    if next_param:
        redirect_url += f"&next={next_param}"
    return redirect(redirect_url)


def landing_view(request):
    """Página de inicio (Landing Page) con planes de suscripción."""
    planes = PlanSuscripcion.objects.filter(activo=True)
    return render(request, "core/landing.html", {"planes": planes})


def register_view(request):
    """Registro de nuevos nutricionistas con elección de plan de suscripción."""
    if request.user.is_authenticated:
        return redirect("core:dashboard")

    planes = PlanSuscripcion.objects.filter(activo=True)

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        password_confirm = request.POST.get("password_confirm", "")
        nombre_completo = request.POST.get("nombre_completo", "").strip()
        especialidad = request.POST.get("especialidad", "").strip()
        telefono = request.POST.get("telefono", "").strip()
        numero_colegiatura = request.POST.get("numero_colegiatura", "").strip()
        direccion_consultorio = request.POST.get("direccion_consultorio", "").strip()
        plan_id = request.POST.get("plan", "")
        tipo_facturacion = request.POST.get("tipo_facturacion", "mensual").strip()
        
        dni = request.POST.get("dni", "").strip()
        ruc = request.POST.get("ruc", "").strip()

        errors = []

        if not username or not email or not password or not nombre_completo:
            errors.append("Por favor completa los campos obligatorios del usuario y perfil.")

        if not dni:
            errors.append("El DNI es obligatorio.")
        elif not dni.isdigit() or len(dni) != 8:
            errors.append("El DNI debe tener exactamente 8 dígitos numéricos.")

        if ruc:
            if not ruc.isdigit() or len(ruc) != 11:
                errors.append("El RUC debe tener exactamente 11 dígitos numéricos.")
            elif not ruc.startswith("10") and not ruc.startswith("20"):
                errors.append("El RUC debe comenzar con 10 o 20.")

        if password != password_confirm:
            errors.append("Las contraseñas no coinciden.")

        if User.objects.filter(username=username).exists():
            errors.append("El nombre de usuario ya está registrado.")

        if User.objects.filter(email=email).exists():
            errors.append("El correo electrónico ya está registrado.")

        if numero_colegiatura:
            import re
            if not re.match(r"^\d{3,6}$", numero_colegiatura):
                errors.append("El C.N.P. debe ser un número de 3 a 6 dígitos.")
            else:
                from core.models import PerfilNutricionista
                if PerfilNutricionista.objects.filter(numero_colegiatura=numero_colegiatura).exists():
                    errors.append("El número de colegiatura C.N.P. ya está registrado.")

        if not plan_id:
            errors.append("Debes elegir un plan de suscripción.")
        else:
            try:
                plan = PlanSuscripcion.objects.get(pk=plan_id, activo=True)
            except (PlanSuscripcion.DoesNotExist, ValueError):
                errors.append("El plan seleccionado no es válido.")

        if errors:
            return render(request, "core/register.html", {
                "planes": planes,
                "errors": errors,
                "data": request.POST
            })

        # Validar método de pago (Tarjeta, Yape o PayPal)
        payment_method_type = request.POST.get("payment_method_type", "tarjeta")
        
        card_number = ""
        yape_phone = ""
        yape_otp = ""
        paypal_email = ""

        if payment_method_type == "tarjeta":
            card_number = request.POST.get("card_number", "").strip()
            card_name = request.POST.get("card_name", "").strip()
            card_expiry = request.POST.get("card_expiry", "").strip()
            card_cvv = request.POST.get("card_cvv", "").strip()

            if not card_number or not card_expiry or not card_cvv:
                errors.append("Debes completar los datos de tu tarjeta de crédito para configurar tu cuenta.")
        elif payment_method_type == "yape":
            yape_phone = request.POST.get("yape_phone", "").strip()
            yape_otp = request.POST.get("yape_otp", "").strip()

            yape_phone_clean = yape_phone.replace(" ", "")
            if not yape_phone_clean or len(yape_phone_clean) != 9 or not yape_phone_clean.startswith("9"):
                errors.append("Ingresa un número de celular Yape válido (9 dígitos, comenzando con 9).")
            if not yape_otp or len(yape_otp) != 6 or not yape_otp.isdigit():
                errors.append("Ingresa un código de aprobación de Yape válido (6 dígitos numéricos).")
        elif payment_method_type == "paypal":
            paypal_email = request.POST.get("paypal_email", "").strip()
            if not paypal_email or "@" not in paypal_email:
                errors.append("Ingresa un correo electrónico de PayPal válido.")
        else:
            errors.append("Método de pago no válido.")

        if errors:
            return render(request, "core/register.html", {
                "planes": planes,
                "errors": errors,
                "data": request.POST
            })

        # Crear el usuario
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=nombre_completo.split(" ")[0],
            last_name=" ".join(nombre_completo.split(" ")[1:])
        )

        # El signal crea el perfil automáticamente. Lo recuperamos y actualizamos.
        perfil = user.perfil
        perfil.nombre_completo = nombre_completo
        perfil.especialidad = especialidad
        perfil.telefono = telefono
        perfil.email_profesional = email
        perfil.numero_colegiatura = numero_colegiatura
        perfil.direccion_consultorio = direccion_consultorio
        perfil.dni = dni
        perfil.ruc = ruc
        perfil.estado = EstadoNutricionista.HABILITADO
        perfil.save()

        # Importaciones locales para facturación
        from facturacion.models import Pago
        from facturacion.choices import MetodoPago, EstadoPago
        from decimal import Decimal

        # Configurar de acuerdo al tipo de plan
        if plan.nombre == "Prueba Gratis":
            precio = Decimal("0.00")
            fecha_fin = timezone.now().date() + timedelta(days=7)
            tipo_facturacion = "mensual"
        else:
            precio = plan.precio_anual if tipo_facturacion == "anual" else plan.precio_mensual
            fecha_fin = timezone.now().date() + timedelta(days=365 if tipo_facturacion == "anual" else 30)

        # Crear la suscripción ACTIVA directamente
        SuscripcionNutricionista.objects.create(
            nutricionista=user,
            plan=plan,
            tipo_facturacion=tipo_facturacion,
            precio_aplicado=precio,
            estado=EstadoSuscripcion.ACTIVA,
            fecha_inicio=timezone.now().date(),
            fecha_fin=fecha_fin
        )

        # Si el plan es de pago, creamos el registro de pago simulado
        if precio > 0:
            if payment_method_type == "tarjeta":
                Pago.objects.create(
                    nutricionista=user,
                    monto=precio,
                    metodo_pago=MetodoPago.STRIPE, # Se mapea como tarjeta
                    referencia=f"CULQI-{user.pk}-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                    estado=EstadoPago.COMPLETADO,
                    comision_stripe=Decimal("0.00"),
                    monto_neto=precio,
                    notas=f"Cobro inicial plan {plan.nombre} ({tipo_facturacion}) - Tarjeta terminada en {card_number[-4:]}",
                )
            elif payment_method_type == "yape":
                Pago.objects.create(
                    nutricionista=user,
                    monto=precio,
                    metodo_pago=MetodoPago.YAPE,
                    referencia=f"YAPE-{user.pk}-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                    estado=EstadoPago.COMPLETADO,
                    comision_stripe=Decimal("0.00"),
                    monto_neto=precio,
                    notas=f"Cobro inicial plan {plan.nombre} ({tipo_facturacion}) - Celular Yape: {yape_phone}",
                )
            elif payment_method_type == "paypal":
                Pago.objects.create(
                    nutricionista=user,
                    monto=precio,
                    metodo_pago=MetodoPago.PAYPAL,
                    referencia=f"PAYPAL-{user.pk}-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                    estado=EstadoPago.COMPLETADO,
                    comision_stripe=Decimal("0.00"),
                    monto_neto=precio,
                    notas=f"Cobro inicial plan {plan.nombre} ({tipo_facturacion}) - PayPal Email: {paypal_email}",
                )
        else:
            # Para la prueba gratuita, creamos un registro de control de S/0.00
            if payment_method_type == "tarjeta":
                Pago.objects.create(
                    nutricionista=user,
                    monto=Decimal("0.00"),
                    metodo_pago=MetodoPago.STRIPE,
                    referencia=f"CULQI-TRIAL-{user.pk}-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                    estado=EstadoPago.COMPLETADO,
                    comision_stripe=Decimal("0.00"),
                    monto_neto=Decimal("0.00"),
                    notas=f"Registro de Tarjeta para Prueba Gratis de 7 días - Tarjeta terminada en {card_number[-4:]}",
                )
            elif payment_method_type == "yape":
                Pago.objects.create(
                    nutricionista=user,
                    monto=Decimal("0.00"),
                    metodo_pago=MetodoPago.YAPE,
                    referencia=f"YAPE-TRIAL-{user.pk}-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                    estado=EstadoPago.COMPLETADO,
                    comision_stripe=Decimal("0.00"),
                    monto_neto=Decimal("0.00"),
                    notas=f"Registro de Yape para Prueba Gratis de 7 días - Celular Yape: {yape_phone}",
                )
            elif payment_method_type == "paypal":
                Pago.objects.create(
                    nutricionista=user,
                    monto=Decimal("0.00"),
                    metodo_pago=MetodoPago.PAYPAL,
                    referencia=f"PAYPAL-TRIAL-{user.pk}-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                    estado=EstadoPago.COMPLETADO,
                    comision_stripe=Decimal("0.00"),
                    monto_neto=Decimal("0.00"),
                    notas=f"Registro de PayPal para Prueba Gratis de 7 días - PayPal Email: {paypal_email}",
                )

        # Logear al usuario automáticamente
        login(request, user)
        if plan.nombre == "Prueba Gratis":
            messages.success(request, f"¡Registro exitoso! Tu prueba gratuita de 7 días ha sido activada correctamente.")
        else:
            messages.success(request, f"¡Registro exitoso! Tu plan {plan.nombre} ha sido activado correctamente.")
        return redirect("core:dashboard")

    return render(request, "core/register.html", {"planes": planes})


def validate_register_fields_view(request):
    """Valida los campos del paso 1 de registro vía AJAX antes de ir al pago."""
    if request.method != "POST":
        return JsonResponse({"valid": False, "errors": ["Método no permitido."]}, status=405)

    import re
    username = request.POST.get("username", "").strip()
    email = request.POST.get("email", "").strip()
    password = request.POST.get("password", "")
    password_confirm = request.POST.get("password_confirm", "")
    nombre_completo = request.POST.get("nombre_completo", "").strip()
    telefono = request.POST.get("telefono", "").strip()
    numero_colegiatura = request.POST.get("numero_colegiatura", "").strip()
    dni = request.POST.get("dni", "").strip()
    ruc = request.POST.get("ruc", "").strip()

    errors = {}

    # Validar username
    username_regex = r"^[a-zA-Z0-9._]+$"
    if not username:
        errors["username"] = "El nombre de usuario es obligatorio."
    elif len(username) < 4:
        errors["username"] = "El nombre de usuario debe tener al menos 4 caracteres."
    elif not re.match(username_regex, username):
        errors["username"] = "Solo se permiten letras, números, puntos y guiones bajos."
    elif User.objects.filter(username=username).exists():
        errors["username"] = "El nombre de usuario ya está registrado."

    # Validar email
    email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not email:
        errors["email"] = "El correo electrónico es obligatorio."
    elif not re.match(email_regex, email):
        errors["email"] = "El correo electrónico no tiene un formato válido."
    elif User.objects.filter(email=email).exists():
        errors["email"] = "El correo electrónico ya está registrado."

    # Validar password
    if not password:
        errors["password"] = "La contraseña es obligatoria."
    elif len(password) < 6:
        errors["password"] = "La contraseña debe tener al menos 6 caracteres."

    if password != password_confirm:
        errors["password_confirm"] = "Las contraseñas no coinciden."

    if not nombre_completo:
        errors["nombre_completo"] = "El nombre completo es obligatorio."

    if telefono:
        if not telefono.isdigit():
            errors["telefono"] = "El teléfono debe contener únicamente números."
        elif len(telefono) != 9:
            errors["telefono"] = "El teléfono debe tener exactamente 9 dígitos."

    if numero_colegiatura:
        # Validar colegiatura (sólo dígitos)
        if not re.match(r"^\d{3,6}$", numero_colegiatura):
            errors["numero_colegiatura"] = "El C.N.P. debe ser un número de 3 a 6 dígitos."
        else:
            from core.models import PerfilNutricionista
            if PerfilNutricionista.objects.filter(numero_colegiatura=numero_colegiatura).exists():
                errors["numero_colegiatura"] = "El número de colegiatura C.N.P. ya está registrado."

    if not dni:
        errors["dni"] = "El DNI es obligatorio."
    elif not dni.isdigit() or len(dni) != 8:
        errors["dni"] = "El DNI debe tener exactamente 8 dígitos numéricos."

    if ruc:
        if not ruc.isdigit() or len(ruc) != 11:
            errors["ruc"] = "El RUC debe tener exactamente 11 dígitos numéricos."
        elif not ruc.startswith("10") and not ruc.startswith("20"):
            errors["ruc"] = "El RUC debe comenzar con 10 o 20."

    if errors:
        return JsonResponse({"valid": False, "errors": errors})
    
    return JsonResponse({"valid": True})



@login_required
def logout_view(request):
    """Cierra la sesión y redirige a la página de inicio (Landing Page)."""
    logout(request)
    return redirect("core:landing")


@login_required
def dashboard_view(request):
    hoy = timezone.now().date()
    inicio_semana = hoy
    fin_semana = hoy + timedelta(days=7)

    # Aislamiento por nutricionista
    pacientes_activos = Paciente.objects.filter(nutricionista=request.user, estado=True)

    total_pacientes = pacientes_activos.count()

    # Optimizamos: solo contamos las citas de hoy sin cargar objetos a memoria
    cantidad_citas_hoy = Cita.objects.filter(
        paciente__nutricionista=request.user, fecha_hora__date=hoy
    ).count()

    proximas_citas = (
        Cita.objects.select_related("paciente")
        .filter(
            paciente__nutricionista=request.user,
            fecha_hora__date__range=[inicio_semana, fin_semana],
            estado="programada",
        )
        .order_by("fecha_hora")
    )

    pacientes_con_plan = PlanNutricional.objects.filter(
        nutricionista=request.user, estado="Activo"
    ).count()

    ultimos_pacientes = Paciente.objects.filter(nutricionista=request.user).order_by(
        "-fecha_registro"
    )[:5]

    context = {
        "total_pacientes": total_pacientes,
        "cantidad_citas_hoy": cantidad_citas_hoy,
        "proximas_citas": proximas_citas[:5],
        "pacientes_con_plan": pacientes_con_plan,
        "ultimos_pacientes": ultimos_pacientes,
    }

    return render(request, "core/dashboard.html", context)


@login_required
def perfil_view(request):
    """
    Ver y editar el perfil profesional del nutricionista autenticado.
    Permite gestionar los datos profesionales, ver el plan activo y configurar el método de pago.
    """
    perfil, _ = request.user.perfil.__class__.objects.get_or_create(
        usuario=request.user,
        defaults={"nombre_completo": request.user.username},
    )

    suscripcion = getattr(request.user, "suscripcion", None)
    ultimo_pago = request.user.pagos_facturacion.filter(estado="completado").order_by("-fecha_pago").first()

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "cancelar_suscripcion":
            if suscripcion:
                suscripcion.estado = "cancelada"
                suscripcion.save()
                messages.success(request, "Suscripción cancelada correctamente.")
            return redirect("core:perfil")

        elif action == "quitar_metodo":
            if ultimo_pago:
                ultimo_pago.delete()
                messages.success(request, "Método de pago removido correctamente.")
            return redirect("core:perfil")

        # De lo contrario, procesar el formulario de perfil profesional
        form = PerfilNutricionistaForm(request.POST, instance=perfil)
        if form.is_valid():
            form.save()
            messages.success(request, "Perfil actualizado correctamente.")
            return redirect("core:perfil")
    else:
        form = PerfilNutricionistaForm(instance=perfil)

    # Analizar el método de pago guardado desde las notas de cobro
    metodo_guardado = None
    if ultimo_pago and "removido" not in ultimo_pago.notas:
        if "Tarjeta terminada en" in ultimo_pago.notas:
            digitos = ultimo_pago.notas.split("terminada en")[-1].strip()
            metodo_guardado = {
                "tipo": "tarjeta",
                "detalle": f"Tarjeta terminada en {digitos}"
            }
        elif "Celular Yape:" in ultimo_pago.notas:
            celular = ultimo_pago.notas.split("Celular Yape:")[-1].strip()
            metodo_guardado = {
                "tipo": "yape",
                "detalle": f"Yape (Celular: {celular})"
            }
        elif "PayPal Email:" in ultimo_pago.notas:
            email_paypal = ultimo_pago.notas.split("PayPal Email:")[-1].strip()
            metodo_guardado = {
                "tipo": "paypal",
                "detalle": f"PayPal ({email_paypal})"
            }

    context = {
        "form": form,
        "suscripcion": suscripcion,
        "metodo_guardado": metodo_guardado,
    }

    return render(request, "core/perfil.html", context)

def error_404(request, exception):
    """Página 404 personalizada con diseño consistente al sistema."""
    return render(request, "404.html", status=404)


def error_500(request):
    """Página 500 personalizada con diseño consistente al sistema."""
    return render(request, "500.html", status=500)


from django.contrib.auth.decorators import login_required

@login_required
def soporte_view(request):
    """Permite al nutricionista enviar solicitudes de soporte técnico e inspeccionar respuestas."""
    from administracion.models import TicketSoporte
    
    if request.method == "POST":
        asunto = request.POST.get("asunto", "").strip()
        mensaje = request.POST.get("mensaje", "").strip()
        
        if not asunto or not mensaje:
            messages.error(request, "Por favor completa el asunto y el mensaje de ayuda.")
        else:
            TicketSoporte.objects.create(
                nutricionista=request.user,
                asunto=asunto,
                mensaje=mensaje,
                estado="abierto"
            )
            messages.success(request, "Tu solicitud de soporte ha sido enviada con éxito. Un administrador la revisará pronto.")
            return redirect("core:soporte")
            
    tickets = request.user.tickets.all().order_by("-fecha_creacion")
    return render(request, "core/soporte/index.html", {"tickets": tickets})


@login_required
def api_alertas(request):
    """Retorna las alertas activas no leídas dirigidas al usuario en formato JSON."""
    from django.http import JsonResponse
    from administracion.models import NotificacionSistema, NotificacionLeida
    try:
        alertas_validas = NotificacionSistema.para_usuario(request.user)
        leidas_ids = NotificacionLeida.objects.filter(usuario=request.user).values_list("notificacion_id", flat=True)
        alertas_no_leidas = alertas_validas.exclude(id__in=leidas_ids)
        
        data = [
            {
                "id": a.id,
                "titulo": a.titulo,
                "mensaje": a.mensaje,
                "tipo": a.tipo,
                "fecha_creacion": a.fecha_creacion.strftime('%d/%m/%Y %H:%M')
            }
            for a in alertas_no_leidas
        ]
        return JsonResponse({
            "status": "success", 
            "alertas": data,
            "alertas_pendientes_count": alertas_no_leidas.count()
        })
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@login_required
def api_alertar_leer(request, alert_id):
    """Registra que el usuario ha leído o descartado una alerta."""
    from django.http import JsonResponse
    from administracion.models import NotificacionSistema, NotificacionLeida
    try:
        notif = NotificacionSistema.objects.get(id=alert_id)
        NotificacionLeida.objects.get_or_create(usuario=request.user, notificacion=notif)
        
        # Calcular nuevo contador
        alertas_validas = NotificacionSistema.para_usuario(request.user)
        leidas_ids = NotificacionLeida.objects.filter(usuario=request.user).values_list("notificacion_id", flat=True)
        alertas_pendientes_count = alertas_validas.exclude(id__in=leidas_ids).count()
        
        return JsonResponse({"status": "success", "alertas_pendientes_count": alertas_pendientes_count})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@login_required
def notificaciones_view(request):
    """Muestra la bandeja de entrada e historial de alertas del sistema."""
    from administracion.models import NotificacionSistema, NotificacionLeida
    from django.contrib import messages
    
    alertas_validas = NotificacionSistema.para_usuario(request.user).order_by("-fecha_creacion")
        
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "marcar_todo":
            for a in alertas_validas:
                NotificacionLeida.objects.get_or_create(usuario=request.user, notificacion=a)
            messages.success(request, "Todas las alertas se marcaron como leídas.")
            return redirect("core:notificaciones")
        elif action == "marcar_una":
            alert_id = request.POST.get("alert_id")
            if alert_id:
                try:
                    a = NotificacionSistema.objects.get(id=alert_id)
                    NotificacionLeida.objects.get_or_create(usuario=request.user, notificacion=a)
                    messages.success(request, f"Alerta '{a.titulo}' marcada como leída.")
                except Exception:
                    pass
            return redirect("core:notificaciones")
            
    leidas_ids = set(NotificacionLeida.objects.filter(usuario=request.user).values_list("notificacion_id", flat=True))
    
    alertas_con_estado = [
        {
            "id": a.id,
            "titulo": a.titulo,
            "mensaje": a.mensaje,
            "tipo": a.tipo,
            "fecha_creacion": a.fecha_creacion,
            "leida": a.id in leidas_ids
        }
        for a in alertas_validas
    ]
        
    context = {
        "alertas": alertas_con_estado,
        "pendientes_count": len([x for x in alertas_con_estado if not x["leida"]])
    }
    return render(request, "core/notificaciones.html", context)

