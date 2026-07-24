# Inventario de funciones de comunidades en `LombardBot.py`

Este documento es la fuente de verdad inicial para decidir qué piezas del bloque de comunidades pueden moverse fuera de `LombardBot.py` sin cambiar comportamiento.

## Objetivo

- Inventariar todas las funciones cuyo nombre contiene `comunidades`.
- Clasificarlas por responsabilidad dominante.
- Identificar dependencias y riesgos antes de extraer código.
- Proponer una estrategia de movimiento incremental que preserve el comportamiento observable de los comandos Discord.

## Alcance

El foco principal es el bloque comprendido entre `comunidades_crear` y `comunidades_regenerar_ronda`. También se incluye cualquier función adicional del archivo cuyo nombre contenga `comunidades` y quede fuera de ese bloque.

## Categorías

1. **Comandos Discord**: entrypoints decorados con `@bot.command` o `@bot.tree.command`; deberían quedarse como adaptadores finos.
2. **Servicio de aplicación**: orquestación de casos de uso, validación de argumentos no estrictamente Discord, sesiones y llamadas a dominio.
3. **Formateo/presentación**: construcción de texto, etiquetas, formato público, imágenes o normalización para salida.
4. **Infraestructura Discord**: resolución/creación/eliminación de canales, hilos, miembros, permisos y avisos administrativos.
5. **Integración Blood Bowl/API**: lectura, validación y conciliación de datos externos de Blood Bowl.
6. **Publicación de resultados**: publicación idempotente de mensajes, imágenes, clasificaciones, transferencias o resultados.
7. **Cierre/regeneración de rondas**: consolidación, cierre de ventanas, limpieza y regeneración de rondas/canales.

## Principios para mover código

- No cambiar nombres de comandos, argumentos, permisos ni textos de respuesta en la primera extracción.
- Extraer primero funciones privadas con menos acoplamiento a `bot`, `ctx` o `interaction`.
- Mantener los commits pequeños: presentación, publicación, Discord infra, integración API y cierre/regeneración deberían moverse por separado.
- En la primera fase, conservar imports reexportados o wrappers en `LombardBot.py` si reduce riesgo.
- Donde una función mezcla categorías, extraer subfunciones internas antes de mover el entrypoint.
- Mantener intacta la idempotencia de publicación basada en BD.
- Mantener el orden actual de commits/rollbacks alrededor de operaciones Discord y SQL.

## Inventario principal

