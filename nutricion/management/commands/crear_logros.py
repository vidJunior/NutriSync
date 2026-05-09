from django.core.management.base import BaseCommand
from nutricion.models import Logro


class Command(BaseCommand):
    help = "Crea los logros base del sistema"

    def handle(self, *args, **options):
        logros = [
            {
                "nombre": "Bebedor de agua",
                "descripcion": "Registra 8 o más vasos de agua en un día",
                "tipo": "agua",
                "icono": "💧",
                "condicion": {"min_vasos_agua": 8},
            },
            {
                "nombre": "Caminante",
                "descripcion": "Alcanza 10,000 pasos en un día",
                "tipo": "pasos",
                "icono": "🚶",
                "condicion": {"min_pasos": 10000},
            },
            {
                "nombre": "Deportista",
                "descripcion": "Hace 30 minutos o más de ejercicio en un día",
                "tipo": "ejercicio",
                "icono": "🏋️",
                "condicion": {"min_minutos": 30},
            },
            {
                "nombre": "Duerme bien",
                "descripcion": "Registra 7 horas o más de sueño en un día",
                "tipo": "sueno",
                "icono": "😴",
                "condicion": {"min_horas_sueno": 7},
            },
            {
                "nombre": "Comilón",
                "descripcion": "Alcanza 2000 calorías en un día",
                "tipo": "calorias",
                "icono": "🍽️",
                "condicion": {"min_calorias": 2000},
            },
            {
                "nombre": "Variedad",
                "descripcion": "Registra 3 comidas distintas en un día",
                "tipo": "comidas",
                "icono": "📋",
                "condicion": {"min_comidas": 3},
            },
        ]

        creados = 0
        for data in logros:
            obj, created = Logro.objects.get_or_create(
                nombre=data["nombre"], defaults=data
            )
            if created:
                creados += 1
                self.stdout.write(self.style.SUCCESS(f"  ✓ {data['nombre']}"))
            else:
                self.stdout.write(f"  - {data['nombre']} (ya existe)")

        self.stdout.write(self.style.SUCCESS(f"\n{creados} logros creados exitosamente."))
