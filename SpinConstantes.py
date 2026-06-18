"""Constantes y normalización para la mecánica Spin.

Según ``logicaSpin.md``, los ámbitos internos soportados son exactamente
``GENERAL`` y ``COMUNIDADES``. Los textos visibles para usuarios se normalizan
antes de usarse en la lógica o persistirse.
"""

from enum import Enum
import unicodedata
from datetime import datetime
from zoneinfo import ZoneInfo


class AmbitoSpin(str, Enum):
    """Ámbitos internos canónicos de Spin."""

    GENERAL = "GENERAL"
    COMUNIDADES = "COMUNIDADES"


AMBITO_SPIN_GENERAL = AmbitoSpin.GENERAL.value
AMBITO_SPIN_COMUNIDADES = AmbitoSpin.COMUNIDADES.value
AMBITOS_SPIN = frozenset(ambito.value for ambito in AmbitoSpin)
AMBITO_SPIN_TODOS = "TODOS"
TIPO_SPIN = "Spin"
TIPO_SPIN_ENCONTRADO = "Encontrado"
TIPO_SPIN_AUTO_RELEASE = "AutoRelease"
TIPO_SPIN_ADMIN_RELEASE = "LiberacionAdmin"

MENSAJES_SPIN_LIBRE = {
    AMBITO_SPIN_GENERAL: "El Spin General está **LIBRE**",
    AMBITO_SPIN_COMUNIDADES: "El Spin Comunidades está **LIBRE**",
}

MENSAJES_CANAL_PARTIDO_LIBERACION_MANUAL = {
    AMBITO_SPIN_GENERAL: "El Spin General ha sido liberado.",
    AMBITO_SPIN_COMUNIDADES: "El Spin Comunidades ha sido liberado.",
}

MENSAJES_CANAL_PARTIDO_LIBERACION_AUTOMATICA = {
    AMBITO_SPIN_GENERAL: (
        "El Spin General ha sido liberado automáticamente. 😡 Afortunadamente "
        "las máquinas somos superiores y cuidamos de los esmirriados humanos."
    ),
    AMBITO_SPIN_COMUNIDADES: (
        "El Spin Comunidades ha sido liberado automáticamente. 😡 La comunidad "
        "ha sobrevivido a otro intento fallido de coordinación humana."
    ),
}


AYUDA_AGREGAR_MENSAJE_SPIN = (
    "Uso: `!AgregarMensajeSpin <ámbito>`\n"
    "Ámbitos válidos: `General` y `Comunidades`.\n"
    "Ejemplos:\n"
    "`!AgregarMensajeSpin General`\n"
    "`!AgregarMensajeSpin Comunidades`"
)


def ayuda_agregar_mensaje_spin():
    """Devuelve la ayuda de uso del comando de creación de mensajes Spin.

    ``logicaSpin.md`` exige que el comando reciba explícitamente el ámbito y
    valide los valores ``General`` y ``Comunidades`` para evitar mensajes
    ambiguos. Omitir el ámbito no asume ningún valor por defecto.
    """

    return AYUDA_AGREGAR_MENSAJE_SPIN


def mensaje_spin_libre(ambito):
    """Devuelve el texto canónico de cola libre para el ámbito indicado.

    ``logicaSpin.md`` define estos textos como fuente de verdad para crear
    mensajes de Spin y para actualizar el mensaje principal al liberar
    reservas.
    """

    ambito_normalizado = normalizar_ambito_spin(ambito)
    if not ambito_normalizado:
        raise ValueError(f"Ámbito de Spin no válido: {ambito!r}")
    return MENSAJES_SPIN_LIBRE[ambito_normalizado]


def mensaje_canal_partido_liberacion_manual(ambito):
    """Devuelve el texto canónico al liberar manualmente una reserva.

    En Spin General este texto no menciona comunidades porque ``logicaSpin.md``
    separa los ámbitos y define un mensaje claro para el canal del partido
    general.
    """

    ambito_normalizado = normalizar_ambito_spin(ambito)
    if not ambito_normalizado:
        raise ValueError(f"Ámbito de Spin no válido: {ambito!r}")
    return MENSAJES_CANAL_PARTIDO_LIBERACION_MANUAL[ambito_normalizado]


