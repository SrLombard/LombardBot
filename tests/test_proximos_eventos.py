from __future__ import annotations

import ast
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


class _ColumnaSimulada:
    def label(self, _nombre):
        return self

    def __eq__(self, _otro):
        return self

    def __ge__(self, _otro):
        return self

    def __le__(self, _otro):
        return self


class _ConsultaSimulada:
    def join(self, *_args):
        return self

    def outerjoin(self, *_args):
        return self

    def filter(self, *_args):
        return self

    def order_by(self, *_args):
        return self

    def all(self):
        return []


class _CanalSimulado:
    def __init__(self, error=None):
        self.error = error
        self.mensajes = []

    async def send(self, mensaje):
        self.mensajes.append(mensaje)
        if self.error:
            raise self.error


def _cargar_funcion(session):
    fuente = Path("LombardBot.py").read_text(encoding="utf-8")
    modulo = ast.parse(fuente)
    nodo = next(
        nodo
        for nodo in modulo.body
        if isinstance(nodo, ast.AsyncFunctionDef)
        and nodo.name == "func_proximos_eventos"
    )

    columnas_usuario = SimpleNamespace(
        nombre_discord=_ColumnaSimulada(),
        raza=_ColumnaSimulada(),
        id_discord=_ColumnaSimulada(),
        idUsuarios=_ColumnaSimulada(),
        grupo=_ColumnaSimulada(),
    )
    modelos = SimpleNamespace(
        Usuario=columnas_usuario,
        Grupo=SimpleNamespace(
            nombre_grupo=_ColumnaSimulada(), id_grupo=_ColumnaSimulada()
        ),
        Calendario=SimpleNamespace(
            coach1=_ColumnaSimulada(),
            coach2=_ColumnaSimulada(),
            fecha=_ColumnaSimulada(),
        ),
        Ticket=SimpleNamespace(
            coach1=_ColumnaSimulada(),
            coach2=_ColumnaSimulada(),
            fecha=_ColumnaSimulada(),
        ),
        conexionEngine=lambda: object(),
    )
    entorno = {
        "GestorSQL": modelos,
        "aliased": lambda modelo: modelo,
        "datetime": datetime,
        "timedelta": timedelta,
        "sessionmaker": lambda **_kwargs: lambda: session,
    }
    exec(compile(ast.Module(body=[nodo], type_ignores=[]), "LombardBot.py", "exec"), entorno)
    return entorno["func_proximos_eventos"]


@pytest.mark.parametrize("error_envio", [None, RuntimeError("fallo de Discord")])
def test_proximos_eventos_cierra_sesion_si_envio_finaliza_o_falla(error_envio):
    session = SimpleNamespace(query=Mock(return_value=_ConsultaSimulada()), close=Mock())
    canal = _CanalSimulado(error_envio)
    bot = SimpleNamespace(get_channel=Mock(return_value=canal))
    funcion = _cargar_funcion(session)

    asyncio.run(
        funcion(
            bot,
            SimpleNamespace(),
            canal_destino_id="123",
            respuesta_privada=False,
        )
    )

    assert canal.mensajes == ["No hay eventos programados en el intervalo dado."]
    session.close.assert_called_once_with()
