# Especificación del torneo suizo por parejas y comunidades

## 1. Propósito y alcance

Este documento define el comportamiento funcional y técnico del nuevo torneo suizo por **parejas** y **comunidades**. Debe utilizarse como fuente de verdad para futuras tareas de implementación, pruebas, mantenimiento y revisión.

Este formato es independiente del torneo suizo individual existente. Puede reutilizar ideas, utilidades e integración con Discord o la API de Blood Bowl, pero debe disponer de **tablas, modelos, consultas y comandos propios** porque su unidad competitiva es el equipo de dos jugadores y porque incorpora selección de atacantes, comunidades y estados especiales.

Principios fundamentales:

- La clasificación suiza y los emparejamientos operan sobre equipos, no sobre usuarios.
- Cada equipo contiene exactamente dos usuarios y pertenece a una comunidad.
- Cada enfrentamiento entre equipos produce exactamente dos partidos individuales BO1.
- Nunca se enfrentan equipos de la misma comunidad.
- Los estados de cazador, cazador Z, herido y zombie pertenecen al equipo.
- La condición zombie es permanente; los otros estados son temporales.
- Los usuarios se utilizan para disputar los partidos individuales y enlazarlos con la API de Blood Bowl.
- No se reutilizarán las tablas `suizo_*` para almacenar este torneo.

---

## 2. Glosario

### Torneo

Edición concreta del formato. Define rondas, fechas, comunidades, puntuaciones, canal hub y categorías de Discord.

### Comunidad

Entidad representada por varios equipos dentro de un torneo. Inicialmente se esperan comunidades como `Butter`, `Hispana` y `PdM`, pero las comunidades se configuran por torneo y no deben estar codificadas como un enum cerrado.

### Equipo

Unidad competitiva del torneo. Tiene:

- un nombre único dentro del torneo;
- una comunidad;
- exactamente dos miembros;
- una raza fija por miembro;
- puntos y estadísticas suizas;
- condición zombie permanente;
- estados temporales de cazador, cazador Z o herido.

### Enfrentamiento

Serie entre dos equipos. Tiene un canal general visible para los cuatro jugadores y los comisarios. Cada equipo elige secretamente a su atacante y, tras ambas elecciones, se crean dos partidos individuales.

### Partido individual

Partido BO1 entre un jugador de cada equipo. Sus puntos internos se utilizan para decidir el resultado del enfrentamiento, pero no generan una clasificación individual.

### Atacante y defensor

Cada equipo elige a uno de sus dos miembros como atacante. El otro miembro queda derivado automáticamente como defensor.

Los partidos resultantes son:

1. atacante del equipo A contra defensor del equipo B;
2. atacante del equipo B contra defensor del equipo A.

### Fotografía de estados

Copia inmutable de los estados de los equipos al generar la ronda. Determina los efectos especiales del enfrentamiento, como conceder puntos por zombificación o contabilizar una muerte de zombie. Una transferencia realizada durante la ronda nunca tiene efectos retroactivos.

---

## 3. Invariantes y restricciones absolutas

1. Un equipo tiene exactamente dos miembros.
2. Un usuario solo puede pertenecer a un equipo dentro del mismo torneo.
3. Los equipos se crean independientemente en cada edición, aunque repitan nombre o miembros en otros torneos.
4. El nombre de equipo es único dentro del torneo.
5. Un equipo pertenece a una sola comunidad.
6. Las comunidades pueden añadirse mientras el torneo esté en estado `CREADO`.
7. Las comunidades quedan bloqueadas al generar la ronda 1.
8. No hay altas tardías, sustituciones ni retiradas mediante comandos de este formato.
9. Una vez inscrito un equipo, no se modifican por comando su nombre, comunidad, miembros ni razas.
10. Nunca se emparejan dos equipos de la misma comunidad, ni siquiera como fallback.
11. No se guarda una ronda parcialmente generada. Si no existe solución completa, se cancela toda la generación.
12. Cada enfrentamiento genera exactamente dos partidos individuales BO1.
13. No existe clasificación individual de jugadores.
14. Ser zombie es permanente y no elimina al equipo del torneo.
15. Un equipo no puede estar herido y ser cazador o cazador Z al mismo tiempo.
16. Un equipo no puede ser cazador y cazador Z al mismo tiempo.
17. La condición zombie sí puede coexistir con cazador, cazador Z o herido.
18. Los estados especiales utilizados para resolver un enfrentamiento son los guardados en su fotografía inicial, no los estados que el equipo pueda recibir posteriormente.

---

## 4. Modelo de datos independiente

Los nombres exactos pueden adaptarse a las convenciones del proyecto, pero la implementación necesita, como mínimo, entidades equivalentes a las siguientes.

### 4.1. Torneo de comunidades

Debe almacenar:

- ID interno.
- Nombre.
- Estado: `CREADO`, `EN_CURSO` o `FINALIZADO`.
- Número total de rondas.
- Fecha límite de la ronda 1.
- Días por ronda.
- ID de competición de Blood Bowl.
- ID del canal hub.
- Puntos de clasificación por victoria, empate, derrota y bye.
- Puntos internos de partido individual por victoria, empate y derrota.
- Plantilla configurable del mensaje inicial para los canales de la ronda 1.
- Plantilla configurable de los mensajes posteriores para los canales de las rondas 2 y siguientes.
- Usuario Discord creador y marcas de tiempo.

