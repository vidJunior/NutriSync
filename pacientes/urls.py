# pacientes/urls.py
# Rutas de pacientes.

from django.urls import path
from . import views

app_name = "pacientes"

urlpatterns = [
    path("", views.PacienteListView.as_view(), name="lista"),
    path("nuevo/", views.PacienteCreateView.as_view(), name="nuevo"),
    path("<int:pk>/", views.PacienteDetailView.as_view(), name="detalle"),
    path("<int:pk>/editar/", views.PacienteUpdateView.as_view(), name="editar"),
    path("<int:pk>/guardar-informacion/", views.paciente_guardar_informacion, name="guardar_informacion"),
    path("<int:pk>/toggle/", views.paciente_toggle_estado, name="toggle"),
    path("<int:pk>/mediciones/", views.paciente_mediciones_list, name="mediciones_list"),
    path("<int:pk>/mediciones/guardar/", views.paciente_medicion_guardar, name="medicion_guardar"),
    path("<int:pk>/mediciones/<int:medida_id>/eliminar/", views.paciente_medicion_eliminar, name="medicion_eliminar"),
    path("<int:pk>/evaluacion/", views.paciente_evaluacion_get, name="evaluacion_get"),
    path("<int:pk>/evaluacion/guardar/", views.paciente_evaluacion_guardar, name="evaluacion_guardar"),
    path("<int:pk>/plan/", views.paciente_plan_get, name="plan_get"),
    path("<int:pk>/plan/guardar/", views.paciente_plan_guardar, name="plan_guardar"),
    path("<int:pk>/plan/nueva-version/", views.paciente_plan_nueva_version, name="plan_nueva_version"),
    path("<int:pk>/plan/aplicar-modelo/", views.paciente_plan_aplicar_modelo, name="plan_aplicar_modelo"),
    path("<int:pk>/plan/duplicar/", views.paciente_plan_duplicar, name="plan_duplicar"),
    path("<int:pk>/plan/eliminar/", views.paciente_plan_eliminar, name="plan_eliminar"),
    path("<int:pk>/plan/enviar/", views.paciente_plan_enviar, name="plan_enviar"),
    path("<int:pk>/plan/<int:plan_id>/imprimir/", views.paciente_plan_imprimir, name="plan_imprimir"),
    path("<int:pk>/seguimiento/", views.paciente_seguimiento_get, name="seguimiento_get"),
    path("<int:pk>/seguimiento/guardar/", views.paciente_seguimiento_guardar, name="seguimiento_guardar"),
    path("<int:pk>/archivos/", views.paciente_archivos_list, name="archivos_list"),
    path("<int:pk>/archivos/subir/", views.paciente_archivo_subir, name="archivo_subir"),
    path("<int:pk>/archivos/<int:archivo_id>/eliminar/", views.paciente_archivo_eliminar, name="archivo_eliminar"),
    path("<int:pk>/recomendaciones/", views.paciente_recomendaciones_get, name="recomendaciones_get"),
    path("<int:pk>/recomendaciones/guardar/", views.paciente_recomendacion_guardar, name="recomendacion_guardar"),
    path("<int:pk>/entregables/", views.paciente_entregables_get, name="entregables_get"),
    path("<int:pk>/entregables/guardar/", views.paciente_entregable_guardar, name="entregable_guardar"),
    path("<int:pk>/entregables/<int:entregable_id>/eliminar/", views.paciente_entregable_eliminar, name="entregable_eliminar"),
    path("<int:pk>/plan/<int:plan_id>/publicar/", views.paciente_plan_publicar, name="plan_publicar"),
    path("<int:pk>/entregables/pdf/", views.paciente_entregables_pdf, name="entregables_pdf"),
    path("<int:pk>/resumen/<int:cita_id>/imprimir/", views.paciente_resumen_imprimir, name="resumen_imprimir"),
    path("<int:pk>/consultas/iniciar/", views.paciente_consulta_iniciar, name="consulta_iniciar"),
    path("<int:pk>/consultas/<int:consulta_id>/finalizar/", views.paciente_consulta_finalizar, name="consulta_finalizar"),
    path("<int:pk>/generar-vinculo/", views.paciente_generar_vinculo, name="generar_vinculo"),
]

