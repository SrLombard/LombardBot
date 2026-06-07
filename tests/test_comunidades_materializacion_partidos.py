import asyncio
from datetime import datetime
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from ComunidadesCore import materializar_identidades_partidos_comunidades
from ComunidadesDiscord import (
    ErrorMaterializacionDiscordComunidades,
    materializar_partidos_comunidades,
)
from GestorSQL import (
    Base,
    ComunidadesCategoriaPartido,
    ComunidadesComunidad,
    ComunidadesEleccionAtacante,
    ComunidadesEnfrentamiento,
    ComunidadesEquipo,
    ComunidadesPartido,
    ComunidadesRonda,
    ComunidadesTorneo,
    Usuario,
)


def _engine():
    engine = create_engine("sqlite://")

    @event.listens_for(engine, "connect")
    def _foreign_keys(dbapi_connection, _):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    return engine


def _crear_escenario(session):
    torneo = ComunidadesTorneo(
        nombre="Comunidades",
        rondas_totales=1,
        fecha_fin_ronda1=datetime(2026, 7, 8, 22, 0),
        plantilla_mensaje_ronda1="R1",
        plantilla_mensaje_rondas_siguientes="R2",
        creado_por_discord_id=999,
    )
    session.add(torneo)
    session.flush()
    comunidades = [
        ComunidadesComunidad(torneo_id=torneo.id, nombre="A"),
        ComunidadesComunidad(torneo_id=torneo.id, nombre="B"),
    ]
    session.add_all(comunidades)
    session.flush()
    equipos = [
        ComunidadesEquipo(torneo_id=torneo.id, comunidad_id=comunidades[0].id, nombre="Equipo A"),
        ComunidadesEquipo(torneo_id=torneo.id, comunidad_id=comunidades[1].id, nombre="Equipo B"),
    ]
    session.add_all(equipos)
    session.flush()
    usuarios = [
        Usuario(idUsuarios=11, id_discord=101, nombre_discord="A Uno"),
        Usuario(idUsuarios=12, id_discord=102, nombre_discord="A Dos"),
        Usuario(idUsuarios=21, id_discord=201, nombre_discord="B Uno"),
        Usuario(idUsuarios=22, id_discord=202, nombre_discord="B Dos"),
    ]
    session.add_all(usuarios)
    ronda = ComunidadesRonda(
        torneo_id=torneo.id,
        numero=1,
        estado="ABIERTA",
        fecha_inicio=datetime(2026, 7, 1),
        fecha_fin=datetime(2026, 7, 8, 22, 0),
        generada_por_discord_id=999,
    )
    session.add(ronda)
    session.flush()
    enfrentamiento = ComunidadesEnfrentamiento(
        torneo_id=torneo.id,
        ronda_id=ronda.id,
        mesa_numero=1,
        equipo_a_id=equipos[0].id,
        equipo_b_id=equipos[1].id,
        canal_general_discord_id=700,
        estado="ELECCIONES_COMPLETAS",
    )
    session.add(enfrentamiento)
    session.flush()
    session.add_all(
        [
            ComunidadesEleccionAtacante(
                torneo_id=torneo.id,
                enfrentamiento_id=enfrentamiento.id,
                equipo_id=equipos[0].id,
                atacante_usuario_id=12,
                defensor_usuario_id=11,
                elegido_por_discord_id=102,
                bloqueada=True,
            ),
            ComunidadesEleccionAtacante(
                torneo_id=torneo.id,
                enfrentamiento_id=enfrentamiento.id,
                equipo_id=equipos[1].id,
                atacante_usuario_id=21,
                defensor_usuario_id=22,
                elegido_por_discord_id=201,
                bloqueada=True,
            ),
            ComunidadesCategoriaPartido(
                torneo_id=torneo.id,
                categoria_discord_id=800,
                orden_alta=1,
            ),
        ]
    )
    session.commit()
    return enfrentamiento.id


class ObjetoDiscord:
    def __init__(self, identificador, nombre=None):
        self.id = identificador
        self.name = nombre


class CanalDiscord(ObjetoDiscord):
    def __init__(self, identificador, categoria=None):
        super().__init__(identificador)
        self.categoria = categoria
        self.mensajes = []
        self.eliminado = False

    async def send(self, mensaje):
        self.mensajes.append(mensaje)

    async def delete(self, reason=None):
        self.eliminado = True
        if self.categoria is not None and self in self.categoria.channels:
            self.categoria.channels.remove(self)


class CategoriaDiscord(ObjetoDiscord):
    def __init__(self, identificador):
        super().__init__(identificador)
        self.channels = []


class GuildDiscord:
    def __init__(self, *, fallar_en_creacion=None):
        self.default_role = ObjetoDiscord(1, "@everyone")
        self.comisario = ObjetoDiscord(2, "Comisario")
        self.roles = [self.default_role, self.comisario]
        self.miembros = {
            discord_id: ObjetoDiscord(discord_id, str(discord_id))
            for discord_id in (101, 102, 201, 202)
        }
        self.general = CanalDiscord(700)
        self.categoria = CategoriaDiscord(800)
        self.canales = {700: self.general, 800: self.categoria}
        self.creaciones = []
        self.fallar_en_creacion = fallar_en_creacion
        self.intentos_creacion = 0

    @property
    def me(self):
        return None

    def get_member(self, identificador):
        return self.miembros.get(identificador)

    def get_channel(self, identificador):
        return self.canales.get(identificador)

    async def fetch_channel(self, identificador):
        return self.canales.get(identificador)

    async def create_text_channel(self, *, name, category, overwrites, reason):
        self.intentos_creacion += 1
        if self.fallar_en_creacion == self.intentos_creacion:
            raise RuntimeError("fallo simulado")
        canal = CanalDiscord(900 + self.intentos_creacion, category)
        category.channels.append(canal)
        self.canales[canal.id] = canal
        self.creaciones.append(
            {"canal": canal, "name": name, "category": category, "overwrites": overwrites}
        )
        return canal


