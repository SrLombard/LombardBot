from decimal import Decimal
from pathlib import Path
import sys

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from ComunidadesCore import (
    CriterioDesempate,
    ConfiguracionPuntosClasificacion,
    ConfiguracionPuntosIndividuales,
    Equipo,
    MarcadorPartido,
    PuntosInternosPartido,
    ResultadoGlobal,
    asignar_puntos_clasificacion,
    calcular_resultado_enfrentamiento,
    calcular_td_globales,
    convertir_marcador_en_puntos_internos,
    decidir_resultado_global,
    identificar_td_atacantes,
    sumar_puntos_internos,
)

PUNTOS_INDIVIDUALES = ConfiguracionPuntosIndividuales("3", "1", "0")
PUNTOS_CLASIFICACION = ConfiguracionPuntosClasificacion("3", "1", "0")


def _calcular(
    partido_atacante_a,
    partido_atacante_b,
    individuales=PUNTOS_INDIVIDUALES,
    clasificacion=PUNTOS_CLASIFICACION,
):
    return calcular_resultado_enfrentamiento(
        (
            MarcadorPartido(*partido_atacante_a, Equipo.A),
            MarcadorPartido(*partido_atacante_b, Equipo.B),
        ),
        individuales,
        clasificacion,
    )


@pytest.mark.parametrize(
    "td_a,td_b,esperado",
    [
        (2, 1, PuntosInternosPartido(Decimal("3"), Decimal("0"))),
        (1, 1, PuntosInternosPartido(Decimal("1"), Decimal("1"))),
        (0, 3, PuntosInternosPartido(Decimal("0"), Decimal("3"))),
        (0, 0, PuntosInternosPartido(Decimal("1"), Decimal("1"))),
    ],
)
def test_convierte_marcador_individual_en_puntos_internos(td_a, td_b, esperado):
    assert (
        convertir_marcador_en_puntos_internos(td_a, td_b, PUNTOS_INDIVIDUALES)
        == esperado
    )


def test_ejemplo_documentado_suma_cuatro_a_uno_y_gana_por_puntos_internos():
    resultado = _calcular((1, 1), (2, 0))

    assert resultado.puntos_internos_a == Decimal("4")
    assert resultado.puntos_internos_b == Decimal("1")
    assert resultado.resultado is ResultadoGlobal.VICTORIA_A
    assert resultado.ganador is Equipo.A
    assert resultado.criterio_desempate is CriterioDesempate.PUNTOS_INTERNOS
    assert (resultado.puntos_clasificacion_a, resultado.puntos_clasificacion_b) == (
        Decimal("3"),
        Decimal("0"),
    )


@pytest.mark.parametrize(
    "partido_atacante_a,partido_atacante_b,resultado_esperado,criterio",
    [
        ((3, 1), (0, 2), ResultadoGlobal.VICTORIA_A, CriterioDesempate.TD_ATACANTE),
        ((2, 1), (0, 3), ResultadoGlobal.VICTORIA_B, CriterioDesempate.TD_ATACANTE),
        ((2, 1), (0, 2), ResultadoGlobal.VICTORIA_B, CriterioDesempate.DIFERENCIA_TD),
        ((2, 0), (1, 2), ResultadoGlobal.VICTORIA_A, CriterioDesempate.DIFERENCIA_TD),
        ((1, 0), (0, 1), ResultadoGlobal.EMPATE, CriterioDesempate.EMPATE_DEFINITIVO),
        ((0, 0), (0, 0), ResultadoGlobal.EMPATE, CriterioDesempate.EMPATE_DEFINITIVO),
    ],
)
def test_aplica_cada_desempate_en_orden(
    partido_atacante_a, partido_atacante_b, resultado_esperado, criterio
):
    resultado = _calcular(partido_atacante_a, partido_atacante_b)

    assert resultado.resultado is resultado_esperado
    assert resultado.criterio_desempate is criterio


def test_identifica_td_de_atacantes_independientemente_del_orden_de_partidos():
    partidos = (
        MarcadorPartido(2, 4, Equipo.B),
        MarcadorPartido(3, 1, Equipo.A),
    )

    assert identificar_td_atacantes(partidos) == (3, 4)


