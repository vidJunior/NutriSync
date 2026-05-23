# pacientes/tests.py
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.urls import reverse
from pacientes.models import Paciente


class PacienteCreateViewTestCase(TestCase):
    def setUp(self):
        # Crear nutricionista para autenticación
        self.nutricionista = User.objects.create_user(
            username="nutri_test", email="nutri_test@gmail.com", password="password123"
        )
        self.client.login(username="nutri_test", password="password123")
        
        self.form_data = {
            "nombre": "Carlos",
            "apellido": "Gómez",
            "dni": "12345678",
            "telefono": "987654321",
            "email": "carlos@gmail.com",
            "sexo": "M",
            "fecha_nacimiento": "1990-05-15",
            "peso": 75.5,
            "talla": 170.0,
        }

    def test_crear_paciente_pagina_completa_redirecciona(self):
        """
        Valida que al enviar el formulario normalmente (sin AJAX ni fragment),
        se cree el paciente y se redireccione al detalle.
        """
        response = self.client.post(
            reverse("pacientes:nuevo"),
            data=self.form_data,
            follow=False
        )
        # Debería haber redireccionado (302) a la ficha del paciente detalle
        self.assertEqual(response.status_code, 302)
        
        # Verificar que se creó el paciente
        paciente = Paciente.objects.filter(nombre="Carlos", apellido="Gómez").first()
        self.assertIsNotNone(paciente)
        self.assertEqual(paciente.nutricionista, self.nutricionista)
        
        # Verificar URL de redirección
        expected_url = reverse("pacientes:detalle", kwargs={"pk": paciente.pk})
        self.assertRedirects(response, expected_url)

    def test_crear_paciente_ajax_retorna_fragmento_exito(self):
        """
        Valida que al enviar el formulario por AJAX (con la cabecera HTTP_X_REQUESTED_WITH),
        se cree el paciente y se retorne la respuesta parcial de éxito (HTML snippet).
        """
        response = self.client.post(
            reverse("pacientes:nuevo"),
            data=self.form_data,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        # Debería retornar 200 OK con el fragmento HTML de éxito
        self.assertEqual(response.status_code, 200)
        
        # Verificar que se creó el paciente
        paciente = Paciente.objects.filter(nombre="Carlos", apellido="Gómez").first()
        self.assertIsNotNone(paciente)
        
        # Verificar que la respuesta contiene el div de éxito con el ID correcto y el pk
        expected_content = f'<div id="paciente-form-success" data-success="true" data-pk="{paciente.pk}"></div>'
        self.assertContains(response, expected_content)

    def test_crear_paciente_formulario_invalido_pagina_completa(self):
        """
        Valida que el envío de un formulario inválido en página completa devuelva
        la página completa con los errores.
        """
        invalid_data = self.form_data.copy()
        invalid_data["nombre"] = ""  # Requerido
        
        response = self.client.post(
            reverse("pacientes:nuevo"),
            data=invalid_data
        )
        self.assertEqual(response.status_code, 200)
        # Debe renderizar el template completo (que hereda de base.html)
        self.assertTemplateUsed(response, "pacientes/form.html")
        self.assertFormError(response.context["form"], "nombre", "Este campo es obligatorio.")

    def test_crear_paciente_formulario_invalido_ajax(self):
        """
        Valida que el envío de un formulario inválido por AJAX devuelva
        únicamente el fragmento del formulario con los errores.
        """
        invalid_data = self.form_data.copy()
        invalid_data["nombre"] = ""  # Requerido
        
        response = self.client.post(
            reverse("pacientes:nuevo"),
            data=invalid_data,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(response.status_code, 200)
        # Debe usar el fragmento en vez de la página completa
        self.assertTemplateUsed(response, "pacientes/_form_content.html")
        self.assertFormError(response.context["form"], "nombre", "Este campo es obligatorio.")

    def test_crear_paciente_dni_corto_ajax(self):
        """
        Valida que el envío de un formulario con DNI de menos de 8 dígitos por AJAX
        devuelva el fragmento con el error de DNI y no un error 404.
        """
        invalid_data = self.form_data.copy()
        invalid_data["dni"] = "12345"  # DNI corto
        
        response = self.client.post(
            reverse("pacientes:nuevo"),
            data=invalid_data,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pacientes/_form_content.html")
        self.assertFormError(response.context["form"], "dni", "El DNI debe tener exactamente 8 dígitos numéricos.")

    def test_crear_paciente_dni_corto_pagina_completa(self):
        """
        Valida que el envío de un formulario con DNI de menos de 8 dígitos sin AJAX
        devuelva la página completa con el error de DNI y no un error 404.
        """
        invalid_data = self.form_data.copy()
        invalid_data["dni"] = "12345"  # DNI corto
        
        response = self.client.post(
            reverse("pacientes:nuevo"),
            data=invalid_data
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pacientes/form.html")
        self.assertFormError(response.context["form"], "dni", "El DNI debe tener exactamente 8 dígitos numéricos.")

    def test_crear_paciente_sexo_vacio_ajax(self):
        """
        Valida que el envío de un formulario con sexo vacío por AJAX
        devuelva el fragmento con el error de sexo.
        """
        invalid_data = self.form_data.copy()
        invalid_data["sexo"] = ""  # Sexo vacío
        
        response = self.client.post(
            reverse("pacientes:nuevo"),
            data=invalid_data,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pacientes/_form_content.html")
        self.assertFormError(response.context["form"], "sexo", "Debe seleccionar un género (Masculino o Femenino).")


class PacienteValidationTestCase(TestCase):
    def setUp(self):
        # Crear nutricionistas
        self.nutri1 = User.objects.create_user(
            username="nutri1", email="nutri1@gmail.com", password="password123"
        )
        self.nutri2 = User.objects.create_user(
            username="nutri2", email="nutri2@gmail.com", password="password123"
        )

    def test_dni_valido_y_error(self):
        # DNI de 8 dígitos numéricos es válido
        p = Paciente(
            nutricionista=self.nutri1,
            nombre="Carlos",
            apellido="Gómez",
            dni="12345678",
            fecha_nacimiento="1990-05-15",
            sexo="M",
            peso=75.5,
            telefono="987654321",
        )
        try:
            p.full_clean()
        except ValidationError:
            self.fail("full_clean() raised ValidationError for a valid patient.")

        # DNI corto
        p.dni = "1234567"
        with self.assertRaises(ValidationError):
            p.full_clean()

        # DNI con letras
        p.dni = "1234567A"
        with self.assertRaises(ValidationError):
            p.full_clean()

    def test_telefono_valido_y_error(self):
        p = Paciente(
            nutricionista=self.nutri1,
            nombre="Carlos",
            apellido="Gómez",
            dni="12345678",
            fecha_nacimiento="1990-05-15",
            sexo="M",
            peso=75.5,
            telefono="987654321",
        )
        # Teléfono incorrecto length
        p.telefono = "12345678"
        with self.assertRaises(ValidationError):
            p.full_clean()

        p.telefono = "9876543210"
        with self.assertRaises(ValidationError):
            p.full_clean()

    def test_peso_valido_y_error(self):
        p = Paciente(
            nutricionista=self.nutri1,
            nombre="Carlos",
            apellido="Gómez",
            dni="12345678",
            fecha_nacimiento="1990-05-15",
            sexo="M",
            peso=75.5,
            telefono="987654321",
        )
        # Peso menor a 2
        p.peso = 1.5
        with self.assertRaises(ValidationError):
            p.full_clean()

        # Peso mayor a 500
        p.peso = 505.0
        with self.assertRaises(ValidationError):
            p.full_clean()

    def test_talla_valido_y_error(self):
        p = Paciente(
            nutricionista=self.nutri1,
            nombre="Carlos",
            apellido="Gómez",
            dni="12345678",
            fecha_nacimiento="1990-05-15",
            sexo="M",
            peso=75.5,
            talla=170.0,
            telefono="987654321",
        )
        # Talla menor a 50
        p.talla = 45.0
        with self.assertRaises(ValidationError):
            p.full_clean()

        # Talla mayor a 250
        p.talla = 255.0
        with self.assertRaises(ValidationError):
            p.full_clean()

    def test_fecha_nacimiento_edad_minima(self):
        p = Paciente(
            nutricionista=self.nutri1,
            nombre="Carlos",
            apellido="Gómez",
            dni="12345678",
            fecha_nacimiento="1990-05-15",
            sexo="M",
            peso=75.5,
            telefono="987654321",
        )
        # Edad menos de 1 año (ej. hoy)
        from datetime import date
        p.fecha_nacimiento = date.today()
        with self.assertRaises(ValidationError):
            p.full_clean()

    def test_unicidad_dni_por_nutricionista(self):
        # Crear primer paciente
        Paciente.objects.create(
            nutricionista=self.nutri1,
            nombre="Juan",
            apellido="Pérez",
            dni="11112222",
            fecha_nacimiento="1990-01-01",
            sexo="M",
            peso=70.0,
            telefono="999888777",
        )

        # Mismo nutricionista, mismo DNI -> Debe fallar a nivel de DB/clean
        dup = Paciente(
            nutricionista=self.nutri1,
            nombre="Pedro",
            apellido="Soto",
            dni="11112222",
            fecha_nacimiento="1990-01-01",
            sexo="M",
            peso=70.0,
            telefono="999888777",
        )
        with self.assertRaises(ValidationError):
            dup.full_clean()

        # Diferente nutricionista, mismo DNI -> Debe pasar
        ok = Paciente(
            nutricionista=self.nutri2,
            nombre="Pedro",
            apellido="Soto",
            dni="11112222",
            fecha_nacimiento="1990-01-01",
            sexo="M",
            peso=70.0,
            telefono="999888777",
        )
        try:
            ok.full_clean()
        except ValidationError:
            self.fail("Diferente nutricionista con mismo DNI no debería fallar.")

    def test_nombre_apellido_no_identicos_form(self):
        from pacientes.forms import PacienteForm
        form_data = {
            "nombre": "Juan",
            "apellido": "Juan",
            "dni": "12345678",
            "telefono": "987654321",
            "sexo": "M",
            "fecha_nacimiento": "1990-05-15",
            "peso": 75.5,
            "talla": 170.0,
        }
        form = PacienteForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("El nombre y el apellido del paciente no pueden ser idénticos.", form.non_field_errors())


class MedidaCorporalSyncTestCase(TestCase):
    def setUp(self):
        self.nutricionista = User.objects.create_user(
            username="nutri_test", email="nutri_test@gmail.com", password="password123"
        )
        self.paciente = Paciente.objects.create(
            nutricionista=self.nutricionista,
            nombre="Carlos",
            apellido="Gómez",
            dni="12345678",
            fecha_nacimiento="1990-05-15",
            sexo="M",
            peso=75.5,
            talla=170.0,
            telefono="987654321",
        )

    def test_sincronizacion_automatica_peso_y_talla(self):
        """
        Valida que al crear una MedidaCorporal con diferente peso y talla,
        el perfil del Paciente se actualice de forma automática en la BD.
        """
        from seguimiento.models import MedidaCorporal
        from datetime import date

        # Crear medida con nuevos valores
        MedidaCorporal.objects.create(
            paciente=self.paciente,
            fecha=date.today(),
            peso_kg=80.0,
            talla_cm=175.0,
        )

        # Recargar de base de datos
        self.paciente.refresh_from_db()

        # Verificar sincronización
        self.assertEqual(float(self.paciente.peso), 80.0)
        self.assertEqual(float(self.paciente.talla), 175.0)

    def test_sincronizacion_sin_cambio(self):
        """
        Valida que si los valores son iguales, la sincronización no cause fallos
        y se mantengan idénticos.
        """
        from seguimiento.models import MedidaCorporal
        from datetime import date

        # Crear medida con valores iguales
        MedidaCorporal.objects.create(
            paciente=self.paciente,
            fecha=date.today(),
            peso_kg=75.5,
            talla_cm=170.0,
        )

        # Recargar de base de datos
        self.paciente.refresh_from_db()

        self.assertEqual(float(self.paciente.peso), 75.5)
        self.assertEqual(float(self.paciente.talla), 170.0)

    def test_precarga_automatica_peso_y_talla_en_formulario(self):
        """
        Valida que al cargar el formulario de nueva medida para un paciente,
        el peso y la talla del paciente se precarguen automáticamente.
        """
        self.client.login(username="nutri_test", password="password123")
        response = self.client.get(
            reverse("seguimiento:medidas_nueva", kwargs={"paciente_pk": self.paciente.pk})
        )
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertEqual(float(form.initial["talla_cm"]), 170.0)
        self.assertEqual(float(form.initial["peso_kg"]), 75.5)

    def test_precarga_automatica_con_medidas_previas(self):
        """
        Valida que si el paciente ya tiene medidas registradas, el formulario
        de nueva medida se inicialice con los valores de la última medición (los más recientes),
        en lugar de los valores del expediente original del paciente.
        """
        from seguimiento.models import MedidaCorporal
        from datetime import date

        # Crear una medida previa con valores actualizados
        MedidaCorporal.objects.create(
            paciente=self.paciente,
            fecha=date.today(),
            peso_kg=82.5,
            talla_cm=172.0,
        )

        self.client.login(username="nutri_test", password="password123")
        response = self.client.get(
            reverse("seguimiento:medidas_nueva", kwargs={"paciente_pk": self.paciente.pk})
        )
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertEqual(float(form.initial["talla_cm"]), 172.0)
        self.assertEqual(float(form.initial["peso_kg"]), 82.5)

    def test_precarga_edicion_paciente_con_medidas_recientes(self):
        """
        Valida que al abrir el formulario para editar a un paciente existente,
        el peso y la talla del formulario se inicialicen con los valores más recientes
        del historial de seguimiento si existen.
        """
        from seguimiento.models import MedidaCorporal
        from datetime import date

        # Crear una medida previa con valores actualizados
        MedidaCorporal.objects.create(
            paciente=self.paciente,
            fecha=date.today(),
            peso_kg=82.5,
            talla_cm=172.0,
        )

        self.client.login(username="nutri_test", password="password123")
        response = self.client.get(
            reverse("pacientes:editar", kwargs={"pk": self.paciente.pk})
        )
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertEqual(float(form.initial["talla"]), 172.0)
        self.assertEqual(float(form.initial["peso"]), 82.5)

    def test_fecha_medicion_automatica_a_hoy(self):
        """
        Valida que al registrar una nueva medida corporal, la fecha se asigne
        automáticamente al día de hoy (sin tener que proveerla en el formulario).
        """
        from datetime import date
        from seguimiento.models import MedidaCorporal
        self.client.login(username="nutri_test", password="password123")
        
        form_data = {
            "peso_kg": 80.0,
            "talla_cm": 170.0,
        }
        
        # Antes del registro, no hay medidas
        self.assertEqual(MedidaCorporal.objects.filter(paciente=self.paciente).count(), 0)
        
        response = self.client.post(
            reverse("seguimiento:medidas_nueva", kwargs={"paciente_pk": self.paciente.pk}),
            data=form_data
        )
        self.assertEqual(response.status_code, 302)  # Redirección exitosa
        
        # Validamos que se haya creado la medida
        medida = MedidaCorporal.objects.filter(paciente=self.paciente).first()
        self.assertIsNotNone(medida)
        self.assertEqual(medida.fecha, date.today())

    def test_notas_recientes_en_detalle_paciente(self):
        """
        Valida que al cargar la ficha clínica del paciente (PacienteDetailView),
        las notas clínicas registradas se inyecten correctamente en el contexto
        para ser mostradas en su ficha.
        """
        from seguimiento.models import NotaClinica
        from datetime import date

        # Crear una nota clínica de prueba
        NotaClinica.objects.create(
            paciente=self.paciente,
            fecha=date.today(),
            titulo="Control Rutinario",
            contenido="Paciente muestra progresos excelentes.",
            tipo="consulta",
        )

        self.client.login(username="nutri_test", password="password123")
        response = self.client.get(
            reverse("pacientes:detalle", kwargs={"pk": self.paciente.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("notas_recientes", response.context)
        notas_context = response.context["notas_recientes"]
        self.assertEqual(len(notas_context), 1)
        self.assertEqual(notas_context[0].titulo, "Control Rutinario")