def mensaje_canal_partido_liberacion_automatica(ambito):
    """Devuelve el texto humorístico canónico al liberar por timeout."""

    ambito_normalizado = normalizar_ambito_spin(ambito)
    if not ambito_normalizado:
        raise ValueError(f"Ámbito de Spin no válido: {ambito!r}")
    return MENSAJES_CANAL_PARTIDO_LIBERACION_AUTOMATICA[ambito_normalizado]

# Canal actual de Spin General; se conserva para compatibilidad operativa.
CANAL_SPIN_GENERAL_ID = 1224128423929315468
# Canal independiente para Spin Comunidades. Configurar el ID real al activarlo.
CANAL_SPIN_COMUNIDADES_ID = None
# El mensaje público que se edita es el primer mensaje del canal, no un ID persistido.

_TEXTOS_AMBITO_SPIN = {
    "general": AMBITO_SPIN_GENERAL,
    "comunidades": AMBITO_SPIN_COMUNIDADES,
}
_TEXTOS_AMBITO_SPIN_TODOS = {
    **_TEXTOS_AMBITO_SPIN,
    "todos": AMBITO_SPIN_TODOS,
}


def _normalizar_texto_ambito(texto):
    texto = str(texto or "").strip()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto.casefold()


def normalizar_ambito_spin(texto, *, permitir_todos=False):
    """Convierte textos de usuario a ámbitos internos de Spin.

    Acepta los textos visibles ``General``, ``Comunidades`` y, cuando
    ``permitir_todos`` es verdadero, ``Todos``. También acepta directamente los
    valores internos ``GENERAL`` y ``COMUNIDADES``.
    """

    opciones = _TEXTOS_AMBITO_SPIN_TODOS if permitir_todos else _TEXTOS_AMBITO_SPIN
    return opciones.get(_normalizar_texto_ambito(texto))


def formatear_linea_historial_spin(fecha, usuario, tipo, ambito):
    """Devuelve una línea no ambigua para el historial de ``/ultimosspins``.

    ``logicaSpin.md`` recomienda que cada registro visible incluya el ámbito
    incluso cuando la consulta ya esté filtrada por ``General`` o
    ``Comunidades``. El formato mantiene la lectura compacta heredada:
    ``[GENERAL] Usuario - Spin - fecha``.
    """

    ambito_normalizado = normalizar_ambito_spin(ambito) or AMBITO_SPIN_GENERAL
    if isinstance(fecha, datetime):
        fecha_madrid = (
            fecha.replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo("Europe/Madrid"))
            if fecha.tzinfo is None
            else fecha.astimezone(ZoneInfo("Europe/Madrid"))
        )
        fecha_texto = fecha_madrid.strftime("%Y-%m-%d %H:%M:%S")
    else:
        fecha_texto = str(fecha)
    return f"[{ambito_normalizado}] {usuario} - {tipo} - {fecha_texto}"


def formatear_historial_spins(registros):
    """Formatea registros de Spin como bloque de líneas con ámbito explícito."""

    lineas = ["Historial de Spin (Europe/Madrid)"]
    for fecha, usuario, tipo, ambito in registros:
        lineas.append(formatear_linea_historial_spin(fecha, usuario, tipo, ambito))
    return "```" + "\n".join(lineas) + "```"


def normalizar_filtro_historial_spin(texto):
    """Normaliza el filtro de ámbito de ``/ultimosspins``.

    ``logicaSpin.md`` define que el valor de usuario ``Todos`` no debe aplicar
    filtro de ámbito, mientras que ``General`` y ``Comunidades`` deben
    convertirse a los valores canónicos persistidos en el historial.
    """

    ambito = normalizar_ambito_spin(texto, permitir_todos=True)
    if ambito == AMBITO_SPIN_TODOS:
        return None
    return ambito
