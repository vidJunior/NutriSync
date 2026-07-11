# config/api.py
from ninja import NinjaAPI
from pacientes.api import router as pacientes_router

api = NinjaAPI(
    title="NutriSync API",
    version="1.0.0",
    description="API para el aplicativo móvil de pacientes de NutriSync"
)

# Registramos el router de pacientes
api.add_router("/paciente", pacientes_router)
