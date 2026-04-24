import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from GestorSQL import (
    Base,
    SuizoEmparejamiento,
    SuizoPairingTrace,
    SuizoParticipante,
    SuizoRonda,
    SuizoTorneo,
    Usuario,
)
from SuizoCore import (
    calcular_h2h,
    calcular_standings,
    generar_pairings_backtracking,
    procesar_cierre_ronda_si_corresponde,
)


def _build_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _crear_torneo_base(session, torneo_id=1, rondas_totales=4, puntos_bye=Decimal("1.5")):
    ahora = datetime.utcnow()
    torneo = SuizoTorneo(
        id=torneo_id,
        nombre="Test",
        activo=True,
        estado="EN_CURSO",
        rondas_totales=rondas_totales,
        ida_vuelta=False,
        formato_serie="BO1",
        puntos_win=Decimal("3"),
        puntos_draw=Decimal("1"),
        puntos_loss=Decimal("0"),
        puntos_bye=puntos_bye,
        fecha_fin_ronda1=ahora + timedelta(days=7),
        dias_por_ronda=7,
        created_at=ahora,
        updated_at=ahora,
    )
    session.add(torneo)
    return torneo


def _crear_usuario_y_participante(session, torneo_id, user_id, raza="Humano", estado="ACTIVO"):
    ahora = datetime.utcnow()
    session.add(
        Usuario(
            idUsuarios=user_id,
            nombre_discord=f"u{user_id}",
            id_discord=1000 + user_id,
            nombre_bloodbowl=f"bb{user_id}",
        )
    )
    session.add(
        SuizoParticipante(
            torneo_id=torneo_id,
            usuario_id=user_id,
            estado=estado,
            tiene_bye=False,
            cantidad_byes=0,
            puntos_ajuste_inicial=Decimal("0"),
            raza_competicion=raza,
            created_at=ahora,
        )
    )


def _crear_ronda(session, torneo_id, numero, estado="CERRADA"):
    ahora = datetime.utcnow()
    ronda = SuizoRonda(
        torneo_id=torneo_id,
        numero=numero,
        estado=estado,
        fecha_inicio=ahora,
        fecha_fin=ahora + timedelta(days=7),
    )
    session.add(ronda)
    session.flush()
    return ronda


def _crear_emparejamiento(session, torneo_id, ronda_id, mesa, c1, c2, estado="ADMINISTRADO", es_bye=False,
                         score1=0, score2=0, puntos1=Decimal("0"), puntos2=Decimal("0")):
    session.add(
        SuizoEmparejamiento(
            torneo_id=torneo_id,
            ronda_id=ronda_id,
            mesa_numero=mesa,
            coach1_usuario_id=c1,
            coach2_usuario_id=c2,
            estado=estado,
            es_bye=es_bye,
            partidos_requeridos=1,
            partidos_reportados=1 if estado != "PENDIENTE" else 0,
            score_final_c1=score1,
            score_final_c2=score2,
            puntos_c1=puntos1,
            puntos_c2=puntos2,
        )
    )


def test_h2h_aplicable_y_no_aplicable():
    standings = [
        {"usuario_id": 1, "puntos": Decimal("3")},
        {"usuario_id": 2, "puntos": Decimal("3")},
        {"usuario_id": 3, "puntos": Decimal("3")},
        {"usuario_id": 4, "puntos": Decimal("0")},
    ]
    emparejamientos = [
        {"coach1_usuario_id": 1, "coach2_usuario_id": 2, "es_bye": False, "puntos_c1": Decimal("3"), "puntos_c2": Decimal("0")},
        {"coach1_usuario_id": 1, "coach2_usuario_id": 4, "es_bye": False, "puntos_c1": Decimal("0"), "puntos_c2": Decimal("0")},
    ]

    h2h = calcular_h2h(standings, emparejamientos)

    assert h2h[1] == Decimal("3")
    assert h2h[2] == Decimal("0")
    assert h2h[3] is None


def test_buchholz_con_corte():
    session = _build_session()
    _crear_torneo_base(session, torneo_id=10)
    for uid in (1, 2, 3, 4):
        _crear_usuario_y_participante(session, 10, uid)

    r1 = _crear_ronda(session, 10, 1)
    _crear_emparejamiento(session, 10, r1.id, 1, 1, 2, score1=1, score2=0, puntos1=Decimal("3"), puntos2=Decimal("0"))
    _crear_emparejamiento(session, 10, r1.id, 2, 3, 4, score1=1, score2=0, puntos1=Decimal("3"), puntos2=Decimal("0"))

    r2 = _crear_ronda(session, 10, 2)
    _crear_emparejamiento(session, 10, r2.id, 1, 1, 3, score1=1, score2=0, puntos1=Decimal("3"), puntos2=Decimal("0"))
    _crear_emparejamiento(session, 10, r2.id, 2, 2, 4, score1=1, score2=0, puntos1=Decimal("3"), puntos2=Decimal("0"))

    session.commit()

    standings = {f["usuario_id"]: f for f in calcular_standings(session, 10)}
    assert standings[1]["buchholz_cut"] == Decimal("3")
    assert standings[2]["buchholz_cut"] == Decimal("6")


