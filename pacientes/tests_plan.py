from datetime import date
from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from pacientes.models import Paciente, PlanAlimentario
from nutricion.models import Receta

class PlanAlimentarioTestCase(TestCase):
    def setUp(self):
        # Create dietitian user
        self.nutricionista = User.objects.create_user(
            username="nutri_test_plan", email="nutri_plan@gmail.com", password="password123"
        )
        self.client.login(username="nutri_test_plan", password="password123")

        # Create patient
        self.paciente = Paciente.objects.create(
            nutricionista=self.nutricionista,
            nombre="Alejandro",
            apellido="Carrasco",
            dni="87654321",
            fecha_nacimiento=date(1995, 3, 10),
            sexo="M",
            peso=85.0,
            talla=180.0,
            telefono="987654321",
        )
        from pacientes.models import Consulta
        self.consulta = Consulta.objects.create(
            paciente=self.paciente,
            profesional=self.nutricionista,
            numero_consulta=1,
            estado="en_curso"
        )
        self.receta_desayuno = Receta.objects.create(
            nombre="Desayuno de prueba",
            creado_por=self.nutricionista,
            es_sistema=True,
        )
        self.receta_cena = Receta.objects.create(
            nombre="Cena de prueba",
            creado_por=self.nutricionista,
            es_sistema=True,
        )

    def test_plan_get_empty_initially(self):
        """Verify that initially GET to plan returns success but no plan active if not created."""
        url = reverse("pacientes:plan_get", kwargs={"pk": self.paciente.pk})
        response = self.client.get(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIsNone(data["plan"])

    def test_plan_guardar_crear_y_actualizar(self):
        """Verify saving creates a plan and then updates its sections."""
        url_guardar = reverse("pacientes:plan_guardar", kwargs={"pk": self.paciente.pk})
        
        # 1. Create a plan with initial section "resumen"
        response = self.client.post(
            url_guardar,
            data={
                "section": "resumen",
                "nombre": "Plan de Definicion",
                "tipo_plan": "Definición Muscular",
                "estado": "Borrador",
                "fecha_inicio": "2026-06-25"
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        plan_id = data["plan_id"]
        
        # Verify it exists in db
        plan = PlanAlimentario.objects.get(pk=plan_id)
        self.assertEqual(plan.nombre, "Plan de Definicion")
        self.assertEqual(plan.tipo_plan, "Definición Muscular")
        self.assertEqual(plan.estado, "Borrador")

        # 2. Update "prescripcion" section
        response = self.client.post(
            url_guardar,
            data={
                "plan_id": plan_id,
                "section": "prescripcion",
                "calorias": "2200",
                "agua_recomendada": "3.0",
                "proteinas": "150",
                "carbohidratos": "250",
                "grasas": "66",
                "fibra": "30"
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(response.status_code, 200)
        plan.refresh_from_db()
        self.assertEqual(plan.calorias, 2200)
        self.assertEqual(plan.proteinas, 150)
        self.assertEqual(plan.carbohidratos, 250)
        self.assertEqual(plan.grasas, 66)

        # 3. Update "comidas" section
        response = self.client.post(
            url_guardar,
            data={
                "plan_id": plan_id,
                "section": "comidas",
                "comida_tipo": ["Desayuno", "Cena"],
                "comida_hora": ["08:00", "21:00"],
                "comida_receta_id": [
                    str(self.receta_desayuno.pk),
                    str(self.receta_cena.pk),
                ],
                "comida_observaciones": ["Sin yema", "Pechuga"]
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(response.status_code, 200)
        plan.refresh_from_db()
        self.assertEqual(len(plan.comidas), 2)
        self.assertEqual(plan.comidas[0]["tipo"], "Desayuno")
        self.assertEqual(
            plan.comidas[1]["receta_id"],
            str(self.receta_cena.pk),
        )

    def test_plan_nueva_version(self):
        """Verify creating a new version copies plan and keeps older version in history."""
        # Create active plan first
        plan = PlanAlimentario.objects.create(
            paciente=self.paciente,
            nombre="Plan v1",
            tipo_plan="Hipertrofia",
            estado="Activo",
            calorias=2000,
            proteinas=120,
            carbohidratos=200,
            grasas=50
        )

        url_nueva_version = reverse("pacientes:plan_nueva_version", kwargs={"pk": self.paciente.pk})
        response = self.client.post(
            url_nueva_version,
            data={"plan_id": plan.pk},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        new_plan_id = data["plan_id"]
        
        # Verifica el cambio de plan activo.
        new_plan = PlanAlimentario.objects.get(pk=new_plan_id)
        plan.refresh_from_db()
        
        self.assertEqual(new_plan.nombre, "Plan v1 (v2)")
        self.assertEqual(new_plan.tipo_plan, "Hipertrofia")
        self.assertEqual(new_plan.estado, "Borrador")
        self.assertEqual(new_plan.calorias, 2000)

    def test_plan_duplicar(self):
        """Verify duplicating a plan."""
        plan = PlanAlimentario.objects.create(
            paciente=self.paciente,
            nombre="Plan Original",
            tipo_plan="Vegetariano",
            estado="Borrador",
            calorias=1800
        )
        url_duplicar = reverse("pacientes:plan_duplicar", kwargs={"pk": self.paciente.pk})
        response = self.client.post(
            url_duplicar,
            data={"plan_id": plan.pk},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        
        dup_plan = PlanAlimentario.objects.get(pk=data["plan_id"])
        self.assertEqual(dup_plan.nombre, "Plan Original (Copia)")
        self.assertEqual(dup_plan.tipo_plan, "Vegetariano")
        self.assertEqual(dup_plan.calorias, 1800)

    def test_plan_eliminar(self):
        """Verify version deletion."""
        plan = PlanAlimentario.objects.create(
            paciente=self.paciente,
            nombre="Plan Temporal",
            estado="Borrador"
        )
        url_eliminar = reverse("pacientes:plan_eliminar", kwargs={"pk": self.paciente.pk})
        response = self.client.post(
            url_eliminar,
            data={"plan_id": plan.pk},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertFalse(PlanAlimentario.objects.filter(pk=plan.pk).exists())

    def test_plan_imprimir_view(self):
        """Verify printer-friendly view renders successfully."""
        plan = PlanAlimentario.objects.create(
            paciente=self.paciente,
            nombre="Plan Imprimible",
            estado="Activo",
            calorias=2200,
            comidas=[{"tipo": "Desayuno", "alimentos": "Avena", "cantidad": "100", "unidad": "g", "hora": "08:00"}]
        )
        url = reverse("pacientes:plan_imprimir", kwargs={"pk": self.paciente.pk, "plan_id": plan.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pacientes/plan_imprimir.html")
        self.assertContains(response, "Plan Imprimible")
        self.assertContains(response, "Avena")

    def test_plan_enviar(self):
        """Verify that sending a plan updates its enviado_al_paciente status."""
        plan = PlanAlimentario.objects.create(
            paciente=self.paciente,
            nombre="Plan Para Enviar",
            estado="Activo",
            comidas=[
                {
                    "tipo": "Desayuno",
                    "alimentos": "Avena con fruta",
                    "hora": "08:00",
                }
            ],
        )
        url_enviar = reverse("pacientes:plan_enviar", kwargs={"pk": self.paciente.pk})
        response = self.client.post(
            url_enviar,
            data={"plan_id": plan.pk},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["message"], "Plan enviado correctamente a la app del paciente")
        
        # Reload from db
        plan.refresh_from_db()
        self.assertTrue(plan.enviado_al_paciente)
        self.assertIsNotNone(plan.fecha_envio)
