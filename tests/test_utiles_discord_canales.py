import asyncio
from types import SimpleNamespace

import pytest

from UtilesDiscord import gestionar_canal_discord


CANAL_SPIN_MENCION = "<#1224128423929315468>"


class ObjetoDiscordDoble:
    def __init__(self, **atributos):
        self.__dict__.update(atributos)


class CanalDoble:
    def __init__(self, *, error_envio=None):
        self.id = 987654321
        self.error_envio = error_envio
        self.mensajes = []
        self.permisos = []

    async def set_permissions(self, coach, **permisos):
        self.permisos.append((coach, permisos))

    async def send(self, mensaje):
        if self.error_envio:
            raise self.error_envio
        self.mensajes.append(mensaje)


class GuildDoble:
    def __init__(self, canal):
        self.categories = [SimpleNamespace(id=123, name="Partidos")]
        self.roles = [ObjetoDiscordDoble(name="Comisario")]
        self.default_role = ObjetoDiscordDoble(name="everyone")
        self.coaches = {
            1: SimpleNamespace(mention="<@1>"),
            2: SimpleNamespace(mention="<@2>"),
        }
        self.canal = canal

    async def create_text_channel(self, **_kwargs):
        return self.canal

    def get_member(self, coach_id):
        return self.coaches.get(coach_id)


def _crear_canal(*, bbname1="", bbname2="", error_envio=None):
    canal = CanalDoble(error_envio=error_envio)
    ctx = SimpleNamespace(guild=GuildDoble(canal))
    canal_id = asyncio.run(
        gestionar_canal_discord(
            ctx,
            "crear",
            nombre_canal="Partido Uno",
            coach1_id_discord=1,
            coach2_id_discord=2,
            categoria_id=123,
            bbname1=bbname1,
            bbname2=bbname2,
        )
    )
    return canal_id, canal


@pytest.mark.parametrize(
    ("bbname1", "bbname2"),
    [("Equipo Uno", "Equipo Dos"), ("", "")],
)
def test_mensaje_predeterminado_interpola_el_canal_spin(bbname1, bbname2):
    canal_id, canal = _crear_canal(bbname1=bbname1, bbname2=bbname2)

    assert canal_id == canal.id
    assert len(canal.mensajes) == 1
    assert CANAL_SPIN_MENCION in canal.mensajes[0]


def test_error_posterior_a_crear_canal_conserva_su_id(capsys):
    canal_id, canal = _crear_canal(error_envio=RuntimeError("envío rechazado"))

    assert canal_id == canal.id
    salida = capsys.readouterr().out
    assert "creado con ID 987654321" in salida
    assert "no se pudo completar su configuración" in salida
    assert "No se pudo crear el canal" not in salida
