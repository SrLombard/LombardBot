from datetime import datetime
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from ComunidadesCore import (
    ErrorAdministracionEleccionesComunidades,
    consultar_elecciones_comunidades,
    forzar_elecciones_comunidades,
)
from GestorSQL import (
    Base,
    ComunidadesComunidad,
    ComunidadesEleccionAtacante,
    ComunidadesEnfrentamiento,
    ComunidadesEquipo,
    ComunidadesMiembro,
    ComunidadesPartido,
    ComunidadesRonda,
    ComunidadesTorneo,
    Usuario,
)


def _engine():
    engine = create_engine("sqlite://")

    @event.listens_for(engine, "connect")
    def _foreign_keys(dbapi_connection, _):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    return engine


def _escenario(session):
    torneo = ComunidadesTorneo(
        nombre="Comunidades",
        rondas_totales=1,
        fecha_fin_ronda1=datetime(2026, 7, 8, 22, 0),
        plantilla_mensaje_ronda1="R1",
        plantilla_mensaje_rondas_siguientes="R2",
        creado_por_discord_id=999,
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
        ComunidadesEquipo(torneo_id=torneo.id, comunidad_id=comunidades[0].id, nombre="Equipo A"),
        ComunidadesEquipo(torneo_id=torneo.id, comunidad_id=comunidades[1].id, nombre="Equipo B"),
    ]
    session.add_all(equipos)
    session.flush()
    usuarios = [
        Usuario(idUsuarios=11, id_discord=101, nombre_discord="A Uno"),
        Usuario(idUsuarios=12, id_discord=102, nombre_discord="A Dos"),
        Usuario(idUsuarios=21, id_discord=201, nombre_discord="B Uno"),
        Usuario(idUsuarios=22, id_discord=202, nombre_discord="B Dos"),
    ]
    session.add_all(usuarios)
    session.add_all([
        ComunidadesMiembro(torneo_id=torneo.id, equipo_id=equipos[0].id, usuario_id=11, posicion=1, raza="Orcos"),
        ComunidadesMiembro(torneo_id=torneo.id, equipo_id=equipos[0].id, usuario_id=12, posicion=2, raza="Enanos"),
        ComunidadesMiembro(torneo_id=torneo.id, equipo_id=equipos[1].id, usuario_id=21, posicion=1, raza="Skaven"),
        ComunidadesMiembro(torneo_id=torneo.id, equipo_id=equipos[1].id, usuario_id=22, posicion=2, raza="Humanos"),
    ])
    ronda = ComunidadesRonda(
        torneo_id=torneo.id,
        numero=1,
        estado="ABIERTA",
        fecha_inicio=datetime(2026, 7, 1),
        fecha_fin=datetime(2026, 7, 8),
        generada_por_discord_id=999,
    )
    session.add(ronda)
    session.flush()
    enfrentamiento = ComunidadesEnfrentamiento(
        torneo_id=torneo.id,
        ronda_id=ronda.id,
        mesa_numero=1,
        equipo_a_id=equipos[0].id,
        equipo_b_id=equipos[1].id,
        estado="PENDIENTE_ELECCIONES",
        canal_general_discord_id=555,
    )
    session.add(enfrentamiento)
    session.commit()
    return torneo.id, enfrentamiento.id


def test_consulta_diferencia_pendiente_abierta_y_bloqueada():
    engine = _engine()
    with Session(engine) as session:
        torneo_id, enfrentamiento_id = _escenario(session)
        filas = consultar_elecciones_comunidades(session, torneo_id=torneo_id, ronda_numero=1)
        assert [e.pendiente for e in filas[0].elecciones] == [True, True]

        enfrentamiento = session.get(ComunidadesEnfrentamiento, enfrentamiento_id)
        session.add(
            ComunidadesEleccionAtacante(
                torneo_id=torneo_id,
                enfrentamiento_id=enfrentamiento_id,
                equipo_id=enfrentamiento.equipo_a_id,
                atacante_usuario_id=11,
                defensor_usuario_id=12,
                elegido_por_discord_id=101,
                elegido_en=datetime(2026, 7, 2, 10, 0),
                bloqueada=False,
            )
        )
        session.flush()
        filas = consultar_elecciones_comunidades(session, torneo_id=torneo_id, ronda_numero=1)
        assert [e.pendiente for e in filas[0].elecciones] == [False, True]
        assert filas[0].elecciones[0].bloqueada is False

        forzar_elecciones_comunidades(
            session,
            torneo_id=torneo_id,
            ronda_numero=1,
            enfrentamiento_id=enfrentamiento_id,
            atacante_equipo_a_discord_id=102,
            atacante_equipo_b_discord_id=201,
            actor_discord_id=999,
            elegido_en=datetime(2026, 7, 2, 12, 0),
        )
        filas = consultar_elecciones_comunidades(session, torneo_id=torneo_id, ronda_numero=1)
        assert [e.pendiente for e in filas[0].elecciones] == [False, False]
        assert [e.bloqueada for e in filas[0].elecciones] == [True, True]
        assert [e.atacante.idUsuarios for e in filas[0].elecciones] == [12, 21]
        assert [e.defensor.idUsuarios for e in filas[0].elecciones] == [11, 22]
        assert all(e.actor_discord_id == 999 for e in filas[0].elecciones)


