"""Lógica base de standings para torneos suizos."""

import json
from datetime import datetime
from decimal import Decimal
from functools import cmp_to_key
from typing import Any, Dict, List, Optional

from sqlalchemy import or_

from GestorSQL import (
    SuizoEmparejamiento,
    SuizoPairingTrace,
    SuizoParticipante,
    SuizoRonda,
    SuizoStandingSnapshot,
    SuizoTorneo,
)
from SuizoConstantes import (
    EMP_ADMINISTRADO,
    EMP_CERRADO,
    EMP_PENDIENTE,
    RONDA_CERRADA,
    TORNEO_FINALIZADO,
)


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


def ordenar_standings(standings: List[EstadoFila]) -> List[EstadoFila]:
    """Ordena standings con desempates deterministas y asigna rank consecutivo."""

    def _comparar_filas(fila_a: EstadoFila, fila_b: EstadoFila) -> int:
        puntos_a = _decimal(fila_a.get("puntos"))
        puntos_b = _decimal(fila_b.get("puntos"))
        if puntos_a != puntos_b:
            return -1 if puntos_a > puntos_b else 1

        h2h_a = fila_a.get("h2h_valor")
        h2h_b = fila_b.get("h2h_valor")
        if h2h_a is not None and h2h_b is not None:
            h2h_a_dec = _decimal(h2h_a)
            h2h_b_dec = _decimal(h2h_b)
            if h2h_a_dec != h2h_b_dec:
                return -1 if h2h_a_dec > h2h_b_dec else 1

        buchholz_a = _decimal(fila_a.get("buchholz_cut"))
        buchholz_b = _decimal(fila_b.get("buchholz_cut"))
        if buchholz_a != buchholz_b:
            return -1 if buchholz_a > buchholz_b else 1

        diff_a = int(fila_a.get("diff_score") or 0)
        diff_b = int(fila_b.get("diff_score") or 0)
        if diff_a != diff_b:
            return -1 if diff_a > diff_b else 1

        usuario_a = int(fila_a.get("usuario_id"))
        usuario_b = int(fila_b.get("usuario_id"))
        if usuario_a != usuario_b:
            return -1 if usuario_a < usuario_b else 1

        return 0

    ordenados = sorted(standings, key=cmp_to_key(_comparar_filas))
    for idx, fila in enumerate(ordenados, start=1):
        fila["rank"] = idx
    return ordenados


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
    rivales_por_usuario: Dict[int, List[int]] = {}
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
            "buchholz_cut": Decimal("0"),
        }
        rivales_por_usuario[p.usuario_id] = []

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

    emparejamientos_cerrados = emparejamientos_q.all()

    for emp in emparejamientos_cerrados:
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
        rivales_por_usuario[c1].append(c2)
        rivales_por_usuario[c2].append(c1)

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
        rivales = rivales_por_usuario.get(fila["usuario_id"], [])
        puntos_rivales = [_decimal(filas[r]["puntos"]) for r in rivales if r in filas]
        if len(puntos_rivales) < 2:
            fila["buchholz_cut"] = Decimal("0")
        else:
            suma_rivales = sum(puntos_rivales, Decimal("0"))
            fila["buchholz_cut"] = suma_rivales - min(puntos_rivales)

    standings_intermedios = list(filas.values())
    h2h_por_usuario = calcular_h2h(standings_intermedios, emparejamientos_cerrados)
    for fila in standings_intermedios:
        fila["h2h_valor"] = h2h_por_usuario.get(int(fila["usuario_id"]))

    return ordenar_standings(standings_intermedios)


def _normalizar_json_detalle_tiebreak(fila: EstadoFila) -> Dict[str, Any]:
    detalle = fila.get("json_detalle_tiebreak")
    if isinstance(detalle, dict):
        return dict(detalle)

    if isinstance(detalle, str) and detalle.strip():
        try:
            parsed = json.loads(detalle)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    return {
        "criterios": {
            "h2h": str(fila.get("h2h_valor")) if fila.get("h2h_valor") is not None else None,
            "buchholz_cut": str(_decimal(fila.get("buchholz_cut"))),
            "diff_score": int(fila.get("diff_score") or 0),
        },
        "explicacion": (
            "Orden aplicado: puntos DESC, h2h DESC (si existe), "
            "buchholz_cut DESC, diff_score DESC y usuario_id ASC."
        ),
    }