El formato individual siempre es BO1 y cada enfrentamiento siempre tiene dos partidos, por lo que no hacen falta opciones BO3/BO5 ni ida/vuelta.

### 4.2. Comunidades del torneo

Cada registro debe relacionar una comunidad con un torneo y almacenar:

- ID interno.
- Torneo.
- Nombre único dentro del torneo.
- Puntos comunitarios por zombificaciones.
- Zombies matados.
- Marcas de tiempo.

No debe usarse un enum fijo: futuros torneos podrán tener comunidades diferentes.

### 4.3. Equipos

Cada equipo debe almacenar:

- ID interno.
- Torneo.
- Comunidad.
- Nombre único dentro del torneo.
- Condición permanente `es_zombie`.
- Estado temporal actual representado de forma consistente:
  - neutro;
  - cazador;
  - cazador Z;
  - herido.
- Contador de byes.
- Marcas de tiempo.

Aunque conceptualmente existan cuatro indicadores —zombie, cazador, cazador Z y herido—, se recomienda modelar `es_zombie` como booleano independiente y el estado temporal como un enum mutuamente excluyente. Esto hace imposibles las combinaciones inválidas sin perder la convivencia permitida con zombie.

### 4.4. Miembros de equipo

Debe relacionar usuarios con equipos y almacenar:

- Equipo.
- Usuario de la tabla `usuarios`.
- Raza fija para esta competición.
- Posición o índice estable dentro de la pareja.

Restricciones:

- exactamente dos miembros por equipo;
- un usuario no puede aparecer en dos equipos del mismo torneo;
- la raza no cambia durante el torneo.

### 4.5. Rondas

Cada ronda debe almacenar:

- Torneo.
- Número.
- Estado.
- Fecha de inicio y fin.
- Usuario que la generó.
- Fecha de cierre.

### 4.6. Enfrentamientos entre equipos

Cada enfrentamiento debe almacenar:

- Torneo y ronda.
- Número de mesa.
- Equipo A y equipo B.
- Canal general de Discord.
- Estado: pendiente de elecciones, partidos creados, en curso, cerrado o administrado.
- Puntos internos sumados por cada equipo.
- TD a favor y en contra de cada equipo.
- TD anotados por el atacante de cada equipo.
- Ganador o empate.
- Puntos de clasificación otorgados a cada equipo.
- Origen del resultado.
- Indicador de doble forfait global, si procede.

### 4.7. Elecciones de atacante

Debe almacenarse una elección por equipo y enfrentamiento:

- Enfrentamiento.
- Equipo.
- Usuario atacante.
- Usuario defensor derivado.
- Usuario Discord que realizó o modificó la elección.
- Fecha y hora de la última elección.
- Indicador de bloqueo.

La elección puede modificarse hasta que ambos equipos hayan elegido. En ese momento, ambas elecciones quedan bloqueadas.

### 4.8. Partidos individuales

Cada enfrentamiento tiene exactamente dos registros:

- Enfrentamiento.
- Índice 1 o 2.
- Usuario local y visitante.
- Referencia al atacante y defensor de cada cruce.
- Canal individual.
- ID del partido en Blood Bowl.
- TD de ambos jugadores.
- Puntos internos de ambos equipos.
- Estado y origen: API o administración.
- Tipo de forfait, cuando corresponda.

### 4.9. Fotografía de estados por enfrentamiento

Debe guardar, para cada uno de los dos equipos:

- condición zombie al generar la ronda;
- estado temporal al generar la ronda;
- comunidad en ese momento;
- ronda y enfrentamiento asociados.

Esta fotografía es inmutable y se utiliza al resolver efectos especiales.

### 4.10. Historial de transiciones

Debe registrar de forma auditable:

- ronda y enfrentamiento;
- equipo;
- estado y condición zombie anteriores;
- estado y condición zombie posteriores;
- motivo: victoria, derrota, empate, bye, zombificación, kill, doble forfait o transferencia;
- puntos comunitarios o kills generados;
- fecha y hora.

### 4.11. Historial de transferencias

Debe almacenar permanentemente:

- torneo y ronda;
- equipo origen y destino;
- comunidad;
- tipo transferido: cazador o cazador Z;
- usuario que ejecutó el comando;
- fecha y hora.

### 4.12. Categorías de Discord

Deben existir tablas independientes y ordenadas para:

- categorías de canales de enfrentamientos;
- categorías de canales de partidos individuales.

Cada registro almacena torneo, ID de categoría y orden de alta.

### 4.13. Snapshots de clasificación

Al cerrar una ronda deben guardarse snapshots reproducibles de:

- clasificación de equipos;
- clasificación de comunidades;
- estadísticas y desempates aplicados.

---

## 5. Usuarios y razas

### 5.1. Alta automática de usuarios

Al inscribir un equipo, si un miembro no existe en `usuarios`, se crea con:

- `id_discord`: ID de Discord;
- `nombre_discord`: nombre visible actual;
- `id_bloodbowl`: `NULL`;
- `nombre_bloodbowl`: `NULL`.

Los datos de Blood Bowl se completarán manualmente antes del primer partido. La importación de resultados depende de que `id_bloodbowl` esté correctamente informado.

### 5.2. Razas válidas

La lista es fija y compartida por todos los torneos de comunidades. Los comandos deben exigir exactamente uno de estos nombres. Cada nombre canónico se vincula directamente con `Iconos/<nombre canónico>.png`:

- `Alianza V. Mundo` → `Iconos/Alianza V. Mundo.png`
- `Amazonas` → `Iconos/Amazonas.png`
- `Caos Elegido` → `Iconos/Caos Elegido.png`
- `Elfos Oscuros` → `Iconos/Elfos Oscuros.png`
- `Elfos Silvanos` → `Iconos/Elfos Silvanos.png`
- `Enanos del Caos` → `Iconos/Enanos del Caos.png`
- `Enanos` → `Iconos/Enanos.png`
- `Hombres Lagarto` → `Iconos/Hombres Lagarto.png`
- `Horror Nigromantico` → `Iconos/Horror Nigromantico.png`
- `Humanos` → `Iconos/Humanos.png`
- `Inframundo` → `Iconos/Inframundo.png`
- `Khorne` → `Iconos/Khorne.png`
- `No muertos` → `Iconos/No muertos.png`
- `Nobleza Imperial` → `Iconos/Nobleza Imperial.png`
- `Nordicos` → `Iconos/Nordicos.png`
- `Nurgle` → `Iconos/Nurgle.png`
- `Orcos negros` → `Iconos/Orcos negros.png`
- `Orcos` → `Iconos/Orcos.png`
- `Renegados` → `Iconos/Renegados.png`
- `Skaven` → `Iconos/Skaven.png`
- `Stunty` → `Iconos/Stunty.png`
- `Union Elfica` → `Iconos/Union Elfica.png`
- `Vampiros` → `Iconos/Vampiros.png`

No existen aliases de recursos gráficos: los archivos con erratas, variantes o acentos distintos del nombre canónico no se utilizan, aunque permanezcan temporalmente en el repositorio. En particular, `Iconos/Elfo Osucros.png` y `Iconos/Unión Élfica.png` quedan obsoletos para este formato. La implementación debe usar `Iconos/Elfos Oscuros.png` e `Iconos/Union Elfica.png`.

No se normalizan variantes, acentos ni errores ortográficos. Las razas quedan fijadas al inscribir el equipo. Los dos miembros de una pareja pueden utilizar la misma raza.

---

## 6. Configuración y comandos administrativos

Todos los comandos con prefijo `!` de esta sección son exclusivos de comisarios, salvo que se indique otra cosa.

### 6.1. Crear torneo

Interfaz prevista:

```text
!comunidades_crear "Nombre torneo" 5 2026-07-01 23:59 7 1497290209505710120
```

Argumentos:

1. nombre;
2. rondas totales;
3. fecha fin de ronda 1;
4. hora fin de ronda 1;
5. días por ronda;
6. canal hub ID.

El torneo se crea en estado `CREADO`. La creación no exige informar todavía el ID de competición de Blood Bowl.

### 6.2. Configurar competición de Blood Bowl

```text
!comunidades_set_competicion <torneo_id> <idCompBbowl>
```

El comando guarda o reemplaza el ID de competición de Blood Bowl del torneo. Solo puede ejecutarse cuando el torneo está en estado `CREADO`; una vez iniciada la ronda 1, el valor queda bloqueado y cualquier intento de cambio debe rechazarse sin modificarlo. No se contempla la edición manual de este dato como flujo operativo ordinario.

### 6.3. Configurar puntuación de clasificación

```text
!comunidades_set_puntos_equipo <torneo_id> <win> <draw> <loss> <bye>
```

Ejemplo:

```text
!comunidades_set_puntos_equipo 1 3 1 0 1.5
```

Estos valores se otorgan al equipo por el resultado global del enfrentamiento. El bye es configurable.

### 6.4. Configurar puntuación interna individual

```text
!comunidades_set_puntos_individuales <torneo_id> <win> <draw> <loss>
```

Ejemplo:

```text
!comunidades_set_puntos_individuales 1 3 1 0
```

Estos valores solo se suman para decidir qué equipo ganó el enfrentamiento. No se publican como puntos de clasificación individual.

### 6.5. Añadir comunidad

```text
!comunidades_add_comunidad <torneo_id> <nombre>
```

Ejemplos:

```text
!comunidades_add_comunidad 1 Butter
!comunidades_add_comunidad 1 Hispana
!comunidades_add_comunidad 1 PdM
```

Solo se permite antes de generar la ronda 1. Desde ese momento, la lista queda congelada.

### 6.6. Añadir categorías de partidos

```text
!comunidades_add_categoria_partidos <torneo_id> <categoria_id>
```

Pueden añadirse varias. Se prueban en el orden de alta.

### 6.7. Añadir categorías de enfrentamientos

```text
!comunidades_add_categoria_enfrentamientos <torneo_id> <categoria_id>
```

Pueden añadirse varias. Se prueban en el orden de alta.

No se necesitan comandos para consultar, eliminar o reordenar categorías; una corrección excepcional se hará manualmente en base de datos.

### 6.8. Añadir equipo

```text
!comunidades_add_equipo <torneo_id> "<nombre_equipo>" <comunidad> <@jugador1> "<raza1>" <@jugador2> "<raza2>"
```

Ejemplo:

```text
!comunidades_add_equipo 1 "Los Rompecráneos" Butter @Jugador1 "Orcos" @Jugador2 "Skaven"
```

Debe validar todas las invariantes de inscripción y crear en `usuarios` a los miembros inexistentes.

