"""Cálculos de resultados y clasificaciones del torneo de comunidades.

La resolución de marcadores y estados se mantiene pura. Las funciones de
clasificación consultan los modelos propios de comunidades mediante la sesión
recibida, sin depender de los modelos del torneo suizo individual.
"""

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import json
from enum import Enum
from functools import cmp_to_key
from typing import Any, Iterable, Optional

from sqlalchemy.exc import IntegrityError

from ComunidadesConstantes import (
    ESTADO_TEMPORAL_CAZADOR,
    ESTADO_TEMPORAL_CAZADOR_Z,
    ESTADO_TEMPORAL_HERIDO,
    ESTADO_TEMPORAL_NEUTRO,
    ENFRENTAMIENTO_ADMINISTRADO,
    ENFRENTAMIENTO_CERRADO,
    ENFRENTAMIENTO_ELECCIONES_COMPLETAS,
    ENFRENTAMIENTO_EN_CURSO,
    ENFRENTAMIENTO_PARTIDOS_CREADOS,
    ENFRENTAMIENTO_PENDIENTE_ELECCIONES,
    RESULTADO_ORIGEN_ADMIN,
    RESULTADO_ORIGEN_API,
    PARTIDO_ADMINISTRADO,
    PARTIDO_FINALIZADO,
    TIPO_FORFAIT_DOBLE,
    TIPOS_FORFAIT,
    PLANTILLA_RONDA1_PENDIENTE,
    PLANTILLA_RONDAS_SIGUIENTES_PENDIENTE,
    RAZAS_VALIDAS,
    RONDA_ABIERTA,
    TORNEO_CREADO,
    TORNEO_EN_CURSO,
    validar_puntuacion,
)


def reservar_operacion_idempotente_comunidades(
    session: Any,
    *,
    clave: str,
    tipo: str,
    torneo_id: int,
    ronda_id: Optional[int] = None,
    enfrentamiento_id: Optional[int] = None,
    partido_id: Optional[int] = None,
    lease_segundos: int = 300,
) -> bool:
    """Reserva una operación externa; permite recuperar leases abandonados."""
    from GestorSQL import ComunidadesOperacionIdempotente

    ahora = datetime.now(timezone.utc).replace(tzinfo=None)
    operacion = (
        session.query(ComunidadesOperacionIdempotente)
        .filter(ComunidadesOperacionIdempotente.clave == clave)
        .with_for_update()
        .one_or_none()
    )
    if operacion is None:
        try:
            with session.begin_nested():
                session.add(
                    ComunidadesOperacionIdempotente(
                        clave=clave,
                        tipo=tipo,
                        torneo_id=torneo_id,
                        ronda_id=ronda_id,
                        enfrentamiento_id=enfrentamiento_id,
                        partido_id=partido_id,
                    )
                )
                session.flush()
            return True
        except IntegrityError:
            operacion = (
                session.query(ComunidadesOperacionIdempotente)
                .filter(ComunidadesOperacionIdempotente.clave == clave)
                .with_for_update()
                .one()
            )
    if operacion.estado == "COMPLETADA":
        return False
    actualizado = operacion.updated_at or operacion.created_at or ahora
    if ahora - actualizado < timedelta(seconds=lease_segundos):
        return False
    operacion.updated_at = ahora
    operacion.tipo = tipo
    operacion.torneo_id = torneo_id
    operacion.ronda_id = ronda_id
    operacion.enfrentamiento_id = enfrentamiento_id
    operacion.partido_id = partido_id
    session.flush()
    return True


def completar_operacion_idempotente_comunidades(
    session: Any, *, clave: str, recurso_externo_id: Optional[object] = None
) -> None:
    from GestorSQL import ComunidadesOperacionIdempotente

    operacion = (
        session.query(ComunidadesOperacionIdempotente)
        .filter(ComunidadesOperacionIdempotente.clave == clave)
        .with_for_update()
        .one()
    )
    operacion.estado = "COMPLETADA"
    operacion.recurso_externo_id = (
        None if recurso_externo_id is None else str(recurso_externo_id)
    )
    session.flush()


def liberar_operacion_idempotente_comunidades(session: Any, *, clave: str) -> None:
    """Libera solo reservas pendientes para que el siguiente reintento continúe."""
    from GestorSQL import ComunidadesOperacionIdempotente

    session.query(ComunidadesOperacionIdempotente).filter(
        ComunidadesOperacionIdempotente.clave == clave,
        ComunidadesOperacionIdempotente.estado == "PENDIENTE",
    ).delete(synchronize_session=False)
    session.flush()


class ErrorConfiguracionComunidades(ValueError):
    """Error de dominio legible para configurar un torneo de comunidades."""

    def __init__(self, codigo: str, detalle: str):
        super().__init__(detalle)
        self.codigo = codigo
        self.detalle = detalle


def _error_configuracion(codigo: str, detalle: str) -> None:
    raise ErrorConfiguracionComunidades(codigo, detalle)


def _validar_entero_positivo(valor: object, nombre: str) -> int:
    if type(valor) is not int or valor <= 0:
        _error_configuracion("VALOR_INVALIDO", f"{nombre} debe ser un entero mayor que 0.")
    return valor


def _normalizar_puntuacion(valor: object, nombre: str) -> Decimal:
    if not validar_puntuacion(valor):
        _error_configuracion(
            "PUNTUACION_INVALIDA",
            f"{nombre} debe ser un decimal entre 0 y 9999.99 con un máximo de dos decimales.",
        )
    return Decimal(str(valor))


def _obtener_torneo_configurable(session: Any, torneo_id: int):
    from GestorSQL import ComunidadesTorneo

    _validar_entero_positivo(torneo_id, "torneo_id")
    torneo = session.query(ComunidadesTorneo).filter(ComunidadesTorneo.id == torneo_id).first()
    if torneo is None:
        _error_configuracion(
            "TORNEO_NO_EXISTE", f"No existe un torneo de comunidades con ID {torneo_id}."
        )
    if torneo.estado != TORNEO_CREADO:
        _error_configuracion(
            "TORNEO_INICIADO",
            "La configuración solo puede modificarse mientras el torneo está en estado CREADO.",
        )
    return torneo


def crear_torneo_comunidades(
    session: Any,
    *,
    nombre: str,
    rondas_totales: int,
    fecha_fin_ronda1: datetime,
    dias_por_ronda: int,
    canal_hub_id: int,
    creado_por_discord_id: int,
):
    """Crea, sin confirmar la transacción, un torneo con valores iniciales seguros."""
    from GestorSQL import ComunidadesTorneo

    if not isinstance(nombre, str) or not nombre.strip():
        _error_configuracion("NOMBRE_INVALIDO", "El nombre del torneo no puede estar vacío.")
    nombre = nombre.strip()
    if len(nombre) > 120:
        _error_configuracion("NOMBRE_INVALIDO", "El nombre del torneo no puede superar 120 caracteres.")
    _validar_entero_positivo(rondas_totales, "rondas_totales")
    if not isinstance(fecha_fin_ronda1, datetime):
        _error_configuracion("FECHA_INVALIDA", "fecha_fin_ronda1 debe ser una fecha y hora válidas.")
    _validar_entero_positivo(dias_por_ronda, "dias_por_ronda")
    _validar_entero_positivo(canal_hub_id, "canal_hub_id")
    _validar_entero_positivo(creado_por_discord_id, "creado_por_discord_id")

    torneo = ComunidadesTorneo(
        nombre=nombre,
        estado=TORNEO_CREADO,
        rondas_totales=rondas_totales,
        fecha_fin_ronda1=fecha_fin_ronda1,
        dias_por_ronda=dias_por_ronda,
        canal_hub_id=canal_hub_id,
        plantilla_mensaje_ronda1=PLANTILLA_RONDA1_PENDIENTE,
        plantilla_mensaje_rondas_siguientes=PLANTILLA_RONDAS_SIGUIENTES_PENDIENTE,
        creado_por_discord_id=creado_por_discord_id,
    )
    session.add(torneo)
    session.flush()
    return torneo


def _validar_texto_alta(valor: object, nombre: str, longitud_maxima: int = 120) -> str:
    if not isinstance(valor, str) or not valor.strip():
        _error_configuracion("VALOR_INVALIDO", f"{nombre} no puede estar vacío.")
    if valor != valor.strip():
        _error_configuracion(
            "VALOR_INVALIDO", f"{nombre} no puede tener espacios al principio o al final."
        )
    if len(valor) > longitud_maxima:
        _error_configuracion(
            "VALOR_INVALIDO", f"{nombre} no puede superar {longitud_maxima} caracteres."
        )
    return valor


def _validar_discord_id(valor: object, nombre: str) -> int:
    if type(valor) is not int or valor <= 0:
        _error_configuracion("VALOR_INVALIDO", f"{nombre} debe ser un ID de Discord válido.")
    return valor


def anadir_comunidad_comunidades(session: Any, *, torneo_id: int, nombre: str):
    """Añade una comunidad sin confirmar la transacción de la sesión."""
    from GestorSQL import ComunidadesComunidad

    torneo = _obtener_torneo_configurable(session, torneo_id)
    nombre = _validar_texto_alta(nombre, "nombre")
    duplicada = (
        session.query(ComunidadesComunidad.id)
        .filter(
            ComunidadesComunidad.torneo_id == torneo.id,
            ComunidadesComunidad.nombre == nombre,
        )
        .first()
    )
    if duplicada is not None:
        _error_configuracion(
            "COMUNIDAD_DUPLICADA",
            f"La comunidad `{nombre}` ya existe en el torneo {torneo.id}.",
        )

    comunidad = ComunidadesComunidad(torneo_id=torneo.id, nombre=nombre)
    session.add(comunidad)
    session.flush()
    return comunidad


def _anadir_categoria_comunidades(
    session: Any, *, torneo_id: int, categoria_discord_id: int, modelo: Any, tipo: str
):
    torneo = _obtener_torneo_configurable(session, torneo_id)
    categoria_discord_id = _validar_discord_id(categoria_discord_id, "categoria_id")
    duplicada = (
        session.query(modelo.id)
        .filter(
            modelo.torneo_id == torneo.id,
            modelo.categoria_discord_id == categoria_discord_id,
        )
        .first()
    )
    if duplicada is not None:
        _error_configuracion(
            "CATEGORIA_DUPLICADA",
            f"La categoría de {tipo} {categoria_discord_id} ya está configurada en el torneo {torneo.id}.",
        )

    ultimo_orden = (
        session.query(modelo.orden_alta)
        .filter(modelo.torneo_id == torneo.id)
        .order_by(modelo.orden_alta.desc())
        .first()
    )
    categoria = modelo(
        torneo_id=torneo.id,
        categoria_discord_id=categoria_discord_id,
        orden_alta=1 if ultimo_orden is None else ultimo_orden[0] + 1,
    )
    session.add(categoria)
    session.flush()
    return categoria


def anadir_categoria_partidos_comunidades(
    session: Any, *, torneo_id: int, categoria_discord_id: int
):
    """Añade una categoría de partidos conservando el orden de alta."""
    from GestorSQL import ComunidadesCategoriaPartido

    return _anadir_categoria_comunidades(
        session,
        torneo_id=torneo_id,
        categoria_discord_id=categoria_discord_id,
        modelo=ComunidadesCategoriaPartido,
        tipo="partidos",
    )


def anadir_categoria_enfrentamientos_comunidades(
    session: Any, *, torneo_id: int, categoria_discord_id: int
):
    """Añade una categoría de enfrentamientos conservando el orden de alta."""
    from GestorSQL import ComunidadesCategoriaEnfrentamiento

    return _anadir_categoria_comunidades(
        session,
        torneo_id=torneo_id,
        categoria_discord_id=categoria_discord_id,
        modelo=ComunidadesCategoriaEnfrentamiento,
        tipo="enfrentamientos",
    )


def obtener_categorias_comunidades(session: Any, *, torneo_id: int, tipo: str):
    """Devuelve las categorías configuradas del tipo indicado en orden de alta."""
    from GestorSQL import (
        ComunidadesCategoriaEnfrentamiento,
        ComunidadesCategoriaPartido,
        ComunidadesTorneo,
    )

    _validar_entero_positivo(torneo_id, "torneo_id")
    torneo_existe = (
        session.query(ComunidadesTorneo.id)
        .filter(ComunidadesTorneo.id == torneo_id)
        .first()
    )
    if torneo_existe is None:
        _error_configuracion(
            "TORNEO_NO_EXISTE",
            f"No existe un torneo de comunidades con ID {torneo_id}.",
        )

    modelos = {
        "enfrentamientos": ComunidadesCategoriaEnfrentamiento,
        "partidos": ComunidadesCategoriaPartido,
    }
    modelo = modelos.get(tipo)
    if modelo is None:
        _error_configuracion(
            "TIPO_CATEGORIA_INVALIDO",
            "El tipo de categoría debe ser 'enfrentamientos' o 'partidos'.",
        )

    return (
        session.query(modelo)
        .filter(modelo.torneo_id == torneo_id)
        .order_by(modelo.orden_alta.asc())
        .all()
    )


def anadir_equipo_comunidades(
    session: Any,
    *,
    torneo_id: int,
    nombre: str,
    comunidad_nombre: str,
    jugador1_discord_id: int,
    jugador1_nombre_discord: str,
    raza1: str,
    jugador2_discord_id: int,
    jugador2_nombre_discord: str,
    raza2: str,
):
    """Inscribe atómicamente un equipo y crea los usuarios que no existan.

    La función hace ``flush`` para validar y devolver IDs, pero deja el ``commit``
    o ``rollback`` al llamador, que actúa como frontera transaccional.
    """
    from GestorSQL import (
        ComunidadesComunidad,
        ComunidadesEquipo,
        ComunidadesMiembro,
        Usuario,
    )

    torneo = _obtener_torneo_configurable(session, torneo_id)
    nombre = _validar_texto_alta(nombre, "nombre_equipo")
    comunidad_nombre = _validar_texto_alta(comunidad_nombre, "comunidad")
    jugador1_discord_id = _validar_discord_id(jugador1_discord_id, "jugador1")
    jugador2_discord_id = _validar_discord_id(jugador2_discord_id, "jugador2")
    jugador1_nombre_discord = _validar_texto_alta(
        jugador1_nombre_discord, "nombre Discord del jugador 1", 255
    )
    jugador2_nombre_discord = _validar_texto_alta(
        jugador2_nombre_discord, "nombre Discord del jugador 2", 255
    )
    if jugador1_discord_id == jugador2_discord_id:
        _error_configuracion(
            "MIEMBROS_REPETIDOS", "Un equipo debe contener dos usuarios distintos."
        )
    for raza, campo in ((raza1, "raza1"), (raza2, "raza2")):
        if raza not in RAZAS_VALIDAS:
            _error_configuracion(
                "RAZA_INVALIDA",
                f"{campo} debe coincidir exactamente con una raza válida: `{raza}` no es válida.",
            )

    comunidad = (
        session.query(ComunidadesComunidad)
        .filter(
            ComunidadesComunidad.torneo_id == torneo.id,
            ComunidadesComunidad.nombre == comunidad_nombre,
        )
        .first()
    )
    if comunidad is None:
        _error_configuracion(
            "COMUNIDAD_NO_EXISTE",
            f"La comunidad `{comunidad_nombre}` no existe en el torneo {torneo.id}.",
        )
    if (
        session.query(ComunidadesEquipo.id)
        .filter(ComunidadesEquipo.torneo_id == torneo.id, ComunidadesEquipo.nombre == nombre)
        .first()
        is not None
    ):
        _error_configuracion(
            "EQUIPO_DUPLICADO", f"El equipo `{nombre}` ya existe en el torneo {torneo.id}."
        )

    usuarios = []
    for discord_id, nombre_discord in (
        (jugador1_discord_id, jugador1_nombre_discord),
        (jugador2_discord_id, jugador2_nombre_discord),
    ):
        usuario = session.query(Usuario).filter(Usuario.id_discord == discord_id).first()
        if usuario is not None:
            inscrito = (
                session.query(ComunidadesMiembro.id)
                .filter(
                    ComunidadesMiembro.torneo_id == torneo.id,
                    ComunidadesMiembro.usuario_id == usuario.idUsuarios,
                )
                .first()
            )
            if inscrito is not None:
                _error_configuracion(
                    "USUARIO_YA_INSCRITO",
                    f"El usuario Discord {discord_id} ya pertenece a otro equipo del torneo {torneo.id}.",
                )
        usuarios.append((usuario, discord_id, nombre_discord))

    for indice, (usuario, discord_id, nombre_discord) in enumerate(usuarios):
        if usuario is None:
            usuario = Usuario(
                id_discord=discord_id,
                nombre_discord=nombre_discord,
                id_bloodbowl=None,
                nombre_bloodbowl=None,
            )
            session.add(usuario)
            session.flush()
            usuarios[indice] = (usuario, discord_id, nombre_discord)

    equipo = ComunidadesEquipo(
        torneo_id=torneo.id, comunidad_id=comunidad.id, nombre=nombre
    )
    session.add(equipo)
    session.flush()
    session.add_all(
        [
            ComunidadesMiembro(
                torneo_id=torneo.id,
                equipo_id=equipo.id,
                usuario_id=usuarios[0][0].idUsuarios,
                raza=raza1,
                posicion=1,
            ),
            ComunidadesMiembro(
                torneo_id=torneo.id,
                equipo_id=equipo.id,
                usuario_id=usuarios[1][0].idUsuarios,
                raza=raza2,
                posicion=2,
            ),
        ]
    )
    session.flush()
    return equipo


def configurar_competicion_comunidades(session: Any, *, torneo_id: int, id_competicion_bbowl: str):
    """Guarda el ID de competición mientras el torneo siga sin iniciar."""
    torneo = _obtener_torneo_configurable(session, torneo_id)
    valor = str(id_competicion_bbowl).strip() if id_competicion_bbowl is not None else ""
    if not valor or len(valor) > 45:
        _error_configuracion(
            "COMPETICION_INVALIDA",
            "idCompBbowl debe tener entre 1 y 45 caracteres.",
        )
    torneo.id_competicion_bbowl = valor
    session.flush()
    return torneo


def configurar_puntos_equipo_comunidades(
    session: Any, *, torneo_id: int, victoria: object, empate: object, derrota: object, bye: object
):
    """Configura exclusivamente la puntuación de clasificación por equipos."""
    torneo = _obtener_torneo_configurable(session, torneo_id)
    valores = {
        "victoria": _normalizar_puntuacion(victoria, "win"),
        "empate": _normalizar_puntuacion(empate, "draw"),
        "derrota": _normalizar_puntuacion(derrota, "loss"),
        "bye": _normalizar_puntuacion(bye, "bye"),
    }
    if not valores["victoria"] > valores["empate"] >= valores["derrota"]:
        _error_configuracion("PUNTUACION_INVALIDA", "Debe cumplirse win > draw >= loss.")
    torneo.puntos_clasificacion_victoria = valores["victoria"]
    torneo.puntos_clasificacion_empate = valores["empate"]
    torneo.puntos_clasificacion_derrota = valores["derrota"]
    torneo.puntos_clasificacion_bye = valores["bye"]
    session.flush()
    return torneo


def configurar_puntos_individuales_comunidades(
    session: Any, *, torneo_id: int, victoria: object, empate: object, derrota: object
):
    """Configura exclusivamente los puntos internos de los partidos BO1."""
    torneo = _obtener_torneo_configurable(session, torneo_id)
    valores = {
        "victoria": _normalizar_puntuacion(victoria, "win"),
        "empate": _normalizar_puntuacion(empate, "draw"),
        "derrota": _normalizar_puntuacion(derrota, "loss"),
    }
    if not valores["victoria"] > valores["empate"] >= valores["derrota"]:
        _error_configuracion("PUNTUACION_INVALIDA", "Debe cumplirse win > draw >= loss.")
    torneo.puntos_individuales_victoria = valores["victoria"]
    torneo.puntos_individuales_empate = valores["empate"]
    torneo.puntos_individuales_derrota = valores["derrota"]
    session.flush()
    return torneo


class Equipo(str, Enum):
    """Lado de un equipo dentro de un enfrentamiento."""

    A = "A"
    B = "B"


class ResultadoGlobal(str, Enum):
    """Resultado final del enfrentamiento desde la perspectiva del equipo A."""

    VICTORIA_A = "VICTORIA_A"
    VICTORIA_B = "VICTORIA_B"
    EMPATE = "EMPATE"


class EstadoTemporal(str, Enum):
    """Estado temporal canónico fotografiado para un equipo."""

    NEUTRO = ESTADO_TEMPORAL_NEUTRO
    CAZADOR = ESTADO_TEMPORAL_CAZADOR
    CAZADOR_Z = ESTADO_TEMPORAL_CAZADOR_Z
    HERIDO = ESTADO_TEMPORAL_HERIDO


class MotivoTransicion(str, Enum):
    """Motivo persistible que explica la transición de un equipo."""

    VICTORIA = "VICTORIA"
    DERROTA = "DERROTA"
    EMPATE = "EMPATE"
    ZOMBIFICACION = "ZOMBIFICACION"
    KILL = "KILL"
    DOBLE_FORFAIT = "DOBLE_FORFAIT"