def test_forzado_reemplaza_una_eleccion_y_audita_al_comisario():
    engine = _engine()
    with Session(engine) as session:
        torneo_id, enfrentamiento_id = _escenario(session)
        session.add(
            ComunidadesEleccionAtacante(
                torneo_id=torneo_id,
                enfrentamiento_id=enfrentamiento_id,
                equipo_id=session.get(ComunidadesEnfrentamiento, enfrentamiento_id).equipo_a_id,
                atacante_usuario_id=11,
                defensor_usuario_id=12,
                elegido_por_discord_id=101,
                elegido_en=datetime(2026, 7, 2, 10, 0),
                bloqueada=False,
            )
        )
        session.commit()

        forzar_elecciones_comunidades(
            session,
            torneo_id=torneo_id,
            ronda_numero=1,
            enfrentamiento_id=enfrentamiento_id,
            atacante_equipo_a_discord_id=102,
            atacante_equipo_b_discord_id=202,
            actor_discord_id=999,
            elegido_en=datetime(2026, 7, 2, 12, 0),
        )
        elecciones = session.query(ComunidadesEleccionAtacante).order_by(ComunidadesEleccionAtacante.equipo_id).all()
        assert len(elecciones) == 2
        assert [e.atacante_usuario_id for e in elecciones] == [12, 22]
        assert all(e.bloqueada and e.elegido_por_discord_id == 999 for e in elecciones)
        assert session.get(ComunidadesEnfrentamiento, enfrentamiento_id).estado == "ELECCIONES_COMPLETAS"


@pytest.mark.parametrize("atacante_a,atacante_b", [(201, 202), (101, 102)])
def test_forzado_rechaza_atacante_del_lado_incorrecto(atacante_a, atacante_b):
    engine = _engine()
    with Session(engine) as session:
        torneo_id, enfrentamiento_id = _escenario(session)
        with pytest.raises(ErrorAdministracionEleccionesComunidades) as error:
            forzar_elecciones_comunidades(
                session,
                torneo_id=torneo_id,
                ronda_numero=1,
                enfrentamiento_id=enfrentamiento_id,
                atacante_equipo_a_discord_id=atacante_a,
                atacante_equipo_b_discord_id=atacante_b,
                actor_discord_id=999,
            )
        assert error.value.codigo == "ATACANTE_NO_PERTENECE"
        session.rollback()
        assert session.query(ComunidadesEleccionAtacante).count() == 0


def test_reintento_con_partidos_existentes_es_idempotente_y_no_admite_cambiar_atacantes():
    engine = _engine()
    with Session(engine) as session:
        torneo_id, enfrentamiento_id = _escenario(session)
        forzar_elecciones_comunidades(
            session,
            torneo_id=torneo_id,
            ronda_numero=1,
            enfrentamiento_id=enfrentamiento_id,
            atacante_equipo_a_discord_id=101,
            atacante_equipo_b_discord_id=201,
            actor_discord_id=999,
        )
        enfrentamiento = session.get(ComunidadesEnfrentamiento, enfrentamiento_id)
        session.add_all([
            ComunidadesPartido(
                torneo_id=torneo_id, enfrentamiento_id=enfrentamiento_id, indice=1,
                equipo_local_id=enfrentamiento.equipo_a_id, equipo_visitante_id=enfrentamiento.equipo_b_id,
                usuario_local_id=11, usuario_visitante_id=22, atacante_usuario_id=11, defensor_usuario_id=22,
            ),
            ComunidadesPartido(
                torneo_id=torneo_id, enfrentamiento_id=enfrentamiento_id, indice=2,
                equipo_local_id=enfrentamiento.equipo_b_id, equipo_visitante_id=enfrentamiento.equipo_a_id,
                usuario_local_id=21, usuario_visitante_id=12, atacante_usuario_id=21, defensor_usuario_id=12,
            ),
        ])
        session.commit()

        forzar_elecciones_comunidades(
            session,
            torneo_id=torneo_id,
            ronda_numero=1,
            enfrentamiento_id=enfrentamiento_id,
            atacante_equipo_a_discord_id=101,
            atacante_equipo_b_discord_id=201,
            actor_discord_id=999,
        )
        assert session.query(ComunidadesPartido).count() == 2

        with pytest.raises(ErrorAdministracionEleccionesComunidades) as error:
            forzar_elecciones_comunidades(
                session,
                torneo_id=torneo_id,
                ronda_numero=1,
                enfrentamiento_id=enfrentamiento_id,
                atacante_equipo_a_discord_id=102,
                atacante_equipo_b_discord_id=201,
                actor_discord_id=999,
            )
        assert error.value.codigo == "PARTIDOS_YA_CREADOS"