| Líneas | Función | Categoría dominante | Decorador | Descripción / decisión sugerida |
|---:|---|---|---|---|
| 4374-4391 | `_ejecutar_configuracion_comunidades` | Servicio de aplicación | - | Wrapper transaccional de configuración. Mover a capa de aplicación si recibe fábrica de sesión y callback de respuesta. |
| 4395-4441 | `comunidades_crear` | Comandos Discord | `@bot.command` | Entry point de creación de torneo. Dejar como adaptador; mover parsing/servicio si crece. |
| 4445-4461 | `comunidades_set_competicion` | Comandos Discord | `@bot.command` | Entry point para configurar competición Blood Bowl. Dejar adaptador; delega bien. |
| 4465-4497 | `comunidades_set_puntos_equipo` | Comandos Discord | `@bot.command` | Entry point de puntuación por equipo. Puede conservarse fino y mover parseo común. |
| 4501-4531 | `comunidades_set_puntos_individuales` | Comandos Discord | `@bot.command` | Entry point de puntuación individual. Similar al anterior. |
| 4550-4557 | `_etiqueta_equipo_escalar_comunidades` | Formateo/presentación | - | Helper puro de presentación. Candidato temprano a `presentacion`. |
| 4561-4578 | `comunidades_add_comunidad` | Comandos Discord | `@bot.command` | Entry point de alta de comunidad. Dejar adaptador. |
| 4581-4604 | `_comunidades_add_categoria` | Servicio de aplicación | - | Helper común con mezcla de permisos, validación Discord y servicio. Extraer con cuidado; quizá separarlo en validación Discord + caso de uso. |
| 4608-4615 | `comunidades_add_categoria_partidos` | Comandos Discord | `@bot.command` | Entry point fino. Dejar adaptador. |
| 4619-4628 | `comunidades_add_categoria_enfrentamientos` | Comandos Discord | `@bot.command` | Entry point fino. Dejar adaptador. |
| 4632-4670 | `comunidades_add_equipo` | Comandos Discord | `@bot.command` | Entry point de alta de equipo. Dejar adaptador; dominio ya parece externo. |
| 4673-4676 | `_normalizar_nombre_canal_comunidades` | Formateo/presentación | - | Normalización de nombre de canal. Aunque se usa en Discord, es helper puro. |
| 4679-4702 | `_resumen_ronda_comunidades` | Formateo/presentación | - | Texto de resumen de ronda. Candidato temprano a presentación. |
| 4705-4715 | `_detalle_error_categorias_comunidades` | Formateo/presentación | - | Formatea errores de categorías. Candidato a presentación/admin. |
| 4718-4724 | `_publicar_error_administrativo_comunidades` | Infraestructura Discord | - | Envío a administración y canal. Mover a adaptador Discord compartido. |
| 4732-4749 | `comunidades_seleccion_atacante` | Comandos Discord | `@bot.tree.command` | Slash command. Dejar entrypoint; la lógica ya delega en servicio externo. |
| 4752-4762 | `_resolver_miembro_guild_comunidades` | Infraestructura Discord | - | Resolución de miembro guild/cache/fetch. Mover a infra Discord. |
| 4766-4769 | `_es_canal_administrativo_comunidades` | Infraestructura Discord | - | Validación de canal administrativo. Mover a infra/políticas Discord. |
| 4772-4802 | `_formatear_consulta_elecciones_comunidades` | Formateo/presentación | - | Presentación de elecciones. Mover a presentación. |
| 4806-4833 | `comunidades_consulta_elecciones` | Comandos Discord | `@bot.command` | Entry point administrativo. Dejar adaptador; mover consulta/formato alrededor. |
| 4836-4842 | `_comunidades_procesar_todos` | Servicio de aplicación | - | Parseo de opción `todos`. Puede moverse a aplicación o parsing de comando. |
| 4845-4868 | `_extraer_resultado_api_comunidades` | Integración Blood Bowl/API | - | Valida payload API. Candidato claro a adaptador Blood Bowl. |
| 4871-4876 | `_nombre_usuario_comunidades` | Formateo/presentación | - | Nombre visible con fallback. Presentación. |
| 4879-4888 | `_localizar_partido_api_comunidades` | Integración Blood Bowl/API | - | Conciliación API vs partidos internos. Adaptador/servicio de integración. |
| 4891-4894 | `_orientar_marcador_api_comunidades` | Integración Blood Bowl/API | - | Orientación de marcador externo. Adaptador API. |
| 4898-5231 | `comunidades_actualizar` | Integración Blood Bowl/API | `@bot.command` | Entry point con mucha lógica: API, BD, publicación y cierre. Debe dividirse antes de mover: comando fino + servicio de actualización + publicador + cierre. |
| 5234-5244 | `_resolver_hilo_resultados_comunidades_sin_bd` | Infraestructura Discord | - | Localiza/crea hilo sin idempotencia BD. Infra Discord, aunque usado por publicación antigua. |
| 5247-5271 | `publicar_imagen_resultado_partido_comunidades_sin_bd` | Publicación de resultados | - | Publica imagen sin registrar idempotencia. Mantener separado del flujo idempotente. |
| 5275-5397 | `comunidades_publica_antiguos` | Comandos Discord | `@bot.command` | Entry point de publicación de históricos. Dejar adaptador; mover búsqueda/publicación. |
| 5403-5440 | `_contexto_publicacion_comunidades` | Publicación de resultados | - | Context manager SQL para idempotencia. Mover junto a publicación. |
| 5443-5468 | `_reservar_publicacion_comunidades` | Publicación de resultados | - | Reserva publicación. Crítico para no duplicar mensajes. |
| 5471-5488 | `_finalizar_publicacion_comunidades` | Publicación de resultados | - | Finaliza estado de publicación. Crítico para idempotencia. |
| 5491-5505 | `_estado_publicacion_comunidades` | Publicación de resultados | - | Consulta estado idempotente. Mover con publicador. |
| 5508-5540 | `_resolver_hilo_resultados_publicacion_comunidades` | Publicación de resultados | - | Hilo de foro con reserva idempotente. Publicación + infra Discord. |
| 5543-5570 | `_enviar_unico_comunidades` | Publicación de resultados | - | Envío idempotente simple. Pieza central de publicación. |
| 5573-5591 | `_enviar_largo_unico_comunidades` | Publicación de resultados | - | Envío idempotente para mensajes largos. Pieza central de publicación. |
| 5594-5606 | `_buscar_hilo_resultados_comunidades` | Infraestructura Discord | - | Busca hilos activos/archivados. Infra Discord. |
| 5609-5622 | `_raza_usuario_partido_comunidades` | Formateo/presentación | - | Dato de presentación para resultado/imagen. |
| 5625-5638 | `_datos_api_imagen_comunidades` | Integración Blood Bowl/API | - | Extrae datos API para imagen. Adaptador API usado por presentación. |
| 5641-5672 | `_comunidad_lado_partido_comunidades` | Formateo/presentación | - | Determina comunidad por lado del partido. Presentación/datos auxiliares. |
| 5675-5682 | `_comunidades_lados_partido_comunidades` | Formateo/presentación | - | Calcula comunidades local/visitante. Presentación. |
| 5685-5747 | `_crear_imagen_resultado_comunidades` | Formateo/presentación | - | Genera imagen de resultado. Mover a presentación, manteniendo dependencia `Imagenes`. |
| 5750-5757 | `_estado_con_emojis_comunidades` | Formateo/presentación | - | Formatea estado con emojis. Presentación pura. |
| 5769-5771 | `_estado_publico_comunidades` | Formateo/presentación | - | Normaliza estado público. Presentación pura. |
| 5774-5776 | `_decimal_publico_comunidades` | Formateo/presentación | - | Formatea decimal público. Presentación pura. |
| 5779-5781 | `_mencion_publica_comunidades` | Formateo/presentación | - | Mención pública. Presentación. |
| 5784-5787 | `_cabecera_publica_comunidades` | Formateo/presentación | - | Cabecera común de consultas. Presentación. |
| 5790-5808 | `_ejecutar_consulta_publica_comunidades` | Servicio de aplicación | - | Wrapper de consulta slash: sesión, defer y formateo. Puede moverse a aplicación/adaptador. |
| 5851-5859 | `_formatear_comunidades_publico` | Formateo/presentación | - | Formatea clasificación de comunidades. Presentación. |
| 5911-5912 | `comunidades_consulta_ronda` | Comandos Discord | `@bot.tree.command` | Slash command fino. Dejar adaptador. |
| 5917-5918 | `comunidades_clasif_equipos` | Comandos Discord | `@bot.tree.command` | Slash command fino. Dejar adaptador. |
| 5923-5924 | `comunidades_clasif_comunidades` | Comandos Discord | `@bot.tree.command` | Slash command fino. Dejar adaptador. |
| 5929-5930 | `comunidades_consulta_equipo` | Comandos Discord | `@bot.tree.command` | Slash command fino. Dejar adaptador. |
| 5935-5936 | `comunidades_consulta_estados` | Comandos Discord | `@bot.tree.command` | Slash command fino. Dejar adaptador. |
| 5941-5942 | `comunidades_estado_canales` | Comandos Discord | `@bot.tree.command` | Slash command fino. Dejar adaptador. |
| 5945-5955 | `_texto_partido_comunidades` | Formateo/presentación | - | Mensaje de resultado individual. Presentación. |
| 5958-5969 | `_desempate_enfrentamiento_comunidades` | Formateo/presentación | - | Explicación del desempate. Presentación. |
| 5972-6015 | `_textos_transiciones_comunidades` | Formateo/presentación | - | Textos de transiciones y efectos. Presentación con consultas BD. |
| 6018-6041 | `_texto_global_comunidades` | Formateo/presentación | - | Mensaje global para canal/hub. Presentación con datos de enfrentamiento. |
| 6044-6058 | `publicar_transferencia_comunidades_en_hub` | Publicación de resultados | - | Publica transferencia en hub idempotentemente. Publicación. |
| 6069-6133 | `comunidades_transferir_cazador` | Comandos Discord | `@bot.tree.command` | Slash command que mezcla caso de uso y publicación. Dejar entrypoint y extraer orquestación. |
| 6136-6224 | `publicar_resultado_partido_comunidades` | Publicación de resultados | - | Publicación idempotente de partido, imagen, global y hub. Mover como unidad después de presentación/infra. |
| 6227-6265 | `_reintentar_publicaciones_partidos_comunidades` | Publicación de resultados | - | Reintentos por partidos. Mover con publicador. |
| 6268-6302 | `_reintentar_publicaciones_ronda_comunidades` | Publicación de resultados | - | Reintentos por ronda. Mover con publicador. |
| 6305-6346 | `_eliminar_canales_ronda_comunidades` | Cierre/regeneración de rondas | - | Limpieza de canales al cierre. Mezcla cierre e infra Discord; extraer a servicio de cierre con adaptador de canales. |
| 6349-6405 | `_post_cierre_ronda_comunidades` | Cierre/regeneración de rondas | - | Publica clasificaciones de cierre. Depende de consultas, presentación y publicación idempotente. |
| 6408-6420 | `_consolidar_cierre_ronda_comunidades` | Cierre/regeneración de rondas | - | Consolida cierre en BD y commit. Servicio de cierre. |
| 6423-6439 | `_resolver_canal_notificacion_comunidades` | Infraestructura Discord | - | Resolución de canal por id. Infra Discord. |
| 6442-6465 | `_datos_resultado_admin_comunidades` | Servicio de aplicación | - | Parseo de resultado admin. Servicio/parsing. |
| 6468-6500 | `_mensaje_resultado_admin_comunidades` | Formateo/presentación | - | Mensaje de resultado admin. Presentación. |
| 6504-6592 | `comunidades_admin_partido` | Comandos Discord | `@bot.command` | Entry point de resultado admin. Extraer registro/publicación/cierre a orquestador. |
| 6596-6653 | `comunidades_forzar_crear_partidos` | Comandos Discord | `@bot.command` | Entry point para forzar elecciones y materializar canales. Mezcla servicio y Discord. |
| 6656-6796 | `_crear_canales_ronda_comunidades` | Infraestructura Discord | - | Crea canales, permisos, mensajes iniciales, resumen y cierre. Alto acoplamiento; extraer tarde. |
| 6799-6830 | `_eliminar_canales_para_regeneracion_comunidades` | Cierre/regeneración de rondas | - | Limpieza estricta previa a regeneración. Mantener con regeneración/infra canales. |
| 6834-6920 | `comunidades_generar_ronda` | Comandos Discord | `@bot.command` | Entry point de generación. Extraer orquestación; conservar adaptador. |
| 6924-6958 | `comunidades_cerrar_transferencias` | Comandos Discord | `@bot.command` | Entry point de cierre administrativo. Extraer cierre/limpieza. |
| 6962-7086 | `comunidades_regenerar_ronda` | Comandos Discord | `@bot.command` | Entry point de regeneración. Extraer validación/orquestación; conservar comando. |

