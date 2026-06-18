from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from GestorSQL import (
    Base,
    ComunidadesComunidad,
    ComunidadesEnfrentamiento,
    ComunidadesEquipo,
    ComunidadesPartido,
    ComunidadesRonda,
    ComunidadesTorneo,
    Usuario,
)
from SpinConstantes import AMBITO_SPIN_COMUNIDADES
from UtilesDiscord import resolver_partido_spin_comunidades


def _session():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _activar_foreign_keys(dbapi_connection, _):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    return Session(engine), engine


def _crear_contexto(session: Session):
    ahora = datetime(2026, 7, 1, 20, 0)
    usuarios = [
        Usuario(idUsuarios=11, id_discord=101, nombre_discord="Local"),
        Usuario(idUsuarios=12, id_discord=102, nombre_discord="Local 2"),
        Usuario(idUsuarios=21, id_discord=201, nombre_discord="Visitante"),
        Usuario(idUsuarios=22, id_discord=202, nombre_discord="Visitante 2"),
    ]
    torneo = ComunidadesTorneo(
        nombre="Copa Spin",
        rondas_totales=3,
        fecha_fin_ronda1=ahora + timedelta(days=7),
        plantilla_mensaje_ronda1="Ronda 1",
        plantilla_mensaje_rondas_siguientes="Ronda {ronda}",
        creado_por_discord_id=999,
    )
    comunidad_a = ComunidadesComunidad(nombre="Comunidad A")
    comunidad_b = ComunidadesComunidad(nombre="Comunidad B")
    equipo_a = ComunidadesEquipo(nombre="Equipo A")
    equipo_b = ComunidadesEquipo(nombre="Equipo B")
    comunidad_a.equipos.append(equipo_a)
    comunidad_b.equipos.append(equipo_b)
    torneo.comunidades.extend([comunidad_a, comunidad_b])
    torneo.equipos.extend([equipo_a, equipo_b])
    ronda = ComunidadesRonda(
        numero=1,
        fecha_inicio=ahora,
        fecha_fin=ahora + timedelta(days=7),
        generada_por_discord_id=999,
    )
    torneo.rondas.append(ronda)
    session.add_all([*usuarios, torneo])
    session.flush()
    enfrentamiento = ComunidadesEnfrentamiento(
        torneo_id=torneo.id,
        ronda=ronda,
        mesa_numero=1,
        equipo_a=equipo_a,
        equipo_b=equipo_b,
    )
    session.add(enfrentamiento)
    session.flush()
    return usuarios, torneo, enfrentamiento, equipo_a, equipo_b, ahora


def _partido(torneo, enfrentamiento, equipo_a, equipo_b, local, visitante, *, indice, canal, fecha, estado="PENDIENTE", partido_bloodbowl_id=None):
    return ComunidadesPartido(
        torneo_id=torneo.id,
        enfrentamiento=enfrentamiento,
        indice=indice,
        equipo_local=equipo_a,
        equipo_visitante=equipo_b,
        usuario_local=local,
        usuario_visitante=visitante,
        atacante_usuario=local,
        defensor_usuario=visitante,
        canal_discord_id=canal,
        fecha=fecha,
        estado=estado,
        partido_bloodbowl_id=partido_bloodbowl_id,
    )


def test_resolver_partido_spin_comunidades_devuelve_spin_match_result_con_datos_necesarios():
    session, engine = _session()
    try:
        usuarios, torneo, enfrentamiento, equipo_a, equipo_b, ahora = _crear_contexto(session)
        lejano = _partido(torneo, enfrentamiento, equipo_a, equipo_b, usuarios[0], usuarios[2], indice=1, canal=901, fecha=ahora + timedelta(days=4))
        cercano = _partido(torneo, enfrentamiento, equipo_a, equipo_b, usuarios[1], usuarios[0], indice=2, canal=902, fecha=ahora + timedelta(days=1), estado="EN_CURSO")
        session.add_all([lejano, cercano])
        session.commit()

        resultado = resolver_partido_spin_comunidades(session, usuarios[0])

        assert resultado.ambito == AMBITO_SPIN_COMUNIDADES
        assert resultado.partido_id == cercano.id
        assert resultado.canal_partido_id == 902
        assert resultado.jugador1_discord_id == 102
        assert resultado.jugador2_discord_id == 101
        assert resultado.indice_partido == 2
        assert resultado.enfrentamiento_id == enfrentamiento.id
        assert resultado.torneo_id == torneo.id
        assert resultado.equipo_a_nombre == "Equipo A"
        assert resultado.equipo_b_nombre == "Equipo B"
        assert "partido individual 2" in resultado.descripcion_corta
        assert "Equipo A vs Equipo B" in resultado.descripcion_corta
    finally:
        session.close()
        engine.dispose()


