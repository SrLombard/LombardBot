import json
from copy import deepcopy
from pathlib import Path


def test_resultados_comparten_el_layout_salvo_el_titulo_de_competicion():
    configuracion = json.loads(Path("configuracion.json").read_text(encoding="utf-8"))

    resultado = deepcopy(configuracion["resultado"])
    resultado_comunidades = deepcopy(configuracion["resultadoComunidades"])

    titulo_resultado = next(elemento for elemento in resultado if elemento.get("titulo") is True)
    titulo_comunidades = next(
        elemento
        for elemento in resultado_comunidades
        if elemento.get("nombre_diccionario") == "comunidadVS"
    )

    resultado.remove(titulo_resultado)
    resultado_comunidades.remove(titulo_comunidades)

    assert resultado_comunidades == resultado
    assert titulo_resultado["titulo"] is True
    assert titulo_comunidades["nombre_diccionario"] == "comunidadVS"