## Función adicional fuera del bloque principal

| Líneas | Función | Categoría dominante | Decorador | Descripción / decisión sugerida |
|---:|---|---|---|---|
| 9684-9814 | `func_proximos_partidos_suizo_comunidades` | Formateo/presentación | - | Genera anuncio/listado de próximos partidos suizo comunidades. Revisar junto a presentación de calendarios, no junto al bloque principal de rondas. |

## Agrupación recomendada por módulos destino

### `comunidades_discord_commands.py`

Mantener aquí o dejar en `LombardBot.py` como adaptadores hasta el final:

- `comunidades_crear`
- `comunidades_set_competicion`
- `comunidades_set_puntos_equipo`
- `comunidades_set_puntos_individuales`
- `comunidades_add_comunidad`
- `comunidades_add_categoria_partidos`
- `comunidades_add_categoria_enfrentamientos`
- `comunidades_add_equipo`
- `comunidades_seleccion_atacante`
- `comunidades_consulta_elecciones`
- `comunidades_actualizar`
- `comunidades_publica_antiguos`
- `comunidades_consulta_ronda`
- `comunidades_clasif_equipos`
- `comunidades_clasif_comunidades`
- `comunidades_consulta_equipo`
- `comunidades_consulta_estados`
- `comunidades_estado_canales`
- `comunidades_transferir_cazador`
- `comunidades_admin_partido`
- `comunidades_forzar_crear_partidos`
- `comunidades_generar_ronda`
- `comunidades_cerrar_transferencias`
- `comunidades_regenerar_ronda`

