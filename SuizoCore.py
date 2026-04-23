"""Lógica base de standings para torneos suizos."""

from decimal import Decimal
from typing import Any, Dict, List, Optional

from GestorSQL import SuizoEmparejamiento, SuizoParticipante, SuizoRonda, SuizoTorneo
from SuizoConstantes import EMP_ADMINISTRADO, EMP_CERRADO


EstadoFila = Dict[str, Any]


def _decimal(valor: Any) -> Decimal:
    if isinstance(valor, Decimal):
        return valor
    return Decimal(str(valor or 0))


def calcular_standings(session, torneo_id, hasta_ronda: Optional[int] = None) -> List[EstadoFila]:
    """Calcula el standing acumulado de un torneo suizo.

    Reglas aplicadas:
    - Solo cuentan emparejamientos en estado ADMINISTRADO o CERRADO.
    - Si hasta_ronda se informa, solo se consideran rondas <= hasta_ronda.
    - En BYE se suman puntos_bye del torneo pero no incrementa PJ.
    - En forfeit/local/visitante se usan score_final_c1/score_final_c2 guardados.
    """
    torneo = session.query(SuizoTorneo).filter(SuizoTorneo.id == torneo_id).one_or_none()
    if torneo is None:
        return []

    participantes = (
        session.query(SuizoParticipante)
        .filter(SuizoParticipante.torneo_id == torneo_id)
        .all()
    )

    filas: Dict[int, EstadoFila] = {}
    for p in participantes:
        filas[p.usuario_id] = {
            "usuario_id": p.usuario_id,
            "estado_participante": p.estado,
            "pj": 0,
            "pg": 0,
            "pe": 0,
            "pp": 0,
            "puntos": _decimal(p.puntos_ajuste_inicial),
            "score_favor": 0,
            "score_contra": 0,
            "diff_score": 0,
        }

    emparejamientos_q = (
        session.query(SuizoEmparejamiento)
        .join(SuizoRonda, SuizoRonda.id == SuizoEmparejamiento.ronda_id)
        .filter(
            SuizoEmparejamiento.torneo_id == torneo_id,
            SuizoEmparejamiento.estado.in_([EMP_ADMINISTRADO, EMP_CERRADO]),
        )
    )

    if hasta_ronda is not None:
        emparejamientos_q = emparejamientos_q.filter(SuizoRonda.numero <= hasta_ronda)

    for emp in emparejamientos_q.all():
        c1 = emp.coach1_usuario_id
        c2 = emp.coach2_usuario_id

        if c1 not in filas:
            continue

        if emp.es_bye or c2 is None:
            filas[c1]["puntos"] += _decimal(torneo.puntos_bye)
            continue

        if c2 not in filas:
            continue

        s1 = int(emp.score_final_c1 or 0)
        s2 = int(emp.score_final_c2 or 0)

        filas[c1]["pj"] += 1
        filas[c2]["pj"] += 1

        filas[c1]["score_favor"] += s1
        filas[c1]["score_contra"] += s2
        filas[c2]["score_favor"] += s2
        filas[c2]["score_contra"] += s1

        filas[c1]["puntos"] += _decimal(emp.puntos_c1)
        filas[c2]["puntos"] += _decimal(emp.puntos_c2)

        if s1 > s2:
            filas[c1]["pg"] += 1
            filas[c2]["pp"] += 1
        elif s1 < s2:
            filas[c2]["pg"] += 1
            filas[c1]["pp"] += 1
        else:
            filas[c1]["pe"] += 1
            filas[c2]["pe"] += 1

    for fila in filas.values():
        fila["diff_score"] = fila["score_favor"] - fila["score_contra"]

    return sorted(
        filas.values(),
        key=lambda f: (
            -_decimal(f["puntos"]),
            -f["diff_score"],
            -f["score_favor"],
            f["usuario_id"],
        ),
    )
