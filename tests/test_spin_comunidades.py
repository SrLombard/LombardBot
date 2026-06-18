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


def test_ayuda_agregar_mensaje_spin_exige_ambito_explicito():
    from SpinConstantes import ayuda_agregar_mensaje_spin

    ayuda = ayuda_agregar_mensaje_spin()

    assert "Uso: `!AgregarMensajeSpin <ámbito>`" in ayuda
    assert "`!AgregarMensajeSpin General`" in ayuda
    assert "`!AgregarMensajeSpin Comunidades`" in ayuda
    assert "equivale a `General`" not in ayuda


def test_mensaje_spin_libre_centraliza_textos_por_ambito():
    from SpinConstantes import (
        AMBITO_SPIN_COMUNIDADES,
        AMBITO_SPIN_GENERAL,
        MENSAJES_SPIN_LIBRE,
        mensaje_spin_libre,
    )

    assert MENSAJES_SPIN_LIBRE == {
        AMBITO_SPIN_GENERAL: "El Spin General está **LIBRE**",
        AMBITO_SPIN_COMUNIDADES: "El Spin Comunidades está **LIBRE**",
    }
    assert mensaje_spin_libre("General") == MENSAJES_SPIN_LIBRE[AMBITO_SPIN_GENERAL]
    assert mensaje_spin_libre("COMUNIDADES") == MENSAJES_SPIN_LIBRE[AMBITO_SPIN_COMUNIDADES]


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

@pytest.mark.asyncio
async def test_encontrado_callback_permita_liberar_al_rival_que_no_inicio_el_spin(monkeypatch):
    from types import SimpleNamespace
    import UtilesDiscord
    from SpinConstantes import AMBITO_SPIN_GENERAL

    mensajes = []
    canales = []

    class Response:
        async def defer(self):
            pass

    class Followup:
        async def send(self, mensaje, *, ephemeral=False):
            mensajes.append((mensaje, ephemeral))

    class Message:
        async def edit(self, **kwargs):
            pass

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
    timeout = TimeoutTask()
    reserva = SimpleNamespace(
        ambito=AMBITO_SPIN_GENERAL,
        usuario_spin=SimpleNamespace(id=111),
        jugador1_discord_id=111,
        jugador2_discord_id=222,
        canal_spin=Channel(),
        canal_partido=CanalPartido(),
        descripcion_partido="General",
        timeout_task=timeout,
        partido=None,
    )
    UtilesDiscord.reservas_spin[AMBITO_SPIN_GENERAL] = reserva

    interaction = SimpleNamespace(
        response=Response(),
        followup=Followup(),
        user=SimpleNamespace(id=222, name="Rival"),
        message=Message(),
        channel=Channel(),
    )

    try:
        await UtilesDiscord.SpinButtonsView(AMBITO_SPIN_GENERAL).encontrado_callback.callback(interaction)
        assert UtilesDiscord.obtener_reserva_spin(AMBITO_SPIN_GENERAL) is None
        assert timeout.cancelled is True
        assert canales == ["El Spin General ha sido liberado."]
        assert mensajes == [("Has liberado el Spin General.", True)]
    finally:
        UtilesDiscord.reservas_spin[AMBITO_SPIN_GENERAL] = None

@pytest.mark.asyncio
async def test_encontrado_callback_libera_estado_aunque_no_exista_mensaje_principal(monkeypatch):
    from types import SimpleNamespace
    import UtilesDiscord
    from SpinConstantes import AMBITO_SPIN_GENERAL

    mensajes = []

    class Response:
        async def defer(self):
            pass

    class Followup:
        async def send(self, mensaje, *, ephemeral=False):
            mensajes.append((mensaje, ephemeral))

    class ChannelSinMensajes:
        def history(self, *, oldest_first=False, limit=1):
            async def iterator():
                if False:
                    yield None
            return iterator()

    class TimeoutTask:
        def __init__(self):
            self.cancelled = False

        def cancel(self):
            self.cancelled = True

    monkeypatch.setattr(UtilesDiscord.Thread, "start", lambda self: None)
    timeout = TimeoutTask()
    reserva = SimpleNamespace(
        ambito=AMBITO_SPIN_GENERAL,
        usuario_spin=SimpleNamespace(id=111),
        jugador1_discord_id=111,
        jugador2_discord_id=222,
        canal_spin=ChannelSinMensajes(),
        canal_partido=None,
        descripcion_partido="General",
        timeout_task=timeout,
        partido=None,
    )
    UtilesDiscord.reservas_spin[AMBITO_SPIN_GENERAL] = reserva

    interaction = SimpleNamespace(
        response=Response(),
        followup=Followup(),
        user=SimpleNamespace(id=111, name="Jugador"),
        channel=ChannelSinMensajes(),
    )

    try:
        await UtilesDiscord.SpinButtonsView(AMBITO_SPIN_GENERAL).encontrado_callback.callback(interaction)
        assert UtilesDiscord.obtener_reserva_spin(AMBITO_SPIN_GENERAL) is None
        assert timeout.cancelled is True
        assert mensajes == [("Has liberado el Spin General.", True)]
    finally:
        UtilesDiscord.reservas_spin[AMBITO_SPIN_GENERAL] = None