### `comunidades_presentacion.py`

Candidatas de menor riesgo:

- `_etiqueta_equipo_escalar_comunidades`
- `_normalizar_nombre_canal_comunidades`
- `_resumen_ronda_comunidades`
- `_detalle_error_categorias_comunidades`
- `_formatear_consulta_elecciones_comunidades`
- `_nombre_usuario_comunidades`
- `_raza_usuario_partido_comunidades`
- `_comunidad_lado_partido_comunidades`
- `_comunidades_lados_partido_comunidades`
- `_crear_imagen_resultado_comunidades`
- `_estado_con_emojis_comunidades`
- `_estado_publico_comunidades`
- `_decimal_publico_comunidades`
- `_mencion_publica_comunidades`
- `_cabecera_publica_comunidades`
- `_formatear_comunidades_publico`
- `_texto_partido_comunidades`
- `_desempate_enfrentamiento_comunidades`
- `_textos_transiciones_comunidades`
- `_texto_global_comunidades`
- `_mensaje_resultado_admin_comunidades`
- `func_proximos_partidos_suizo_comunidades`

### `comunidades_discord_infra.py`

- `_publicar_error_administrativo_comunidades`
- `_resolver_miembro_guild_comunidades`
- `_es_canal_administrativo_comunidades`
- `_resolver_hilo_resultados_comunidades_sin_bd`
- `_buscar_hilo_resultados_comunidades`
- `_resolver_canal_notificacion_comunidades`
- `_crear_canales_ronda_comunidades`

