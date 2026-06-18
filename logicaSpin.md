# logicaSpin.md

## 1. Propósito del documento

Este documento define la lógica funcional y técnica de la mecánica **Spin** del bot.

Debe usarse como fuente de verdad para implementar, mantener y extender:

- **Spin General**
- **Spin Comunidades**
- historial de spins
- liberación automática
- liberación manual
- creación de mensajes con botones
- comando `/ultimosspins`
- comando administrativo para liberar spins atascados

La mecánica Spin permite que un jugador indique que está buscando partido. Si tiene un partido pendiente en el ámbito correspondiente, el bot reserva temporalmente esa cola para evitar que otra persona la use al mismo tiempo, avisa en el canal del partido y actualiza el mensaje público del Spin.

## 2. Glosario

### Spin

Acción de pulsar el botón `Spin` para indicar disponibilidad para jugar un partido pendiente.

### Encontrado

Acción de pulsar el botón `Encontrado` para indicar que el partido ya ha sido encontrado o que la búsqueda puede darse por finalizada.

### Cola de Spin

Reserva independiente asociada a un ámbito concreto.

Habrá, como mínimo, dos colas:

- `GENERAL`
- `COMUNIDADES`

Cada cola puede estar libre u ocupada.

### Ámbito

Tipo funcional de Spin.

Valores previstos:

- `GENERAL`
- `COMUNIDADES`

Estos valores se usarán también para filtrar historial en `/ultimosspins`.

### Spin General

Spin usado para los torneos y competiciones generales ya existentes.

Incluye, entre otros:

- calendario normal;
- playoffs oro;
- playoffs plata;
- playoffs bronce;
- ticket;
- torneo suizo individual.

### Spin Comunidades

Spin usado para partidos individuales del torneo suizo de comunidades.

Aunque inicialmente solo habrá un torneo de comunidades activo, la implementación debe quedar preparada para soportar varios torneos de comunidades en el futuro.

### Reserva

Estado temporal en el que una cola de Spin queda ocupada por un partido concreto.

Una reserva debe contener, como mínimo:

- ámbito;
- usuario que inició el Spin;
- usuarios del partido;
- canal del mensaje de Spin;
- canal del partido;
- instante de creación;
- tarea de timeout asociada;
- datos descriptivos del partido.

## 3. Principios generales

1. **Spin General y Spin Comunidades son colas independientes.**

   Una reserva activa en `GENERAL` no debe bloquear una reserva activa en `COMUNIDADES`.

2. **Ambas colas pueden estar ocupadas simultáneamente.**

   Debe ser posible que un jugador use Spin General mientras otro jugador usa Spin Comunidades.

3. **Cada ámbito tiene su propio canal de Spin.**

   Los torneos viven en entornos distintos dentro del mismo servidor Discord. Los jugadores de un entorno pueden no tener acceso a los canales del otro.

4. **Discord garantiza los permisos de acceso.**

   El bot no necesita validar manualmente si un usuario puede ver el canal donde pulsa el botón. Si puede pulsarlo, se asume que Discord ya ha aplicado los permisos correctos.

5. **Cada cola solo busca partidos de su ámbito.**

   - Spin General solo busca partidos generales.
   - Spin Comunidades solo busca partidos de comunidades.

6. **Si el usuario pulsa en la cola equivocada, no se busca en la otra.**

   Si un usuario de comunidades pulsa Spin General y no tiene partido general pendiente, recibirá un mensaje efímero indicando que no tiene partido pendiente en esa cola.

7. **Las reservas no persisten tras reinicio.**

   Al reiniciar el bot, todas las reservas se consideran liberadas.

8. **El timeout es de 5 minutos en todos los ámbitos.**

   Si nadie pulsa `Encontrado` en 5 minutos, la reserva se libera automáticamente.

9. **El mensaje principal del canal de Spin se localiza como primer mensaje del canal.**

   No se guardará el ID del mensaje de Spin como fuente de verdad.

   Motivo: si Discord falla, si un botón queda presionado permanentemente o si se pierde el mensaje, se puede borrar el mensaje anterior y volver a crear uno nuevo. El bot volverá a funcionar editando el primer mensaje del canal.

