from datetime import datetime
from decimal import Decimal
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import ComunidadesCore
from ComunidadesCore import (
    ErrorRegistroResultadoComunidades,
    registrar_resultado_partido_comunidades,
)
from GestorSQL import (
    Base,
    ComunidadesComunidad,
    ComunidadesEnfrentamiento,
    ComunidadesEquipo,
    ComunidadesFotografiaEstado,
    ComunidadesHistorialTransicion,
    ComunidadesPartido,
    ComunidadesRonda,
    ComunidadesTorneo,
    Usuario,
)


def _session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _foreign_keys(dbapi_connection, _):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    return Session(engine)


def _escenario(*, estado_a="CAZADOR", zombie_a=False, estado_b="HERIDO", zombie_b=False):
    session = _session()
    torneo = ComunidadesTorneo(
        nombre="Comunidades",
        estado="EN_CURSO",
        rondas_totales=1,
        fecha_fin_ronda1=datetime(2026, 7, 8),
        puntos_clasificacion_victoria=Decimal("4"),
        puntos_clasificacion_empate=Decimal("2"),
        puntos_clasificacion_derrota=Decimal("0.5"),
        puntos_individuales_victoria=Decimal("3"),
        puntos_individuales_empate=Decimal("1"),
        puntos_individuales_derrota=Decimal("0"),
        plantilla_mensaje_ronda1="R1",
        plantilla_mensaje_rondas_siguientes="R2",
        creado_por_discord_id=1,
    )
    session.add(torneo)
    session.flush()
    comunidades = [
        ComunidadesComunidad(torneo_id=torneo.id, nombre="A"),
        ComunidadesComunidad(torneo_id=torneo.id, nombre="B"),
    ]
    session.add_all(comunidades)
    session.flush()
    equipos = [
        ComunidadesEquipo(
            torneo_id=torneo.id,
            comunidad_id=comunidades[0].id,
            nombre="Equipo A",
            estado_temporal=estado_a,
            es_zombie=zombie_a,
        ),
        ComunidadesEquipo(
            torneo_id=torneo.id,
            comunidad_id=comunidades[1].id,
            nombre="Equipo B",
            estado_temporal=estado_b,
            es_zombie=zombie_b,
        ),
    ]
    session.add_all(equipos)
    session.add_all(
        [
            Usuario(idUsuarios=11, nombre_discord="A atacante"),
            Usuario(idUsuarios=12, nombre_discord="A defensor"),
            Usuario(idUsuarios=21, nombre_discord="B atacante"),
            Usuario(idUsuarios=22, nombre_discord="B defensor"),
        ]
    )
    ronda = ComunidadesRonda(
        torneo_id=torneo.id,
        numero=1,
        estado="ABIERTA",
        fecha_inicio=datetime(2026, 7, 1),
        fecha_fin=datetime(2026, 7, 8),
        generada_por_discord_id=1,
    )
    session.add(ronda)
    session.flush()
    enfrentamiento = ComunidadesEnfrentamiento(
        torneo_id=torneo.id,
        ronda_id=ronda.id,
        mesa_numero=1,
        equipo_a_id=equipos[0].id,
        equipo_b_id=equipos[1].id,
        estado="PARTIDOS_CREADOS",
    )
    session.add(enfrentamiento)
    session.flush()
    partidos = [
        ComunidadesPartido(
            torneo_id=torneo.id,
            enfrentamiento_id=enfrentamiento.id,
            indice=1,
            equipo_local_id=equipos[0].id,
            equipo_visitante_id=equipos[1].id,
            usuario_local_id=11,
            usuario_visitante_id=22,
            atacante_usuario_id=11,
            defensor_usuario_id=22,
        ),
        ComunidadesPartido(
            torneo_id=torneo.id,
            enfrentamiento_id=enfrentamiento.id,
            indice=2,
            equipo_local_id=equipos[1].id,
            equipo_visitante_id=equipos[0].id,
            usuario_local_id=21,
            usuario_visitante_id=12,
            atacante_usuario_id=21,
            defensor_usuario_id=12,
        ),
    ]
    session.add_all(partidos)
    session.add_all(
        [
            ComunidadesFotografiaEstado(
                torneo_id=torneo.id,
                ronda_id=ronda.id,
                enfrentamiento_id=enfrentamiento.id,
                equipo_id=equipos[0].id,
                comunidad_id=comunidades[0].id,
                estado_temporal=estado_a,
                es_zombie=zombie_a,
            ),
            ComunidadesFotografiaEstado(
                torneo_id=torneo.id,
                ronda_id=ronda.id,
                enfrentamiento_id=enfrentamiento.id,
                equipo_id=equipos[1].id,
                comunidad_id=comunidades[1].id,
                estado_temporal=estado_b,
                es_zombie=zombie_b,
            ),
        ]
    )
    session.commit()
    return session, torneo, comunidades, equipos, enfrentamiento, partidos