@dataclass(frozen=True)
class EstadoFotografiado:
    """Estado inmutable de un equipo al generarse la ronda."""

    estado_temporal: EstadoTemporal
    es_zombie: bool

    def __post_init__(self) -> None:
        try:
            estado = EstadoTemporal(self.estado_temporal)
        except (TypeError, ValueError) as exc:
            raise ValueError("estado temporal fotografiado desconocido") from exc
        if type(self.es_zombie) is not bool:
            raise TypeError("es_zombie debe ser booleano")
        object.__setattr__(self, "estado_temporal", estado)


@dataclass(frozen=True)
class EfectoComunitario:
    """Efecto especial concedido al equipo y comunidad vencedores."""

    equipo: Equipo
    comunidad: object

    def __post_init__(self) -> None:
        object.__setattr__(self, "equipo", Equipo(self.equipo))
        if self.comunidad is None:
            raise ValueError("la comunidad beneficiaria no puede ser None")


@dataclass(frozen=True)
class TransicionEstados:
    """Resultado completo de aplicar la máquina de estados a un cruce."""

    estado_final_a: EstadoFotografiado
    estado_final_b: EstadoFotografiado
    cambio_zombie_a: bool
    cambio_zombie_b: bool
    punto_zombificacion: EfectoComunitario | None
    kill: EfectoComunitario | None
    motivo_a: MotivoTransicion
    motivo_b: MotivoTransicion

    def __post_init__(self) -> None:
        if not isinstance(self.estado_final_a, EstadoFotografiado):
            raise TypeError("estado_final_a debe ser EstadoFotografiado")
        if not isinstance(self.estado_final_b, EstadoFotografiado):
            raise TypeError("estado_final_b debe ser EstadoFotografiado")
        if (
            type(self.cambio_zombie_a) is not bool
            or type(self.cambio_zombie_b) is not bool
        ):
            raise TypeError("los cambios zombie deben ser booleanos")
        if self.punto_zombificacion is not None and not isinstance(
            self.punto_zombificacion, EfectoComunitario
        ):
            raise TypeError("punto_zombificacion debe ser EfectoComunitario o None")
        if self.kill is not None and not isinstance(self.kill, EfectoComunitario):
            raise TypeError("kill debe ser EfectoComunitario o None")
        object.__setattr__(self, "motivo_a", MotivoTransicion(self.motivo_a))
        object.__setattr__(self, "motivo_b", MotivoTransicion(self.motivo_b))


class CriterioDesempate(str, Enum):
    """Criterio que determinó el resultado global."""

    PUNTOS_INTERNOS = "PUNTOS_INTERNOS"
    TD_ATACANTE = "TD_ATACANTE"
    DIFERENCIA_TD = "DIFERENCIA_TD"
    EMPATE_DEFINITIVO = "EMPATE_DEFINITIVO"


@dataclass(frozen=True)
class ConfiguracionPuntosIndividuales:
    """Puntos internos otorgados por cada resultado de un BO1."""

    victoria: Decimal
    empate: Decimal
    derrota: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "victoria", _decimal_no_negativo(self.victoria, "victoria")
        )
        object.__setattr__(self, "empate", _decimal_no_negativo(self.empate, "empate"))
        object.__setattr__(
            self, "derrota", _decimal_no_negativo(self.derrota, "derrota")
        )


@dataclass(frozen=True)
class ConfiguracionPuntosClasificacion:
    """Puntos de clasificación otorgados por el resultado global."""

    victoria: Decimal
    empate: Decimal
    derrota: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "victoria", _decimal_no_negativo(self.victoria, "victoria")
        )
        object.__setattr__(self, "empate", _decimal_no_negativo(self.empate, "empate"))
        object.__setattr__(
            self, "derrota", _decimal_no_negativo(self.derrota, "derrota")
        )


@dataclass(frozen=True)
class MarcadorPartido:
    """Marcador de un BO1 orientado a los lados A/B del enfrentamiento."""

    td_a: int
    td_b: int
    equipo_atacante: Equipo

    def __post_init__(self) -> None:
        _validar_td(self.td_a, "td_a")
        _validar_td(self.td_b, "td_b")
        object.__setattr__(self, "equipo_atacante", _equipo(self.equipo_atacante))


@dataclass(frozen=True)
class PuntosInternosPartido:
    """Puntos internos que un partido concede a los equipos A y B."""

    puntos_a: Decimal
    puntos_b: Decimal


@dataclass(frozen=True)
class TotalesTouchdowns:
    """TD agregados de la serie y sus diferencias por equipo."""

    td_favor_a: int
    td_contra_a: int
    td_favor_b: int
    td_contra_b: int
    diferencia_a: int
    diferencia_b: int


@dataclass(frozen=True)
class DecisionGlobal:
    """Ganador global y criterio que decidió el enfrentamiento."""

    resultado: ResultadoGlobal
    ganador: Equipo | None
    criterio: CriterioDesempate


@dataclass(frozen=True)
class ResultadoEnfrentamiento:
    """Valores calculados necesarios para persistencia y presentación."""

    puntos_internos_a: Decimal
    puntos_internos_b: Decimal
    td_favor_a: int
    td_contra_a: int
    td_favor_b: int
    td_contra_b: int
    diferencia_td_a: int
    diferencia_td_b: int
    td_atacante_a: int
    td_atacante_b: int
    resultado: ResultadoGlobal
    ganador: Equipo | None
    criterio_desempate: CriterioDesempate
    puntos_clasificacion_a: Decimal
    puntos_clasificacion_b: Decimal


def _decimal_no_negativo(valor: object, nombre: str) -> Decimal:
    if isinstance(valor, bool):
        raise TypeError(f"{nombre} debe ser un número decimal")
    try:
        decimal = valor if isinstance(valor, Decimal) else Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise TypeError(f"{nombre} debe ser un número decimal") from exc
    if not decimal.is_finite() or decimal < 0:
        raise ValueError(f"{nombre} debe ser finito y no negativo")
    return decimal


def _validar_td(valor: object, nombre: str) -> None:
    if type(valor) is not int:
        raise TypeError(f"{nombre} debe ser un entero")
    if valor < 0:
        raise ValueError(f"{nombre} no puede ser negativo")


def _equipo(valor: Equipo | str) -> Equipo:
    try:
        return Equipo(valor)
    except (TypeError, ValueError) as exc:
        raise ValueError("equipo_atacante debe ser Equipo.A o Equipo.B") from exc


def convertir_marcador_en_puntos_internos(
    td_a: int,
    td_b: int,
    configuracion: ConfiguracionPuntosIndividuales,
) -> PuntosInternosPartido:
    """Convierte el marcador de un BO1 en puntos internos para A y B."""
    _validar_td(td_a, "td_a")
    _validar_td(td_b, "td_b")
    if not isinstance(configuracion, ConfiguracionPuntosIndividuales):
        raise TypeError("configuracion debe ser ConfiguracionPuntosIndividuales")

    if td_a > td_b:
        return PuntosInternosPartido(configuracion.victoria, configuracion.derrota)
    if td_b > td_a:
        return PuntosInternosPartido(configuracion.derrota, configuracion.victoria)
    return PuntosInternosPartido(configuracion.empate, configuracion.empate)


def sumar_puntos_internos(
    puntos_partidos: Iterable[PuntosInternosPartido],
) -> PuntosInternosPartido:
    """Suma los puntos internos de los dos BO1 del enfrentamiento."""
    puntos = tuple(puntos_partidos)
    if len(puntos) != 2:
        raise ValueError("un enfrentamiento debe contener exactamente dos partidos")
    if any(not isinstance(partido, PuntosInternosPartido) for partido in puntos):
        raise TypeError("todos los elementos deben ser PuntosInternosPartido")
    return PuntosInternosPartido(
        sum((partido.puntos_a for partido in puntos), Decimal("0")),
        sum((partido.puntos_b for partido in puntos), Decimal("0")),
    )


def identificar_td_atacantes(
    partidos: Iterable[MarcadorPartido],
) -> tuple[int, int]:
    """Devuelve los TD de los atacantes A y B en sus respectivos BO1."""
    marcadores = _validar_partidos(partidos)
    por_atacante = {partido.equipo_atacante: partido for partido in marcadores}
    if set(por_atacante) != {Equipo.A, Equipo.B}:
        raise ValueError("debe existir un partido del atacante A y otro del atacante B")
    return por_atacante[Equipo.A].td_a, por_atacante[Equipo.B].td_b


def calcular_td_globales(partidos: Iterable[MarcadorPartido]) -> TotalesTouchdowns:
    """Calcula TD a favor, en contra y diferencia global de ambos equipos."""
    marcadores = _validar_partidos(partidos)
    td_favor_a = sum(partido.td_a for partido in marcadores)
    td_favor_b = sum(partido.td_b for partido in marcadores)
    return TotalesTouchdowns(
        td_favor_a=td_favor_a,
        td_contra_a=td_favor_b,
        td_favor_b=td_favor_b,
        td_contra_b=td_favor_a,
        diferencia_a=td_favor_a - td_favor_b,
        diferencia_b=td_favor_b - td_favor_a,
    )


def _validar_partidos(
    partidos: Iterable[MarcadorPartido],
) -> tuple[MarcadorPartido, MarcadorPartido]:
    marcadores = tuple(partidos)
    if len(marcadores) != 2:
        raise ValueError("un enfrentamiento debe contener exactamente dos partidos")
    if any(not isinstance(partido, MarcadorPartido) for partido in marcadores):
        raise TypeError("todos los elementos deben ser MarcadorPartido")
    return marcadores[0], marcadores[1]


def decidir_resultado_global(
    puntos_a: Decimal,
    puntos_b: Decimal,
    td_atacante_a: int,
    td_atacante_b: int,
    diferencia_td_a: int,
    diferencia_td_b: int,
) -> DecisionGlobal:
    """Aplica en orden puntos internos, TD atacante y diferencia global de TD."""
    puntos_a = _decimal_no_negativo(puntos_a, "puntos_a")
    puntos_b = _decimal_no_negativo(puntos_b, "puntos_b")
    _validar_td(td_atacante_a, "td_atacante_a")
    _validar_td(td_atacante_b, "td_atacante_b")
    if type(diferencia_td_a) is not int or type(diferencia_td_b) is not int:
        raise TypeError("las diferencias de TD deben ser enteros")

    comparaciones = (
        (puntos_a, puntos_b, CriterioDesempate.PUNTOS_INTERNOS),
        (td_atacante_a, td_atacante_b, CriterioDesempate.TD_ATACANTE),
        (diferencia_td_a, diferencia_td_b, CriterioDesempate.DIFERENCIA_TD),
    )
    for valor_a, valor_b, criterio in comparaciones:
        if valor_a > valor_b:
            return DecisionGlobal(ResultadoGlobal.VICTORIA_A, Equipo.A, criterio)
        if valor_b > valor_a:
            return DecisionGlobal(ResultadoGlobal.VICTORIA_B, Equipo.B, criterio)
    return DecisionGlobal(
        ResultadoGlobal.EMPATE,
        None,
        CriterioDesempate.EMPATE_DEFINITIVO,
    )


def asignar_puntos_clasificacion(
    resultado: ResultadoGlobal,
    configuracion: ConfiguracionPuntosClasificacion,
) -> tuple[Decimal, Decimal]:
    """Asigna puntos de clasificación sin reutilizar los puntos internos."""
    if not isinstance(configuracion, ConfiguracionPuntosClasificacion):
        raise TypeError("configuracion debe ser ConfiguracionPuntosClasificacion")
    try:
        resultado = ResultadoGlobal(resultado)
    except (TypeError, ValueError) as exc:
        raise ValueError("resultado global desconocido") from exc

    if resultado is ResultadoGlobal.VICTORIA_A:
        return configuracion.victoria, configuracion.derrota
    if resultado is ResultadoGlobal.VICTORIA_B:
        return configuracion.derrota, configuracion.victoria
    return configuracion.empate, configuracion.empate


def calcular_resultado_enfrentamiento(
    partidos: Iterable[MarcadorPartido],
    puntos_individuales: ConfiguracionPuntosIndividuales,
    puntos_clasificacion: ConfiguracionPuntosClasificacion,
) -> ResultadoEnfrentamiento:
    """Calcula íntegramente y de forma determinista un enfrentamiento."""
    marcadores = _validar_partidos(partidos)
    puntos_por_partido = tuple(
        convertir_marcador_en_puntos_internos(
            partido.td_a,
            partido.td_b,
            puntos_individuales,
        )
        for partido in marcadores
    )
    puntos_totales = sumar_puntos_internos(puntos_por_partido)
    td_atacante_a, td_atacante_b = identificar_td_atacantes(marcadores)
    touchdowns = calcular_td_globales(marcadores)
    decision = decidir_resultado_global(
        puntos_totales.puntos_a,
        puntos_totales.puntos_b,
        td_atacante_a,
        td_atacante_b,
        touchdowns.diferencia_a,
        touchdowns.diferencia_b,
    )
    clasificacion_a, clasificacion_b = asignar_puntos_clasificacion(
        decision.resultado,
        puntos_clasificacion,
    )
    return ResultadoEnfrentamiento(
        puntos_internos_a=puntos_totales.puntos_a,
        puntos_internos_b=puntos_totales.puntos_b,
        td_favor_a=touchdowns.td_favor_a,
        td_contra_a=touchdowns.td_contra_a,
        td_favor_b=touchdowns.td_favor_b,
        td_contra_b=touchdowns.td_contra_b,
        diferencia_td_a=touchdowns.diferencia_a,
        diferencia_td_b=touchdowns.diferencia_b,
        td_atacante_a=td_atacante_a,
        td_atacante_b=td_atacante_b,
        resultado=decision.resultado,
        ganador=decision.ganador,
        criterio_desempate=decision.criterio,
        puntos_clasificacion_a=clasificacion_a,
        puntos_clasificacion_b=clasificacion_b,
    )


def resolver_transicion_estados(
    estado_inicial_a: EstadoFotografiado,
    estado_inicial_b: EstadoFotografiado,
    resultado_global: ResultadoGlobal,
    doble_forfait: bool,
    comunidad_a: object,
    comunidad_b: object,
) -> TransicionEstados:
    """Resuelve exhaustivamente la sección 12 desde la fotografía inicial.

    La función no consulta estados vivos: tanto las transiciones ordinarias como
    los efectos especiales se calculan exclusivamente con los dos estados
    fotografiados recibidos.
    """
    _validar_entrada_transicion(
        estado_inicial_a,
        estado_inicial_b,
        resultado_global,
        doble_forfait,
        comunidad_a,
        comunidad_b,
    )
    resultado = ResultadoGlobal(resultado_global)

    if doble_forfait:
        transicion = TransicionEstados(
            estado_final_a=estado_inicial_a,
            estado_final_b=estado_inicial_b,
            cambio_zombie_a=False,
            cambio_zombie_b=False,
            punto_zombificacion=None,
            kill=None,
            motivo_a=MotivoTransicion.DOBLE_FORFAIT,
            motivo_b=MotivoTransicion.DOBLE_FORFAIT,
        )
    elif resultado is ResultadoGlobal.EMPATE:
        transicion = TransicionEstados(
            estado_final_a=EstadoFotografiado(
                EstadoTemporal.NEUTRO, estado_inicial_a.es_zombie
            ),
            estado_final_b=EstadoFotografiado(
                EstadoTemporal.NEUTRO, estado_inicial_b.es_zombie
            ),
            cambio_zombie_a=False,
            cambio_zombie_b=False,
            punto_zombificacion=None,
            kill=None,
            motivo_a=MotivoTransicion.EMPATE,
            motivo_b=MotivoTransicion.EMPATE,
        )
    else:
        ganador = Equipo.A if resultado is ResultadoGlobal.VICTORIA_A else Equipo.B
        if ganador is Equipo.A:
            transicion = _resolver_victoria(
                ganador=Equipo.A,
                estado_ganador=estado_inicial_a,
                estado_perdedor=estado_inicial_b,
                comunidad_ganador=comunidad_a,
            )
        else:
            invertida = _resolver_victoria(
                ganador=Equipo.B,
                estado_ganador=estado_inicial_b,
                estado_perdedor=estado_inicial_a,
                comunidad_ganador=comunidad_b,
            )
            transicion = TransicionEstados(
                estado_final_a=invertida.estado_final_b,
                estado_final_b=invertida.estado_final_a,
                cambio_zombie_a=invertida.cambio_zombie_b,
                cambio_zombie_b=invertida.cambio_zombie_a,
                punto_zombificacion=invertida.punto_zombificacion,
                kill=invertida.kill,
                motivo_a=invertida.motivo_b,
                motivo_b=invertida.motivo_a,
            )

    _validar_salida_transicion(
        estado_inicial_a,
        estado_inicial_b,
        resultado,
        doble_forfait,
        comunidad_a,
        comunidad_b,
        transicion,
    )
    return transicion


def _resolver_victoria(
    *,
    ganador: Equipo,
    estado_ganador: EstadoFotografiado,
    estado_perdedor: EstadoFotografiado,
    comunidad_ganador: object,
) -> TransicionEstados:
    """Resuelve una victoria colocando al ganador en la primera posición."""
    punto = None
    kill = None
    motivo_ganador = MotivoTransicion.VICTORIA
    motivo_perdedor = MotivoTransicion.DERROTA

    if estado_perdedor.estado_temporal is EstadoTemporal.HERIDO:
        estado_final_ganador = EstadoFotografiado(
            EstadoTemporal.NEUTRO, estado_ganador.es_zombie
        )
        estado_final_perdedor = EstadoFotografiado(EstadoTemporal.NEUTRO, True)
        cambio_zombie_perdedor = not estado_perdedor.es_zombie

        if not estado_perdedor.es_zombie:
            motivo_perdedor = MotivoTransicion.ZOMBIFICACION
            if estado_ganador.estado_temporal is EstadoTemporal.CAZADOR:
                punto = EfectoComunitario(ganador, comunidad_ganador)
        elif estado_ganador.estado_temporal is EstadoTemporal.CAZADOR_Z:
            motivo_ganador = MotivoTransicion.KILL
            kill = EfectoComunitario(ganador, comunidad_ganador)
    else:
        estado_final_ganador = EstadoFotografiado(
            (
                EstadoTemporal.CAZADOR_Z
                if estado_perdedor.es_zombie
                else EstadoTemporal.CAZADOR
            ),
            estado_ganador.es_zombie,
        )
        estado_final_perdedor = EstadoFotografiado(
            EstadoTemporal.HERIDO, estado_perdedor.es_zombie
        )
        cambio_zombie_perdedor = False

    return TransicionEstados(
        estado_final_a=estado_final_ganador,
        estado_final_b=estado_final_perdedor,
        cambio_zombie_a=False,
        cambio_zombie_b=cambio_zombie_perdedor,
        punto_zombificacion=punto,
        kill=kill,
        motivo_a=motivo_ganador,
        motivo_b=motivo_perdedor,
    )


def _validar_entrada_transicion(
    estado_a: object,
    estado_b: object,
    resultado: object,
    doble_forfait: object,
    comunidad_a: object,
    comunidad_b: object,
) -> None:
    if not isinstance(estado_a, EstadoFotografiado) or not isinstance(
        estado_b, EstadoFotografiado
    ):
        raise TypeError("los estados iniciales deben ser EstadoFotografiado")
    try:
        resultado = ResultadoGlobal(resultado)
    except (TypeError, ValueError) as exc:
        raise ValueError("resultado global desconocido") from exc
    if type(doble_forfait) is not bool:
        raise TypeError("doble_forfait debe ser booleano")
    if doble_forfait and resultado is not ResultadoGlobal.EMPATE:
        raise ValueError("un doble forfait global debe tener resultado EMPATE")
    if comunidad_a is None or comunidad_b is None:
        raise ValueError("ambas comunidades son obligatorias")
    if comunidad_a == comunidad_b:
        raise ValueError(
            "los equipos enfrentados deben pertenecer a comunidades distintas"
        )


def _validar_salida_transicion(
    estado_inicial_a: EstadoFotografiado,
    estado_inicial_b: EstadoFotografiado,
    resultado: ResultadoGlobal,
    doble_forfait: bool,
    comunidad_a: object,
    comunidad_b: object,
    transicion: TransicionEstados,
) -> None:
    for inicial, final, cambio in (
        (estado_inicial_a, transicion.estado_final_a, transicion.cambio_zombie_a),
        (estado_inicial_b, transicion.estado_final_b, transicion.cambio_zombie_b),
    ):
        if inicial.es_zombie and not final.es_zombie:
            raise AssertionError("la condición zombie no puede desaparecer")
        if cambio != (not inicial.es_zombie and final.es_zombie):
            raise AssertionError(
                "el indicador de cambio zombie no coincide con los estados"
            )

    if transicion.punto_zombificacion and transicion.kill:
        raise AssertionError("una transición no puede conceder punto y kill a la vez")

    if doble_forfait or resultado is ResultadoGlobal.EMPATE:
        if transicion.punto_zombificacion or transicion.kill:
            raise AssertionError("un empate no puede generar efectos comunitarios")
        return

    if resultado is ResultadoGlobal.VICTORIA_A:
        ganador = estado_inicial_a
        perdedor = estado_inicial_b
        equipo_ganador = Equipo.A
        comunidad_ganador = comunidad_a
    else:
        ganador = estado_inicial_b
        perdedor = estado_inicial_a
        equipo_ganador = Equipo.B
        comunidad_ganador = comunidad_b

    punto_esperado = (
        ganador.estado_temporal is EstadoTemporal.CAZADOR
        and perdedor.estado_temporal is EstadoTemporal.HERIDO
        and not perdedor.es_zombie
    )
    kill_esperada = (
        ganador.estado_temporal is EstadoTemporal.CAZADOR_Z
        and perdedor.estado_temporal is EstadoTemporal.HERIDO
        and perdedor.es_zombie
    )
    efecto_esperado = EfectoComunitario(equipo_ganador, comunidad_ganador)
    if (transicion.punto_zombificacion == efecto_esperado) != punto_esperado:
        raise AssertionError("el punto de zombificación no coincide con la fotografía")
    if (transicion.kill == efecto_esperado) != kill_esperada:
        raise AssertionError("la kill no coincide con la fotografía")


