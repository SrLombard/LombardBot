from __future__ import annotations

from Imagenes import _datos_comunidades_resultado


def test_datos_comunidades_resultado_respeta_lado_local_visitante(
    comunidades_session,
    escenario_comunidades_factory,
    ronda_comunidades_factory,
    materializar_enfrentamiento,
):
    torneo, comunidades, _equipos = escenario_comunidades_factory(equipos=4, comunidades=4, rondas=1)
    ronda_comunidades_factory(torneo, 1, semilla=1)
    enfrentamiento = torneo.rondas[0].enfrentamientos[0]
    partidos = materializar_enfrentamiento(enfrentamiento, ronda_numero=1)
    partido = partidos[1]
    partido.partido_bloodbowl_id = "bbowl-partido-2"
    comunidades_session.commit()

    datos = _datos_comunidades_resultado(comunidades_session, "bbowl-partido-2")

    assert datos == {
        "comunidad1": {"0": partido.equipo_local.comunidad.nombre},
        "comunidad2": {"0": partido.equipo_visitante.comunidad.nombre},
        "comunidadVS": {
            "0": f"{partido.equipo_local.comunidad.nombre} Vs {partido.equipo_visitante.comunidad.nombre}"
        },
    }
    assert partido.equipo_local_id == enfrentamiento.equipo_b_id
    assert partido.equipo_visitante_id == enfrentamiento.equipo_a_id