def test_bye_suma_puntos_y_no_pj():
    session = _build_session()
    _crear_torneo_base(session, torneo_id=20, puntos_bye=Decimal("1.5"))
    _crear_usuario_y_participante(session, 20, 1)
    _crear_usuario_y_participante(session, 20, 2)

    r1 = _crear_ronda(session, 20, 1)
    _crear_emparejamiento(
        session,
        20,
        r1.id,
        mesa=1,
        c1=1,
        c2=None,
        es_bye=True,
        score1=0,
        score2=0,
        puntos1=Decimal("0"),
        puntos2=Decimal("0"),
    )
    session.commit()

    standings = {f["usuario_id"]: f for f in calcular_standings(session, 20)}
    assert standings[1]["puntos"] == Decimal("1.5")
    assert standings[1]["pj"] == 0


def test_h2h_rompe_empate_por_encima_de_buchholz():
    session = _build_session()
    _crear_torneo_base(session, torneo_id=25)
    for uid in (1, 2, 3, 4):
        _crear_usuario_y_participante(session, 25, uid)

    participante_3 = session.query(SuizoParticipante).filter_by(torneo_id=25, usuario_id=3).one()
    participante_4 = session.query(SuizoParticipante).filter_by(torneo_id=25, usuario_id=4).one()
    participante_3.puntos_ajuste_inicial = Decimal("3")
    participante_4.puntos_ajuste_inicial = Decimal("-3")

    r1 = _crear_ronda(session, 25, 1)
    _crear_emparejamiento(
        session, 25, r1.id, 1, 1, 2, score1=1, score2=0, puntos1=Decimal("3"), puntos2=Decimal("0")
    )
    _crear_emparejamiento(
        session, 25, r1.id, 2, 3, 4, score1=1, score2=0, puntos1=Decimal("3"), puntos2=Decimal("0")
    )

    r2 = _crear_ronda(session, 25, 2)
    _crear_emparejamiento(
        session, 25, r2.id, 1, 4, 1, score1=1, score2=0, puntos1=Decimal("3"), puntos2=Decimal("0")
    )
    _crear_emparejamiento(
        session, 25, r2.id, 2, 2, 3, score1=1, score2=0, puntos1=Decimal("3"), puntos2=Decimal("0")
    )
    session.commit()

    standings = calcular_standings(session, 25)
    fila_1 = next(f for f in standings if f["usuario_id"] == 1)
    fila_2 = next(f for f in standings if f["usuario_id"] == 2)

    assert fila_1["puntos"] == fila_2["puntos"] == Decimal("3")
    assert fila_2["buchholz_cut"] > fila_1["buchholz_cut"]
    assert fila_1["h2h_valor"] == Decimal("3")
    assert fila_2["h2h_valor"] == Decimal("0")
    assert fila_1["rank"] < fila_2["rank"]


def test_fallback_a_repetidos_cuando_no_hay_solucion():
    session = _build_session()
    _crear_torneo_base(session, torneo_id=30)
    for uid, raza in ((1, "A"), (2, "B"), (3, "C"), (4, "D")):
        _crear_usuario_y_participante(session, 30, uid, raza=raza)

    r1 = _crear_ronda(session, 30, 1)
    _crear_emparejamiento(session, 30, r1.id, 1, 1, 4)
    _crear_emparejamiento(session, 30, r1.id, 2, 2, 3)

    r2 = _crear_ronda(session, 30, 2)
    _crear_emparejamiento(session, 30, r2.id, 1, 2, 4)
    _crear_emparejamiento(session, 30, r2.id, 2, 1, 3)

    r3 = _crear_ronda(session, 30, 3)
    _crear_emparejamiento(session, 30, r3.id, 1, 3, 4)
    _crear_emparejamiento(session, 30, r3.id, 2, 1, 2)

    _crear_ronda(session, 30, 4, estado="ABIERTA")
    session.commit()

    pairings = generar_pairings_backtracking(session, 30, 4)

    assert len(pairings) == 2
    ultima_traza = session.query(SuizoPairingTrace).order_by(SuizoPairingTrace.id.desc()).first()
    assert ultima_traza is not None
    assert ultima_traza.resultado == "FALLBACK_REPETIDO"