### 6.9. Generar y regenerar ronda

```text
!comunidades_generar_ronda <torneo_id> <ronda>
!comunidades_regenerar_ronda <torneo_id> <ronda>
```

Generar la ronda 1 inicia el torneo y bloquea comunidades e inscripciones.

La regeneración elimina inmediatamente todo lo derivado de la ronda:

- canales generales;
- canales individuales;
- elecciones;
- partidos y resultados no consolidados;
- emparejamientos;
- fotografías de estados;
- transiciones y puntuación derivadas de esa ronda.

No elimina publicaciones del foro ni mensajes anteriores del canal hub.

### 6.10. Actualizar desde la API

```text
!comunidades_actualizar <torneo_id>
!comunidades_actualizar <torneo_id> 1
```

Debe reutilizar conceptualmente el flujo del suizo actual para localizar partidos por `id_bloodbowl`, guardar resultados, publicar imágenes y cerrar partidos. La opción `1` puede procesar todos los partidos encontrados en una pasada.

### 6.11. Administrar un partido individual

Debe existir un comando equivalente a:

```text
!comunidades_admin_partido <torneo_id> <ronda> <enfrentamiento> <partido> <tipo> [td_local] [td_visitante]
```

Tipos:

- `forfeit_local`;
- `forfeit_visitante`;
- `empate_admin`;
- `doble_forfeit`;
- `manual`.

Los resultados administrativos se procesan como resultados reales y pueden producir heridas, cazadores, zombificaciones o kills. `doble_forfeit` otorga `0-0` en puntos internos para ese partido.

No habrá un comando para imponer directamente un resultado global: se administran los dos partidos individuales y el cierre del segundo dispara la resolución normal del enfrentamiento.

### 6.12. Forzar la creación de partidos

Debe existir un comando administrativo equivalente a:

```text
!comunidades_forzar_crear_partidos <torneo_id> <ronda> <enfrentamiento> <@atacante_equipo_a> <@atacante_equipo_b>
```

Los argumentos de atacante son siempre obligatorios, incluso si uno o ambos equipos ya habían registrado una elección. `equipo_a` y `equipo_b` son, respectivamente, los lados A y B almacenados en el enfrentamiento indicado; no dependen del orden en que se escriban las menciones ni de quién hubiera elegido previamente.

Antes de modificar datos, el comando debe validar que el torneo, la ronda y el enfrentamiento existen, que el enfrentamiento admite todavía la creación de partidos, que cada atacante indicado pertenece al equipo de su lado y que los dos partidos y sus canales pueden crearse. Si una elección previa existe, se reemplaza por la indicada en el comando. El defensor de cada equipo se deriva obligatoriamente como el otro miembro de la pareja; no se recibe como argumento.

Tras superar todas las validaciones, el comando reemplaza ambas elecciones, las bloquea, crea los dos partidos y crea sus dos canales. La operación es atómica desde el punto de vista funcional: si falla una validación o cualquier parte de la creación, no se conserva ninguna elección reemplazada, partido ni canal nuevo. La implementación debe revertir los cambios de base de datos y eliminar cualquier canal que hubiera alcanzado a crear antes del fallo.

El comando deja los dos partidos disponibles para que los comisarios los administren después por separado. La regla operativa comunicada a los jugadores será que deben elegir atacante en un plazo de 24 horas. No se requiere automatización del vencimiento y el comando no calcula ni valida que hayan transcurrido las 24 horas: el comisario decide cuándo procede aplicar el forzado.

### 6.13. Consultar elecciones secretas

```text
!comunidades_consulta_elecciones <torneo_id> <ronda>
```

Restricciones:

- solo comisarios;
- solo se ejecuta en el canal de administración hardcodeado del bot;
- si se invoca fuera, no revela información y avisa de que debe utilizarse en el canal administrativo.

Debe mostrar por enfrentamiento:

- equipo;
- atacante seleccionado;
- defensor derivado;
- pendiente si no eligió;
- usuario que hizo o modificó la elección;
- fecha y hora de la última elección.

---

## 7. Comandos públicos y consultas

Los comandos de participantes y las consultas ordinarias deben ser slash commands públicos y usar el prefijo `comunidades_`. Como mínimo:

```text
/comunidades_transferir_cazador torneo_id:1 equipo_destino:"Nombre del equipo"
/comunidades_consulta_ronda
/comunidades_clasificacion_equipos
/comunidades_clasificacion_comunidades
/comunidades_consulta_equipo
/comunidades_consulta_estados
/comunidades_consulta_estado_canales
```

`/comunidades_transferir_cazador` puede ejecutarlo cualquiera de los dos integrantes del equipo origen y está sujeto a todas las reglas de la sección 13. Las consultas deben mostrar claramente los estados mediante emojis, salvo en los canales individuales, donde basta con identificar atacante y defensor.

Leyenda recomendada:

- 🏹 Cazador.
- 🩸 Herido.
- 🧟 Zombie.
- 🏹🧟 Cazador Z.

Cuando un equipo sea zombie y además tenga un estado temporal, deben mostrarse ambas condiciones sin ocultar ninguna.

---

## 8. Generación de emparejamientos

### 8.1. Base suiza

Los emparejamientos se realizan entre equipos utilizando su clasificación acumulada. Para candidatos equivalentes, se busca cercanía de puntos suizos.