10. **El historial de Spin debe distinguir acción y ámbito.**

    El campo `tipo` mantiene su función actual:

    - `Spin`
    - `Encontrado`
    - otros eventos equivalentes si se definen

    Debe añadirse una nueva columna `ambito` para distinguir:

    - `GENERAL`
    - `COMUNIDADES`

## 4. Ámbitos soportados

### 4.1. GENERAL

Representa la cola actual de Spin usada por las competiciones generales.

Debe buscar partidos pendientes en las fuentes ya soportadas actualmente por el bot:

- `Calendario`
- `PlayOffsOro`
- `PlayOffsPlata`
- `PlayOffsBronce`
- `Ticket`
- `SuizoEmparejamiento`

La lógica concreta de filtrado debe conservar el comportamiento existente salvo que se indique otra cosa.

Criterios actuales esperados:

- el usuario que pulsa Spin participa en el partido;
- el partido tiene canal asociado;
- el partido no está resuelto;
- si hay varios partidos, se elige el partido con fecha más cercana cuando exista fecha.

### 4.2. COMUNIDADES

Representa la cola de Spin usada por los partidos individuales del torneo suizo de comunidades.

Debe buscar en `ComunidadesPartido`.

Un partido de comunidades es elegible para Spin Comunidades si cumple todas estas condiciones:

1. El usuario que pulsa Spin participa en el partido:

   - `usuario_local_id == usuario_db.idUsuarios`
   - o `usuario_visitante_id == usuario_db.idUsuarios`

2. El partido tiene canal de Discord:

   - `canal_discord_id IS NOT NULL`

3. El partido está pendiente o en curso:

   - `estado == PENDIENTE`
   - o `estado == EN_CURSO`

4. El partido no está finalizado ni administrado:

   - no debe tener `estado == FINALIZADO`
   - no debe tener `estado == ADMINISTRADO`

5. El partido no tiene `partido_bloodbowl_id`.

   Si `partido_bloodbowl_id` ya existe, significa que el partido ya fue encontrado o iniciado, por lo que no debe poder usar Spin.

## 5. Preparación para varios torneos de comunidades

Aunque inicialmente solo habrá un torneo de comunidades activo, la lógica debe diseñarse preparada para varios.

La interfaz de usuario puede mostrar simplemente:

- `Spin Comunidades`

Pero internamente es recomendable que la resolución de partido pueda conservar o devolver:

- `torneo_id`
- `ronda_id`
- `enfrentamiento_id`
- `partido_id`
- `indice`

Esto permitirá en el futuro distinguir varias competiciones de comunidades sin rediseñar la mecánica.

No es necesario crear una cola visible por torneo en la primera implementación.

La cola visible inicial será:

- `COMUNIDADES`

## 6. Selección de partido cuando hay varios pendientes

Si un jugador tiene varios partidos pendientes dentro del mismo ámbito, se debe elegir el partido con fecha más cercana, siempre que exista fecha.

Criterio recomendado:

1. Partidos con fecha más cercana al momento actual.
2. Si algún partido no tiene fecha, queda por detrás de los que sí tienen fecha.
3. Si varios partidos empatan o no tienen fecha, usar un criterio determinista secundario:
   - torneo;
   - ronda;
   - enfrentamiento;
   - índice de partido;
   - ID interno.

Para `COMUNIDADES`, el criterio principal también será la fecha más cercana si existe.

## 7. Estados de una cola

Cada cola de Spin puede estar en uno de estos estados:

### LIBRE

No hay reserva activa.

Botones esperados:

- `Spin`: habilitado.
- `Encontrado`: deshabilitado.

Mensaje principal esperado:

- Spin General:

  ```text
  El Spin General está **LIBRE**
  ```

- Spin Comunidades:

  ```text
  El Spin Comunidades está **LIBRE**
  ```

### RESERVADA

Hay una reserva activa.

Botones esperados:

- `Spin`: deshabilitado.
- `Encontrado`: habilitado.

