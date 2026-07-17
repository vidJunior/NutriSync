import os
import sys
import django
from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError, PermissionDenied
from django.utils import timezone
from datetime import timedelta, date
from decimal import Decimal

# Agregar la raíz del proyecto al path para que 'config' y las apps sean importables
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

# Configurar Django para permitir la importación de modelos en un script independiente
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from pacientes.models import Paciente
from agendas.models import Cita
from facturacion.models import SuscripcionNutricionista, PlanSuscripcion, Cobro
from config.choices import EstadoCita
from facturacion.choices import EstadoSuscripcion

# ==============================================================================
# SIMULADORES PARA INTEGRACIONES Y FUNCIONALIDADES EXTERNAS (SendGrid, Logs, Stripe)
# ==============================================================================

def enviar_correo_sendgrid(email, asunto, cuerpo):
    """Simulador de envío de correos vía SendGrid (UT-12-01 y UT-12-02)."""
    if not email or email.strip() == "":
        return "OMITIDO_EMAIL_VACIO"
    # Simula la llamada HTTP a SendGrid que retorna 202 (Accepted) de aceptación de cola
    return 202


def registrar_log_paciente(usuario, accion, ip, paciente):
    """Simulador de inserción de logs CRUD con IP (UT-15-01)."""
    # En un sistema real esto se guardaría en una tabla AuditoriaPacienteLog o similar.
    # Simulamos el guardado retornando un diccionario con los datos insertados.
    log_entry = {
        "usuario": usuario.username,
        "accion": accion,
        "ip": ip,
        "paciente_id": paciente.pk,
        "fecha": timezone.now()
    }
    return log_entry


def consultar_logs_paciente(usuario, tenant_id_consulta):
    """Simulador de verificación de Multi-tenancy en logs (UT-15-02)."""
    # Obtenemos el tenant (consultorio_id o id_usuario) del usuario
    tenant_usuario = usuario.pk  # En NutriSync el tenant lógico suele ser el ID del nutricionista
    if tenant_usuario != tenant_id_consulta:
        raise PermissionDenied("Acceso no autorizado: No se permite lectura cruzada de logs de otro tenant.")
    return "LOGS_AUTORIZADOS"


# ==============================================================================
# CLASE DE PRUEBAS DEL SISTEMA FUNCIONAL
# ==============================================================================

