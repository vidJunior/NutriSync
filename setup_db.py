# Script de inicialización para crear el superusuario y cargar 15 alimentos base
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth import get_user_model
from alimentos.models import Alimento
from nutricion.models import Logro


User = get_user_model()
# Crea automáticamente un administrador (admin/admin) si no existe
u, created = User.objects.get_or_create(
    username="admin",
    defaults={"email": "admin@admin.com", "is_staff": True, "is_superuser": True},
)
u.set_password("admin")
u.save()
if created:
    print("Superuser 'admin' creado con éxito.")
else:
    print("Contraseña del superusuario actualizada a 'admin'.")

# Lista de alimentos iniciales requeridos por el plan de desarrollo
alimentos_data = [
    ("Arroz blanco cocido", "Genérico", 130.0, 2.7, 28.2, 0.3, 0.4, True),
    ("Pollo a la brasa (pechuga)", "Genérico", 195.0, 29.5, 0.0, 7.7, 0.0, True),
    ("Lomo saltado", "Genérico", 150.0, 15.0, 8.0, 7.0, 1.5, True),
    ("Papa amarilla cocida", "Genérico", 100.0, 2.0, 23.0, 0.1, 2.0, True),
    ("Ceviche de pescado", "Genérico", 120.0, 18.0, 5.0, 3.0, 0.5, True),
    ("Quinua cocida", "Genérico", 120.0, 4.4, 21.3, 1.9, 2.8, True),
    ("Ají de gallina", "Genérico", 180.0, 12.0, 10.0, 11.0, 1.0, True),
    ("Causa limeña", "Genérico", 160.0, 5.0, 22.0, 6.0, 1.5, True),
    ("Leche evaporada", "Gloria", 134.0, 6.8, 10.0, 7.5, 0.0, True),
    ("Pan francés", "Genérico", 280.0, 8.5, 55.0, 2.0, 2.5, True),
    ("Plátano de isla", "Genérico", 89.0, 1.1, 22.8, 0.3, 2.6, True),
    ("Huevo cocido", "Genérico", 155.0, 13.0, 1.1, 11.0, 0.0, False),
    ("Avena cocida", "Quaker", 68.0, 2.5, 12.0, 1.4, 1.7, False),
    ("Atún en conserva", "Florida", 116.0, 25.5, 0.0, 0.8, 0.0, False),
    ("Palta (aguacate)", "Genérico", 160.0, 2.0, 8.5, 14.7, 6.7, True),
]

for item in alimentos_data:
    Alimento.objects.get_or_create(
        nombre=item[0],
        defaults={
            "marca": item[1],
            "calorias_100g": item[2],
            "proteinas_100g": item[3],
            "carbohidratos_100g": item[4],
            "grasas_100g": item[5],
            "fibra_100g": item[6],
            "es_peruano": item[7],
        },
    )
print("15 alimentos cargados en PostgreSQL.")

# Crear logros base
logros_data = [
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

logros_creados = 0
for data in logros_data:
    obj, created = Logro.objects.get_or_create(nombre=data["nombre"], defaults=data)
    if created:
        logros_creados += 1
print(f"{logros_creados} logros creados en PostgreSQL.")
