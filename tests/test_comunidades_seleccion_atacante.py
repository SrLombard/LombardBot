from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
import sys
import threading

sys.path.append(str(Path(__file__).resolve().parents[1]))

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from ComunidadesCore import (
    ErrorSeleccionAtacanteComunidades,
    registrar_eleccion_atacante_comunidades,
)
from GestorSQL import (
    Base,
    ComunidadesComunidad,
    ComunidadesEleccionAtacante,
    ComunidadesEnfrentamiento,
    ComunidadesEquipo,
    ComunidadesMiembro,
    ComunidadesRonda,
    ComunidadesTorneo,
    Usuario,
)


def _engine(url="sqlite://"):
    engine = create_engine(
        url,
        connect_args={"check_same_thread": False, "timeout": 10},
    )

    @event.listens_for(engine, "connect")
    def _foreign_keys(dbapi_connection, _):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    return engine


def _crear_escenario(engine):
    with Session(engine) as session:
        torneo = ComunidadesTorneo(
            nombre="Comunidades",
            rondas_totales=1,
            fecha_fin_ronda1=datetime(2026, 7, 8),
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
            ComunidadesEquipo(
                torneo_id=torneo.id,
                comunidad_id=comunidades[0].id,
                nombre="Equipo A",
            ),
            ComunidadesEquipo(
                torneo_id=torneo.id,
                comunidad_id=comunidades[1].id,
                nombre="Equipo B",
            ),
        ]
        session.add_all(equipos)
        session.flush()
        usuarios = [
            Usuario(idUsuarios=11, id_discord=101, nombre_discord="A1"),
            Usuario(idUsuarios=12, id_discord=102, nombre_discord="A2"),
            Usuario(idUsuarios=21, id_discord=201, nombre_discord="B1"),
            Usuario(idUsuarios=22, id_discord=202, nombre_discord="B2"),
            Usuario(idUsuarios=31, id_discord=301, nombre_discord="Ajeno"),
        ]
        session.add_all(usuarios)
        session.flush()
        session.add_all(
            [
                ComunidadesMiembro(
                    torneo_id=torneo.id,
                    equipo_id=equipos[0].id,
                    usuario_id=11,
                    posicion=1,
                    raza="Humanos",
                ),
                ComunidadesMiembro(
                    torneo_id=torneo.id,
                    equipo_id=equipos[0].id,
                    usuario_id=12,
                    posicion=2,
                    raza="Orcos",
                ),
                ComunidadesMiembro(
                    torneo_id=torneo.id,
                    equipo_id=equipos[1].id,
                    usuario_id=21,
                    posicion=1,
                    raza="Skaven",
                ),
                ComunidadesMiembro(
                    torneo_id=torneo.id,
                    equipo_id=equipos[1].id,
                    usuario_id=22,
                    posicion=2,
                    raza="Enanos",
                ),
            ]
        )
        ronda = ComunidadesRonda(
            torneo_id=torneo.id,
            numero=1,
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
            canal_general_discord_id=555,
        )
        session.add(enfrentamiento)
        session.commit()
        return enfrentamiento.id


def test_resuelve_por_canal_registra_actor_y_deriva_defensor():
    engine = _engine()
    enfrentamiento_id = _crear_escenario(engine)
    fecha = datetime(2026, 7, 2, 12, 30)

    with Session(engine) as session:
        resultado = registrar_eleccion_atacante_comunidades(
            session,
            canal_general_discord_id=555,
            actor_discord_id=101,
            atacante_usuario_id=11,
            elegido_en=fecha,
        )

        assert resultado.eleccion.enfrentamiento_id == enfrentamiento_id
        assert resultado.eleccion.atacante_usuario_id == 11
        assert resultado.eleccion.defensor_usuario_id == 12
        assert resultado.eleccion.elegido_por_discord_id == 101
        assert resultado.eleccion.elegido_en == fecha
        assert resultado.atacante.idUsuarios == 11
        assert resultado.defensor.idUsuarios == 12
        assert resultado.ambas_elecciones_completas is False
        assert resultado.requiere_crear_partidos is False
        assert resultado.eleccion.bloqueada is False


