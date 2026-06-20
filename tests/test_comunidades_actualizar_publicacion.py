from __future__ import annotations

from pathlib import Path

from DiscordConstantes import (
    FORO_RESULTADOS_COMUNIDADES_ID,
    FORO_RESULTADOS_GENERAL_ID,
)
from GestorSQL import ComunidadesEnfrentamiento
from Imagenes import _datos_comunidades_resultado


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


def test_comunidades_actualizar_reintenta_solo_partidos_fallidos_con_foro_comunidades():
    fuente = Path("LombardBot.py").read_text(encoding="utf-8")
    inicio = fuente.index("@bot.command(name=\"comunidades_actualizar\")")
    fin = fuente.index("\n\nLOGGER_COMUNIDADES", inicio)
    cuerpo = fuente[inicio:fin]

    assert "partidos_publicacion_fallida = set()" in cuerpo
    assert "partidos_publicacion_fallida.add(int(resultado.partido.id))" in cuerpo
    assert "await _reintentar_publicaciones_partidos_comunidades(" in cuerpo
    assert "await _reintentar_publicaciones_ronda_comunidades(" not in cuerpo
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


def test_constantes_foros_resultados_separan_comunidades_de_flujos_generales():
    assert FORO_RESULTADOS_COMUNIDADES_ID == 1517927833966739567
    assert FORO_RESULTADOS_GENERAL_ID == 1223765590146158653


def test_comunidades_actualizar_importado_usa_foro_especifico_de_comunidades():
    fuente = Path("LombardBot.py").read_text(encoding="utf-8")
    inicio = fuente.index('@bot.command(name="comunidades_actualizar")')
    fin = fuente.index("\n\nLOGGER_COMUNIDADES", inicio)
    cuerpo = fuente[inicio:fin]

    bloque_publicacion = cuerpo[
        cuerpo.index("await publicar_resultado_partido_comunidades"):
        cuerpo.index("if not procesar_todos:")
    ]

    assert "id_foro=FORO_RESULTADOS_COMUNIDADES_ID" in bloque_publicacion
    assert "FORO_RESULTADOS_GENERAL_ID" not in bloque_publicacion
    assert str(FORO_RESULTADOS_COMUNIDADES_ID) == "1517927833966739567"


def test_publicacion_comunidades_genera_resultado_con_plantilla_comunidades():
    fuente = Path("LombardBot.py").read_text(encoding="utf-8")
    inicio = fuente.index("async def publicar_resultado_partido_comunidades")
    fin = fuente.index(
        "\n\nasync def _reintentar_publicaciones_ronda_comunidades", inicio
    )
    cuerpo = fuente[inicio:fin]

    assert (
        "ruta = _crear_imagen_resultado_comunidades(session, partido, match)" in cuerpo
    )

    fuente_imagenes = Path("Imagenes.py").read_text(encoding="utf-8")
    inicio_imagen = fuente_imagenes.index("async def imagenResultado(")
    fin_imagen = fuente_imagenes.index("\n    finally:", inicio_imagen)
    cuerpo_imagen = fuente_imagenes[inicio_imagen:fin_imagen]

    assert "'resultadoComunidades'" in cuerpo_imagen
    assert "es_comunidades" in cuerpo_imagen


def test_publicacion_comunidades_usa_session_get_y_reutiliza_hilo_completado():
    fuente = Path("LombardBot.py").read_text(encoding="utf-8")
    inicio = fuente.index("async def publicar_resultado_partido_comunidades")
    fin = fuente.index(
        "\n\nasync def _reintentar_publicaciones_ronda_comunidades", inicio
    )
    cuerpo = fuente[inicio:fin]

    assert "session.get(GestorSQL.ComunidadesPartido, int(partido_id))" in cuerpo
    assert ".query(GestorSQL.ComunidadesPartido).get" not in cuerpo
    assert "await _resolver_hilo_resultados_publicacion_comunidades(" in cuerpo

    inicio_helper = fuente.index(
        "async def _resolver_hilo_resultados_publicacion_comunidades"
    )
    fin_helper = fuente.index("\n\nasync def _enviar_unico_comunidades", inicio_helper)
    helper = fuente[inicio_helper:fin_helper]

    assert 'estado_hilo == "COMPLETADA" and hilo_id' in helper
    assert "await _resolver_canal_notificacion_comunidades(ctx, int(hilo_id))" in helper
    assert "otro proceso está creando el hilo de resultados" in helper


def test_datos_plantilla_comunidades_incluyen_comunidades_y_vs_exacto(
    comunidades_session,
    escenario_comunidades_factory,
    ronda_comunidades_factory,
    materializar_enfrentamiento,
):
    torneo, comunidades, _ = escenario_comunidades_factory(
        equipos=2, comunidades=2, rondas=1
    )
    ronda = ronda_comunidades_factory(torneo, 1, semilla=12)
    enfrentamiento = comunidades_session.get(
        ComunidadesEnfrentamiento,
        ronda["enfrentamiento_ids"][0],
    )
    partido = materializar_enfrentamiento(enfrentamiento, ronda_numero=1)[0]
    partido.partido_bloodbowl_id = "bbowl-comunidades-resultado"
    comunidades_session.commit()

    datos = _datos_comunidades_resultado(
        comunidades_session, "bbowl-comunidades-resultado"
    )

    assert set(datos) == {"comunidad1", "comunidad2", "comunidadVS"}
    assert datos["comunidad1"] == {"0": comunidades[0].nombre}
    assert datos["comunidad2"] == {"0": comunidades[1].nombre}
    assert datos["comunidadVS"] == {
        "0": f"{comunidades[0].nombre} Vs {comunidades[1].nombre}"
    }
    assert " Vs " in datos["comunidadVS"]["0"]
    assert " vs " not in datos["comunidadVS"]["0"]


def test_suizo_normal_sigue_usando_foro_general_y_plantilla_resultado_actual():
    fuente = Path("LombardBot.py").read_text(encoding="utf-8")
    inicio = fuente.index("async def publicar_resultado_suizo_en_foro")
    fin = fuente.index("\n\ndef _es_mensaje_inicial_suizo", inicio)
    cuerpo = fuente[inicio:fin]

    assert "foro_resultados_id = FORO_RESULTADOS_GENERAL_ID" in cuerpo
    assert "FORO_RESULTADOS_COMUNIDADES_ID" not in cuerpo
    assert 'Imagenes.crear_imagen(\n        "resultado"' in cuerpo
    assert '"resultadoComunidades"' not in cuerpo
    assert str(FORO_RESULTADOS_GENERAL_ID) == "1223765590146158653"
