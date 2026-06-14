from datetime import datetime
from types import SimpleNamespace

from ComunidadesDiscord import (
    etiqueta_equipo_comunidades,
    mensajes_canal_enfrentamiento_comunidades,
)


def _usuario(discord_id, nombre_bloodbowl, preferencia=None, raza_usuario="Incorrecta"):
    preferencias_fecha = (
        SimpleNamespace(preferencia=preferencia) if preferencia is not None else None
    )
    return SimpleNamespace(
        id_discord=discord_id,
        nombre_bloodbowl=nombre_bloodbowl,
        nombre_discord=f"Discord {discord_id}",
        preferencias_fecha=preferencias_fecha,
        raza=raza_usuario,
    )


def _equipo(equipo_id, nombre, comunidad, miembros):
    return SimpleNamespace(
        id=equipo_id,
        nombre=nombre,
        comunidad=SimpleNamespace(nombre=comunidad),
        miembros=miembros,
    )


def _enfrentamiento():
    equipo_a = _equipo(
        1,
        "Valientes",
        "Butter",
        [
            SimpleNamespace(
                posicion=2,
                raza="Skaven",
                usuario=_usuario(102, "RataBB"),
            ),
            SimpleNamespace(
                posicion=1,
                raza="Orcos",
                usuario=_usuario(101, "OrcoBB", "laborables desde las 20:00"),
            ),
        ],
    )
    equipo_b = _equipo(
        2,
        "Nocturnos",
        "Hispana",
        [
            SimpleNamespace(
                posicion=1,
                raza="Humanos",
                usuario=_usuario(201, "HumanoBB", "fines de semana"),
            ),
            SimpleNamespace(
                posicion=2,
                raza="Enanos",
                usuario=_usuario(202, "EnanoBB", "   "),
            ),
        ],
    )
    return SimpleNamespace(
        mesa_numero=3,
        equipo_a=equipo_a,
        equipo_b=equipo_b,
        equipo_a_id=1,
        equipo_b_id=2,
        fotografias_estado=[
            SimpleNamespace(equipo_id=1, es_zombie=False, estado_temporal="NEUTRO"),
            SimpleNamespace(equipo_id=2, es_zombie=True, estado_temporal="HERIDO"),
        ],
    )


def test_etiqueta_equipo_antepone_la_comunidad_entre_corchetes():
    equipo = _equipo(1, "Equipo @A", "Comunidad @B", [])

    assert etiqueta_equipo_comunidades(equipo) == (
        "[Comunidad @\u200bB] Equipo @\u200bA"
    )


def test_mensaje_general_muestra_datos_del_torneo_y_preferencias_despues_de_jugadores():
    torneo = SimpleNamespace(
        plantilla_mensaje_ronda1="Aviso de primera ronda",
        plantilla_mensaje_rondas_siguientes="Aviso posterior",
    )
    ronda = SimpleNamespace(numero=1, fecha_fin=datetime(2026, 7, 8, 22, 0))

    general, adicional = mensajes_canal_enfrentamiento_comunidades(
        torneo, ronda, _enfrentamiento()
    )

    assert "## Mesa 3: [Butter] Valientes vs [Hispana] Nocturnos" in general
    assert "- <@101> — **OrcoBB** — Orcos" in general
    assert "- <@102> — **RataBB** — Skaven" in general
    assert "Incorrecta" not in general
    assert general.index("<@101> — **OrcoBB**") < general.index("### Preferencias horarias")
    assert "<@101> suele poder jugar laborables desde las 20:00" in general
    assert "<@201> suele poder jugar fines de semana" in general
    assert "<@202> suele poder jugar" not in general
    assert adicional == "Aviso de primera ronda"


def test_plantilla_vacia_no_genera_mensaje_adicional():
    torneo = SimpleNamespace(
        plantilla_mensaje_ronda1="Aviso inicial",
        plantilla_mensaje_rondas_siguientes="   ",
    )
    ronda = SimpleNamespace(numero=2, fecha_fin=datetime(2026, 7, 15, 22, 0))

    general, adicional = mensajes_canal_enfrentamiento_comunidades(
        torneo, ronda, _enfrentamiento()
    )

    assert general.startswith("## Mesa 3:")
    assert adicional is None