def test_resolver_partido_spin_comunidades_filtra_no_elegibles():
    session, engine = _session()
    try:
        usuarios, torneo, enfrentamiento, equipo_a, equipo_b, ahora = _crear_contexto(session)
        session.add_all([
            _partido(torneo, enfrentamiento, equipo_a, equipo_b, usuarios[0], usuarios[2], indice=1, canal=None, fecha=ahora),
            _partido(torneo, enfrentamiento, equipo_a, equipo_b, usuarios[1], usuarios[3], indice=2, canal=902, fecha=ahora),
        ])
        session.commit()

        assert resolver_partido_spin_comunidades(session, usuarios[0]) is None
    finally:
        session.close()
        engine.dispose()


def test_resolver_partido_spin_delega_solo_en_general(monkeypatch):
    import UtilesDiscord
    from SpinConstantes import AMBITO_SPIN_GENERAL

    llamadas = []

    def resolver_general(session, usuario_db):
        llamadas.append("general")
        return "partido-general"

    def resolver_comunidades(session, usuario_db):
        llamadas.append("comunidades")
        return "partido-comunidades"

    monkeypatch.setattr(UtilesDiscord, "resolver_partido_spin_general", resolver_general)
    monkeypatch.setattr(UtilesDiscord, "resolver_partido_spin_comunidades", resolver_comunidades)

    assert UtilesDiscord.resolver_partido_spin(object(), object(), AMBITO_SPIN_GENERAL) == "partido-general"
    assert llamadas == ["general"]


def test_resolver_partido_spin_delega_solo_en_comunidades(monkeypatch):
    import UtilesDiscord

    llamadas = []

    def resolver_general(session, usuario_db):
        llamadas.append("general")
        return "partido-general"

    def resolver_comunidades(session, usuario_db):
        llamadas.append("comunidades")
        return "partido-comunidades"

    monkeypatch.setattr(UtilesDiscord, "resolver_partido_spin_general", resolver_general)
    monkeypatch.setattr(UtilesDiscord, "resolver_partido_spin_comunidades", resolver_comunidades)

    assert UtilesDiscord.resolver_partido_spin(object(), object(), "Comunidades") == "partido-comunidades"
    assert llamadas == ["comunidades"]


def test_resolver_partido_spin_rechaza_ambito_no_valido(monkeypatch):
    import pytest
    import UtilesDiscord

    def resolver_no_debe_llamarse(session, usuario_db):
        raise AssertionError("No debe consultar proveedores con un ámbito no válido")

    monkeypatch.setattr(UtilesDiscord, "resolver_partido_spin_general", resolver_no_debe_llamarse)
    monkeypatch.setattr(UtilesDiscord, "resolver_partido_spin_comunidades", resolver_no_debe_llamarse)

    with pytest.raises(ValueError, match="Ámbito de Spin no válido"):
        UtilesDiscord.resolver_partido_spin(object(), object(), "Ticket")


def test_spin_buttons_view_parametriza_custom_ids_por_ambito():
    import UtilesDiscord
    from SpinConstantes import AMBITO_SPIN_GENERAL, AMBITO_SPIN_COMUNIDADES

    vista_general = UtilesDiscord.SpinButtonsView(AMBITO_SPIN_GENERAL)
    vista_comunidades = UtilesDiscord.SpinButtonsView(AMBITO_SPIN_COMUNIDADES)

    ids_general = {boton.label: boton.custom_id for boton in vista_general.children}
    ids_comunidades = {boton.label: boton.custom_id for boton in vista_comunidades.children}

    assert vista_general.ambito == AMBITO_SPIN_GENERAL
    assert vista_comunidades.ambito == AMBITO_SPIN_COMUNIDADES
    assert ids_general == {
        "Spin": "lombardbot:spin:general",
        "Encontrado": "lombardbot:encontrado:general",
    }
    assert ids_comunidades == {
        "Spin": "lombardbot:spin:comunidades",
        "Encontrado": "lombardbot:encontrado:comunidades",
    }


