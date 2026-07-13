# administracion/context_processors.py
# Inyecta el perfil del administrador en el contexto global.

def admin_context(request):
    """Inyecta el perfil del administrador en el contexto."""
    if request.user.is_authenticated:
        perfil = getattr(request.user, "perfil", None)
        if perfil and perfil.rol == "admin_plataforma":
            return {"admin_perfil": perfil}
    return {"admin_perfil": None}
