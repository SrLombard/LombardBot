from itertools import product
from pathlib import Path
import sys

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from ComunidadesCore import (
    EfectoComunitario,
    Equipo,
    EstadoFotografiado,
    EstadoTemporal,
    MotivoTransicion,
    ResultadoGlobal,
    resolver_transicion_estados,
)

COMUNIDAD_A = "Butter"
COMUNIDAD_B = "Hispana"


def estado(temporal, zombie=False):
    return EstadoFotografiado(temporal, zombie)


@pytest.mark.parametrize(
    (
        "caso",
        "inicial_a",
        "inicial_b",
        "resultado",
        "final_a",
        "final_b",
        "punto",
        "kill",
        "motivos",
    ),
    [
        (
            "12.2 victoria contra normal",
            estado(EstadoTemporal.NEUTRO),
            estado(EstadoTemporal.NEUTRO),
            ResultadoGlobal.VICTORIA_A,
            estado(EstadoTemporal.CAZADOR),
            estado(EstadoTemporal.HERIDO),
            None,
            None,
            (MotivoTransicion.VICTORIA, MotivoTransicion.DERROTA),
        ),
        (
            "12.2 cazador renovado",
            estado(EstadoTemporal.CAZADOR),
            estado(EstadoTemporal.CAZADOR_Z),
            ResultadoGlobal.VICTORIA_A,
            estado(EstadoTemporal.CAZADOR),
            estado(EstadoTemporal.HERIDO),
            None,
            None,
            (MotivoTransicion.VICTORIA, MotivoTransicion.DERROTA),
        ),
        (
            "12.7 victoria contra zombie sano",
            estado(EstadoTemporal.NEUTRO),
            estado(EstadoTemporal.CAZADOR, True),
            ResultadoGlobal.VICTORIA_A,
            estado(EstadoTemporal.CAZADOR_Z),
            estado(EstadoTemporal.HERIDO, True),
            None,
            None,
            (MotivoTransicion.VICTORIA, MotivoTransicion.DERROTA),
        ),
        (
            "12.7 cazador Z renovado",
            estado(EstadoTemporal.CAZADOR_Z),
            estado(EstadoTemporal.NEUTRO, True),
            ResultadoGlobal.VICTORIA_A,
            estado(EstadoTemporal.CAZADOR_Z),
            estado(EstadoTemporal.HERIDO, True),
            None,
            None,
            (MotivoTransicion.VICTORIA, MotivoTransicion.DERROTA),
        ),
        (
            "12.4 cazador inicial zombifica y puntua",
            estado(EstadoTemporal.CAZADOR),
            estado(EstadoTemporal.HERIDO),
            ResultadoGlobal.VICTORIA_A,
            estado(EstadoTemporal.NEUTRO),
            estado(EstadoTemporal.NEUTRO, True),
            EfectoComunitario(Equipo.A, COMUNIDAD_A),
            None,
            (MotivoTransicion.VICTORIA, MotivoTransicion.ZOMBIFICACION),
        ),
        (
            "12.4 neutro zombifica sin punto",
            estado(EstadoTemporal.NEUTRO),
            estado(EstadoTemporal.HERIDO),
            ResultadoGlobal.VICTORIA_A,
            estado(EstadoTemporal.NEUTRO),
            estado(EstadoTemporal.NEUTRO, True),
            None,
            None,
            (MotivoTransicion.VICTORIA, MotivoTransicion.ZOMBIFICACION),
        ),
        (
            "12.4 cazador Z zombifica sin punto",
            estado(EstadoTemporal.CAZADOR_Z),
            estado(EstadoTemporal.HERIDO),
            ResultadoGlobal.VICTORIA_A,
            estado(EstadoTemporal.NEUTRO),
            estado(EstadoTemporal.NEUTRO, True),
            None,
            None,
            (MotivoTransicion.VICTORIA, MotivoTransicion.ZOMBIFICACION),
        ),
        (
            "12.5 cazador Z mata zombie herido",
            estado(EstadoTemporal.CAZADOR_Z),
            estado(EstadoTemporal.HERIDO, True),
            ResultadoGlobal.VICTORIA_A,
            estado(EstadoTemporal.NEUTRO),
            estado(EstadoTemporal.NEUTRO, True),
            None,
            EfectoComunitario(Equipo.A, COMUNIDAD_A),
            (MotivoTransicion.KILL, MotivoTransicion.DERROTA),
        ),
        (
            "12.6 cazador normal no mata zombie herido",
            estado(EstadoTemporal.CAZADOR),
            estado(EstadoTemporal.HERIDO, True),
            ResultadoGlobal.VICTORIA_A,
            estado(EstadoTemporal.NEUTRO),
            estado(EstadoTemporal.NEUTRO, True),
            None,
            None,
            (MotivoTransicion.VICTORIA, MotivoTransicion.DERROTA),
        ),
        (
            "12.8 zombie herido gana a no zombie",
            estado(EstadoTemporal.HERIDO, True),
            estado(EstadoTemporal.NEUTRO),
            ResultadoGlobal.VICTORIA_A,
            estado(EstadoTemporal.CAZADOR, True),
            estado(EstadoTemporal.HERIDO),
            None,
            None,
            (MotivoTransicion.VICTORIA, MotivoTransicion.DERROTA),
        ),
        (
            "12.8 zombie herido gana a zombie",
            estado(EstadoTemporal.HERIDO, True),
            estado(EstadoTemporal.NEUTRO, True),
            ResultadoGlobal.VICTORIA_A,
            estado(EstadoTemporal.CAZADOR_Z, True),
            estado(EstadoTemporal.HERIDO, True),
            None,
            None,
            (MotivoTransicion.VICTORIA, MotivoTransicion.DERROTA),
        ),
    ],
)
def test_tabla_de_transiciones_documentadas(
    caso,
    inicial_a,
    inicial_b,
    resultado,
    final_a,
    final_b,
    punto,
    kill,
    motivos,
):
    transicion = resolver_transicion_estados(
        inicial_a, inicial_b, resultado, False, COMUNIDAD_A, COMUNIDAD_B
    )

    assert transicion.estado_final_a == final_a, caso
    assert transicion.estado_final_b == final_b, caso
    assert transicion.punto_zombificacion == punto, caso
    assert transicion.kill == kill, caso
    assert (transicion.motivo_a, transicion.motivo_b) == motivos, caso
    assert transicion.cambio_zombie_a == (not inicial_a.es_zombie and final_a.es_zombie)
    assert transicion.cambio_zombie_b == (not inicial_b.es_zombie and final_b.es_zombie)