def guardar_snapshot_ronda(session, torneo_id, ronda_numero, standings_ordenados):
    """Guarda snapshot completo de standings para una ronda.

    Inserta una fila por jugador con estadísticas completas y desempates.
    Si ya existía snapshot para la ronda, lo reemplaza por completo.
    """
    session.query(SuizoStandingSnapshot).filter(
        SuizoStandingSnapshot.torneo_id == torneo_id,
        SuizoStandingSnapshot.ronda_numero == ronda_numero,
    ).delete(synchronize_session=False)

    snapshots = []
    for idx, fila in enumerate(standings_ordenados, start=1):
        rank_ronda = int(fila.get("rank") or idx)
        snapshots.append(
            SuizoStandingSnapshot(
                torneo_id=torneo_id,
                ronda_numero=ronda_numero,
                usuario_id=int(fila["usuario_id"]),
                estado_participante=fila.get("estado_participante") or "ACTIVO",
                pj=int(fila.get("pj") or 0),
                pg=int(fila.get("pg") or 0),
                pe=int(fila.get("pe") or 0),
                pp=int(fila.get("pp") or 0),
                puntos=_decimal(fila.get("puntos")),
                score_favor=int(fila.get("score_favor") or 0),
                score_contra=int(fila.get("score_contra") or 0),
                diff_score=int(fila.get("diff_score") or 0),
                buchholz_cut=_decimal(fila.get("buchholz_cut")),
                h2h_valor=_decimal(fila.get("h2h_valor")) if fila.get("h2h_valor") is not None else None,
                rank_ronda=rank_ronda,
                json_detalle_tiebreak=_normalizar_json_detalle_tiebreak(fila),
            )
        )

    if snapshots:
        session.bulk_save_objects(snapshots)

    session.flush()
    return len(snapshots)


def procesar_cierre_ronda_si_corresponde(session, torneo_id, ronda_numero):
    """Cierra una ronda si ya no hay emparejamientos pendientes.

    Flujo:
    - Si quedan emparejamientos en estado PENDIENTE, no cierra.
    - Cierra ronda (estado + cerrada_en), recalcula standings y guarda snapshot.
    - Si era última ronda, finaliza torneo.
    - Si no era la última, devuelve instrucción para generar la siguiente.
    """
    torneo = session.query(SuizoTorneo).filter(SuizoTorneo.id == torneo_id).one_or_none()
    if torneo is None:
        return {"cerrada": False, "motivo": "TORNEO_NO_EXISTE", "pendientes": None, "ronda_numero": int(ronda_numero)}

    ronda = (
        session.query(SuizoRonda)
        .filter(
            SuizoRonda.torneo_id == torneo_id,
            SuizoRonda.numero == ronda_numero,
        )
        .one_or_none()
    )
    if ronda is None:
        return {"cerrada": False, "motivo": "RONDA_NO_EXISTE", "pendientes": None, "ronda_numero": int(ronda_numero)}

    pendientes = (
        session.query(SuizoEmparejamiento)
        .filter(
            SuizoEmparejamiento.torneo_id == torneo_id,
            SuizoEmparejamiento.ronda_id == ronda.id,
            SuizoEmparejamiento.estado == EMP_PENDIENTE,
        )
        .count()
    )
    if pendientes > 0:
        return {
            "cerrada": False,
            "motivo": "HAY_PENDIENTES",
            "pendientes": int(pendientes),
            "ronda_numero": int(ronda_numero),
        }

    ronda.estado = RONDA_CERRADA
    ronda.cerrada_en = datetime.now()

    standings = calcular_standings(session, torneo_id, hasta_ronda=ronda_numero)
    snapshot_filas = guardar_snapshot_ronda(session, torneo_id, ronda_numero, standings)

    es_ultima_ronda = int(ronda_numero) >= int(torneo.rondas_totales)
    if es_ultima_ronda:
        torneo.estado = TORNEO_FINALIZADO

    session.flush()
    return {
        "cerrada": True,
        "motivo": "CERRADA",
        "pendientes": 0,
        "es_ultima_ronda": es_ultima_ronda,
        "siguiente_ronda_numero": None if es_ultima_ronda else int(ronda_numero) + 1,
        "snapshot_filas": int(snapshot_filas),
        "standings": standings,
        "ronda_numero": int(ronda_numero),
    }


