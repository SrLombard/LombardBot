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


class ErrorMaterializacionDiscordComunidades(RuntimeError):
    """Incidencia recuperable durante la creación de canales individuales."""

    def __init__(self, codigo: str, detalle: str):
        super().__init__(detalle)
        self.codigo = codigo
        self.detalle = detalle


@dataclass(frozen=True)
class ResultadoMaterializacionDiscordComunidades:
    """Resultado idempotente de materializar los dos partidos en Discord."""

    enfrentamiento_id: int
    partido_ids: Tuple[int, int]
    canal_ids: Tuple[int, int]
    canales_creados: int


def _error_materializacion_discord(codigo: str, detalle: str) -> None:
    raise ErrorMaterializacionDiscordComunidades(codigo, detalle)


def _nombre_canal_partido_comunidades(enfrentamiento: Any, partido: Any) -> str:
    def normalizar(valor: object) -> str:
        texto = str(valor or "jugador").lower()
        resultado = []
        for caracter in texto:
            if caracter.isalnum():
                resultado.append(caracter)
            elif resultado and resultado[-1] != "-":
                resultado.append("-")
        return "".join(resultado).strip("-") or "jugador"

    return (
        f"r{int(enfrentamiento.ronda.numero)}-m{int(enfrentamiento.mesa_numero)}-"
        f"p{int(partido.indice)}-{normalizar(partido.usuario_local.nombre_discord)}-vs-"
        f"{normalizar(partido.usuario_visitante.nombre_discord)}"
    )[:100]


def _mensaje_partido_comunidades(enfrentamiento: Any, partido: Any) -> str:
    atacante_discord_id = int(partido.atacante_usuario.id_discord)
    defensor_discord_id = int(partido.defensor_usuario.id_discord)
    return (
        f"## Partido {int(partido.indice)} — Mesa {int(enfrentamiento.mesa_numero)}\n"
        f"**Atacante:** <@{atacante_discord_id}>\n"
        f"**Defensor:** <@{defensor_discord_id}>\n\n"
        f"<@{atacante_discord_id}> contra <@{defensor_discord_id}>\n"
        f"**Fecha límite:** {enfrentamiento.ronda.fecha_fin.strftime('%Y-%m-%d %H:%M')}"
    )


async def _resolver_miembro_comunidades(guild: Any, discord_id: int):
    miembro = guild.get_member(discord_id)
    if miembro is not None:
        return miembro
    fetch_member = getattr(guild, "fetch_member", None)
    if not callable(fetch_member):
        return None
    try:
        return await fetch_member(discord_id)
    except Exception:
        return None


async def _resolver_canal_comunidades(guild: Any, canal_id: int):
    canal = guild.get_channel(canal_id)
    if canal is not None:
        return canal
    fetch_channel = getattr(guild, "fetch_channel", None)
    if not callable(fetch_channel):
        return None
    try:
        return await fetch_channel(canal_id)
    except Exception:
        return None