# ---------------------------------------------------------------------------
# Emparejamientos de comunidades
# ---------------------------------------------------------------------------

PairingComunidades = dict[str, Any]
TrazaPairingsComunidades = dict[str, Any]


@dataclass(frozen=True)
class _EquipoPairing:
    equipo_id: int
    comunidad_id: int
    puntos: Decimal
    posicion: int
    estado_temporal: EstadoTemporal
    es_zombie: bool
    cantidad_byes: int
    razas: frozenset[str]


_ETAPAS_PAIRING = (
    ("BASE", False, False, 0),
    ("PERMITIR_MIRRORS", True, False, 1),
    ("PERMITIR_ESTADOS_NO_DESEADOS", True, True, 2),
    ("PERMITIR_REPETIDOS", True, True, 3),
)


def _normalizar_raza(raza: object) -> str:
    return " ".join(str(raza or "").strip().casefold().split())


def _es_objetivo_caza(a: _EquipoPairing, b: _EquipoPairing) -> bool:
    return (
        a.estado_temporal is EstadoTemporal.CAZADOR
        and b.estado_temporal is EstadoTemporal.HERIDO
        and not b.es_zombie
    ) or (
        a.estado_temporal is EstadoTemporal.CAZADOR_Z
        and b.estado_temporal is EstadoTemporal.HERIDO
        and b.es_zombie
    )


def _prioridad_estado_pairing(a: _EquipoPairing, b: _EquipoPairing) -> int:
    """Devuelve 0 para cazas prioritarias, 1 para neutros y 2 para fallback."""
    if _es_objetivo_caza(a, b) or _es_objetivo_caza(b, a):
        return 0
    if (
        a.estado_temporal is EstadoTemporal.NEUTRO
        and b.estado_temporal is EstadoTemporal.NEUTRO
    ):
        return 1
    return 2


def _es_mirror_pairing(a: _EquipoPairing, b: _EquipoPairing) -> bool:
    return bool(a.razas.intersection(b.razas))


def generar_pairings_comunidades_backtracking(
    session: Any,
    torneo_id: int,
    ronda_numero: int,
    rng: Any = None,
) -> tuple[list[PairingComunidades], TrazaPairingsComunidades]:
    """Calcula una ronda completa sin persistirla.

    La función devuelve ``(pairings, traza)``. Cada intento conserva como
    restricciones absolutas la comunidad distinta y la solución completa, y
    relaja en orden mirrors, estados no deseados y rivales repetidos. Si no hay
    solución, ``pairings`` es una lista vacía y la traza contiene un error
    estructurado con código ``SIN_SOLUCION_COMPLETA``.
    """
    import random

    from GestorSQL import (
        ComunidadesEnfrentamiento,
        ComunidadesEquipo,
        ComunidadesMiembro,
        ComunidadesRonda,
    )

    if rng is None:
        rng = random.Random()
    if not hasattr(rng, "random"):
        raise TypeError("rng debe proporcionar un método random()")
    if ronda_numero < 1:
        raise ValueError("ronda_numero debe ser mayor que cero")

    clasificacion = calcular_clasificacion_equipos(
        session, torneo_id, hasta_ronda=ronda_numero - 1
    )
    if not clasificacion:
        return [], {
            "nivel_fallback": None,
            "etapa": "CANCELACION",
            "intentos": [],
            "error": {
                "codigo": "SIN_EQUIPOS",
                "detalle": "No hay equipos disponibles para emparejar.",
            },
        }

    filas = {int(fila["equipo_id"]): fila for fila in clasificacion}
    equipos_orm = (
        session.query(ComunidadesEquipo)
        .filter(ComunidadesEquipo.torneo_id == torneo_id)
        .all()
    )
    razas_por_equipo: dict[int, set[str]] = {int(e.id): set() for e in equipos_orm}
    for equipo_id, raza in (
        session.query(ComunidadesMiembro.equipo_id, ComunidadesMiembro.raza)
        .filter(ComunidadesMiembro.torneo_id == torneo_id)
        .all()
    ):
        normalizada = _normalizar_raza(raza)
        if normalizada:
            razas_por_equipo.setdefault(int(equipo_id), set()).add(normalizada)

    equipos: dict[int, _EquipoPairing] = {}
    for equipo in equipos_orm:
        fila = filas[int(equipo.id)]
        equipos[int(equipo.id)] = _EquipoPairing(
            equipo_id=int(equipo.id),
            comunidad_id=int(equipo.comunidad_id),
            puntos=_decimal(fila["puntos"]),
            posicion=int(fila.get("posicion", len(filas))),
            estado_temporal=EstadoTemporal(equipo.estado_temporal),
            es_zombie=bool(equipo.es_zombie),
            cantidad_byes=int(fila.get("cantidad_byes", equipo.cantidad_byes or 0)),
            razas=frozenset(razas_por_equipo.get(int(equipo.id), set())),
        )

    historial = (
        session.query(
            ComunidadesEnfrentamiento.equipo_a_id,
            ComunidadesEnfrentamiento.equipo_b_id,
        )
        .join(ComunidadesRonda, ComunidadesRonda.id == ComunidadesEnfrentamiento.ronda_id)
        .filter(
            ComunidadesEnfrentamiento.torneo_id == torneo_id,
            ComunidadesRonda.numero < ronda_numero,
        )
        .all()
    )
    rivales_previos = {equipo_id: set() for equipo_id in equipos}
    for equipo_a_id, equipo_b_id in historial:
        a, b = int(equipo_a_id), int(equipo_b_id)
        if a in rivales_previos and b in rivales_previos:
            rivales_previos[a].add(b)
            rivales_previos[b].add(a)

    ids = tuple(equipos)
    azar_pareja = {
        frozenset((a, b)): rng.random()
        for indice, a in enumerate(ids)
        for b in ids[indice + 1 :]
    }
    azar_bye = {equipo_id: rng.random() for equipo_id in ids}

    def ordenar_byes() -> list[Optional[int]]:
        if len(ids) % 2 == 0:
            return [None]
        return sorted(
            ids,
            key=lambda equipo_id: (
                equipos[equipo_id].estado_temporal is not EstadoTemporal.NEUTRO,
                equipos[equipo_id].cantidad_byes > 0,
                -equipos[equipo_id].posicion,
                azar_bye[equipo_id],
            ),
        )

    def resolver_etapa(
        permite_mirror: bool,
        permite_estados: bool,
        permite_repetidos: bool,
        bye_id: Optional[int],
    ) -> tuple[Optional[list[tuple[int, int]]], int]:
        pendientes_iniciales = tuple(e for e in ids if e != bye_id)
        mejor: Optional[list[tuple[int, int]]] = None
        mejor_coste: Optional[tuple[Any, ...]] = None
        exploradas = 0

        def backtrack(
            pendientes: tuple[int, ...],
            parejas: list[tuple[int, int]],
            estados_no_deseados: int,
            diferencia_puntos: Decimal,
            mirrors: int,
            azar_total: float,
        ) -> None:
            nonlocal mejor, mejor_coste, exploradas
            if not pendientes:
                exploradas += 1
                coste = (
                    estados_no_deseados,
                    diferencia_puntos,
                    mirrors,
                    azar_total,
                )
                if mejor_coste is None or coste < mejor_coste:
                    mejor_coste = coste
                    mejor = list(parejas)
                return

            # Elegir primero el equipo más restringido reduce drásticamente la
            # búsqueda sin convertir el orden de clasificación en una regla.
            def cantidad_candidatos(equipo_id: int) -> int:
                equipo = equipos[equipo_id]
                return sum(
                    equipos[otro].comunidad_id != equipo.comunidad_id
                    for otro in pendientes
                    if otro != equipo_id
                )

            a_id = min(
                pendientes,
                key=lambda equipo_id: (
                    cantidad_candidatos(equipo_id),
                    equipos[equipo_id].estado_temporal is EstadoTemporal.NEUTRO,
                    equipos[equipo_id].posicion,
                    equipo_id,
                ),
            )
            a = equipos[a_id]
            resto = tuple(e for e in pendientes if e != a_id)
            candidatos = []
            for b_id in resto:
                b = equipos[b_id]
                if a.comunidad_id == b.comunidad_id:
                    continue
                repetido = b_id in rivales_previos[a_id]
                if repetido and not permite_repetidos:
                    continue
                prioridad = _prioridad_estado_pairing(a, b)
                if prioridad == 2 and not permite_estados:
                    continue
                mirror = _es_mirror_pairing(a, b)
                if mirror and not permite_mirror:
                    continue
                candidatos.append(
                    (
                        prioridad,
                        abs(a.puntos - b.puntos),
                        mirror,
                        azar_pareja[frozenset((a_id, b_id))],
                        b_id,
                    )
                )
            candidatos.sort(key=lambda candidato: candidato[:-1])

            for prioridad, diferencia, mirror, azar, b_id in candidatos:
                nuevo_no_deseado = estados_no_deseados + (prioridad == 2)
                nueva_diferencia = diferencia_puntos + diferencia
                nuevos_mirrors = mirrors + int(mirror)
                coste_parcial = (
                    nuevo_no_deseado,
                    nueva_diferencia,
                    nuevos_mirrors,
                    azar_total + azar,
                )
                if mejor_coste is not None and coste_parcial >= mejor_coste:
                    continue
                parejas.append((a_id, b_id))
                backtrack(
                    tuple(e for e in resto if e != b_id),
                    parejas,
                    nuevo_no_deseado,
                    nueva_diferencia,
                    nuevos_mirrors,
                    azar_total + azar,
                )
                parejas.pop()

        backtrack(pendientes_iniciales, [], 0, Decimal("0"), 0, 0.0)
        return mejor, exploradas

    intentos: list[dict[str, Any]] = []
    # El orden del bye es una prioridad propia y absoluta: para cada candidato
    # se agotan los fallbacks de emparejamiento antes de considerar el siguiente.
    for bye_id in ordenar_byes():
        for etapa, permite_mirror, permite_estados, nivel in _ETAPAS_PAIRING:
            permite_repetidos = etapa == "PERMITIR_REPETIDOS"
            solucion, soluciones_exploradas = resolver_etapa(
                permite_mirror,
                permite_estados,
                permite_repetidos,
                bye_id,
            )
            intento = {
                "etapa": etapa,
                "nivel_fallback": nivel,
                "bye_equipo_id": bye_id,
                "permite_mirrors": permite_mirror,
                "permite_estados_no_deseados": permite_estados,
                "permite_repetidos": permite_repetidos,
                "soluciones_completas_exploradas": soluciones_exploradas,
                "encontrada": solucion is not None,
            }
            intentos.append(intento)
            if solucion is None:
                continue

            pairings: list[PairingComunidades] = []
            for mesa, (a_id, b_id) in enumerate(solucion, start=1):
                a, b = equipos[a_id], equipos[b_id]
                pairings.append(
                    {
                        "mesa_numero": mesa,
                        "equipo_a_id": a_id,
                        "equipo_b_id": b_id,
                        "es_bye": False,
                        "diferencia_puntos": abs(a.puntos - b.puntos),
                        "prioridad_estado": _prioridad_estado_pairing(a, b),
                        "es_mirror": _es_mirror_pairing(a, b),
                        "es_rival_repetido": b_id in rivales_previos[a_id],
                    }
                )
            if bye_id is not None:
                pairings.append(
                    {
                        "mesa_numero": len(pairings) + 1,
                        "equipo_a_id": bye_id,
                        "equipo_b_id": None,
                        "es_bye": True,
                        "diferencia_puntos": None,
                        "prioridad_estado": None,
                        "es_mirror": False,
                        "es_rival_repetido": False,
                    }
                )
            return pairings, {
                "nivel_fallback": nivel,
                "etapa": etapa,
                "intentos": intentos,
                "error": None,
            }

    return [], {
        "nivel_fallback": None,
        "etapa": "CANCELACION",
        "intentos": intentos,
        "error": {
            "codigo": "SIN_SOLUCION_COMPLETA",
            "detalle": (
                "No existe una ronda completa sin enfrentar equipos de la "
                "misma comunidad."
            ),
        },
    }


class ErrorSeleccionAtacanteComunidades(ValueError):
    """Error de dominio al registrar una elección de atacante."""

    def __init__(self, codigo: str, detalle: str):
        super().__init__(detalle)
        self.codigo = codigo
        self.detalle = detalle


@dataclass(frozen=True)
class ResultadoSeleccionAtacanteComunidades:
    """Contrato explícito devuelto tras persistir una elección."""

    eleccion: Any
    atacante: Any
    defensor: Any
    equipo_nombre: str
    ambas_elecciones_completas: bool
    requiere_crear_partidos: bool
    acaba_de_completar_elecciones: bool


def _error_seleccion_atacante(codigo: str, detalle: str) -> None:
    raise ErrorSeleccionAtacanteComunidades(codigo, detalle)


def _resolver_enfrentamiento_seleccion(
    session: Any,
    *,
    enfrentamiento_id: Optional[int],
    canal_general_discord_id: Optional[int],
):
    from GestorSQL import ComunidadesEnfrentamiento

    if (enfrentamiento_id is None) == (canal_general_discord_id is None):
        _error_seleccion_atacante(
            "REFERENCIA_ENFRENTAMIENTO_INVALIDA",
            "Debe indicarse exactamente un ID de enfrentamiento o de canal general.",
        )
    if enfrentamiento_id is not None:
        if type(enfrentamiento_id) is not int or enfrentamiento_id <= 0:
            _error_seleccion_atacante(
                "REFERENCIA_ENFRENTAMIENTO_INVALIDA",
                "El ID del enfrentamiento debe ser un entero mayor que cero.",
            )
        filtro = ComunidadesEnfrentamiento.id == enfrentamiento_id
    else:
        if type(canal_general_discord_id) is not int or canal_general_discord_id <= 0:
            _error_seleccion_atacante(
                "REFERENCIA_ENFRENTAMIENTO_INVALIDA",
                "El ID del canal general debe ser un entero mayor que cero.",
            )
        filtro = (
            ComunidadesEnfrentamiento.canal_general_discord_id
            == canal_general_discord_id
        )

    enfrentamientos = session.query(ComunidadesEnfrentamiento).filter(filtro).limit(2).all()
    if not enfrentamientos:
        _error_seleccion_atacante(
            "ENFRENTAMIENTO_NO_EXISTE",
            "No existe un enfrentamiento asociado a la referencia indicada.",
        )
    if len(enfrentamientos) != 1:
        _error_seleccion_atacante(
            "CANAL_ENFRENTAMIENTO_AMBIGUO",
            "El canal general está asociado a más de un enfrentamiento.",
        )
    return enfrentamientos[0]


def registrar_eleccion_atacante_comunidades(
    session: Any,
    *,
    actor_discord_id: int,
    atacante_usuario_id: Optional[int] = None,
    atacante_discord_id: Optional[int] = None,
    enfrentamiento_id: Optional[int] = None,
    canal_general_discord_id: Optional[int] = None,
    elegido_en: Optional[datetime] = None,
) -> ResultadoSeleccionAtacanteComunidades:
    """Registra una elección y bloquea las dos al quedar completas.

    La escritura serializa a los contendientes mediante una actualización
    condicional del enfrentamiento. En InnoDB bloquea la fila y en SQLite
    adquiere el bloqueo de escritura, evitando que dos últimas elecciones
    creen filas duplicadas o observen un estado parcial.
    """
    from GestorSQL import (
        ComunidadesEleccionAtacante,
        ComunidadesEnfrentamiento,
        ComunidadesMiembro,
    )

    if type(actor_discord_id) is not int or actor_discord_id <= 0:
        _error_seleccion_atacante(
            "ACTOR_INVALIDO", "El ID Discord del actor debe ser un entero mayor que cero."
        )
    if (atacante_usuario_id is None) == (atacante_discord_id is None):
        _error_seleccion_atacante(
            "ATACANTE_INVALIDO",
            "Debe indicarse exactamente un ID interno o un ID Discord del atacante.",
        )
    atacante_referencia = (
        atacante_usuario_id
        if atacante_usuario_id is not None
        else atacante_discord_id
    )
    if type(atacante_referencia) is not int or atacante_referencia <= 0:
        _error_seleccion_atacante(
            "ATACANTE_INVALIDO", "El ID del atacante debe ser un entero mayor que cero."
        )
    if elegido_en is not None and not isinstance(elegido_en, datetime):
        _error_seleccion_atacante(
            "FECHA_INVALIDA", "La fecha de elección debe ser datetime o None."
        )

    try:
        enfrentamiento = _resolver_enfrentamiento_seleccion(
            session,
            enfrentamiento_id=enfrentamiento_id,
            canal_general_discord_id=canal_general_discord_id,
        )
        identificador = int(enfrentamiento.id)

        # Una UPDATE sobre la propia fila sirve como mutex transaccional y la
        # condición impide reabrir un enfrentamiento ya completado.
        session.query(ComunidadesEnfrentamiento).filter(
            ComunidadesEnfrentamiento.id == identificador,
            ComunidadesEnfrentamiento.estado
            == ENFRENTAMIENTO_PENDIENTE_ELECCIONES,
        ).update(
            {ComunidadesEnfrentamiento.estado: ENFRENTAMIENTO_PENDIENTE_ELECCIONES},
            synchronize_session=False,
        )
        session.expire_all()
        enfrentamiento = session.get(ComunidadesEnfrentamiento, identificador)

        if enfrentamiento.ronda is None or enfrentamiento.ronda.estado != "ABIERTA":
            _error_seleccion_atacante(
                "ENFRENTAMIENTO_NO_ACTIVO",
                "El enfrentamiento no pertenece a una ronda activa.",
            )

        equipo_ids = (int(enfrentamiento.equipo_a_id), int(enfrentamiento.equipo_b_id))
        miembros = (
            session.query(ComunidadesMiembro)
            .filter(
                ComunidadesMiembro.torneo_id == enfrentamiento.torneo_id,
                ComunidadesMiembro.equipo_id.in_(equipo_ids),
            )
            .all()
        )
        miembros_actor = [
            miembro
            for miembro in miembros
            if miembro.usuario is not None
            and miembro.usuario.id_discord is not None
            and int(miembro.usuario.id_discord) == actor_discord_id
        ]
        if len(miembros_actor) != 1:
            _error_seleccion_atacante(
                "ACTOR_NO_PERTENECE",
                "El actor no pertenece a ninguno de los equipos del enfrentamiento.",
            )
        equipo_id = int(miembros_actor[0].equipo_id)
        miembros_equipo = [
            miembro for miembro in miembros if int(miembro.equipo_id) == equipo_id
        ]
        if len(miembros_equipo) != 2:
            _error_seleccion_atacante(
                "EQUIPO_INCOMPLETO", "El equipo del actor no tiene exactamente dos miembros."
            )
        atacante_miembro = next(
            (
                miembro
                for miembro in miembros_equipo
                if (
                    atacante_usuario_id is not None
                    and int(miembro.usuario_id) == atacante_usuario_id
                )
                or (
                    atacante_discord_id is not None
                    and miembro.usuario is not None
                    and miembro.usuario.id_discord is not None
                    and int(miembro.usuario.id_discord) == atacante_discord_id
                )
            ),
            None,
        )
        if atacante_miembro is None:
            _error_seleccion_atacante(
                "ATACANTE_NO_PERTENECE",
                "El atacante seleccionado no pertenece al equipo del actor.",
            )
        atacante_usuario_id_resuelto = int(atacante_miembro.usuario_id)
        defensor_miembro = next(
            miembro
            for miembro in miembros_equipo
            if int(miembro.usuario_id) != atacante_usuario_id_resuelto
        )

        eleccion = (
            session.query(ComunidadesEleccionAtacante)
            .filter(
                ComunidadesEleccionAtacante.enfrentamiento_id == identificador,
                ComunidadesEleccionAtacante.equipo_id == equipo_id,
            )
            .one_or_none()
        )
        if enfrentamiento.estado != ENFRENTAMIENTO_PENDIENTE_ELECCIONES:
            _error_seleccion_atacante(
                "ELECCIONES_BLOQUEADAS",
                "Las elecciones del enfrentamiento ya no se pueden modificar.",
            )

        ahora = elegido_en or datetime.now(timezone.utc).replace(tzinfo=None)
        if eleccion is None:
            eleccion = ComunidadesEleccionAtacante(
                torneo_id=enfrentamiento.torneo_id,
                enfrentamiento_id=identificador,
                equipo_id=equipo_id,
                atacante_usuario_id=atacante_usuario_id_resuelto,
                defensor_usuario_id=int(defensor_miembro.usuario_id),
                elegido_por_discord_id=actor_discord_id,
                elegido_en=ahora,
                bloqueada=False,
            )
            session.add(eleccion)
        else:
            if bool(eleccion.bloqueada):
                _error_seleccion_atacante(
                    "ELECCIONES_BLOQUEADAS",
                    "La elección del equipo ya está bloqueada.",
                )
            eleccion.atacante_usuario_id = atacante_usuario_id_resuelto
            eleccion.defensor_usuario_id = int(defensor_miembro.usuario_id)
            eleccion.elegido_por_discord_id = actor_discord_id
            eleccion.elegido_en = ahora
        session.flush()

        elecciones = (
            session.query(ComunidadesEleccionAtacante)
            .filter(ComunidadesEleccionAtacante.enfrentamiento_id == identificador)
            .all()
        )
        completas = {int(item.equipo_id) for item in elecciones} == set(equipo_ids)
        if completas:
            for item in elecciones:
                item.bloqueada = True
            enfrentamiento.estado = ENFRENTAMIENTO_ELECCIONES_COMPLETAS
            session.flush()

        session.commit()
        return ResultadoSeleccionAtacanteComunidades(
            eleccion=eleccion,
            atacante=atacante_miembro.usuario,
            defensor=defensor_miembro.usuario,
            equipo_nombre=str(atacante_miembro.equipo.nombre),
            ambas_elecciones_completas=completas,
            requiere_crear_partidos=completas,
            acaba_de_completar_elecciones=completas,
        )
    except Exception:
        session.rollback()
        raise


