# pacientes/api.py
from typing import List, Dict, Any, Optional
import re

from django.conf import settings
from django.utils import timezone
from django.core import signing
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from ninja import Router, Schema
from ninja.security import HttpBearer
from ninja.errors import HttpError
from django.core.cache import cache
from pacientes.models import Paciente, CodigoVinculacion, PlanAlimentario, ArchivoPaciente
from agendas.models import Cita
from seguimiento.models import MedidaCorporal, NotaClinica, Recomendacion
from core.validation import validate_hex_color, validate_http_url
from pacientes.validators import validate_dni, validate_telefono

router = Router()

def obtener_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if settings.TRUST_X_FORWARDED_FOR and x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '').strip()

# Autenticación con token

class PacienteAuth(HttpBearer):
    def authenticate(self, request, token):
        try:
            # Valida el token de 30 días.
            data = signing.loads(token, max_age=60*60*24*30)
            user_id = data.get("user_id")
            # Precarga el perfil del paciente.
            user = User.objects.select_related('paciente_perfil').get(pk=user_id)
            paciente = user.paciente_perfil
            if not user.is_active or not paciente.estado or paciente.usuario_id != user.id:
                return None
            return user
        except (
            signing.SignatureExpired,
            signing.BadSignature,
            User.DoesNotExist,
            Paciente.DoesNotExist,
        ):
            return None

auth_paciente = PacienteAuth()

# Esquemas de entrada y salida

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
    motivo_consulta: str
    resumen_consulta: str
    objetivos_acordados: str
    plan_accion: str
    observaciones_clinicas: str
    tipo: str

class RecomendacionSchema(Schema):
    id: int
    fecha: str
    categoria: str
    descripcion: Dict[str, Any]
    estado_cumplimiento: str

class ArchivoPacienteSchema(Schema):
    id: int
    nombre: str
    categoria: str
    fecha_registro: str
    archivo_url: str
    observaciones: str


# Autenticación y registro

@router.post("/auth/register-vinculado", response={200: TokenSchema})
def registrar_paciente_vinculado(request, data: RegistroPacienteSchema):
    """
    Registra una cuenta de usuario Django vinculada a un expediente de paciente
    mediante el DNI y el código de vinculación otorgado por el nutricionista.
    """
    dni = data.dni.strip()
    code = data.codigo_vinculacion.strip().upper()
    username = data.username.strip()
    email = data.email.strip().lower()
    password = data.password
    try:
        validate_dni(dni)
        validate_email(email)
        validate_password(password)
    except ValidationError as exc:
        raise HttpError(400, " ".join(exc.messages))
    if not re.fullmatch(r"[\w.@+-]{3,150}", username):
        raise HttpError(400, "El nombre de usuario no tiene un formato válido.")
    if not re.fullmatch(r"[A-Z0-9]{6}", code):
        raise HttpError(400, "El código de vinculación no tiene un formato válido.")
    if User.objects.filter(email__iexact=email).exists():
        raise HttpError(400, "El correo electrónico ya está asociado a otra cuenta.")

    ip = obtener_client_ip(request)
    limite_clave = f"rl_vinculo_{ip}"
    intentos = cache.get(limite_clave, 0)
    
    if intentos >= 5:
        raise HttpError(429, "Demasiados intentos de vinculación fallidos. Intente de nuevo en 5 minutos.")

    error_generico = "El DNI o el código de vinculación proporcionados no son válidos."

    try:
        # 1. Buscar candidatos por DNI
        pacientes_candidatos = Paciente.objects.filter(dni=dni, estado=True)
        if not pacientes_candidatos.exists():
            raise Paciente.DoesNotExist

        paciente = None
        for cand in pacientes_candidatos:
            try:
                vinculo = CodigoVinculacion.objects.get(paciente=cand)
                # Validar código y vigencia, y que el correo coincida
                if vinculo.esta_valido() and vinculo.codigo == code:
                    if cand.email and cand.email.strip().lower() == email:
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

    # 4. Valida que el usuario esté disponible.
    if User.objects.filter(username__iexact=username).exists():
        cache.set(limite_clave, intentos + 1, 300)
        raise HttpError(400, "El nombre de usuario seleccionado ya está en uso.")

    # 5. Crear usuario y enlazar de forma atómica
    with transaction.atomic():
        paciente = Paciente.objects.select_for_update().get(pk=paciente.pk)
        vinculo = CodigoVinculacion.objects.select_for_update().get(paciente=paciente)
        if paciente.usuario_id or not vinculo.esta_valido() or vinculo.codigo != code:
            raise HttpError(400, error_generico)
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=paciente.nombre,
                last_name=paciente.apellido
            )
        except IntegrityError as exc:
            raise HttpError(
                400,
                "El usuario o correo ya está asociado a otra cuenta.",
            ) from exc
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
    username = data.username.strip()
    if not username or len(username) > 150 or len(data.password) > 128:
        raise HttpError(401, "Credenciales incorrectas.")

    ip = obtener_client_ip(request)
    limite_clave = f"rl_login_{ip}"
    intentos = cache.get(limite_clave, 0)
    
    if intentos >= 5:
        raise HttpError(429, "Demasiados intentos de inicio de sesión fallidos. Intente de nuevo en 5 minutos.")

    user = authenticate(username=username, password=data.password)
    if user is None:
        cache.set(limite_clave, intentos + 1, 300)
        raise HttpError(401, "Credenciales incorrectas.")

    # Verifica el vínculo con un paciente activo.
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