@pytest.mark.asyncio
async def test_encontrado_callback_no_hace_excepcion_por_admin_ni_comisario(monkeypatch):
    from types import SimpleNamespace
    import UtilesDiscord
    from SpinConstantes import AMBITO_SPIN_GENERAL

    mensajes = []

    class Response:
        async def defer(self):
            pass

    class Followup:
        async def send(self, mensaje, *, ephemeral=False):
            mensajes.append((mensaje, ephemeral))

    admin_permissions = SimpleNamespace(administrator=True)
    rol_comisario = SimpleNamespace(name="Comisario")
    reserva = SimpleNamespace(jugador1_discord_id=111, jugador2_discord_id=222, timeout_task=None, canal_partido=None)
    UtilesDiscord.reservas_spin[AMBITO_SPIN_GENERAL] = reserva

    interaction = SimpleNamespace(
        response=Response(),
        followup=Followup(),
        user=SimpleNamespace(id=999, name="Admin", guild_permissions=admin_permissions, roles=[rol_comisario]),
    )

    try:
        await UtilesDiscord.SpinButtonsView(AMBITO_SPIN_GENERAL).encontrado_callback.callback(interaction)
        assert UtilesDiscord.obtener_reserva_spin(AMBITO_SPIN_GENERAL) is reserva
        assert mensajes == [("Solo uno de los jugadores del partido reservado puede liberar este Spin.", True)]
    finally:
        UtilesDiscord.reservas_spin[AMBITO_SPIN_GENERAL] = None

@pytest.mark.asyncio
async def test_timeout_libera_solo_la_reserva_exacta_de_su_ambito(monkeypatch):
    from types import SimpleNamespace
    import UtilesDiscord
    from SpinConstantes import AMBITO_SPIN_GENERAL, AMBITO_SPIN_COMUNIDADES

    mensajes_canal = []
    dms = []
    edits = []

    async def sleep_inmediato(segundos):
        assert segundos == 300

    class CanalPartido:
        async def send(self, mensaje):
            mensajes_canal.append(mensaje)

    class User:
        def __init__(self, id):
            self.id = id

        async def send(self, mensaje):
            dms.append((self.id, mensaje))

    class Message:
        async def edit(self, **kwargs):
            edits.append(kwargs)

    class Channel:
        def history(self, *, oldest_first=False, limit=1):
            async def iterator():
                yield Message()
            return iterator()

    monkeypatch.setattr(UtilesDiscord.asyncio, "sleep", sleep_inmediato)
    monkeypatch.setattr(UtilesDiscord.Thread, "start", lambda self: None)

    reserva_general = SimpleNamespace(
        ambito=AMBITO_SPIN_GENERAL,
        usuario_spin=User(10),
        jugador1_discord_id=111,
        jugador2_discord_id=222,
        canal_spin=Channel(),
        canal_partido=CanalPartido(),
        timeout_task=None,
    )
    reserva_comunidades = SimpleNamespace(
        ambito=AMBITO_SPIN_COMUNIDADES,
        usuario_spin=User(20),
        jugador1_discord_id=333,
        jugador2_discord_id=444,
        canal_spin=Channel(),
        canal_partido=CanalPartido(),
        timeout_task=None,
    )
    UtilesDiscord.reservas_spin[AMBITO_SPIN_GENERAL] = reserva_general
    UtilesDiscord.reservas_spin[AMBITO_SPIN_COMUNIDADES] = reserva_comunidades

    try:
        await UtilesDiscord.SpinButtonsView(AMBITO_SPIN_GENERAL).auto_release_spin(reserva_general, Message())

        assert UtilesDiscord.obtener_reserva_spin(AMBITO_SPIN_GENERAL) is None
        assert UtilesDiscord.obtener_reserva_spin(AMBITO_SPIN_COMUNIDADES) is reserva_comunidades
        assert mensajes_canal == ["El Spin General ha sido liberado automáticamente. 😡 Afortunadamente las máquinas somos superiores y cuidamos de los esmirriados humanos."]
        assert dms == [(10, 'Tu spin ha sido liberado automáticamente debido a la inactividad.')]
        assert any(edit.get("content") == "El Spin General está **LIBRE**" for edit in edits)
    finally:
        UtilesDiscord.reservas_spin[AMBITO_SPIN_GENERAL] = None
        UtilesDiscord.reservas_spin[AMBITO_SPIN_COMUNIDADES] = None