def test_primer_partido_solo_guarda_resultado_y_no_aplica_transiciones():
    session, _, comunidades, equipos, enfrentamiento, partidos = _escenario()

    registro = registrar_resultado_partido_comunidades(
        session,
        partido_id=partidos[0].id,
        td_local=2,
        td_visitante=1,
        origen="API",
        partido_bloodbowl_id="bb-1",
    )

    assert registro.enfrentamiento_resuelto is False
    assert registro.idempotente is False
    assert partidos[0].estado == "FINALIZADO"
    assert partidos[0].puntos_internos_local == Decimal("3")
    assert partidos[0].puntos_internos_visitante == Decimal("0")
    assert enfrentamiento.estado == "EN_CURSO"
    assert session.query(ComunidadesHistorialTransicion).count() == 0
    assert [(e.partidos_jugados, e.puntos_clasificacion) for e in equipos] == [
        (0, Decimal("0")),
        (0, Decimal("0")),
    ]
    assert [(c.puntos_zombificaciones, c.zombies_matados) for c in comunidades] == [
        (Decimal("0"), 0),
        (Decimal("0"), 0),
    ]


def test_segundo_partido_resuelve_una_vez_con_fotografia_y_origen_mixto():
    session, _, comunidades, equipos, enfrentamiento, partidos = _escenario()
    registrar_resultado_partido_comunidades(
        session,
        partido_id=partidos[0].id,
        td_local=2,
        td_visitante=0,
        origen="API",
        partido_bloodbowl_id="bb-1",
    )
    # La resolución debe ignorar estos estados vivos y usar CAZADOR/HERIDO fotografiados.
    equipos[0].estado_temporal = "NEUTRO"
    equipos[1].estado_temporal = "NEUTRO"
    session.flush()

    registro = registrar_resultado_partido_comunidades(
        session,
        partido_id=partidos[1].id,
        td_local=1,
        td_visitante=1,
        origen="ADMIN",
    )

    assert registro.enfrentamiento_resuelto is True
    assert enfrentamiento.estado == "ADMINISTRADO"
    assert enfrentamiento.resultado_origen == "ADMIN"
    assert enfrentamiento.ganador_equipo_id == equipos[0].id
    assert (enfrentamiento.puntos_internos_a, enfrentamiento.puntos_internos_b) == (
        Decimal("4"),
        Decimal("1"),
    )
    assert (equipos[0].puntos_clasificacion, equipos[1].puntos_clasificacion) == (
        Decimal("4"),
        Decimal("0.5"),
    )
    assert equipos[0].estado_temporal == "NEUTRO"
    assert (equipos[1].estado_temporal, equipos[1].es_zombie) == ("NEUTRO", True)
    assert comunidades[0].puntos_zombificaciones == Decimal("1")
    assert comunidades[0].zombies_matados == 0
    historiales = session.query(ComunidadesHistorialTransicion).all()
    assert len(historiales) == 2
    assert sum(Decimal(h.puntos_comunitarios_generados) for h in historiales) == Decimal("1")
    assert sum(h.kills_generadas for h in historiales) == 0

    reintento = registrar_resultado_partido_comunidades(
        session,
        partido_id=partidos[1].id,
        td_local=1,
        td_visitante=1,
        origen="ADMIN",
    )
    assert reintento.idempotente is True
    assert session.query(ComunidadesHistorialTransicion).count() == 2
    assert comunidades[0].puntos_zombificaciones == Decimal("1")
    assert (equipos[0].partidos_jugados, equipos[1].partidos_jugados) == (1, 1)


def test_kill_incrementa_contador_y_el_mismo_historial():
    session, _, comunidades, equipos, _, partidos = _escenario(
        estado_a="CAZADOR_Z", estado_b="HERIDO", zombie_b=True
    )
    registrar_resultado_partido_comunidades(
        session,
        partido_id=partidos[0].id,
        td_local=1,
        td_visitante=0,
        origen="ADMIN",
    )
    registrar_resultado_partido_comunidades(
        session,
        partido_id=partidos[1].id,
        td_local=0,
        td_visitante=0,
        origen="ADMIN",
    )

    historiales = session.query(ComunidadesHistorialTransicion).all()
    assert comunidades[0].zombies_matados == 1
    assert sum(h.kills_generadas for h in historiales) == 1
    assert comunidades[0].puntos_zombificaciones == Decimal("0")
    assert equipos[0].estado_temporal == "NEUTRO"
    assert (equipos[1].estado_temporal, equipos[1].es_zombie) == ("NEUTRO", True)


