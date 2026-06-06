"""Valores canónicos y validaciones puras del torneo de comunidades.

Este módulo no depende de Discord, de la base de datos ni de ``LombardBot``.
Los textos se comparan de forma exacta: no se corrigen mayúsculas, acentos,
espacios ni errores ortográficos.
"""

from decimal import Decimal, InvalidOperation

# Estados de torneo
TORNEO_CREADO = "CREADO"
TORNEO_EN_CURSO = "EN_CURSO"
TORNEO_FINALIZADO = "FINALIZADO"
ESTADOS_TORNEO = frozenset({
    TORNEO_CREADO,
    TORNEO_EN_CURSO,
    TORNEO_FINALIZADO,
})

# Estados de ronda
RONDA_ABIERTA = "ABIERTA"
RONDA_BLOQUEADA = "BLOQUEADA"
RONDA_CERRADA = "CERRADA"
ESTADOS_RONDA = frozenset({
    RONDA_ABIERTA,
    RONDA_BLOQUEADA,
    RONDA_CERRADA,
})

# Estados de enfrentamiento
ENFRENTAMIENTO_PENDIENTE_ELECCIONES = "PENDIENTE_ELECCIONES"
ENFRENTAMIENTO_PARTIDOS_CREADOS = "PARTIDOS_CREADOS"
ENFRENTAMIENTO_EN_CURSO = "EN_CURSO"
ENFRENTAMIENTO_CERRADO = "CERRADO"
ENFRENTAMIENTO_ADMINISTRADO = "ADMINISTRADO"
ESTADOS_ENFRENTAMIENTO = frozenset({
    ENFRENTAMIENTO_PENDIENTE_ELECCIONES,
    ENFRENTAMIENTO_PARTIDOS_CREADOS,
    ENFRENTAMIENTO_EN_CURSO,
    ENFRENTAMIENTO_CERRADO,
    ENFRENTAMIENTO_ADMINISTRADO,
})

# Estados de partido individual
PARTIDO_PENDIENTE = "PENDIENTE"
PARTIDO_EN_CURSO = "EN_CURSO"
PARTIDO_FINALIZADO = "FINALIZADO"
PARTIDO_ADMINISTRADO = "ADMINISTRADO"
ESTADOS_PARTIDO = frozenset({
    PARTIDO_PENDIENTE,
    PARTIDO_EN_CURSO,
    PARTIDO_FINALIZADO,
    PARTIDO_ADMINISTRADO,
})

# Estado temporal del equipo. La condición zombie es independiente y permanente.
ESTADO_TEMPORAL_NEUTRO = "NEUTRO"
ESTADO_TEMPORAL_CAZADOR = "CAZADOR"
ESTADO_TEMPORAL_CAZADOR_Z = "CAZADOR_Z"
ESTADO_TEMPORAL_HERIDO = "HERIDO"
ESTADOS_TEMPORALES = frozenset({
    ESTADO_TEMPORAL_NEUTRO,
    ESTADO_TEMPORAL_CAZADOR,
    ESTADO_TEMPORAL_CAZADOR_Z,
    ESTADO_TEMPORAL_HERIDO,
})

# Orígenes de resultados
RESULTADO_ORIGEN_API = "API"
RESULTADO_ORIGEN_ADMIN = "ADMIN"
ORIGENES_RESULTADO = frozenset({
    RESULTADO_ORIGEN_API,
    RESULTADO_ORIGEN_ADMIN,
})

# Tipos aceptados por el comando de administración de partidos.
TIPO_ADMIN_FORFEIT_LOCAL = "forfeit_local"
TIPO_ADMIN_FORFEIT_VISITANTE = "forfeit_visitante"
TIPO_ADMIN_EMPATE = "empate_admin"
TIPO_ADMIN_DOBLE_FORFEIT = "doble_forfeit"
TIPO_ADMIN_MANUAL = "manual"
TIPOS_ADMINISTRATIVOS = frozenset({
    TIPO_ADMIN_FORFEIT_LOCAL,
    TIPO_ADMIN_FORFEIT_VISITANTE,
    TIPO_ADMIN_EMPATE,
    TIPO_ADMIN_DOBLE_FORFEIT,
    TIPO_ADMIN_MANUAL,
})

# Razas canónicas. El orden coincide con la especificación funcional.
RAZAS = (
    "Alianza V. Mundo",
    "Amazonas",
    "Caos Elegido",
    "Elfos Oscuros",
    "Elfos Silvanos",
    "Enanos del Caos",
    "Enanos",
    "Hombres Lagarto",
    "Horror Nigromantico",
    "Humanos",
    "Inframundo",
    "Khorne",
    "No muertos",
    "Nobleza Imperial",
    "Nordicos",
    "Nurgle",
    "Orcos negros",
    "Orcos",
    "Renegados",
    "Skaven",
    "Stunty",
    "Union Elfica",
    "Vampiros",
)
RAZAS_VALIDAS = frozenset(RAZAS)

