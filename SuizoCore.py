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


def _get_valor_registro(registro: Any, campo: str, default: Any = None) -> Any:
    """Obtiene un campo desde dict u objeto."""
    if isinstance(registro, dict):
        return registro.get(campo, default)
    return getattr(registro, campo, default)


def calcular_h2h(standings: List[EstadoFila], emparejamientos_cerrados: List[Any]) -> Dict[int, Optional[Decimal]]:
    """Calcula H2H solo para empates con enfrentamiento directo real.

    Reglas:
    - Solo se evalúan jugadores empatados en puntos.
    - Solo se calcula H2H si los jugadores empatados se enfrentaron entre sí.
    - Si no hay partido directo dentro del empate, H2H es None.
    - No se aplica transitividad.
    """
    h2h_por_usuario: Dict[int, Optional[Decimal]] = {
        int(fila["usuario_id"]): None for fila in standings
    }

    empatados_por_puntos: Dict[Decimal, List[int]] = {}
    for fila in standings:
        puntos = _decimal(fila.get("puntos"))
        usuario_id = int(fila["usuario_id"])
        empatados_por_puntos.setdefault(puntos, []).append(usuario_id)

    for usuarios_empatados in empatados_por_puntos.values():
        if len(usuarios_empatados) < 2:
            continue

        set_empatados = set(usuarios_empatados)
        h2h_acumulado: Dict[int, Decimal] = {u: Decimal("0") for u in usuarios_empatados}
        tiene_partido_directo: Dict[int, bool] = {u: False for u in usuarios_empatados}

        for emp in emparejamientos_cerrados:
            c1 = _get_valor_registro(emp, "coach1_usuario_id")
            c2 = _get_valor_registro(emp, "coach2_usuario_id")
            es_bye = bool(_get_valor_registro(emp, "es_bye", False))

            if es_bye or c1 is None or c2 is None:
                continue

            c1 = int(c1)
            c2 = int(c2)
            if c1 not in set_empatados or c2 not in set_empatados:
                continue

            puntos_c1 = _decimal(_get_valor_registro(emp, "puntos_c1"))
            puntos_c2 = _decimal(_get_valor_registro(emp, "puntos_c2"))

            h2h_acumulado[c1] += puntos_c1
            h2h_acumulado[c2] += puntos_c2
            tiene_partido_directo[c1] = True
            tiene_partido_directo[c2] = True

        for usuario_id in usuarios_empatados:
            if tiene_partido_directo[usuario_id]:
                h2h_por_usuario[usuario_id] = h2h_acumulado[usuario_id]

    return h2h_por_usuario


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
