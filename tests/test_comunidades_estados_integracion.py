from __future__ import annotations

import random

from ComunidadesCore import administrar_partido_comunidades, generar_ronda_comunidades
from GestorSQL import (
    ComunidadesComunidad,
    ComunidadesEnfrentamiento,
    ComunidadesHistorialTransicion,
    ComunidadesRonda,
)


def _ganar_ambos_partidos(
    session, torneo, enfrentamiento, ganador_id, materializar_enfrentamiento
):
    partidos = materializar_enfrentamiento(enfrentamiento, ronda_numero=1)
    for partido in partidos:
        marcador = (2, 0) if int(partido.equipo_local_id) == int(ganador_id) else (0, 2)
        administrar_partido_comunidades(
            session,
            torneo_id=int(torneo.id),
            ronda_numero=1,
            enfrentamiento_id=int(enfrentamiento.id),
            partido_indice=int(partido.indice),
            td_local=marcador[0],
            td_visitante=marcador[1],
        )


def test_zombificacion_y_kill_se_resuelven_con_la_fotografia_inicial(
    comunidades_session,
    torneo_comunidades_factory,
    comunidad_comunidades_factory,
    equipo_comunidades_factory,
    materializar_enfrentamiento,
):
    torneo = torneo_comunidades_factory(rondas=1)
    comunidades = [
        comunidad_comunidades_factory(torneo, nombre)
        for nombre in ("Cazadores", "Heridos", "Cazadores Z", "Zombies")
    ]
    equipos = [
        equipo_comunidades_factory(
            torneo, comunidades[0], nombre="Cazador", estado="CAZADOR"
        ),
        equipo_comunidades_factory(
            torneo, comunidades[1], nombre="Herido", estado="HERIDO"
        ),
        equipo_comunidades_factory(
            torneo, comunidades[2], nombre="Cazador Z", estado="CAZADOR_Z"
        ),
        equipo_comunidades_factory(
            torneo,
            comunidades[3],
            nombre="Zombie herido",
            estado="HERIDO",
            zombie=True,
        ),
    ]
    comunidades_session.commit()

    generar_ronda_comunidades(
        comunidades_session, torneo.id, 1, 999_999, random.Random(4)
    )
    ronda = comunidades_session.query(ComunidadesRonda).one()
    enfrentamientos = comunidades_session.query(ComunidadesEnfrentamiento).all()
    por_equipos = {
        frozenset((enfrentamiento.equipo_a.nombre, enfrentamiento.equipo_b.nombre)): enfrentamiento
        for enfrentamiento in enfrentamientos
    }
    assert set(por_equipos) == {
        frozenset(("Cazador", "Herido")),
        frozenset(("Cazador Z", "Zombie herido")),
    }

    for nombres, nombre_ganador in (
        (frozenset(("Cazador", "Herido")), "Cazador"),
        (frozenset(("Cazador Z", "Zombie herido")), "Cazador Z"),
    ):
        enfrentamiento = por_equipos[nombres]
        ganador = next(
            equipo
            for equipo in (enfrentamiento.equipo_a, enfrentamiento.equipo_b)
            if equipo.nombre == nombre_ganador
        )
        _ganar_ambos_partidos(
            comunidades_session,
            torneo,
            enfrentamiento,
            ganador.id,
            materializar_enfrentamiento,
        )
    comunidades_session.commit()

    actualizados = {equipo.nombre: equipo for equipo in equipos}
    assert actualizados["Herido"].es_zombie is True
    assert actualizados["Zombie herido"].es_zombie is True
    motivos = {
        transicion.motivo
        for transicion in comunidades_session.query(ComunidadesHistorialTransicion)
        .filter_by(ronda_id=ronda.id)
        .all()
    }
    assert {"ZOMBIFICACION", "KILL"}.issubset(motivos)
    contadores = {
        comunidad.nombre: (comunidad.puntos_zombificaciones, comunidad.zombies_matados)
        for comunidad in comunidades_session.query(ComunidadesComunidad).all()
    }
    assert contadores["Cazadores"][0] > 0
    assert contadores["Cazadores Z"][1] == 1