class ErrorTransferenciaComunidades(ValueError):
    """Error de dominio legible para transferir cazador entre equipos."""

    def __init__(self, codigo: str, detalle: str):
        super().__init__(detalle)
        self.codigo = codigo
        self.detalle = detalle


def _error_transferencia(codigo: str, detalle: str) -> None:
    raise ErrorTransferenciaComunidades(codigo, detalle)


def _enfrentamiento_finalizado_o_bye_comunidades(
    session: Any, *, torneo_id: int, ronda_id: int, equipo_id: int
) -> bool:
    """Indica si el equipo ya terminó su participación en la ronda vigente."""
    from GestorSQL import ComunidadesEnfrentamiento, ComunidadesHistorialTransicion

    enfrentamiento = (
        session.query(ComunidadesEnfrentamiento)
        .filter(
            ComunidadesEnfrentamiento.torneo_id == torneo_id,
            ComunidadesEnfrentamiento.ronda_id == ronda_id,
            (
                (ComunidadesEnfrentamiento.equipo_a_id == equipo_id)
                | (ComunidadesEnfrentamiento.equipo_b_id == equipo_id)
            ),
        )
        .with_for_update()
        .one_or_none()
    )
    if enfrentamiento is not None:
        return enfrentamiento.estado in {
            ENFRENTAMIENTO_CERRADO,
            ENFRENTAMIENTO_ADMINISTRADO,
        }

    return (
        session.query(ComunidadesHistorialTransicion.id)
        .filter(
            ComunidadesHistorialTransicion.torneo_id == torneo_id,
            ComunidadesHistorialTransicion.ronda_id == ronda_id,
            ComunidadesHistorialTransicion.equipo_id == equipo_id,
            ComunidadesHistorialTransicion.motivo == "BYE",
        )
        .first()
        is not None
    )


def transferir_cazador_comunidades(
    session: Any,
    *,
    torneo_id: int,
    equipo_destino_nombre: str,
    actor_discord_id: int,
    clave_idempotencia: str,
):
    """Transfiere atómicamente un cazador obtenido en la ronda vigente.

    El equipo origen se deduce de la pertenencia del actor al torneo. Se
    bloquean ronda y equipos antes de validar para impedir dos transferencias
    concurrentes del mismo estado. La procedencia se acredita con la última
    transición del origen en la ronda actual, no solo con su valor presente.
    """
    from GestorSQL import (
        ComunidadesEquipo,
        ComunidadesHistorialTransferencia,
        ComunidadesHistorialTransicion,
        ComunidadesMiembro,
        ComunidadesRonda,
        Usuario,
    )

    if type(torneo_id) is not int or torneo_id <= 0:
        _error_transferencia(
            "TORNEO_INVALIDO", "torneo_id debe ser un entero mayor que cero."
        )
    if type(actor_discord_id) is not int or actor_discord_id <= 0:
        _error_transferencia(
            "ACTOR_INVALIDO", "El ID Discord del actor debe ser un entero mayor que cero."
        )
    clave_idempotencia = str(clave_idempotencia or "").strip()
    if not clave_idempotencia or len(clave_idempotencia) > 190:
        _error_transferencia(
            "CLAVE_IDEMPOTENCIA_INVALIDA",
            "La transferencia requiere una clave idempotente válida.",
        )
    existente = (
        session.query(ComunidadesHistorialTransferencia)
        .filter(
            ComunidadesHistorialTransferencia.clave_idempotencia
            == clave_idempotencia
        )
        .one_or_none()
    )
    if existente is not None:
        if int(existente.torneo_id) != torneo_id:
            _error_transferencia(
                "CLAVE_IDEMPOTENCIA_CONFLICTIVA",
                "La clave idempotente pertenece a otro torneo.",
            )
        return existente

    equipo_destino_nombre = str(equipo_destino_nombre or "").strip()
    if not equipo_destino_nombre:
        _error_transferencia(
            "DESTINO_INVALIDO", "Debe indicar el nombre del equipo destino."
        )

    try:
        ronda = (
            session.query(ComunidadesRonda)
            .filter(
                ComunidadesRonda.torneo_id == torneo_id,
                ComunidadesRonda.estado == RONDA_ABIERTA,
            )
            .order_by(ComunidadesRonda.numero.desc())
            .with_for_update()
            .first()
        )
        if ronda is None:
            _error_transferencia(
                "RONDA_NO_DISPONIBLE",
                "El torneo no tiene una ronda abierta en la que transferir el estado.",
            )

        origen = (
            session.query(ComunidadesEquipo)
            .join(
                ComunidadesMiembro,
                (ComunidadesMiembro.equipo_id == ComunidadesEquipo.id)
                & (ComunidadesMiembro.torneo_id == ComunidadesEquipo.torneo_id),
            )
            .join(Usuario, Usuario.idUsuarios == ComunidadesMiembro.usuario_id)
            .filter(
                ComunidadesEquipo.torneo_id == torneo_id,
                Usuario.id_discord == actor_discord_id,
            )
            .one_or_none()
        )
        if origen is None:
            _error_transferencia(
                "ACTOR_NO_MIEMBRO",
                "Solo un miembro del equipo origen puede transferir el estado.",
            )

        destino = (
            session.query(ComunidadesEquipo)
            .filter(
                ComunidadesEquipo.torneo_id == torneo_id,
                ComunidadesEquipo.nombre == equipo_destino_nombre,
            )
            .one_or_none()
        )
        if destino is None:
            _error_transferencia(
                "DESTINO_NO_EXISTE",
                f"El equipo destino `{equipo_destino_nombre}` no existe en el torneo.",
            )
        if int(origen.id) == int(destino.id):
            _error_transferencia(
                "MISMO_EQUIPO", "El equipo origen y el destino deben ser distintos."
            )
        equipos_bloqueados = (
            session.query(ComunidadesEquipo)
            .filter(ComunidadesEquipo.id.in_(sorted((int(origen.id), int(destino.id)))))
            .order_by(ComunidadesEquipo.id)
            .with_for_update()
            .all()
        )
        por_id = {int(equipo.id): equipo for equipo in equipos_bloqueados}
        origen = por_id[int(origen.id)]
        destino = por_id[int(destino.id)]
        if int(origen.comunidad_id) != int(destino.comunidad_id):
            _error_transferencia(
                "COMUNIDAD_DISTINTA",
                "El equipo origen y el destino deben pertenecer a la misma comunidad.",
            )

        for equipo in (origen, destino):
            if not _enfrentamiento_finalizado_o_bye_comunidades(
                session,
                torneo_id=torneo_id,
                ronda_id=int(ronda.id),
                equipo_id=int(equipo.id),
            ):
                _error_transferencia(
                    "ENFRENTAMIENTO_EN_CURSO",
                    "No puede transferir el estado con un enfrentamiento en curso",
                )

        tipo = str(origen.estado_temporal)
        if tipo not in {
            EstadoTemporal.CAZADOR.value,
            EstadoTemporal.CAZADOR_Z.value,
        }:
            _error_transferencia(
                "ORIGEN_SIN_CAZADOR",
                "El equipo origen no tiene cazador ni cazador Z para transferir.",
            )
        if str(destino.estado_temporal) != EstadoTemporal.NEUTRO.value:
            _error_transferencia(
                "DESTINO_NO_NEUTRO",
                "El equipo destino debe estar temporalmente neutro.",
            )

        ultima_transicion = (
            session.query(ComunidadesHistorialTransicion)
            .filter(
                ComunidadesHistorialTransicion.torneo_id == torneo_id,
                ComunidadesHistorialTransicion.ronda_id == ronda.id,
                ComunidadesHistorialTransicion.equipo_id == origen.id,
            )
            .order_by(
                ComunidadesHistorialTransicion.created_at.desc(),
                ComunidadesHistorialTransicion.id.desc(),
            )
            .with_for_update()
            .first()
        )
        if (
            ultima_transicion is None
            or ultima_transicion.motivo not in {"VICTORIA", "TRANSFERENCIA"}
            or str(ultima_transicion.estado_temporal_posterior) != tipo
        ):
            _error_transferencia(
                "ESTADO_NO_OBTENIDO_EN_RONDA",
                "No se puede transferir un estado heredado de una ronda anterior.",
            )

        zombie_origen = bool(origen.es_zombie)
        zombie_destino = bool(destino.es_zombie)
        origen.estado_temporal = EstadoTemporal.NEUTRO.value
        destino.estado_temporal = tipo
        session.add_all(
            [
                ComunidadesHistorialTransicion(
                    torneo_id=torneo_id,
                    ronda_id=ronda.id,
                    enfrentamiento_id=None,
                    equipo_id=origen.id,
                    estado_temporal_anterior=tipo,
                    es_zombie_anterior=zombie_origen,
                    estado_temporal_posterior=EstadoTemporal.NEUTRO.value,
                    es_zombie_posterior=zombie_origen,
                    motivo="TRANSFERENCIA",
                ),
                ComunidadesHistorialTransicion(
                    torneo_id=torneo_id,
                    ronda_id=ronda.id,
                    enfrentamiento_id=None,
                    equipo_id=destino.id,
                    estado_temporal_anterior=EstadoTemporal.NEUTRO.value,
                    es_zombie_anterior=zombie_destino,
                    estado_temporal_posterior=tipo,
                    es_zombie_posterior=zombie_destino,
                    motivo="TRANSFERENCIA",
                ),
            ]
        )
        transferencia = ComunidadesHistorialTransferencia(
            torneo_id=torneo_id,
            ronda_id=ronda.id,
            comunidad_id=origen.comunidad_id,
            equipo_origen_id=origen.id,
            equipo_destino_id=destino.id,
            tipo=tipo,
            ejecutada_por_discord_id=actor_discord_id,
            clave_idempotencia=clave_idempotencia,
        )
        session.add(transferencia)
        session.flush()
        session.commit()
        return transferencia
    except IntegrityError:
        session.rollback()
        existente = (
            session.query(ComunidadesHistorialTransferencia)
            .filter(
                ComunidadesHistorialTransferencia.clave_idempotencia
                == clave_idempotencia
            )
            .one_or_none()
        )
        if existente is not None:
            return existente
        raise
    except Exception:
        session.rollback()
        raise


class ErrorAdministracionEleccionesComunidades(ValueError):
    """Error de dominio para consultar o imponer elecciones administrativas."""

    def __init__(self, codigo: str, detalle: str):
        super().__init__(detalle)
        self.codigo = codigo
        self.detalle = detalle


@dataclass(frozen=True)
class EleccionEquipoAdministrativaComunidades:
    equipo: Any
    atacante: Optional[Any]
    defensor: Optional[Any]
    pendiente: bool
    bloqueada: bool
    actor_discord_id: Optional[int]
    elegido_en: Optional[datetime]


@dataclass(frozen=True)
class EleccionesEnfrentamientoAdministrativasComunidades:
    enfrentamiento: Any
    elecciones: tuple[
        EleccionEquipoAdministrativaComunidades,
        EleccionEquipoAdministrativaComunidades,
    ]


def _error_administracion_elecciones(codigo: str, detalle: str) -> None:
    raise ErrorAdministracionEleccionesComunidades(codigo, detalle)


def consultar_elecciones_comunidades(
    session: Any, *, torneo_id: int, ronda_numero: int
) -> tuple[EleccionesEnfrentamientoAdministrativasComunidades, ...]:
    """Devuelve las elecciones de una ronda; el llamador debe validar permisos antes."""
    from GestorSQL import (
        ComunidadesEleccionAtacante,
        ComunidadesEnfrentamiento,
        ComunidadesRonda,
        ComunidadesTorneo,
    )

    for valor, nombre in ((torneo_id, "torneo_id"), (ronda_numero, "ronda")):
        if type(valor) is not int or valor <= 0:
            _error_administracion_elecciones(
                "VALOR_INVALIDO", f"{nombre} debe ser un entero mayor que cero."
            )
    torneo = session.get(ComunidadesTorneo, torneo_id)
    if torneo is None:
        _error_administracion_elecciones(
            "TORNEO_NO_EXISTE", f"No existe el torneo de comunidades {torneo_id}."
        )
    ronda = (
        session.query(ComunidadesRonda)
        .filter(
            ComunidadesRonda.torneo_id == torneo_id,
            ComunidadesRonda.numero == ronda_numero,
        )
        .one_or_none()
    )
    if ronda is None:
        _error_administracion_elecciones(
            "RONDA_NO_EXISTE",
            f"No existe la ronda {ronda_numero} del torneo {torneo_id}.",
        )

    enfrentamientos = (
        session.query(ComunidadesEnfrentamiento)
        .filter(ComunidadesEnfrentamiento.ronda_id == ronda.id)
        .order_by(ComunidadesEnfrentamiento.mesa_numero)
        .all()
    )
    resultado = []
    for enfrentamiento in enfrentamientos:
        elecciones = (
            session.query(ComunidadesEleccionAtacante)
            .filter(
                ComunidadesEleccionAtacante.enfrentamiento_id == enfrentamiento.id
            )
            .all()
        )
        por_equipo = {int(eleccion.equipo_id): eleccion for eleccion in elecciones}
        detalles = []
        for equipo in (enfrentamiento.equipo_a, enfrentamiento.equipo_b):
            eleccion = por_equipo.get(int(equipo.id))
            detalles.append(
                EleccionEquipoAdministrativaComunidades(
                    equipo=equipo,
                    atacante=(eleccion.atacante_usuario if eleccion else None),
                    defensor=(eleccion.defensor_usuario if eleccion else None),
                    pendiente=eleccion is None,
                    bloqueada=bool(eleccion.bloqueada) if eleccion else False,
                    actor_discord_id=(
                        int(eleccion.elegido_por_discord_id) if eleccion else None
                    ),
                    elegido_en=eleccion.elegido_en if eleccion else None,
                )
            )
        resultado.append(
            EleccionesEnfrentamientoAdministrativasComunidades(
                enfrentamiento=enfrentamiento,
                elecciones=(detalles[0], detalles[1]),
            )
        )
    return tuple(resultado)


def forzar_elecciones_comunidades(
    session: Any,
    *,
    torneo_id: int,
    ronda_numero: int,
    enfrentamiento_id: int,
    atacante_equipo_a_discord_id: int,
    atacante_equipo_b_discord_id: int,
    actor_discord_id: int,
    elegido_en: Optional[datetime] = None,
):
    """Impone y bloquea las dos elecciones sin confirmar la transacción."""
    from GestorSQL import (
        ComunidadesEleccionAtacante,
        ComunidadesEnfrentamiento,
        ComunidadesMiembro,
        ComunidadesPartido,
        ComunidadesRonda,
        ComunidadesTorneo,
    )

    for valor, nombre in (
        (torneo_id, "torneo_id"),
        (ronda_numero, "ronda"),
        (enfrentamiento_id, "enfrentamiento"),
        (atacante_equipo_a_discord_id, "atacante_equipo_a"),
        (atacante_equipo_b_discord_id, "atacante_equipo_b"),
        (actor_discord_id, "actor_discord_id"),
    ):
        if type(valor) is not int or valor <= 0:
            _error_administracion_elecciones(
                "VALOR_INVALIDO", f"{nombre} debe ser un entero mayor que cero."
            )
    if elegido_en is not None and not isinstance(elegido_en, datetime):
        _error_administracion_elecciones(
            "FECHA_INVALIDA", "elegido_en debe ser datetime o None."
        )
    if session.get(ComunidadesTorneo, torneo_id) is None:
        _error_administracion_elecciones(
            "TORNEO_NO_EXISTE", f"No existe el torneo de comunidades {torneo_id}."
        )
    ronda = (
        session.query(ComunidadesRonda)
        .filter(
            ComunidadesRonda.torneo_id == torneo_id,
            ComunidadesRonda.numero == ronda_numero,
        )
        .one_or_none()
    )
    if ronda is None:
        _error_administracion_elecciones(
            "RONDA_NO_EXISTE",
            f"No existe la ronda {ronda_numero} del torneo {torneo_id}.",
        )
    enfrentamiento = (
        session.query(ComunidadesEnfrentamiento)
        .filter(
            ComunidadesEnfrentamiento.id == enfrentamiento_id,
            ComunidadesEnfrentamiento.torneo_id == torneo_id,
            ComunidadesEnfrentamiento.ronda_id == ronda.id,
        )
        .with_for_update()
        .one_or_none()
    )
    if enfrentamiento is None:
        _error_administracion_elecciones(
            "ENFRENTAMIENTO_NO_EXISTE",
            "El enfrentamiento no pertenece al torneo y ronda indicados.",
        )

    miembros = (
        session.query(ComunidadesMiembro)
        .filter(
            ComunidadesMiembro.torneo_id == torneo_id,
            ComunidadesMiembro.equipo_id.in_(
                (enfrentamiento.equipo_a_id, enfrentamiento.equipo_b_id)
            ),
        )
        .all()
    )
    por_equipo = {}
    for equipo_id, discord_id, lado in (
        (int(enfrentamiento.equipo_a_id), atacante_equipo_a_discord_id, "A"),
        (int(enfrentamiento.equipo_b_id), atacante_equipo_b_discord_id, "B"),
    ):
        miembros_equipo = [m for m in miembros if int(m.equipo_id) == equipo_id]
        if len(miembros_equipo) != 2:
            _error_administracion_elecciones(
                "EQUIPO_INCOMPLETO", f"El equipo del lado {lado} no tiene dos miembros."
            )
        atacante = next(
            (
                m
                for m in miembros_equipo
                if m.usuario is not None
                and m.usuario.id_discord is not None
                and int(m.usuario.id_discord) == discord_id
            ),
            None,
        )
        if atacante is None:
            _error_administracion_elecciones(
                "ATACANTE_NO_PERTENECE",
                f"El atacante indicado para el equipo {lado} no pertenece a ese equipo.",
            )
        defensor = next(m for m in miembros_equipo if m is not atacante)
        por_equipo[equipo_id] = (atacante, defensor)

    partidos = (
        session.query(ComunidadesPartido)
        .filter(ComunidadesPartido.enfrentamiento_id == enfrentamiento_id)
        .order_by(ComunidadesPartido.indice)
        .all()
    )
    elecciones = (
        session.query(ComunidadesEleccionAtacante)
        .filter(ComunidadesEleccionAtacante.enfrentamiento_id == enfrentamiento_id)
        .all()
    )
    elecciones_por_equipo = {int(e.equipo_id): e for e in elecciones}
    if partidos:
        if len(partidos) != 2 or [int(p.indice) for p in partidos] != [1, 2]:
            _error_administracion_elecciones(
                "PARTIDOS_INCOMPLETOS",
                "El enfrentamiento tiene una materialización parcial o inconsistente.",
            )
        coinciden = all(
            equipo_id in elecciones_por_equipo
            and int(elecciones_por_equipo[equipo_id].atacante_usuario_id)
            == int(por_equipo[equipo_id][0].usuario_id)
            for equipo_id in por_equipo
        )
        if not coinciden:
            _error_administracion_elecciones(
                "PARTIDOS_YA_CREADOS",
                "Los partidos ya existen y no pueden sustituirse con otros atacantes.",
            )
        return enfrentamiento

    if enfrentamiento.estado not in {
        ENFRENTAMIENTO_PENDIENTE_ELECCIONES,
        ENFRENTAMIENTO_ELECCIONES_COMPLETAS,
    }:
        _error_administracion_elecciones(
            "ENFRENTAMIENTO_NO_ADMITE_CREACION",
            f"El enfrentamiento está en estado {enfrentamiento.estado}.",
        )

    ahora = elegido_en or datetime.now(timezone.utc).replace(tzinfo=None)
    for equipo_id, (atacante, defensor) in por_equipo.items():
        eleccion = elecciones_por_equipo.get(equipo_id)
        if eleccion is None:
            eleccion = ComunidadesEleccionAtacante(
                torneo_id=torneo_id,
                enfrentamiento_id=enfrentamiento_id,
                equipo_id=equipo_id,
            )
            session.add(eleccion)
        eleccion.atacante_usuario_id = int(atacante.usuario_id)
        eleccion.defensor_usuario_id = int(defensor.usuario_id)
        eleccion.elegido_por_discord_id = actor_discord_id
        eleccion.elegido_en = ahora
        eleccion.bloqueada = True
    enfrentamiento.estado = ENFRENTAMIENTO_ELECCIONES_COMPLETAS
    session.flush()
    return enfrentamiento