### 8.2. Restricciones absolutas

1. Nunca enfrentar equipos de la misma comunidad.
2. Generar la ronda completa o no generar nada.

Si la distribución de comunidades hace imposible una solución completa, la operación se cancela y se informa en el canal administrativo.

### 8.3. Prioridades por estado

Se intentan formar prioritariamente:

- cazador normal contra herido no zombie;
- cazador Z contra zombie herido.

Dentro de cada prioridad:

1. minimizar diferencia de puntos;
2. si varios candidatos tienen igual proximidad, evitar mirrors;
3. resolver equivalencias mediante azar.

Los zombies heridos deben reservarse para cazadores Z. Se evita:

- cazador normal contra zombie herido;
- cazador Z contra un rival que no sea zombie herido;
- neutro u otro estado contra zombie herido cuando exista una alternativa válida.

### 8.4. Mirrors

Existe mirror de equipos cuando ambos equipos comparten al menos una raza, independientemente de quién sea finalmente atacante.

Ejemplo: un equipo `Orcos/Skaven` y otro `Humanos/Skaven` constituyen mirror por compartir `Skaven`.

Se intenta evitar, pero no es una restricción absoluta.

### 8.5. Rivales repetidos

Se intenta no repetir enfrentamientos entre equipos. La repetición está permitida solamente como fallback.

### 8.6. Orden de relajación

El algoritmo debe intentar una solución completa y relajar reglas en este orden:

1. permitir mirrors;
2. permitir emparejamientos de estado no deseados;
3. permitir rivales repetidos;
4. cancelar si sigue sin existir una solución completa sin enfrentar comunidades iguales.

La restricción de comunidad nunca se relaja.

### 8.7. Bye

Si hay un número impar de equipos, se asigna un bye siguiendo este orden:

1. equipos sin cazador, cazador Z ni herido;
2. equipos sin bye previo;
3. peor clasificado;
4. azar como último desempate.

Un zombie neutro es elegible porque ser zombie no es un estado temporal. Si solo queda un equipo con estado temporal, puede recibir el bye.

Efectos:

- suma la puntuación de bye configurada;
- pierde cazador, cazador Z o herido;
- conserva para siempre la condición zombie;
- se registra igual que en el suizo actual a efectos de PJ, PG/PE/PP y Buchholz;
- no añade touchdowns ni rival para enfrentamiento directo;
- se evita repetir bye si existe una alternativa válida.

### 8.8. Fotografía inicial

Antes de abrir los canales se guarda la fotografía de estado de cada equipo. Esa fotografía determina qué efectos especiales puede activar el resultado de la ronda.

---

## 9. Canales y categorías de Discord

### 9.1. Canal general del enfrentamiento

Al generar la ronda se crea un canal `Equipo A vs Equipo B`, visible para:

- los cuatro jugadores;
- comisarios y permisos administrativos habituales.

Se ubica en la primera categoría de enfrentamientos configurada con menos de 40 canales. Se cuentan todos los canales existentes en la categoría, aunque pertenezcan a otros usos.

Si tiene 40 canales, se prueba la siguiente categoría según orden de alta. Si todas están llenas o no existe una categoría utilizable, se informa en el canal administrativo hardcodeado y no se deja la operación en un estado parcial.

### 9.2. Contenido del canal general

Los mensajes de los canales son configurables por torneo mediante dos campos de texto obligatorios en la tabla del torneo, con los nombres `mensajeInicial` y `mensajesSubsiguientes`:

- `mensajeInicial` se utiliza en los canales creados para la ronda 1;
- `mensajesSubsiguientes` se utiliza en los canales creados para las rondas 2 y siguientes.

En la v1 no habrá comandos para editar estos campos: su alta y modificación se realizarán directamente en base de datos. El texto exacto no queda hardcodeado en el bot. Si las plantillas contienen marcadores, la implementación solo podrá sustituir los marcadores admitidos expresamente por el contrato técnico correspondiente.

El mensaje resultante del canal general debe explicar:

- que cada equipo dispone de 24 horas para seleccionar atacante;
- cómo ejecutar `/comunidades_seleccion_atacante`;
- que la elección es secreta;
- cómo se derivan los dos partidos;
- fecha límite de la ronda;
- estados visibles de ambos equipos al inicio;
- reglas resumidas de resolución del enfrentamiento.

### 9.3. Canales individuales

Cuando ambos equipos hayan elegido, se crean dos canales adicionales con permisos, fechas y publicación de resultados equivalentes al suizo actual, pero con mensajes específicos de este formato que identifiquen atacante y defensor.

Se distribuyen entre las categorías de partidos configuradas, en orden de alta y con límite de 40 canales por categoría, contando todos los canales existentes.

### 9.4. Permanencia y eliminación

- Al terminar un partido individual, su canal permanece hasta el cierre de la ronda.
- Al terminar el enfrentamiento, el canal general también permanece hasta el cierre de la ronda.
- Al cerrar la ronda se eliminan todos los canales generales e individuales de esa ronda.
- No se eliminan publicaciones del foro.
- No se eliminan mensajes del canal hub.

---

## 10. Selección secreta de atacante

Comando público slash:

```text
/comunidades_seleccion_atacante usuario:@Jugador
```

Reglas:

1. Solo funciona dentro del canal general de un enfrentamiento activo.
2. Solo puede usarlo uno de los dos miembros de uno de los equipos del canal.
3. Solo puede elegir como atacante a un miembro de su propio equipo.
4. Puede elegirse a sí mismo o a su compañero.
5. No puede elegir para otro equipo ni para otro enfrentamiento.
6. La respuesta al usuario es ephemeral y muestra atacante y defensor.
7. En el canal público solo aparece: `El equipo NOMBREEQUIPO ha elegido atacante`.
8. La identidad elegida permanece secreta para el rival.
9. Puede cambiarse mientras el rival todavía no haya elegido.
10. Cuando ambos han elegido, las elecciones quedan bloqueadas.
11. Al bloquearse, se publica `Se van a crear los encuentros` y se crean los dos partidos y canales individuales.

El defensor siempre es el otro miembro de la pareja y no requiere selección independiente.

---

## 11. Resolución de partidos y enfrentamientos

### 11.1. Puntos internos

Cada partido individual concede los valores configurados en `comunidades_set_puntos_individuales`.

Ejemplo con `3/1/0`:

- Partido 1 empatado: A `1`, B `1`.
- Partido 2 ganado por A: A `3`, B `0`.
- Suma del enfrentamiento: A `4`, B `1`.

### 11.2. Determinación del ganador global

1. Se suman los puntos internos de los dos partidos.
2. Gana el equipo con mayor suma.
3. Si empatan, gana el equipo cuyo atacante anotó más TD en su partido individual.
4. Si continúa el empate, se compara la diferencia global de TD de la serie:

```text
TD de ambos miembros del equipo - TD recibidos por ambos miembros
```

5. Si continúa el empate, el enfrentamiento acaba empatado.

### 11.3. Puntos de clasificación

Después de decidir el resultado global, se otorgan los valores configurados en `comunidades_set_puntos_equipo`:

- victoria global: `win`;
- empate global: `draw`;
- derrota global: `loss`.

Los puntos internos no se añaden directamente a la clasificación.

### 11.4. Estadísticas

Solo se mantiene clasificación de equipos. Los TD de ambos miembros se acumulan como TD a favor y en contra del equipo.

### 11.5. Cierre automático

- El primer partido cerrado se publica, pero no resuelve estados.
- Al cerrar el segundo partido se resuelve automáticamente el enfrentamiento completo.
- La resolución aplica puntuación, transiciones, zombificaciones, kills e historial en una sola transacción lógica.

---

## 12. Máquina de estados

### 12.1. Dimensiones

Cada equipo tiene:

- `es_zombie`: sí/no, permanente;
- estado temporal: neutro, cazador, cazador Z o herido.

Combinaciones permitidas:

- normal neutro;
- normal cazador;
- normal cazador Z;
- normal herido;
- zombie neutro;
- zombie cazador;
- zombie cazador Z;
- zombie herido.

### 12.2. Regla base de victoria

- Ganar a un rival no zombie y no herido concede cazador normal.
- Ganar a un zombie no herido concede cazador Z.
- El perdedor pasa a herido, salvo las excepciones de caza consumada descritas más adelante.
- Un cazador que gana de nuevo a un rival normal renueva cazador.
- Un cazador Z que gana a un zombie no herido renueva cazador Z.

### 12.3. Regla base de empate

- Ambos equipos pierden cazador, cazador Z o herido.
- Ambos quedan temporalmente neutros.
- La condición zombie no cambia.

### 12.4. Herido no zombie que pierde

Siempre se convierte permanentemente en zombie y deja de estar herido.

- Si el vencedor era cazador normal en la fotografía inicial, su comunidad recibe 1 punto de zombificación y el vencedor queda neutro.
- Si el vencedor no era cazador normal en la fotografía inicial, no se concede punto comunitario y el vencedor queda neutro.
- Si el vencedor era cazador Z, tampoco se concede punto de zombificación y queda neutro.

La conversión ocurre aunque el ganador no tenga el estado apropiado; el estado solo determina si se concede el punto comunitario.

### 12.5. Zombie herido que pierde contra cazador Z inicial

- Continúa siendo zombie.
- Deja de estar herido y queda neutro.
- Se suma 1 zombie matado a la comunidad del cazador Z.
- No se suma punto de zombificación.
- El cazador Z queda neutro porque completó su caza.

Esta es la única situación que cuenta como **matar un zombie**.

### 12.6. Zombie herido que pierde contra otro estado

Si pierde contra cazador normal, neutro u otro equipo que no era cazador Z en la fotografía inicial:

- continúa siendo zombie;
- deja de estar herido;
- no se suma punto de zombificación;
- no se suma una kill;
- el ganador queda neutro.

Estos cruces deben evitarse en los emparejamientos, pero tienen una resolución definida como fallback.

### 12.7. Zombie no herido que pierde

- Continúa siendo zombie.
- Pasa a herido.
- El ganador obtiene o renueva cazador Z.
- No se suma kill todavía, porque una kill exige que el zombie ya estuviera herido y el vencedor fuera cazador Z al inicio.

### 12.8. Zombie herido que gana o empata

Si gana:

- continúa zombie;
- deja de estar herido;
- obtiene cazador normal si venció a un no zombie;
- obtiene cazador Z si venció a un zombie.

Si empata:

- continúa zombie;
- deja de estar herido;
- queda temporalmente neutro.

### 12.9. Efecto de la fotografía inicial

Los puntos por zombificación y las kills se determinan con el estado al generar la ronda.

