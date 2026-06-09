from __future__ import annotations

from datetime import datetime
from itertools import count
import random
from pathlib import Path
from typing import Callable

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from ComunidadesCore import (
    anadir_comunidad_comunidades,
    anadir_equipo_comunidades,
    crear_torneo_comunidades,
    generar_ronda_comunidades,
    forzar_elecciones_comunidades,
    materializar_identidades_partidos_comunidades,
)
from GestorSQL import Base, ComunidadesMiembro


RAZAS_FIXTURE = (
    "Amazonas",
    "Caos Elegido",
    "Elfos Silvanos",
    "Enanos",
    "Hombres Lagarto",
    "Humanos",
    "Nobleza Imperial",
    "No muertos",
    "Nordicos",
    "Orcos",
    "Renegados",
    "Union Elfica",
)


@pytest.fixture
def comunidades_session() -> Session:
    """SQLite aislado con las mismas claves foráneas que los tests de persistencia."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _activar_claves_foraneas(dbapi_connection, _connection_record):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def torneo_comunidades_factory(comunidades_session: Session) -> Callable:
    secuencia = count(1)

    def crear(*, rondas: int = 2, nombre: str | None = None):
        numero = next(secuencia)
        torneo = crear_torneo_comunidades(
            comunidades_session,
            nombre=nombre or f"Torneo integración {numero}",
            rondas_totales=rondas,
            fecha_fin_ronda1=datetime(2026, 7, 8, 22, 0),
            dias_por_ronda=7,
            canal_hub_id=800_000 + numero,
            creado_por_discord_id=900_000 + numero,
        )
        torneo.id_competicion_bbowl = f"bbowl-{numero}"
        torneo.plantilla_mensaje_ronda1 = "Ronda inicial"
        torneo.plantilla_mensaje_rondas_siguientes = "Ronda {ronda}"
        comunidades_session.flush()
        return torneo

    return crear


@pytest.fixture
def comunidad_comunidades_factory(comunidades_session: Session) -> Callable:
    def crear(torneo, nombre: str):
        return anadir_comunidad_comunidades(
            comunidades_session, torneo_id=int(torneo.id), nombre=nombre
        )

    return crear


@pytest.fixture
def equipo_comunidades_factory(comunidades_session: Session) -> Callable:
    secuencia = count(1)

    def crear(
        torneo,
        comunidad,
        *,
        nombre: str | None = None,
        razas: tuple[str, str] | None = None,
        estado: str = "NEUTRO",
        zombie: bool = False,
    ):
        numero = next(secuencia)
        razas_equipo = razas or (
            RAZAS_FIXTURE[(numero * 2 - 2) % len(RAZAS_FIXTURE)],
            RAZAS_FIXTURE[(numero * 2 - 1) % len(RAZAS_FIXTURE)],
        )
        equipo = anadir_equipo_comunidades(
            comunidades_session,
            torneo_id=int(torneo.id),
            nombre=nombre or f"Equipo {numero:02d}",
            comunidad_nombre=comunidad.nombre,
            jugador1_discord_id=1_000_000 + numero * 10 + 1,
            jugador1_nombre_discord=f"Jugador {numero:02d} A",
            raza1=razas_equipo[0],
            jugador2_discord_id=1_000_000 + numero * 10 + 2,
            jugador2_nombre_discord=f"Jugador {numero:02d} B",
            raza2=razas_equipo[1],
        )
        equipo.estado_temporal = estado
        equipo.es_zombie = zombie
        comunidades_session.flush()
        return equipo

    return crear


@pytest.fixture
def escenario_comunidades_factory(
    comunidades_session: Session,
    torneo_comunidades_factory: Callable,
    comunidad_comunidades_factory: Callable,
    equipo_comunidades_factory: Callable,
) -> Callable:
    """Crea un torneo inscrito con distribución circular entre comunidades."""

    def crear(*, equipos: int = 4, comunidades: int = 4, rondas: int = 2):
        torneo = torneo_comunidades_factory(rondas=rondas)
        comunidades_creadas = [
            comunidad_comunidades_factory(torneo, f"Comunidad {indice + 1}")
            for indice in range(comunidades)
        ]
        equipos_creados = [
            equipo_comunidades_factory(
                torneo,
                comunidades_creadas[indice % comunidades],
                nombre=f"Equipo {indice + 1}",
            )
            for indice in range(equipos)
        ]
        comunidades_session.commit()
        return torneo, comunidades_creadas, equipos_creados

    return crear


@pytest.fixture
def ronda_comunidades_factory(comunidades_session: Session) -> Callable:
    """Genera rondas reales con una semilla explícita y reproducible."""

    def crear(torneo, numero: int, *, semilla: int = 1, actor_id: int = 999_999):
        return generar_ronda_comunidades(
            comunidades_session,
            int(torneo.id),
            numero,
            actor_id,
            random.Random(semilla),
        )

    return crear


@pytest.fixture
def materializar_enfrentamiento(comunidades_session: Session) -> Callable:
    """Fuerza elecciones deterministas y crea las dos identidades BO1."""

    def materializar(enfrentamiento, *, ronda_numero: int):
        miembros_a = (
            comunidades_session.query(ComunidadesMiembro)
            .filter_by(equipo_id=enfrentamiento.equipo_a_id)
            .order_by(ComunidadesMiembro.posicion)
            .all()
        )
        miembros_b = (
            comunidades_session.query(ComunidadesMiembro)
            .filter_by(equipo_id=enfrentamiento.equipo_b_id)
            .order_by(ComunidadesMiembro.posicion)
            .all()
        )
        forzar_elecciones_comunidades(
            comunidades_session,
            torneo_id=int(enfrentamiento.torneo_id),
            ronda_numero=ronda_numero,
            enfrentamiento_id=int(enfrentamiento.id),
            atacante_equipo_a_discord_id=int(miembros_a[0].usuario.id_discord),
            atacante_equipo_b_discord_id=int(miembros_b[0].usuario.id_discord),
            actor_discord_id=999_999,
        )
        resultado = materializar_identidades_partidos_comunidades(
            comunidades_session, enfrentamiento_id=int(enfrentamiento.id)
        )
        comunidades_session.flush()
        return resultado.partidos

    return materializar


@pytest.fixture
def ddl_mysql_path() -> Path:
    return Path(__file__).resolve().parents[1] / "BD" / "comunidades_schema.sql"
