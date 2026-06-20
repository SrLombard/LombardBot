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
