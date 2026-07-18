# agendas/models.py
# Citas y bloqueos de agenda.

from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth.models import User
from datetime import timedelta
from config.choices import TipoCita, EstadoCita
from pacientes.models import Paciente
from agendas.validators import validate_duracion_minutos, validate_costo_positivo


class Cita(models.Model):
    """
    Representa una consulta médica agendada entre el nutricionista y el paciente.
    La validación en clean() impide el solapamiento de citas y asegura que el paciente esté activo.
    """

    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="citas",
        verbose_name="Paciente",
    )
    nutricionista = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="citas_creadas",
        verbose_name="Nutricionista",
    )
    fecha_hora = models.DateTimeField(
        verbose_name="Fecha y hora",
        help_text="Fecha y hora de inicio de la cita",
    )
    duracion_minutos = models.PositiveIntegerField(
        default=45,
        validators=[validate_duracion_minutos],
        verbose_name="Duración (minutos)",
        help_text="Duración estimada de la consulta en minutos",
    )
    tipo = models.CharField(
        max_length=20,
        choices=TipoCita.CHOICES,
        default=TipoCita.SEGUIMIENTO,
        verbose_name="Tipo de consulta",
    )
    estado = models.CharField(
        max_length=20,
        choices=EstadoCita.CHOICES,
        default=EstadoCita.PROGRAMADA,
        verbose_name="Estado",
    )
    motivo = models.TextField(
        verbose_name="Motivo de la consulta",
        help_text="Breve descripción del motivo de la cita",
    )
    notas_consulta = models.TextField(
        blank=True,
        verbose_name="Notas clínicas",
        help_text="Observaciones, diagnóstico o notas redactadas durante la consulta",
    )
    costo = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0.00,
        validators=[validate_costo_positivo],
        verbose_name="Costo de la consulta",
    )
    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de registro",
    )

    class Meta:
        ordering = ["fecha_hora"]
        verbose_name = "Cita"
        verbose_name_plural = "Citas"
        db_table = "citas_cita"  # Mantener estable la tabla física original en PostgreSQL
        # Índices para búsquedas y ordenamientos frecuentes
        indexes = [
            models.Index(fields=["fecha_hora", "estado"]),
        ]

    def __str__(self):
        return (
            f"Cita con {self.paciente} - {self.fecha_hora.strftime('%d/%m/%Y %H:%M')}"
        )

    # Estado
    @property
    def esta_programada(self):
        return self.estado == EstadoCita.PROGRAMADA

    @property
    def esta_completada(self):
        return self.estado == EstadoCita.COMPLETADA

    @property
    def esta_cancelada(self):
        return self.estado == EstadoCita.CANCELADA

    @property
    def no_asistio(self):
        return self.estado == EstadoCita.NO_ASISTIO

    @property
    def fecha_fin(self):
        """Devuelve la fecha y hora estimada de finalización de la cita."""
        if self.fecha_hora:
            return self.fecha_hora + timedelta(minutes=self.duracion_minutos)
        return None

    @property
    def color_class(self):
        if self.estado == 'cancelada':
            return 'red'
        elif self.estado == 'bloqueada' or self.tipo == 'bloqueo':
            return 'grey'
        elif self.tipo == 'primera_consulta':
            return 'green'
        elif self.tipo == 'seguimiento':
            return 'blue'
        elif self.tipo == 'evaluacion':
            return 'purple'
        elif self.tipo == 'control':
            return 'orange'
        return 'blue'

    # Validaciones
    def clean(self):
        super().clean()
        errors = {}

        # Obtener instancia original en caso de edición
        original = None
        if self.pk:
            try:
                original = self.__class__.objects.get(pk=self.pk)
            except self.__class__.DoesNotExist:
                pass

        # 1. Validar que el paciente esté activo
        if self.paciente_id:
            # Recarga el estado guardado.
            paciente = Paciente.objects.only("estado", "nombre", "apellido").get(
                pk=self.paciente_id
            )
            if not paciente.esta_activo:
                errors["paciente"] = ValidationError(
                    "No se pueden programar citas para un paciente inactivo."
                )
            if (
                self.nutricionista_id
                and self.nutricionista_id != self.paciente.nutricionista_id
            ):
                errors["nutricionista"] = ValidationError(
                    "El nutricionista debe ser el responsable del paciente."
                )

        # 1.5 Bloquea citas finalizadas.
        if original and original.estado in [EstadoCita.COMPLETADA, EstadoCita.FINALIZADA]:
            if self.estado != original.estado:
                errors["estado"] = ValidationError(
                    "El estado de una cita completada o finalizada es inalterable."
                )

        # 2. Bloquea fechas pasadas.
        if self.fecha_hora:
            validar_fecha_pasada = False
            if not self.pk:
                # Cita nueva: la fecha siempre debe ser a futuro
                validar_fecha_pasada = True
            else:
                # Valida solo si cambió la fecha.
                if original and self.fecha_hora != original.fecha_hora:
                    validar_fecha_pasada = True

            if validar_fecha_pasada:
                # Tolera un minuto de desfase.
                if self.fecha_hora < timezone.now() - timedelta(minutes=1):
                    errors["fecha_hora"] = ValidationError(
                        "La fecha y hora de la cita no puede ser en el pasado."
                    )

        # 3. Valida cruces de horario.
        if self.fecha_hora and self.duracion_minutos:
            # Obtiene el nutricionista de la cita.
            nutricionista = self.paciente.nutricionista if self.paciente_id else self.nutricionista
            
            if nutricionista:
                inicio_nuevo = self.fecha_hora
                fin_nuevo = self.fecha_fin
                fecha_dia = timezone.localtime(self.fecha_hora).date()

                # Busca cruces de horario del mismo día.
                # Incluye citas directas y de pacientes.
                citas_dia = (
                    Cita.objects.filter(
                        models.Q(paciente__nutricionista=nutricionista) | models.Q(nutricionista=nutricionista),
                        fecha_hora__date=fecha_dia,
                    )
                    .exclude(estado=EstadoCita.CANCELADA)
                )

                # Excluimos la cita actual en caso de edición
                if self.pk:
                    citas_dia = citas_dia.exclude(pk=self.pk)

                for cita_existente in citas_dia:
                    inicio_existente = cita_existente.fecha_hora
                    fin_existente = cita_existente.fecha_fin

                    # Detecta intervalos superpuestos.
                    if inicio_existente < fin_nuevo and fin_existente > inicio_nuevo:
                        desc_cita = (
                            f"otra cita del paciente {cita_existente.paciente.nombre_completo}"
                            if cita_existente.paciente_id
                            else f"un bloqueo de horario ({cita_existente.motivo})"
                        )
                        errors["fecha_hora"] = ValidationError(
                            f"El horario seleccionado se solapa con {desc_cita} "
                            f"({inicio_existente.strftime('%H:%M')} - {fin_existente.strftime('%H:%M')})."
                        )
                        break

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        # Asigna el nutricionista del paciente.
        if self.paciente_id and not self.nutricionista_id:
            self.nutricionista = self.paciente.nutricionista
            
        # Siguiendo los estándares del docente de la sesión 2,
        # Valida antes de guardar.
        self.full_clean()
        super().save(*args, **kwargs)