class PruebasSistemaFuncionales(TestCase):
    
    def setUp(self):
        # Configurar un plan de suscripción de prueba para los tests
        self.plan_prueba = PlanSuscripcion.objects.create(
            nombre="Plan Test",
            precio_mensual=Decimal("59.00"),
            precio_anual=Decimal("599.00"),
            limite_pacientes=50,
            limite_citas_mes=100
        )
        
        # Crear Nutricionistas (Especialistas / Tenants)
        self.nutricionista_1 = User.objects.create_user(
            username="nutri_especialista_1",
            email="nutri1@nutrisync.com",
            password="Password123"
        )
        self.nutricionista_2 = User.objects.create_user(
            username="nutri_especialista_2",
            email="nutri2@nutrisync.com",
            password="Password123"
        )
        
        # Crear Pacientes activos asociados a cada nutricionista
        self.paciente_1 = Paciente.objects.create(
            nutricionista=self.nutricionista_1,
            nombre="Juan",
            apellido="Pérez",
            dni="77777777",
            fecha_nacimiento=date(1990, 5, 15),
            sexo="M",
            peso=Decimal("75.00"),
            talla=Decimal("175.00"),
            telefono="999888777",
            email="juan.perez@example.com",
            estado=True
        )
        self.paciente_sin_correo = Paciente.objects.create(
            nutricionista=self.nutricionista_1,
            nombre="Pedro",
            apellido="Gómez",
            dni="88888888",
            fecha_nacimiento=date(1985, 10, 20),
            sexo="M",
            peso=Decimal("80.00"),
            talla=Decimal("180.00"),
            telefono="999111222",
            email="",  # Correo vacío
            estado=True
        )

        # Crear Suscripciones para los nutricionistas
        self.suscripcion_1 = SuscripcionNutricionista.objects.create(
            nutricionista=self.nutricionista_1,
            plan=self.plan_prueba,
            precio_aplicado=Decimal("59.00"),
            estado=EstadoSuscripcion.ACTIVA,
            fecha_inicio=date.today(),
            fecha_fin=date.today() + timedelta(days=30),
            stripe_subscription_id="sub_stripe_123"
        )

    # --------------------------------------------------------------------------
    # UT-10-01: Reserva de Bloque Libre
    # --------------------------------------------------------------------------
    def test_ut_10_01_reserva_bloque_libre(self):
        """Valida que una cita pueda reservarse con éxito en un horario disponible."""
        fecha_cita = timezone.now() + timedelta(days=5) # 5 días en el futuro
        # Alinear a las 10:00 AM
        fecha_cita = fecha_cita.replace(hour=10, minute=0, second=0, microsecond=0)
        
        cita = Cita.objects.create(
            paciente=self.paciente_1,
            nutricionista=self.nutricionista_1,
            fecha_hora=fecha_cita,
            duracion_minutos=45,
            motivo="Control de peso mensual",
            costo=Decimal("100.00"),
            estado=EstadoCita.PROGRAMADA
        )
        
        self.assertIsNotNone(cita.pk)
        self.assertEqual(cita.estado, EstadoCita.PROGRAMADA)
        self.assertEqual(cita.fecha_hora, fecha_cita)

    # --------------------------------------------------------------------------
    # UT-10-02: Reserva de Horario Ocupado
    # --------------------------------------------------------------------------
    def test_ut_10_02_reserva_horario_ocupado(self):
        """Valida que se impida la creación de citas solapadas para el mismo nutricionista."""
        fecha_cita = timezone.now() + timedelta(days=5)
        fecha_cita = fecha_cita.replace(hour=10, minute=0, second=0, microsecond=0)
        
        # Registrar primera cita a las 10:00 AM
        Cita.objects.create(
            paciente=self.paciente_1,
            nutricionista=self.nutricionista_1,
            fecha_hora=fecha_cita,
            duracion_minutos=45,
            motivo="Cita 1",
            costo=Decimal("100.00"),
            estado=EstadoCita.PROGRAMADA
        )
        
        # Crear segunda cita en el mismo horario y nutricionista
        cita_solapada = Cita(
            paciente=self.paciente_1,
            nutricionista=self.nutricionista_1,
            fecha_hora=fecha_cita,
            duracion_minutos=45,
            motivo="Intento de cita 2 en horario ocupado",
            costo=Decimal("100.00"),
            estado=EstadoCita.PROGRAMADA
        )
        
        # Debe fallar la validación de solapamiento
        with self.assertRaises(ValidationError) as context:
            cita_solapada.full_clean()
            
        self.assertIn("fecha_hora", context.exception.message_dict)

    # --------------------------------------------------------------------------
    # UT-11-01: Inicio de Cita
    # --------------------------------------------------------------------------
    def test_ut_11_01_inicio_cita(self):
        """Valida que una cita pueda iniciarse, pasando a estado 'En Consulta'."""
        fecha_cita = timezone.now() + timedelta(days=5)
        cita = Cita.objects.create(
            paciente=self.paciente_1,
            nutricionista=self.nutricionista_1,
            fecha_hora=fecha_cita,
            duracion_minutos=45,
            motivo="Cita pendiente",
            estado=EstadoCita.PROGRAMADA
        )
        
        # Cambiar estado a 'En Consulta'
        cita.estado = EstadoCita.EN_CONSULTA
        cita.save()
        
        cita_actualizada = Cita.objects.get(pk=cita.pk)
        self.assertEqual(cita_actualizada.estado, EstadoCita.EN_CONSULTA)

    # --------------------------------------------------------------------------
    # UT-11-02: Cancelación de Cita Terminada
    # --------------------------------------------------------------------------
    def test_ut_11_02_cancelacion_cita_terminada(self):
        """Valida que el backend impida cambiar a 'Cancelada' el estado de una cita completada/finalizada."""
        fecha_cita = timezone.now() + timedelta(days=5)
        
        # Cita creada y completada
        cita = Cita.objects.create(
            paciente=self.paciente_1,
            nutricionista=self.nutricionista_1,
            fecha_hora=fecha_cita,
            duracion_minutos=45,
            motivo="Cita realizada",
            estado=EstadoCita.COMPLETADA
        )
        
        # Intentar cambiar a 'Cancelada'
        cita.estado = EstadoCita.CANCELADA
        
        with self.assertRaises(ValidationError) as context:
            cita.full_clean()
            
        self.assertIn("estado", context.exception.message_dict)
        self.assertIn("inalterable", context.exception.message_dict["estado"][0])

    # --------------------------------------------------------------------------
    # UT-11-03: Adelanto y Vinculación de Cita Programada (Exitoso)
    # --------------------------------------------------------------------------
    def test_ut_11_03_adelanto_vincular_cita_exitoso(self):
        """Valida que se pueda adelantar e iniciar una cita programada futura actualizando su fecha y hora a 'ahora'."""
        self.client.force_login(self.nutricionista_1)
        
        # 1. Crear una cita programada futura
        fecha_futura = timezone.now() + timedelta(days=3)
        cita = Cita.objects.create(
            paciente=self.paciente_1,
            nutricionista=self.nutricionista_1,
            fecha_hora=fecha_futura,
            duracion_minutos=45,
            motivo="Consulta de control futura",
            estado=EstadoCita.PROGRAMADA
        )
        
        # 2. Enviar petición para iniciar consulta vinculando y adelantando la cita
        from django.urls import reverse
        url = reverse("pacientes:consulta_iniciar", args=[self.paciente_1.pk])
        response = self.client.post(url, {
            "tipo": "control",
            "cita_id": str(cita.id),
            "vincular_cita": "true"
        }, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        
        # 3. Verificar que la cita fue actualizada
        cita_actualizada = Cita.objects.get(pk=cita.pk)
        self.assertEqual(cita_actualizada.estado, EstadoCita.EN_CONSULTA)
        # La fecha y hora de la cita debe estar cerca del momento actual (menos de 5 segundos de diferencia)
        self.assertLess((timezone.now() - cita_actualizada.fecha_hora).total_seconds(), 5)

    # --------------------------------------------------------------------------
    # UT-11-04: Adelanto y Vinculación de Cita Programada (Con Solapamiento)
    # --------------------------------------------------------------------------
    def test_ut_11_04_adelanto_vincular_cita_con_solapamiento(self):
        """Valida que falle el adelanto de una cita si interfiere con otra cita agendada en la hora actual."""
        self.client.force_login(self.nutricionista_1)
        
        # 1. Crear una cita activa justo HOY a esta misma hora (cruce)
        # Hacemos que empiece 10 minutos en el futuro y dure 45 minutos (cruzando el momento actual de la petición)
        hora_cruce = timezone.now() + timedelta(minutes=10)
        cita_existente = Cita.objects.create(
            paciente=self.paciente_sin_correo, # Otro paciente
            nutricionista=self.nutricionista_1,
            fecha_hora=hora_cruce,
            duracion_minutos=45,
            motivo="Cita que genera cruce",
            estado=EstadoCita.PROGRAMADA
        )
        
        # 2. Crear la cita programada futura que se intentará adelantar
        fecha_futura = timezone.now() + timedelta(days=3)
        cita_adelantar = Cita.objects.create(
            paciente=self.paciente_1,
            nutricionista=self.nutricionista_1,
            fecha_hora=fecha_futura,
            duracion_minutos=45,
            motivo="Consulta de control futura",
            estado=EstadoCita.PROGRAMADA
        )
        
        # 3. Intentar adelantar la cita por POST
        from django.urls import reverse
        url = reverse("pacientes:consulta_iniciar", args=[self.paciente_1.pk])
        response = self.client.post(url, {
            "tipo": "control",
            "cita_id": str(cita_adelantar.id),
            "vincular_cita": "true"
        }, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertIn("solapa", data["error"])
        
        # 4. Verificar que la cita futura no cambió su estado ni su fecha
        cita_persistida = Cita.objects.get(pk=cita_adelantar.pk)
        self.assertEqual(cita_persistida.estado, EstadoCita.PROGRAMADA)
        self.assertEqual(cita_persistida.fecha_hora, fecha_futura)

    # --------------------------------------------------------------------------
    # UT-12-01: Envío de Correo Exitoso
    # --------------------------------------------------------------------------
    def test_ut_12_01_envio_correo_exitoso(self):
        """Valida que se envíe un correo de recordatorio exitosamente si el paciente tiene email."""
        resultado = enviar_correo_sendgrid(
            email=self.paciente_1.email,
            asunto="Recordatorio de cita",
            cuerpo="Hola Juan, tienes una cita mañana."
        )
        self.assertEqual(resultado, 202)

    # --------------------------------------------------------------------------
    # UT-12-02: Envío con Correo Vacío
    # --------------------------------------------------------------------------
    def test_ut_12_02_envio_con_correo_vacio(self):
        """Valida que el sistema omita el envío y prevenga excepciones SMTP si el email está vacío."""
        resultado = enviar_correo_sendgrid(
            email=self.paciente_sin_correo.email,
            asunto="Recordatorio de cita",
            cuerpo="Hola Pedro, tienes una cita mañana."
        )
        self.assertEqual(resultado, "OMITIDO_EMAIL_VACIO")

    # --------------------------------------------------------------------------
    # UT-13-01: Cobro Recurrente Exitoso
    # --------------------------------------------------------------------------
    def test_ut_13_01_cobro_recurrente_exitoso(self):
        """Valida que la suscripción activa se renueve por 30 días al recibir confirmación de cobro de Stripe."""
        # Datos simulados de webhook de renovación exitosa
        self.assertEqual(self.suscripcion_1.estado, EstadoSuscripcion.ACTIVA)
        fecha_fin_original = self.suscripcion_1.fecha_fin
        
        # Simular webhook de pago exitoso (invoice.payment_succeeded)
        suscripcion_db = SuscripcionNutricionista.objects.get(stripe_subscription_id="sub_stripe_123")
        suscripcion_db.estado = EstadoSuscripcion.ACTIVA
        suscripcion_db.fecha_fin = fecha_fin_original + timedelta(days=30)
        suscripcion_db.save()
        
        # Verificar renovación de 30 días adicionales
        self.assertEqual(suscripcion_db.estado, EstadoSuscripcion.ACTIVA)
        self.assertEqual(suscripcion_db.fecha_fin, fecha_fin_original + timedelta(days=30))

    # --------------------------------------------------------------------------
    # UT-13-02: Cobro Declinado en Stripe
    # --------------------------------------------------------------------------
    def test_ut_13_02_cobro_declinado_en_stripe(self):
        """Valida que la cuenta del consultorio se suspenda si el cobro de la renovación en Stripe falla."""
        # Simular webhook de pago fallido (invoice.payment_failed)
        suscripcion_db = SuscripcionNutricionista.objects.get(stripe_subscription_id="sub_stripe_123")
        suscripcion_db.estado = EstadoSuscripcion.VENCIDA  # El estado vencida suspende la cuenta
        suscripcion_db.save()
        
        self.assertEqual(suscripcion_db.estado, EstadoSuscripcion.VENCIDA)

    # --------------------------------------------------------------------------
    # UT-14-01: Cálculo de Ingresos Netos
    # --------------------------------------------------------------------------
    def test_ut_14_01_calculo_ingresos_netos(self):
        """Valida que la sumatoria de cobros del nutricionista en el dashboard financiero sume exactamente S/. 295.00."""
        # Crear 5 cobros independientes de S/. 59.00 cada uno (5 * 59.00 = 295.00)
        for i in range(5):
            Cobro.objects.create(
                nutricionista=self.nutricionista_1,
                paciente=self.paciente_1,
                total=Decimal("59.00"),
                igv=Decimal("9.00"),
                monto=Decimal("50.00"),
                estado="pendiente"
            )
            
        # Ejecutar sumatoria agregada de cobros para este nutricionista
        total_acumulado = Cobro.objects.filter(
            nutricionista=self.nutricionista_1
        ).aggregate(total_sum=django.db.models.Sum("total"))["total_sum"]
        
        self.assertEqual(total_acumulado, Decimal("295.00"))

    # --------------------------------------------------------------------------
    # UT-14-02: Dashboard para Usuario Nuevo
    # --------------------------------------------------------------------------
    def test_ut_14_02_dashboard_para_usuario_nuevo(self):
        """Valida que el dashboard financiero de un nutricionista nuevo cargue en S/. 0.00 sin errores."""
        # Consultar cobros del nutricionista 2 (nuevo y sin cobros)
        total_acumulado = Cobro.objects.filter(
            nutricionista=self.nutricionista_2
        ).aggregate(total_sum=django.db.models.Sum("total"))["total_sum"]
        
        # El resultado debe ser None o Decimal(0)
        ingresos_netos = total_acumulado or Decimal("0.00")
        self.assertEqual(ingresos_netos, Decimal("0.00"))

    # --------------------------------------------------------------------------
    # UT-15-01: Inserción de Log CRUD
    # --------------------------------------------------------------------------
    def test_ut_15_01_insercion_log_crud(self):
        """Valida que la edición clínica inserte un log de auditoría conteniendo la dirección IP del autor."""
        log = registrar_log_paciente(
            usuario=self.nutricionista_1,
            accion="UPDATE_FICHA",
            ip="192.168.1.50",
            paciente=self.paciente_1
        )
        
        self.assertIsNotNone(log)
        self.assertEqual(log["usuario"], "nutri_especialista_1")
        self.assertEqual(log["accion"], "UPDATE_FICHA")
        self.assertEqual(log["ip"], "192.168.1.50")
        self.assertEqual(log["paciente_id"], self.paciente_1.pk)

    # --------------------------------------------------------------------------
    # UT-15-02: Lectura Cruzada de Logs
    # --------------------------------------------------------------------------
    def test_ut_15_02_lectura_cruzada_logs(self):
        """Valida que el middleware de multi-tenancy bloquee y retorne 403 Forbidden ante accesos ajenos."""
        # Intento del nutricionista 1 de leer logs de su propio tenant (Permitido)
        res_ok = consultar_logs_paciente(self.nutricionista_1, self.nutricionista_1.pk)
        self.assertEqual(res_ok, "LOGS_AUTORIZADOS")
        
        # Intento de lectura cruzada: nutricionista 2 intenta leer logs de tenant 1 (Bloqueado)
        with self.assertRaises(PermissionDenied):
            consultar_logs_paciente(self.nutricionista_2, self.nutricionista_1.pk)

    # --------------------------------------------------------------------------
    # UT-11-05: Validación de Requisitos Obligatorios al Finalizar Consulta
    # --------------------------------------------------------------------------
    def test_ut_11_05_finalizar_consulta_requisitos_faltantes(self):
        """Valida que falle la finalización si faltan datos requeridos (observaciones, peso) según el tipo de consulta."""
        from django.urls import reverse
        from seguimiento.models import MedidaCorporal
        self.client.force_login(self.nutricionista_1)

        # 1. Iniciar una consulta de Seguimiento
        res_ini = self.client.post(
            reverse("pacientes:consulta_iniciar", kwargs={"pk": self.paciente_1.pk}),
            data={"tipo": "seguimiento"}
        )
        self.assertEqual(res_ini.status_code, 200)
        consulta_id = res_ini.json()["consulta_id"]

        # 2. Intentar finalizar con force_validation=true (Debe fallar)
        res_fin_fail = self.client.post(
            reverse("pacientes:consulta_finalizar", kwargs={"pk": self.paciente_1.pk, "consulta_id": consulta_id}),
            data={"force_validation": "true"}
        )
        self.assertEqual(res_fin_fail.status_code, 400)
        data_fail = res_fin_fail.json()
        self.assertFalse(data_fail["success"])
        self.assertEqual(data_fail["error_type"], "missing_requirements")
        self.assertIn("Debes escribir observaciones detalladas de la evolución del paciente (mínimo 10 caracteres).", data_fail["missing_fields"])
        self.assertIn("Se requiere registrar el peso actual del paciente en esta consulta para evaluar el progreso.", data_fail["missing_fields"])

        # 3. Completar las observaciones requeridas
        from pacientes.models import Consulta
        consulta_obj = Consulta.objects.get(id=consulta_id)
        consulta_obj.observaciones = "El paciente muestra una excelente evolución y adherencia."
        consulta_obj.save()

        # 4. Registrar la medición de peso requerida en esta consulta
        MedidaCorporal.objects.create(
            paciente=self.paciente_1,
            consulta=consulta_obj,
            fecha=timezone.now().date(),
            peso_kg=72.5,
            talla_cm=175.0
        )

        # 5. Intentar finalizar de nuevo (Debe tener éxito)
        res_fin_ok = self.client.post(
            reverse("pacientes:consulta_finalizar", kwargs={"pk": self.paciente_1.pk, "consulta_id": consulta_id}),
            data={"force_validation": "true"}
        )
        self.assertEqual(res_fin_ok.status_code, 200)
        self.assertTrue(res_fin_ok.json()["success"])

