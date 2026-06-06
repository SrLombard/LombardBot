from datetime import datetime
from decimal import Decimal
from pathlib import Path
import sys

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from ComunidadesConstantes import (
    PLANTILLA_RONDA1_PENDIENTE,
    PLANTILLA_RONDAS_SIGUIENTES_PENDIENTE,
)
from ComunidadesCore import (
    ErrorConfiguracionComunidades,
    configurar_competicion_comunidades,
    configurar_puntos_equipo_comunidades,
    configurar_puntos_individuales_comunidades,
    crear_torneo_comunidades,
)
from ComunidadesDiscord import parsear_decimal, parsear_fecha_limite
from GestorSQL import Base, ComunidadesTorneo


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _crear(session):
    return crear_torneo_comunidades(
        session,
        nombre="Copa de Comunidades",
        rondas_totales=5,
        fecha_fin_ronda1=datetime(2026, 7, 1, 23, 59),
        dias_por_ronda=7,
        canal_hub_id=1497290209505710120,
        creado_por_discord_id=123,
    )


def test_crea_torneo_en_estado_creado_con_plantillas_pendientes():
    with _session() as session:
        torneo = _crear(session)
        session.commit()

        guardado = session.get(ComunidadesTorneo, torneo.id)
        assert guardado.estado == "CREADO"
        assert guardado.rondas_totales == 5
        assert guardado.dias_por_ronda == 7
        assert guardado.id_competicion_bbowl is None
        assert guardado.plantilla_mensaje_ronda1 == PLANTILLA_RONDA1_PENDIENTE
        assert (
            guardado.plantilla_mensaje_rondas_siguientes
            == PLANTILLA_RONDAS_SIGUIENTES_PENDIENTE
        )


@pytest.mark.parametrize("campo,valor", [("rondas_totales", 0), ("rondas_totales", -1), ("dias_por_ronda", 0), ("dias_por_ronda", -2)])
def test_rechaza_rondas_y_dias_invalidos(campo, valor):
    argumentos = {
        "nombre": "Copa",
        "rondas_totales": 5,
        "fecha_fin_ronda1": datetime(2026, 7, 1, 23, 59),
        "dias_por_ronda": 7,
        "canal_hub_id": 10,
        "creado_por_discord_id": 20,
    }
    argumentos[campo] = valor
    with _session() as session, pytest.raises(ErrorConfiguracionComunidades):
        crear_torneo_comunidades(session, **argumentos)


@pytest.mark.parametrize(
    "fecha,hora",
    [
        ("2026-02-30", "23:59"),
        ("2026-7-01", "23:59"),
        ("2026-07-01", "3:05"),
        ("01-07-2026", "23:59"),
        ("2026-07-01", "24:00"),
    ],
)
def test_parsear_fecha_rechaza_valores_invalidos_o_no_estrictos(fecha, hora):
    with pytest.raises(ValueError, match="YYYY-MM-DD HH:MM"):
        parsear_fecha_limite(fecha, hora)


def test_parsear_fecha_acepta_formato_documentado():
    assert parsear_fecha_limite("2026-07-01", "23:59") == datetime(2026, 7, 1, 23, 59)


@pytest.mark.parametrize("valor", ["abc", "", None])
def test_parsear_decimal_rechaza_textos_no_numericos(valor):
    with pytest.raises(ValueError, match="decimal válido"):
        parsear_decimal(valor, "win")


@pytest.mark.parametrize("valor", ["NaN", "Infinity", "-1", "1.001", "10000"])
def test_core_rechaza_decimales_fuera_del_dominio(valor):
    with _session() as session:
        torneo = _crear(session)
        session.commit()
        with pytest.raises(ErrorConfiguracionComunidades):
            configurar_puntos_equipo_comunidades(
                session,
                torneo_id=torneo.id,
                victoria=valor,
                empate=Decimal("1"),
                derrota=Decimal("0"),
                bye=Decimal("1.5"),
            )


