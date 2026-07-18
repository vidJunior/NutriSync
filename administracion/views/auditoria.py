# administracion/views/auditoria.py
# Auditoría administrativa.

from django.shortcuts import render
from django.core.paginator import Paginator

from administracion.mixins import admin_requerido
from administracion.models import LogAuditoriaAdmin


@admin_requerido
def logs_lista_view(request):
    """Lista el registro histórico de logs de auditoría del panel administrativo."""
    logs_queryset = LogAuditoriaAdmin.objects.select_related("administrador").all().order_by("-fecha")
    
    paginator = Paginator(logs_queryset, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    
    return render(request, "administracion/auditoria/logs.html", {"page_obj": page_obj})
