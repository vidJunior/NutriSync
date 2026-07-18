from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from decimal import Decimal
from core.models import PerfilNutricionista, Rol
from core.forms import PerfilNutricionistaForm
from facturacion.models import PlanSuscripcion

class ColegiaturaUnicaTestCase(TestCase):
    def setUp(self):
        # Crea el plan de prueba.
        self.plan = PlanSuscripcion.objects.create(
            nombre="Prueba Gratis",
            descripcion="Plan de prueba",
            precio_mensual=Decimal("0.00"),
            precio_anual=Decimal("0.00"),
            limite_pacientes=10,
            activo=True
        )
        
        # Crear un usuario nutricionista inicial
        self.user1 = User.objects.create_user(
            username="nutri1",
            email="nutri1@example.com",
            password="Password123"
        )
        
        # Completa el perfil si la señal no lo creó.
        self.perfil1, created = PerfilNutricionista.objects.get_or_create(
            usuario=self.user1,
            defaults={
                'nombre_completo': "Nutricionista Uno",
                'numero_colegiatura': "CNP-12345",
                'rol': Rol.NUTRICIONISTA,
                'estado': 'habilitado'
            }
        )
        if not created:
            self.perfil1.numero_colegiatura = "CNP-12345"
            self.perfil1.save()

        # Crea otro usuario.
        self.user2 = User.objects.create_user(
            username="nutri2",
            email="nutri2@example.com",
            password="Password123"
        )
        self.perfil2, created = PerfilNutricionista.objects.get_or_create(
            usuario=self.user2,
            defaults={
                'nombre_completo': "Nutricionista Dos",
                'numero_colegiatura': "CNP-54321",
                'rol': Rol.NUTRICIONISTA,
                'estado': 'habilitado'
            }
        )
        if not created:
            self.perfil2.numero_colegiatura = "CNP-54321"
            self.perfil2.save()

    def test_registro_rechazado_por_cnp_duplicado(self):
        """Valida que no se pueda registrar un nutricionista con una colegiatura existente."""
        response = self.client.post(reverse('core:register'), {
            'username': 'nutri_nuevo',
            'email': 'nuevo@example.com',
            'password': 'Password123',
            'password_confirm': 'Password123',
            'nombre_completo': 'Nutricionista Nuevo',
            'especialidad': 'Deportiva',
            'telefono': '999999999',
            'numero_colegiatura': 'CNP-12345',  # CNP duplicado de user1
            'direccion_consultorio': 'Av. Larco 123',
            'plan': self.plan.pk,
            'payment_method_type': 'tarjeta',
            'card_number': '4111 1111 1111 1111',
            'card_expiry': '12/30',
            'card_cvc': '123',
            'dni': '77777777'
        })
        
        # Muestra el formulario con el error.
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "El número de colegiatura C.N.P. ya está registrado.")
        
        # Confirma que el usuario no existe.
        self.assertFalse(User.objects.filter(username='nutri_nuevo').exists())

    def test_editar_perfil_rechaza_cnp_duplicado(self):
        """Valida que al editar el perfil no se permita usar un CNP duplicado."""
        self.client.login(username="nutri2", password="Password123")
        
        # Intenta duplicar la colegiatura.
        form_data = {
            "nombre_completo": "Nutricionista Dos Modificado",
            "especialidad": "Clínica",
            "telefono": "987654321",
            "email_profesional": "nutri2@example.com",
            "numero_colegiatura": "CNP-12345",  # CNP duplicado
            "direccion_consultorio": "Av. Arequipa 500"
        }
        
        form = PerfilNutricionistaForm(data=form_data, instance=self.perfil2)
        self.assertFalse(form.is_valid())
        self.assertIn("numero_colegiatura", form.errors)
        self.assertEqual(
            form.errors["numero_colegiatura"][0],
            "Este número de colegiatura C.N.P. ya está registrado."
        )
