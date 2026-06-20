from __future__ import annotations

from pathlib import Path


def test_comunidades_actualizar_publica_cada_resultado_api_antes_del_corte_una_pasada():
    """El modo `1` debe publicar el resultado detectado antes de cortar el bucle."""
    fuente = Path("LombardBot.py").read_text(encoding="utf-8")
    inicio = fuente.index("@bot.command(name=\"comunidades_actualizar\")")
    fin = fuente.index("\n\nLOGGER_COMUNIDADES", inicio)
    cuerpo = fuente[inicio:fin]

    pos_commit = cuerpo.index("session.commit()")
    pos_publicar = cuerpo.index("await publicar_resultado_partido_comunidades", pos_commit)
    pos_break = cuerpo.index("if not procesar_todos:", pos_publicar)

    assert pos_commit < pos_publicar < pos_break
    bloque_publicacion = cuerpo[pos_publicar:pos_break]
    assert "match=match" in bloque_publicacion
    assert "id_foro=FORO_RESULTADOS_COMUNIDADES_ID" in bloque_publicacion


def test_comunidades_actualizar_mantiene_reintento_con_foro_comunidades():
    fuente = Path("LombardBot.py").read_text(encoding="utf-8")
    inicio = fuente.index("@bot.command(name=\"comunidades_actualizar\")")
    fin = fuente.index("\n\nLOGGER_COMUNIDADES", inicio)
    cuerpo = fuente[inicio:fin]

    assert "await _reintentar_publicaciones_ronda_comunidades(" in cuerpo
    assert "id_foro=FORO_RESULTADOS_COMUNIDADES_ID" in cuerpo


def test_comunidades_admin_partido_publica_en_foro_comunidades():
    fuente = Path("LombardBot.py").read_text(encoding="utf-8")
    inicio = fuente.index('@bot.command(name="comunidades_admin_partido")')
    fin = fuente.index('\n\n@bot.command', inicio)
    cuerpo = fuente[inicio:fin]

    assert "await publicar_resultado_partido_comunidades" in cuerpo
    assert "id_foro=FORO_RESULTADOS_COMUNIDADES_ID" in cuerpo
    assert "FORO_RESULTADOS_GENERAL_ID" not in cuerpo


def test_crear_imagen_resultado_comunidades_usa_plantilla_y_campos_extra():
    fuente = Path("LombardBot.py").read_text(encoding="utf-8")
    inicio = fuente.index("def _crear_imagen_resultado_comunidades")
    fin = fuente.index("\n\ndef _estado_con_emojis_comunidades", inicio)
    cuerpo = fuente[inicio:fin]

    assert 'Imagenes.crear_imagen(\n        "resultadoComunidades"' in cuerpo
    assert "comunidad1={\"0\": comunidad_local}" in cuerpo
    assert "comunidad2={\"0\": comunidad_visitante}" in cuerpo
    assert "comunidadVS={\"0\": comunidad_vs}" in cuerpo
