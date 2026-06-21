import json
from copy import deepcopy
from pathlib import Path


def test_resultado_comunidades_es_resultado_con_titulo_de_comunidades_vs():
    configuracion = json.loads(Path("configuracion.json").read_text(encoding="utf-8"))

    resultado = deepcopy(configuracion["resultado"])
    resultado_comunidades = deepcopy(configuracion["resultadoComunidades"])

    titulo_resultado = next(elemento for elemento in resultado if elemento.get("titulo") is True)
    titulo_comunidades = resultado_comunidades[resultado.index(titulo_resultado)]

    esperado = deepcopy(titulo_resultado)
    esperado.pop("titulo")
    esperado.pop("funcionColor", None)
    esperado["nombre_diccionario"] = "comunidadVS"
    esperado["clave"] = "0"
    esperado["color"] = "#FFFFFF"
    esperado["outlineColor"] = "#FEFEFF"

    resultado[resultado.index(titulo_resultado)] = esperado

    assert resultado_comunidades == resultado
    assert titulo_comunidades["posicion_x"] == titulo_resultado["posicion_x"]
    assert titulo_comunidades["posicion_y"] == titulo_resultado["posicion_y"]
    assert titulo_comunidades["fuente"] == titulo_resultado["fuente"]
    assert titulo_comunidades["size"] == titulo_resultado["size"]
    assert titulo_comunidades["efecto"] == titulo_resultado["efecto"]
    assert titulo_comunidades["nombre_diccionario"] == "comunidadVS"
