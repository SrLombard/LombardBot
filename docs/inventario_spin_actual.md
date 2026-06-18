# Inventario actual de Spin

Fuente de verdad para la lógica objetivo: [`logicaSpin.md`](../logicaSpin.md).

Este inventario solo documenta el estado actual del código antes de modificar lógica. No cambia comportamiento.

## Referencias buscadas

Se buscaron estas referencias explícitas:

- `SpinButtonsView`
- `UsuarioSpin`
- `AgregarMensajeSpin`
- `ultimosspins`
- `your_bot:spin`
- `your_bot:encontrado`

## Resumen por responsabilidad

| Responsabilidad | Archivo(s) actuales | Observaciones |
| --- | --- | --- |
| Vista de botones | `UtilesDiscord.py`, `ComandosAntiguos.py`, uso en `LombardBot.py` | La vista activa parece ser `UtilesDiscord.SpinButtonsView`; `ComandosAntiguos.py` conserva una versión antigua. |
| Estado global | `UtilesDiscord.py`, referencias antiguas en `ComandosAntiguos.py` | `UsuarioSpin` es una única cola global; ya no se mantiene un ID fijo del mensaje de Spin como fuente de verdad. |
| Creación de mensaje de Spin | `LombardBot.py` | Comando prefijado `!AgregaMensajeSpin`, sin argumento de ámbito. |
| Comando `/ultimosspins` | `LombardBot.py` | Slash command con argumento `minutos`; no filtra por ámbito. |
| Inserciones en tabla `Spin` | `UtilesDiscord.py`, `GestorSQL.py`, versión antigua en `ComandosAntiguos.py` | `GestorSQL.insertar_spin(usuario, fecha, tipo)` inserta `user`, `fecha`, `tipo`; no existe `ambito`. |
| Configuración de canal o mensaje | `UtilesDiscord.py`, `LombardBot.py`, menciones de texto en `UtilesDiscord.py` | Existen constantes separadas para canal Spin General/Comunidades. El estado público del Spin se edita tomando el primer mensaje del canal. |

## Detalle por archivo

### `UtilesDiscord.py`

- Define el estado global actual: `UsuarioSpin = None`.
- Define `SpinButtonsView`, la vista persistente actual con `timeout=None`.
- Dentro de la vista almacena estado de instancia: `spin_timeout_task`, `canal` y `canal_partido`.
- El botón `Spin` usa `custom_id='your_bot:spin'`.
- El botón `Encontrado` usa `custom_id='your_bot:encontrado'`.
- `spin_callback` usa una única cola global (`UsuarioSpin`) y busca partidos generales en:
  - `Calendario`;
  - `PlayOffsOro`;
  - `PlayOffsPlata`;
  - `PlayOffsBronce`;
  - `Ticket`;
  - `SuizoEmparejamiento`.
- `spin_callback` envía mensaje al canal del partido, deshabilita/habilita botones, edita el primer mensaje del canal y registra `tipo='Spin'`.
- `encontrado_callback` solo libera si pulsa el mismo usuario guardado en `UsuarioSpin`, edita el primer mensaje a libre y registra `tipo='Encontrado'`.
- `auto_release_spin` libera tras 300 segundos, envía mensaje al canal del partido, DM al usuario, edita botones/primer mensaje y registra `tipo='Encontrado'` con usuario `LOMBARDBOT`.
- Los textos de creación de canales referencian `CANAL_SPIN_GENERAL_ID` para mantener compatibilidad con el canal actual.

### `LombardBot.py`

- En `on_ready`, registra la vista persistente con `bot.add_view(UtilesDiscord.SpinButtonsView())`.
- El comando `!AgregarVista` añade `UtilesDiscord.SpinButtonsView()` a un mensaje existente.
- El comando prefijado `!AgregaMensajeSpin` crea el mensaje de Spin actual:
  - envía el texto libre `"'El spin está **LIBRE**'"`;
  - envía otro mensaje con `"¡Úsame para Spinear!"` y la vista `UtilesDiscord.SpinButtonsView()`;
  - reinicia `UtilesDiscord.UsuarioSpin = None`.
- El comando slash `/ultimosspins` consulta `GestorSQL.Spin.fecha`, `GestorSQL.Spin.user` y `GestorSQL.Spin.tipo` desde un intervalo en minutos y devuelve una tabla sin ámbito.

### `GestorSQL.py`

- Define el modelo ORM `Spin` con tabla `Spin` y columnas:
  - `idSpin = Column('idCalendario', Integer, primary_key=True)`;
  - `user`;
  - `fecha`;
  - `tipo`.
- Define `insertar_spin(usuario, fecha, tipo)`, que crea `Spin(user=usuario, fecha=fecha, tipo=tipo)` y hace commit.
- No hay columna ni parámetro `ambito` en el modelo o función de inserción.

### `ComandosAntiguos.py`

- Contiene una implementación antigua de `SpinButtonsView` con los mismos `custom_id` (`your_bot:spin` y `your_bot:encontrado`).
- Usa `UsuarioSpin`; el estado público del Spin se localiza como primer mensaje del canal.
- Inserta en `Spin` llamando a `GestorSQL.insertar_spin(...)` en el flujo antiguo de `Spin`.
- Por el nombre del archivo y la existencia de la vista activa en `UtilesDiscord.py`, parece código histórico; conviene confirmar antes de modificarlo.

## Diferencias relevantes frente a `logicaSpin.md`

- Actualmente hay una sola cola global (`UsuarioSpin`), no colas independientes `GENERAL` y `COMUNIDADES`.
- Los botones usan `your_bot:spin` y `your_bot:encontrado`, sin ámbito en el `custom_id`.
- La creación actual del mensaje de Spin no acepta argumento de ámbito.
- `/ultimosspins` acepta argumento `ambito` para filtrar el historial.
- La tabla/modelo `Spin` tiene columna `ambito`.
- Existen constantes separadas para canal de Spin General y canal de Spin Comunidades.
- Existe dependencia del ID de canal de Spin General por compatibilidad, centralizada como constante; el mensaje público se edita como primer mensaje del canal.