async def materializar_partidos_comunidades(
    session: Any,
    guild: Any,
    *,
    enfrentamiento_id: int,
) -> ResultadoMaterializacionDiscordComunidades:
    """Crea de forma reintentable los dos registros y sus canales privados.

    Las identidades se confirman primero. Después cada canal se crea, recibe su
    mensaje y se asocia al partido en una confirmación independiente. Así, un
    fallo tras el primer canal deja un estado parcial visible y recuperable sin
    duplicar el canal ya guardado.
    """
    import discord
    from ComunidadesCore import materializar_identidades_partidos_comunidades
    from GestorSQL import ComunidadesEnfrentamiento, ComunidadesPartido

    try:
        materializar_identidades_partidos_comunidades(
            session, enfrentamiento_id=enfrentamiento_id
        )
        session.commit()
    except Exception:
        session.rollback()
        raise

    enfrentamiento = session.get(ComunidadesEnfrentamiento, enfrentamiento_id)
    partidos = (
        session.query(ComunidadesPartido)
        .filter(ComunidadesPartido.enfrentamiento_id == enfrentamiento_id)
        .order_by(ComunidadesPartido.indice)
        .all()
    )
    if enfrentamiento is None or len(partidos) != 2:
        _error_materializacion_discord(
            "IDENTIDADES_NO_DISPONIBLES",
            "No se pudieron recuperar las dos identidades persistidas.",
        )

    pendientes = [partido for partido in partidos if partido.canal_discord_id is None]
    if not pendientes:
        if enfrentamiento.estado != "PARTIDOS_CREADOS":
            enfrentamiento.estado = "PARTIDOS_CREADOS"
            session.commit()
        return ResultadoMaterializacionDiscordComunidades(
            enfrentamiento_id=enfrentamiento_id,
            partido_ids=(int(partidos[0].id), int(partidos[1].id)),
            canal_ids=(int(partidos[0].canal_discord_id), int(partidos[1].canal_discord_id)),
            canales_creados=0,
        )

    canal_general_id = enfrentamiento.canal_general_discord_id
    if canal_general_id is None:
        _error_materializacion_discord(
            "CANAL_GENERAL_NO_ASOCIADO",
            "El enfrentamiento no tiene un canal general asociado.",
        )
    canal_general = await _resolver_canal_comunidades(guild, int(canal_general_id))
    if canal_general is None:
        _error_materializacion_discord(
            "CANAL_GENERAL_INACCESIBLE",
            f"No se pudo acceder al canal general {int(canal_general_id)}.",
        )

    comisario_role = next(
        (rol for rol in getattr(guild, "roles", ()) if getattr(rol, "name", None) == "Comisario"),
        None,
    )
    if comisario_role is None:
        _error_materializacion_discord(
            "ROL_COMISARIO_INEXISTENTE",
            "No existe el rol Comisario necesario para configurar los permisos.",
        )

    miembros_por_partido = {}
    for partido in pendientes:
        miembros = []
        for usuario in (partido.usuario_local, partido.usuario_visitante):
            discord_id = getattr(usuario, "id_discord", None)
            if discord_id is None:
                _error_materializacion_discord(
                    "USUARIO_SIN_DISCORD",
                    f"El usuario BD {int(usuario.idUsuarios)} no tiene ID de Discord.",
                )
            miembro = await _resolver_miembro_comunidades(guild, int(discord_id))
            if miembro is None:
                _error_materializacion_discord(
                    "MIEMBRO_NO_ENCONTRADO",
                    f"No se encontró el usuario Discord {int(discord_id)} en el servidor.",
                )
            miembros.append(miembro)
        miembros_por_partido[int(partido.id)] = tuple(miembros)

    categorias = await planificar_categorias_comunidades(
        session,
        guild,
        torneo_id=int(enfrentamiento.torneo_id),
        tipo="partidos",
        cantidad=len(pendientes),
    )

    canales_creados = 0
    for partido, categoria in zip(pendientes, categorias):
        miembros = miembros_por_partido[int(partido.id)]
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(
                view_channel=False, read_messages=False
            ),
            comisario_role: discord.PermissionOverwrite(
                view_channel=True, read_messages=True, send_messages=True
            ),
        }
        for miembro in miembros:
            overwrites[miembro] = discord.PermissionOverwrite(
                view_channel=True, read_messages=True, send_messages=True
            )

        canal = None
        try:
            canal = await guild.create_text_channel(
                name=_nombre_canal_partido_comunidades(enfrentamiento, partido),
                category=categoria,
                overwrites=overwrites,
                reason=(
                    f"Torneo de comunidades, enfrentamiento {enfrentamiento_id}, "
                    f"partido {int(partido.indice)}"
                ),
            )
            await canal.send(_mensaje_partido_comunidades(enfrentamiento, partido))
            partido.canal_discord_id = int(canal.id)
            session.commit()
            canales_creados += 1
        except Exception as exc:
            session.rollback()
            limpieza = ""
            if canal is not None:
                try:
                    await canal.delete(reason="Fallo al materializar partido de comunidades")
                except Exception as error_limpieza:
                    limpieza = f"; no se pudo eliminar el canal huérfano ({error_limpieza})"
            _error_materializacion_discord(
                "FALLO_CREACION_CANAL",
                f"Falló el canal del partido {int(partido.indice)} ({exc}){limpieza}.",
            )

    session.expire_all()
    enfrentamiento = session.get(ComunidadesEnfrentamiento, enfrentamiento_id)
    partidos = (
        session.query(ComunidadesPartido)
        .filter(ComunidadesPartido.enfrentamiento_id == enfrentamiento_id)
        .order_by(ComunidadesPartido.indice)
        .all()
    )
    if len(partidos) == 2 and all(partido.canal_discord_id is not None for partido in partidos):
        enfrentamiento.estado = "PARTIDOS_CREADOS"
        session.commit()

    return ResultadoMaterializacionDiscordComunidades(
        enfrentamiento_id=enfrentamiento_id,
        partido_ids=(int(partidos[0].id), int(partidos[1].id)),
        canal_ids=(int(partidos[0].canal_discord_id), int(partidos[1].canal_discord_id)),
        canales_creados=canales_creados,
    )


