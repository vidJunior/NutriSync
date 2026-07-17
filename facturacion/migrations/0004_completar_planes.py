# facturacion/migrations/0004_completar_planes.py
# Migración de datos: completa el plan Enterprise que falló en 0002.

from django.db import migrations


def forwards(apps, schema_editor):
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


def backwards(apps, schema_editor):
    PlanSuscripcion = apps.get_model("facturacion", "PlanSuscripcion")
    PlanSuscripcion.objects.filter(nombre="Enterprise").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("facturacion", "0003_alter_plan_limite"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