@pytest.mark.parametrize(
    "inicial_a,inicial_b",
    [
        (estado(EstadoTemporal.CAZADOR), estado(EstadoTemporal.HERIDO)),
        (estado(EstadoTemporal.HERIDO, True), estado(EstadoTemporal.CAZADOR_Z, True)),
        (estado(EstadoTemporal.CAZADOR_Z), estado(EstadoTemporal.NEUTRO, True)),
    ],
)
def test_empate_limpia_estados_temporales_y_conserva_zombies(inicial_a, inicial_b):
    transicion = resolver_transicion_estados(
        inicial_a,
        inicial_b,
        ResultadoGlobal.EMPATE,
        False,
        COMUNIDAD_A,
        COMUNIDAD_B,
    )

    assert transicion.estado_final_a == estado(
        EstadoTemporal.NEUTRO, inicial_a.es_zombie
    )
    assert transicion.estado_final_b == estado(
        EstadoTemporal.NEUTRO, inicial_b.es_zombie
    )
    assert transicion.punto_zombificacion is None
    assert transicion.kill is None
    assert transicion.motivo_a is MotivoTransicion.EMPATE
    assert transicion.motivo_b is MotivoTransicion.EMPATE


def test_doble_forfait_global_no_cambia_estados_ni_genera_efectos():
    inicial_a = estado(EstadoTemporal.HERIDO)
    inicial_b = estado(EstadoTemporal.CAZADOR_Z, True)

    transicion = resolver_transicion_estados(
        inicial_a,
        inicial_b,
        ResultadoGlobal.EMPATE,
        True,
        COMUNIDAD_A,
        COMUNIDAD_B,
    )

    assert transicion.estado_final_a is inicial_a
    assert transicion.estado_final_b is inicial_b
    assert not transicion.cambio_zombie_a
    assert not transicion.cambio_zombie_b
    assert transicion.punto_zombificacion is None
    assert transicion.kill is None
    assert transicion.motivo_a is MotivoTransicion.DOBLE_FORFAIT
    assert transicion.motivo_b is MotivoTransicion.DOBLE_FORFAIT


