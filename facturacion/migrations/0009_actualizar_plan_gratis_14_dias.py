# facturacion/migrations/0009_actualizar_plan_gratis_14_dias.py
# Migración de datos: actualiza la descripción del plan Prueba Gratis a 14 días.

from django.db import migrations


def forwards(apps, schema_editor):
    PlanSuscripcion = apps.get_model("facturacion", "PlanSuscripcion")
    try:
        plan = PlanSuscripcion.objects.get(nombre="Prueba Gratis")
        plan.descripcion = "Acceso total a NutriSync gratis por 14 días. Requiere tarjeta de crédito o Yape. Cancela en cualquier momento."
        plan.save()
    except PlanSuscripcion.DoesNotExist:
        pass


def backwards(apps, schema_editor):
    PlanSuscripcion = apps.get_model("facturacion", "PlanSuscripcion")
    try:
        plan = PlanSuscripcion.objects.get(nombre="Prueba Gratis")
        plan.descripcion = "Acceso total a NutriSync gratis por 7 días. Requiere tarjeta de crédito. Cancela en cualquier momento."
        plan.save()
    except PlanSuscripcion.DoesNotExist:
        pass


class Migration(migrations.Migration):

    dependencies = [
        ("facturacion", "0007_alter_cobro_cita_alter_cobro_metodo_pago_usado_and_more"),
        ("facturacion", "0008_actualizar_descripcion_enterprise"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