def test_spin_buttons_view_no_usa_custom_ids_heredados():
    import UtilesDiscord
    from SpinConstantes import AMBITO_SPIN_GENERAL, AMBITO_SPIN_COMUNIDADES

    ids = {
        boton.custom_id
        for vista in (
            UtilesDiscord.SpinButtonsView(AMBITO_SPIN_GENERAL),
            UtilesDiscord.SpinButtonsView(AMBITO_SPIN_COMUNIDADES),
        )
        for boton in vista.children
    }

    assert "your_bot:spin" not in ids
    assert "your_bot:encontrado" not in ids
    assert ids == {
        "lombardbot:spin:general",
        "lombardbot:encontrado:general",
        "lombardbot:spin:comunidades",
        "lombardbot:encontrado:comunidades",
    }


def test_reservas_spin_arrancan_liberadas_tras_cargar_modulo():
    import importlib
    import UtilesDiscord
    from SpinConstantes import AMBITO_SPIN_GENERAL, AMBITO_SPIN_COMUNIDADES

    UtilesDiscord.reservas_spin[AMBITO_SPIN_GENERAL] = object()
    UtilesDiscord.reservas_spin[AMBITO_SPIN_COMUNIDADES] = object()

    UtilesDiscord = importlib.reload(UtilesDiscord)

    assert UtilesDiscord.obtener_reserva_spin(AMBITO_SPIN_GENERAL) is None
    assert UtilesDiscord.obtener_reserva_spin(AMBITO_SPIN_COMUNIDADES) is None


def test_reservas_spin_tienen_bloqueos_independientes_por_ambito():
    import UtilesDiscord
    from SpinConstantes import AMBITO_SPIN_GENERAL, AMBITO_SPIN_COMUNIDADES

    assert UtilesDiscord.obtener_bloqueo_reserva_spin(AMBITO_SPIN_GENERAL) is not UtilesDiscord.obtener_bloqueo_reserva_spin(AMBITO_SPIN_COMUNIDADES)


@pytest.mark.asyncio
async def test_spin_callback_con_reserva_activa_solo_responde_en_esa_cola(monkeypatch):
    from types import SimpleNamespace
    import UtilesDiscord
    from SpinConstantes import AMBITO_SPIN_GENERAL, AMBITO_SPIN_COMUNIDADES

    mensajes = []

    class Response:
        async def defer(self):
            pass

    class Followup:
        async def send(self, mensaje, *, ephemeral=False):
            mensajes.append((mensaje, ephemeral))

    UtilesDiscord.reservas_spin[AMBITO_SPIN_GENERAL] = object()
    UtilesDiscord.reservas_spin[AMBITO_SPIN_COMUNIDADES] = None
    monkeypatch.setattr(UtilesDiscord.GestorSQL, "conexionEngine", lambda: (_ for _ in ()).throw(AssertionError("No debe consultar la base de datos si la cola está reservada")))

    vista = UtilesDiscord.SpinButtonsView(AMBITO_SPIN_GENERAL)
    interaction = SimpleNamespace(
        response=Response(),
        followup=Followup(),
        user=SimpleNamespace(id=123, mention="<@123>", name="Usuario"),
    )

    try:
        await vista.spin_callback.callback(interaction)
    finally:
        UtilesDiscord.reservas_spin[AMBITO_SPIN_GENERAL] = None

    assert mensajes == [("Ya hay un usuario buscando partido en esta cola.", True)]
    assert UtilesDiscord.obtener_reserva_spin(AMBITO_SPIN_COMUNIDADES) is None