def _intercambiar_equipo(efecto):
    if efecto is None:
        return None
    return EfectoComunitario(
        Equipo.B if efecto.equipo is Equipo.A else Equipo.A,
        efecto.comunidad,
    )


@pytest.mark.parametrize(
    "inicial_a,inicial_b,resultado",
    [
        (
            estado(EstadoTemporal.CAZADOR),
            estado(EstadoTemporal.HERIDO),
            ResultadoGlobal.VICTORIA_A,
        ),
        (
            estado(EstadoTemporal.CAZADOR_Z),
            estado(EstadoTemporal.HERIDO, True),
            ResultadoGlobal.VICTORIA_A,
        ),
        (
            estado(EstadoTemporal.HERIDO, True),
            estado(EstadoTemporal.NEUTRO),
            ResultadoGlobal.VICTORIA_B,
        ),
        (
            estado(EstadoTemporal.CAZADOR),
            estado(EstadoTemporal.CAZADOR_Z, True),
            ResultadoGlobal.EMPATE,
        ),
    ],
)
def test_simetria_entre_lados_a_y_b(inicial_a, inicial_b, resultado):
    original = resolver_transicion_estados(
        inicial_a, inicial_b, resultado, False, COMUNIDAD_A, COMUNIDAD_B
    )
    resultado_invertido = {
        ResultadoGlobal.VICTORIA_A: ResultadoGlobal.VICTORIA_B,
        ResultadoGlobal.VICTORIA_B: ResultadoGlobal.VICTORIA_A,
        ResultadoGlobal.EMPATE: ResultadoGlobal.EMPATE,
    }[resultado]
    invertida = resolver_transicion_estados(
        inicial_b,
        inicial_a,
        resultado_invertido,
        False,
        COMUNIDAD_B,
        COMUNIDAD_A,
    )

    assert invertida.estado_final_a == original.estado_final_b
    assert invertida.estado_final_b == original.estado_final_a
    assert invertida.cambio_zombie_a == original.cambio_zombie_b
    assert invertida.cambio_zombie_b == original.cambio_zombie_a
    assert invertida.punto_zombificacion == _intercambiar_equipo(
        original.punto_zombificacion
    )
    assert invertida.kill == _intercambiar_equipo(original.kill)
    assert invertida.motivo_a == original.motivo_b
    assert invertida.motivo_b == original.motivo_a


ESTADOS_POSIBLES = tuple(
    estado(temporal, zombie)
    for temporal, zombie in product(EstadoTemporal, (False, True))
)


@pytest.mark.parametrize(
    "inicial_a,inicial_b,resultado",
    product(ESTADOS_POSIBLES, ESTADOS_POSIBLES, ResultadoGlobal),
)
def test_matriz_exhaustiva_siempre_respeta_invariantes(inicial_a, inicial_b, resultado):
    transicion = resolver_transicion_estados(
        inicial_a, inicial_b, resultado, False, COMUNIDAD_A, COMUNIDAD_B
    )

    assert inicial_a.es_zombie <= transicion.estado_final_a.es_zombie
    assert inicial_b.es_zombie <= transicion.estado_final_b.es_zombie
    assert isinstance(transicion.estado_final_a.estado_temporal, EstadoTemporal)
    assert isinstance(transicion.estado_final_b.estado_temporal, EstadoTemporal)
    assert not (transicion.punto_zombificacion and transicion.kill)

    if transicion.punto_zombificacion:
        ganador, perdedor = (
            (inicial_a, inicial_b)
            if resultado is ResultadoGlobal.VICTORIA_A
            else (inicial_b, inicial_a)
        )
        assert ganador.estado_temporal is EstadoTemporal.CAZADOR
        assert perdedor == estado(EstadoTemporal.HERIDO)

    if transicion.kill:
        ganador, perdedor = (
            (inicial_a, inicial_b)
            if resultado is ResultadoGlobal.VICTORIA_A
            else (inicial_b, inicial_a)
        )
        assert ganador.estado_temporal is EstadoTemporal.CAZADOR_Z
        assert perdedor == estado(EstadoTemporal.HERIDO, True)


