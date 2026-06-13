import asyncio
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from ComunidadesCore import ErrorSeleccionAtacanteComunidades
from ComunidadesDiscord import ejecutar_seleccion_atacante_comunidades


class SessionDoble:
    def __init__(self):
        self.closed = False
        self.rollbacks = 0

    def close(self):
        self.closed = True

    def rollback(self):
        self.rollbacks += 1


class ResponseDoble:
    def __init__(self):
        self.mensajes = []

    def is_done(self):
        return bool(self.mensajes)

    async def send_message(self, mensaje, *, ephemeral=False):
        self.mensajes.append((mensaje, ephemeral))


class FollowupDoble:
    def __init__(self):
        self.mensajes = []

    async def send(self, mensaje, *, ephemeral=False):
        self.mensajes.append((mensaje, ephemeral))


class CanalDoble:
    def __init__(self, canal_id=555, fallar_en=None):
        self.id = canal_id
        self.mensajes = []
        self.fallar_en = fallar_en
        self.intentos = 0

    async def send(self, mensaje):
        self.intentos += 1
        if self.fallar_en == self.intentos:
            raise RuntimeError("fallo Discord")
        self.mensajes.append(mensaje)


class InteraccionDoble:
    def __init__(self, *, canal=None, actor_id=101):
        self.guild = SimpleNamespace(id=1)
        self.channel = canal or CanalDoble()
        self.user = SimpleNamespace(id=actor_id)
        self.response = ResponseDoble()
        self.followup = FollowupDoble()


def resultado_eleccion(*, completar=False):
    equipo = SimpleNamespace(
        nombre="Equipo @A",
        comunidad=SimpleNamespace(nombre="Comunidad @Uno"),
    )
    return SimpleNamespace(
        eleccion=SimpleNamespace(enfrentamiento_id=77, equipo=equipo),
        atacante=SimpleNamespace(id_discord=101, nombre_discord="Uno"),
        defensor=SimpleNamespace(id_discord=102, nombre_discord="Dos"),
        equipo_nombre="Equipo @A",
        requiere_crear_partidos=completar,
        acaba_de_completar_elecciones=completar,
    )


def ejecutar(coro):
    return asyncio.run(coro)


def test_primera_eleccion_responde_privado_publica_sin_identidades_y_no_materializa():
    interaccion = InteraccionDoble()
    sesiones = []
    llamadas = []

    def session_factory():
        sesion = SessionDoble()
        sesiones.append(sesion)
        return sesion

    def elegir(session, **kwargs):
        llamadas.append(kwargs)
        return resultado_eleccion()

    async def materializar(*args, **kwargs):
        raise AssertionError("No debe materializar la primera elección")

    ejecutar(
        ejecutar_seleccion_atacante_comunidades(
            interaccion,
            SimpleNamespace(id=101),
            session_factory=session_factory,
            servicio_eleccion=elegir,
            servicio_materializacion=materializar,
            servicio_resolucion_enfrentamiento=lambda session, canal_id: 77,
            elegido_en=datetime(2026, 6, 7, 12, 0),
        )
    )

    privado, ephemeral = interaccion.response.mensajes[0]
    assert ephemeral is True
    assert "**Equipo:** Equipo @\u200bA (Comunidad @\u200bUno)" in privado
    assert "**Atacante:** <@101>" in privado
    assert "**Defensor:** <@102>" in privado
    assert interaccion.channel.mensajes == [
        "El equipo Equipo @\u200bA (Comunidad @\u200bUno) ha elegido atacante"
    ]
    assert llamadas == [{
        "enfrentamiento_id": 77,
        "actor_discord_id": 101,
        "atacante_discord_id": 101,
        "elegido_en": datetime(2026, 6, 7, 12, 0),
    }]
    assert len(sesiones) == 1 and sesiones[0].closed


def test_segunda_eleccion_anuncia_materializa_una_vez_y_confirma_canales():
    interaccion = InteraccionDoble(actor_id=201)
    sesiones = []
    materializaciones = []

    def session_factory():
        sesion = SessionDoble()
        sesiones.append(sesion)
        return sesion

    def elegir(session, **kwargs):
        return resultado_eleccion(completar=True)

    async def materializar(session, guild, *, enfrentamiento_id):
        materializaciones.append((session, guild, enfrentamiento_id))
        return SimpleNamespace(canal_ids=(901, 902))

    ejecutar(
        ejecutar_seleccion_atacante_comunidades(
            interaccion,
            SimpleNamespace(id=202),
            session_factory=session_factory,
            servicio_eleccion=elegir,
            servicio_materializacion=materializar,
            servicio_resolucion_enfrentamiento=lambda session, canal_id: 77,
        )
    )

    assert interaccion.channel.mensajes == [
        "El equipo Equipo @\u200bA (Comunidad @\u200bUno) ha elegido atacante",
        "Se van a crear los encuentros",
        "Encuentros creados: <#901> y <#902>",
    ]
    assert len(materializaciones) == 1
    assert materializaciones[0][2] == 77
    assert len(sesiones) == 2 and all(sesion.closed for sesion in sesiones)