Mensaje principal esperado:

- Spin General:

  ```text
  Spin General reservado: <@jugador1> y <@jugador2> pueden buscar partido.
  ```

- Spin Comunidades:

  ```text
  Spin de comunidades reservado para el partido individual <N> del enfrentamiento <Equipo A> vs <Equipo B>: <@jugador1> y <@jugador2> pueden buscar partido.
  ```

### LIBERANDO

Estado transitorio interno mientras se procesa una liberación manual o automática.

Debe evitar dobles liberaciones simultáneas.

## 8. Flujo del botón Spin

Cuando un usuario pulsa `Spin` en una cola:

1. El bot identifica el ámbito de la cola:

   - `GENERAL`
   - `COMUNIDADES`

2. El bot comprueba si esa cola ya está reservada.

3. Si la cola está reservada:

   - no modifica nada;
   - responde de forma efímera:

     ```text
     Ya hay un usuario buscando partido en esta cola.
     ```

4. Si la cola está libre:

   - busca el usuario en base de datos usando el ID de Discord;
   - si no encuentra usuario, responde efímeramente:

     ```text
     No se encontró tu usuario en la base de datos.
     ```

5. El bot busca partidos pendientes solo en el ámbito correspondiente.

6. Si no hay partidos pendientes en esa cola, responde efímeramente:

   ```text
   No tienes ningún partido pendiente en esta cola de Spin.
   ```

7. Si hay partidos pendientes:

   - selecciona el partido correspondiente según los criterios del ámbito;
   - crea la reserva de la cola;
   - deshabilita el botón `Spin`;
   - habilita el botón `Encontrado`;
   - edita el primer mensaje del canal de Spin;
   - envía un mensaje en el canal del partido;
   - registra el evento en la tabla de historial;
   - arranca un timeout de 5 minutos.

8. Mensaje efímero de éxito:

   - Spin General:

     ```text
     Ahora puedes buscar partido en Spin General.
     ```

   - Spin Comunidades:

     ```text
     Ahora puedes buscar partido en Spin Comunidades.
     ```

## 9. Flujo del botón Encontrado

Cuando un usuario pulsa `Encontrado`:

1. El bot identifica el ámbito de la cola.

2. El bot comprueba si la cola está reservada.

3. Si la cola está libre:

   - no modifica nada;
   - responde efímeramente:

     ```text
     No hay ningún Spin reservado en esta cola.
     ```

4. Si la cola está reservada, el bot comprueba si el usuario que pulsa es uno de los dos jugadores del partido reservado.

5. Puede pulsar `Encontrado` cualquiera de los dos jugadores del partido.

   Esto es un cambio intencionado respecto al comportamiento anterior, donde solo podía pulsarlo quien inició el Spin.

6. Si quien pulsa no es uno de los dos jugadores del partido:

   - no libera el Spin;
   - responde efímeramente:

     ```text
     Solo uno de los jugadores del partido reservado puede liberar este Spin.
     ```

7. Si quien pulsa sí es uno de los dos jugadores:

   - libera la reserva;
   - cancela el timeout;
   - habilita `Spin`;
   - deshabilita `Encontrado`;
   - edita el primer mensaje del canal de Spin para indicar que está libre;
   - envía mensaje en el canal del partido;
   - registra el evento en la tabla de historial con `tipo = Encontrado`.

## 10. Liberación automática por timeout

Cada reserva dura 5 minutos.

Si transcurren 5 minutos y nadie ha pulsado `Encontrado`:

1. El bot comprueba que la reserva sigue activa.
2. Libera la reserva.
3. Habilita `Spin`.
4. Deshabilita `Encontrado`.
5. Edita el primer mensaje del canal de Spin para indicar que la cola está libre.
6. Envía un mensaje en el canal del partido.
7. Envía DM al usuario que inició el Spin, si es posible.
8. Registra el evento en historial.

El texto debe mantener el tono humorístico actual.

Ejemplo para Spin General:

```text
El Spin General ha sido liberado automáticamente. 😡 Afortunadamente las máquinas somos superiores y cuidamos de los esmirriados humanos.
```