@pytest.mark.asyncio
async def test_timeout_antiguo_no_libera_reserva_nueva_del_mismo_ambito(monkeypatch):
    from types import SimpleNamespace
    import UtilesDiscord
    from SpinConstantes import AMBITO_SPIN_GENERAL

    mensajes_canal = []

    async def sleep_inmediato(segundos):
        assert segundos == 300

    class CanalPartido:
        async def send(self, mensaje):
            mensajes_canal.append(mensaje)

    monkeypatch.setattr(UtilesDiscord.asyncio, "sleep", sleep_inmediato)
    monkeypatch.setattr(UtilesDiscord.Thread, "start", lambda self: None)

    reserva_antigua = SimpleNamespace(
        ambito=AMBITO_SPIN_GENERAL,
        usuario_spin=SimpleNamespace(id=10),
        canal_spin=None,
        canal_partido=CanalPartido(),
    )
    reserva_nueva = SimpleNamespace(
        ambito=AMBITO_SPIN_GENERAL,
        usuario_spin=SimpleNamespace(id=10),
        canal_spin=None,
        canal_partido=CanalPartido(),
    )
    UtilesDiscord.reservas_spin[AMBITO_SPIN_GENERAL] = reserva_nueva

    try:
        await UtilesDiscord.SpinButtonsView(AMBITO_SPIN_GENERAL).auto_release_spin(reserva_antigua)

        assert UtilesDiscord.obtener_reserva_spin(AMBITO_SPIN_GENERAL) is reserva_nueva
        assert mensajes_canal == []
    finally:
        UtilesDiscord.reservas_spin[AMBITO_SPIN_GENERAL] = None


def test_mensaje_spin_reservado_se_construye_desde_spin_match_result():
    from SpinConstantes import AMBITO_SPIN_GENERAL
    from UtilesDiscord import SpinMatchResult, mensaje_spin_reservado

    resultado = SpinMatchResult(
        ambito=AMBITO_SPIN_GENERAL,
        canal_partido_id=900,
        jugador1_discord_id=101,
        jugador2_discord_id=201,
        fecha=None,
    )

    assert mensaje_spin_reservado(resultado) == "Spin General reservado: <@101> y <@201> pueden buscar partido."


def test_mensaje_spin_reservado_comunidades_usa_contexto_o_fallback():
    from SpinConstantes import AMBITO_SPIN_COMUNIDADES
    from UtilesDiscord import SpinMatchResult, mensaje_spin_reservado

    completo = SpinMatchResult(
        ambito=AMBITO_SPIN_COMUNIDADES,
        canal_partido_id=902,
        jugador1_discord_id=102,
        jugador2_discord_id=101,
        fecha=None,
        indice_partido=2,
        equipo_a_nombre="Equipo A",
        equipo_b_nombre="Equipo B",
    )
    incompleto = SpinMatchResult(
        ambito=AMBITO_SPIN_COMUNIDADES,
        canal_partido_id=902,
        jugador1_discord_id=102,
        jugador2_discord_id=101,
        fecha=None,
        indice_partido=2,
        equipo_a_nombre="Equipo A",
    )

    assert mensaje_spin_reservado(completo) == (
        "Spin de comunidades reservado para el partido individual 2 "
        "del enfrentamiento Equipo A vs Equipo B: <@102> y <@101> pueden buscar partido."
    )
    assert mensaje_spin_reservado(incompleto) == "Spin de comunidades reservado: <@102> y <@101> pueden buscar partido."
    assert "None" not in mensaje_spin_reservado(incompleto)