def test_guarda_las_dos_puntuaciones_sin_mezclarlas():
    with _session() as session:
        torneo = _crear(session)
        session.commit()

        configurar_puntos_equipo_comunidades(
            session,
            torneo_id=torneo.id,
            victoria=Decimal("5"),
            empate=Decimal("2"),
            derrota=Decimal("1"),
            bye=Decimal("2.5"),
        )
        configurar_puntos_individuales_comunidades(
            session,
            torneo_id=torneo.id,
            victoria=Decimal("3"),
            empate=Decimal("1"),
            derrota=Decimal("0"),
        )
        session.commit()

        guardado = session.get(ComunidadesTorneo, torneo.id)
        assert (
            guardado.puntos_clasificacion_victoria,
            guardado.puntos_clasificacion_empate,
            guardado.puntos_clasificacion_derrota,
            guardado.puntos_clasificacion_bye,
        ) == (Decimal("5.00"), Decimal("2.00"), Decimal("1.00"), Decimal("2.50"))
        assert (
            guardado.puntos_individuales_victoria,
            guardado.puntos_individuales_empate,
            guardado.puntos_individuales_derrota,
        ) == (Decimal("3.00"), Decimal("1.00"), Decimal("0.00"))


def test_configura_competicion_y_permite_reemplazarla_antes_del_inicio():
    with _session() as session:
        torneo = _crear(session)
        session.commit()
        configurar_competicion_comunidades(
            session, torneo_id=torneo.id, id_competicion_bbowl="primera"
        )
        configurar_competicion_comunidades(
            session, torneo_id=torneo.id, id_competicion_bbowl="segunda"
        )
        session.commit()
        assert session.get(ComunidadesTorneo, torneo.id).id_competicion_bbowl == "segunda"


@pytest.mark.parametrize("operacion", ["competicion", "equipos", "individuales"])
def test_rechaza_cualquier_configuracion_despues_del_inicio_sin_modificarla(operacion):
    with _session() as session:
        torneo = _crear(session)
        session.commit()
        torneo.estado = "EN_CURSO"
        session.commit()

        valores_antes = (
            torneo.id_competicion_bbowl,
            torneo.puntos_clasificacion_victoria,
            torneo.puntos_individuales_victoria,
        )
        with pytest.raises(ErrorConfiguracionComunidades, match="estado CREADO"):
            if operacion == "competicion":
                configurar_competicion_comunidades(
                    session, torneo_id=torneo.id, id_competicion_bbowl="nueva"
                )
            elif operacion == "equipos":
                configurar_puntos_equipo_comunidades(
                    session, torneo_id=torneo.id, victoria=4, empate=2, derrota=0, bye=1
                )
            else:
                configurar_puntos_individuales_comunidades(
                    session, torneo_id=torneo.id, victoria=4, empate=2, derrota=0
                )
        session.rollback()
        guardado = session.get(ComunidadesTorneo, torneo.id)
        assert (
            guardado.id_competicion_bbowl,
            guardado.puntos_clasificacion_victoria,
            guardado.puntos_individuales_victoria,
        ) == valores_antes


def test_error_en_puntuacion_no_deja_actualizacion_parcial():
    with _session() as session:
        torneo = _crear(session)
        session.commit()
        originales = (
            torneo.puntos_clasificacion_victoria,
            torneo.puntos_clasificacion_empate,
            torneo.puntos_clasificacion_derrota,
            torneo.puntos_clasificacion_bye,
        )

        with pytest.raises(ErrorConfiguracionComunidades):
            configurar_puntos_equipo_comunidades(
                session,
                torneo_id=torneo.id,
                victoria=Decimal("5"),
                empate=Decimal("2"),
                derrota=Decimal("1"),
                bye=Decimal("1.001"),
            )
        session.rollback()
        guardado = session.get(ComunidadesTorneo, torneo.id)
        assert (
            guardado.puntos_clasificacion_victoria,
            guardado.puntos_clasificacion_empate,
            guardado.puntos_clasificacion_derrota,
            guardado.puntos_clasificacion_bye,
        ) == originales