Ejemplo para Spin Comunidades:

```text
El Spin Comunidades ha sido liberado automáticamente. 😡 La comunidad ha sobrevivido a otro intento fallido de coordinación humana.
```

Si no se puede enviar DM, el fallo no debe impedir liberar la reserva.

Si no se puede editar el mensaje de Spin, el fallo no debe impedir liberar la reserva.

## 11. Mensajes en canal de partido

### 11.1. Spin General reservado

Cuando se reserva Spin General:

```text
<@jugador1> y <@jugador2>, podéis spinear.
```

### 11.2. Spin Comunidades reservado

Cuando se reserva Spin Comunidades:

```text
<@jugador1> y <@jugador2>, podéis spinear vuestro partido de comunidades.
```

Opcionalmente, si hay contexto suficiente:

```text
<@jugador1> y <@jugador2>, podéis spinear vuestro partido de comunidades: partido individual <N> del enfrentamiento <Equipo A> vs <Equipo B>.
```

### 11.3. Liberación manual

Spin General:

```text
El Spin General ha sido liberado.
```

Spin Comunidades:

```text
El Spin Comunidades ha sido liberado.
```

### 11.4. Liberación automática

Spin General:

```text
El Spin General ha sido liberado automáticamente. 😡 Afortunadamente las máquinas somos superiores y cuidamos de los esmirriados humanos.
```

Spin Comunidades:

```text
El Spin Comunidades ha sido liberado automáticamente. 😡 La comunidad ha sobrevivido a otro intento fallido de coordinación humana.
```

## 12. Mensajes principales en canales de Spin

Cada canal de Spin debe tener un primer mensaje que el bot editará.

No se debe depender de guardar el ID de ese mensaje.

### 12.1. Spin General libre

```text
El Spin General está **LIBRE**
```

### 12.2. Spin General reservado

```text
Spin General reservado: <@jugador1> y <@jugador2> pueden buscar partido.
```

### 12.3. Spin Comunidades libre

```text
El Spin Comunidades está **LIBRE**
```

### 12.4. Spin Comunidades reservado

```text
Spin de comunidades reservado para el partido individual <N> del enfrentamiento <Equipo A> vs <Equipo B>: <@jugador1> y <@jugador2> pueden buscar partido.
```

## 13. Botones

Cada mensaje de Spin debe tener dos botones:

1. `Spin`
2. `Encontrado`

### 13.1. Estado inicial

- `Spin`: habilitado.
- `Encontrado`: deshabilitado.

### 13.2. Estado reservado

- `Spin`: deshabilitado.
- `Encontrado`: habilitado.

### 13.3. Estado liberado

- `Spin`: habilitado.
- `Encontrado`: deshabilitado.

### 13.4. Identificación del ámbito

Los botones deben permitir identificar el ámbito al que pertenecen.

Se recomienda usar identificadores diferenciados, por ejemplo:

```text
lombardbot:spin:general
lombardbot:encontrado:general
lombardbot:spin:comunidades
lombardbot:encontrado:comunidades
```

También es aceptable que la vista reciba el ámbito como parámetro, siempre que las interacciones persistentes puedan reconstruirse correctamente tras reinicio.

## 14. Creación de mensajes de Spin

Actualmente existe un comando similar a:

```text
!AgregarMensajeSpin
```

Debe mantenerse una mecánica similar, pero añadiendo un argumento para decidir qué Spin se está creando.

### 14.1. Comando esperado

Ejemplo recomendado:

```text
!AgregarMensajeSpin General
```

```text
!AgregarMensajeSpin Comunidades
```

También pueden aceptarse valores normalizados:

```text
!AgregarMensajeSpin GENERAL
!AgregarMensajeSpin COMUNIDADES
```

El comando debe validar el argumento.

Valores válidos:

- `General`
- `Comunidades`

### 14.2. Comportamiento

Al ejecutar el comando:

