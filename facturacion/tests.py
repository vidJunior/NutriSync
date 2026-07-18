from datetime import date

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse

from pacientes.models import Paciente

from .choices import EstadoCobro
from .models import Cobro, Pago
from .validators import (
    validate_cvv,
    validate_datos_yape,
    validate_email_paypal,
    validate_numero_tarjeta,
)


class PaymentValidationTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="nutri_payments",
            password="StrongPass123!",
        )
        self.paciente = Paciente.objects.create(
            nutricionista=self.user,
            nombre="Paciente",
            apellido="Prueba",
            dni="76543210",
            fecha_nacimiento=date(1990, 1, 1),
            sexo="F",
            peso=60,
            talla=165,
            telefono="987654321",
        )
        self.cobro = Cobro.objects.create(
            nutricionista=self.user,
            paciente=self.paciente,
            concepto="consulta",
            descripcion="Consulta nutricional",
            monto="100.00",
        )
        self.client.force_login(self.user)

    def test_validadores_aceptan_datos_de_prueba(self):
        self.assertEqual(
            validate_numero_tarjeta("4111 1111 1111 1111"),
            "4111111111111111",
        )
        self.assertEqual(validate_cvv("123"), "123")
        self.assertEqual(
            validate_datos_yape("987654321", "123456"),
            "987654321",
        )
        self.assertEqual(
            validate_email_paypal("TEST@example.com"),
            "test@example.com",
        )

    def test_validadores_rechazan_datos_manipulados(self):
        with self.assertRaises(ValidationError):
            validate_numero_tarjeta("4111111111111112")
        with self.assertRaises(ValidationError):
            validate_datos_yape("123", "abc")
        with self.assertRaises(ValidationError):
            validate_email_paypal("correo-invalido")

    @override_settings(PAYMENT_SANDBOX=False)
    def test_checkout_simulado_no_marca_pago_en_produccion(self):
        response = self.client.post(
            reverse(
                "facturacion:crear_checkout_cobro",
                kwargs={"pk": self.cobro.pk},
            )
        )
        self.assertEqual(response.status_code, 302)
        self.cobro.refresh_from_db()
        self.assertEqual(self.cobro.estado, EstadoCobro.PENDIENTE)
        self.assertFalse(Pago.objects.filter(cobro=self.cobro).exists())

    def test_callback_get_no_modifica_estado_financiero(self):
        response = self.client.get(
            reverse("facturacion:checkout_exito"),
            {"type": "cobro", "id": self.cobro.pk},
        )
        self.assertEqual(response.status_code, 302)
        self.cobro.refresh_from_db()
        self.assertEqual(self.cobro.estado, EstadoCobro.PENDIENTE)
        self.assertFalse(Pago.objects.filter(cobro=self.cobro).exists())
