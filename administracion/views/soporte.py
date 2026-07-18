# administracion/views/soporte.py
# Gestión de soporte.

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone
from django.core.paginator import Paginator

from administracion.mixins import admin_requerido
from administracion.models import TicketSoporte, LogAuditoriaAdmin


@admin_requerido
def soporte_lista_view(request):
    """Lista las solicitudes de soporte técnico con filtros por estado."""
    estado_filtro = request.GET.get("estado", "abierto")
    
    queryset = TicketSoporte.objects.select_related("nutricionista__perfil")
    
    if estado_filtro:
        queryset = queryset.filter(estado=estado_filtro)
        
    queryset = queryset.order_by("-fecha_creacion")
    
    paginator = Paginator(queryset, 15)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    
    context = {
        "page_obj": page_obj,
        "estado_filtro": estado_filtro,
        "estados": [
            ("abierto", "Abiertos"),
            ("proceso", "En Proceso"),
            ("resuelto", "Resueltos"),
        ]
    }
    return render(request, "administracion/soporte/list.html", context)


@admin_requerido
def soporte_responder_view(request, pk):
    """Permite al operador visualizar la consulta del nutricionista y registrar una respuesta."""
    ticket = get_object_or_404(TicketSoporte, pk=pk)
    
    if request.method == "POST":
        respuesta = request.POST.get("respuesta", "").strip()
        nuevo_estado = request.POST.get("estado", "resuelto")
        
        if len(respuesta) > 10000:
            messages.error(request, "La respuesta no puede superar 10000 caracteres.")
        elif nuevo_estado not in dict(TicketSoporte.ESTADO_CHOICES):
            messages.error(request, "El estado del ticket no es válido.")
        elif not respuesta:
            messages.error(request, "Por favor escribe una respuesta para el ticket de soporte.")
        else:
            ticket.respuesta_admin = respuesta
            ticket.estado = nuevo_estado
            ticket.fecha_respuesta = timezone.now()
            ticket.respondido_por = request.user
            ticket.save()
            
            # Registrar en auditoría
            LogAuditoriaAdmin.objects.create(
                administrador=request.user,
                accion="Resolver Ticket",
                detalle=f"Respondió el ticket #{ticket.id} ('{ticket.asunto}') enviado por @{ticket.nutricionista.username} y lo marcó como '{nuevo_estado}'."
            )
            
            messages.success(request, f"Se ha enviado la respuesta del ticket #{ticket.id} con éxito.")
            return redirect("administracion:soporte_lista")
            
    return render(request, "administracion/soporte/responder.html", {"ticket": ticket})