1. El bot identifica el ámbito solicitado.
2. Publica un nuevo mensaje de Spin en el canal actual.
3. El mensaje debe contener el texto libre correspondiente.
4. El mensaje debe incluir la vista con botones correspondiente al ámbito.
5. El botón `Spin` debe aparecer habilitado.
6. El botón `Encontrado` debe aparecer deshabilitado.

### 14.3. Textos iniciales

Para General:

```text
El Spin General está **LIBRE**
```

Para Comunidades:

```text
El Spin Comunidades está **LIBRE**
```

### 14.4. Motivo para no guardar ID del mensaje

No se guardará el ID del mensaje como fuente de verdad.

Si Discord falla, si un botón queda bloqueado o si el mensaje se corrompe, la solución operativa será:

1. borrar el mensaje anterior;
2. ejecutar de nuevo `!AgregarMensajeSpin <ambito>`;
3. dejar que el bot use el nuevo primer mensaje del canal.

## 15. Configuración de canales

Los canales de Spin deben configurarse mediante constantes separadas en archivo de configuración.

Debe existir una configuración independiente para:

- canal de Spin General;
- canal de Spin Comunidades.

Ejemplo conceptual:

```python
CANAL_SPIN_GENERAL_ID = ...
CANAL_SPIN_COMUNIDADES_ID = ...
```

No deben mezclarse ambos canales.

No se debe asumir que los jugadores de un ámbito pueden ver el canal del otro.

## 16. Historial de Spins

La tabla de historial de Spin debe permitir auditar el orden de eventos.

El campo `tipo` mantiene su propósito actual:

- permite saber si el registro representa un `Spin`;
- o si representa un `Encontrado`;
- permite comprobar que el orden es intercalado en caso de error.

Debe añadirse una nueva columna:

```text
ambito
```

Valores:

- `GENERAL`
- `COMUNIDADES`

### 16.1. Campos mínimos recomendados

La tabla de historial debería almacenar, como mínimo:

- usuario;
- fecha;
- tipo;
- ambito.

Campos adicionales recomendados para trazabilidad futura:

- `usuario_discord_id`;
- `canal_spin_id`;
- `canal_partido_id`;
- `torneo_id`, si aplica;
- `partido_id`, si aplica;
- `origen_liberacion`, por ejemplo:
  - `MANUAL`
  - `TIMEOUT`
  - `ADMIN`
  - `REINICIO`

Estos campos adicionales no son obligatorios para la primera versión, pero son recomendables.

## 17. `/ultimosspins`

El comando `/ultimosspins` debe adaptarse para consultar ambas colas.

### 17.1. Nuevo argumento

Debe añadirse un argumento:

```text
ambito
```

Valores predefinidos:

- `Todos`
- `General`
- `Comunidades`

### 17.2. Valor por defecto

El valor por defecto debe ser:

```text
Todos
```

Esto mantiene compatibilidad con el comportamiento anterior.

### 17.3. Comportamiento por valor

#### `Todos`

Muestra historial de todos los ámbitos.

Incluye registros de:

- Spin General;
- Spin Comunidades.

#### `General`

Muestra únicamente registros con:

```text
ambito = GENERAL
```

#### `Comunidades`

Muestra únicamente registros con:

```text
ambito = COMUNIDADES
```

### 17.4. Presentación recomendada

Cada línea del historial debería mostrar el ámbito para evitar ambigüedad.

Ejemplo:

```text
[GENERAL] UsuarioX - Spin - 2026-06-18 20:15
[GENERAL] UsuarioX - Encontrado - 2026-06-18 20:17
[COMUNIDADES] UsuarioY - Spin - 2026-06-18 20:20
[COMUNIDADES] UsuarioZ - Encontrado - 2026-06-18 20:22
```

Si se filtra por un ámbito concreto, mostrar el ámbito sigue siendo recomendable.

## 18. Comando administrativo para liberar Spin

Los administradores o comisarios no deben poder liberar un Spin pulsando el botón `Encontrado`.

Motivo: podrían liberar una reserva con buena intención pero generar caos operativo.

En su lugar, debe existir un comando administrativo explícito para liberar una cola de Spin.

### 18.1. Comando recomendado