def test_calcula_td_globales_y_diferencias_complementarias():
    totales = calcular_td_globales(
        (MarcadorPartido(3, 0, Equipo.A), MarcadorPartido(1, 2, Equipo.B))
    )

    assert (totales.td_favor_a, totales.td_contra_a) == (4, 2)
    assert (totales.td_favor_b, totales.td_contra_b) == (2, 4)
    assert (totales.diferencia_a, totales.diferencia_b) == (2, -2)


def test_puntuaciones_no_estandar_se_mantienen_separadas():
    individuales = ConfiguracionPuntosIndividuales("7.5", "2.25", "0.5")
    clasificacion = ConfiguracionPuntosClasificacion("11", "4.5", "1.25")

    resultado = _calcular((2, 0), (1, 1), individuales, clasificacion)

    assert (resultado.puntos_internos_a, resultado.puntos_internos_b) == (
        Decimal("9.75"),
        Decimal("2.75"),
    )
    assert (resultado.puntos_clasificacion_a, resultado.puntos_clasificacion_b) == (
        Decimal("11"),
        Decimal("1.25"),
    )


def test_empate_no_estandar_usa_solo_puntos_de_clasificacion():
    resultado = _calcular(
        (0, 0),
        (0, 0),
        ConfiguracionPuntosIndividuales("8", "2.75", "0"),
        ConfiguracionPuntosClasificacion("10", "4.25", "1"),
    )

    assert (resultado.puntos_internos_a, resultado.puntos_internos_b) == (
        Decimal("5.50"),
        Decimal("5.50"),
    )
    assert (resultado.puntos_clasificacion_a, resultado.puntos_clasificacion_b) == (
        Decimal("4.25"),
        Decimal("4.25"),
    )


def test_resultado_contiene_todos_los_valores_persistibles_del_enfrentamiento():
    resultado = _calcular((2, 0), (1, 2))

    assert resultado.puntos_internos_a == Decimal("3")
    assert resultado.puntos_internos_b == Decimal("3")
    assert (resultado.td_favor_a, resultado.td_contra_a) == (3, 2)
    assert (resultado.td_favor_b, resultado.td_contra_b) == (2, 3)
    assert (resultado.diferencia_td_a, resultado.diferencia_td_b) == (1, -1)
    assert (resultado.td_atacante_a, resultado.td_atacante_b) == (2, 2)
    assert resultado.resultado is ResultadoGlobal.VICTORIA_A
    assert resultado.ganador is Equipo.A
    assert resultado.criterio_desempate is CriterioDesempate.DIFERENCIA_TD
    assert (resultado.puntos_clasificacion_a, resultado.puntos_clasificacion_b) == (
        Decimal("3"),
        Decimal("0"),
    )


def test_funciones_intermedias_suman_decimales_y_asignan_clasificacion():
    puntos = sumar_puntos_internos(
        (
            PuntosInternosPartido(Decimal("1.25"), Decimal("2.5")),
            PuntosInternosPartido(Decimal("3.75"), Decimal("0.5")),
        )
    )
    decision = decidir_resultado_global(puntos.puntos_a, puntos.puntos_b, 0, 0, 0, 0)

    assert puntos == PuntosInternosPartido(Decimal("5.00"), Decimal("3.0"))
    assert decision.criterio is CriterioDesempate.PUNTOS_INTERNOS
    assert asignar_puntos_clasificacion(
        decision.resultado, ConfiguracionPuntosClasificacion("6", "2", "0.5")
    ) == (Decimal("6"), Decimal("0.5"))


@pytest.mark.parametrize(
    "partidos",
    [
        (),
        (MarcadorPartido(0, 0, Equipo.A),),
        (
            MarcadorPartido(0, 0, Equipo.A),
            MarcadorPartido(0, 0, Equipo.A),
        ),
    ],
)
def test_rechaza_series_que_no_contienen_un_partido_por_atacante(partidos):
    with pytest.raises(ValueError):
        calcular_resultado_enfrentamiento(
            partidos, PUNTOS_INDIVIDUALES, PUNTOS_CLASIFICACION
        )


@pytest.mark.parametrize("td", [-1, 1.5, True])
def test_rechaza_td_negativos_o_no_enteros(td):
    with pytest.raises((TypeError, ValueError)):
        MarcadorPartido(td, 0, Equipo.A)
