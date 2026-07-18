from datetime import date, datetime, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone

from agendas.models import Cita
from core.models import PerfilNutricionista
from pacientes.models import Paciente, Consulta, PlanAlimentario
from seguimiento.models import MedidaCorporal, NotaClinica, Recomendacion
from nutricion.models import PlanNutricional
from config.choices import Sexo, TipoCita, EstadoCita, TipoNota

class Command(BaseCommand):
    help = 'Inserta 5 casos de ejemplo completos para NutriSync con pacientes, citas, seguimiento y planes.'

    def handle(self, *args, **options):
        # 1. Creación del usuario y asignación de contraseña fija
        nutricionista_user, created_user = User.objects.get_or_create(
            username='demo_nutricionista',
            defaults={'first_name': 'Dra. Ana', 'last_name': 'Mendoza', 'email': 'ana@example.com'}
        )
        
        # Siempre nos aseguramos de que tenga esta contraseña para poder iniciar sesión
        nutricionista_user.set_password('Password123!')
        nutricionista_user.save()

        if not hasattr(nutricionista_user, 'perfil'):
            PerfilNutricionista.objects.get_or_create(
                usuario=nutricionista_user,
                defaults={
                    'nombre_completo': 'Dra. Ana Mendoza',
                    'especialidad': 'Nutrición clínica',
                    'telefono': '999888777',
                    'email_profesional': 'ana@nutrisync.test',
                    'numero_colegiatura': 'COL-1001',
                    'dni': '40111222',
                    'ruc': '20123456789',
                    'direccion_consultorio': 'Av. Los Álamos 123',
                    'estado': 'habilitado',
                    'rol': 'nutricionista',
                }
            )

        plan_modelo, _ = PlanNutricional.objects.get_or_create(
            nombre='Plan de pérdida de peso general',
            defaults={
                'nutricionista': nutricionista_user,
                'descripcion': 'Modelo base para pacientes con sobrepeso',
                'objetivo': 'perdida_peso',
                'tipo_paciente': 'Adulto sedentario',
                'calorias_diarias': 1800,
                'proteinas_g': Decimal('120.0'),
                'carbohidratos_g': Decimal('180.0'),
                'grasas_g': Decimal('60.0'),
                'fibra_g': 30,
                'agua_recomendada': Decimal('2.5'),
                'num_comidas': 4,
                'estado': 'Activo',
            },
        )

        casos = [
            {
                'nombre': 'María', 'apellido': 'Rojas', 'dni': '70123456', 'fecha_nacimiento': date(1988, 4, 14),
                'sexo': Sexo.FEMENINO, 'ocupacion': 'Docente', 'peso': Decimal('72.50'), 'talla': Decimal('160.0'),
                'telefono': '987654321', 'email': 'maria@example.com', 'direccion': 'Jr. San Martín 456',
                'condiciones_medicas': 'Hipertensión leve', 'alergias': 'Maní', 'notas_generales': 'Motivo de Consulta: Pérdida de peso\nObservaciones Iniciales:\nLe cuesta controlar los antojos por la tarde.',
                'informacion_clinica': {'objetivo_principal': 'Pérdida de peso', 'habitos': 'Sedentarismo', 'meta': 'Bajar 6 kg'},
                'evaluacion': {'objetivo_principal': 'Pérdida de peso', 'estado': 'Sobrepeso'},
                'seguimiento': {'fase': 'Inicial', 'frecuencia': 'Semanal'},
                'cita_fecha': timezone.now() + timedelta(days=2), 'cita_motivo': 'Primera evaluación nutricional', 'cita_tipo': TipoCita.PRIMERA_CONSULTA,
                'cita_estado': EstadoCita.PROGRAMADA, 'consulta_numero': 1, 'consulta_tipo': 'primera_consulta', 'consulta_observaciones': 'Paciente motivada, requiere plan de 1,800 kcal.',
                'plan_nombre': 'Plan inicial para pérdida de peso', 'plan_tipo': 'Pérdida de peso', 'plan_calorias': 1800, 'plan_proteinas': 120, 'plan_carbohidratos': 180, 'plan_grasas': 60,
                'medida_fecha': date.today() - timedelta(days=5), 'medida_peso': Decimal('72.5'), 'medida_talla': Decimal('160.0'), 'medida_grasa': Decimal('32.0'), 'medida_cintura': Decimal('87.0'), 'medida_cadera': Decimal('98.0'),
                'nota_titulo': 'Primera sesión', 'nota_resumen': 'Se estableció objetivo de pérdida de 0.5 kg por semana.', 'nota_plan': 'Priorizar desayuno y meriendas con proteína.', 'nota_tipo': TipoNota.CONSULTA,
                'reco_categoria': 'alimentacion', 'reco_descripcion': {'mensaje': 'Aumentar consumo de verduras', 'detalle': 'Incluir 2 porciones diarias'}, 'reco_estado': 'pendiente',
                'adherencia': 'Buena'
            },
            {
                'nombre': 'Carlos', 'apellido': 'Vega', 'dni': '71234567', 'fecha_nacimiento': date(1992, 8, 21),
                'sexo': Sexo.MASCULINO, 'ocupacion': 'Ingeniero', 'peso': Decimal('88.00'), 'talla': Decimal('176.0'),
                'telefono': '912345678', 'email': 'carlos@example.com', 'direccion': 'Av. Brasil 789',
                'condiciones_medicas': 'Sin antecedentes relevantes', 'alergias': 'Ninguna', 'notas_generales': 'Motivo de Consulta: Ganancia muscular\nObservaciones Iniciales:\nQuiere aumentar masa muscular sin subir mucho grasa.',
                'informacion_clinica': {'objetivo_principal': 'Ganancia muscular', 'habitos': 'Entrena 4 veces por semana', 'meta': 'Subir 4 kg de masa muscular'},
                'evaluacion': {'objetivo_principal': 'Ganancia muscular', 'estado': 'Eutrófico'},
                'seguimiento': {'fase': 'Intermedio', 'frecuencia': 'Quincenal'},
                'cita_fecha': timezone.now() + timedelta(days=5), 'cita_motivo': 'Seguimiento de plan de hipertrofia', 'cita_tipo': TipoCita.SEGUIMIENTO,
                'cita_estado': EstadoCita.PROGRAMADA, 'consulta_numero': 2, 'consulta_tipo': 'seguimiento', 'consulta_observaciones': 'Se ajusta proteína y calorías.',
                'plan_nombre': 'Plan de ganancia muscular', 'plan_tipo': 'Ganancia muscular', 'plan_calorias': 2600, 'plan_proteinas': 180, 'plan_carbohidratos': 300, 'plan_grasas': 80,
                'medida_fecha': date.today() - timedelta(days=2), 'medida_peso': Decimal('88.0'), 'medida_talla': Decimal('176.0'), 'medida_grasa': Decimal('18.5'), 'medida_cintura': Decimal('91.0'), 'medida_cadera': Decimal('102.0'),
                'nota_titulo': 'Seguimiento de hipertrofia', 'nota_resumen': 'El paciente ha aumentado 1 kg de peso en 2 semanas.', 'nota_plan': 'Mantener 5 comidas diarias y suplementación post-entreno.', 'nota_tipo': TipoNota.SEGUIMIENTO,
                'reco_categoria': 'actividad_fisica', 'reco_descripcion': {'mensaje': 'Agregar 2 sesiones de movilidad', 'detalle': '10 minutos post-entreno'}, 'reco_estado': 'cumplida',
                'adherencia': 'Excelente'
            },
            {
                'nombre': 'Lucía', 'apellido': 'Pérez', 'dni': '72345678', 'fecha_nacimiento': date(1995, 1, 10),
                'sexo': Sexo.FEMENINO, 'ocupacion': 'Enfermera', 'peso': Decimal('61.20'), 'talla': Decimal('168.0'),
                'telefono': '923456789', 'email': 'lucia@example.com', 'direccion': 'Calle Los Olivos 321',
                'condiciones_medicas': 'Tiroides', 'alergias': 'Lácteos', 'notas_generales': 'Motivo de Consulta: Mantenimiento\nObservaciones Iniciales:\nQuiere mantener peso y mejorar hábitos.',
                'informacion_clinica': {'objetivo_principal': 'Mantenimiento', 'habitos': 'Alimentación irregular', 'meta': 'Mantener peso actual'},
                'evaluacion': {'objetivo_principal': 'Mantenimiento', 'estado': 'Normal'},
                'seguimiento': {'fase': 'Mantenimiento', 'frecuencia': 'Mensual'},
                'cita_fecha': timezone.now() + timedelta(days=8), 'cita_motivo': 'Control mensual', 'cita_tipo': TipoCita.CONTROL,
                'cita_estado': EstadoCita.PROGRAMADA, 'consulta_numero': 3, 'consulta_tipo': 'control', 'consulta_observaciones': 'Se mejora adherencia y se revisa seguimiento.',
                'plan_nombre': 'Plan de mantenimiento', 'plan_tipo': 'Mantenimiento', 'plan_calorias': 2000, 'plan_proteinas': 140, 'plan_carbohidratos': 220, 'plan_grasas': 65,
                'medida_fecha': date.today() - timedelta(days=10), 'medida_peso': Decimal('61.2'), 'medida_talla': Decimal('168.0'), 'medida_grasa': Decimal('24.5'), 'medida_cintura': Decimal('70.0'), 'medida_cadera': Decimal('95.0'),
                'nota_titulo': 'Control mensual', 'nota_resumen': 'Se mantiene el peso actual y se reevalúa la rutina.', 'nota_plan': 'Agregar una comida proteica adicional.', 'nota_tipo': TipoNota.SEGUIMIENTO,
                'reco_categoria': 'hidratacion', 'reco_descripcion': {'mensaje': 'Consumir 2.5 L de agua', 'detalle': 'Distribuir a lo largo del día'}, 'reco_estado': 'parcial',
                'adherencia': 'Regular'
            },
            {
                'nombre': 'Diego', 'apellido': 'Salazar', 'dni': '73456789', 'fecha_nacimiento': date(1980, 11, 5),
                'sexo': Sexo.MASCULINO, 'ocupacion': 'Chofer', 'peso': Decimal('95.50'), 'talla': Decimal('174.0'),
                'telefono': '934567890', 'email': 'diego@example.com', 'direccion': 'Pasaje Las Flores 102',
                'condiciones_medicas': 'Diabetes tipo 2', 'alergias': 'Gluten', 'notas_generales': 'Motivo de Consulta: Salud general\nObservaciones Iniciales:\nNecesita controlar glucosa y evitar sobrecarga de carbohidratos.',
                'informacion_clinica': {'objetivo_principal': 'Salud general', 'habitos': 'Consumo frecuente de snacks', 'meta': 'Mejorar control glucémico'},
                'evaluacion': {'objetivo_principal': 'Salud general', 'estado': 'Riesgo metabólico'},
                'seguimiento': {'fase': 'Inicial', 'frecuencia': 'Semanal'},
                'cita_fecha': timezone.now() + timedelta(days=10), 'cita_motivo': 'Consulta clínica por control metabólico', 'cita_tipo': TipoCita.CONTROL,
                'cita_estado': EstadoCita.PROGRAMADA, 'consulta_numero': 4, 'consulta_tipo': 'clinica', 'consulta_observaciones': 'Se prioriza alimentación con bajo índice glucémico.',
                'plan_nombre': 'Plan para control glicémico', 'plan_tipo': 'Salud general', 'plan_calorias': 2100, 'plan_proteinas': 150, 'plan_carbohidratos': 220, 'plan_grasas': 70,
                'medida_fecha': date.today() - timedelta(days=7), 'medida_peso': Decimal('95.5'), 'medida_talla': Decimal('174.0'), 'medida_grasa': Decimal('29.0'), 'medida_cintura': Decimal('103.0'), 'medida_cadera': Decimal('106.0'),
                'nota_titulo': 'Control metabólico', 'nota_resumen': 'Se ajustó la distribución de carbohidratos.', 'nota_plan': 'Reemplazar snacks por fruta y nueces.', 'nota_tipo': TipoNota.CONSULTA,
                'reco_categoria': 'alimentos_limitar', 'reco_descripcion': {'mensaje': 'Reducir consumo de pan y azúcar', 'detalle': 'Evitar más de 2 porciones diarias'}, 'reco_estado': 'pendiente',
                'adherencia': 'Buena'
            },
            {
                'nombre': 'Sofía', 'apellido': 'Torres', 'dni': '74567890', 'fecha_nacimiento': date(1998, 6, 30),
                'sexo': Sexo.FEMENINO, 'ocupacion': 'Estudiante', 'peso': Decimal('57.80'), 'talla': Decimal('162.0'),
                'telefono': '945678901', 'email': 'sofia@example.com', 'direccion': 'Av. Central 555',
                'condiciones_medicas': 'Sin patologías', 'alergias': 'Mariscos', 'notas_generales': 'Motivo de Consulta: Pérdida de peso\nObservaciones Iniciales:\nBusca mejorar energía y hábitos alimentarios.',
                'informacion_clinica': {'objetivo_principal': 'Pérdida de peso', 'habitos': 'Desayunos muy ligeros', 'meta': 'Perder 3 kg'},
                'evaluacion': {'objetivo_principal': 'Pérdida de peso', 'estado': 'Leve sobrepeso'},
                'seguimiento': {'fase': 'Inicial', 'frecuencia': 'Quincenal'},
                'cita_fecha': timezone.now() + timedelta(days=12), 'cita_motivo': 'Reevaluación', 'cita_tipo': TipoCita.SEGUIMIENTO,
                'cita_estado': EstadoCita.PROGRAMADA, 'consulta_numero': 5, 'consulta_tipo': 'reevaluacion', 'consulta_observaciones': 'Se reevalúa adherencia y se coloca plan más completo.',
                'plan_nombre': 'Plan para mejorar energía', 'plan_tipo': 'Pérdida de peso', 'plan_calorias': 1750, 'plan_proteinas': 125, 'plan_carbohidratos': 170, 'plan_grasas': 55,
                'medida_fecha': date.today() - timedelta(days=3), 'medida_peso': Decimal('57.8'), 'medida_talla': Decimal('162.0'), 'medida_grasa': Decimal('26.0'), 'medida_cintura': Decimal('72.0'), 'medida_cadera': Decimal('96.0'),
                'nota_titulo': 'Reevaluación inicial', 'nota_resumen': 'Se incorpora desayuno completo y más proteínas.', 'nota_plan': 'Evitar omitir comidas.', 'nota_tipo': TipoNota.OBSERVACION,
                'reco_categoria': 'generales', 'reco_descripcion': {'mensaje': 'Dormir 8 horas diarias', 'detalle': 'Priorizar la rutina nocturna'}, 'reco_estado': 'cumplida',
                'adherencia': 'Excelente'
            },
        ]

        created_count = 0
        for data in casos:
            paciente, created = Paciente.objects.get_or_create(
                nutricionista=nutricionista_user,
                dni=data['dni'],
                defaults={
                    'nombre': data['nombre'],
                    'apellido': data['apellido'],
                    'fecha_nacimiento': data['fecha_nacimiento'],
                    'sexo': data['sexo'],
                    'ocupacion': data['ocupacion'],
                    'peso': data['peso'],
                    'talla': data['talla'],
                    'telefono': data['telefono'],
                    'email': data['email'],
                    'direccion': data['direccion'],
                    'condiciones_medicas': data['condiciones_medicas'],
                    'alergias': data['alergias'],
                    'notas_generales': data['notas_generales'],
                    'informacion_clinica': data['informacion_clinica'],
                    'evaluacion': data['evaluacion'],
                    'seguimiento': data['seguimiento'],
                },
            )
            if created:
                created_count += 1

            cita, _ = Cita.objects.get_or_create(
                paciente=paciente,
                nutricionista=nutricionista_user,
                fecha_hora=data['cita_fecha'],
                defaults={
                    'duracion_minutos': 45,
                    'tipo': data['cita_tipo'],
                    'estado': data['cita_estado'],
                    'motivo': data['cita_motivo'],
                    'costo': Decimal('80.00'),
                },
            )

            consulta, _ = Consulta.objects.get_or_create(
                paciente=paciente,
                numero_consulta=data['consulta_numero'],
                defaults={
                    'tipo': data['consulta_tipo'],
                    'fecha': date.today() - timedelta(days=2),
                    'hora_inicio': '09:00:00',
                    'hora_fin': '09:45:00',
                    'estado': 'finalizada',
                    'profesional': nutricionista_user,
                    'cita': cita,
                    'observaciones': data['consulta_observaciones'],
                    'informacion_clinica': data['informacion_clinica'],
                    'evaluacion': data['evaluacion'],
                    'seguimiento': data['seguimiento'],
                },
            )

            plan_alimentario, _ = PlanAlimentario.objects.get_or_create(
                paciente=paciente,
                nombre=data['plan_nombre'],
                defaults={
                    'consulta': consulta,
                    'tipo_plan': data['plan_tipo'],
                    'calorias': data['plan_calorias'],
                    'proteinas': data['plan_proteinas'],
                    'carbohidratos': data['plan_carbohidratos'],
                    'grasas': data['plan_grasas'],
                    'fibra': 30,
                    'agua_recomendada': Decimal('2.5'),
                    'estado': 'Activo',
                    'comidas': [
                        {'tipo': 'Desayuno', 'detalle': 'Avena + fruta'},
                        {'tipo': 'Almuerzo', 'detalle': 'Proteína + verdura'},
                        {'tipo': 'Cena', 'detalle': 'Ensalada proteica'}
                    ],
                },
            )

            MedidaCorporal.objects.get_or_create(
                paciente=paciente,
                fecha=data['medida_fecha'],
                defaults={
                    'consulta': consulta,
                    'peso_kg': data['medida_peso'],
                    'talla_cm': data['medida_talla'],
                    'grasa_corporal_pct': data['medida_grasa'],
                    'cintura_cm': data['medida_cintura'],
                    'cadera_cm': data['medida_cadera'],
                    'peso_objetivo_kg': data['medida_peso'] - Decimal('4.0'),
                    'notas': 'Registro inicial del seguimiento.',
                },
            )

            # 2. Ajuste de NotaClinica: motivo_consulta, observaciones, adherencia_plan
            NotaClinica.objects.get_or_create(
                paciente=paciente,
                fecha=data['medida_fecha'],
                defaults={
                    'consulta': consulta,
                    'cita': cita,
                    'titulo': data['nota_titulo'],
                    'motivo_consulta': data['notas_generales'],
                    'resumen_consulta': data['nota_resumen'],
                    'objetivos_acordados': 'Mejorar adherencia general',
                    'plan_accion': data['nota_plan'],
                    'observaciones_clinicas': 'Paciente comprometido durante la sesión', # Reemplaza a observaciones_clinicas
                    'adherencia_plan': 6, # Nuevo campo añadido
                    'tipo': data['nota_tipo'],
                },
            )

            Recomendacion.objects.get_or_create(
                paciente=paciente,
                cita=cita,
                defaults={
                    'consulta': consulta,
                    'nutricionista': nutricionista_user,
                    'categoria': data['reco_categoria'],
                    'descripcion': data['reco_descripcion'],
                    'fecha': date.today(),
                    'estado_cumplimiento': data['reco_estado'],
                },
            )

        self.stdout.write(self.style.SUCCESS(f'Se crearon/actualizaron {created_count} pacientes nuevos y se cargó el demo completo.'))
        self.stdout.write(self.style.SUCCESS(f"✅ Nutricionista listo! | Usuario: demo_nutricionista | Clave: Password123!"))