from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

sys.path.append(str(Path(__file__).resolve().parents[1]))

from ComunidadesCore import (
    calcular_clasificacion_comunidades,
    calcular_clasificacion_equipos,
    calcular_h2h_equipos,
    ordenar_clasificacion_equipos,
)
from GestorSQL import (
    Base,
    ComunidadesComunidad,
    ComunidadesEnfrentamiento,
    ComunidadesEquipo,
    ComunidadesHistorialTransicion,
    ComunidadesRonda,
    ComunidadesTorneo,
)


def _session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return Session(engine)


def _crear_torneo(session, torneo_id=1, puntos_bye="1.5"):
    torneo = ComunidadesTorneo(
        id=torneo_id,
        nombre=f"Torneo {torneo_id}",
        rondas_totales=5,
        fecha_fin_ronda1=datetime(2026, 7, 8),
        dias_por_ronda=7,
        puntos_clasificacion_bye=Decimal(puntos_bye),
        plantilla_mensaje_ronda1="Ronda 1",
        plantilla_mensaje_rondas_siguientes="Ronda {ronda}",
        creado_por_discord_id=1,
    )
    session.add(torneo)
    return torneo


def _crear_comunidad(session, torneo, nombre):
    comunidad = ComunidadesComunidad(torneo=torneo, nombre=nombre)
    session.add(comunidad)
    session.flush()
    return comunidad


def _crear_equipo(session, torneo, comunidad, equipo_id, nombre=None):
    equipo = ComunidadesEquipo(
        id=equipo_id,
        torneo=torneo,
        comunidad=comunidad,
        nombre=nombre or f"Equipo {equipo_id}",
    )
    session.add(equipo)
    session.flush()
    return equipo


def _crear_ronda(session, torneo, numero):
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


def _enfrentamiento(
    session,
    torneo,
    ronda,
    mesa,
    equipo_a,
    equipo_b,
    puntos_a,
    puntos_b,
    td_a=0,
    td_b=0,
    estado="CERRADO",
    origen="API",
):
    if Decimal(str(puntos_a)) > Decimal(str(puntos_b)):
        ganador_id = equipo_a.id
    elif Decimal(str(puntos_b)) > Decimal(str(puntos_a)):
        ganador_id = equipo_b.id
    else:
        ganador_id = None
    enfrentamiento = ComunidadesEnfrentamiento(
        torneo=torneo,
        ronda=ronda,
        mesa_numero=mesa,
        equipo_a=equipo_a,
        equipo_b=equipo_b,
        estado=estado,
        puntos_clasificacion_a=Decimal(str(puntos_a)),
        puntos_clasificacion_b=Decimal(str(puntos_b)),
        td_favor_a=td_a,
        td_contra_a=td_b,
        td_favor_b=td_b,
        td_contra_b=td_a,
        ganador_equipo_id=ganador_id,
        resultado_origen=origen,
    )
    session.add(enfrentamiento)
    session.flush()
    return enfrentamiento


def _transicion(
    session,
    torneo,
    ronda,
    equipo,
    motivo,
    puntos_comunitarios="0",
    kills=0,
):
    session.add(
        ComunidadesHistorialTransicion(
            torneo_id=torneo.id,
            ronda_id=ronda.id,
            equipo_id=equipo.id,
            estado_temporal_anterior="NEUTRO",
            es_zombie_anterior=False,
            estado_temporal_posterior="NEUTRO",
            es_zombie_posterior=False,
            motivo=motivo,
            puntos_comunitarios_generados=Decimal(puntos_comunitarios),
            kills_generadas=kills,
        )
    )


def test_h2h_solo_es_aplicable_si_hay_enfrentamiento_directo_en_el_empate():
    clasificacion = [
        {"equipo_id": 1, "puntos": Decimal("3")},
        {"equipo_id": 2, "puntos": Decimal("3")},
        {"equipo_id": 3, "puntos": Decimal("3")},
        {"equipo_id": 4, "puntos": Decimal("0")},
    ]
    enfrentamientos = [
        {
            "equipo_a_id": 1,
            "equipo_b_id": 2,
            "puntos_clasificacion_a": Decimal("3"),
            "puntos_clasificacion_b": Decimal("0"),
        },
        {
            "equipo_a_id": 1,
            "equipo_b_id": 4,
            "puntos_clasificacion_a": Decimal("0"),
            "puntos_clasificacion_b": Decimal("0"),
        },
    ]

    assert calcular_h2h_equipos(clasificacion, enfrentamientos) == {
        1: Decimal("3"),
        2: Decimal("0"),
        3: None,
        4: None,
    }