def texto_discord_seguro_comunidades(valor: object) -> str:
    """Evita menciones accidentales al presentar nombres configurables."""
    return str(valor or "").replace("@", "@\u200b")


def mencion_usuario_comunidades(usuario: Any) -> str:
    """Construye una mención desde un usuario persistido por comunidades."""
    discord_id = getattr(usuario, "id_discord", None)
    if discord_id is None:
        return texto_discord_seguro_comunidades(
            getattr(usuario, "nombre_discord", "Jugador")
        )
    return f"<@{int(discord_id)}>"


def mensaje_eleccion_ephemeral_comunidades(resultado: Any) -> str:
    """Presenta únicamente al equipo que eligió sus identidades privadas."""
    return (
        f"**Equipo:** {texto_discord_seguro_comunidades(resultado.equipo_nombre)}\n"
        f"**Atacante:** {mencion_usuario_comunidades(resultado.atacante)}\n"
        f"**Defensor:** {mencion_usuario_comunidades(resultado.defensor)}"
    )


async def _responder_ephemeral_comunidades(interaction: Any, mensaje: str) -> None:
    respuesta = interaction.response
    if respuesta.is_done():
        await interaction.followup.send(mensaje, ephemeral=True)
    else:
        await respuesta.send_message(mensaje, ephemeral=True)


_MENSAJES_ERROR_SELECCION_COMUNIDADES = {
    "ENFRENTAMIENTO_NO_EXISTE": (
        "Este canal no corresponde al canal general de un enfrentamiento activo."
    ),
    "CANAL_ENFRENTAMIENTO_AMBIGUO": (
        "Este canal no permite identificar un único enfrentamiento activo."
    ),
    "ENFRENTAMIENTO_NO_ACTIVO": "El enfrentamiento de este canal no está activo.",
    "ACTOR_NO_PERTENECE": "No perteneces a ninguno de los equipos de este enfrentamiento.",
    "ATACANTE_NO_PERTENECE": "Solo puedes elegir a un miembro de tu propio equipo.",
    "EQUIPO_INCOMPLETO": "Tu equipo no tiene exactamente dos miembros configurados.",
    "ELECCIONES_BLOQUEADAS": "Las elecciones ya están completas y no se pueden modificar.",
}


def resolver_enfrentamiento_id_por_canal_comunidades(
    session: Any, canal_general_discord_id: int
) -> int:
    """Traduce el contexto Discord a una única referencia de dominio."""
    from ComunidadesCore import ErrorSeleccionAtacanteComunidades
    from GestorSQL import ComunidadesEnfrentamiento

    enfrentamientos = (
        session.query(ComunidadesEnfrentamiento.id)
        .filter(
            ComunidadesEnfrentamiento.canal_general_discord_id
            == canal_general_discord_id
        )
        .limit(2)
        .all()
    )
    if not enfrentamientos:
        raise ErrorSeleccionAtacanteComunidades(
            "ENFRENTAMIENTO_NO_EXISTE",
            "No existe un enfrentamiento asociado al canal indicado.",
        )
    if len(enfrentamientos) != 1:
        raise ErrorSeleccionAtacanteComunidades(
            "CANAL_ENFRENTAMIENTO_AMBIGUO",
            "El canal está asociado a más de un enfrentamiento.",
        )
    return int(enfrentamientos[0][0])