@pytest.mark.asyncio
async def test_encontrado_callback_libera_solo_reserva_del_ambito_de_la_vista(monkeypatch):
    from types import SimpleNamespace
    import UtilesDiscord
    from SpinConstantes import AMBITO_SPIN_GENERAL, AMBITO_SPIN_COMUNIDADES

    mensajes = []
    edits = []
    canales = []

    class Response:
        async def defer(self):
            pass

    class Followup:
        async def send(self, mensaje, *, ephemeral=False):
            mensajes.append((mensaje, ephemeral))

    class Message:
        async def edit(self, **kwargs):
            edits.append(kwargs)

    class Channel:
        def history(self, *, oldest_first=False, limit=1):
            async def iterator():
                yield Message()
            return iterator()

    class CanalPartido:
        async def send(self, mensaje):
            canales.append(mensaje)

    class TimeoutTask:
        def __init__(self):
            self.cancelled = False

        def cancel(self):
            self.cancelled = True

    monkeypatch.setattr(UtilesDiscord.Thread, "start", lambda self: None)
    timeout_general = TimeoutTask()
    timeout_comunidades = TimeoutTask()
    reserva_general = SimpleNamespace(
        ambito=AMBITO_SPIN_GENERAL,
        usuario_spin=SimpleNamespace(id=10),
        jugador1_discord_id=111,
        jugador2_discord_id=222,
        canal_spin=Channel(),
        canal_partido=CanalPartido(),
        descripcion_partido="General",
        timeout_task=timeout_general,
        partido=None,
    )
    reserva_comunidades = SimpleNamespace(
        ambito=AMBITO_SPIN_COMUNIDADES,
        usuario_spin=SimpleNamespace(id=30),
        jugador1_discord_id=333,
        jugador2_discord_id=444,
        canal_spin=Channel(),
        canal_partido=CanalPartido(),
        descripcion_partido="Comunidades",
        timeout_task=timeout_comunidades,
        partido=None,
    )
    UtilesDiscord.reservas_spin[AMBITO_SPIN_GENERAL] = reserva_general
    UtilesDiscord.reservas_spin[AMBITO_SPIN_COMUNIDADES] = reserva_comunidades

    interaction = SimpleNamespace(
        response=Response(),
        followup=Followup(),
        user=SimpleNamespace(id=333, name="JugadorComunidades"),
        message=Message(),
        channel=Channel(),
    )

    try:
        await UtilesDiscord.SpinButtonsView(AMBITO_SPIN_COMUNIDADES).encontrado_callback.callback(interaction)
        assert UtilesDiscord.obtener_reserva_spin(AMBITO_SPIN_GENERAL) is reserva_general
        assert UtilesDiscord.obtener_reserva_spin(AMBITO_SPIN_COMUNIDADES) is None
        assert timeout_comunidades.cancelled is True
        assert timeout_general.cancelled is False
        assert canales == ["El Spin Comunidades ha sido liberado."]
        assert mensajes == [("Has liberado el Spin Comunidades.", True)]
    finally:
        UtilesDiscord.reservas_spin[AMBITO_SPIN_GENERAL] = None
        UtilesDiscord.reservas_spin[AMBITO_SPIN_COMUNIDADES] = None


@pytest.mark.asyncio
async def test_encontrado_callback_rechaza_usuario_ajeno_sin_liberar_ningun_ambito(monkeypatch):
    from types import SimpleNamespace
    import UtilesDiscord
    from SpinConstantes import AMBITO_SPIN_GENERAL, AMBITO_SPIN_COMUNIDADES

    mensajes = []

    class Response:
        async def defer(self):
            pass

    class Followup:
        async def send(self, mensaje, *, ephemeral=False):
            mensajes.append((mensaje, ephemeral))

    reserva_general = SimpleNamespace(jugador1_discord_id=111, jugador2_discord_id=222, timeout_task=None, canal_partido=None)
    reserva_comunidades = SimpleNamespace(jugador1_discord_id=333, jugador2_discord_id=444, timeout_task=None, canal_partido=None)
    UtilesDiscord.reservas_spin[AMBITO_SPIN_GENERAL] = reserva_general
    UtilesDiscord.reservas_spin[AMBITO_SPIN_COMUNIDADES] = reserva_comunidades

    interaction = SimpleNamespace(
        response=Response(),
        followup=Followup(),
        user=SimpleNamespace(id=999, name="Intruso"),
    )

    try:
        await UtilesDiscord.SpinButtonsView(AMBITO_SPIN_GENERAL).encontrado_callback.callback(interaction)
        assert UtilesDiscord.obtener_reserva_spin(AMBITO_SPIN_GENERAL) is reserva_general
        assert UtilesDiscord.obtener_reserva_spin(AMBITO_SPIN_COMUNIDADES) is reserva_comunidades
        assert mensajes == [("Solo uno de los jugadores del partido reservado puede liberar este Spin.", True)]
    finally:
        UtilesDiscord.reservas_spin[AMBITO_SPIN_GENERAL] = None
        UtilesDiscord.reservas_spin[AMBITO_SPIN_COMUNIDADES] = None
