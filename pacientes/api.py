# pacientes/api.py
from typing import List, Dict, Any, Optional
from django.utils import timezone
from django.core import signing
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction
from ninja import Router, Schema
from ninja.security import HttpBearer
from ninja.errors import HttpError
from django.core.cache import cache
from pacientes.models import Paciente, CodigoVinculacion, PlanAlimentario
from citas.models import Cita
from seguimiento.models import MedidaCorporal, NotaClinica

router = Router()

def obtener_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '').strip()

# ─── Seguridad y Autenticación con Token Firmado ─────────────────────────────

class PacienteAuth(HttpBearer):
    def authenticate(self, request, token):
        try:
            # Descifrar y validar el token firmado (vigente por 30 días)
            data = signing.loads(token, max_age=60*60*24*30)
            user_id = data.get("user_id")
            user = User.objects.get(pk=user_id)
            return user
        except (signing.SignatureExpired, signing.BadSignature, User.DoesNotExist):
            return None

auth_paciente = PacienteAuth()

# ─── Esquemas de Pydantic (Request / Response) ───────────────────────────────

class RegistroPacienteSchema(Schema):
    dni: str
    codigo_vinculacion: str
    username: str
    email: str
    password: str

class LoginSchema(Schema):
    username: str
    password: str

class TokenSchema(Schema):
    token: str
    nombre_paciente: str
    email: str

class PacientePerfilSchema(Schema):
    id: int
    nombre: str
    apellido: str
    dni: str
    edad: Optional[int]
    peso: float
    talla: Optional[float]
    imc_inicial: Optional[float]
    imc_clasificacion: Optional[str]
    email: str
    telefono: str
    condiciones_medicas: str
    alergias: str
    avatar_color: Optional[str] = None
    foto_url: Optional[str] = None

class PerfilUpdateSchema(Schema):
    nombre: str
    apellido: str
    telefono: str
    email: str
    avatar_color: Optional[str] = None
    foto_url: Optional[str] = None

class PlanAlimentarioSchema(Schema):
    id: int
    nombre: str
    tipo_plan: str
    calorias: int
    proteinas: int
    carbohidratos: int
    grasas: int
    fibra: int
    agua_recomendada: float
    estado: str
    comidas: List[Dict[str, Any]]
    sustituciones: List[Dict[str, Any]]
    recomendaciones: List[Dict[str, Any]]
    suplementacion: List[Dict[str, Any]]

class MedidaCorporalSchema(Schema):
    id: int
    fecha: str
    peso_kg: float
    talla_cm: float
    imc: float
    grasa_corporal_pct: Optional[float]
    cintura_cm: Optional[float]
    cadera_cm: Optional[float]
    masa_muscular_kg: Optional[float]
    agua_corporal_pct: Optional[float]
    tmb: Optional[int]
    notas: str

class CitaSchema(Schema):
    id: int
    fecha_hora: str
    duracion_minutos: int
    tipo: str
    estado: str
    motivo: str
    nombre_nutricionista: str

class NotaClinicaSchema(Schema):
    id: int
    fecha: str
    titulo: str
    contenido: str
    tipo: str


# ─── Endpoints de Autenticación y Registro ───────────────────────────────────