@pytest.mark.parametrize(
    ("actor", "atacante", "codigo"),
    [
        (301, 11, "ACTOR_NO_PERTENECE"),
        (101, 21, "ATACANTE_NO_PERTENECE"),
        (101, 31, "ATACANTE_NO_PERTENECE"),
    ],
)
def test_rechaza_actor_ajeno_y_candidato_fuera_del_equipo(actor, atacante, codigo):
    engine = _engine()
    enfrentamiento_id = _crear_escenario(engine)

    with Session(engine) as session:
        with pytest.raises(ErrorSeleccionAtacanteComunidades) as error:
            registrar_eleccion_atacante_comunidades(
                session,
                enfrentamiento_id=enfrentamiento_id,
                actor_discord_id=actor,
                atacante_usuario_id=atacante,
            )
        assert error.value.codigo == codigo
        assert session.query(ComunidadesEleccionAtacante).count() == 0


def test_permite_cambiar_eleccion_antes_de_que_el_rival_elija():
    engine = _engine()
    enfrentamiento_id = _crear_escenario(engine)

    with Session(engine) as session:
        primera = registrar_eleccion_atacante_comunidades(
            session,
            enfrentamiento_id=enfrentamiento_id,
            actor_discord_id=101,
            atacante_usuario_id=11,
            elegido_en=datetime(2026, 7, 2, 10, 0),
        )
        segunda = registrar_eleccion_atacante_comunidades(
            session,
            enfrentamiento_id=enfrentamiento_id,
            actor_discord_id=102,
            atacante_usuario_id=12,
            elegido_en=datetime(2026, 7, 2, 11, 0),
        )

        assert segunda.eleccion.id == primera.eleccion.id
        assert session.query(ComunidadesEleccionAtacante).count() == 1
        assert segunda.eleccion.atacante_usuario_id == 12
        assert segunda.eleccion.defensor_usuario_id == 11
        assert segunda.eleccion.elegido_por_discord_id == 102
        assert segunda.eleccion.elegido_en == datetime(2026, 7, 2, 11, 0)


def test_segunda_eleccion_bloquea_ambas_y_marca_materializacion_pendiente():
    engine = _engine()
    enfrentamiento_id = _crear_escenario(engine)

    with Session(engine) as session:
        registrar_eleccion_atacante_comunidades(
            session,
            enfrentamiento_id=enfrentamiento_id,
            actor_discord_id=101,
            atacante_usuario_id=11,
        )
        resultado = registrar_eleccion_atacante_comunidades(
            session,
            enfrentamiento_id=enfrentamiento_id,
            actor_discord_id=201,
            atacante_usuario_id=22,
        )

        elecciones = session.query(ComunidadesEleccionAtacante).all()
        enfrentamiento = session.get(ComunidadesEnfrentamiento, enfrentamiento_id)
        assert len(elecciones) == 2
        assert all(eleccion.bloqueada for eleccion in elecciones)
        assert enfrentamiento.estado == "ELECCIONES_COMPLETAS"
        assert resultado.ambas_elecciones_completas is True
        assert resultado.requiere_crear_partidos is True
        assert resultado.atacante.idUsuarios == 22
        assert resultado.defensor.idUsuarios == 21


