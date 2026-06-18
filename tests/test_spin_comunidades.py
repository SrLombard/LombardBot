from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from GestorSQL import (
    Base,
    ComunidadesComunidad,
    ComunidadesEnfrentamiento,
    ComunidadesEquipo,
    ComunidadesPartido,
    ComunidadesRonda,
    ComunidadesTorneo,
    Usuario,
)
from SpinConstantes import AMBITO_SPIN_COMUNIDADES
from UtilesDiscord import resolver_partido_spin_comunidades


def _session():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _activar_foreign_keys(dbapi_connection, _):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    return Session(engine), engine


def _crear_contexto(session: Session):
    ahora = datetime(2026, 7, 1, 20, 0)
    usuarios = [
        Usuario(idUsuarios=11, id_discord=101, nombre_discord="Local"),
        Usuario(idUsuarios=12, id_discord=102, nombre_discord="Local 2"),
        Usuario(idUsuarios=21, id_discord=201, nombre_discord="Visitante"),
        Usuario(idUsuarios=22, id_discord=202, nombre_discord="Visitante 2"),
    ]
    torneo = ComunidadesTorneo(
        nombre="Copa Spin",
        rondas_totales=3,
        fecha_fin_ronda1=ahora + timedelta(days=7),
        plantilla_mensaje_ronda1="Ronda 1",
        plantilla_mensaje_rondas_siguientes="Ronda {ronda}",
        creado_por_discord_id=999,
    )
    comunidad_a = ComunidadesComunidad(nombre="Comunidad A")
    comunidad_b = ComunidadesComunidad(nombre="Comunidad B")
    equipo_a = ComunidadesEquipo(nombre="Equipo A")
    equipo_b = ComunidadesEquipo(nombre="Equipo B")
    comunidad_a.equipos.append(equipo_a)
    comunidad_b.equipos.append(equipo_b)
    torneo.comunidades.extend([comunidad_a, comunidad_b])
    torneo.equipos.extend([equipo_a, equipo_b])
    ronda = ComunidadesRonda(
        numero=1,
        fecha_inicio=ahora,
        fecha_fin=ahora + timedelta(days=7),
        generada_por_discord_id=999,
    )
    torneo.rondas.append(ronda)
    session.add_all([*usuarios, torneo])
    session.flush()
    enfrentamiento = ComunidadesEnfrentamiento(
        torneo_id=torneo.id,
        ronda=ronda,
        mesa_numero=1,
        equipo_a=equipo_a,
        equipo_b=equipo_b,
    )
    session.add(enfrentamiento)
    session.flush()
    return usuarios, torneo, enfrentamiento, equipo_a, equipo_b, ahora


def _partido(torneo, enfrentamiento, equipo_a, equipo_b, local, visitante, *, indice, canal, fecha, estado="PENDIENTE", partido_bloodbowl_id=None):
    return ComunidadesPartido(
        torneo_id=torneo.id,
        enfrentamiento=enfrentamiento,
        indice=indice,
        equipo_local=equipo_a,
        equipo_visitante=equipo_b,
        usuario_local=local,
        usuario_visitante=visitante,
        atacante_usuario=local,
        defensor_usuario=visitante,
        canal_discord_id=canal,
        fecha=fecha,
        estado=estado,
        partido_bloodbowl_id=partido_bloodbowl_id,
    )


def test_resolver_partido_spin_comunidades_devuelve_spin_match_result_con_datos_necesarios():
    session, engine = _session()
    try:
        usuarios, torneo, enfrentamiento, equipo_a, equipo_b, ahora = _crear_contexto(session)
        lejano = _partido(torneo, enfrentamiento, equipo_a, equipo_b, usuarios[0], usuarios[2], indice=1, canal=901, fecha=ahora + timedelta(days=4))
        cercano = _partido(torneo, enfrentamiento, equipo_a, equipo_b, usuarios[1], usuarios[0], indice=2, canal=902, fecha=ahora + timedelta(days=1), estado="EN_CURSO")
        session.add_all([lejano, cercano])
        session.commit()

        resultado = resolver_partido_spin_comunidades(session, usuarios[0])

        assert resultado.ambito == AMBITO_SPIN_COMUNIDADES
        assert resultado.partido_id == cercano.id
        assert resultado.canal_partido_id == 902
        assert resultado.jugador1_discord_id == 102
        assert resultado.jugador2_discord_id == 101
        assert resultado.indice_partido == 2
        assert resultado.enfrentamiento_id == enfrentamiento.id
        assert resultado.torneo_id == torneo.id
        assert resultado.equipo_a_nombre == "Equipo A"
        assert resultado.equipo_b_nombre == "Equipo B"
        assert "partido individual 2" in resultado.descripcion_corta
        assert "Equipo A vs Equipo B" in resultado.descripcion_corta
    finally:
        session.close()
        engine.dispose()


def test_resolver_partido_spin_comunidades_filtra_no_elegibles():
    session, engine = _session()
    try:
        usuarios, torneo, enfrentamiento, equipo_a, equipo_b, ahora = _crear_contexto(session)
        session.add_all([
            _partido(torneo, enfrentamiento, equipo_a, equipo_b, usuarios[0], usuarios[2], indice=1, canal=None, fecha=ahora),
            _partido(torneo, enfrentamiento, equipo_a, equipo_b, usuarios[1], usuarios[3], indice=2, canal=902, fecha=ahora),
        ])
        session.commit()

        assert resolver_partido_spin_comunidades(session, usuarios[0]) is None
    finally:
        session.close()
        engine.dispose()
