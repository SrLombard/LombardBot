import asyncio
from datetime import datetime
from pathlib import Path
import sys

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from ComunidadesCore import (
    anadir_categoria_enfrentamientos_comunidades,
    anadir_categoria_partidos_comunidades,
    crear_torneo_comunidades,
    obtener_categorias_comunidades,
)
from ComunidadesDiscord import (
    ErrorSeleccionCategoriaComunidades,
    seleccionar_categoria_comunidades,
)
from GestorSQL import Base


class CategoriaDiscordDoble:
    def __init__(self, categoria_id, numero_canales):
        self.id = categoria_id
        self.channels = [object() for _ in range(numero_canales)]


class PermisosDoble:
    def __init__(self, *, view_channel=True, manage_channels=True):
        self.view_channel = view_channel
        self.manage_channels = manage_channels


class CategoriaConPermisosDoble(CategoriaDiscordDoble):
    def __init__(self, categoria_id, numero_canales, permisos):
        super().__init__(categoria_id, numero_canales)
        self.permisos = permisos

    def permissions_for(self, miembro):
        return self.permisos


class RespuestaDiscordError(Exception):
    def __init__(self, status):
        super().__init__(f"Discord respondió {status}")
        self.status = status


class GuildDoble:
    def __init__(self, categorias=None, errores_fetch=None):
        self.me = object()
        self.categorias = categorias or {}
        self.errores_fetch = errores_fetch or {}
        self.ids_consultados = []
        self.ids_recuperados = []

    def get_channel(self, categoria_id):
        self.ids_consultados.append(categoria_id)
        return self.categorias.get(categoria_id)

    async def fetch_channel(self, categoria_id):
        self.ids_recuperados.append(categoria_id)
        if categoria_id in self.errores_fetch:
            raise RespuestaDiscordError(self.errores_fetch[categoria_id])
        return self.categorias.get(categoria_id)


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _crear_torneo(session):
    torneo = crear_torneo_comunidades(
        session,
        nombre="Copa",
        rondas_totales=3,
        fecha_fin_ronda1=datetime(2026, 7, 1, 23, 59),
        dias_por_ronda=7,
        canal_hub_id=1497290209505710120,
        creado_por_discord_id=1497290209505710121,
    )
    session.commit()
    return torneo


def _seleccionar(session, guild, torneo_id, tipo):
    return asyncio.run(
        seleccionar_categoria_comunidades(
            session, guild, torneo_id=torneo_id, tipo=tipo
        )
    )


def test_recupera_categorias_de_cada_tipo_en_orden_de_alta():
    with _session() as session:
        torneo = _crear_torneo(session)
        anadir_categoria_partidos_comunidades(
            session, torneo_id=torneo.id, categoria_discord_id=103
        )
        anadir_categoria_partidos_comunidades(
            session, torneo_id=torneo.id, categoria_discord_id=101
        )
        anadir_categoria_enfrentamientos_comunidades(
            session, torneo_id=torneo.id, categoria_discord_id=202
        )
        anadir_categoria_enfrentamientos_comunidades(
            session, torneo_id=torneo.id, categoria_discord_id=201
        )
        session.commit()

        partidos = obtener_categorias_comunidades(
            session, torneo_id=torneo.id, tipo="partidos"
        )
        enfrentamientos = obtener_categorias_comunidades(
            session, torneo_id=torneo.id, tipo="enfrentamientos"
        )

        assert [categoria.categoria_discord_id for categoria in partidos] == [103, 101]
        assert [categoria.categoria_discord_id for categoria in enfrentamientos] == [202, 201]


@pytest.mark.parametrize("tipo", ["partidos", "enfrentamientos"])
def test_selecciona_primera_categoria_con_capacidad_para_ambos_tipos(tipo):
    with _session() as session:
        torneo = _crear_torneo(session)
        alta = (
            anadir_categoria_partidos_comunidades
            if tipo == "partidos"
            else anadir_categoria_enfrentamientos_comunidades
        )
        for categoria_id in (301, 302, 303):
            alta(session, torneo_id=torneo.id, categoria_discord_id=categoria_id)
        session.commit()

        guild = GuildDoble(
            {
                303: CategoriaDiscordDoble(303, 0),
                302: CategoriaDiscordDoble(302, 39),
                301: CategoriaDiscordDoble(301, 40),
            }
        )

        seleccionada = _seleccionar(session, guild, torneo.id, tipo)

        assert seleccionada.id == 302
        assert guild.ids_consultados == [301, 302]


