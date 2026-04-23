# Operativa de torneo suizo (LombardBot)

Este documento resume el flujo completo de gestión de un torneo suizo con LombardBot, con ejemplos listos para copiar/pegar usando comandos `!` y `/`.

---

## 1) Creación de torneo

Crea el torneo indicando nombre, número de rondas, modo (`ida` o `idavuelta`), formato (`bo1|bo3|bo5`) y fecha/hora límite de la ronda 1.

### Comando `!` (copy/paste)
```txt
!suizo_crear "ButterCup_Suizo_S7" 5 ida bo1 2026-05-01 23:59 123456789012345678
```

> El último parámetro (`canal_hub_id`) es opcional. Si no quieres canal hub, omítelo.

Opcionalmente, ajusta puntuación:

```txt
!suizo_set_puntos 12 3 1 0 1.5
```

---

## 2) Alta de jugadores

Puedes dar altas individuales o en lote.

### Comando `!` (individual)
```txt
!suizo_add_jugador 12 @CoachUno
!suizo_add_jugador 12 @CoachDos "Elfos Silvanos"
```

### Comando `!` (lote)
```txt
!suizo_add_lote 12 @CoachUno @CoachDos @CoachTres
```

---

## 3) Generación de ronda

Genera una ronda concreta (normalmente empiezas con la 1).

### Comando `!` (copy/paste)
```txt
!suizo_generar_ronda 12 1
```

Si necesitas rehacer una ronda abierta sin resultados:

```txt
!suizo_regenerar_ronda 12 1
```

Consulta de emparejamientos y clasificación con `/`:

### Comandos `/` (copy/paste)
```txt
/suizo_consulta_ronda torneo_id:12 ronda:1
/suizo_consulta_clasificacion torneo_id:12
/suizo_consulta_estado_canales torneo_id:12 ronda:1
```

---

## 4) Actualización diaria

Para importar resultados desde la API y cerrar mesas automáticamente.

### Comando `!` (copy/paste)
```txt
!actualiza_suizo 12
```

Si quieres procesar todos los partidos encontrados en una pasada:

```txt
!actualiza_suizo 12 1
```

Recomendación operativa diaria:
1. Ejecutar `!actualiza_suizo <torneo_id>`.
2. Revisar `/suizo_consulta_ronda`.
3. Revisar `/suizo_consulta_clasificacion`.

---

## 5) Administración de no jugados

Cuando un partido no se ha jugado en plazo, administra el resultado manualmente.

### Comando `!` (forfait / empate admin / doble forfait)
```txt
!suizo_admin_resultado 12 2 4 forfeit_local
!suizo_admin_resultado 12 2 5 forfeit_visitante
!suizo_admin_resultado 12 2 6 empate_admin
!suizo_admin_resultado 12 2 7 doble_forfeit
```

### Comando `!` (marcador manual)
```txt
!suizo_admin_resultado 12 2 8 manual 2 1
```

---

## 6) Drops y altas tardías

### Drop (retirada)
```txt
!suizo_drop 12 @CoachTres abandono por inactividad
```

### Alta tardía
```txt
!suizo_add_tardio 12 @CoachNuevo
!suizo_add_tardio 12 @CoachNuevo "Skaven"
```

> El alta tardía entra desde la siguiente ronda disponible y con ajuste inicial de puntos calculado por el sistema.

---

## 7) Cierre automático y fin de torneo

El cierre ocurre durante `!actualiza_suizo` cuando no quedan mesas pendientes en la ronda abierta:
- Se cierra la ronda.
- Se guarda snapshot de standings.
- Si no es la última ronda, se genera automáticamente la siguiente.
- Si es la última ronda, el torneo pasa a finalizado y se publica clasificación final.

### Comando `!` clave
```txt
!actualiza_suizo 12
```

### Comandos `/` para seguimiento final
```txt
/suizo_consulta_clasificacion torneo_id:12
/suizo_consulta_desempates torneo_id:12
/suizo_consulta_jugador torneo_id:12 usuario:@CoachUno
```

---

## Flujo rápido recomendado (checklist)

```txt
!suizo_crear "MiTorneo" 5 ida bo1 2026-05-01 23:59
!suizo_add_lote 12 @Coach1 @Coach2 @Coach3 @Coach4 @Coach5 @Coach6
!suizo_generar_ronda 12 1
!actualiza_suizo 12
!suizo_admin_resultado 12 1 3 forfeit_local
!actualiza_suizo 12
!suizo_add_tardio 12 @Coach7
!suizo_drop 12 @Coach2 abandono voluntario
!actualiza_suizo 12
```

Y para consulta rápida de staff/jugadores:

```txt
/suizo_consulta_ronda torneo_id:12
/suizo_consulta_clasificacion torneo_id:12
```