# Endpoints protegidos

@router.get("/perfil", auth=auth_paciente, response=PacientePerfilSchema)
def obtener_perfil(request):
    """Retorna los datos del perfil y medidas iniciales del paciente autenticado."""
    paciente = request.auth.paciente_perfil
    # Añade los datos clínicos del JSON.
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
    
    # Convierte las fechas para serializarlas.
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
    notas = NotaClinica.objects.filter(paciente=paciente).order_by('-fecha')
    
    resultado = []
    for n in notas:
        resultado.append({
            "id": n.id,
            "fecha": n.fecha.strftime("%Y-%m-%d"),
            "titulo": n.titulo,
            "motivo_consulta": n.motivo_consulta or "",
            "resumen_consulta": n.resumen_consulta or "",
            "objetivos_acordados": n.objetivos_acordados or "",
            "plan_accion": n.plan_accion or "",
            "observaciones_clinicas": n.observaciones_clinicas or "",
            "tipo": n.get_tipo_display()
        })
    return resultado


@router.get("/recomendaciones", auth=auth_paciente, response=List[RecomendacionSchema])
def obtener_recomendaciones_paciente(request):
    """Retorna las recomendaciones de hábitos, hidratación, etc. entregadas al paciente."""
    paciente = request.auth.paciente_perfil
    recoms = Recomendacion.objects.filter(paciente=paciente).order_by('-fecha')
    resultado = []
    for r in recoms:
        resultado.append({
            "id": r.id,
            "fecha": r.fecha.strftime("%Y-%m-%d"),
            "categoria": r.categoria,
            "descripcion": r.descripcion or {},
            "estado_cumplimiento": r.get_estado_cumplimiento_display()
        })
    return resultado


@router.get("/archivos", auth=auth_paciente, response=List[ArchivoPacienteSchema])
def obtener_archivos_paciente(request):
    """Retorna la lista de archivos (laboratorios, PDF, etc.) compartidos con el paciente."""
    paciente = request.auth.paciente_perfil
    archivos = ArchivoPaciente.objects.filter(paciente=paciente).order_by('-fecha_registro')
    resultado = []
    for a in archivos:
        url_archivo = a.archivo.url if a.archivo else ""
        resultado.append({
            "id": a.id,
            "nombre": a.nombre,
            "categoria": a.get_categoria_display(),
            "fecha_registro": a.fecha_registro.strftime("%Y-%m-%d"),
            "archivo_url": url_archivo,
            "observaciones": a.observaciones or ""
        })
    return resultado


@router.post("/perfil/update", auth=auth_paciente)
@transaction.atomic
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
        
    email = data.email.strip().lower()
    try:
        validate_email(email)
        validate_telefono(data.telefono.strip())
        validate_hex_color(data.avatar_color)
        validate_http_url(data.foto_url)
    except ValidationError as exc:
        raise HttpError(400, " ".join(exc.messages))
    if User.objects.filter(email__iexact=email).exclude(pk=user.pk).exists():
        raise HttpError(400, "El correo electrónico ya está asociado a otra cuenta.")
    if (
        Paciente.objects.filter(
            nutricionista=paciente.nutricionista,
            email__iexact=email,
        )
        .exclude(pk=paciente.pk)
        .exists()
    ):
        raise HttpError(400, "El profesional ya tiene otro paciente con este correo.")

    paciente.nombre = data.nombre.strip()
    paciente.apellido = data.apellido.strip()
    paciente.telefono = data.telefono.strip()
    paciente.email = email
    
    # Guarda los datos del avatar.
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
    try:
        user.full_clean()
        user.save()
    except ValidationError as exc:
        raise HttpError(400, " ".join(exc.messages))
    
    return {
        "success": True,
        "nombre_paciente": f"{paciente.nombre} {paciente.apellido}",
        "email": paciente.email,
        "telefono": paciente.telefono,
        "avatar_color": paciente.informacion_clinica.get("avatar_color", "#10B981"),
        "foto_url": paciente.informacion_clinica.get("foto_url", "")
    }