def test_repeticion_identica_es_idempotente_y_cambio_posterior_se_rechaza():
    engine = _engine()
    enfrentamiento_id = _crear_escenario(engine)

    with Session(engine) as session:
        registrar_eleccion_atacante_comunidades(
            session,
            enfrentamiento_id=enfrentamiento_id,
            actor_discord_id=101,
            atacante_usuario_id=11,
        )
        original = registrar_eleccion_atacante_comunidades(
            session,
            enfrentamiento_id=enfrentamiento_id,
            actor_discord_id=201,
            atacante_usuario_id=21,
        )
        repetida = registrar_eleccion_atacante_comunidades(
            session,
            enfrentamiento_id=enfrentamiento_id,
            actor_discord_id=201,
            atacante_usuario_id=21,
        )

        assert repetida.eleccion.id == original.eleccion.id
        assert repetida.ambas_elecciones_completas is True
        assert session.query(ComunidadesEleccionAtacante).count() == 2

        with pytest.raises(ErrorSeleccionAtacanteComunidades) as error:
            registrar_eleccion_atacante_comunidades(
                session,
                enfrentamiento_id=enfrentamiento_id,
                actor_discord_id=202,
                atacante_usuario_id=22,
            )
        assert error.value.codigo == "ELECCIONES_BLOQUEADAS"
        elecciones = session.query(ComunidadesEleccionAtacante).all()
        assert {eleccion.atacante_usuario_id for eleccion in elecciones} == {11, 21}


def test_dos_elecciones_simultaneas_no_duplican_estado(tmp_path: Path):
    database = tmp_path / "selecciones.sqlite"
    engine = _engine(f"sqlite:///{database}")
    enfrentamiento_id = _crear_escenario(engine)
    barrera = threading.Barrier(2)

    def elegir(actor, atacante):
        with Session(engine) as session:
            barrera.wait(timeout=5)
            resultado = registrar_eleccion_atacante_comunidades(
                session,
                enfrentamiento_id=enfrentamiento_id,
                actor_discord_id=actor,
                atacante_usuario_id=atacante,
            )
            return resultado.ambas_elecciones_completas

    with ThreadPoolExecutor(max_workers=2) as executor:
        futuros = [executor.submit(elegir, 101, 11), executor.submit(elegir, 201, 21)]
        resultados = [futuro.result(timeout=15) for futuro in futuros]

    with Session(engine) as session:
        elecciones = session.query(ComunidadesEleccionAtacante).all()
        enfrentamiento = session.get(ComunidadesEnfrentamiento, enfrentamiento_id)
        assert sorted(resultados) == [False, True]
        assert len(elecciones) == 2
        assert {eleccion.equipo_id for eleccion in elecciones} == {
            enfrentamiento.equipo_a_id,
            enfrentamiento.equipo_b_id,
        }
        assert all(eleccion.bloqueada for eleccion in elecciones)
        assert enfrentamiento.estado == "ELECCIONES_COMPLETAS"


def test_dos_actualizaciones_simultaneas_del_mismo_equipo_conservan_una_sola_fila(
    tmp_path: Path,
):
    database = tmp_path / "seleccion-mismo-equipo.sqlite"
    engine = _engine(f"sqlite:///{database}")
    enfrentamiento_id = _crear_escenario(engine)
    barrera = threading.Barrier(2)

    def elegir(actor, atacante):
        with Session(engine) as session:
            barrera.wait(timeout=5)
            registrar_eleccion_atacante_comunidades(
                session,
                enfrentamiento_id=enfrentamiento_id,
                actor_discord_id=actor,
                atacante_usuario_id=atacante,
            )

    with ThreadPoolExecutor(max_workers=2) as executor:
        futuros = [executor.submit(elegir, 101, 11), executor.submit(elegir, 102, 12)]
        for futuro in futuros:
            futuro.result(timeout=15)

    with Session(engine) as session:
        elecciones = session.query(ComunidadesEleccionAtacante).all()
        enfrentamiento = session.get(ComunidadesEnfrentamiento, enfrentamiento_id)
        assert len(elecciones) == 1
        assert elecciones[0].atacante_usuario_id in {11, 12}
        assert elecciones[0].bloqueada is False
        assert enfrentamiento.estado == "PENDIENTE_ELECCIONES"
