"""Parsing de argumentos Discord para los comandos del torneo de comunidades."""

from datetime import datetime
from decimal import Decimal, InvalidOperation


def parsear_fecha_limite(fecha: str, hora: str) -> datetime:
    """Convierte exclusivamente ``YYYY-MM-DD HH:MM`` a ``datetime``."""
    texto = f"{fecha} {hora}"
    try:
        resultado = datetime.strptime(texto, "%Y-%m-%d %H:%M")
    except (TypeError, ValueError) as exc:
        raise ValueError("Usa el formato de fecha y hora `YYYY-MM-DD HH:MM`.") from exc
    if resultado.strftime("%Y-%m-%d %H:%M") != texto:
        raise ValueError("Usa el formato de fecha y hora `YYYY-MM-DD HH:MM`.")
    return resultado


def parsear_decimal(valor: str, nombre: str) -> Decimal:
    """Convierte un argumento en Decimal; las reglas de negocio se validan en core."""
    try:
        return Decimal(valor)
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"`{nombre}` debe ser un número decimal válido.") from exc
