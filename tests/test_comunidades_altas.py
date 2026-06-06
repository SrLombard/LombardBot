from datetime import datetime
from pathlib import Path
import sys

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))
from sqlalchemy import BigInteger, create_engine
from sqlalchemy.orm import Session

from ComunidadesCore import (
    ErrorConfiguracionComunidades,
    anadir_categoria_enfrentamientos_comunidades,
    anadir_categoria_partidos_comunidades,
    anadir_comunidad_comunidades,
    anadir_equipo_comunidades,
    crear_torneo_comunidades,
)
from GestorSQL import (
    Base,
    ComunidadesCategoriaEnfrentamiento,
    ComunidadesCategoriaPartido,
    ComunidadesComunidad,
    ComunidadesEquipo,
    ComunidadesMiembro,
    ComunidadesTorneo,
    Usuario,
)


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _crear_torneo(session):
    torneo = crear_torneo_comunidades(
        session,
        nombre="Copa",
        rondas_totales=3,
        fecha_fin_ronda1=datetime(2026, 7, 1, 23, 59),
        dias_por_ronda=7,
        canal_hub_id=1497290209505710120,
        creado_por_discord_id=1497290209505710121,
    )
    session.commit()
    return torneo


def _anadir_equipo(session, torneo_id, **cambios):
    argumentos = {
        "torneo_id": torneo_id,
        "nombre": "Los Rompecráneos",
        "comunidad_nombre": "Butter",
        "jugador1_discord_id": 1497290209505710122,
        "jugador1_nombre_discord": "Jugador Uno",
        "raza1": "Orcos",
        "jugador2_discord_id": 1497290209505710123,
        "jugador2_nombre_discord": "Jugador Dos",
        "raza2": "Skaven",
    }
    argumentos.update(cambios)
    return anadir_equipo_comunidades(session, **argumentos)


def test_ids_discord_de_usuarios_usan_big_integer():
    assert isinstance(Usuario.__table__.c.id_discord.type, BigInteger)


def test_anade_comunidad_y_rechaza_duplicados_exactos():
    with _session() as session:
        torneo = _crear_torneo(session)
        comunidad = anadir_comunidad_comunidades(
            session, torneo_id=torneo.id, nombre="Butter League"
        )
        session.commit()

        assert comunidad.nombre == "Butter League"
        with pytest.raises(ErrorConfiguracionComunidades, match="ya existe"):
            anadir_comunidad_comunidades(
                session, torneo_id=torneo.id, nombre="Butter League"
            )


def test_categorias_conservan_orden_y_no_aceptan_duplicados():
    with _session() as session:
        torneo = _crear_torneo(session)
        primera = anadir_categoria_partidos_comunidades(
            session, torneo_id=torneo.id, categoria_discord_id=1497290209505710130
        )
        segunda = anadir_categoria_partidos_comunidades(
            session, torneo_id=torneo.id, categoria_discord_id=1497290209505710131
        )
        enfrentamientos = anadir_categoria_enfrentamientos_comunidades(
            session, torneo_id=torneo.id, categoria_discord_id=1497290209505710130
        )
        session.commit()

        assert (primera.orden_alta, segunda.orden_alta) == (1, 2)
        assert enfrentamientos.orden_alta == 1
        with pytest.raises(ErrorConfiguracionComunidades, match="ya está configurada"):
            anadir_categoria_partidos_comunidades(
                session, torneo_id=torneo.id, categoria_discord_id=1497290209505710130
            )


def test_alta_equipo_crea_dos_miembros_y_usuarios_con_razas_exactas():
    with _session() as session:
        torneo = _crear_torneo(session)
        anadir_comunidad_comunidades(session, torneo_id=torneo.id, nombre="Butter")
        session.commit()

        equipo = _anadir_equipo(session, torneo.id)
        session.commit()

        miembros = (
            session.query(ComunidadesMiembro)
            .filter(ComunidadesMiembro.equipo_id == equipo.id)
            .order_by(ComunidadesMiembro.posicion)
            .all()
        )
        assert equipo.nombre == "Los Rompecráneos"
        assert [miembro.raza for miembro in miembros] == ["Orcos", "Skaven"]
        assert session.query(Usuario).count() == 2
        assert {usuario.id_discord for usuario in session.query(Usuario)} == {
            1497290209505710122,
            1497290209505710123,
        }


def test_alta_equipo_rechaza_nombre_usuario_y_raza_duplicados_o_invalidos():
    with _session() as session:
        torneo = _crear_torneo(session)
        anadir_comunidad_comunidades(session, torneo_id=torneo.id, nombre="Butter")
        session.commit()
        _anadir_equipo(session, torneo.id)
        session.commit()

        with pytest.raises(ErrorConfiguracionComunidades, match="ya existe"):
            _anadir_equipo(
                session,
                torneo.id,
                jugador1_discord_id=1497290209505710200,
                jugador2_discord_id=1497290209505710201,
            )
        session.rollback()
        with pytest.raises(ErrorConfiguracionComunidades, match="ya pertenece"):
            _anadir_equipo(
                session,
                torneo.id,
                nombre="Otro equipo",
                jugador2_discord_id=1497290209505710201,
            )
        session.rollback()
        with pytest.raises(ErrorConfiguracionComunidades, match="no es válida"):
            _anadir_equipo(
                session,
                torneo.id,
                nombre="Raza inválida",
                jugador1_discord_id=1497290209505710200,
                jugador2_discord_id=1497290209505710201,
                raza2="skaven",
            )


def test_error_de_alta_no_deja_registros_parciales():
    with _session() as session:
        torneo = _crear_torneo(session)
        anadir_comunidad_comunidades(session, torneo_id=torneo.id, nombre="Butter")
        session.commit()

        with pytest.raises(ErrorConfiguracionComunidades):
            _anadir_equipo(session, torneo.id, raza2="Raza inventada")
        session.rollback()

        assert session.query(Usuario).count() == 0
        assert session.query(ComunidadesEquipo).count() == 0
        assert session.query(ComunidadesMiembro).count() == 0


@pytest.mark.parametrize("operacion", ["comunidad", "partidos", "enfrentamientos", "equipo"])
def test_altas_se_bloquean_tras_iniciar_torneo(operacion):
    with _session() as session:
        torneo = _crear_torneo(session)
        anadir_comunidad_comunidades(session, torneo_id=torneo.id, nombre="Butter")
        session.commit()
        torneo.estado = "EN_CURSO"
        session.commit()

        with pytest.raises(ErrorConfiguracionComunidades, match="estado CREADO"):
            if operacion == "comunidad":
                anadir_comunidad_comunidades(session, torneo_id=torneo.id, nombre="Hispana")
            elif operacion == "partidos":
                anadir_categoria_partidos_comunidades(
                    session, torneo_id=torneo.id, categoria_discord_id=10
                )
            elif operacion == "enfrentamientos":
                anadir_categoria_enfrentamientos_comunidades(
                    session, torneo_id=torneo.id, categoria_discord_id=10
                )
            else:
                _anadir_equipo(session, torneo.id)
        session.rollback()

        assert session.query(ComunidadesComunidad).count() == 1
        assert session.query(ComunidadesCategoriaPartido).count() == 0
        assert session.query(ComunidadesCategoriaEnfrentamiento).count() == 0
        assert session.query(ComunidadesEquipo).count() == 0
