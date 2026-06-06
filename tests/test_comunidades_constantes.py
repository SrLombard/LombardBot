from decimal import Decimal
from itertools import product
from pathlib import Path
import sys

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from ComunidadesConstantes import (
    EMOJI_CAZADOR,
    EMOJI_CAZADOR_Z,
    EMOJI_HERIDO,
    EMOJI_ZOMBIE,
    ESTADOS_ENFRENTAMIENTO,
    ESTADOS_PARTIDO,
    ESTADOS_RONDA,
    ESTADOS_TEMPORALES,
    ESTADOS_TORNEO,
    ICONOS_POR_RAZA,
    LIMITE_CANALES_POR_CATEGORIA,
    ORIGENES_RESULTADO,
    RAZAS,
    RAZAS_VALIDAS,
    TIPOS_ADMINISTRATIVOS,
    validar_combinacion_estados,
    validar_estado_temporal,
    validar_puntuacion,
    validar_raza,
)


RAZAS_ESPERADAS = (
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


@pytest.mark.parametrize("raza", RAZAS_ESPERADAS)
def test_acepta_cada_raza_canónica(raza):
    assert validar_raza(raza)


def test_lista_exacta_de_23_razas_y_mapa_de_iconos():
    assert RAZAS == RAZAS_ESPERADAS
    assert RAZAS_VALIDAS == frozenset(RAZAS_ESPERADAS)
    assert len(RAZAS) == len(RAZAS_VALIDAS) == 23
    assert ICONOS_POR_RAZA == {
        raza: f"Iconos/{raza}.png"
        for raza in RAZAS_ESPERADAS
    }
    raiz_repositorio = Path(__file__).resolve().parents[1]
    assert all((raiz_repositorio / ruta).is_file() for ruta in ICONOS_POR_RAZA.values())


@pytest.mark.parametrize(
    "raza",
    [
        "Unión Élfica",
        "Khornne",
        "Khorne ",
        "khorne",
        "Nórdicos",
        "Horror Nigromántico",
        "Elfo Osucros",
        "Elfos oscuros",
        "",
        None,
    ],
)
def test_rechaza_aliases_acentos_mayúsculas_espacios_y_erratas(raza):
    assert not validar_raza(raza)


def test_valores_canónicos_de_estados_orígenes_y_tipos_administrativos():
    assert ESTADOS_TORNEO == {"CREADO", "EN_CURSO", "FINALIZADO"}
    assert ESTADOS_RONDA == {"ABIERTA", "BLOQUEADA", "CERRADA"}
    assert ESTADOS_ENFRENTAMIENTO == {
        "PENDIENTE_ELECCIONES",
        "PARTIDOS_CREADOS",
        "EN_CURSO",
        "CERRADO",
        "ADMINISTRADO",
    }
    assert ESTADOS_PARTIDO == {"PENDIENTE", "EN_CURSO", "FINALIZADO", "ADMINISTRADO"}
    assert ESTADOS_TEMPORALES == {"NEUTRO", "CAZADOR", "CAZADOR_Z", "HERIDO"}
    assert ORIGENES_RESULTADO == {"API", "ADMIN"}
    assert TIPOS_ADMINISTRATIVOS == {
        "forfeit_local",
        "forfeit_visitante",
        "empate_admin",
        "doble_forfeit",
        "manual",
    }


@pytest.mark.parametrize("estado", ["NEUTRO", "CAZADOR", "CAZADOR_Z", "HERIDO"])
def test_valida_estados_temporales_exactos(estado):
    assert validar_estado_temporal(estado)


@pytest.mark.parametrize("estado", ["cazador", "CAZADOR Z", "HERÍDO", "", None])
def test_rechaza_variantes_de_estado_temporal(estado):
    assert not validar_estado_temporal(estado)


@pytest.mark.parametrize("herido,cazador,cazador_z,zombie", product((False, True), repeat=4))
def test_valida_todas_las_combinaciones_de_estado(herido, cazador, cazador_z, zombie):
    esperado = sum((herido, cazador, cazador_z)) <= 1
    assert validar_combinacion_estados(
        herido=herido,
        cazador=cazador,
        cazador_z=cazador_z,
        zombie=zombie,
    ) is esperado


@pytest.mark.parametrize(
    "kwargs",
    [
        {"herido": True, "cazador": True},
        {"herido": True, "cazador_z": True},
        {"cazador": True, "cazador_z": True},
        {"herido": True, "cazador": True, "cazador_z": True, "zombie": True},
    ],
)
def test_rechaza_combinaciones_temporales_incompatibles(kwargs):
    assert not validar_combinacion_estados(**kwargs)


def test_zombie_puede_coexistir_con_cualquier_estado_temporal_individual():
    assert validar_combinacion_estados(zombie=True)
    assert validar_combinacion_estados(zombie=True, herido=True)
    assert validar_combinacion_estados(zombie=True, cazador=True)
    assert validar_combinacion_estados(zombie=True, cazador_z=True)


@pytest.mark.parametrize("valor", [0, 3, 1.5, "1.50", Decimal("9999.99")])
def test_acepta_puntuaciones_validas(valor):
    assert validar_puntuacion(valor)


@pytest.mark.parametrize(
    "valor",
    [-1, "-0.01", "1.001", " 1", "1 ", "", "NaN", "Infinity", 10000, True, None, object()],
)
def test_rechaza_puntuaciones_invalidas(valor):
    assert not validar_puntuacion(valor)


def test_emojis_y_limite_de_canales():
    assert EMOJI_CAZADOR == "🏹"
    assert EMOJI_HERIDO == "🩸"
    assert EMOJI_ZOMBIE == "🧟"
    assert EMOJI_CAZADOR_Z == "🏹🧟"
    assert LIMITE_CANALES_POR_CATEGORIA == 40