class ErrorMaterializacionPartidosComunidades(ValueError):
    """Error de dominio al fijar las identidades de los partidos."""

    def __init__(self, codigo: str, detalle: str):
        super().__init__(detalle)
        self.codigo = codigo
        self.detalle = detalle


@dataclass(frozen=True)
class ResultadoMaterializacionPartidosComunidades:
    """Identidades estables de los dos partidos de un enfrentamiento."""

    enfrentamiento: Any
    partidos: tuple[Any, Any]
    creados: bool


def _error_materializacion_partidos(codigo: str, detalle: str) -> None:
    raise ErrorMaterializacionPartidosComunidades(codigo, detalle)


def materializar_identidades_partidos_comunidades(
    session: Any,
    *,
    enfrentamiento_id: int,
) -> ResultadoMaterializacionPartidosComunidades:
    """Persiste exactamente los dos cruces derivados de elecciones bloqueadas.

    Esta función no confirma la transacción. El llamador debe hacer ``commit``
    antes de iniciar efectos externos en Discord, de modo que un reintento
    conserve la misma identidad de partido aunque falle la creación de canales.
    """
    from GestorSQL import (
        ComunidadesEleccionAtacante,
        ComunidadesEnfrentamiento,
        ComunidadesPartido,
    )

    if type(enfrentamiento_id) is not int or enfrentamiento_id <= 0:
        _error_materializacion_partidos(
            "REFERENCIA_INVALIDA",
            "El ID del enfrentamiento debe ser un entero mayor que cero.",
        )

    enfrentamiento = (
        session.query(ComunidadesEnfrentamiento)
        .filter(ComunidadesEnfrentamiento.id == enfrentamiento_id)
        .with_for_update()
        .one_or_none()
    )
    if enfrentamiento is None:
        _error_materializacion_partidos(
            "ENFRENTAMIENTO_NO_EXISTE",
            f"No existe el enfrentamiento {enfrentamiento_id}.",
        )

    partidos_existentes = (
        session.query(ComunidadesPartido)
        .filter(ComunidadesPartido.enfrentamiento_id == enfrentamiento_id)
        .order_by(ComunidadesPartido.indice)
        .all()
    )
    if partidos_existentes:
        indices = [int(partido.indice) for partido in partidos_existentes]
        if len(partidos_existentes) != 2 or indices != [1, 2]:
            _error_materializacion_partidos(
                "PARTIDOS_INCOMPLETOS",
                "El enfrentamiento tiene una materialización parcial o inconsistente.",
            )
        return ResultadoMaterializacionPartidosComunidades(
            enfrentamiento=enfrentamiento,
            partidos=(partidos_existentes[0], partidos_existentes[1]),
            creados=False,
        )

    if enfrentamiento.estado != ENFRENTAMIENTO_ELECCIONES_COMPLETAS:
        _error_materializacion_partidos(
            "ELECCIONES_NO_COMPLETAS",
            (
                "Los partidos solo pueden materializarse cuando ambas "
                "elecciones están bloqueadas."
            ),
        )

    elecciones = (
        session.query(ComunidadesEleccionAtacante)
        .filter(ComunidadesEleccionAtacante.enfrentamiento_id == enfrentamiento_id)
        .all()
    )
    por_equipo = {int(eleccion.equipo_id): eleccion for eleccion in elecciones}
    equipos_esperados = {
        int(enfrentamiento.equipo_a_id),
        int(enfrentamiento.equipo_b_id),
    }
    if set(por_equipo) != equipos_esperados or not all(
        bool(eleccion.bloqueada) for eleccion in elecciones
    ):
        _error_materializacion_partidos(
            "ELECCIONES_NO_BLOQUEADAS",
            "Deben existir dos elecciones bloqueadas, una por cada equipo.",
        )

    eleccion_a = por_equipo[int(enfrentamiento.equipo_a_id)]
    eleccion_b = por_equipo[int(enfrentamiento.equipo_b_id)]
    datos = (
        {
            "indice": 1,
            "equipo_local_id": int(enfrentamiento.equipo_a_id),
            "equipo_visitante_id": int(enfrentamiento.equipo_b_id),
            "usuario_local_id": int(eleccion_a.atacante_usuario_id),
            "usuario_visitante_id": int(eleccion_b.defensor_usuario_id),
            "atacante_usuario_id": int(eleccion_a.atacante_usuario_id),
            "defensor_usuario_id": int(eleccion_b.defensor_usuario_id),
        },
        {
            "indice": 2,
            "equipo_local_id": int(enfrentamiento.equipo_b_id),
            "equipo_visitante_id": int(enfrentamiento.equipo_a_id),
            "usuario_local_id": int(eleccion_b.atacante_usuario_id),
            "usuario_visitante_id": int(eleccion_a.defensor_usuario_id),
            "atacante_usuario_id": int(eleccion_b.atacante_usuario_id),
            "defensor_usuario_id": int(eleccion_a.defensor_usuario_id),
        },
    )
    partidos = tuple(
        ComunidadesPartido(
            torneo_id=int(enfrentamiento.torneo_id),
            enfrentamiento_id=int(enfrentamiento.id),
            estado="PENDIENTE",
            **cruce,
        )
        for cruce in datos
    )
    session.add_all(partidos)
    session.flush()
    return ResultadoMaterializacionPartidosComunidades(
        enfrentamiento=enfrentamiento,
        partidos=(partidos[0], partidos[1]),
        creados=True,
    )


class ErrorRegistroResultadoComunidades(ValueError):
    """Error funcional al persistir un resultado individual o resolver su serie."""

    def __init__(self, codigo: str, detalle: str):
        super().__init__(detalle)
        self.codigo = codigo
        self.detalle = detalle


def _error_registro_resultado(codigo: str, detalle: str) -> None:
    raise ErrorRegistroResultadoComunidades(codigo, detalle)


@dataclass(frozen=True)
class ResultadoRegistroPartidoComunidades:
    """Resultado persistido y posible resolución global disparada por el registro."""

    partido: Any
    enfrentamiento: Any
    enfrentamiento_resuelto: bool
    idempotente: bool
    resultado_global: Optional[ResultadoEnfrentamiento]


def _validar_td_resultado(valor: object, nombre: str) -> int:
    if type(valor) is not int or valor < 0:
        _error_registro_resultado(
            "TD_INVALIDOS", f"{nombre} debe ser un entero mayor o igual que cero."
        )
    return valor


def _normalizar_id_bloodbowl(valor: object) -> Optional[str]:
    if valor is None:
        return None
    if not isinstance(valor, str) or not valor.strip() or valor != valor.strip():
        _error_registro_resultado(
            "ID_BLOODBOWL_INVALIDO",
            "partido_bloodbowl_id debe ser un texto no vacío y sin espacios exteriores.",
        )
    if len(valor) > 45:
        _error_registro_resultado(
            "ID_BLOODBOWL_INVALIDO",
            "partido_bloodbowl_id no puede superar 45 caracteres.",
        )
    return valor


def _marcador_desde_partido(partido: Any, enfrentamiento: Any) -> MarcadorPartido:
    """Orienta un partido persistido como equipo A/equipo B."""
    equipo_a_id = int(enfrentamiento.equipo_a_id)
    equipo_b_id = int(enfrentamiento.equipo_b_id)
    local_id = int(partido.equipo_local_id)
    visitante_id = int(partido.equipo_visitante_id)
    if (local_id, visitante_id) == (equipo_a_id, equipo_b_id):
        td_a, td_b = int(partido.td_local), int(partido.td_visitante)
        equipo_atacante = (
            Equipo.A
            if int(partido.atacante_usuario_id) == int(partido.usuario_local_id)
            else Equipo.B
        )
    elif (local_id, visitante_id) == (equipo_b_id, equipo_a_id):
        td_a, td_b = int(partido.td_visitante), int(partido.td_local)
        equipo_atacante = (
            Equipo.B
            if int(partido.atacante_usuario_id) == int(partido.usuario_local_id)
            else Equipo.A
        )
    else:
        _error_registro_resultado(
            "PARTIDO_INCONSISTENTE",
            "Los equipos del partido no coinciden con los del enfrentamiento.",
        )
    if int(partido.atacante_usuario_id) not in {
        int(partido.usuario_local_id),
        int(partido.usuario_visitante_id),
    }:
        _error_registro_resultado(
            "PARTIDO_INCONSISTENTE",
            "El atacante del partido no coincide con ninguno de sus jugadores.",
        )
    return MarcadorPartido(td_a, td_b, equipo_atacante)


def _puntos_persistidos_desde_partido(
    partido: Any, enfrentamiento: Any
) -> PuntosInternosPartido:
    """Orienta los puntos internos persistidos como equipo A/equipo B."""
    local_id = int(partido.equipo_local_id)
    visitante_id = int(partido.equipo_visitante_id)
    equipo_a_id = int(enfrentamiento.equipo_a_id)
    equipo_b_id = int(enfrentamiento.equipo_b_id)
    local = Decimal(partido.puntos_internos_local)
    visitante = Decimal(partido.puntos_internos_visitante)
    if (local_id, visitante_id) == (equipo_a_id, equipo_b_id):
        return PuntosInternosPartido(local, visitante)
    if (local_id, visitante_id) == (equipo_b_id, equipo_a_id):
        return PuntosInternosPartido(visitante, local)
    _error_registro_resultado(
        "PARTIDO_INCONSISTENTE",
        "Los equipos del partido no coinciden con los del enfrentamiento.",
    )


def _incrementar_contadores_comunidad(
    comunidad: Any, *, puntos_zombificacion: Decimal, kills: int
) -> None:
    """Punto único de actualización para facilitar auditoría y rollback."""
    comunidad.puntos_zombificaciones = (
        Decimal(comunidad.puntos_zombificaciones or 0) + puntos_zombificacion
    )
    comunidad.zombies_matados = int(comunidad.zombies_matados or 0) + kills


def _aplicar_resultado_equipo(
    equipo: Any,
    *,
    puntos: Decimal,
    td_favor: int,
    td_contra: int,
    resultado: ResultadoGlobal,
    lado: Equipo,
    doble_forfait: bool = False,
) -> None:
    equipo.partidos_jugados = int(equipo.partidos_jugados or 0) + 1
    equipo.puntos_clasificacion = Decimal(equipo.puntos_clasificacion or 0) + puntos
    equipo.td_favor = int(equipo.td_favor or 0) + td_favor
    equipo.td_contra = int(equipo.td_contra or 0) + td_contra
    if doble_forfait:
        equipo.derrotas = int(equipo.derrotas or 0) + 1
    elif resultado is ResultadoGlobal.EMPATE:
        equipo.empates = int(equipo.empates or 0) + 1
    elif (resultado is ResultadoGlobal.VICTORIA_A and lado is Equipo.A) or (
        resultado is ResultadoGlobal.VICTORIA_B and lado is Equipo.B
    ):
        equipo.victorias = int(equipo.victorias or 0) + 1
    else:
        equipo.derrotas = int(equipo.derrotas or 0) + 1


def _resolver_enfrentamiento_persistido(
    session: Any, enfrentamiento: Any, partidos: tuple[Any, Any]
) -> ResultadoEnfrentamiento:
    from GestorSQL import (
        ComunidadesComunidad,
        ComunidadesEquipo,
        ComunidadesFotografiaEstado,
        ComunidadesHistorialTransicion,
    )

    torneo = enfrentamiento.torneo
    configuracion_individual = ConfiguracionPuntosIndividuales(
        torneo.puntos_individuales_victoria,
        torneo.puntos_individuales_empate,
        torneo.puntos_individuales_derrota,
    )
    configuracion_clasificacion = ConfiguracionPuntosClasificacion(
        torneo.puntos_clasificacion_victoria,
        torneo.puntos_clasificacion_empate,
        torneo.puntos_clasificacion_derrota,
    )
    resultado = calcular_resultado_enfrentamiento(
        tuple(_marcador_desde_partido(p, enfrentamiento) for p in partidos),
        configuracion_individual,
        configuracion_clasificacion,
    )
    puntos_persistidos = sumar_puntos_internos(
        tuple(_puntos_persistidos_desde_partido(p, enfrentamiento) for p in partidos)
    )
    decision = decidir_resultado_global(
        puntos_persistidos.puntos_a,
        puntos_persistidos.puntos_b,
        resultado.td_atacante_a,
        resultado.td_atacante_b,
        resultado.diferencia_td_a,
        resultado.diferencia_td_b,
    )
    clasificacion_a, clasificacion_b = asignar_puntos_clasificacion(
        decision.resultado, configuracion_clasificacion
    )
    resultado = replace(
        resultado,
        puntos_internos_a=puntos_persistidos.puntos_a,
        puntos_internos_b=puntos_persistidos.puntos_b,
        resultado=decision.resultado,
        ganador=decision.ganador,
        criterio_desempate=decision.criterio,
        puntos_clasificacion_a=clasificacion_a,
        puntos_clasificacion_b=clasificacion_b,
    )
    doble_forfait = all(p.tipo_forfait == TIPO_FORFAIT_DOBLE for p in partidos)
    if doble_forfait:
        resultado = replace(
            resultado,
            puntos_clasificacion_a=configuracion_clasificacion.derrota,
            puntos_clasificacion_b=configuracion_clasificacion.derrota,
        )

    fotografias = (
        session.query(ComunidadesFotografiaEstado)
        .filter(ComunidadesFotografiaEstado.enfrentamiento_id == enfrentamiento.id)
        .with_for_update()
        .all()
    )
    por_equipo = {int(f.equipo_id): f for f in fotografias}
    ids_equipos = (int(enfrentamiento.equipo_a_id), int(enfrentamiento.equipo_b_id))
    if len(fotografias) != 2 or set(por_equipo) != set(ids_equipos):
        _error_registro_resultado(
            "FOTOGRAFIA_INCOMPLETA",
            "El enfrentamiento necesita exactamente una fotografía inicial por equipo.",
        )
    equipos = {
        int(e.id): e
        for e in session.query(ComunidadesEquipo)
        .filter(ComunidadesEquipo.id.in_(ids_equipos))
        .with_for_update()
        .all()
    }
    comunidades_ids = {int(por_equipo[equipo_id].comunidad_id) for equipo_id in ids_equipos}
    comunidades = {
        int(c.id): c
        for c in session.query(ComunidadesComunidad)
        .filter(ComunidadesComunidad.id.in_(comunidades_ids))
        .with_for_update()
        .all()
    }
    if len(equipos) != 2 or set(comunidades) != comunidades_ids:
        _error_registro_resultado(
            "REFERENCIAS_INCOMPLETAS",
            "No se pudieron cargar los equipos o comunidades fotografiados.",
        )

    foto_a, foto_b = (por_equipo[equipo_id] for equipo_id in ids_equipos)
    inicial_a = EstadoFotografiado(EstadoTemporal(foto_a.estado_temporal), bool(foto_a.es_zombie))
    inicial_b = EstadoFotografiado(EstadoTemporal(foto_b.estado_temporal), bool(foto_b.es_zombie))
    transicion = resolver_transicion_estados(
        inicial_a,
        inicial_b,
        resultado.resultado,
        doble_forfait,
        int(foto_a.comunidad_id),
        int(foto_b.comunidad_id),
    )

    enfrentamiento.puntos_internos_a = resultado.puntos_internos_a
    enfrentamiento.puntos_internos_b = resultado.puntos_internos_b
    enfrentamiento.td_favor_a = resultado.td_favor_a
    enfrentamiento.td_contra_a = resultado.td_contra_a
    enfrentamiento.td_favor_b = resultado.td_favor_b
    enfrentamiento.td_contra_b = resultado.td_contra_b
    enfrentamiento.td_atacante_a = resultado.td_atacante_a
    enfrentamiento.td_atacante_b = resultado.td_atacante_b
    enfrentamiento.ganador_equipo_id = (
        ids_equipos[0]
        if resultado.ganador is Equipo.A
        else ids_equipos[1]
        if resultado.ganador is Equipo.B
        else None
    )
    enfrentamiento.puntos_clasificacion_a = resultado.puntos_clasificacion_a
    enfrentamiento.puntos_clasificacion_b = resultado.puntos_clasificacion_b
    enfrentamiento.es_doble_forfait = doble_forfait
    enfrentamiento.resultado_origen = (
        RESULTADO_ORIGEN_ADMIN
        if any(p.resultado_origen == RESULTADO_ORIGEN_ADMIN for p in partidos)
        else RESULTADO_ORIGEN_API
    )
    enfrentamiento.estado = (
        ENFRENTAMIENTO_ADMINISTRADO
        if enfrentamiento.resultado_origen == RESULTADO_ORIGEN_ADMIN
        else ENFRENTAMIENTO_CERRADO
    )

    equipo_a, equipo_b = (equipos[equipo_id] for equipo_id in ids_equipos)
    _aplicar_resultado_equipo(
        equipo_a,
        puntos=resultado.puntos_clasificacion_a,
        td_favor=resultado.td_favor_a,
        td_contra=resultado.td_contra_a,
        resultado=resultado.resultado,
        lado=Equipo.A,
        doble_forfait=doble_forfait,
    )
    _aplicar_resultado_equipo(
        equipo_b,
        puntos=resultado.puntos_clasificacion_b,
        td_favor=resultado.td_favor_b,
        td_contra=resultado.td_contra_b,
        resultado=resultado.resultado,
        lado=Equipo.B,
        doble_forfait=doble_forfait,
    )
    finales = (transicion.estado_final_a, transicion.estado_final_b)
    motivos = (transicion.motivo_a, transicion.motivo_b)
    efectos_puntos = {Equipo.A: Decimal("0"), Equipo.B: Decimal("0")}
    efectos_kills = {Equipo.A: 0, Equipo.B: 0}
    if transicion.punto_zombificacion is not None:
        efectos_puntos[transicion.punto_zombificacion.equipo] = Decimal("1")
    if transicion.kill is not None:
        efectos_kills[transicion.kill.equipo] = 1

    for lado, equipo, foto, final, motivo in zip(
        (Equipo.A, Equipo.B),
        (equipo_a, equipo_b),
        (foto_a, foto_b),
        finales,
        motivos,
    ):
        equipo.estado_temporal = final.estado_temporal.value
        equipo.es_zombie = final.es_zombie
        puntos_generados = efectos_puntos[lado]
        kills_generadas = efectos_kills[lado]
        comunidad = comunidades[int(foto.comunidad_id)]
        _incrementar_contadores_comunidad(
            comunidad,
            puntos_zombificacion=puntos_generados,
            kills=kills_generadas,
        )
        session.add(
            ComunidadesHistorialTransicion(
                torneo_id=enfrentamiento.torneo_id,
                ronda_id=enfrentamiento.ronda_id,
                enfrentamiento_id=enfrentamiento.id,
                equipo_id=equipo.id,
                estado_temporal_anterior=foto.estado_temporal,
                es_zombie_anterior=bool(foto.es_zombie),
                estado_temporal_posterior=final.estado_temporal.value,
                es_zombie_posterior=final.es_zombie,
                motivo=motivo.value,
                puntos_comunitarios_generados=puntos_generados,
                kills_generadas=kills_generadas,
            )
        )
    session.flush()
    return resultado