Ejemplo:

1. A comienza neutro y B comienza herido.
2. A gana a B.
3. B se convierte en zombie.
4. La comunidad de A no recibe punto porque A no era cazador en la fotografía inicial.
5. Una transferencia posterior hacia A solo afectará a la siguiente ronda.

### 12.10. Doble forfait global

Si los dos partidos terminan en doble forfait y el enfrentamiento global queda como doble forfait:

- ambos equipos reciben los puntos de derrota configurados para la clasificación;
- no cambian estados;
- no hay zombificación;
- no hay kill.

Es una excepción explícita a la limpieza de estados de un empate ordinario.

---

## 13. Transferencia de cazador o cazador Z

### 13.1. Finalidad

Permite redistribuir dentro de una comunidad un estado de cazador para mejorar las opciones de emparejamiento de la ronda siguiente. Nunca altera la resolución ni los emparejamientos de la ronda actual.

### 13.2. Momento permitido

Solo puede transferirse durante una ronda, después de que:

- el equipo origen haya cerrado su enfrentamiento;
- el equipo destino haya cerrado su enfrentamiento;
- el origen disponga de un estado de cazador o cazador Z obtenido o renovado en esa misma ronda.

No se pueden transferir estados arrastrados de rondas anteriores. Si origen o destino tiene un enfrentamiento en curso, debe responderse:

```text
No puede transferir el estado con un enfrentamiento en curso
```

Un intento fallido no queda pendiente: el usuario debe volver a ejecutar el comando cuando ambos enfrentamientos estén cerrados.

### 13.3. Requisitos

- Origen y destino pertenecen a la misma comunidad.
- Cualquiera de los dos miembros del origen puede ejecutar el comando.
- No requiere aceptación del destino.
- El destino no puede estar herido.
- El destino no puede ser cazador ni cazador Z.
- El destino puede ser zombie siempre que esté temporalmente neutro.
- El origen pierde el estado transferido.
- El destino recibe exactamente el mismo tipo.

### 13.4. Transferencias sucesivas

El estado puede transferirse varias veces en la misma ronda, por ejemplo A → B → C, siempre que cada operación cumpla las reglas. Una transferencia concreta no se deshace; devolver el estado constituye una nueva transferencia y queda registrada por separado.

### 13.5. Publicación

Toda transferencia válida debe:

- registrarse en el historial;
- publicarse inmediatamente en el canal hub;
- indicar comunidad, equipo origen, equipo destino y tipo transferido mediante emojis.

---

## 14. Clasificación de equipos

Orden definitivo:

1. Puntos de clasificación, descendente.
2. Buchholz Cut, descendente, con el mismo cálculo que el suizo actual.
3. Enfrentamiento directo, descendente.
4. Diferencia acumulada de TD, descendente.
5. ID interno del equipo, ascendente.

### Enfrentamiento directo

Dentro de cada grupo empatado a puntos se suman los puntos obtenidos contra otros equipos del mismo grupo. Si no existe un valor aplicable, se continúa con diferencia de TD y después ID.

### Emparejamientos

La clasificación sirve como base, pero el último desempate para el orden de emparejamiento es aleatorio, no el ID interno, para no favorecer sistemáticamente IDs bajos.

---

## 15. Clasificación de comunidades

Orden definitivo:

1. Puntos comunitarios por zombificaciones, descendente.
2. Zombies matados, descendente.
3. Suma de puntos suizos actuales de todos los equipos de la comunidad, descendente.
4. Empate compartido, sin forzar un orden artificial.

La suma incluye:

- victorias, empates y derrotas;
- byes;
- resultados administrativos.

Columnas mínimas:

- posición, admitiendo posiciones compartidas;
- comunidad;
- puntos por zombificaciones;
- zombies matados;
- suma de puntos suizos de sus equipos.

---

## 16. Publicaciones y visibilidad

### 16.1. Foro de resultados

Se conserva el foro hardcodeado usado por el suizo actual. Al importar o administrar cada partido individual:

- se genera y publica la imagen de resultado;
- se informa en el canal individual correspondiente.

No se eliminan publicaciones del foro al cerrar o regenerar rondas.

### 16.2. Canal general

Al terminar el segundo partido:

- se publica el resultado global;
- se informa de puntos internos, desempates usados y puntos de clasificación;
- se muestran las transiciones de estado.

### 16.3. Canal hub

Se utiliza para:

- publicar mesas e inicios de ronda;
- publicar resultados globales entre equipos;
- anunciar nuevos cazadores, cazadores Z, heridos y zombies;
- anunciar puntos comunitarios;
- anunciar zombies matados;
- anunciar transferencias de cazador;
- publicar clasificaciones y cierre de ronda.

Los mensajes del hub se conservan.

### 16.4. Canal administrativo

Se usa el ID hardcodeado existente para:

- consultas secretas de elecciones;
- errores por falta de categorías o capacidad;
- fallos de generación completa;
- incidencias que no deban revelar información en canales públicos.

---

## 17. Cierre de ronda y torneo

Una ronda se cierra cuando todos los enfrentamientos y byes están resueltos.

Al cerrar:

1. se comprueba que no quedan partidos ni enfrentamientos pendientes;
2. se consolidan puntos, estados y estadísticas;
3. se guardan snapshots de equipos y comunidades;
4. se publican los resúmenes en el hub;
5. se eliminan todos los canales generales e individuales de la ronda;
6. si quedan rondas, la ronda actual queda cerrada y no se genera ni se habilita automáticamente la siguiente;
7. si era la última, el torneo pasa a `FINALIZADO` y se publican ambas clasificaciones finales.

Cuando queden rondas, un comisario deberá ejecutar explícitamente `!comunidades_generar_ronda <torneo_id> <ronda>` para crear la siguiente. La generación conserva su regla de todo o nada: si falla, la ronda anterior permanece cerrada, no se guarda parcialmente la nueva ronda y se informa del error en el canal administrativo hardcodeado.

Los estados temporales vigentes se arrastran a la siguiente ronda cuando esta se genere. Ser zombie permanece siempre.

---

## 18. Casos administrativos y errores esperados

La implementación debe rechazar de forma explícita:

- comunidad inexistente;
- comunidad duplicada;
- modificación de comunidades tras generar ronda 1;
- equipo duplicado en el torneo;
- usuario ya inscrito en otro equipo del torneo;
- equipo con menos o más de dos miembros;
- raza no perteneciente exactamente a la lista permitida;
- selección fuera del canal correspondiente;
- selección hecha por alguien ajeno al equipo;
- selección de un usuario ajeno al equipo;
- cambio de elección después del bloqueo;
- transferencia entre comunidades;
- transferencia con enfrentamiento en curso;
- transferencia de un estado procedente de una ronda anterior;
- transferencia a herido, cazador o cazador Z;
- generación que requiera enfrentar la misma comunidad;
- creación de canales sin categorías configuradas o con todas a 40 canales;
- consulta secreta fuera del canal administrativo;
- importación API de usuarios sin `id_bloodbowl` informado.

Las operaciones complejas deben ser atómicas: un error no debe dejar rondas parciales, canales huérfanos evitables, selecciones bloqueadas sin partidos ni puntuaciones aplicadas a medias.

---

## 19. Flujo operativo de ejemplo

```text
!comunidades_crear "Copa de Comunidades" 5 2026-07-01 23:59 7 1497290209505710120
!comunidades_set_puntos_equipo 1 3 1 0 1.5
!comunidades_set_puntos_individuales 1 3 1 0

!comunidades_add_comunidad 1 Butter
!comunidades_add_comunidad 1 Hispana
!comunidades_add_comunidad 1 PdM

!comunidades_add_categoria_enfrentamientos 1 111111111111111111
!comunidades_add_categoria_enfrentamientos 1 222222222222222222
!comunidades_add_categoria_partidos 1 333333333333333333
!comunidades_add_categoria_partidos 1 444444444444444444

!comunidades_add_equipo 1 "Los Rompecráneos" Butter @Jugador1 "Orcos" @Jugador2 "Skaven"
!comunidades_add_equipo 1 "La Guardia" Hispana @Jugador3 "Humanos" @Jugador4 "Enanos"

!comunidades_generar_ronda 1 1
```

En cada canal general:

```text
/comunidades_seleccion_atacante usuario:@Jugador1
```

Actualización y consultas:

```text
!comunidades_actualizar 1 1
/comunidades_consulta_ronda torneo_id:1 ronda:1
/comunidades_clasificacion_equipos torneo_id:1
/comunidades_clasificacion_comunidades torneo_id:1
/comunidades_consulta_estados torneo_id:1
```

Consulta secreta administrativa:

```text
!comunidades_consulta_elecciones 1 1
```

---

## 20. Decisiones cerradas y asuntos de implementación

### Decisiones cerradas

Todas las reglas funcionales de este documento se consideran confirmadas, en particular:

- entidades separadas del suizo individual;
- parejas de exactamente dos usuarios;
- comunidades configurables antes del inicio;
- dos puntuaciones independientes;
- dos partidos BO1 por enfrentamiento;
- selección secreta de atacante;
- prohibición absoluta de misma comunidad;
- orden de prioridades y fallbacks;
- máquina de estados y fotografía inicial;
- transferencias solo con ambos enfrentamientos cerrados;
- clasificación de equipos y comunidades;
- categorías ordenadas con límite de 40 canales;
- conservación del foro y hub;
- eliminación de canales al cerrar ronda;
- forzado con ambos atacantes obligatorios, reemplazo de elecciones y creación atómica;
- configuración de `idCompBbowl` mediante `!comunidades_set_competicion`, solo en estado `CREADO`;
- cierre sin generación automática de la siguiente ronda;
- mensajes iniciales y posteriores configurables en base de datos desde la primera versión, sin comandos de edición en la v1;
- correspondencia directa entre las 23 razas canónicas y `Iconos/<nombre canónico>.png`, sin aliases.

### Detalles que la tarea de implementación deberá concretar sin cambiar reglas

- nombres físicos definitivos de las demás tablas y constraints;
- IDs hardcodeados existentes del foro y canal administrativo;
- texto inicial de las plantillas configurables, sus marcadores admitidos y el diseño visual de embeds;
- estrategia técnica para garantizar el rollback coordinado de base de datos y canales Discord exigido por las operaciones atómicas;
- comportamiento exacto ya existente de PJ/PG/PE/PP y Buchholz para bye, que debe reutilizarse sin desviaciones;

Si una futura tarea descubre una ambigüedad no cubierta, debe detener la implementación y pedir confirmación antes de introducir una regla nueva.
