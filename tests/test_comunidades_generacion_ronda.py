import json
import random
from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from ComunidadesCore import (
    ErrorGeneracionRondaComunidades,
    generar_ronda_comunidades,
)
from GestorSQL import (
    Base,
    ComunidadesComunidad,
    ComunidadesEnfrentamiento,
    ComunidadesEquipo,
    ComunidadesFotografiaEstado,
    ComunidadesHistorialTransicion,
    ComunidadesMiembro,
    ComunidadesRonda,
    ComunidadesTorneo,
    ComunidadesTrazaEmparejamiento,
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


def _torneo(session, rondas=3):
    torneo = ComunidadesTorneo(
        nombre="Comunidades",
        rondas_totales=rondas,
        fecha_fin_ronda1=datetime(2026, 7, 8),
        dias_por_ronda=7,
        puntos_clasificacion_bye=Decimal("1.50"),
        plantilla_mensaje_ronda1="R1",
        plantilla_mensaje_rondas_siguientes="R{ronda}",
        creado_por_discord_id=1,
    )
    session.add(torneo)
    session.flush()
    return torneo


def _equipo(
    session,
    torneo,
    equipo_id,
    comunidad_nombre,
    *,
    estado="NEUTRO",
    zombie=False,
    razas=("Humanos", "Orcos"),
):
    comunidad = ComunidadesComunidad(
        torneo_id=torneo.id, nombre=comunidad_nombre
    )
    session.add(comunidad)
    session.flush()
    equipo = ComunidadesEquipo(
        id=equipo_id,
        torneo_id=torneo.id,
        comunidad_id=comunidad.id,
        nombre=f"Equipo {equipo_id}",
        estado_temporal=estado,
        es_zombie=zombie,
    )
    session.add(equipo)
    session.flush()
    for posicion, raza in enumerate(razas, start=1):
        usuario_id = equipo_id * 10 + posicion
        usuario = Usuario(idUsuarios=usuario_id, nombre_discord=f"U{usuario_id}")
        session.add(usuario)
        session.flush()
        session.add(
            ComunidadesMiembro(
                torneo_id=torneo.id,
                equipo_id=equipo.id,
                usuario_id=usuario.idUsuarios,
                posicion=posicion,
                raza=raza,
            )
        )
    session.flush()
    return equipo


def test_genera_ronda_completa_con_fotografias_traza_e_inicio_del_torneo():
    session = _session()
    torneo = _torneo(session)
    equipos = [
        _equipo(session, torneo, 1, "A", estado="CAZADOR", razas=("R1", "R2")),
        _equipo(session, torneo, 2, "B", estado="HERIDO", razas=("R3", "R4")),
        _equipo(session, torneo, 3, "C", estado="CAZADOR_Z", razas=("R5", "R6")),
        _equipo(
            session, torneo, 4, "D", estado="HERIDO", zombie=True, razas=("R7", "R8")
        ),
    ]
    session.commit()

    resultado = generar_ronda_comunidades(
        session, torneo.id, 1, 99, random.Random(4)
    )

    ronda = session.get(ComunidadesRonda, resultado["ronda_id"])
    enfrentamientos = session.query(ComunidadesEnfrentamiento).all()
    fotografias = session.query(ComunidadesFotografiaEstado).all()
    assert ronda.estado == "ABIERTA"
    assert ronda.fecha_inicio == datetime(2026, 7, 1)
    assert ronda.fecha_fin == datetime(2026, 7, 8)
    assert session.get(ComunidadesTorneo, torneo.id).estado == "EN_CURSO"
    assert len(enfrentamientos) == 2
    assert len(fotografias) == 4
    assert all(len(enfrentamiento.fotografias_estado) == 2 for enfrentamiento in enfrentamientos)

    fotografias_iniciales = {
        foto.equipo_id: (foto.estado_temporal, foto.es_zombie, foto.comunidad_id)
        for foto in fotografias
    }
    equipos[0].estado_temporal = "NEUTRO"
    equipos[1].es_zombie = True
    session.commit()
    session.expire_all()
    assert {
        foto.equipo_id: (foto.estado_temporal, foto.es_zombie, foto.comunidad_id)
        for foto in session.query(ComunidadesFotografiaEstado).all()
    } == fotografias_iniciales

    finales = (
        session.query(ComunidadesTrazaEmparejamiento)
        .filter(ComunidadesTrazaEmparejamiento.etapa == "SELECCION_FINAL")
        .all()
    )
    assert len(finales) == 2
    assert all(json.loads(fila.detalle)["fallback_utilizado"] == "BASE" for fila in finales)


def test_bye_se_resuelve_aplica_puntos_limpia_temporal_y_conserva_zombie():
    session = _session()
    torneo = _torneo(session)
    bye = _equipo(session, torneo, 1, "A", zombie=True)
    _equipo(session, torneo, 2, "B", estado="CAZADOR")
    _equipo(session, torneo, 3, "C", estado="HERIDO")
    session.commit()

    resultado = generar_ronda_comunidades(
        session, torneo.id, 1, 99, random.Random(7)
    )

    assert resultado["bye_equipo_id"] == bye.id
    bye_actual = session.get(ComunidadesEquipo, bye.id)
    assert bye_actual.estado_temporal == "NEUTRO"
    assert bye_actual.es_zombie is True
    assert bye_actual.cantidad_byes == 1
    assert bye_actual.puntos_clasificacion == Decimal("1.50")
    transicion = session.query(ComunidadesHistorialTransicion).one()
    assert transicion.motivo == "BYE"
    assert transicion.enfrentamiento_id is None
    assert transicion.es_zombie_anterior is True
    assert transicion.es_zombie_posterior is True
    assert transicion.estado_temporal_posterior == "NEUTRO"
    assert session.query(ComunidadesEnfrentamiento).count() == 1
    assert session.query(ComunidadesFotografiaEstado).count() == 2


def test_fallo_intermedio_revierte_ronda_enfrentamientos_fotos_traza_y_estado():
    session = _session()
    torneo = _torneo(session)
    for equipo_id, comunidad in enumerate(("A", "B", "C", "D"), start=1):
        _equipo(session, torneo, equipo_id, comunidad)
    session.commit()

    def fallar(_):
        raise RuntimeError("fallo simulado")

    with pytest.raises(RuntimeError, match="fallo simulado"):
        generar_ronda_comunidades(
            session,
            torneo.id,
            1,
            99,
            random.Random(3),
            on_enfrentamiento_persistido=fallar,
        )

    assert session.query(ComunidadesRonda).count() == 0
    assert session.query(ComunidadesEnfrentamiento).count() == 0
    assert session.query(ComunidadesFotografiaEstado).count() == 0
    assert session.query(ComunidadesTrazaEmparejamiento).count() == 0
    assert session.get(ComunidadesTorneo, torneo.id).estado == "CREADO"


def test_rechaza_ronda_duplicada_sin_alterar_la_generada():
    session = _session()
    torneo = _torneo(session)
    _equipo(session, torneo, 1, "A")
    _equipo(session, torneo, 2, "B")
    session.commit()
    generar_ronda_comunidades(session, torneo.id, 1, 99, random.Random(1))

    with pytest.raises(ErrorGeneracionRondaComunidades) as error:
        generar_ronda_comunidades(session, torneo.id, 1, 99, random.Random(1))

    assert error.value.codigo == "RONDA_DUPLICADA"
    assert session.query(ComunidadesRonda).count() == 1
    assert session.query(ComunidadesEnfrentamiento).count() == 1
    assert session.query(ComunidadesFotografiaEstado).count() == 2


def test_traza_persistida_identifica_el_fallback_utilizado():
    session = _session()
    torneo = _torneo(session)
    _equipo(session, torneo, 1, "A", razas=("Orcos", "Skaven"))
    _equipo(session, torneo, 2, "B", razas=("Humanos", "Skaven"))
    session.commit()

    resultado = generar_ronda_comunidades(
        session, torneo.id, 1, 99, random.Random(1)
    )

    assert resultado["etapa"] == "PERMITIR_MIRRORS"
    trazas = session.query(ComunidadesTrazaEmparejamiento).order_by(
        ComunidadesTrazaEmparejamiento.secuencia
    ).all()
    assert [traza.etapa for traza in trazas[:2]] == ["BASE", "PERMITIR_MIRRORS"]
    seleccion = trazas[-1]
    assert seleccion.etapa == "SELECCION_FINAL"
    assert json.loads(seleccion.detalle)["fallback_utilizado"] == "PERMITIR_MIRRORS"


def test_valida_numero_y_no_permite_otra_ronda_mientras_hay_una_abierta():
    session = _session()
    torneo = _torneo(session, rondas=2)
    _equipo(session, torneo, 1, "A")
    _equipo(session, torneo, 2, "B")
    session.commit()

    with pytest.raises(ErrorGeneracionRondaComunidades) as numero_error:
        generar_ronda_comunidades(session, torneo.id, 3, 99, random.Random(1))
    assert numero_error.value.codigo == "NUMERO_RONDA_INVALIDO"
    assert session.query(ComunidadesRonda).count() == 0

    generar_ronda_comunidades(session, torneo.id, 1, 99, random.Random(1))
    with pytest.raises(ErrorGeneracionRondaComunidades) as abierta_error:
        generar_ronda_comunidades(session, torneo.id, 2, 99, random.Random(1))
    assert abierta_error.value.codigo == "RONDA_ABIERTA_INCOMPATIBLE"
    assert session.query(ComunidadesRonda).count() == 1