@pytest.mark.parametrize(
    "ganador,perdedor",
    [
        (estado(EstadoTemporal.CAZADOR_Z), estado(EstadoTemporal.HERIDO)),
        (estado(EstadoTemporal.CAZADOR), estado(EstadoTemporal.HERIDO, True)),
        (estado(EstadoTemporal.NEUTRO), estado(EstadoTemporal.HERIDO, True)),
        (estado(EstadoTemporal.HERIDO), estado(EstadoTemporal.HERIDO)),
    ],
)
def test_cruces_no_deseados_tienen_fallback_sin_punto_ni_kill(ganador, perdedor):
    transicion = resolver_transicion_estados(
        ganador,
        perdedor,
        ResultadoGlobal.VICTORIA_A,
        False,
        COMUNIDAD_A,
        COMUNIDAD_B,
    )

    assert transicion.estado_final_a.estado_temporal is EstadoTemporal.NEUTRO
    assert transicion.estado_final_b == estado(EstadoTemporal.NEUTRO, True)
    assert transicion.punto_zombificacion is None
    assert transicion.kill is None


def test_una_transferencia_posterior_no_altera_el_calculo_de_la_fotografia():
    fotografia_a = estado(EstadoTemporal.NEUTRO)
    fotografia_b = estado(EstadoTemporal.HERIDO)
    estado_vivo_a_tras_transferencia = estado(EstadoTemporal.CAZADOR)

    antes = resolver_transicion_estados(
        fotografia_a,
        fotografia_b,
        ResultadoGlobal.VICTORIA_A,
        False,
        COMUNIDAD_A,
        COMUNIDAD_B,
    )
    despues = resolver_transicion_estados(
        fotografia_a,
        fotografia_b,
        ResultadoGlobal.VICTORIA_A,
        False,
        COMUNIDAD_A,
        COMUNIDAD_B,
    )

    assert estado_vivo_a_tras_transferencia != fotografia_a
    assert antes == despues
    assert despues.punto_zombificacion is None
    assert despues.estado_final_b == estado(EstadoTemporal.NEUTRO, True)


@pytest.mark.parametrize(
    "args,error",
    [
        (
            (
                "NEUTRO",
                estado(EstadoTemporal.NEUTRO),
                ResultadoGlobal.EMPATE,
                False,
                COMUNIDAD_A,
                COMUNIDAD_B,
            ),
            TypeError,
        ),
        (
            (
                estado(EstadoTemporal.NEUTRO),
                estado(EstadoTemporal.NEUTRO),
                "DESCONOCIDO",
                False,
                COMUNIDAD_A,
                COMUNIDAD_B,
            ),
            ValueError,
        ),
        (
            (
                estado(EstadoTemporal.NEUTRO),
                estado(EstadoTemporal.NEUTRO),
                ResultadoGlobal.EMPATE,
                1,
                COMUNIDAD_A,
                COMUNIDAD_B,
            ),
            TypeError,
        ),
        (
            (
                estado(EstadoTemporal.NEUTRO),
                estado(EstadoTemporal.NEUTRO),
                ResultadoGlobal.VICTORIA_A,
                True,
                COMUNIDAD_A,
                COMUNIDAD_B,
            ),
            ValueError,
        ),
        (
            (
                estado(EstadoTemporal.NEUTRO),
                estado(EstadoTemporal.NEUTRO),
                ResultadoGlobal.EMPATE,
                False,
                COMUNIDAD_A,
                COMUNIDAD_A,
            ),
            ValueError,
        ),
    ],
)
def test_valida_invariantes_de_entrada(args, error):
    with pytest.raises(error):
        resolver_transicion_estados(*args)


@pytest.mark.parametrize("zombie", [None, 0, 1, "si"])
def test_estado_fotografiado_exige_condicion_zombie_booleana(zombie):
    with pytest.raises(TypeError):
        estado(EstadoTemporal.NEUTRO, zombie)