def registrar_resultado_partido_comunidades(
    session: Any,
    *,
    partido_id: int,
    td_local: int,
    td_visitante: int,
    origen: str,
    partido_bloodbowl_id: Optional[str] = None,
    tipo_forfait: Optional[str] = None,
) -> ResultadoRegistroPartidoComunidades:
    """Registra un partido y resuelve su enfrentamiento al cerrar el segundo.

    La función es la frontera transaccional común para API y administración. Un
    reintento idéntico devuelve el resultado ya persistido; uno contradictorio
    se rechaza. La resolución global completa ocurre dentro de un savepoint, de
    modo que cualquier fallo revierte también el primer registro de ese intento.
    """
    from GestorSQL import ComunidadesEnfrentamiento, ComunidadesPartido

    if type(partido_id) is not int or partido_id <= 0:
        _error_registro_resultado(
            "PARTIDO_INVALIDO", "partido_id debe ser un entero mayor que cero."
        )
    td_local = _validar_td_resultado(td_local, "td_local")
    td_visitante = _validar_td_resultado(td_visitante, "td_visitante")
    if origen not in {RESULTADO_ORIGEN_API, RESULTADO_ORIGEN_ADMIN}:
        _error_registro_resultado("ORIGEN_INVALIDO", "origen debe ser API o ADMIN.")
    partido_bloodbowl_id = _normalizar_id_bloodbowl(partido_bloodbowl_id)
    if origen == RESULTADO_ORIGEN_API and partido_bloodbowl_id is None:
        _error_registro_resultado(
            "ID_BLOODBOWL_REQUERIDO",
            "Los resultados de API requieren partido_bloodbowl_id.",
        )
    if tipo_forfait is not None and tipo_forfait not in TIPOS_FORFAIT:
        _error_registro_resultado(
            "FORFAIT_INVALIDO", "tipo_forfait debe ser LOCAL, VISITANTE o DOBLE."
        )
    if origen == RESULTADO_ORIGEN_API and tipo_forfait is not None:
        _error_registro_resultado(
            "FORFAIT_INVALIDO", "Los forfeits solo se registran por administración."
        )
    if tipo_forfait == TIPO_FORFAIT_DOBLE and (td_local, td_visitante) != (0, 0):
        _error_registro_resultado(
            "DOBLE_FORFAIT_INVALIDO", "Un doble forfait debe registrarse con TD 0-0."
        )

    with session.begin_nested():
        referencia = (
            session.query(
                ComunidadesPartido.id, ComunidadesPartido.enfrentamiento_id
            )
            .filter(ComunidadesPartido.id == partido_id)
            .one_or_none()
        )
        if referencia is None:
            _error_registro_resultado(
                "PARTIDO_NO_EXISTE", f"No existe el partido {partido_id}."
            )
        # Todos los resultados del mismo enfrentamiento bloquean primero la
        # misma fila padre y después sus partidos en orden estable. Así dos
        # resultados simultáneos no invierten el orden de locks ni resuelven
        # dos veces los contadores globales.
        enfrentamiento = (
            session.query(ComunidadesEnfrentamiento)
            .filter(ComunidadesEnfrentamiento.id == referencia.enfrentamiento_id)
            .with_for_update()
            .one()
        )
        partidos_bloqueados = tuple(
            session.query(ComunidadesPartido)
            .filter(
                ComunidadesPartido.enfrentamiento_id == enfrentamiento.id
            )
            .order_by(ComunidadesPartido.id)
            .with_for_update()
            .all()
        )
        partido = next(
            (item for item in partidos_bloqueados if int(item.id) == partido_id),
            None,
        )
        if partido is None:
            _error_registro_resultado(
                "PARTIDO_NO_EXISTE", f"No existe el partido {partido_id}."
            )
        if partido_bloodbowl_id is not None:
            duplicado = (
                session.query(ComunidadesPartido.id)
                .filter(
                    ComunidadesPartido.partido_bloodbowl_id == partido_bloodbowl_id,
                    ComunidadesPartido.id != partido.id,
                )
                .first()
            )
            if duplicado is not None:
                _error_registro_resultado(
                    "ID_BLOODBOWL_DUPLICADO",
                    "El ID de Blood Bowl ya está asociado a otro partido.",
                )

        estado_cerrado = partido.estado in {PARTIDO_FINALIZADO, PARTIDO_ADMINISTRADO}
        if estado_cerrado:
            coincide = (
                int(partido.td_local) == td_local
                and int(partido.td_visitante) == td_visitante
                and partido.resultado_origen == origen
                and partido.tipo_forfait == tipo_forfait
                and (
                    partido_bloodbowl_id is None
                    or partido.partido_bloodbowl_id == partido_bloodbowl_id
                )
            )
            if not coincide:
                _error_registro_resultado(
                    "RESULTADO_DUPLICADO_CONFLICTIVO",
                    "El partido ya tiene un resultado cerrado diferente.",
                )
            resuelto = enfrentamiento.estado in {
                ENFRENTAMIENTO_CERRADO,
                ENFRENTAMIENTO_ADMINISTRADO,
            }
            return ResultadoRegistroPartidoComunidades(
                partido, enfrentamiento, resuelto, True, None
            )
        if enfrentamiento.estado not in {
            ENFRENTAMIENTO_PARTIDOS_CREADOS,
            ENFRENTAMIENTO_EN_CURSO,
        }:
            _error_registro_resultado(
                "ENFRENTAMIENTO_NO_ADMITE_RESULTADOS",
                f"El enfrentamiento está en estado {enfrentamiento.estado}.",
            )
        if partido.partido_bloodbowl_id not in {None, partido_bloodbowl_id}:
            _error_registro_resultado(
                "ID_BLOODBOWL_CONFLICTIVO",
                "El partido ya tiene asociado otro ID de Blood Bowl.",
            )

        configuracion = ConfiguracionPuntosIndividuales(
            enfrentamiento.torneo.puntos_individuales_victoria,
            enfrentamiento.torneo.puntos_individuales_empate,
            enfrentamiento.torneo.puntos_individuales_derrota,
        )
        puntos = (
            PuntosInternosPartido(Decimal("0"), Decimal("0"))
            if tipo_forfait == TIPO_FORFAIT_DOBLE
            else convertir_marcador_en_puntos_internos(td_local, td_visitante, configuracion)
        )
        partido.td_local = td_local
        partido.td_visitante = td_visitante
        partido.puntos_internos_local = puntos.puntos_a
        partido.puntos_internos_visitante = puntos.puntos_b
        partido.resultado_origen = origen
        partido.tipo_forfait = tipo_forfait
        partido.partido_bloodbowl_id = partido_bloodbowl_id or partido.partido_bloodbowl_id
        partido.estado = (
            PARTIDO_ADMINISTRADO
            if origen == RESULTADO_ORIGEN_ADMIN
            else PARTIDO_FINALIZADO
        )
        session.flush()

        partidos = tuple(
            sorted(partidos_bloqueados, key=lambda item: int(item.indice))
        )
        if len(partidos) != 2:
            _error_registro_resultado(
                "PARTIDOS_INCOMPLETOS",
                "El enfrentamiento debe contener exactamente dos partidos.",
            )
        cerrados = [
            p for p in partidos if p.estado in {PARTIDO_FINALIZADO, PARTIDO_ADMINISTRADO}
        ]
        if len(cerrados) == 1:
            enfrentamiento.estado = ENFRENTAMIENTO_EN_CURSO
            session.flush()
            return ResultadoRegistroPartidoComunidades(
                partido, enfrentamiento, False, False, None
            )
        if len(cerrados) != 2:
            _error_registro_resultado(
                "ESTADO_PARTIDOS_INCONSISTENTE",
                "Los partidos del enfrentamiento tienen estados incompatibles.",
            )
        resultado_global = _resolver_enfrentamiento_persistido(
            session, enfrentamiento, partidos
        )
        return ResultadoRegistroPartidoComunidades(
            partido, enfrentamiento, True, False, resultado_global
        )


def administrar_partido_comunidades(
    session: Any,
    *,
    torneo_id: int,
    ronda_numero: int,
    enfrentamiento_id: int,
    partido_indice: int,
    td_local: int,
    td_visitante: int,
    tipo_forfait: Optional[str] = None,
) -> ResultadoRegistroPartidoComunidades:
    """Resuelve un partido administrativo y usa el cierre común de resultados.

    Este servicio valida que los cuatro identificadores pertenezcan al mismo
    contexto operativo. La persistencia del marcador y, al cerrar el segundo
    partido, la resolución global se delegan sin duplicación en
    :func:`registrar_resultado_partido_comunidades`, la misma frontera usada
    por la actualización desde la API.
    """
    from GestorSQL import (
        ComunidadesEnfrentamiento,
        ComunidadesPartido,
        ComunidadesRonda,
        ComunidadesTorneo,
    )

    for valor, nombre in (
        (torneo_id, "torneo_id"),
        (ronda_numero, "ronda_numero"),
        (enfrentamiento_id, "enfrentamiento_id"),
    ):
        if type(valor) is not int or valor <= 0:
            _error_registro_resultado(
                "IDENTIFICADOR_INVALIDO",
                f"{nombre} debe ser un entero mayor que cero.",
            )
    if type(partido_indice) is not int or partido_indice not in {1, 2}:
        _error_registro_resultado(
            "INDICE_PARTIDO_INVALIDO",
            "El índice de partido debe ser 1 o 2.",
        )

    torneo = (
        session.query(ComunidadesTorneo)
        .filter(ComunidadesTorneo.id == torneo_id)
        .one_or_none()
    )
    if torneo is None:
        _error_registro_resultado(
            "TORNEO_NO_EXISTE",
            f"No existe un torneo de comunidades con ID {torneo_id}.",
        )
    if torneo.estado != TORNEO_EN_CURSO:
        _error_registro_resultado(
            "TORNEO_NO_EN_CURSO",
            f"El torneo {torneo_id} está en estado {torneo.estado}; "
            "solo se administran partidos de torneos EN_CURSO.",
        )

    ronda = (
        session.query(ComunidadesRonda)
        .filter(
            ComunidadesRonda.torneo_id == torneo_id,
            ComunidadesRonda.numero == ronda_numero,
        )
        .one_or_none()
    )
    if ronda is None:
        _error_registro_resultado(
            "RONDA_NO_EXISTE",
            f"No existe la ronda {ronda_numero} en el torneo {torneo_id}.",
        )
    if ronda.estado != RONDA_ABIERTA:
        _error_registro_resultado(
            "RONDA_NO_ABIERTA",
            f"La ronda {ronda_numero} está en estado {ronda.estado}; "
            "solo se administran partidos de rondas ABIERTAS.",
        )

    enfrentamiento = (
        session.query(ComunidadesEnfrentamiento)
        .filter(
            ComunidadesEnfrentamiento.id == enfrentamiento_id,
            ComunidadesEnfrentamiento.torneo_id == torneo_id,
            ComunidadesEnfrentamiento.ronda_id == ronda.id,
        )
        .one_or_none()
    )
    if enfrentamiento is None:
        _error_registro_resultado(
            "ENFRENTAMIENTO_NO_EXISTE",
            f"No existe el enfrentamiento {enfrentamiento_id} en la ronda "
            f"{ronda_numero} del torneo {torneo_id}.",
        )

    partido = (
        session.query(ComunidadesPartido)
        .filter(
            ComunidadesPartido.torneo_id == torneo_id,
            ComunidadesPartido.enfrentamiento_id == enfrentamiento_id,
            ComunidadesPartido.indice == partido_indice,
        )
        .one_or_none()
    )
    if partido is None:
        _error_registro_resultado(
            "PARTIDO_NO_EXISTE",
            f"El enfrentamiento {enfrentamiento_id} no tiene creado el partido "
            f"{partido_indice}.",
        )
    if partido.estado in {PARTIDO_FINALIZADO, PARTIDO_ADMINISTRADO}:
        _error_registro_resultado(
            "PARTIDO_YA_CERRADO",
            f"El partido {partido_indice} ya está cerrado con estado "
            f"{partido.estado} y no puede administrarse de nuevo.",
        )

    return registrar_resultado_partido_comunidades(
        session,
        partido_id=int(partido.id),
        td_local=td_local,
        td_visitante=td_visitante,
        origen=RESULTADO_ORIGEN_ADMIN,
        tipo_forfait=tipo_forfait,
    )


class ErrorGeneracionRondaComunidades(ValueError):
    """Error funcional que cancela por completo la generación de una ronda."""

    def __init__(self, codigo: str, detalle: str):
        super().__init__(detalle)
        self.codigo = codigo
        self.detalle = detalle


def _error_generacion(codigo: str, detalle: str) -> None:
    raise ErrorGeneracionRondaComunidades(codigo, detalle)


def _validar_generacion_ronda_comunidades(
    session: Any,
    torneo: Any,
    ronda_numero: int,
) -> Optional[Any]:
    """Valida la secuencia y devuelve la ronda anterior cuando corresponde."""
    from GestorSQL import ComunidadesEquipo, ComunidadesMiembro, ComunidadesRonda

    if ronda_numero < 1 or ronda_numero > int(torneo.rondas_totales):
        _error_generacion(
            "NUMERO_RONDA_INVALIDO",
            f"La ronda debe estar entre 1 y {int(torneo.rondas_totales)}.",
        )

    existente = (
        session.query(ComunidadesRonda)
        .filter(
            ComunidadesRonda.torneo_id == torneo.id,
            ComunidadesRonda.numero == ronda_numero,
        )
        .one_or_none()
    )
    if existente is not None:
        _error_generacion("RONDA_DUPLICADA", "La ronda solicitada ya existe.")

    incompatible = (
        session.query(ComunidadesRonda)
        .filter(
            ComunidadesRonda.torneo_id == torneo.id,
            ComunidadesRonda.estado.in_(["ABIERTA", "BLOQUEADA"]),
        )
        .first()
    )
    if incompatible is not None:
        _error_generacion(
            "RONDA_ABIERTA_INCOMPATIBLE",
            f"La ronda {int(incompatible.numero)} todavía no está cerrada.",
        )

    if ronda_numero == 1:
        if torneo.estado != "CREADO":
            _error_generacion(
                "ESTADO_TORNEO_INVALIDO",
                "La ronda 1 solo puede generarse con el torneo en estado CREADO.",
            )
        ronda_anterior = None
    else:
        if torneo.estado != "EN_CURSO":
            _error_generacion(
                "ESTADO_TORNEO_INVALIDO",
                "Las rondas posteriores requieren un torneo EN_CURSO.",
            )
        ronda_anterior = (
            session.query(ComunidadesRonda)
            .filter(
                ComunidadesRonda.torneo_id == torneo.id,
                ComunidadesRonda.numero == ronda_numero - 1,
            )
            .one_or_none()
        )
        if ronda_anterior is None:
            _error_generacion(
                "RONDA_ANTERIOR_INEXISTENTE",
                f"No existe la ronda {ronda_numero - 1}.",
            )
        if ronda_anterior.estado != "CERRADA":
            _error_generacion(
                "RONDA_ANTERIOR_NO_CERRADA",
                f"La ronda {ronda_numero - 1} no está cerrada.",
            )

    equipos = (
        session.query(ComunidadesEquipo)
        .filter(ComunidadesEquipo.torneo_id == torneo.id)
        .with_for_update()
        .all()
    )
    if not equipos:
        _error_generacion("SIN_EQUIPOS", "El torneo no tiene equipos inscritos.")

    # Se comprueba explícitamente para conservar la invariante incluso en bases
    # creadas antes de los constraints actuales.
    for equipo in equipos:
        cantidad = (
            session.query(ComunidadesMiembro)
            .filter(ComunidadesMiembro.equipo_id == equipo.id)
            .count()
        )
        if cantidad != 2:
            _error_generacion(
                "EQUIPO_INCOMPLETO",
                f"El equipo {int(equipo.id)} debe tener exactamente dos miembros.",
            )
    return ronda_anterior


def _guardar_traza_generacion(
    session: Any,
    torneo_id: int,
    ronda_id: int,
    pairings: list[PairingComunidades],
    traza: TrazaPairingsComunidades,
) -> None:
    from GestorSQL import ComunidadesTrazaEmparejamiento

    secuencia = 1
    for intento in traza.get("intentos", []):
        bye_id = intento.get("bye_equipo_id")
        session.add(
            ComunidadesTrazaEmparejamiento(
                torneo_id=torneo_id,
                ronda_id=ronda_id,
                secuencia=secuencia,
                etapa=intento["etapa"],
                equipo_a_id=bye_id,
                detalle=json.dumps(intento, ensure_ascii=False, default=str),
            )
        )
        secuencia += 1

    for pairing in pairings:
        es_bye = bool(pairing["es_bye"])
        detalle = {
            "tipo": "BYE" if es_bye else "PAIRING",
            "nivel_fallback": traza.get("nivel_fallback"),
            "fallback_utilizado": traza.get("etapa"),
            "mesa_numero": pairing["mesa_numero"],
        }
        session.add(
            ComunidadesTrazaEmparejamiento(
                torneo_id=torneo_id,
                ronda_id=ronda_id,
                secuencia=secuencia,
                etapa="SELECCION_BYE" if es_bye else "SELECCION_FINAL",
                equipo_a_id=pairing["equipo_a_id"],
                equipo_b_id=pairing["equipo_b_id"],
                diferencia_puntos=pairing["diferencia_puntos"],
                es_mirror=pairing["es_mirror"],
                es_rival_repetido=pairing["es_rival_repetido"],
                prioridad_estado=pairing["prioridad_estado"],
                detalle=json.dumps(detalle, ensure_ascii=False),
            )
        )
        secuencia += 1


def _persistir_ronda_comunidades(
    session: Any,
    *,
    torneo: Any,
    ronda_numero: int,
    generada_por_discord_id: int,
    pairings: list[PairingComunidades],
    traza: TrazaPairingsComunidades,
    ronda_anterior: Optional[Any],
    on_enfrentamiento_persistido: Any = None,
) -> dict[str, Any]:
    """Persiste una ronda ya validada dentro de la transacción del llamador."""
    from GestorSQL import (
        ComunidadesEnfrentamiento,
        ComunidadesEquipo,
        ComunidadesFotografiaEstado,
        ComunidadesHistorialTransicion,
        ComunidadesRonda,
    )

    torneo_id = int(torneo.id)
    if ronda_numero == 1:
        fecha_fin = torneo.fecha_fin_ronda1
        fecha_inicio = fecha_fin - timedelta(days=int(torneo.dias_por_ronda))
    else:
        fecha_inicio = ronda_anterior.fecha_fin
        fecha_fin = fecha_inicio + timedelta(days=int(torneo.dias_por_ronda))

    ronda = ComunidadesRonda(
        torneo_id=torneo_id,
        numero=ronda_numero,
        estado="ABIERTA",
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        generada_por_discord_id=generada_por_discord_id,
    )
    session.add(ronda)
    session.flush()

    equipos = {
        int(equipo.id): equipo
        for equipo in session.query(ComunidadesEquipo)
        .filter(ComunidadesEquipo.torneo_id == torneo_id)
        .with_for_update()
        .all()
    }
    enfrentamiento_ids: list[int] = []
    bye_equipo_id: Optional[int] = None

    for pairing in pairings:
        equipo_a = equipos[int(pairing["equipo_a_id"])]
        if pairing["es_bye"]:
            bye_equipo_id = int(equipo_a.id)
            estado_anterior = equipo_a.estado_temporal
            zombie_anterior = bool(equipo_a.es_zombie)
            equipo_a.estado_temporal = EstadoTemporal.NEUTRO.value
            equipo_a.cantidad_byes = int(equipo_a.cantidad_byes or 0) + 1
            equipo_a.puntos_clasificacion = _decimal(
                equipo_a.puntos_clasificacion
            ) + _decimal(torneo.puntos_clasificacion_bye)
            session.add(
                ComunidadesHistorialTransicion(
                    torneo_id=torneo_id,
                    ronda_id=ronda.id,
                    enfrentamiento_id=None,
                    equipo_id=equipo_a.id,
                    estado_temporal_anterior=estado_anterior,
                    es_zombie_anterior=zombie_anterior,
                    estado_temporal_posterior=EstadoTemporal.NEUTRO.value,
                    es_zombie_posterior=zombie_anterior,
                    motivo="BYE",
                )
            )
            continue

        equipo_b = equipos[int(pairing["equipo_b_id"])]
        enfrentamiento = ComunidadesEnfrentamiento(
            torneo_id=torneo_id,
            ronda_id=ronda.id,
            mesa_numero=pairing["mesa_numero"],
            equipo_a_id=equipo_a.id,
            equipo_b_id=equipo_b.id,
            estado="PENDIENTE_ELECCIONES",
        )
        session.add(enfrentamiento)
        session.flush()
        enfrentamiento_ids.append(int(enfrentamiento.id))

        for equipo in (equipo_a, equipo_b):
            session.add(
                ComunidadesFotografiaEstado(
                    torneo_id=torneo_id,
                    ronda_id=ronda.id,
                    enfrentamiento_id=enfrentamiento.id,
                    equipo_id=equipo.id,
                    comunidad_id=equipo.comunidad_id,
                    es_zombie=bool(equipo.es_zombie),
                    estado_temporal=equipo.estado_temporal,
                )
            )
        session.flush()
        if on_enfrentamiento_persistido is not None:
            on_enfrentamiento_persistido(enfrentamiento)

    _guardar_traza_generacion(session, torneo_id, ronda.id, pairings, traza)
    if ronda_numero == 1:
        torneo.estado = "EN_CURSO"

    session.flush()
    return {
        "torneo_id": torneo_id,
        "ronda_id": int(ronda.id),
        "ronda_numero": int(ronda_numero),
        "enfrentamiento_ids": enfrentamiento_ids,
        "bye_equipo_id": bye_equipo_id,
        "nivel_fallback": traza.get("nivel_fallback"),
        "etapa": traza.get("etapa"),
    }


def generar_ronda_comunidades(
    session: Any,
    torneo_id: int,
    ronda_numero: int,
    generada_por_discord_id: int,
    rng: Any = None,
    *,
    on_enfrentamiento_persistido: Any = None,
) -> dict[str, Any]:
    """Genera y confirma una ronda completa sin realizar operaciones Discord."""
    from GestorSQL import ComunidadesTorneo

    try:
        torneo = (
            session.query(ComunidadesTorneo)
            .filter(ComunidadesTorneo.id == torneo_id)
            .with_for_update()
            .one_or_none()
        )
        if torneo is None:
            _error_generacion("TORNEO_INEXISTENTE", "El torneo no existe.")

        ronda_anterior = _validar_generacion_ronda_comunidades(
            session, torneo, ronda_numero
        )
        pairings, traza = generar_pairings_comunidades_backtracking(
            session, torneo_id, ronda_numero, rng
        )
        if not pairings:
            error = traza.get("error") or {}
            _error_generacion(
                error.get("codigo", "SIN_SOLUCION_COMPLETA"),
                error.get("detalle", "No existe una solución completa."),
            )

        resultado = _persistir_ronda_comunidades(
            session,
            torneo=torneo,
            ronda_numero=ronda_numero,
            generada_por_discord_id=generada_por_discord_id,
            pairings=pairings,
            traza=traza,
            ronda_anterior=ronda_anterior,
            on_enfrentamiento_persistido=on_enfrentamiento_persistido,
        )
        session.commit()
        return resultado
    except Exception:
        session.rollback()
        raise