async def ejecutar_seleccion_atacante_comunidades(
    interaction: Any,
    usuario: Any,
    *,
    session_factory: Any,
    servicio_eleccion: Any = None,
    servicio_materializacion: Any = None,
    servicio_resolucion_enfrentamiento: Any = None,
    notificar_administracion: Any = None,
    elegido_en: Optional[datetime] = None,
) -> Optional[Any]:
    """Orquesta el slash command sin reproducir reglas de dominio.

    Cada servicio recibe una sesión independiente. La elección queda confirmada
    y su sesión se cierra antes de publicar en Discord o crear canales.
    """
    from ComunidadesCore import (
        ErrorSeleccionAtacanteComunidades,
        registrar_eleccion_atacante_comunidades,
    )

    if servicio_eleccion is None:
        servicio_eleccion = registrar_eleccion_atacante_comunidades
    if servicio_materializacion is None:
        servicio_materializacion = materializar_partidos_comunidades
    if servicio_resolucion_enfrentamiento is None:
        servicio_resolucion_enfrentamiento = resolver_enfrentamiento_id_por_canal_comunidades

    guild = getattr(interaction, "guild", None)
    channel = getattr(interaction, "channel", None)
    actor = getattr(interaction, "user", None)
    if guild is None or channel is None or actor is None:
        await _responder_ephemeral_comunidades(
            interaction, "Este comando solo puede utilizarse en el servidor."
        )
        return None

    session = session_factory()
    try:
        enfrentamiento_id = servicio_resolucion_enfrentamiento(
            session, int(channel.id)
        )
        resultado = servicio_eleccion(
            session,
            enfrentamiento_id=enfrentamiento_id,
            actor_discord_id=int(actor.id),
            atacante_discord_id=int(usuario.id),
            elegido_en=elegido_en,
        )
        enfrentamiento_id = int(resultado.eleccion.enfrentamiento_id)
        mensaje_privado = mensaje_eleccion_ephemeral_comunidades(resultado)
        mensaje_publico = (
            "El equipo "
            f"{texto_discord_seguro_comunidades(resultado.equipo_nombre)} "
            "ha elegido atacante"
        )
        requiere_materializacion = bool(resultado.requiere_crear_partidos)
    except ErrorSeleccionAtacanteComunidades as exc:
        await _responder_ephemeral_comunidades(
            interaction,
            _MENSAJES_ERROR_SELECCION_COMUNIDADES.get(
                exc.codigo, "No se pudo registrar la elección indicada."
            ),
        )
        return None
    except Exception as exc:
        try:
            session.rollback()
        finally:
            if notificar_administracion is not None:
                await notificar_administracion(
                    "Fallo al registrar una elección de comunidades "
                    f"en el canal `{int(channel.id)}` ({type(exc).__name__}: {exc})."
                )
        await _responder_ephemeral_comunidades(
            interaction, "No se pudo registrar la elección. Inténtalo de nuevo más tarde."
        )
        return None
    finally:
        session.close()

    try:
        await _responder_ephemeral_comunidades(interaction, mensaje_privado)
    except Exception as exc:
        if notificar_administracion is not None:
            await notificar_administracion(
                "La elección quedó persistida, pero falló la respuesta privada "
                f"del enfrentamiento `{enfrentamiento_id}` ({type(exc).__name__}: {exc})."
            )

    try:
        await channel.send(mensaje_publico)
    except Exception as exc:
        if notificar_administracion is not None:
            await notificar_administracion(
                "La elección quedó persistida, pero falló el aviso público "
                f"del enfrentamiento `{enfrentamiento_id}` ({type(exc).__name__}: {exc})."
            )

    if not requiere_materializacion:
        return resultado

    try:
        await channel.send("Se van a crear los encuentros")
    except Exception as exc:
        if notificar_administracion is not None:
            await notificar_administracion(
                "Las elecciones quedaron bloqueadas, pero falló el aviso previo "
                f"del enfrentamiento `{enfrentamiento_id}` ({type(exc).__name__}: {exc})."
            )

    session_materializacion = session_factory()
    try:
        materializacion = await servicio_materializacion(
            session_materializacion,
            guild,
            enfrentamiento_id=enfrentamiento_id,
        )
    except Exception as exc:
        session_materializacion.rollback()
        if notificar_administracion is not None:
            await notificar_administracion(
                "Las elecciones del enfrentamiento "
                f"`{enfrentamiento_id}` permanecen bloqueadas, pero la materialización "
                f"no se completó ({type(exc).__name__}: {exc})."
            )
        try:
            await _responder_ephemeral_comunidades(
                interaction,
                "La elección se guardó, pero no se pudieron crear todos los encuentros. "
                "La administración ha sido avisada.",
            )
        except Exception:
            pass
        return resultado
    finally:
        session_materializacion.close()

    canales = " y ".join(f"<#{int(canal_id)}>" for canal_id in materializacion.canal_ids)
    try:
        await channel.send(f"Encuentros creados: {canales}")
    except Exception as exc:
        if notificar_administracion is not None:
            await notificar_administracion(
                "Los encuentros del enfrentamiento "
                f"`{enfrentamiento_id}` se materializaron, pero falló su confirmación "
                f"pública ({type(exc).__name__}: {exc})."
            )
    return resultado
