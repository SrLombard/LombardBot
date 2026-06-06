"""Cálculos puros de resultados para enfrentamientos de comunidades.

Este módulo no conoce SQLAlchemy, Discord ni estados del torneo. Todos los
marcadores se expresan desde la perspectiva estable de los equipos A y B del
enfrentamiento, independientemente de quién figure como local en Blood Bowl.
"""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Iterable


class Equipo(str, Enum):
    """Lado de un equipo dentro de un enfrentamiento."""

    A = "A"
    B = "B"


class ResultadoGlobal(str, Enum):
    """Resultado final del enfrentamiento desde la perspectiva del equipo A."""

    VICTORIA_A = "VICTORIA_A"
    VICTORIA_B = "VICTORIA_B"
    EMPATE = "EMPATE"


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