# El mapeo es deliberadamente explícito: la ruta física no se deduce ni admite aliases.
ICONOS_POR_RAZA = {
    "Alianza V. Mundo": "Iconos/Alianza V. Mundo.png",
    "Amazonas": "Iconos/Amazonas.png",
    "Caos Elegido": "Iconos/Caos Elegido.png",
    "Elfos Oscuros": "Iconos/Elfos Oscuros.png",
    "Elfos Silvanos": "Iconos/Elfos Silvanos.png",
    "Enanos del Caos": "Iconos/Enanos del Caos.png",
    "Enanos": "Iconos/Enanos.png",
    "Hombres Lagarto": "Iconos/Hombres Lagarto.png",
    "Horror Nigromantico": "Iconos/Horror Nigromantico.png",
    "Humanos": "Iconos/Humanos.png",
    "Inframundo": "Iconos/Inframundo.png",
    "Khorne": "Iconos/Khorne.png",
    "No muertos": "Iconos/No muertos.png",
    "Nobleza Imperial": "Iconos/Nobleza Imperial.png",
    "Nordicos": "Iconos/Nordicos.png",
    "Nurgle": "Iconos/Nurgle.png",
    "Orcos negros": "Iconos/Orcos negros.png",
    "Orcos": "Iconos/Orcos.png",
    "Renegados": "Iconos/Renegados.png",
    "Skaven": "Iconos/Skaven.png",
    "Stunty": "Iconos/Stunty.png",
    "Union Elfica": "Iconos/Union Elfica.png",
    "Vampiros": "Iconos/Vampiros.png",
}

# Textos de estado para presentaciones que no quieran depender de Discord.
EMOJI_CAZADOR = "🏹"
EMOJI_HERIDO = "🩸"
EMOJI_ZOMBIE = "🧟"
EMOJI_CAZADOR_Z = f"{EMOJI_CAZADOR}{EMOJI_ZOMBIE}"
EMOJIS_ESTADO_TEMPORAL = {
    ESTADO_TEMPORAL_NEUTRO: "",
    ESTADO_TEMPORAL_CAZADOR: EMOJI_CAZADOR,
    ESTADO_TEMPORAL_CAZADOR_Z: EMOJI_CAZADOR_Z,
    ESTADO_TEMPORAL_HERIDO: EMOJI_HERIDO,
}

LIMITE_CANALES_POR_CATEGORIA = 40

# Las plantillas son obligatorias en el esquema, pero en la v1 se configuran
# directamente en base de datos después de crear el torneo.
PLANTILLA_RONDA1_PENDIENTE = "PENDIENTE_CONFIGURACION_BD_MENSAJE_INICIAL"
PLANTILLA_RONDAS_SIGUIENTES_PENDIENTE = (
    "PENDIENTE_CONFIGURACION_BD_MENSAJES_SUBSIGUIENTES"
)


def validar_raza(raza):
    """Indica si ``raza`` coincide exactamente con un nombre canónico."""
    return isinstance(raza, str) and raza in RAZAS_VALIDAS


def validar_puntuacion(valor):
    """Valida una puntuación no negativa, finita y con hasta dos decimales.

    Se aceptan números y textos decimales sin espacios exteriores. Los booleanos,
    la notación no finita y los valores que no caben en ``DECIMAL(6, 2)`` se
    rechazan para mantener la misma restricción que la configuración persistida.
    """
    if isinstance(valor, bool) or valor is None:
        return False
    if isinstance(valor, str) and (not valor or valor != valor.strip()):
        return False

    try:
        puntuacion = Decimal(str(valor))
    except (InvalidOperation, ValueError, TypeError):
        return False

    if not puntuacion.is_finite() or puntuacion < 0 or puntuacion > Decimal("9999.99"):
        return False
    return puntuacion.as_tuple().exponent >= -2


def validar_estado_temporal(estado_temporal):
    """Indica si el estado temporal es uno de los cuatro valores canónicos."""
    return isinstance(estado_temporal, str) and estado_temporal in ESTADOS_TEMPORALES


def validar_combinacion_estados(*, herido=False, cazador=False, cazador_z=False, zombie=False):
    """Valida los indicadores conceptuales de estado de un equipo.

    ``zombie`` puede convivir con cualquier estado temporal. Entre ``herido``,
    ``cazador`` y ``cazador_z`` solo puede haber como máximo uno activo.
    """
    indicadores = (herido, cazador, cazador_z, zombie)
    if any(type(indicador) is not bool for indicador in indicadores):
        return False
    return sum((herido, cazador, cazador_z)) <= 1