def test_orden_publicado_respeta_puntos_buchholz_h2h_td_e_id():
    base = {
        "puntos": Decimal("6"),
        "buchholz_cut": Decimal("9"),
        "h2h_valor": Decimal("1"),
        "diferencia_td": 2,
    }
    filas = [
        {**base, "equipo_id": 6, "puntos": Decimal("7")},
        {**base, "equipo_id": 5, "buchholz_cut": Decimal("10")},
        {**base, "equipo_id": 4, "h2h_valor": Decimal("3")},
        {**base, "equipo_id": 3, "diferencia_td": 3},
        {**base, "equipo_id": 2},
        {**base, "equipo_id": 1},
    ]

    ordenada = ordenar_clasificacion_equipos(filas)

    assert [fila["equipo_id"] for fila in ordenada] == [6, 5, 4, 3, 1, 2]
    assert [fila["posicion"] for fila in ordenada] == [1, 2, 3, 4, 5, 6]


def test_calcula_estadisticas_buchholz_cut_y_resultados_administrativos():
    session = _session()
    torneo = _crear_torneo(session)
    comunidades = [_crear_comunidad(session, torneo, f"C{i}") for i in range(4)]
    equipos = [
        _crear_equipo(session, torneo, comunidades[i], i + 1) for i in range(4)
    ]
    r1 = _crear_ronda(session, torneo, 1)
    _enfrentamiento(session, torneo, r1, 1, equipos[0], equipos[1], 3, 0, 3, 1)
    _enfrentamiento(session, torneo, r1, 2, equipos[2], equipos[3], 3, 0, 2, 0)
    r2 = _crear_ronda(session, torneo, 2)
    _enfrentamiento(
        session, torneo, r2, 1, equipos[0], equipos[2], 3, 0, 1, 0, origen="ADMIN"
    )
    _enfrentamiento(session, torneo, r2, 2, equipos[1], equipos[3], 3, 0, 2, 2)
    session.commit()

    filas = {fila["equipo_id"]: fila for fila in calcular_clasificacion_equipos(session, torneo.id)}

    assert (filas[1]["pj"], filas[1]["pg"], filas[1]["pe"], filas[1]["pp"]) == (2, 2, 0, 0)
    assert (filas[1]["td_favor"], filas[1]["td_contra"], filas[1]["diferencia_td"]) == (4, 1, 3)
    assert filas[1]["puntos"] == Decimal("6")
    assert filas[1]["buchholz_cut"] == Decimal("3")
    assert filas[2]["buchholz_cut"] == Decimal("6")


def test_bye_suma_puntos_y_buchholz_del_rival_pero_no_partido_ni_h2h():
    session = _session()
    torneo = _crear_torneo(session, puntos_bye="1.5")
    comunidades = [_crear_comunidad(session, torneo, f"C{i}") for i in range(3)]
    equipos = [
        _crear_equipo(session, torneo, comunidades[i], i + 1) for i in range(3)
    ]
    r1 = _crear_ronda(session, torneo, 1)
    _enfrentamiento(session, torneo, r1, 1, equipos[0], equipos[1], 3, 0, 1, 0)
    _transicion(session, torneo, r1, equipos[2], "BYE")
    r2 = _crear_ronda(session, torneo, 2)
    _enfrentamiento(session, torneo, r2, 1, equipos[0], equipos[2], 3, 0, 1, 0)
    _transicion(session, torneo, r2, equipos[1], "BYE")
    session.commit()

    filas = {fila["equipo_id"]: fila for fila in calcular_clasificacion_equipos(session, torneo.id)}

    assert filas[2]["puntos"] == Decimal("1.5")
    assert (filas[2]["pj"], filas[2]["pg"], filas[2]["pe"], filas[2]["pp"]) == (1, 0, 0, 1)
    assert filas[2]["cantidad_byes"] == 1
    assert (filas[2]["td_favor"], filas[2]["td_contra"]) == (0, 1)
    assert filas[1]["buchholz_cut"] == Decimal("1.5")
    assert filas[2]["h2h_valor"] is None


