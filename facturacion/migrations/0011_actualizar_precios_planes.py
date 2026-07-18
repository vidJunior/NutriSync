# facturacion/migrations/0011_actualizar_precios_planes.py
# Migración de datos: actualiza los precios del Plan Básico (59.99) y Plan Profesional (99.99).

from django.db import migrations


def forwards(apps, schema_editor):
    PlanSuscripcion = apps.get_model("facturacion", "PlanSuscripcion")
    
    # Actualizar Plan Básico
    try:
        basico = PlanSuscripcion.objects.get(nombre="Básico")
        basico.precio_mensual = "59.99"
        basico.precio_anual = "599.90"
        basico.save()
    except PlanSuscripcion.DoesNotExist:
        pass
        
    # Actualizar Plan Profesional
    try:
        profesional = PlanSuscripcion.objects.get(nombre="Profesional")
        profesional.precio_mensual = "99.99"
        profesional.precio_anual = "999.90"
        profesional.save()
    except PlanSuscripcion.DoesNotExist:
        pass


def backwards(apps, schema_editor):
    PlanSuscripcion = apps.get_model("facturacion", "PlanSuscripcion")
    
    # Revertir Plan Básico a precios antiguos
    try:
        basico = PlanSuscripcion.objects.get(nombre="Básico")
        basico.precio_mensual = "99.00"
        basico.precio_anual = "990.00"
        basico.save()
    except PlanSuscripcion.DoesNotExist:
        pass
        
    # Revertir Plan Profesional a precios antiguos
    try:
        profesional = PlanSuscripcion.objects.get(nombre="Profesional")
        profesional.precio_mensual = "199.00"
        profesional.precio_anual = "1990.00"
        profesional.save()
    except PlanSuscripcion.DoesNotExist:
        pass


class Migration(migrations.Migration):

    dependencies = [
        ("facturacion", "0010_eliminar_plan_enterprise"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