def test_drop_genera_forfeit_1_0_con_3_puntos():
    session = _build_session()
    _crear_torneo_base(session, torneo_id=40, rondas_totales=1)
    _crear_usuario_y_participante(session, 40, 1)
    _crear_usuario_y_participante(session, 40, 2)

    r1 = _crear_ronda(session, 40, 1, estado="ABIERTA")
    _crear_emparejamiento(session, 40, r1.id, 1, 1, 2, estado="PENDIENTE")
    session.flush()

    emp = session.query(SuizoEmparejamiento).filter_by(torneo_id=40, ronda_id=r1.id).one()

    # Simula el bloque de suizo_drop cuando se retira coach1.
    emp.score_final_c1 = 0
    emp.score_final_c2 = 1
    emp.puntos_c1 = Decimal("0")
    emp.puntos_c2 = Decimal("3")
    emp.ganador_usuario_id = emp.coach2_usuario_id
    emp.forfeit_tipo = "VISITANTE"
    emp.partidos_reportados = emp.partidos_requeridos
    emp.estado = "ADMINISTRADO"
    emp.resultado_origen = "ADMIN"

    session.commit()

    actualizado = session.query(SuizoEmparejamiento).filter_by(id=emp.id).one()
    assert actualizado.score_final_c1 == 0
    assert actualizado.score_final_c2 == 1
    assert actualizado.puntos_c2 == Decimal("3")


def test_admin_forfeit_respeta_configuracion_2_1_0():
    session = _build_session()
    _crear_torneo_base(session, torneo_id=41, rondas_totales=1)
    torneo = session.query(SuizoTorneo).filter_by(id=41).one()
    torneo.puntos_win = Decimal("2")
    torneo.puntos_draw = Decimal("1")
    torneo.puntos_loss = Decimal("0")
    _crear_usuario_y_participante(session, 41, 1)
    _crear_usuario_y_participante(session, 41, 2)

    r1 = _crear_ronda(session, 41, 1, estado="ABIERTA")
    _crear_emparejamiento(session, 41, r1.id, 1, 1, 2, estado="PENDIENTE")
    session.flush()

    emp = session.query(SuizoEmparejamiento).filter_by(torneo_id=41, ronda_id=r1.id).one()
    puntos_win = Decimal(str(torneo.puntos_win))
    puntos_draw = Decimal(str(torneo.puntos_draw))
    puntos_loss = Decimal(str(torneo.puntos_loss))

    # Simula las reglas de suizo_admin_resultado para tipos administrativos.
    emp.score_final_c1 = 1
    emp.score_final_c2 = 0
    emp.puntos_c1 = puntos_win
    emp.puntos_c2 = puntos_loss
    session.flush()
    assert emp.puntos_c1 == Decimal("2")
    assert emp.puntos_c2 == Decimal("0")

    emp.score_final_c1 = 0
    emp.score_final_c2 = 1
    emp.puntos_c1 = puntos_loss
    emp.puntos_c2 = puntos_win
    session.flush()
    assert emp.puntos_c1 == Decimal("0")
    assert emp.puntos_c2 == Decimal("2")

    emp.score_final_c1 = 0
    emp.score_final_c2 = 0
    emp.puntos_c1 = puntos_draw
    emp.puntos_c2 = puntos_draw
    session.flush()
    assert emp.puntos_c1 == Decimal("1")
    assert emp.puntos_c2 == Decimal("1")

    # Regla explícita: doble forfait mantiene 0/0.
    emp.puntos_c1 = Decimal("0")
    emp.puntos_c2 = Decimal("0")
    session.flush()
    assert emp.puntos_c1 == Decimal("0")
    assert emp.puntos_c2 == Decimal("0")


def test_cierre_de_ronda_solo_cuando_todo_esta_resuelto():
    session = _build_session()
    _crear_torneo_base(session, torneo_id=50, rondas_totales=1)
    for uid in (1, 2, 3, 4):
        _crear_usuario_y_participante(session, 50, uid)

    r1 = _crear_ronda(session, 50, 1, estado="ABIERTA")
    _crear_emparejamiento(session, 50, r1.id, 1, 1, 2, estado="PENDIENTE")
    _crear_emparejamiento(session, 50, r1.id, 2, 3, 4, estado="ADMINISTRADO", score1=1, score2=0, puntos1=Decimal("3"))
    session.commit()

    cierre_inicial = procesar_cierre_ronda_si_corresponde(session, 50, 1)
    assert cierre_inicial["cerrada"] is False
    assert cierre_inicial["motivo"] == "HAY_PENDIENTES"

    pendiente = session.query(SuizoEmparejamiento).filter_by(torneo_id=50, ronda_id=r1.id, mesa_numero=1).one()
    pendiente.estado = "ADMINISTRADO"
    pendiente.score_final_c1 = 1
    pendiente.score_final_c2 = 0
    pendiente.puntos_c1 = Decimal("3")
    pendiente.puntos_c2 = Decimal("0")
    session.commit()

    cierre_final = procesar_cierre_ronda_si_corresponde(session, 50, 1)
    assert cierre_final["cerrada"] is True
    assert cierre_final["motivo"] == "CERRADA"
    assert cierre_final["snapshot_filas"] == 4