def test_elecciones_bloqueadas_no_publican_ni_materializan():
    interaccion = InteraccionDoble()
    materializaciones = []

    def elegir(session, **kwargs):
        raise ErrorSeleccionAtacanteComunidades(
            "ELECCIONES_BLOQUEADAS", "detalle no público"
        )

    async def materializar(*args, **kwargs):
        materializaciones.append(True)

    ejecutar(
        ejecutar_seleccion_atacante_comunidades(
            interaccion,
            SimpleNamespace(id=101),
            session_factory=SessionDoble,
            servicio_eleccion=elegir,
            servicio_materializacion=materializar,
            servicio_resolucion_enfrentamiento=lambda session, canal_id: 77,
        )
    )

    assert interaccion.response.mensajes == [
        ("Las elecciones ya están completas y no se pueden modificar.", True)
    ]
    assert interaccion.channel.mensajes == []
    assert materializaciones == []


def test_fallo_materializacion_conserva_eleccion_notifica_y_cierra_sesion():
    interaccion = InteraccionDoble()
    sesiones = []
    avisos = []

    def session_factory():
        sesion = SessionDoble()
        sesiones.append(sesion)
        return sesion

    def elegir(session, **kwargs):
        return resultado_eleccion(completar=True)

    async def materializar(session, guild, *, enfrentamiento_id):
        raise RuntimeError("secreto interno")

    async def notificar(mensaje):
        avisos.append(mensaje)

    ejecutar(
        ejecutar_seleccion_atacante_comunidades(
            interaccion,
            SimpleNamespace(id=101),
            session_factory=session_factory,
            servicio_eleccion=elegir,
            servicio_materializacion=materializar,
            servicio_resolucion_enfrentamiento=lambda session, canal_id: 77,
            notificar_administracion=notificar,
        )
    )

    assert len(sesiones) == 2
    assert sesiones[1].rollbacks == 1
    assert all(sesion.closed for sesion in sesiones)
    assert "secreto interno" in avisos[0]
    assert "secreto interno" not in interaccion.followup.mensajes[0][0]
    assert interaccion.channel.mensajes == [
        "El equipo Equipo @\u200bA (Comunidad @\u200bUno) ha elegido atacante",
        "Se van a crear los encuentros",
    ]


def test_fallo_del_aviso_publico_no_revierte_y_aun_materializa():
    interaccion = InteraccionDoble(canal=CanalDoble(fallar_en=1))
    avisos = []
    materializaciones = []

    def elegir(session, **kwargs):
        return resultado_eleccion(completar=True)

    async def materializar(session, guild, *, enfrentamiento_id):
        materializaciones.append(enfrentamiento_id)
        return SimpleNamespace(canal_ids=(901, 902))

    async def notificar(mensaje):
        avisos.append(mensaje)

    ejecutar(
        ejecutar_seleccion_atacante_comunidades(
            interaccion,
            SimpleNamespace(id=101),
            session_factory=SessionDoble,
            servicio_eleccion=elegir,
            servicio_materializacion=materializar,
            servicio_resolucion_enfrentamiento=lambda session, canal_id: 77,
            notificar_administracion=notificar,
        )
    )

    assert materializaciones == [77]
    assert avisos and "aviso público" in avisos[0]
    assert interaccion.channel.mensajes == [
        "Se van a crear los encuentros",
        "Encuentros creados: <#901> y <#902>",
    ]


def test_canal_sin_enfrentamiento_se_rechaza_sin_llamar_servicios():
    interaccion = InteraccionDoble(canal=CanalDoble(canal_id=999))
    llamadas = []

    def resolver(session, canal_id):
        raise ErrorSeleccionAtacanteComunidades(
            "ENFRENTAMIENTO_NO_EXISTE", "detalle interno"
        )

    def elegir(*args, **kwargs):
        llamadas.append("eleccion")

    async def materializar(*args, **kwargs):
        llamadas.append("materializacion")

    ejecutar(
        ejecutar_seleccion_atacante_comunidades(
            interaccion,
            SimpleNamespace(id=101),
            session_factory=SessionDoble,
            servicio_resolucion_enfrentamiento=resolver,
            servicio_eleccion=elegir,
            servicio_materializacion=materializar,
        )
    )

    assert interaccion.response.mensajes == [
        ("Este canal no corresponde al canal general de un enfrentamiento activo.", True)
    ]
    assert interaccion.channel.mensajes == []
    assert llamadas == []
