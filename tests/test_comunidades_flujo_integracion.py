from __future__ import annotations

import random
from decimal import Decimal

from ComunidadesCore import (
    administrar_partido_comunidades,
    generar_ronda_comunidades,
    procesar_cierre_ronda_comunidades_si_corresponde,
    regenerar_ronda_comunidades,
)
from GestorSQL import (
    ComunidadesEnfrentamiento,
    ComunidadesRonda,
    ComunidadesSnapshotClasificacionComunidad,
    ComunidadesSnapshotClasificacionEquipo,
)


def _resolver_ronda_administrativamente(
    session, torneo, ronda_numero, materializar_enfrentamiento
):
    ronda = (
        session.query(ComunidadesRonda)
        .filter_by(torneo_id=torneo.id, numero=ronda_numero)
        .one()
    )
    enfrentamientos = (
        session.query(ComunidadesEnfrentamiento)
        .filter_by(ronda_id=ronda.id)
        .order_by(ComunidadesEnfrentamiento.mesa_numero)
        .all()
    )
    for indice, enfrentamiento in enumerate(enfrentamientos):
        partidos = materializar_enfrentamiento(
            enfrentamiento, ronda_numero=ronda_numero
        )
        marcadores = ((2, 0), (1, 1)) if indice % 2 == 0 else ((0, 1), (2, 0))
        for partido, (td_local, td_visitante) in zip(partidos, marcadores):
            administrar_partido_comunidades(
                session,
                torneo_id=int(torneo.id),
                ronda_numero=ronda_numero,
                enfrentamiento_id=int(enfrentamiento.id),
                partido_indice=int(partido.indice),
                td_local=td_local,
                td_visitante=td_visitante,
            )
    session.commit()
    return enfrentamientos


def test_ciclo_de_dos_rondas_desde_inscripcion_hasta_final_con_snapshots(
    comunidades_session,
    escenario_comunidades_factory,
    materializar_enfrentamiento,
):
    torneo, comunidades, equipos = escenario_comunidades_factory(
        equipos=4, comunidades=4, rondas=2
    )

    ronda_1 = generar_ronda_comunidades(
        comunidades_session, torneo.id, 1, 999_999, random.Random(101)
    )
    assert ronda_1["nivel_fallback"] == "BASE"
    assert len(ronda_1["enfrentamiento_ids"]) == 2

    enfrentamientos_1 = _resolver_ronda_administrativamente(
        comunidades_session, torneo, 1, materializar_enfrentamiento
    )
    assert all(enfrentamiento.estado == "ADMINISTRADO" for enfrentamiento in enfrentamientos_1)
    assert all(
        len(enfrentamiento.partidos) == 2
        and {partido.resultado_origen for partido in enfrentamiento.partidos} == {"ADMIN"}
        for enfrentamiento in enfrentamientos_1
    )

    cierre_1 = procesar_cierre_ronda_comunidades_si_corresponde(
        comunidades_session, torneo.id, 1
    )
    comunidades_session.commit()
    assert cierre_1["cerrada"] is True
    assert cierre_1["es_ultima_ronda"] is False
    assert cierre_1["snapshot_equipos"] == len(equipos)
    assert cierre_1["snapshot_comunidades"] == len(comunidades)

    ronda_2 = generar_ronda_comunidades(
        comunidades_session, torneo.id, 2, 999_999, random.Random(202)
    )
    assert len(ronda_2["enfrentamiento_ids"]) == 2
    _resolver_ronda_administrativamente(
        comunidades_session, torneo, 2, materializar_enfrentamiento
    )

    cierre_2 = procesar_cierre_ronda_comunidades_si_corresponde(
        comunidades_session, torneo.id, 2
    )
    comunidades_session.commit()
    assert cierre_2["cerrada"] is True
    assert cierre_2["es_ultima_ronda"] is True
    assert comunidades_session.get(type(torneo), torneo.id).estado == "FINALIZADO"
    assert comunidades_session.query(ComunidadesSnapshotClasificacionEquipo).count() == 8
    assert comunidades_session.query(ComunidadesSnapshotClasificacionComunidad).count() == 8
    assert sum(equipo.partidos_jugados for equipo in equipos) == 8
    assert sum(equipo.puntos_clasificacion for equipo in equipos) > Decimal("0")


def test_bye_y_regeneracion_revierten_todo_el_estado_de_la_ronda(
    comunidades_session,
    escenario_comunidades_factory,
):
    torneo, _, equipos = escenario_comunidades_factory(
        equipos=5, comunidades=5, rondas=2
    )
    original = generar_ronda_comunidades(
        comunidades_session, torneo.id, 1, 999_999, random.Random(7)
    )
    bye_original = original["bye_equipo_id"]
    ronda_original = original["ronda_id"]
    equipo_bye = comunidades_session.get(type(equipos[0]), bye_original)
    assert equipo_bye.cantidad_byes == 1
    assert equipo_bye.puntos_clasificacion == Decimal("1.50")

    regenerada = regenerar_ronda_comunidades(
        comunidades_session,
        torneo.id,
        1,
        999_999,
        random.Random(19),
    )
    assert regenerada["ronda_anterior_id"] == ronda_original
    assert regenerada["ronda_id"] != ronda_original
    assert comunidades_session.get(ComunidadesRonda, ronda_original) is None
    assert sum(equipo.cantidad_byes for equipo in equipos) == 1
    assert sum(equipo.puntos_clasificacion for equipo in equipos) == Decimal("1.50")
    assert comunidades_session.query(ComunidadesRonda).count() == 1