@router.post("/auth/register-vinculado", response={200: TokenSchema})
def registrar_paciente_vinculado(request, data: RegistroPacienteSchema):
    """
    Registra una cuenta de usuario Django vinculada a un expediente de paciente
    mediante el DNI y el código de vinculación otorgado por el nutricionista.
    """
    ip = obtener_client_ip(request)
    limite_clave = f"rl_vinculo_{ip}"
    intentos = cache.get(limite_clave, 0)
    
    if intentos >= 5:
        raise HttpError(429, "Demasiados intentos de vinculación fallidos. Intente de nuevo en 5 minutos.")

    error_generico = "El DNI o el código de vinculación proporcionados no son válidos."

    try:
        # 1. Buscar candidatos por DNI
        pacientes_candidatos = Paciente.objects.filter(dni=data.dni, estado=True)
        if not pacientes_candidatos.exists():
            raise Paciente.DoesNotExist

        paciente = None
        for cand in pacientes_candidatos:
            try:
                vinculo = CodigoVinculacion.objects.get(paciente=cand)
                # Validar código y vigencia, y que el correo coincida
                if vinculo.esta_valido() and vinculo.codigo == data.codigo_vinculacion.strip().upper():
                    if cand.email and cand.email.strip().lower() == data.email.strip().lower():
                        paciente = cand
                        break
            except CodigoVinculacion.DoesNotExist:
                continue

        if paciente is None:
            cache.set(limite_clave, intentos + 1, 300)
            raise HttpError(400, error_generico)

        # 2. Validar que no tenga ya un usuario vinculado
        if paciente.usuario is not None:
            cache.set(limite_clave, intentos + 1, 300)
            raise HttpError(400, "Este DNI ya tiene una cuenta móvil vinculada.")

    except Paciente.DoesNotExist:
        cache.set(limite_clave, intentos + 1, 300)
        raise HttpError(400, error_generico)

    # 4. Validar que el nombre de usuario de Django no esté ocupado
    if User.objects.filter(username=data.username).exists():
        cache.set(limite_clave, intentos + 1, 300)
        raise HttpError(400, "El nombre de usuario seleccionado ya está en uso.")

    # 5. Crear usuario y enlazar de forma atómica
    with transaction.atomic():
        user = User.objects.create_user(
            username=data.username,
            email=data.email,
            password=data.password,
            first_name=paciente.nombre,
            last_name=paciente.apellido
        )
        paciente.usuario = user
        paciente.save()

        # Marcar código como utilizado
        vinculo.utilizado = True
        vinculo.save()

    # Resetear el limitador al tener éxito
    cache.delete(limite_clave)

    # 6. Generar token firmado
    token_generado = signing.dumps({"user_id": user.id})

    return {
        "token": token_generado,
        "nombre_paciente": paciente.nombre_completo,
        "email": user.email
    }


@router.post("/auth/login", response={200: TokenSchema})
def login_paciente(request, data: LoginSchema):
    """
    Inicia sesión usando el nombre de usuario y la contraseña del paciente,
    devolviendo un token firmado si la autenticación es correcta.
    """
    ip = obtener_client_ip(request)
    limite_clave = f"rl_login_{ip}"
    intentos = cache.get(limite_clave, 0)
    
    if intentos >= 5:
        raise HttpError(429, "Demasiados intentos de inicio de sesión fallidos. Intente de nuevo en 5 minutos.")

    user = authenticate(username=data.username, password=data.password)
    if user is None:
        cache.set(limite_clave, intentos + 1, 300)
        raise HttpError(401, "Credenciales incorrectas.")

    # Validamos que el usuario esté realmente enlazado a un paciente activo
    try:
        paciente = user.paciente_perfil
        if not paciente.estado:
            raise HttpError(403, "La cuenta del paciente está inhabilitada.")
    except Paciente.DoesNotExist:
        raise HttpError(403, "El usuario no corresponde al perfil de un paciente.")

    # Resetear el limitador al tener éxito
    cache.delete(limite_clave)

    token_generado = signing.dumps({"user_id": user.id})

    return {
        "token": token_generado,
        "nombre_paciente": paciente.nombre_completo,
        "email": user.email
    }


# ─── Endpoints de Consumo de Datos (Protegidos) ──────────────────────────────

@router.get("/perfil", auth=auth_paciente, response=PacientePerfilSchema)
def obtener_perfil(request):
    """Retorna los datos del perfil y medidas iniciales del paciente autenticado."""
    paciente = request.auth.paciente_perfil
    # Inyectar atributos dinámicos del JSON de informacion_clinica
    info = paciente.informacion_clinica or {}
    paciente.avatar_color = info.get("avatar_color", "#10B981")
    paciente.foto_url = info.get("foto_url", "")
    return paciente


@router.get("/plan-activo", auth=auth_paciente, response=PlanAlimentarioSchema)
def obtener_plan_activo(request):
    """Retorna el plan alimenticio activo del paciente."""
    paciente = request.auth.paciente_perfil
    plan = PlanAlimentario.objects.filter(paciente=paciente, estado='Activo').first()
    if not plan:
        raise HttpError(404, "No tienes un plan alimentario activo asignado.")
    return plan