def _restar_contador_regeneracion(valor: object, decremento: object, nombre: str):
    actual = _decimal(valor)
    resultado = actual - _decimal(decremento)
    if resultado < 0:
        _error_generacion(
            "AUDITORIA_INCONSISTENTE",
            f"La reversión dejaría {nombre} con un valor negativo.",
        )
    return resultado


def _revertir_ronda_comunidades(session: Any, *, torneo: Any, ronda: Any) -> None:
    """Revierte efectos usando exclusivamente la auditoría completa de la ronda."""
    from GestorSQL import (
        ComunidadesComunidad,
        ComunidadesEnfrentamiento,
        ComunidadesEquipo,
        ComunidadesFotografiaEstado,
        ComunidadesHistorialTransicion,
        ComunidadesHistorialTransferencia,
        ComunidadesSnapshotClasificacionComunidad,
        ComunidadesSnapshotClasificacionEquipo,
        ComunidadesTrazaEmparejamiento,
    )

    ronda_id = int(ronda.id)
    snapshots = (
        session.query(ComunidadesSnapshotClasificacionEquipo)
        .filter(ComunidadesSnapshotClasificacionEquipo.ronda_id == ronda_id)
        .count()
        + session.query(ComunidadesSnapshotClasificacionComunidad)
        .filter(ComunidadesSnapshotClasificacionComunidad.ronda_id == ronda_id)
        .count()
    )
    if snapshots:
        _error_generacion(
            "RONDA_CONSOLIDADA",
            "La ronda tiene snapshots consolidados y no puede regenerarse.",
        )

    equipos = {
        int(e.id): e
        for e in session.query(ComunidadesEquipo)
        .filter(ComunidadesEquipo.torneo_id == torneo.id)
        .with_for_update()
        .all()
    }
    comunidades = {
        int(c.id): c
        for c in session.query(ComunidadesComunidad)
        .filter(ComunidadesComunidad.torneo_id == torneo.id)
        .with_for_update()
        .all()
    }
    fotografias = {
        (int(f.enfrentamiento_id), int(f.equipo_id)): f
        for f in session.query(ComunidadesFotografiaEstado)
        .filter(ComunidadesFotografiaEstado.ronda_id == ronda_id)
        .all()
    }
    transiciones = (
        session.query(ComunidadesHistorialTransicion)
        .filter(ComunidadesHistorialTransicion.ronda_id == ronda_id)
        .order_by(
            ComunidadesHistorialTransicion.created_at.desc(),
            ComunidadesHistorialTransicion.id.desc(),
        )
        .with_for_update()
        .all()
    )
    for transicion in transiciones:
        equipo = equipos.get(int(transicion.equipo_id))
        if equipo is None:
            _error_generacion("AUDITORIA_INCONSISTENTE", "Falta un equipo auditado.")
        if (
            str(equipo.estado_temporal) != str(transicion.estado_temporal_posterior)
            or bool(equipo.es_zombie) != bool(transicion.es_zombie_posterior)
        ):
            _error_generacion(
                "AUDITORIA_INCONSISTENTE",
                f"El estado actual del equipo {int(equipo.id)} no coincide con el historial.",
            )
        equipo.estado_temporal = transicion.estado_temporal_anterior
        equipo.es_zombie = bool(transicion.es_zombie_anterior)

        puntos = _decimal(transicion.puntos_comunitarios_generados)
        kills = int(transicion.kills_generadas or 0)
        if puntos or kills:
            clave = (int(transicion.enfrentamiento_id), int(transicion.equipo_id))
            fotografia = fotografias.get(clave)
            if fotografia is None or int(fotografia.comunidad_id) not in comunidades:
                _error_generacion(
                    "AUDITORIA_INCONSISTENTE",
                    "Falta la fotografía necesaria para revertir contadores comunitarios.",
                )
            comunidad = comunidades[int(fotografia.comunidad_id)]
            comunidad.puntos_zombificaciones = _restar_contador_regeneracion(
                comunidad.puntos_zombificaciones, puntos, "puntos comunitarios"
            )
            comunidad.zombies_matados = int(
                _restar_contador_regeneracion(
                    comunidad.zombies_matados, kills, "zombies matados"
                )
            )

    enfrentamientos = (
        session.query(ComunidadesEnfrentamiento)
        .filter(ComunidadesEnfrentamiento.ronda_id == ronda_id)
        .with_for_update()
        .all()
    )
    for enfrentamiento in enfrentamientos:
        if enfrentamiento.estado not in {ENFRENTAMIENTO_CERRADO, ENFRENTAMIENTO_ADMINISTRADO}:
            continue
        equipo_a = equipos[int(enfrentamiento.equipo_a_id)]
        equipo_b = equipos[int(enfrentamiento.equipo_b_id)]
        for equipo, puntos, td_favor, td_contra in (
            (equipo_a, enfrentamiento.puntos_clasificacion_a, enfrentamiento.td_favor_a, enfrentamiento.td_contra_a),
            (equipo_b, enfrentamiento.puntos_clasificacion_b, enfrentamiento.td_favor_b, enfrentamiento.td_contra_b),
        ):
            equipo.partidos_jugados = int(
                _restar_contador_regeneracion(equipo.partidos_jugados, 1, "partidos jugados")
            )
            equipo.puntos_clasificacion = _restar_contador_regeneracion(
                equipo.puntos_clasificacion, puntos, "puntos de clasificación"
            )
            equipo.td_favor = int(
                _restar_contador_regeneracion(equipo.td_favor, td_favor, "TD a favor")
            )
            equipo.td_contra = int(
                _restar_contador_regeneracion(equipo.td_contra, td_contra, "TD en contra")
            )
        if bool(enfrentamiento.es_doble_forfait):
            equipo_a.derrotas = int(_restar_contador_regeneracion(equipo_a.derrotas, 1, "derrotas"))
            equipo_b.derrotas = int(_restar_contador_regeneracion(equipo_b.derrotas, 1, "derrotas"))
        elif enfrentamiento.ganador_equipo_id is None:
            equipo_a.empates = int(_restar_contador_regeneracion(equipo_a.empates, 1, "empates"))
            equipo_b.empates = int(_restar_contador_regeneracion(equipo_b.empates, 1, "empates"))
        else:
            ganador_id = int(enfrentamiento.ganador_equipo_id)
            ganador = equipo_a if int(equipo_a.id) == ganador_id else equipo_b
            perdedor = equipo_b if ganador is equipo_a else equipo_a
            ganador.victorias = int(_restar_contador_regeneracion(ganador.victorias, 1, "victorias"))
            perdedor.derrotas = int(_restar_contador_regeneracion(perdedor.derrotas, 1, "derrotas"))

    for transicion in transiciones:
        if transicion.motivo != "BYE":
            continue
        equipo = equipos[int(transicion.equipo_id)]
        equipo.cantidad_byes = int(
            _restar_contador_regeneracion(equipo.cantidad_byes, 1, "byes")
        )
        equipo.puntos_clasificacion = _restar_contador_regeneracion(
            equipo.puntos_clasificacion,
            torneo.puntos_clasificacion_bye,
            "puntos de clasificación por bye",
        )

    session.query(ComunidadesHistorialTransferencia).filter(
        ComunidadesHistorialTransferencia.ronda_id == ronda_id
    ).delete(synchronize_session=False)
    session.query(ComunidadesHistorialTransicion).filter(
        ComunidadesHistorialTransicion.ronda_id == ronda_id
    ).delete(synchronize_session=False)
    session.query(ComunidadesTrazaEmparejamiento).filter(
        ComunidadesTrazaEmparejamiento.ronda_id == ronda_id
    ).delete(synchronize_session=False)
    for enfrentamiento in enfrentamientos:
        session.delete(enfrentamiento)
    session.flush()
    session.delete(ronda)
    session.flush()


def regenerar_ronda_comunidades(
    session: Any,
    torneo_id: int,
    ronda_numero: int,
    generada_por_discord_id: int,
    rng: Any = None,
    *,
    confirmar: bool = True,
) -> dict[str, Any]:
    """Revierte y reemplaza atómicamente la última ronda abierta."""
    from GestorSQL import ComunidadesRonda, ComunidadesTorneo

    try:
        torneo = (
            session.query(ComunidadesTorneo)
            .filter(ComunidadesTorneo.id == torneo_id)
            .with_for_update()
            .one_or_none()
        )
        if torneo is None:
            _error_generacion("TORNEO_INEXISTENTE", "El torneo no existe.")
        if torneo.estado != TORNEO_EN_CURSO:
            _error_generacion(
                "ESTADO_TORNEO_INVALIDO",
                "Solo se regeneran rondas de torneos EN_CURSO.",
            )
        ronda = (
            session.query(ComunidadesRonda)
            .filter_by(torneo_id=torneo_id, numero=ronda_numero)
            .with_for_update()
            .one_or_none()
        )
        if ronda is None:
            _error_generacion("RONDA_INEXISTENTE", "La ronda solicitada no existe.")
        if ronda.estado != RONDA_ABIERTA:
            _error_generacion(
                "RONDA_NO_ABIERTA",
                "Solo puede regenerarse una ronda ABIERTA y no consolidada.",
            )
        posterior = (
            session.query(ComunidadesRonda.id)
            .filter(
                ComunidadesRonda.torneo_id == torneo_id,
                ComunidadesRonda.numero > ronda_numero,
            )
            .first()
        )
        if posterior is not None:
            _error_generacion(
                "RONDA_HISTORICA",
                "No puede regenerarse una ronda seguida por rondas posteriores.",
            )

        ronda_anterior = (
            None
            if ronda_numero == 1
            else session.query(ComunidadesRonda)
            .filter_by(torneo_id=torneo_id, numero=ronda_numero - 1)
            .one_or_none()
        )
        if ronda_numero > 1 and (ronda_anterior is None or ronda_anterior.estado != "CERRADA"):
            _error_generacion(
                "RONDA_ANTERIOR_NO_CERRADA",
                "La ronda anterior debe existir y estar cerrada.",
            )

        ronda_anterior_id = int(ronda.id)
        _revertir_ronda_comunidades(session, torneo=torneo, ronda=ronda)
        pairings, traza = generar_pairings_comunidades_backtracking(
            session, torneo_id, ronda_numero, rng
        )
        if not pairings:
            error = traza.get("error") or {}
            _error_generacion(
                error.get("codigo", "SIN_SOLUCION_COMPLETA"),
                error.get("detalle", "No existe una solución completa."),
            )
        resultado = _persistir_ronda_comunidades(
            session,
            torneo=torneo,
            ronda_numero=ronda_numero,
            generada_por_discord_id=generada_por_discord_id,
            pairings=pairings,
            traza=traza,
            ronda_anterior=ronda_anterior,
        )
        resultado["ronda_anterior_id"] = ronda_anterior_id
        if confirmar:
            session.commit()
        return resultado
    except Exception:
        session.rollback()
        raise


# Alias legible para consumidores que prefieran el orden verbo-ámbito-técnica.
generar_pairings_backtracking_comunidades = generar_pairings_comunidades_backtracking


# ---------------------------------------------------------------------------
# Clasificaciones acumuladas
# ---------------------------------------------------------------------------

FilaClasificacion = dict[str, Any]


def _decimal(valor: Any) -> Decimal:
    """Normaliza valores numéricos de ORM/diccionarios sin perder precisión."""
    if isinstance(valor, Decimal):
        return valor
    return Decimal(str(valor or 0))


def _valor(registro: Any, campo: str, default: Any = None) -> Any:
    if isinstance(registro, dict):
        return registro.get(campo, default)
    return getattr(registro, campo, default)


def calcular_h2h_equipos(
    clasificacion: list[FilaClasificacion],
    enfrentamientos_cerrados: Iterable[Any],
) -> dict[int, Optional[Decimal]]:
    """Calcula el enfrentamiento directo dentro de cada empate a puntos.

    Un equipo solo recibe valor si disputó al menos un enfrentamiento real
    contra otro integrante de su grupo empatado. Los byes no se representan
    como enfrentamientos y, por tanto, nunca participan en este cálculo.
    """
    h2h: dict[int, Optional[Decimal]] = {
        int(fila["equipo_id"]): None for fila in clasificacion
    }
    empatados: dict[Decimal, list[int]] = {}
    for fila in clasificacion:
        empatados.setdefault(_decimal(fila.get("puntos")), []).append(
            int(fila["equipo_id"])
        )

    for equipos in empatados.values():
        if len(equipos) < 2:
            continue
        conjunto = set(equipos)
        acumulado = {equipo_id: Decimal("0") for equipo_id in equipos}
        aplicable = {equipo_id: False for equipo_id in equipos}

        for enfrentamiento in enfrentamientos_cerrados:
            equipo_a_id = _valor(enfrentamiento, "equipo_a_id")
            equipo_b_id = _valor(enfrentamiento, "equipo_b_id")
            if equipo_a_id is None or equipo_b_id is None:
                continue
            equipo_a_id = int(equipo_a_id)
            equipo_b_id = int(equipo_b_id)
            if equipo_a_id not in conjunto or equipo_b_id not in conjunto:
                continue

            acumulado[equipo_a_id] += _decimal(
                _valor(enfrentamiento, "puntos_clasificacion_a")
            )
            acumulado[equipo_b_id] += _decimal(
                _valor(enfrentamiento, "puntos_clasificacion_b")
            )
            aplicable[equipo_a_id] = True
            aplicable[equipo_b_id] = True

        for equipo_id in equipos:
            if aplicable[equipo_id]:
                h2h[equipo_id] = acumulado[equipo_id]

    return h2h


def ordenar_clasificacion_equipos(
    clasificacion: list[FilaClasificacion],
) -> list[FilaClasificacion]:
    """Ordena la clasificación publicada y asigna posiciones consecutivas.

    El ID es exclusivamente el último desempate determinista de esta
    clasificación publicada. No debe reutilizarse como desempate de pairing.
    """

    def comparar(a: FilaClasificacion, b: FilaClasificacion) -> int:
        for campo in ("puntos", "buchholz_cut"):
            valor_a = _decimal(a.get(campo))
            valor_b = _decimal(b.get(campo))
            if valor_a != valor_b:
                return -1 if valor_a > valor_b else 1

        h2h_a = a.get("h2h_valor")
        h2h_b = b.get("h2h_valor")
        if h2h_a is not None and h2h_b is not None:
            valor_a = _decimal(h2h_a)
            valor_b = _decimal(h2h_b)
            if valor_a != valor_b:
                return -1 if valor_a > valor_b else 1

        diferencia_a = int(a.get("diferencia_td") or 0)
        diferencia_b = int(b.get("diferencia_td") or 0)
        if diferencia_a != diferencia_b:
            return -1 if diferencia_a > diferencia_b else 1

        equipo_a = int(a["equipo_id"])
        equipo_b = int(b["equipo_id"])
        if equipo_a != equipo_b:
            return -1 if equipo_a < equipo_b else 1
        return 0

    ordenada = sorted(clasificacion, key=cmp_to_key(comparar))
    for posicion, fila in enumerate(ordenada, start=1):
        fila["posicion"] = posicion
    return ordenada


def calcular_clasificacion_equipos(
    session: Any,
    torneo_id: int,
    hasta_ronda: Optional[int] = None,
) -> list[FilaClasificacion]:
    """Calcula estadísticas y desempates actuales de todos los equipos.

    Solo cuentan enfrentamientos ``CERRADO`` o ``ADMINISTRADO``. Los byes se
    reconstruyen desde las transiciones con motivo ``BYE``: suman la
    puntuación configurada y el contador de byes, pero no PJ, PG, PE ni PP,
    no añaden TD, rival, Buchholz directo ni H2H.
    """
    from GestorSQL import (
        ComunidadesEnfrentamiento,
        ComunidadesEquipo,
        ComunidadesHistorialTransicion,
        ComunidadesRonda,
        ComunidadesTorneo,
    )

    torneo = (
        session.query(ComunidadesTorneo)
        .filter(ComunidadesTorneo.id == torneo_id)
        .one_or_none()
    )
    if torneo is None:
        return []

    equipos = (
        session.query(ComunidadesEquipo)
        .filter(ComunidadesEquipo.torneo_id == torneo_id)
        .all()
    )
    filas: dict[int, FilaClasificacion] = {}
    rivales: dict[int, list[int]] = {}
    for equipo in equipos:
        filas[equipo.id] = {
            "equipo_id": int(equipo.id),
            "comunidad_id": int(equipo.comunidad_id),
            "nombre": equipo.nombre,
            "pj": 0,
            "pg": 0,
            "pe": 0,
            "pp": 0,
            "cantidad_byes": 0,
            "puntos": Decimal("0"),
            "td_favor": 0,
            "td_contra": 0,
            "diferencia_td": 0,
            "buchholz_cut": Decimal("0"),
            "h2h_valor": None,
        }
        rivales[equipo.id] = []

    consulta = (
        session.query(ComunidadesEnfrentamiento)
        .join(ComunidadesRonda, ComunidadesRonda.id == ComunidadesEnfrentamiento.ronda_id)
        .filter(
            ComunidadesEnfrentamiento.torneo_id == torneo_id,
            ComunidadesEnfrentamiento.estado.in_(["CERRADO", "ADMINISTRADO"]),
        )
    )
    if hasta_ronda is not None:
        consulta = consulta.filter(ComunidadesRonda.numero <= hasta_ronda)
    enfrentamientos = consulta.all()

    for enfrentamiento in enfrentamientos:
        equipo_a_id = int(enfrentamiento.equipo_a_id)
        equipo_b_id = int(enfrentamiento.equipo_b_id)
        if equipo_a_id not in filas or equipo_b_id not in filas:
            continue
        fila_a = filas[equipo_a_id]
        fila_b = filas[equipo_b_id]
        fila_a["pj"] += 1
        fila_b["pj"] += 1
        fila_a["puntos"] += _decimal(enfrentamiento.puntos_clasificacion_a)
        fila_b["puntos"] += _decimal(enfrentamiento.puntos_clasificacion_b)
        fila_a["td_favor"] += int(enfrentamiento.td_favor_a or 0)
        fila_a["td_contra"] += int(enfrentamiento.td_contra_a or 0)
        fila_b["td_favor"] += int(enfrentamiento.td_favor_b or 0)
        fila_b["td_contra"] += int(enfrentamiento.td_contra_b or 0)
        rivales[equipo_a_id].append(equipo_b_id)
        rivales[equipo_b_id].append(equipo_a_id)

        ganador_id = enfrentamiento.ganador_equipo_id
        if enfrentamiento.es_doble_forfait:
            fila_a["pp"] += 1
            fila_b["pp"] += 1
        elif ganador_id is None:
            fila_a["pe"] += 1
            fila_b["pe"] += 1
        elif int(ganador_id) == equipo_a_id:
            fila_a["pg"] += 1
            fila_b["pp"] += 1
        elif int(ganador_id) == equipo_b_id:
            fila_b["pg"] += 1
            fila_a["pp"] += 1

    consulta_byes = (
        session.query(ComunidadesHistorialTransicion)
        .join(ComunidadesRonda, ComunidadesRonda.id == ComunidadesHistorialTransicion.ronda_id)
        .filter(
            ComunidadesHistorialTransicion.torneo_id == torneo_id,
            ComunidadesHistorialTransicion.motivo == "BYE",
        )
    )
    if hasta_ronda is not None:
        consulta_byes = consulta_byes.filter(ComunidadesRonda.numero <= hasta_ronda)
    for transicion in consulta_byes.all():
        equipo_id = int(transicion.equipo_id)
        if equipo_id in filas:
            filas[equipo_id]["cantidad_byes"] += 1
            filas[equipo_id]["puntos"] += _decimal(
                torneo.puntos_clasificacion_bye
            )

    for equipo_id, fila in filas.items():
        fila["diferencia_td"] = fila["td_favor"] - fila["td_contra"]
        puntos_rivales = [filas[rival]["puntos"] for rival in rivales[equipo_id]]
        if len(puntos_rivales) >= 2:
            fila["buchholz_cut"] = sum(
                puntos_rivales, Decimal("0")
            ) - min(puntos_rivales)

    clasificacion = list(filas.values())
    h2h = calcular_h2h_equipos(clasificacion, enfrentamientos)
    for fila in clasificacion:
        fila["h2h_valor"] = h2h[fila["equipo_id"]]
    return ordenar_clasificacion_equipos(clasificacion)


