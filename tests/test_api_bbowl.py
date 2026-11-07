from __future__ import annotations

import ast
import asyncio
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy import and_, create_engine, or_
from sqlalchemy.orm import Session

import APIBbowl
import GestorSQL


@pytest.fixture
def respuesta_api():
    # Estadísticas reales de la respuesta de noviembre de 2026, sin URLs ni claves.
    ruta = Path(__file__).parent / 'fixtures' / 'bb3_matches_strings.json'
    return json.loads(ruta.read_text(encoding='utf-8'))


def simular_api(monkeypatch, respuesta, status=200):
    get = Mock(return_value=SimpleNamespace(
        status_code=status, json=lambda: deepcopy(respuesta)
    ))
    monkeypatch.setattr(APIBbowl.requests, 'get', get)
    return get


@pytest.mark.parametrize('formato', ['texto', 'enteros', 'mixto'])
@pytest.mark.parametrize('local_index', [0, 1])
def test_actualizar_clasificacion_calcula_y_guarda_estadisticas(
    monkeypatch, respuesta_api, formato, local_index
):
    if formato != 'texto':
        for indice, equipo in enumerate(respuesta_api['matches'][0]['teams']):
            if formato == 'enteros' or indice == 0:
                for campo, valor in equipo.items():
                    if campo in APIBbowl._CAMPOS_ENTEROS_EQUIPO:
                        equipo[campo] = int(valor)
    simular_api(monkeypatch, respuesta_api)

    # Carga la función real sin arrancar el bot ni conectar con Discord/MySQL.
    ruta_bot = Path(__file__).resolve().parents[1] / 'LombardBot.py'
    modulo = ast.parse(ruta_bot.read_text(encoding='utf-8'))
    nodo = next(n for n in modulo.body if isinstance(n, ast.AsyncFunctionDef)
                and n.name == 'actualizar_clasificacion')
    discord = SimpleNamespace(
        publicar=AsyncMock(), gestionar_canal_discord=AsyncMock(),
        mensaje_administradores=AsyncMock(),
    )
    entorno = {'GestorSQL': GestorSQL, 'and_': and_, 'or_': or_,
               'UtilesDiscord': discord}
    exec(compile(ast.Module(body=[nodo], type_ignores=[]), str(ruta_bot), 'exec'), entorno)

    engine = create_engine('sqlite://')
    GestorSQL.Base.metadata.create_all(engine)
    try:
        with Session(engine, expire_on_commit=False) as session:
            usuarios = [GestorSQL.Usuario(
                id_bloodbowl=f'coach-{i}', nombre_discord=f'Coach {i}', jornada_actual=1
            ) for i in range(2)]
            session.add_all(usuarios)
            session.flush()
            calendario = GestorSQL.Calendario(
                usuario_coach1=usuarios[local_index],
                usuario_coach2=usuarios[1 - local_index],
                jornada=1, canalAsociado=123,
            )
            session.add(calendario)
            session.commit()

            resultado = asyncio.run(entorno['actualizar_clasificacion'](
                None, session,
                lambda: APIBbowl.obtener_partido_ButterCup('token-prueba'),
                GestorSQL.Calendario, 456, todos=1,
            ))

            assert resultado == 'Actualización completada.'
            partido = session.query(GestorSQL.Partidos).one()
            # Se mantiene el cálculo existente: bajas causadas por el rival menos muertes.
            esperados = {
                'resultado': (2, 1), 'lesiones': (3, 1), 'muertes': (1, 0),
                'pases': (0, 1), 'catches': (1, 3), 'interceptions': (0, 0),
                'ko': (1, 4), 'push': (0, 0), 'mRun': (44, 25), 'mPass': (0, 5),
            }
            for campo, valores in esperados.items():
                for lado, indice in ((1, local_index), (2, 1 - local_index)):
                    valor = getattr(partido, f'{campo}{lado}')
                    assert valor == valores[indice], f'{campo}{lado}'
                    assert type(valor) is int
            assert partido.idPartidoBbowl == 'partido-prueba'
            assert calendario.partidos_idPartidos == partido.idPartidos
            assert [u.jornada_actual for u in usuarios] == [2, 2]
            discord.publicar.assert_awaited_once()
            discord.gestionar_canal_discord.assert_awaited_once_with(
                None, 'eliminar', canal_id=123
            )
            discord.mensaje_administradores.assert_not_awaited()
    finally:
        engine.dispose()


def test_consulta_uuid_normaliza_estadisticas_y_conserva_metadatos(monkeypatch, respuesta_api):
    match = respuesta_api['matches'][0]
    match['teams'][0]['inflictedinterceptions'] = None
    respuesta = {'match': match, 'coaches': [{'id': 'coach-0'}],
                 'teams': [{'id': 'equipo-0', 'idcoach': 'coach-0'}]}
    original = deepcopy(respuesta)
    simular_api(monkeypatch, respuesta)

    partido = APIBbowl.obtener_partido_por_uuid('token-prueba', 'partido-prueba')

    assert partido['teams'][0]['sustaineddead'] == 1
    assert partido['teams'][1]['inflictedmeterspassing'] == 5
    assert partido['teams'][0]['inflictedinterceptions'] is None
    assert partido['coaches_info'] == respuesta['coaches']
    assert partido['teams_info'] == respuesta['teams']
    assert partido['teams'][0]['idteamlisting'] == 'equipo-0'
    assert partido['teams'][0]['idraces'] == match['teams'][0]['idraces']
    assert partido['teams'][0]['nbsupporters'] == match['teams'][0]['nbsupporters']
    assert respuesta == original


@pytest.mark.parametrize('valor', ['', 'desconocido', '1.5'])
def test_estadistica_invalida_no_se_convierte_en_cero(monkeypatch, respuesta_api, valor):
    respuesta_api['matches'][0]['teams'][1]['score'] = valor
    simular_api(monkeypatch, respuesta_api)

    with pytest.raises(ValueError, match=r'partido-prueba: teams\[1\].score'):
        APIBbowl.obtener_partidos('token-prueba', 'competicion-prueba')


def test_consulta_sin_partidos(monkeypatch):
    simular_api(monkeypatch, {'matches': []})
    assert APIBbowl.obtener_partidos('token-prueba', 'competicion-prueba') == []


def test_error_http_conserva_resultado_none(monkeypatch):
    simular_api(monkeypatch, {}, status=503)
    assert APIBbowl.obtener_partidos('token-prueba', 'competicion-prueba') is None
    assert APIBbowl.obtener_partido_por_uuid('token-prueba', 'partido-prueba') is None
