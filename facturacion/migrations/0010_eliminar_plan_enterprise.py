# facturacion/migrations/0010_eliminar_plan_enterprise.py
# Migración de datos: elimina de forma definitiva el plan Enterprise de la base de datos.

from django.db import migrations


def forwards(apps, schema_editor):
    PlanSuscripcion = apps.get_model("facturacion", "PlanSuscripcion")
    PlanSuscripcion.objects.filter(nombre="Enterprise").delete()


def backwards(apps, schema_editor):
    PlanSuscripcion = apps.get_model("facturacion", "PlanSuscripcion")
    PlanSuscripcion.objects.get_or_create(
        nombre="Enterprise",
        defaults={
            "descripcion": "Sin límites. Para nutricionistas que necesitan todo el poder de NutriSync.",
            "precio_mensual": "399.00",
            "precio_anual": "3990.00",
            "limite_pacientes": -1,
            "limite_citas_mes": -1,
            "comision_cobros": "1.00",
            "comision_suscripcion": "0.00",
            "activo": True,
        },
    )


class Migration(migrations.Migration):

    dependencies = [
        ("facturacion", "0009_actualizar_plan_gratis_14_dias"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