def calcular_clasificacion_comunidades(
    session: Any,
    torneo_id: int,
    hasta_ronda: Optional[int] = None,
    clasificacion_equipos: Optional[list[FilaClasificacion]] = None,
) -> list[FilaClasificacion]:
    """Calcula la clasificación comunitaria con posiciones compartidas."""
    from GestorSQL import (
        ComunidadesComunidad,
        ComunidadesEquipo,
        ComunidadesHistorialTransicion,
        ComunidadesRonda,
    )

    comunidades = (
        session.query(ComunidadesComunidad)
        .filter(ComunidadesComunidad.torneo_id == torneo_id)
        .all()
    )
    if not comunidades:
        return []

    if clasificacion_equipos is None:
        clasificacion_equipos = calcular_clasificacion_equipos(
            session, torneo_id, hasta_ronda
        )

    filas: dict[int, FilaClasificacion] = {
        comunidad.id: {
            "comunidad_id": int(comunidad.id),
            "nombre": comunidad.nombre,
            "puntos_zombificaciones": Decimal("0"),
            "zombies_matados": 0,
            "suma_puntos_equipos": Decimal("0"),
        }
        for comunidad in comunidades
    }
    for equipo in clasificacion_equipos:
        comunidad_id = int(equipo["comunidad_id"])
        if comunidad_id in filas:
            filas[comunidad_id]["suma_puntos_equipos"] += _decimal(
                equipo.get("puntos")
            )

    consulta = (
        session.query(ComunidadesHistorialTransicion, ComunidadesEquipo.comunidad_id)
        .join(
            ComunidadesEquipo,
            (ComunidadesEquipo.id == ComunidadesHistorialTransicion.equipo_id)
            & (ComunidadesEquipo.torneo_id == ComunidadesHistorialTransicion.torneo_id),
        )
        .join(ComunidadesRonda, ComunidadesRonda.id == ComunidadesHistorialTransicion.ronda_id)
        .filter(ComunidadesHistorialTransicion.torneo_id == torneo_id)
    )
    if hasta_ronda is not None:
        consulta = consulta.filter(ComunidadesRonda.numero <= hasta_ronda)
    for transicion, comunidad_id in consulta.all():
        comunidad_id = int(comunidad_id)
        if comunidad_id not in filas:
            continue
        filas[comunidad_id]["puntos_zombificaciones"] += _decimal(
            transicion.puntos_comunitarios_generados
        )
        filas[comunidad_id]["zombies_matados"] += int(
            transicion.kills_generadas or 0
        )

    ordenada = sorted(
        filas.values(),
        key=lambda fila: (
            -fila["puntos_zombificaciones"],
            -fila["zombies_matados"],
            -fila["suma_puntos_equipos"],
            fila["comunidad_id"],
        ),
    )
    criterio_anterior: Optional[tuple[Decimal, int, Decimal]] = None
    for indice, fila in enumerate(ordenada, start=1):
        criterio = (
            fila["puntos_zombificaciones"],
            fila["zombies_matados"],
            fila["suma_puntos_equipos"],
        )
        if criterio != criterio_anterior:
            posicion = indice
            criterio_anterior = criterio
        fila["posicion"] = posicion
    return ordenada


# ---------------------------------------------------------------------------
# Cierre de ronda
# ---------------------------------------------------------------------------

def _guardar_snapshots_cierre_comunidades(
    session: Any,
    *,
    torneo_id: int,
    ronda: Any,
    clasificacion_equipos: list[FilaClasificacion],
    clasificacion_comunidades: list[FilaClasificacion],
) -> tuple[int, int]:
    """Guarda una única fotografía de cada clasificación para la ronda.

    La ronda y sus dos conjuntos de filas se confirman en la misma transacción.
    Si el cierre se reintenta, se reutilizan los snapshots completos existentes;
    un conjunto parcial se considera una inconsistencia y nunca se completa con
    datos potencialmente calculados en otro momento.
    """
    from GestorSQL import (
        ComunidadesSnapshotClasificacionComunidad,
        ComunidadesSnapshotClasificacionEquipo,
    )

    snapshots_equipo = (
        session.query(ComunidadesSnapshotClasificacionEquipo)
        .filter_by(torneo_id=torneo_id, ronda_id=ronda.id)
        .count()
    )
    snapshots_comunidad = (
        session.query(ComunidadesSnapshotClasificacionComunidad)
        .filter_by(torneo_id=torneo_id, ronda_id=ronda.id)
        .count()
    )
    esperados_equipo = len(clasificacion_equipos)
    esperados_comunidad = len(clasificacion_comunidades)
    if snapshots_equipo or snapshots_comunidad:
        if (snapshots_equipo, snapshots_comunidad) != (
            esperados_equipo,
            esperados_comunidad,
        ):
            raise RuntimeError(
                "Los snapshots existentes de la ronda están incompletos "
                f"(equipos {snapshots_equipo}/{esperados_equipo}, "
                f"comunidades {snapshots_comunidad}/{esperados_comunidad})."
            )
        return snapshots_equipo, snapshots_comunidad

    for fila in clasificacion_equipos:
        session.add(
            ComunidadesSnapshotClasificacionEquipo(
                torneo_id=torneo_id,
                ronda_id=ronda.id,
                equipo_id=int(fila["equipo_id"]),
                posicion=int(fila["posicion"]),
                puntos_clasificacion=_decimal(fila["puntos"]),
                buchholz_cut=_decimal(fila["buchholz_cut"]),
                puntos_enfrentamiento_directo=(
                    None
                    if fila.get("h2h_valor") is None
                    else _decimal(fila["h2h_valor"])
                ),
                td_favor=int(fila["td_favor"]),
                td_contra=int(fila["td_contra"]),
                partidos_jugados=int(fila["pj"]),
                victorias=int(fila["pg"]),
                empates=int(fila["pe"]),
                derrotas=int(fila["pp"]),
                cantidad_byes=int(fila["cantidad_byes"]),
            )
        )
    for fila in clasificacion_comunidades:
        session.add(
            ComunidadesSnapshotClasificacionComunidad(
                torneo_id=torneo_id,
                ronda_id=ronda.id,
                comunidad_id=int(fila["comunidad_id"]),
                posicion=int(fila["posicion"]),
                puntos_zombificaciones=_decimal(fila["puntos_zombificaciones"]),
                zombies_matados=int(fila["zombies_matados"]),
                suma_puntos_equipos=_decimal(fila["suma_puntos_equipos"]),
            )
        )
    session.flush()
    return esperados_equipo, esperados_comunidad


def procesar_cierre_ronda_comunidades_si_corresponde(
    session: Any, torneo_id: int, ronda_numero: int
) -> dict[str, Any]:
    """Consolida una ronda resuelta sin realizar operaciones de Discord.

    El cierre de base de datos es atómico e idempotente. La publicación y la
    limpieza de canales se realizan después del commit desde ``LombardBot``.
    Según la especificación, una ronda posterior nunca se crea automáticamente.
    """
    from GestorSQL import (
        ComunidadesEnfrentamiento,
        ComunidadesHistorialTransicion,
        ComunidadesPartido,
        ComunidadesRonda,
        ComunidadesTorneo,
        ComunidadesTrazaEmparejamiento,
    )

    torneo = (
        session.query(ComunidadesTorneo)
        .filter(ComunidadesTorneo.id == torneo_id)
        .with_for_update()
        .one_or_none()
    )
    if torneo is None:
        return {
            "cerrada": False,
            "motivo": "TORNEO_NO_EXISTE",
            "ronda_numero": int(ronda_numero),
        }
    ronda = (
        session.query(ComunidadesRonda)
        .filter_by(torneo_id=torneo_id, numero=ronda_numero)
        .with_for_update()
        .one_or_none()
    )
    if ronda is None:
        return {
            "cerrada": False,
            "motivo": "RONDA_NO_EXISTE",
            "ronda_numero": int(ronda_numero),
        }

    estados_enfrentamiento_resueltos = (
        ENFRENTAMIENTO_CERRADO,
        ENFRENTAMIENTO_ADMINISTRADO,
    )
    estados_partido_resueltos = (PARTIDO_FINALIZADO, PARTIDO_ADMINISTRADO)
    pendientes_enfrentamiento = (
        session.query(ComunidadesEnfrentamiento)
        .filter(
            ComunidadesEnfrentamiento.ronda_id == ronda.id,
            ~ComunidadesEnfrentamiento.estado.in_(estados_enfrentamiento_resueltos),
        )
        .count()
    )
    pendientes_partido = (
        session.query(ComunidadesPartido)
        .join(
            ComunidadesEnfrentamiento,
            ComunidadesEnfrentamiento.id == ComunidadesPartido.enfrentamiento_id,
        )
        .filter(
            ComunidadesEnfrentamiento.ronda_id == ronda.id,
            ~ComunidadesPartido.estado.in_(estados_partido_resueltos),
        )
        .count()
    )
    byes_esperados = (
        session.query(ComunidadesTrazaEmparejamiento)
        .filter_by(ronda_id=ronda.id, etapa="SELECCION_BYE")
        .count()
    )
    byes_resueltos = (
        session.query(ComunidadesHistorialTransicion)
        .filter_by(ronda_id=ronda.id, enfrentamiento_id=None, motivo="BYE")
        .count()
    )
    pendientes_bye = max(0, int(byes_esperados) - int(byes_resueltos))
    if pendientes_enfrentamiento or pendientes_partido or pendientes_bye:
        return {
            "cerrada": False,
            "motivo": "HAY_PENDIENTES",
            "pendientes_enfrentamientos": int(pendientes_enfrentamiento),
            "pendientes_partidos": int(pendientes_partido),
            "pendientes_byes": pendientes_bye,
            "ronda_numero": int(ronda_numero),
        }

    clasificacion_equipos = calcular_clasificacion_equipos(
        session, torneo_id, hasta_ronda=ronda_numero
    )
    clasificacion_comunidades = calcular_clasificacion_comunidades(
        session,
        torneo_id,
        hasta_ronda=ronda_numero,
        clasificacion_equipos=clasificacion_equipos,
    )
    snapshot_equipos, snapshot_comunidades = _guardar_snapshots_cierre_comunidades(
        session,
        torneo_id=torneo_id,
        ronda=ronda,
        clasificacion_equipos=clasificacion_equipos,
        clasificacion_comunidades=clasificacion_comunidades,
    )

    ya_cerrada = ronda.estado == "CERRADA"
    if not ya_cerrada:
        ronda.estado = "CERRADA"
        ronda.cerrada_en = datetime.now(timezone.utc).replace(tzinfo=None)

    es_ultima_ronda = int(ronda_numero) >= int(torneo.rondas_totales)
    if es_ultima_ronda:
        torneo.estado = "FINALIZADO"
    session.flush()
    return {
        "cerrada": True,
        "motivo": "YA_CERRADA" if ya_cerrada else "CERRADA",
        "idempotente": ya_cerrada,
        "ronda_id": int(ronda.id),
        "ronda_numero": int(ronda_numero),
        "es_ultima_ronda": es_ultima_ronda,
        "siguiente_ronda_numero": (
            None if es_ultima_ronda else int(ronda_numero) + 1
        ),
        "snapshot_equipos": int(snapshot_equipos),
        "snapshot_comunidades": int(snapshot_comunidades),
        "clasificacion_equipos": clasificacion_equipos,
        "clasificacion_comunidades": clasificacion_comunidades,
    }


# ---------------------------------------------------------------------------
# Consultas públicas
# ---------------------------------------------------------------------------

class ErrorConsultaComunidades(ValueError):
    """Error de dominio legible para las consultas públicas."""

    def __init__(self, codigo: str, detalle: str):
        super().__init__(detalle)
        self.codigo = codigo
        self.detalle = detalle


def _error_consulta(codigo: str, detalle: str) -> None:
    raise ErrorConsultaComunidades(codigo, detalle)


def _obtener_torneo_consulta(session: Any, torneo_id: int):
    from GestorSQL import ComunidadesTorneo

    torneo = session.query(ComunidadesTorneo).filter_by(id=torneo_id).one_or_none()
    if torneo is None:
        _error_consulta("TORNEO_INEXISTENTE", f"No existe el torneo de comunidades con ID {torneo_id}.")
    return torneo


def _obtener_ronda_consulta(session: Any, torneo_id: int, numero: Optional[int]):
    from GestorSQL import ComunidadesRonda

    consulta = session.query(ComunidadesRonda).filter_by(torneo_id=torneo_id)
    if numero is None:
        ronda = consulta.order_by(ComunidadesRonda.numero.desc()).first()
    else:
        if type(numero) is not int or numero <= 0:
            _error_consulta("RONDA_INVALIDA", "La ronda debe ser un entero positivo.")
        ronda = consulta.filter_by(numero=numero).one_or_none()
    if ronda is None:
        texto = "última generada" if numero is None else str(numero)
        _error_consulta("RONDA_INEXISTENTE", f"El torneo {torneo_id} no tiene la ronda {texto}.")
    return ronda


def consultar_clasificacion_equipos_comunidades(
    session: Any, *, torneo_id: int, ronda: Optional[int] = None
) -> dict[str, Any]:
    """Obtiene la clasificación actual del core o un snapshot cerrado."""
    from GestorSQL import ComunidadesSnapshotClasificacionEquipo

    torneo = _obtener_torneo_consulta(session, torneo_id)
    if ronda is None:
        filas = calcular_clasificacion_equipos(session, torneo_id)
        equipos = {int(e.id): e for e in torneo.equipos}
        for fila in filas:
            equipo = equipos[int(fila["equipo_id"])]
            fila.update(
                comunidad_nombre=equipo.comunidad.nombre,
                es_zombie=bool(equipo.es_zombie),
                estado_temporal=equipo.estado_temporal,
            )
        return {"torneo": torneo, "ronda": None, "fuente": "ACTUAL", "filas": filas}

    ronda_db = _obtener_ronda_consulta(session, torneo_id, ronda)
    snapshots = (
        session.query(ComunidadesSnapshotClasificacionEquipo)
        .filter_by(torneo_id=torneo_id, ronda_id=ronda_db.id)
        .order_by(
            ComunidadesSnapshotClasificacionEquipo.posicion.asc(),
            ComunidadesSnapshotClasificacionEquipo.equipo_id.asc(),
        )
        .all()
    )
    if not snapshots:
        _error_consulta("SNAPSHOT_INEXISTENTE", f"La ronda {ronda} todavía no tiene snapshot de equipos.")
    filas = []
    for snap in snapshots:
        equipo = snap.equipo
        filas.append({
            "posicion": int(snap.posicion), "equipo_id": int(snap.equipo_id),
            "nombre": equipo.nombre, "comunidad_nombre": equipo.comunidad.nombre,
            "es_zombie": bool(equipo.es_zombie), "estado_temporal": equipo.estado_temporal,
            "pj": int(snap.partidos_jugados), "pg": int(snap.victorias),
            "pe": int(snap.empates), "pp": int(snap.derrotas),
            "cantidad_byes": int(snap.cantidad_byes), "puntos": _decimal(snap.puntos_clasificacion),
            "buchholz_cut": _decimal(snap.buchholz_cut),
            "h2h_valor": None if snap.puntos_enfrentamiento_directo is None else _decimal(snap.puntos_enfrentamiento_directo),
            "td_favor": int(snap.td_favor), "td_contra": int(snap.td_contra),
            "diferencia_td": int(snap.td_favor) - int(snap.td_contra),
        })
    return {"torneo": torneo, "ronda": ronda_db, "fuente": "SNAPSHOT", "filas": filas}


def consultar_clasificacion_comunidades_comunidades(
    session: Any, *, torneo_id: int, ronda: Optional[int] = None
) -> dict[str, Any]:
    """Obtiene la clasificación comunitaria actual o un snapshot cerrado."""
    from GestorSQL import ComunidadesSnapshotClasificacionComunidad

    torneo = _obtener_torneo_consulta(session, torneo_id)
    if ronda is None:
        equipos = calcular_clasificacion_equipos(session, torneo_id)
        filas = calcular_clasificacion_comunidades(session, torneo_id, clasificacion_equipos=equipos)
        return {"torneo": torneo, "ronda": None, "fuente": "ACTUAL", "filas": filas}

    ronda_db = _obtener_ronda_consulta(session, torneo_id, ronda)
    snapshots = (
        session.query(ComunidadesSnapshotClasificacionComunidad)
        .filter_by(torneo_id=torneo_id, ronda_id=ronda_db.id)
        .order_by(
            ComunidadesSnapshotClasificacionComunidad.posicion.asc(),
            ComunidadesSnapshotClasificacionComunidad.comunidad_id.asc(),
        ).all()
    )
    if not snapshots:
        _error_consulta("SNAPSHOT_INEXISTENTE", f"La ronda {ronda} todavía no tiene snapshot de comunidades.")
    filas = [{
        "posicion": int(s.posicion), "nombre": s.comunidad.nombre,
        "puntos_zombificaciones": _decimal(s.puntos_zombificaciones),
        "zombies_matados": int(s.zombies_matados),
        "suma_puntos_equipos": _decimal(s.suma_puntos_equipos),
    } for s in snapshots]
    return {"torneo": torneo, "ronda": ronda_db, "fuente": "SNAPSHOT", "filas": filas}


def consultar_ronda_comunidades(
    session: Any, *, torneo_id: int, ronda: Optional[int] = None
) -> dict[str, Any]:
    """Expone una ronda sin leer elecciones de atacante."""
    from GestorSQL import ComunidadesEnfrentamiento, ComunidadesFotografiaEstado, ComunidadesHistorialTransicion

    torneo = _obtener_torneo_consulta(session, torneo_id)
    ronda_db = _obtener_ronda_consulta(session, torneo_id, ronda)
    enfrentamientos = (
        session.query(ComunidadesEnfrentamiento)
        .filter_by(torneo_id=torneo_id, ronda_id=ronda_db.id)
        .order_by(ComunidadesEnfrentamiento.mesa_numero.asc()).all()
    )
    fotos = session.query(ComunidadesFotografiaEstado).filter_by(
        torneo_id=torneo_id, ronda_id=ronda_db.id
    ).all()
    estados = {(int(f.enfrentamiento_id), int(f.equipo_id)): {
        "es_zombie": bool(f.es_zombie), "estado_temporal": f.estado_temporal
    } for f in fotos}
    filas = []
    for e in enfrentamientos:
        filas.append({
            "mesa": int(e.mesa_numero), "equipo_a": e.equipo_a, "equipo_b": e.equipo_b,
            "estado_a": estados.get((int(e.id), int(e.equipo_a_id)), {"es_zombie": bool(e.equipo_a.es_zombie), "estado_temporal": e.equipo_a.estado_temporal}),
            "estado_b": estados.get((int(e.id), int(e.equipo_b_id)), {"es_zombie": bool(e.equipo_b.es_zombie), "estado_temporal": e.equipo_b.estado_temporal}),
            "estado": e.estado, "canal_general_discord_id": e.canal_general_discord_id,
            "puntos_internos_a": _decimal(e.puntos_internos_a), "puntos_internos_b": _decimal(e.puntos_internos_b),
            "puntos_clasificacion_a": _decimal(e.puntos_clasificacion_a), "puntos_clasificacion_b": _decimal(e.puntos_clasificacion_b),
        })
    bye = session.query(ComunidadesHistorialTransicion).filter_by(
        torneo_id=torneo_id, ronda_id=ronda_db.id, motivo="BYE"
    ).one_or_none()
    return {"torneo": torneo, "ronda": ronda_db, "enfrentamientos": filas,
            "bye_equipo": None if bye is None else bye.equipo}


def consultar_equipo_comunidades(session: Any, *, torneo_id: int, equipo_nombre: str) -> dict[str, Any]:
    """Obtiene identidad pública, estado y clasificación actual de un equipo."""
    from GestorSQL import ComunidadesEquipo

    torneo = _obtener_torneo_consulta(session, torneo_id)
    nombre = str(equipo_nombre or "").strip()
    equipo = session.query(ComunidadesEquipo).filter_by(torneo_id=torneo_id, nombre=nombre).one_or_none()
    if equipo is None:
        _error_consulta("EQUIPO_INEXISTENTE", f"No existe el equipo '{nombre}' en el torneo {torneo_id}.")
    fila = next((f for f in calcular_clasificacion_equipos(session, torneo_id)
                 if int(f["equipo_id"]) == int(equipo.id)), None)
    return {"torneo": torneo, "equipo": equipo,
            "miembros": sorted(equipo.miembros, key=lambda m: int(m.posicion)),
            "clasificacion": fila}


def consultar_estados_comunidades(session: Any, *, torneo_id: int) -> dict[str, Any]:
    """Lista estados actuales en el orden exacto del clasificador del core."""
    from GestorSQL import ComunidadesEquipo

    torneo = _obtener_torneo_consulta(session, torneo_id)
    equipos = {int(e.id): e for e in session.query(ComunidadesEquipo).filter_by(torneo_id=torneo_id).all()}
    filas = [{"clasificacion": f, "equipo": equipos[int(f["equipo_id"])]}
             for f in calcular_clasificacion_equipos(session, torneo_id)]
    return {"torneo": torneo, "filas": filas}


def consultar_estado_canales_comunidades(
    session: Any, *, torneo_id: int, ronda: Optional[int] = None
) -> dict[str, Any]:
    """Expone canales y progreso sin identidades ni roles secretos."""
    from GestorSQL import ComunidadesEnfrentamiento

    torneo = _obtener_torneo_consulta(session, torneo_id)
    ronda_db = _obtener_ronda_consulta(session, torneo_id, ronda)
    enfrentamientos = session.query(ComunidadesEnfrentamiento).filter_by(
        torneo_id=torneo_id, ronda_id=ronda_db.id
    ).order_by(ComunidadesEnfrentamiento.mesa_numero.asc()).all()
    filas = []
    for e in enfrentamientos:
        filas.append({
            "mesa": int(e.mesa_numero), "equipo_a": e.equipo_a, "equipo_b": e.equipo_b,
            "estado": e.estado, "canal_general_discord_id": e.canal_general_discord_id,
            "partidos": [{"indice": int(p.indice), "estado": p.estado, "canal_discord_id": p.canal_discord_id}
                         for p in sorted(e.partidos, key=lambda p: int(p.indice))],
        })
    return {"torneo": torneo, "ronda": ronda_db, "filas": filas}