def test_cuenta_todos_los_canales_sin_filtrar_su_procedencia():
    with _session() as session:
        torneo = _crear_torneo(session)
        anadir_categoria_partidos_comunidades(
            session, torneo_id=torneo.id, categoria_discord_id=401
        )
        anadir_categoria_partidos_comunidades(
            session, torneo_id=torneo.id, categoria_discord_id=402
        )
        session.commit()
        primera = CategoriaDiscordDoble(401, 40)
        primera.channels[-1] = {"pertenece_al_torneo": False}
        segunda = CategoriaDiscordDoble(402, 0)

        seleccionada = _seleccionar(
            session, GuildDoble({401: primera, 402: segunda}), torneo.id, "partidos"
        )

        assert seleccionada is segunda


def test_salta_categoria_eliminada_y_usa_la_siguiente():
    with _session() as session:
        torneo = _crear_torneo(session)
        for categoria_id in (501, 502):
            anadir_categoria_enfrentamientos_comunidades(
                session, torneo_id=torneo.id, categoria_discord_id=categoria_id
            )
        session.commit()
        guild = GuildDoble(
            {502: CategoriaDiscordDoble(502, 0)}, errores_fetch={501: 404}
        )

        seleccionada = _seleccionar(
            session, guild, torneo.id, "enfrentamientos"
        )

        assert seleccionada.id == 502
        assert guild.ids_recuperados == [501]


def test_salta_categoria_sin_permisos_para_administrar_canales():
    with _session() as session:
        torneo = _crear_torneo(session)
        for categoria_id in (551, 552):
            anadir_categoria_enfrentamientos_comunidades(
                session, torneo_id=torneo.id, categoria_discord_id=categoria_id
            )
        session.commit()
        sin_permisos = CategoriaConPermisosDoble(
            551, 0, PermisosDoble(manage_channels=False)
        )
        disponible = CategoriaDiscordDoble(552, 0)

        seleccionada = _seleccionar(
            session,
            GuildDoble({551: sin_permisos, 552: disponible}),
            torneo.id,
            "enfrentamientos",
        )

        assert seleccionada is disponible


def test_error_estructurado_diferencia_inexistente_inaccesible_y_llena():
    with _session() as session:
        torneo = _crear_torneo(session)
        for categoria_id in (601, 602, 603):
            anadir_categoria_partidos_comunidades(
                session, torneo_id=torneo.id, categoria_discord_id=categoria_id
            )
        session.commit()
        guild = GuildDoble(
            {603: CategoriaDiscordDoble(603, 40)},
            errores_fetch={601: 404, 602: 403},
        )

        with pytest.raises(ErrorSeleccionCategoriaComunidades) as capturado:
            _seleccionar(session, guild, torneo.id, "partidos")

        error = capturado.value
        assert error.codigo == "SIN_CATEGORIA_UTILIZABLE"
        assert [incidencia.estado for incidencia in error.incidencias] == [
            "INEXISTENTE",
            "INACCESIBLE",
            "LLENA",
        ]
        assert error.incidencias[-1].canales_existentes == 40
        assert error.para_administracion() == {
            "codigo": "SIN_CATEGORIA_UTILIZABLE",
            "detalle": (
                f"Ninguna categoría de partidos del torneo {torneo.id} "
                "tiene capacidad disponible."
            ),
            "torneo_id": torneo.id,
            "tipo": "partidos",
            "categorias": [
                {
                    "categoria_discord_id": 601,
                    "orden_alta": 1,
                    "estado": "INEXISTENTE",
                    "canales_existentes": None,
                    "detalle": None,
                },
                {
                    "categoria_discord_id": 602,
                    "orden_alta": 2,
                    "estado": "INACCESIBLE",
                    "canales_existentes": None,
                    "detalle": None,
                },
                {
                    "categoria_discord_id": 603,
                    "orden_alta": 3,
                    "estado": "LLENA",
                    "canales_existentes": 40,
                    "detalle": None,
                },
            ],
        }


def test_torneo_sin_categorias_falla_con_error_especifico():
    with _session() as session:
        torneo = _crear_torneo(session)

        with pytest.raises(ErrorSeleccionCategoriaComunidades) as capturado:
            _seleccionar(session, GuildDoble(), torneo.id, "enfrentamientos")

        error = capturado.value
        assert error.codigo == "SIN_CATEGORIAS_CONFIGURADAS"
        assert error.incidencias == ()
        assert error.para_administracion()["categorias"] == []