Ejemplo:

```text
/liberarspin ambito:General
```

```text
/liberarspin ambito:Comunidades
```

También puede implementarse como comando prefijado si el proyecto lo prefiere:

```text
!liberarspin General
!liberarspin Comunidades
```

### 18.2. Argumento

El comando debe aceptar:

```text
ambito
```

Valores:

- `General`
- `Comunidades`

No se recomienda permitir `Todos` en la primera versión para evitar liberar varias colas por accidente.

### 18.3. Permisos

Solo deben poder usarlo:

- administradores;
- comisarios;
- roles equivalentes definidos por el bot.

### 18.4. Comportamiento

Al ejecutar el comando:

1. Validar permisos.
2. Validar ámbito.
3. Comprobar si la cola está reservada.
4. Si está libre, responder:

   ```text
   El Spin <ambito> ya estaba libre.
   ```

5. Si está reservada:

   - liberar reserva;
   - cancelar timeout;
   - habilitar botón `Spin`;
   - deshabilitar botón `Encontrado`;
   - editar primer mensaje del canal de Spin;
   - enviar mensaje en canal del partido indicando liberación administrativa;
   - registrar evento en historial.

### 18.5. Mensajes

Liberación administrativa de Spin General:

```text
El Spin General ha sido liberado por administración.
```

Liberación administrativa de Spin Comunidades:

```text
El Spin Comunidades ha sido liberado por administración.
```

## 19. Reinicio del bot

Al reiniciar el bot:

1. Todas las reservas en memoria se pierden.
2. Todas las colas se consideran libres.
3. No se debe intentar recuperar una reserva anterior.
4. Las vistas persistentes deben registrarse de nuevo para ambos ámbitos.
5. Si un mensaje quedó visualmente en estado reservado antes del reinicio, la solución operativa aceptada es recrear el mensaje con `!AgregarMensajeSpin <ambito>` o ejecutar un mecanismo que restaure visualmente la cola.

No es obligatorio registrar un evento de liberación por reinicio en la primera versión.

## 20. Arquitectura recomendada

La implementación no debe duplicar dos clases completas de Spin.

Debe existir una lógica común reutilizable y proveedores específicos por ámbito.

### 20.1. Vista común

Debe existir una vista de botones parametrizable por ámbito.

Ejemplo conceptual:

```text
SpinButtonsView(ambito="GENERAL")
SpinButtonsView(ambito="COMUNIDADES")
```

La vista común debe encargarse de:

- recibir interacción;
- identificar ámbito;
- consultar estado de la cola;
- llamar al proveedor de partidos correspondiente;
- reservar;
- editar botones;
- editar primer mensaje;
- lanzar timeout;
- liberar manualmente;
- liberar automáticamente.

### 20.2. Proveedores de partido

Cada ámbito debe tener un proveedor de partido.

#### Proveedor General

Busca en:

- `Calendario`
- `PlayOffsOro`
- `PlayOffsPlata`
- `PlayOffsBronce`
- `Ticket`
- `SuizoEmparejamiento`

#### Proveedor Comunidades

Busca en:

- `ComunidadesPartido`

### 20.3. Resultado normalizado

Ambos proveedores deben devolver un resultado con estructura común.

Campos recomendados:

```text
ambito
canal_partido_id
jugador1_discord_id
jugador2_discord_id
fecha
descripcion_corta
descripcion_larga
torneo_id
partido_id
enfrentamiento_id
indice_partido
equipo_a_nombre
equipo_b_nombre
```

No todos los campos aplican a todos los ámbitos.

Los campos no aplicables pueden ser `None`.

## 21. Resultado normalizado para Spin General

Ejemplo conceptual:

```text
ambito = GENERAL
canal_partido_id = 123
jugador1_discord_id = 111
jugador2_discord_id = 222
fecha = 2026-06-18 22:00
descripcion_corta = "Spin General"
descripcion_larga = "Spin General reservado: <@111> y <@222> pueden buscar partido."
```

## 22. Resultado normalizado para Spin Comunidades

Ejemplo conceptual:

```text
ambito = COMUNIDADES
canal_partido_id = 456
jugador1_discord_id = 333
jugador2_discord_id = 444
fecha = 2026-06-18 22:00
descripcion_corta = "Spin Comunidades"
descripcion_larga = "Spin de comunidades reservado para el partido individual 1 del enfrentamiento Equipo A vs Equipo B: <@333> y <@444> pueden buscar partido."
torneo_id = 1
partido_id = 25
enfrentamiento_id = 10
indice_partido = 1
equipo_a_nombre = "Equipo A"
equipo_b_nombre = "Equipo B"
```

## 23. Reglas específicas de permisos para Encontrado

El botón `Encontrado` puede ser pulsado por:

- jugador 1 del partido reservado;
- jugador 2 del partido reservado.

No puede ser pulsado por:

- administradores, salvo que también sean uno de los jugadores;
- comisarios, salvo que también sean uno de los jugadores;
- otros usuarios.

Para liberación administrativa debe usarse el comando específico de administración.

## 24. Respuestas efímeras recomendadas

### 24.1. Cola ya ocupada

```text
Ya hay un usuario buscando partido en esta cola.
```

### 24.2. Usuario no encontrado

```text
No se encontró tu usuario en la base de datos.
```

### 24.3. Sin partido pendiente

```text
No tienes ningún partido pendiente en esta cola de Spin.
```

### 24.4. Spin reservado correctamente

Spin General:

```text
Ahora puedes buscar partido en Spin General.
```

Spin Comunidades:

```text
Ahora puedes buscar partido en Spin Comunidades.
```

### 24.5. Encontrado sin reserva

```text
No hay ningún Spin reservado en esta cola.
```

### 24.6. Usuario no autorizado para Encontrado

```text
Solo uno de los jugadores del partido reservado puede liberar este Spin.
```

### 24.7. Encontrado correcto

Spin General:

```text
Has liberado el Spin General.
```

Spin Comunidades:

```text
Has liberado el Spin Comunidades.
```

## 25. Manejo de errores

La liberación de una cola debe ser robusta.

Si falla una acción secundaria, no debe impedirse la liberación interna.

Acciones secundarias:

- enviar mensaje al canal del partido;
- enviar DM al usuario;
- editar el primer mensaje del canal de Spin;
- actualizar botones visualmente.

Regla:

1. Primero liberar el estado interno.
2. Después intentar actualizar Discord.
3. Registrar o notificar errores si existe mecanismo de administración.
4. No dejar la cola bloqueada por un fallo de Discord.

## 26. Sesiones de base de datos

Toda operación que abra una sesión SQL debe cerrarla siempre.

La lógica de Spin debe evitar retornos tempranos que dejen sesiones abiertas.

Regla recomendada:

- usar `try/finally`;
- cerrar sesión en `finally`;
- copiar los datos necesarios antes de cerrar sesión si luego se van a usar para enviar mensajes Discord.

## 27. Compatibilidad con comportamiento anterior

La nueva implementación debe conservar el comportamiento funcional del Spin existente para el ámbito `GENERAL`.

Cambios aceptados:

- el estado deja de ser global único y pasa a ser por ámbito;
- `/ultimosspins` puede filtrar por ámbito;
- el historial añade columna `ambito`;
- `Encontrado` podrá ser usado por cualquiera de los dos jugadores del partido;
- los mensajes pueden mencionar explícitamente `Spin General`.

No debe romperse:

- la posibilidad de crear mensaje de Spin general;
- la búsqueda de partidos generales;
- la liberación automática tras 5 minutos;
- el registro de eventos `Spin` y `Encontrado`.

## 28. Migración de datos

Debe añadirse la columna:

```text
ambito
```

a la tabla de historial de Spin.

Para registros antiguos, se recomienda asignar:

```text
GENERAL
```

Motivo: todos los registros anteriores pertenecían al Spin existente, que pasa a considerarse Spin General.

## 29. Valores canónicos

### 29.1. Ámbitos internos

```text
GENERAL
COMUNIDADES
```

### 29.2. Valores de usuario para comandos