def test_doble_forfait_global_da_dos_derrotas_y_conserva_estados():
    session, _, comunidades, equipos, enfrentamiento, partidos = _escenario(
        estado_a="HERIDO", estado_b="CAZADOR_Z", zombie_b=True
    )
    for partido in partidos:
        registrar_resultado_partido_comunidades(
            session,
            partido_id=partido.id,
            td_local=0,
            td_visitante=0,
            origen="ADMIN",
            tipo_forfait="DOBLE",
        )

    assert enfrentamiento.es_doble_forfait is True
    assert enfrentamiento.ganador_equipo_id is None
    assert (enfrentamiento.puntos_internos_a, enfrentamiento.puntos_internos_b) == (
        Decimal("0"),
        Decimal("0"),
    )
    assert (enfrentamiento.puntos_clasificacion_a, enfrentamiento.puntos_clasificacion_b) == (
        Decimal("0.5"),
        Decimal("0.5"),
    )
    assert [(e.victorias, e.empates, e.derrotas) for e in equipos] == [(0, 0, 1), (0, 0, 1)]
    assert (equipos[0].estado_temporal, equipos[0].es_zombie) == ("HERIDO", False)
    assert (equipos[1].estado_temporal, equipos[1].es_zombie) == ("CAZADOR_Z", True)
    assert [(c.puntos_zombificaciones, c.zombies_matados) for c in comunidades] == [
        (Decimal("0"), 0),
        (Decimal("0"), 0),
    ]
    assert {h.motivo for h in session.query(ComunidadesHistorialTransicion)} == {
        "DOBLE_FORFAIT"
    }


def test_id_bloodbowl_duplicado_se_rechaza_antes_de_modificar_otro_partido():
    session, _, _, _, enfrentamiento, partidos = _escenario()
    registrar_resultado_partido_comunidades(
        session,
        partido_id=partidos[0].id,
        td_local=1,
        td_visitante=0,
        origen="API",
        partido_bloodbowl_id="duplicado",
    )

    with pytest.raises(ErrorRegistroResultadoComunidades) as exc:
        registrar_resultado_partido_comunidades(
            session,
            partido_id=partidos[1].id,
            td_local=0,
            td_visitante=1,
            origen="API",
            partido_bloodbowl_id="duplicado",
        )

    assert exc.value.codigo == "ID_BLOODBOWL_DUPLICADO"
    assert partidos[1].estado == "PENDIENTE"
    assert enfrentamiento.estado == "EN_CURSO"


def test_fallo_despues_de_incrementar_comunidad_revierte_toda_la_resolucion(monkeypatch):
    session, _, comunidades, equipos, enfrentamiento, partidos = _escenario()
    registrar_resultado_partido_comunidades(
        session,
        partido_id=partidos[0].id,
        td_local=2,
        td_visitante=0,
        origen="ADMIN",
    )
    original = ComunidadesCore._incrementar_contadores_comunidad

    def incrementar_y_fallar(comunidad, *, puntos_zombificacion, kills):
        original(
            comunidad,
            puntos_zombificacion=puntos_zombificacion,
            kills=kills,
        )
        raise RuntimeError("fallo simulado tras incrementar comunidad")

    monkeypatch.setattr(
        ComunidadesCore, "_incrementar_contadores_comunidad", incrementar_y_fallar
    )
    with pytest.raises(RuntimeError, match="fallo simulado"):
        registrar_resultado_partido_comunidades(
            session,
            partido_id=partidos[1].id,
            td_local=0,
            td_visitante=0,
            origen="ADMIN",
        )

    session.expire_all()
    assert session.get(ComunidadesPartido, partidos[1].id).estado == "PENDIENTE"
    assert session.get(ComunidadesEnfrentamiento, enfrentamiento.id).estado == "EN_CURSO"
    assert session.query(ComunidadesHistorialTransicion).count() == 0
    assert (
        session.get(ComunidadesComunidad, comunidades[0].id).puntos_zombificaciones
        == Decimal("0")
    )
    for equipo in equipos:
        actual = session.get(ComunidadesEquipo, equipo.id)
        assert actual.partidos_jugados == 0
        assert actual.puntos_clasificacion == Decimal("0")