### `comunidades_bloodbowl_api.py`

- `_extraer_resultado_api_comunidades`
- `_localizar_partido_api_comunidades`
- `_orientar_marcador_api_comunidades`
- `_datos_api_imagen_comunidades`
- La lógica interna de actualización de `comunidades_actualizar`, después de separar el entrypoint Discord.

### `comunidades_publicacion.py`

- `publicar_imagen_resultado_partido_comunidades_sin_bd`
- `_contexto_publicacion_comunidades`
- `_reservar_publicacion_comunidades`
- `_finalizar_publicacion_comunidades`
- `_estado_publicacion_comunidades`
- `_resolver_hilo_resultados_publicacion_comunidades`
- `_enviar_unico_comunidades`
- `_enviar_largo_unico_comunidades`
- `publicar_transferencia_comunidades_en_hub`
- `publicar_resultado_partido_comunidades`
- `_reintentar_publicaciones_partidos_comunidades`
- `_reintentar_publicaciones_ronda_comunidades`

### `comunidades_rondas.py`

- `_eliminar_canales_ronda_comunidades`
- `_post_cierre_ronda_comunidades`
- `_consolidar_cierre_ronda_comunidades`
- `_eliminar_canales_para_regeneracion_comunidades`
- La lógica interna de `comunidades_generar_ronda`, `comunidades_cerrar_transferencias` y `comunidades_regenerar_ronda`.

### `comunidades_app.py`

- `_ejecutar_configuracion_comunidades`
- `_comunidades_add_categoria`
- `_comunidades_procesar_todos`
- `_ejecutar_consulta_publica_comunidades`
- `_datos_resultado_admin_comunidades`
- Orquestadores extraídos desde comandos complejos.

## Orden de extracción recomendado

1. **Presentación pura**: mover helpers que devuelven strings o valores simples. Riesgo bajo.
2. **Integración Blood Bowl/API pura**: mover validadores y conciliadores de payload API. Riesgo bajo-medio.
3. **Publicación idempotente**: mover como unidad, manteniendo pruebas manuales/reintentos. Riesgo medio por interacción BD/Discord.
4. **Infraestructura Discord**: mover resolutores y helpers de canales/hilos. Riesgo medio por dependencias de `ctx`, `guild`, `discord` y constantes.
5. **Cierre/regeneración**: mover consolidación y limpieza con tests o fixtures si existen. Riesgo alto por transacciones y canales.
6. **Comandos complejos**: adelgazar `comunidades_actualizar`, `comunidades_admin_partido`, `comunidades_generar_ronda` y `comunidades_regenerar_ronda` al final.

## Funciones con mezcla de responsabilidades que requieren especial cuidado

### `comunidades_actualizar`

Responsabilidades mezcladas:

- Validación de permisos y argumento Discord.
- Lectura de torneo/rondas/partidos en BD.
- Llamada a API Blood Bowl.
- Conciliación de coaches y partidos.
- Registro de resultados.
- Publicación de resultados.
- Reintento de publicaciones.
- Consolidación de cierre de ronda.
- Construcción de resumen para Discord.

Extracción sugerida:

1. Extraer parseo/validación API.
2. Extraer servicio `actualizar_resultados_comunidades_desde_api` que devuelva un objeto resumen.
3. Extraer formateador del resumen.
4. Dejar el comando solo con permisos, sesión, llamada y envío.

### `_crear_canales_ronda_comunidades`

Responsabilidades mezcladas:

- Consulta de torneo/ronda/enfrentamientos.
- Resolución de miembros Discord.
- Construcción de permisos.
- Creación de canales.
- Persistencia de ids de canal.
- Publicación de mensajes iniciales.
- Publicación de resumen en hub.
- Consolidación de cierre si procede.

Extracción sugerida:

1. Extraer formateo de nombres/permisos.
2. Extraer creador de canales con interfaz inyectable.
3. Separar publicación inicial de persistencia.
4. Mantener rollback/commit igual durante el primer movimiento.

### `publicar_resultado_partido_comunidades`

Responsabilidades mezcladas:

- Resolución de canales.
- Envío idempotente a canal individual.
- Resolución/creación de hilo de foro.
- Generación y limpieza de imagen temporal.
- Publicación global en canal general y hub.
- Acumulación de avisos para reintento.

Extracción sugerida:

Mover como unidad a `comunidades_publicacion.py` después de mover sus helpers directos. No cambiar claves de idempotencia: `partido-canal`, `hilo-foro`, `partido-foro`, `global-general`, `global-hub`.

### `comunidades_regenerar_ronda`

Responsabilidades mezcladas:

- Validación de permisos/guild/rol.
- Validación de estado de ronda.
- Detección de rondas posteriores.
- Selección de categorías.
- Recopilación y eliminación de canales.
- Regeneración de emparejamientos.
- Recreación de canales.
- Publicación de resumen y cierre automático si aplica.

Extracción sugerida:

1. Extraer validaciones de ronda a servicio puro de BD.
2. Extraer limpieza de canales a infra/rondas.
3. Reusar `_crear_canales_ronda_comunidades` hasta que se estabilice.
4. Dejar comando como adaptador final.

## Dependencias críticas a vigilar

- Constantes de estado: `RONDA_ABIERTA`, `RONDA_PENDIENTE_TRANSFERENCIAS`, `TORNEO_EN_CURSO`, `PARTIDO_PENDIENTE`, `PARTIDO_EN_CURSO`, `PARTIDO_FINALIZADO`, `PARTIDO_ADMINISTRADO`, `ENFRENTAMIENTO_PARTIDOS_CREADOS`, `ENFRENTAMIENTO_EN_CURSO`, `ENFRENTAMIENTO_CERRADO`, `ENFRENTAMIENTO_ADMINISTRADO`.
- Constantes Discord/canales: `FORO_RESULTADOS_COMUNIDADES_ID`, `CANAL_ANUNCIOS_SUIZO_COMUNIDADES_ID`, `canales_permitidos`, rol `Comisario`.
- Módulos externos usados directa o indirectamente: `GestorSQL`, `UtilesDiscord`, `APIBbowl`, `Imagenes`, `discord`, `File`, `sessionmaker`.
- Servicios de dominio ya existentes: funciones como `crear_torneo_comunidades`, `generar_ronda_comunidades`, `registrar_resultado_partido_comunidades`, `procesar_cierre_ronda_comunidades_si_corresponde`, consultas públicas y operaciones de transferencia.
- Idempotencia de publicación: tabla/modelo `ComunidadesPublicacion` y claves de publicación.

## Checklist para cada movimiento

- [ ] Confirmar que la función movida no depende de variables globales no importadas explícitamente.
- [ ] Añadir imports explícitos en el nuevo módulo.
- [ ] Mantener firma original o crear wrapper compatible en `LombardBot.py`.
- [ ] Ejecutar comprobación de sintaxis/import si el entorno lo permite.
- [ ] Probar al menos el comando afectado en un entorno Discord de staging si existe.
- [ ] Verificar que los mensajes públicos no cambian salvo que el cambio sea intencionado.
- [ ] Verificar que no se duplican publicaciones tras reintentos.
- [ ] Verificar commits/rollbacks en rutas de error.

## Primeros candidatos de bajo riesgo

1. `_estado_publico_comunidades`
2. `_decimal_publico_comunidades`
3. `_mencion_publica_comunidades`
4. `_estado_con_emojis_comunidades`
5. `_normalizar_nombre_canal_comunidades`
6. `_comunidades_procesar_todos`
7. `_extraer_resultado_api_comunidades`
8. `_orientar_marcador_api_comunidades`
9. `_nombre_usuario_comunidades`
10. `_detalle_error_categorias_comunidades`

## Cambios que conviene evitar en la primera fase

- Cambiar nombres o descripciones de slash commands.
- Cambiar formato exacto de mensajes enviados al usuario.
- Cambiar claves de idempotencia de publicación.
- Cambiar el orden de `session.commit()`, `session.rollback()` y operaciones Discord.
- Extraer simultáneamente comandos y dominio si no hay pruebas automatizadas alrededor.
- Reordenar imports masivamente en `LombardBot.py` sin necesidad.
