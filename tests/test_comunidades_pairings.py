from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
import random
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

sys.path.append(str(Path(__file__).resolve().parents[1]))

from ComunidadesCore import generar_pairings_comunidades_backtracking
from GestorSQL import (
    Base,
    ComunidadesComunidad,
    ComunidadesEnfrentamiento,
    ComunidadesEquipo,
    ComunidadesMiembro,
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
    Base.metadata.create_all(engine)
    return Session(engine)


def _torneo(session):
    torneo = ComunidadesTorneo(
        nombre="Comunidades",
        rondas_totales=6,
        fecha_fin_ronda1=datetime(2026, 7, 8),
        dias_por_ronda=7,
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
    comunidad,
    estado="NEUTRO",
    zombie=False,
    razas=("Humanos", "Orcos"),
    byes=0,
):
    comunidad_orm = (
        session.query(ComunidadesComunidad)
        .filter_by(torneo_id=torneo.id, nombre=comunidad)
        .one_or_none()
    )
    if comunidad_orm is None:
        comunidad_orm = ComunidadesComunidad(torneo=torneo, nombre=comunidad)
        session.add(comunidad_orm)
        session.flush()
    equipo = ComunidadesEquipo(
        id=equipo_id,
        torneo=torneo,
        comunidad=comunidad_orm,
        nombre=f"Equipo {equipo_id}",
        estado_temporal=estado,
        es_zombie=zombie,
        cantidad_byes=byes,
    )
    for posicion, raza in enumerate(razas, start=1):
        usuario_id = equipo_id * 10 + posicion
        usuario = Usuario(idUsuarios=usuario_id, nombre_discord=f"U{usuario_id}")
        session.add(usuario)
        equipo.miembros.append(
            ComunidadesMiembro(
                torneo_id=torneo.id,
                usuario=usuario,
                posicion=posicion,
                raza=raza,
            )
        )
    session.add(equipo)
    session.flush()
    return equipo


def _ronda(session, torneo, numero):
    inicio = datetime(2026, 7, 1) + timedelta(days=7 * (numero - 1))
    ronda = ComunidadesRonda(
        torneo=torneo,
        numero=numero,
        fecha_inicio=inicio,
        fecha_fin=inicio + timedelta(days=7),
        generada_por_discord_id=1,
    )
    session.add(ronda)
    session.flush()
    return ronda


def _enfrentamiento_previo(session, torneo, ronda, a, b, puntos_a=3, puntos_b=0):
    session.add(
        ComunidadesEnfrentamiento(
            torneo=torneo,
            ronda=ronda,
            mesa_numero=len(ronda.enfrentamientos) + 1,
            equipo_a=a,
            equipo_b=b,
            estado="CERRADO",
            ganador_equipo_id=a.id if puntos_a > puntos_b else None,
            puntos_clasificacion_a=Decimal(str(puntos_a)),
            puntos_clasificacion_b=Decimal(str(puntos_b)),
        )
    )
    session.flush()


def _parejas(pairings):
    return {
        frozenset((p["equipo_a_id"], p["equipo_b_id"]))
        for p in pairings
        if not p["es_bye"]
    }


def test_solucion_estricta_prioriza_ambos_tipos_de_caza_y_comunidades_distintas():
    session = _session()
    torneo = _torneo(session)
    _equipo(session, torneo, 1, "A", "CAZADOR", razas=("R1", "X1"))
    _equipo(session, torneo, 2, "B", "HERIDO", zombie=False, razas=("R2", "X2"))
    _equipo(session, torneo, 3, "C", "CAZADOR_Z", razas=("R3", "X3"))
    _equipo(session, torneo, 4, "D", "HERIDO", zombie=True, razas=("R4", "X4"))

    pairings, traza = generar_pairings_comunidades_backtracking(
        session, torneo.id, 1, random.Random(4)
    )

    assert _parejas(pairings) == {frozenset((1, 2)), frozenset((3, 4))}
    assert all(p["prioridad_estado"] == 0 for p in pairings)
    assert traza["etapa"] == "BASE"


def test_mirror_es_el_primer_fallback_y_detecta_cualquier_raza_compartida():
    session = _session()
    torneo = _torneo(session)
    _equipo(session, torneo, 1, "A", razas=("Orcos", "Skaven"))
    _equipo(session, torneo, 2, "B", razas=("Humanos", "Skaven"))

    pairings, traza = generar_pairings_comunidades_backtracking(
        session, torneo.id, 1, random.Random(1)
    )

    assert pairings[0]["es_mirror"] is True
    assert traza["etapa"] == "PERMITIR_MIRRORS"
    assert traza["nivel_fallback"] == 1


def test_estados_no_deseados_solo_se_permiten_despues_de_mirrors():
    session = _session()
    torneo = _torneo(session)
    _equipo(session, torneo, 1, "A", estado="CAZADOR", razas=("Orcos", "Skaven"))
    _equipo(session, torneo, 2, "B", estado="NEUTRO", razas=("Humanos", "Enanos"))

    pairings, traza = generar_pairings_comunidades_backtracking(
        session, torneo.id, 1, random.Random(2)
    )

    assert pairings[0]["prioridad_estado"] == 2
    assert traza["etapa"] == "PERMITIR_ESTADOS_NO_DESEADOS"
    assert [i["etapa"] for i in traza["intentos"]] == [
        "BASE",
        "PERMITIR_MIRRORS",
        "PERMITIR_ESTADOS_NO_DESEADOS",
    ]


def test_rival_repetido_solo_se_permite_en_ultimo_fallback():
    session = _session()
    torneo = _torneo(session)
    a = _equipo(session, torneo, 1, "A", razas=("Orcos", "Skaven"))
    b = _equipo(session, torneo, 2, "B", razas=("Humanos", "Enanos"))
    ronda = _ronda(session, torneo, 1)
    _enfrentamiento_previo(session, torneo, ronda, a, b)

    pairings, traza = generar_pairings_comunidades_backtracking(
        session, torneo.id, 2, random.Random(3)
    )

    assert pairings[0]["es_rival_repetido"] is True
    assert traza["etapa"] == "PERMITIR_REPETIDOS"
    assert traza["nivel_fallback"] == 3


def test_distribucion_imposible_no_persiste_ni_devuelve_ronda_parcial():
    session = _session()
    torneo = _torneo(session)
    _equipo(session, torneo, 1, "A")
    _equipo(session, torneo, 2, "A")
    _equipo(session, torneo, 3, "A")
    _equipo(session, torneo, 4, "B")
    antes = len(session.new)

    pairings, traza = generar_pairings_comunidades_backtracking(
        session, torneo.id, 1, random.Random(4)
    )

    assert pairings == []
    assert traza["etapa"] == "CANCELACION"
    assert traza["error"]["codigo"] == "SIN_SOLUCION_COMPLETA"
    assert len(session.new) == antes
    assert session.query(ComunidadesEnfrentamiento).count() == 0


def test_bye_prioriza_neutro_sin_bye_previo_y_peor_clasificado(monkeypatch):
    session = _session()
    torneo = _torneo(session)
    _equipo(session, torneo, 1, "A", estado="HERIDO")
    _equipo(session, torneo, 2, "B", byes=0)
    _equipo(session, torneo, 3, "C", byes=1)
    _equipo(session, torneo, 4, "D", byes=0)
    _equipo(session, torneo, 5, "E", byes=0)

    import ComunidadesCore

    posiciones = {1: 5, 2: 1, 3: 5, 4: 4, 5: 2}
    original = ComunidadesCore.calcular_clasificacion_equipos

    def clasificacion(*args, **kwargs):
        filas = original(*args, **kwargs)
        for fila in filas:
            fila["posicion"] = posiciones[fila["equipo_id"]]
            fila["cantidad_byes"] = 1 if fila["equipo_id"] == 3 else 0
        return filas

    monkeypatch.setattr(ComunidadesCore, "calcular_clasificacion_equipos", clasificacion)
    pairings, _ = generar_pairings_comunidades_backtracking(
        session, torneo.id, 1, random.Random(5)
    )

    bye = next(p for p in pairings if p["es_bye"])
    assert bye["equipo_a_id"] == 4


def test_azar_inyectado_hace_la_salida_determinista():
    def generar(seed):
        session = _session()
        torneo = _torneo(session)
        for equipo_id, comunidad in enumerate(("A", "B", "C", "D", "E", "F"), start=1):
            _equipo(session, torneo, equipo_id, comunidad, razas=(f"R{equipo_id}", f"X{equipo_id}"))
        return generar_pairings_comunidades_backtracking(
            session, torneo.id, 1, random.Random(seed)
        )[0]

    assert generar(99) == generar(99)


def test_dentro_de_la_prioridad_minimiza_diferencia_de_puntos(monkeypatch):
    session = _session()
    torneo = _torneo(session)
    _equipo(session, torneo, 1, "A", estado="CAZADOR", razas=("R1", "X1"))
    _equipo(session, torneo, 2, "B", estado="CAZADOR", razas=("R2", "X2"))
    _equipo(session, torneo, 3, "C", estado="HERIDO", razas=("R3", "X3"))
    _equipo(session, torneo, 4, "D", estado="HERIDO", razas=("R4", "X4"))

    import ComunidadesCore

    puntos = {1: Decimal("10"), 2: Decimal("2"), 3: Decimal("9"), 4: Decimal("1")}
    original = ComunidadesCore.calcular_clasificacion_equipos

    def clasificacion(*args, **kwargs):
        filas = original(*args, **kwargs)
        for fila in filas:
            fila["puntos"] = puntos[fila["equipo_id"]]
        return filas

    monkeypatch.setattr(ComunidadesCore, "calcular_clasificacion_equipos", clasificacion)
    pairings, traza = generar_pairings_comunidades_backtracking(
        session, torneo.id, 1, random.Random(7)
    )

    assert _parejas(pairings) == {frozenset((1, 3)), frozenset((2, 4))}
    assert traza["etapa"] == "BASE"