def test_transferencia_tras_cerrar_ambos_enfrentamientos_es_idempotente(
    comunidades_session,
    torneo_comunidades_factory,
    comunidad_comunidades_factory,
    equipo_comunidades_factory,
    materializar_enfrentamiento,
):
    from ComunidadesCore import transferir_cazador_comunidades
    from GestorSQL import ComunidadesHistorialTransicion, ComunidadesMiembro

    torneo = torneo_comunidades_factory(rondas=2)
    comunidad_origen = comunidad_comunidades_factory(torneo, "Comunidad compartida")
    otras = [
        comunidad_comunidades_factory(torneo, "Rival 1"),
        comunidad_comunidades_factory(torneo, "Rival 2"),
    ]
    origen = equipo_comunidades_factory(torneo, comunidad_origen, nombre="Origen")
    destino = equipo_comunidades_factory(torneo, comunidad_origen, nombre="Destino")
    equipo_comunidades_factory(torneo, otras[0], nombre="Rival A")
    equipo_comunidades_factory(torneo, otras[1], nombre="Rival B")
    comunidades_session.commit()

    generar_ronda_comunidades(
        comunidades_session, torneo.id, 1, 999_999, random.Random(31)
    )
    _resolver_ronda_administrativamente(
        comunidades_session, torneo, 1, materializar_enfrentamiento
    )

    transicion_origen = (
        comunidades_session.query(ComunidadesHistorialTransicion)
        .filter_by(equipo_id=origen.id)
        .one()
    )
    transicion_origen.motivo = "VICTORIA"
    transicion_origen.estado_temporal_posterior = "CAZADOR"
    origen.estado_temporal = "CAZADOR"
    destino.estado_temporal = "NEUTRO"
    comunidades_session.commit()

    actor = (
        comunidades_session.query(ComunidadesMiembro)
        .filter_by(equipo_id=origen.id, posicion=1)
        .one()
        .usuario.id_discord
    )
    transferencia = transferir_cazador_comunidades(
        comunidades_session,
        torneo_id=int(torneo.id),
        equipo_destino_nombre=destino.nombre,
        actor_discord_id=int(actor),
        clave_idempotencia="integracion-transferencia-1",
    )
    repetida = transferir_cazador_comunidades(
        comunidades_session,
        torneo_id=int(torneo.id),
        equipo_destino_nombre=destino.nombre,
        actor_discord_id=int(actor),
        clave_idempotencia="integracion-transferencia-1",
    )

    assert repetida.id == transferencia.id
    assert origen.estado_temporal == "NEUTRO"
    assert destino.estado_temporal == "CAZADOR"
    assert [
        transicion.motivo
        for transicion in comunidades_session.query(ComunidadesHistorialTransicion)
        .filter_by(equipo_id=destino.id)
        .order_by(ComunidadesHistorialTransicion.id)
        .all()
    ][-1] == "TRANSFERENCIA"


def test_api_mockeada_registra_los_dos_resultados_sin_red(
    comunidades_session,
    escenario_comunidades_factory,
    materializar_enfrentamiento,
):
    from ComunidadesCore import registrar_resultado_partido_comunidades

    class ApiBloodBowlDoble:
        def __init__(self):
            self.llamadas = []

        def obtener_partidos(self, token, competicion_id):
            self.llamadas.append((token, competicion_id))
            return [
                {"uuid": "api-partido-1", "local": 2, "visitante": 0},
                {"uuid": "api-partido-2", "local": 1, "visitante": 1},
            ]

    torneo, _, _ = escenario_comunidades_factory(
        equipos=2, comunidades=2, rondas=1
    )
    resultado_ronda = generar_ronda_comunidades(
        comunidades_session, torneo.id, 1, 999_999, random.Random(11)
    )
    enfrentamiento = comunidades_session.get(
        ComunidadesEnfrentamiento, resultado_ronda["enfrentamiento_ids"][0]
    )
    partidos = materializar_enfrentamiento(enfrentamiento, ronda_numero=1)
    api = ApiBloodBowlDoble()

    for partido, match in zip(
        partidos, api.obtener_partidos("token-falso", torneo.id_competicion_bbowl)
    ):
        registrar_resultado_partido_comunidades(
            comunidades_session,
            partido_id=int(partido.id),
            td_local=match["local"],
            td_visitante=match["visitante"],
            origen="API",
            partido_bloodbowl_id=match["uuid"],
        )
    comunidades_session.commit()

    assert api.llamadas == [("token-falso", torneo.id_competicion_bbowl)]
    assert enfrentamiento.estado == "CERRADO"
    assert {partido.partido_bloodbowl_id for partido in partidos} == {
        "api-partido-1",
        "api-partido-2",
    }
    assert {partido.resultado_origen for partido in partidos} == {"API"}
