"""Cálculos de resultados y clasificaciones del torneo de comunidades.

La resolución de marcadores y estados se mantiene pura. Las funciones de
clasificación consultan los modelos propios de comunidades mediante la sesión
recibida, sin depender de los modelos del torneo suizo individual.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
import json
from enum import Enum
from functools import cmp_to_key
from typing import Any, Iterable, Optional

from ComunidadesConstantes import (
    ESTADO_TEMPORAL_CAZADOR,
    ESTADO_TEMPORAL_CAZADOR_Z,
    ESTADO_TEMPORAL_HERIDO,
    ESTADO_TEMPORAL_NEUTRO,
    PLANTILLA_RONDA1_PENDIENTE,
    PLANTILLA_RONDAS_SIGUIENTES_PENDIENTE,
    TORNEO_CREADO,
    validar_puntuacion,
)


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


def generar_ronda_comunidades(
    session: Any,
    torneo_id: int,
    ronda_numero: int,
    generada_por_discord_id: int,
    rng: Any = None,
    *,
    on_enfrentamiento_persistido: Any = None,
) -> dict[str, Any]:
    """Genera y confirma una ronda completa sin realizar operaciones Discord.

    El servicio es la frontera transaccional: confirma únicamente después de
    crear ronda, enfrentamientos, dos fotografías por enfrentamiento, traza y
    efectos del bye. Ante cualquier excepción revierte la sesión completa.
    ``on_enfrentamiento_persistido`` permite instrumentar la operación y probar
    fallos intermedios; se ejecuta después de cada enfrentamiento completo.
    """
    from GestorSQL import (
        ComunidadesEnfrentamiento,
        ComunidadesEquipo,
        ComunidadesFotografiaEstado,
        ComunidadesHistorialTransicion,
        ComunidadesRonda,
        ComunidadesTorneo,
    )

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
        resultado = {
            "torneo_id": int(torneo_id),
            "ronda_id": int(ronda.id),
            "ronda_numero": int(ronda_numero),
            "enfrentamiento_ids": enfrentamiento_ids,
            "bye_equipo_id": bye_equipo_id,
            "nivel_fallback": traza.get("nivel_fallback"),
            "etapa": traza.get("etapa"),
        }
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
        if ganador_id is None:
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