```text
General
Comunidades
Todos
```

### 29.3. Tipos de evento

Mantener los existentes:

```text
Spin
Encontrado
```

Opcionales recomendados:

```text
AutoRelease
LiberacionAdmin
```

Si se añaden nuevos tipos, debe conservarse la capacidad de auditar el orden de reservas y liberaciones.

## 30. Resumen de comportamiento esperado

1. Hay dos canales distintos:
   - canal de Spin General;
   - canal de Spin Comunidades.
2. Cada canal tiene su propio mensaje con botones.
3. Cada mensaje controla una cola independiente.
4. Un Spin General activo no bloquea un Spin Comunidades activo.
5. Un Spin Comunidades activo no bloquea un Spin General activo.
6. Cada cola tiene timeout de 5 minutos.
7. Cada cola busca solo partidos de su ámbito.
8. Spin Comunidades busca en `ComunidadesPartido`.
9. Spin Comunidades excluye partidos que ya tengan `partido_bloodbowl_id`.
10. Cualquier jugador del partido reservado puede pulsar `Encontrado`.
11. Administradores y comisarios no liberan desde el botón.
12. Debe existir un comando administrativo explícito para liberar una cola.
13. `/ultimosspins` debe aceptar `ambito` con:
    - `Todos`
    - `General`
    - `Comunidades`
14. La tabla de historial debe añadir columna `ambito`.
15. Al reiniciar el bot, todas las reservas se consideran liberadas.

## 31. Checklist de implementación

- [ ] Crear constantes separadas para canal de Spin General y canal de Spin Comunidades.
- [ ] Parametrizar la vista de botones por ámbito.
- [ ] Crear estado de reserva independiente por ámbito.
- [ ] Mantener timeout de 5 minutos por reserva.
- [ ] Crear proveedor de partidos para Spin General.
- [ ] Crear proveedor de partidos para Spin Comunidades.
- [ ] Añadir búsqueda en `ComunidadesPartido`.
- [ ] Excluir partidos de comunidades con `partido_bloodbowl_id`.
- [ ] Permitir `Encontrado` a cualquiera de los dos jugadores del partido.
- [ ] Impedir `Encontrado` a usuarios ajenos al partido.
- [ ] Añadir columna `ambito` al historial de Spin.
- [ ] Migrar registros antiguos a `GENERAL`.
- [ ] Adaptar `/ultimosspins` con argumento `ambito`.
- [ ] Añadir valores `Todos`, `General`, `Comunidades` a `/ultimosspins`.
- [ ] Adaptar `!AgregarMensajeSpin` para aceptar ámbito.
- [ ] Crear mensaje inicial correcto por ámbito.
- [ ] Crear comando administrativo para liberar Spin por ámbito.
- [ ] Asegurar cierre de sesiones SQL.
- [ ] Asegurar liberación interna aunque falle Discord.
- [ ] Registrar vistas persistentes para ambos ámbitos al arrancar el bot.

## 32. Decisiones cerradas

- Spin General y Spin Comunidades no comparten cola.
- Ambas colas pueden usarse simultáneamente.
- Tendrán canales diferentes.
- Discord gestiona permisos de acceso.
- El timeout es de 5 minutos en ambos ámbitos.
- Al reiniciar, las reservas se consideran liberadas.
- El primer mensaje del canal es el mensaje que se edita.
- No se guardará el ID del mensaje de Spin como fuente de verdad.
- `/ultimosspins` usará argumento `ambito`.
- Valores de `/ultimosspins`: `Todos`, `General`, `Comunidades`.
- El campo `tipo` conserva su función actual.
- Se añade nueva columna `ambito`.
- Spin Comunidades busca en `ComunidadesPartido`.
- Spin Comunidades no permite partidos con `partido_bloodbowl_id`.
- Cualquier jugador del partido puede pulsar `Encontrado`.
- Administradores/comisarios no liberan desde botón.
- Debe existir comando administrativo específico para liberar por ámbito.
- `!AgregarMensajeSpin` o equivalente debe aceptar argumento de ámbito.
