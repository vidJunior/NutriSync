# config/choices.py
# Opciones compartidas del proyecto.

class Sexo:
    MASCULINO = "M"
    FEMENINO = "F"
    CHOICES = [
        (MASCULINO, "Masculino"),
        (FEMENINO, "Femenino"),
    ]


class TipoCita:
    PRIMERA_CONSULTA = "primera_consulta"
    SEGUIMIENTO = "seguimiento"
    CONTROL = "control"
    EVALUACION = "evaluacion"
    BLOQUEO = "bloqueo"
    CHOICES = [
        (PRIMERA_CONSULTA, "Primera Consulta"),
        (SEGUIMIENTO, "Seguimiento"),
        (CONTROL, "Control"),
        (EVALUACION, "Evaluación"),
        (BLOQUEO, "Bloqueo de Horario"),
    ]


class EstadoCita:
    PROGRAMADA = "programada"
    EN_CONSULTA = "en_consulta"
    FINALIZADA = "finalizada"
    COMPLETADA = "completada"
    CANCELADA = "cancelada"
    NO_ASISTIO = "no_asistio"
    BLOQUEADA = "bloqueada"
    CHOICES = [
        (PROGRAMADA, "Programada"),
        (EN_CONSULTA, "En consulta"),
        (FINALIZADA, "Finalizada"),
        (COMPLETADA, "Completada"),
        (CANCELADA, "Cancelada"),
        (NO_ASISTIO, "No asistió"),
        (BLOQUEADA, "Bloqueada"),
    ]


class TipoComida:
    DESAYUNO = "desayuno"
    ALMUERZO = "almuerzo"
    CENA = "cena"
    SNACK = "snack"
    CHOICES = [
        (DESAYUNO, "Desayuno"),
        (ALMUERZO, "Almuerzo"),
        (CENA, "Cena"),
        (SNACK, "Snack"),
    ]


class DiaSemana:
    LUNES = "lunes"
    MARTES = "martes"
    MIERCOLES = "miercoles"
    JUEVES = "jueves"
    VIERNES = "viernes"
    SABADO = "sabado"
    DOMINGO = "domingo"
    CHOICES = [
        (LUNES, "Lunes"),
        (MARTES, "Martes"),
        (MIERCOLES, "Miércoles"),
        (JUEVES, "Jueves"),
        (VIERNES, "Viernes"),
        (SABADO, "Sábado"),
        (DOMINGO, "Domingo"),
    ]


class Objetivo:
    PERDIDA_PESO = "perdida_peso"
    GANANCIA_MUSCULAR = "ganancia_muscular"
    MANTENIMIENTO = "mantenimiento"
    SALUD_GENERAL = "salud_general"
    CHOICES = [
        (PERDIDA_PESO, "Pérdida de peso"),
        (GANANCIA_MUSCULAR, "Ganancia muscular"),
        (MANTENIMIENTO, "Mantenimiento"),
        (SALUD_GENERAL, "Salud general"),
    ]


class TipoNota:
    CONSULTA = "consulta"
    SEGUIMIENTO = "seguimiento"
    OBSERVACION = "observacion"
    CHOICES = [
        (CONSULTA, "Consulta"),
        (SEGUIMIENTO, "Seguimiento"),
        (OBSERVACION, "Observación"),
    ]


class EstadoNutricionista:
    HABILITADO = "habilitado"
    DESHABILITADO = "deshabilitado"
    CHOICES = [
        (HABILITADO, "Habilitado"),
        (DESHABILITADO, "Deshabilitado"),
    ]