@router.get("/medidas", auth=auth_paciente, response=List[MedidaCorporalSchema])
def obtener_historial_medidas(request):
    """Retorna el historial completo de mediciones antropométricas del paciente."""
    paciente = request.auth.paciente_perfil
    medidas = MedidaCorporal.objects.filter(paciente=paciente).order_by('-fecha')
    
    # Formateamos las fechas a string para evitar problemas de serialización
    resultado = []
    for m in medidas:
        resultado.append({
            "id": m.id,
            "fecha": m.fecha.strftime("%Y-%m-%d"),
            "peso_kg": float(m.peso_kg),
            "talla_cm": float(m.talla_cm),
            "imc": float(m.imc),
            "grasa_corporal_pct": float(m.grasa_corporal_pct) if m.grasa_corporal_pct else None,
            "cintura_cm": float(m.cintura_cm) if m.cintura_cm else None,
            "cadera_cm": float(m.cadera_cm) if m.cadera_cm else None,
            "masa_muscular_kg": float(m.masa_muscular_kg) if m.masa_muscular_kg else None,
            "agua_corporal_pct": float(m.agua_corporal_pct) if m.agua_corporal_pct else None,
            "tmb": m.tmb,
            "notas": m.notas
        })
    return resultado


@router.get("/citas", auth=auth_paciente, response=List[CitaSchema])
def obtener_proximas_citas(request):
    """Retorna las citas futuras del paciente."""
    paciente = request.auth.paciente_perfil
    citas = Cita.objects.filter(
        paciente=paciente,
        fecha_hora__gte=timezone.now()
    ).exclude(estado='cancelada').order_by('fecha_hora')
    
    resultado = []
    for c in citas:
        nutri_nombre = "Asignado"
        if c.nutricionista:
            nutri_nombre = c.nutricionista.perfil.nombre_completo if hasattr(c.nutricionista, 'perfil') else c.nutricionista.get_full_name() or c.nutricionista.username
            
        resultado.append({
            "id": c.id,
            "fecha_hora": c.fecha_hora.strftime("%Y-%m-%d %H:%M"),
            "duracion_minutos": c.duracion_minutos,
            "tipo": c.get_tipo_display(),
            "estado": c.get_estado_display(),
            "motivo": c.motivo,
            "nombre_nutricionista": nutri_nombre
        })
    return resultado


@router.get("/notas", auth=auth_paciente, response=List[NotaClinicaSchema])
def obtener_notas_compartidas(request):
    """Retorna las notas clínicas asociadas al paciente."""
    paciente = request.auth.paciente_perfil
    # Filtramos por tipo consulta o seguimiento (evitamos recetas internas si existiesen, o mostramos las que aplican)
    notas = NotaClinica.objects.filter(paciente=paciente).order_by('-fecha')
    
    resultado = []
    for n in notas:
        resultado.append({
            "id": n.id,
            "fecha": n.fecha.strftime("%Y-%m-%d"),
            "titulo": n.titulo,
            "contenido": n.contenido,
            "tipo": n.get_tipo_display()
        })
    return resultado


@router.post("/perfil/update", auth=auth_paciente)
def actualizar_perfil(request, data: PerfilUpdateSchema):
    """Actualiza la información de perfil del paciente autenticado y su usuario Django."""
    user = request.auth
    paciente = user.paciente_perfil
    
    # Validar campos vacíos
    if not data.nombre.strip() or not data.apellido.strip() or not data.telefono.strip() or not data.email.strip():
        raise HttpError(400, "Todos los campos son obligatorios.")
        
    # Validar formato de correo básico
    if "@" not in data.email:
        raise HttpError(400, "Formato de correo electrónico inválido.")
        
    paciente.nombre = data.nombre.strip()
    paciente.apellido = data.apellido.strip()
    paciente.telefono = data.telefono.strip()
    paciente.email = data.email.strip().lower()
    
    # Guardar en informacion_clinica los atributos del avatar
    if paciente.informacion_clinica is None:
        paciente.informacion_clinica = {}
    
    if data.avatar_color:
        paciente.informacion_clinica["avatar_color"] = data.avatar_color.strip()
    if data.foto_url is not None:
        paciente.informacion_clinica["foto_url"] = data.foto_url.strip()
        
    try:
        paciente.full_clean()
        paciente.save()
    except ValidationError as e:
        raise HttpError(400, str(e))
        
    # Sincronizar el User de Django
    user.first_name = paciente.nombre
    user.last_name = paciente.apellido
    user.email = paciente.email
    user.save()
    
    return {
        "success": True,
        "nombre_paciente": f"{paciente.nombre} {paciente.apellido}",
        "email": paciente.email,
        "telefono": paciente.telefono,
        "avatar_color": paciente.informacion_clinica.get("avatar_color", "#10B981"),
        "foto_url": paciente.informacion_clinica.get("foto_url", "")
    }
