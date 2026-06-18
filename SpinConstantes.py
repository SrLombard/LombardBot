"""Constantes y normalización para la mecánica Spin.

Según ``logicaSpin.md``, los ámbitos internos soportados son exactamente
``GENERAL`` y ``COMUNIDADES``. Los textos visibles para usuarios se normalizan
antes de usarse en la lógica o persistirse.
"""

from enum import Enum
import unicodedata


class AmbitoSpin(str, Enum):
    """Ámbitos internos canónicos de Spin."""

    GENERAL = "GENERAL"
    COMUNIDADES = "COMUNIDADES"


AMBITO_SPIN_GENERAL = AmbitoSpin.GENERAL.value
AMBITO_SPIN_COMUNIDADES = AmbitoSpin.COMUNIDADES.value
AMBITOS_SPIN = frozenset(ambito.value for ambito in AmbitoSpin)
AMBITO_SPIN_TODOS = "TODOS"

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
