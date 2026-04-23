"""Constantes y utilidades mínimas para torneo suizo."""

# Estados de torneo
TORNEO_CREADO = "CREADO"
TORNEO_EN_CURSO = "EN_CURSO"
TORNEO_FINALIZADO = "FINALIZADO"

# Estados de ronda
RONDA_ABIERTA = "ABIERTA"
RONDA_BLOQUEADA = "BLOQUEADA"
RONDA_CERRADA = "CERRADA"

# Estados de emparejamiento
EMP_PENDIENTE = "PENDIENTE"
EMP_REPORTADO = "REPORTADO"
EMP_ADMINISTRADO = "ADMINISTRADO"
EMP_CERRADO = "CERRADO"

# Estados de participante
PART_ACTIVO = "ACTIVO"
PART_RETIRADO = "RETIRADO"

# Formatos de serie
FORMATOS_SERIE = {"BO1", "BO3", "BO5"}


def normalizar_formato_serie(texto):
    """Normaliza bo1/bo3/bo5 a BO1/BO3/BO5 o lanza ValueError."""
    valor = str(texto).strip().upper()
    if valor not in FORMATOS_SERIE:
        raise ValueError(f"Formato de serie inválido: {texto!r}")
    return valor
