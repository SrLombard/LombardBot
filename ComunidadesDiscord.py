"""Helpers de Discord para los comandos del torneo de comunidades."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Optional, Tuple


MAX_CANALES_POR_CATEGORIA_COMUNIDADES = 40


@dataclass(frozen=True)
class IncidenciaCategoriaComunidades:
    """Motivo por el que una categoría configurada no se puede utilizar."""

    categoria_discord_id: int
    orden_alta: int
    estado: str
    canales_existentes: Optional[int] = None
    detalle: Optional[str] = None


class ErrorSeleccionCategoriaComunidades(ValueError):
    """Error estructurado listo para comunicarse en el canal administrativo."""

    def __init__(
        self,
        codigo: str,
        detalle: str,
        *,
        torneo_id: int,
        tipo: str,
        incidencias: Tuple[IncidenciaCategoriaComunidades, ...] = (),
    ):
        super().__init__(detalle)
        self.codigo = codigo
        self.detalle = detalle
        self.torneo_id = torneo_id
        self.tipo = tipo
        self.incidencias = incidencias

    def para_administracion(self) -> dict:
        """Expone un payload estable para que el llamador componga la publicación."""
        return {
            "codigo": self.codigo,
            "detalle": self.detalle,
            "torneo_id": self.torneo_id,
            "tipo": self.tipo,
            "categorias": [
                {
                    "categoria_discord_id": incidencia.categoria_discord_id,
                    "orden_alta": incidencia.orden_alta,
                    "estado": incidencia.estado,
                    "canales_existentes": incidencia.canales_existentes,
                    "detalle": incidencia.detalle,
                }
                for incidencia in self.incidencias
            ],
        }


def _estado_error_discord(exc: Exception) -> str:
    """Distingue las respuestas que Discord usa para recurso ausente y prohibido."""
    status = getattr(exc, "status", None)
    nombre = type(exc).__name__.lower()
    if status == 404 or nombre == "notfound":
        return "INEXISTENTE"
    return "INACCESIBLE"


async def _resolver_canal_configurado(guild: Any, categoria_id: int):
    categoria = guild.get_channel(categoria_id)
    if categoria is not None:
        return categoria, None

    fetch_channel = getattr(guild, "fetch_channel", None)
    if fetch_channel is None:
        return None, "INEXISTENTE"

    try:
        categoria = await fetch_channel(categoria_id)
    except Exception as exc:
        return None, _estado_error_discord(exc)
    if categoria is None:
        return None, "INEXISTENTE"
    return categoria, None


def _detalle_inaccesible(guild: Any, categoria: Any) -> Optional[str]:
    """Comprueba los permisos necesarios cuando el objeto Discord los expone."""
    permissions_for = getattr(categoria, "permissions_for", None)
    miembro_bot = getattr(guild, "me", None)
    if not callable(permissions_for) or miembro_bot is None:
        return None

    try:
        permisos = permissions_for(miembro_bot)
    except Exception:
        return "No se pudieron comprobar los permisos del bot en la categoría."

    if not getattr(permisos, "view_channel", True):
        return "El bot no puede ver la categoría."
    if not getattr(permisos, "manage_channels", True):
        return "El bot no puede administrar canales en la categoría."
    return None


async def planificar_categorias_comunidades(
    session: Any,
    guild: Any,
    *,
    torneo_id: int,
    tipo: str,
    cantidad: int,
):
    """Reserva lógicamente categorías para varias creaciones sin tocar Discord.

    La planificación completa permite detectar falta de capacidad antes de
    persistir una ronda. Cada aparición de una categoría en el resultado
    representa un canal nuevo y respeta tanto ``orden_alta`` como el límite
    global de 40 canales existentes por categoría.
    """
    from ComunidadesCore import obtener_categorias_comunidades

    if cantidad < 0:
        raise ValueError("cantidad no puede ser negativa.")
    if cantidad == 0:
        return ()

    categorias_configuradas = obtener_categorias_comunidades(
        session, torneo_id=torneo_id, tipo=tipo
    )
    if not categorias_configuradas:
        raise ErrorSeleccionCategoriaComunidades(
            "SIN_CATEGORIAS_CONFIGURADAS",
            f"El torneo {torneo_id} no tiene categorías de {tipo} configuradas.",
            torneo_id=torneo_id,
            tipo=tipo,
        )

    incidencias = []
    plan = []
    for configuracion in categorias_configuradas:
        categoria_id = int(configuracion.categoria_discord_id)
        categoria, estado_error = await _resolver_canal_configurado(guild, categoria_id)
        if categoria is None:
            incidencias.append(
                IncidenciaCategoriaComunidades(
                    categoria_discord_id=categoria_id,
                    orden_alta=int(configuracion.orden_alta),
                    estado=estado_error,
                )
            )
            continue

        detalle_inaccesible = _detalle_inaccesible(guild, categoria)
        if detalle_inaccesible is not None:
            incidencias.append(
                IncidenciaCategoriaComunidades(
                    categoria_discord_id=categoria_id,
                    orden_alta=int(configuracion.orden_alta),
                    estado="INACCESIBLE",
                    detalle=detalle_inaccesible,
                )
            )
            continue

        try:
            canales_existentes = len(categoria.channels)
        except (AttributeError, TypeError):
            incidencias.append(
                IncidenciaCategoriaComunidades(
                    categoria_discord_id=categoria_id,
                    orden_alta=int(configuracion.orden_alta),
                    estado="INACCESIBLE",
                    detalle="No se pudo contar los canales de la categoría.",
                )
            )
            continue

        huecos = MAX_CANALES_POR_CATEGORIA_COMUNIDADES - canales_existentes
        if huecos <= 0:
            incidencias.append(
                IncidenciaCategoriaComunidades(
                    categoria_discord_id=categoria_id,
                    orden_alta=int(configuracion.orden_alta),
                    estado="LLENA",
                    canales_existentes=canales_existentes,
                )
            )
            continue
        asignados = min(huecos, cantidad - len(plan))
        plan.extend([categoria] * asignados)
        if len(plan) == cantidad:
            return tuple(plan)

    raise ErrorSeleccionCategoriaComunidades(
        "CAPACIDAD_INSUFICIENTE",
        (
            f"Las categorías de {tipo} del torneo {torneo_id} no tienen "
            f"capacidad para {cantidad} canales nuevos (disponibles: {len(plan)})."
        ),
        torneo_id=torneo_id,
        tipo=tipo,
        incidencias=tuple(incidencias),
    )


async def seleccionar_categoria_comunidades(
    session: Any,
    guild: Any,
    *,
    torneo_id: int,
    tipo: str,
):
    """Elige la primera categoría configurada con menos de 40 canales."""
    try:
        return (
            await planificar_categorias_comunidades(
                session,
                guild,
                torneo_id=torneo_id,
                tipo=tipo,
                cantidad=1,
            )
        )[0]
    except ErrorSeleccionCategoriaComunidades as exc:
        if exc.codigo != "CAPACIDAD_INSUFICIENTE":
            raise
        raise ErrorSeleccionCategoriaComunidades(
            "SIN_CATEGORIA_UTILIZABLE",
            f"Ninguna categoría de {tipo} del torneo {torneo_id} tiene capacidad disponible.",
            torneo_id=torneo_id,
            tipo=tipo,
            incidencias=exc.incidencias,
        ) from exc


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
