"""Cálculos puros de resultados para enfrentamientos de comunidades.

Este módulo no conoce SQLAlchemy, Discord ni estados del torneo. Todos los
marcadores se expresan desde la perspectiva estable de los equipos A y B del
enfrentamiento, independientemente de quién figure como local en Blood Bowl.
"""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Iterable

from ComunidadesConstantes import (
    ESTADO_TEMPORAL_CAZADOR,
    ESTADO_TEMPORAL_CAZADOR_Z,
    ESTADO_TEMPORAL_HERIDO,
    ESTADO_TEMPORAL_NEUTRO,
)


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
