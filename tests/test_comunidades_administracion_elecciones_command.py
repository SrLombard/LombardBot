import ast
import asyncio
from pathlib import Path
from types import SimpleNamespace


FUENTE = Path(__file__).resolve().parents[1] / "LombardBot.py"


class Contexto:
    def __init__(self, *, comisario, canal_id):
        roles = [SimpleNamespace(name="Comisario")] if comisario else []
        self.author = SimpleNamespace(id=999, roles=roles)
        self.channel = SimpleNamespace(id=canal_id)
        self.mensajes = []

    async def send(self, mensaje):
        self.mensajes.append(mensaje)


def _cargar_consulta(*, consulta):
    arbol = ast.parse(FUENTE.read_text(encoding="utf-8-sig"))
    nombres = {
        "es_comisario",
        "_es_canal_administrativo_comunidades",
        "comunidades_consulta_elecciones",
    }
    nodos = []
    for nodo in arbol.body:
        if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)) and nodo.name in nombres:
            nodo.decorator_list = []
            nodos.append(nodo)
    modulo = ast.Module(body=nodos, type_ignores=[])

    class SessionProhibida:
        def __init__(self):
            raise AssertionError("No se debe abrir sesión antes de validar rol y canal")

    entorno = {
        "canales_permitidos": ["457740100097540106"],
        "Session": SessionProhibida,
        "consultar_elecciones_comunidades": consulta,
        "UtilesDiscord": SimpleNamespace(enviar_mensaje_largo=None),
        "ErrorAdministracionEleccionesComunidades": RuntimeError,
    }
    exec(compile(modulo, str(FUENTE), "exec"), entorno)
    return entorno["comunidades_consulta_elecciones"]


def test_no_comisario_no_abre_sesion_ni_revela_informacion():
    llamadas = []
    comando = _cargar_consulta(consulta=lambda *args, **kwargs: llamadas.append(kwargs))
    ctx = Contexto(comisario=False, canal_id=457740100097540106)

    asyncio.run(comando(ctx, 1, 1))

    assert llamadas == []
    assert ctx.mensajes == ["No tienes permiso. Este comando es exclusivo para Comisario."]


def test_canal_incorrecto_se_valida_antes_de_leer_elecciones():
    llamadas = []
    comando = _cargar_consulta(consulta=lambda *args, **kwargs: llamadas.append(kwargs))
    ctx = Contexto(comisario=True, canal_id=123)

    asyncio.run(comando(ctx, 1, 1))

    assert llamadas == []
    assert len(ctx.mensajes) == 1
    assert "No se ha consultado ni revelado ninguna elección" in ctx.mensajes[0]
