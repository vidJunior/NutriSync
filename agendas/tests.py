# agendas/tests.py
# Pruebas de agenda.

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from pacientes.models import Paciente
from agendas.models import Cita
from config.choices import TipoCita, EstadoCita


class CitaModelTestCase(TestCase):
    """
    Pruebas unitarias para validar las reglas de negocio del modelo Cita:
    1. Bloqueo de citas a pacientes inactivos.
    2. Bloqueo de solapamiento de horarios del mismo nutricionista.
    3. Permiso de solapamiento en nutricionistas diferentes.
    4. Permiso de solapamiento con citas canceladas.
    """

    def setUp(self):
        # 1. Crear usuarios nutricionistas
        self.nutricionista_a = User.objects.create_user(
            username="nutri_a", email="nutri_a@gmail.com", password="password123"
        )
        self.nutricionista_b = User.objects.create_user(
            username="nutri_b", email="nutri_b@gmail.com", password="password123"
        )

        # 2. Crear pacientes para el nutricionista A
        self.paciente_activo_a = Paciente.objects.create(
            nutricionista=self.nutricionista_a,
            nombre="Juan",
            apellido="Pérez",
            dni="12345678",
            telefono="987654321",
            estado=True,  # Activo
            fecha_nacimiento="1990-01-01",
            sexo="M",
            peso=70.0,
        )
        self.paciente_inactivo_a = Paciente.objects.create(
            nutricionista=self.nutricionista_a,
            nombre="María",
            apellido="Gómez",
            dni="87654321",
            telefono="912345678",
            estado=False,  # Inactivo
            fecha_nacimiento="1992-05-10",
            sexo="F",
            peso=60.0,
        )

        # 3. Crear paciente para el nutricionista B
        self.paciente_activo_b = Paciente.objects.create(
            nutricionista=self.nutricionista_b,
            nombre="Carlos",
            apellido="López",
            dni="11223344",
            telefono="954321678",
            estado=True,  # Activo
            fecha_nacimiento="1988-11-20",
            sexo="M",
            peso=80.0,
        )

        # Usar una fecha futura fija para las pruebas
        self.fecha_base = timezone.localtime(timezone.now()) + timedelta(days=5)

    def test_crear_cita_paciente_activo_exitoso(self):
        """Valida que se pueda programar correctamente una cita a un paciente activo."""
        cita = Cita.objects.create(
            paciente=self.paciente_activo_a,
            fecha_hora=self.fecha_base,
            duracion_minutos=45,
            tipo=TipoCita.EVALUACION,
            estado=EstadoCita.PROGRAMADA,
            motivo="Consulta de rutina",
        )
        self.assertIsNotNone(cita.pk)
        self.assertEqual(cita.paciente, self.paciente_activo_a)

    def test_error_cita_paciente_inactivo(self):
        """Valida que no se permita agendar citas a pacientes inactivos."""
        cita = Cita(
            paciente=self.paciente_inactivo_a,
            fecha_hora=self.fecha_base,
            duracion_minutos=45,
            motivo="Consulta de rutina",
        )
        # Debe lanzar una ValidationError
        with self.assertRaises(ValidationError) as context:
            cita.save()
        
        self.assertIn("No se pueden programar citas para un paciente inactivo.", str(context.exception))

    def test_error_solapamiento_mismo_nutricionista(self):
        """Valida que no se permitan dos citas solapadas para el mismo nutricionista."""
        # Programar la primera cita: 10:00 - 10:45
        hora_cita = self.fecha_base.replace(hour=10, minute=0, second=0, microsecond=0)
        Cita.objects.create(
            paciente=self.paciente_activo_a,
            fecha_hora=hora_cita,
            duracion_minutos=45,
            motivo="Consulta de rutina",
        )

        # Intento 1: Solapamiento exacto (10:00 - 10:45)
        cita_solapada_1 = Cita(
            paciente=self.paciente_activo_a,
            fecha_hora=hora_cita,
            duracion_minutos=45,
            motivo="Consulta de rutina",
        )
        with self.assertRaises(ValidationError):
            cita_solapada_1.save()

        # 2. Cruce al inicio.
        cita_solapada_2 = Cita(
            paciente=self.paciente_activo_a,
            fecha_hora=hora_cita - timedelta(minutes=15),
            duracion_minutos=45,
            motivo="Consulta de rutina",
        )
        with self.assertRaises(ValidationError):
            cita_solapada_2.save()

        # 3. Cruce al final.
        cita_solapada_3 = Cita(
            paciente=self.paciente_activo_a,
            fecha_hora=hora_cita + timedelta(minutes=15),
            duracion_minutos=45,
            motivo="Consulta de rutina",
        )
        with self.assertRaises(ValidationError):
            cita_solapada_3.save()

        # 4. Intervalo contenido.
        cita_solapada_4 = Cita(
            paciente=self.paciente_activo_a,
            fecha_hora=hora_cita + timedelta(minutes=10),
            duracion_minutos=20,
            motivo="Consulta de rutina",
        )
        with self.assertRaises(ValidationError):
            cita_solapada_4.save()

    def test_exito_citas_consecutivas_sin_solapamiento(self):
        """Valida que se puedan registrar citas inmediatamente consecutivas sin error."""
        hora_cita_1 = self.fecha_base.replace(hour=10, minute=0, second=0, microsecond=0)
        # Cita 1: 10:00 - 10:45
        Cita.objects.create(
            paciente=self.paciente_activo_a,
            fecha_hora=hora_cita_1,
            duracion_minutos=45,
            motivo="Consulta de rutina",
        )

        # Cita 2: 10:45 - 11:30 (Consecutiva exacta)
        cita_consecutiva = Cita(
            paciente=self.paciente_activo_a,
            fecha_hora=hora_cita_1 + timedelta(minutes=45),
            duracion_minutos=45,
            motivo="Consulta de rutina",
        )
        # No debe lanzar error
        try:
            cita_consecutiva.save()
        except ValidationError:
            self.fail("ValidationError lanzada en cita consecutiva no solapada.")

    def test_exito_solapamiento_nutricionistas_diferentes(self):
        """Valida que dos nutricionistas diferentes sí puedan programar citas a la misma hora."""
        hora_cita = self.fecha_base.replace(hour=10, minute=0, second=0, microsecond=0)
        # Nutricionista A programa cita de 10:00 a 10:45
        Cita.objects.create(
            paciente=self.paciente_activo_a,
            fecha_hora=hora_cita,
            duracion_minutos=45,
            motivo="Consulta de rutina",
        )

        # Otro nutricionista usa el mismo horario.
        cita_nutri_b = Cita(
            paciente=self.paciente_activo_b,
            fecha_hora=hora_cita,
            duracion_minutos=45,
            motivo="Consulta de rutina",
        )
        
        # No debe lanzar error
        try:
            cita_nutri_b.save()
        except ValidationError:
            self.fail("ValidationError lanzada indebidamente al solaparse citas de distintos nutricionistas.")

    def test_exito_solapamiento_con_cita_cancelada(self):
        """Valida que se pueda agendar en el mismo horario si la cita preexistente fue cancelada."""
        hora_cita = self.fecha_base.replace(hour=10, minute=0, second=0, microsecond=0)
        # Programar cita de 10:00 a 10:45 y luego cancelarla
        cita_cancelada = Cita.objects.create(
            paciente=self.paciente_activo_a,
            fecha_hora=hora_cita,
            duracion_minutos=45,
            motivo="Consulta de rutina",
        )
        cita_cancelada.estado = EstadoCita.CANCELADA
        cita_cancelada.save()

        # Programar nueva cita en el mismo horario
        nueva_cita = Cita(
            paciente=self.paciente_activo_a,
            fecha_hora=hora_cita,
            duracion_minutos=45,
            motivo="Consulta de rutina",
        )
        
        # No debe lanzar error
        try:
            nueva_cita.save()
        except ValidationError:
            self.fail("ValidationError lanzada al solapar con cita cancelada.")

    def test_bloqueo_horario_exitoso(self):
        """Valida que se pueda crear un bloqueo de horario sin paciente."""
        bloqueo = Cita.objects.create(
            paciente=None,
            nutricionista=self.nutricionista_a,
            fecha_hora=self.fecha_base,
            duracion_minutos=60,
            tipo=TipoCita.BLOQUEO,
            estado=EstadoCita.BLOQUEADA,
            motivo="Almuerzo",
        )
        self.assertIsNotNone(bloqueo.pk)
        self.assertIsNone(bloqueo.paciente)
        self.assertEqual(bloqueo.nutricionista, self.nutricionista_a)

    def test_error_solapamiento_cita_con_bloqueo(self):
        """Valida que no se permita agendar una cita que se solape con un bloqueo de horario."""
        hora_base = self.fecha_base.replace(hour=11, minute=0, second=0, microsecond=0)
        # Crear bloqueo de 11:00 a 12:00
        Cita.objects.create(
            paciente=None,
            nutricionista=self.nutricionista_a,
            fecha_hora=hora_base,
            duracion_minutos=60,
            tipo=TipoCita.BLOQUEO,
            estado=EstadoCita.BLOQUEADA,
            motivo="Reunión",
        )

        # Cita de 11:30 a 12:15
        cita_solapada = Cita(
            paciente=self.paciente_activo_a,
            fecha_hora=hora_base + timedelta(minutes=30),
            duracion_minutos=45,
            motivo="Consulta de rutina",
        )
        
        with self.assertRaises(ValidationError):
            cita_solapada.save()

    def test_error_solapamiento_bloqueo_con_cita(self):
        """Valida que no se permita crear un bloqueo que se solape con una cita preexistente."""
        hora_base = self.fecha_base.replace(hour=14, minute=0, second=0, microsecond=0)
        # Crear cita de 14:00 a 14:45
        Cita.objects.create(
            paciente=self.paciente_activo_a,
            fecha_hora=hora_base,
            duracion_minutos=45,
            motivo="Consulta de rutina",
        )

        # Bloqueo de 14:30 a 15:30
        bloqueo_solapado = Cita(
            paciente=None,
            nutricionista=self.nutricionista_a,
            fecha_hora=hora_base + timedelta(minutes=30),
            duracion_minutos=60,
            tipo=TipoCita.BLOQUEO,
            estado=EstadoCita.BLOQUEADA,
            motivo="Capacitación",
        )
        
        with self.assertRaises(ValidationError):
            bloqueo_solapado.save()