def generar_pairings_backtracking(session, torneo_id, ronda_numero):
    """Genera pairings de ronda usando backtracking con reglas suizas.

    Prioridades:
    1) Evitar rivales repetidos.
    2) Evitar mirror de raza.
    3) Permitir repetidos/mirror como fallback si no hay solución.
    """
    ronda = (
        session.query(SuizoRonda)
        .filter(
            SuizoRonda.torneo_id == torneo_id,
            SuizoRonda.numero == ronda_numero,
        )
        .one_or_none()
    )
    if ronda is None:
        return []

    standings = calcular_standings(session, torneo_id, hasta_ronda=ronda_numero - 1 if ronda_numero > 1 else None)
    participantes = (
        session.query(SuizoParticipante)
        .filter(
            SuizoParticipante.torneo_id == torneo_id,
            SuizoParticipante.estado == "ACTIVO",
            or_(
                SuizoParticipante.late_join_ronda.is_(None),
                SuizoParticipante.late_join_ronda <= ronda_numero,
            ),
        )
        .all()
    )
    participantes_por_usuario = {int(p.usuario_id): p for p in participantes}
    activos = [fila for fila in standings if int(fila["usuario_id"]) in participantes_por_usuario]
    if not activos:
        return []

    activos_por_puntos: Dict[str, List[int]] = {}
    for fila in activos:
        puntos = str(_decimal(fila.get("puntos")))
        activos_por_puntos.setdefault(puntos, []).append(int(fila["usuario_id"]))

    usuarios_ordenados = [int(f["usuario_id"]) for f in activos]
    grupo_por_usuario = {}
    for idx, (_, usuarios) in enumerate(
        sorted(activos_por_puntos.items(), key=lambda item: Decimal(item[0]), reverse=True)
    ):
        for u in usuarios:
            grupo_por_usuario[u] = idx

    historial = (
        session.query(SuizoEmparejamiento.coach1_usuario_id, SuizoEmparejamiento.coach2_usuario_id, SuizoEmparejamiento.es_bye)
        .join(SuizoRonda, SuizoRonda.id == SuizoEmparejamiento.ronda_id)
        .filter(
            SuizoEmparejamiento.torneo_id == torneo_id,
            SuizoRonda.numero < ronda_numero,
        )
        .all()
    )

    rivales_previos = {u: set() for u in usuarios_ordenados}
    byes_previos = {u: int(participantes_por_usuario[u].cantidad_byes or 0) for u in usuarios_ordenados}
    for c1, c2, es_bye in historial:
        if c1 is None:
            continue
        c1 = int(c1)
        if c1 in byes_previos and bool(es_bye):
            byes_previos[c1] += 1
        if c2 is None or bool(es_bye):
            continue
        c2 = int(c2)
        if c1 in rivales_previos:
            rivales_previos[c1].add(c2)
        if c2 in rivales_previos:
            rivales_previos[c2].add(c1)

    def es_mirror(u1, u2):
        raza1 = (participantes_por_usuario[u1].raza_competicion or "").strip().lower()
        raza2 = (participantes_por_usuario[u2].raza_competicion or "").strip().lower()
        return bool(raza1 and raza2 and raza1 == raza2)

    def elegir_bye(disponibles):
        elegibles = [u for u in disponibles if byes_previos.get(u, 0) == 0]
        pool = elegibles if elegibles else list(disponibles)
        return sorted(
            pool,
            key=lambda u: (
                grupo_por_usuario.get(u, 10**6),
                _decimal(next(f["puntos"] for f in activos if int(f["usuario_id"]) == u)),
                u,
            ),
            reverse=True,
        )[-1]

    def resolver(allow_repeat, allow_mirror):
        conflictos = {"repetido": 0, "mirror": 0, "sin_rival": 0}
        usados = set()
        mesas = []

        bye_asignado = None
        if len(usuarios_ordenados) % 2 == 1:
            bye_asignado = elegir_bye(usuarios_ordenados)
            usados.add(bye_asignado)
            mesas.append(
                {
                    "coach1": bye_asignado,
                    "coach2": None,
                    "es_bye": True,
                    "forfeit_tipo": "NONE",
                }
            )

        restantes = [u for u in usuarios_ordenados if u not in usados]

        def backtrack(pendientes):
            if not pendientes:
                return True
            u1 = pendientes[0]
            candidatos = []
            for u2 in pendientes[1:]:
                delta_grupo = abs(grupo_por_usuario.get(u1, 0) - grupo_por_usuario.get(u2, 0))
                candidatos.append((delta_grupo, es_mirror(u1, u2), u2))
            candidatos.sort(key=lambda x: (x[0], x[1], x[2]))

            for _, mirror_actual, u2 in candidatos:
                repetido = u2 in rivales_previos.get(u1, set())
                if repetido and not allow_repeat:
                    conflictos["repetido"] += 1
                    continue
                if mirror_actual and not allow_mirror:
                    conflictos["mirror"] += 1
                    continue

                mesas.append(
                    {
                        "coach1": u1,
                        "coach2": u2,
                        "es_bye": False,
                        "forfeit_tipo": "NONE",
                    }
                )
                nuevos = [u for u in pendientes[1:] if u != u2]
                if backtrack(nuevos):
                    return True
                mesas.pop()

            conflictos["sin_rival"] += 1
            return False

        ok = backtrack(restantes)
        if not ok:
            return None, conflictos
        mesas_ordenadas = sorted(
            mesas,
            key=lambda m: (0 if not m["es_bye"] else 1, m["coach1"], m["coach2"] if m["coach2"] is not None else 10**9),
        )
        return mesas_ordenadas, conflictos

    seed_snapshot = (
        session.query(SuizoStandingSnapshot.id)
        .filter(
            SuizoStandingSnapshot.torneo_id == torneo_id,
            SuizoStandingSnapshot.ronda_numero == max(1, ronda_numero - 1),
        )
        .order_by(SuizoStandingSnapshot.id.asc())
        .first()
    )
    seed_snapshot_id = int(seed_snapshot[0]) if seed_snapshot else None

    intentos = [
        (1, False, False, "OK"),
        (2, False, True, "FALLBACK_MIRROR"),
        (3, True, False, "FALLBACK_REPETIDO"),
        (4, True, True, "FALLBACK_REPETIDO"),
    ]

    resultado_final = []
    for intento, allow_repeat, allow_mirror, resultado in intentos:
        mesas, conflictos = resolver(allow_repeat=allow_repeat, allow_mirror=allow_mirror)
        traza = SuizoPairingTrace(
            torneo_id=torneo_id,
            ronda_id=ronda.id,
            seed_snapshot_id=seed_snapshot_id,
            intento=intento,
            resultado=resultado if mesas else "SIN_SOLUCION",
            reglas_aplicadas={
                "solo_activos": True,
                "agrupado_por_puntos": True,
                "allow_repeat": allow_repeat,
                "allow_mirror": allow_mirror,
            },
            conflictos=conflictos,
            created_at=datetime.utcnow(),
        )
        session.add(traza)
        if mesas is not None:
            resultado_final = mesas
            break

    session.flush()
    return resultado_final