def test_h2h_multiple_suma_solo_partidos_del_grupo_empatado():
    clasificacion = [
        {"equipo_id": 1, "puntos": Decimal("6")},
        {"equipo_id": 2, "puntos": Decimal("6")},
        {"equipo_id": 3, "puntos": Decimal("6")},
    ]
    enfrentamientos = [
        {
            "equipo_a_id": 1,
            "equipo_b_id": 2,
            "puntos_clasificacion_a": 3,
            "puntos_clasificacion_b": 0,
        },
        {
            "equipo_a_id": 2,
            "equipo_b_id": 3,
            "puntos_clasificacion_a": 1,
            "puntos_clasificacion_b": 1,
        },
        {
            "equipo_a_id": 1,
            "equipo_b_id": 9,
            "puntos_clasificacion_a": 3,
            "puntos_clasificacion_b": 0,
        },
    ]

    assert calcular_h2h_equipos(clasificacion, enfrentamientos) == {
        1: Decimal("3"),
        2: Decimal("1"),
        3: Decimal("1"),
    }


def test_clasificacion_hasta_ronda_excluye_resultados_y_byes_posteriores():
    session = _session()
    torneo = _crear_torneo(session)
    comunidades = [_crear_comunidad(session, torneo, f"C{i}") for i in range(3)]
    equipos = [_crear_equipo(session, torneo, comunidades[i], i + 1) for i in range(3)]
    r1 = _crear_ronda(session, torneo, 1)
    _enfrentamiento(session, torneo, r1, 1, equipos[0], equipos[1], 3, 0, 2, 0)
    _transicion(session, torneo, r1, equipos[2], "BYE")
    r2 = _crear_ronda(session, torneo, 2)
    _enfrentamiento(session, torneo, r2, 1, equipos[1], equipos[2], 3, 0, 1, 0)
    _transicion(session, torneo, r2, equipos[0], "BYE")
    session.commit()

    filas = {
        fila["equipo_id"]: fila
        for fila in calcular_clasificacion_equipos(
            session, torneo.id, hasta_ronda=1
        )
    }

    assert filas[1]["puntos"] == Decimal("3")
    assert filas[1]["cantidad_byes"] == 0
    assert filas[2]["pj"] == 1
    assert filas[3]["puntos"] == Decimal("1.5")
    assert filas[3]["pj"] == 0


def test_comunidades_ordenan_por_efectos_y_puntos_y_comparten_posicion():
    session = _session()
    torneo = _crear_torneo(session)
    comunidades = [_crear_comunidad(session, torneo, nombre) for nombre in ("A", "B", "C", "D")]
    equipos = [_crear_equipo(session, torneo, comunidades[i], i + 1) for i in range(4)]
    r1 = _crear_ronda(session, torneo, 1)
    _enfrentamiento(session, torneo, r1, 1, equipos[0], equipos[2], 3, 0, 1, 0)
    _enfrentamiento(session, torneo, r1, 2, equipos[1], equipos[3], 3, 0, 1, 0, origen="ADMIN")
    _transicion(session, torneo, r1, equipos[0], "ZOMBIFICACION", "1", 0)
    _transicion(session, torneo, r1, equipos[1], "ZOMBIFICACION", "1", 0)
    r2 = _crear_ronda(session, torneo, 2)
    _transicion(session, torneo, r2, equipos[2], "KILL", "0", 1)
    _transicion(session, torneo, r2, equipos[0], "BYE")
    r3 = _crear_ronda(session, torneo, 3)
    _transicion(session, torneo, r3, equipos[1], "BYE")
    session.commit()

    ronda_1 = calcular_clasificacion_comunidades(session, torneo.id, hasta_ronda=1)
    completa = calcular_clasificacion_comunidades(session, torneo.id)

    assert [(fila["nombre"], fila["posicion"]) for fila in ronda_1] == [
        ("A", 1),
        ("B", 1),
        ("C", 3),
        ("D", 3),
    ]
    assert ronda_1[0]["suma_puntos_equipos"] == Decimal("3")
    assert [(fila["nombre"], fila["posicion"]) for fila in completa] == [
        ("A", 1),
        ("B", 1),
        ("C", 3),
        ("D", 4),
    ]
    assert completa[0]["suma_puntos_equipos"] == Decimal("4.5")
    assert completa[1]["suma_puntos_equipos"] == Decimal("4.5")
    assert completa[2]["zombies_matados"] == 1