def test_construye_los_dos_cruces_con_indices_estables_e_idempotentes():
    engine = _engine()
    with Session(engine) as session:
        enfrentamiento_id = _crear_escenario(session)

        primero = materializar_identidades_partidos_comunidades(
            session, enfrentamiento_id=enfrentamiento_id
        )
        session.commit()
        segundo = materializar_identidades_partidos_comunidades(
            session, enfrentamiento_id=enfrentamiento_id
        )

        assert primero.creados is True
        assert segundo.creados is False
        partidos = session.query(ComunidadesPartido).order_by(ComunidadesPartido.indice).all()
        assert len(partidos) == 2
        assert [partido.indice for partido in partidos] == [1, 2]
        assert (partidos[0].usuario_local_id, partidos[0].usuario_visitante_id) == (12, 22)
        assert (partidos[1].usuario_local_id, partidos[1].usuario_visitante_id) == (21, 11)
        assert (partidos[0].atacante_usuario_id, partidos[0].defensor_usuario_id) == (12, 22)
        assert (partidos[1].atacante_usuario_id, partidos[1].defensor_usuario_id) == (21, 11)


def test_materializa_dos_canales_con_permisos_mensajes_y_estado():
    engine = _engine()
    guild = GuildDiscord()
    with Session(engine) as session:
        enfrentamiento_id = _crear_escenario(session)
        resultado = asyncio.run(
            materializar_partidos_comunidades(
                session, guild, enfrentamiento_id=enfrentamiento_id
            )
        )

        assert resultado.canales_creados == 2
        assert len(guild.creaciones) == 2
        assert guild.general.mensajes == []
        assert all(creacion["category"] is guild.categoria for creacion in guild.creaciones)
        assert set(guild.creaciones[0]["overwrites"]) == {
            guild.default_role,
            guild.comisario,
            guild.miembros[102],
            guild.miembros[202],
        }
        assert "**Atacante:** <@102>" in guild.creaciones[0]["canal"].mensajes[0]
        assert "**Defensor:** <@202>" in guild.creaciones[0]["canal"].mensajes[0]
        assert "**Fecha límite:** 2026-07-08 22:00" in guild.creaciones[0]["canal"].mensajes[0]
        enfrentamiento = session.get(ComunidadesEnfrentamiento, enfrentamiento_id)
        assert enfrentamiento.estado == "PARTIDOS_CREADOS"
        assert [partido.canal_discord_id for partido in enfrentamiento.partidos] == [901, 902]

        repetido = asyncio.run(
            materializar_partidos_comunidades(
                session, guild, enfrentamiento_id=enfrentamiento_id
            )
        )
        assert repetido.canales_creados == 0
        assert len(guild.creaciones) == 2
        assert session.query(ComunidadesPartido).count() == 2


def test_fallo_tras_primer_canal_es_detectable_y_reintento_no_duplica():
    engine = _engine()
    guild = GuildDiscord(fallar_en_creacion=2)
    with Session(engine) as session:
        enfrentamiento_id = _crear_escenario(session)

        with pytest.raises(ErrorMaterializacionDiscordComunidades) as error:
            asyncio.run(
                materializar_partidos_comunidades(
                    session, guild, enfrentamiento_id=enfrentamiento_id
                )
            )
        assert error.value.codigo == "FALLO_CREACION_CANAL"
        partidos = session.query(ComunidadesPartido).order_by(ComunidadesPartido.indice).all()
        assert len(partidos) == 2
        assert [partido.canal_discord_id for partido in partidos] == [901, None]
        assert session.get(ComunidadesEnfrentamiento, enfrentamiento_id).estado == "ELECCIONES_COMPLETAS"

        guild.fallar_en_creacion = None
        resultado = asyncio.run(
            materializar_partidos_comunidades(
                session, guild, enfrentamiento_id=enfrentamiento_id
            )
        )
        assert resultado.canales_creados == 1
        assert session.query(ComunidadesPartido).count() == 2
        assert [partido.canal_discord_id for partido in session.query(ComunidadesPartido).order_by(ComunidadesPartido.indice)] == [901, 903]
        assert session.get(ComunidadesEnfrentamiento, enfrentamiento_id).estado == "PARTIDOS_CREADOS"


def test_materializacion_atomica_elimina_primer_canal_y_revierte_partidos_si_falla_el_segundo():
    engine = _engine()
    guild = GuildDiscord(fallar_en_creacion=2)
    with Session(engine) as session:
        enfrentamiento_id = _crear_escenario(session)

        with pytest.raises(ErrorMaterializacionDiscordComunidades) as error:
            asyncio.run(
                materializar_partidos_comunidades(
                    session, guild, enfrentamiento_id=enfrentamiento_id, atomico=True
                )
            )

        assert error.value.codigo == "FALLO_CREACION_CANAL"
        assert guild.creaciones[0]["canal"].eliminado is True
        assert guild.categoria.channels == []
        assert session.query(ComunidadesPartido).count() == 0
        assert session.get(ComunidadesEnfrentamiento, enfrentamiento_id).estado == "ELECCIONES_COMPLETAS"
