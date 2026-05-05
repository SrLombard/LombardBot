
## 1) Creación de torneo

Crea el torneo indicando nombre, número de rondas, modo (`ida` o `idavuelta`), formato (`bo1|bo3|bo5`) y fecha/hora límite de la ronda 1.

### Comando
```txt
!suizo_crear "ButterCup_Suizo_S7" 5 ida bo1 2026-05-03 23:59 1497290209505710120

Agregar id competición a suizo_torneo.idCompBbowl
```

> El último parámetro (`canal_hub_id`) es opcional. Si no quieres canal hub, omítelo.

Argumentos
    nombre (str): nombre del torneo.
        Si tiene espacios, conviene usar comillas: "Mi Torneo".
    rondas (int): número total de rondas.
        Debe ser >= 1.
    ida_vuelta (str): modo del torneo.
        Valores válidos (case-insensitive): ida o idavuelta.
        Internamente guarda: ida=0, idavuelta=1.
    formato_serie (str): formato de cada emparejamiento.
        Válidos: bo1, bo3, bo5 (internamente se normaliza a BO1/BO3/BO5).
    fecha_fin (str): fecha fin ronda 1 en formato YYYY-MM-DD.
    hora_fin (str): hora fin ronda 1 en formato HH:MM.
    canal_hub_id (int, opcional): canal Discord donde publicar resumen de rondas.
Qué hace
    Crea un torneo suizo en BD con estado inicial CREADO.
    Configura puntuación por defecto:
        win=3, draw=1, loss=0, bye=1.5.
    Guarda fecha fin de ronda 1 y otros metadatos.
Restricciones/errores
    Solo rol Comisario.
    Falla si:
        rondas < 1
        ida_vuelta inválido
        formato_serie inválido
        fecha/hora con formato incorrecto

Opcionalmente, ajusta puntuación:

```txt
!suizo_set_puntos 1 3 1 0 1.5
```
Argumentos
    torneo_id (int)
    win, draw, loss, bye (str parseado a Decimal)
        Permite decimales (1.5, 2, etc.)

---

## 2) Alta de jugadores

Puedes dar altas individuales o en lote.

### Comando `!` (individual)
```txt
!suizo_add_jugador 1 @CoachUno
!suizo_add_jugador 1 @CoachDos "Elfos Silvanos"
```

### Comando `!` (lote)
```txt
!suizo_add_lote 1 @CoachUno @CoachDos @CoachTres
```
!suizo_importar_inscripcion siempre DESPUES de !actualizar_usuarios_inscripcion
---

## 3) Generación de ronda

Genera una ronda concreta (normalmente empiezas con la 1).

### Comando `!` (copy/paste)
```txt
!suizo_generar_ronda 12 1

```

Si necesitas rehacer una ronda abierta sin resultados:

```txt
!suizo_regenerar_ronda 1 1
```

Consulta de emparejamientos y clasificación con `/`:

### Comandos `/` (copy/paste)
```txt
/suizo_consulta_ronda torneo_id:1 ronda:1
/suizo_consulta_clasificacion torneo_id:1
/suizo_consulta_estado_canales torneo_id:1 ronda:1
```

---

## 4) Actualización diaria

Para importar resultados desde la API y cerrar mesas automáticamente.

### Comando `!` (copy/paste)
```txt
!actualiza_suizo 1
```

Si quieres procesar todos los partidos encontrados en una pasada:

```txt
!actualiza_suizo 1 1
```

---

## 5) Administración de no jugados

Cuando un partido no se ha jugado en plazo, administra el resultado manualmente.

### Comando `!` (forfait / empate admin / doble forfait)
```txt
!suizo_admin_resultado 1 2 4 forfeit_local
!suizo_admin_resultado 1 2 5 forfeit_visitante
!suizo_admin_resultado 1 2 6 empate_admin
!suizo_admin_resultado 1 2 7 doble_forfeit

TODO debe informar en el canal
```

Regla de puntuación administrativa (consistente en todo el sistema):
- `forfeit_local` asigna `puntos_win / puntos_loss` según configuración del torneo.
- `forfeit_visitante` asigna `puntos_loss / puntos_win` según configuración del torneo.
- `empate_admin` asigna `puntos_draw / puntos_draw` según configuración del torneo.
- `doble_forfeit` mantiene `0 / 0` como regla fija.

### Comando `!` (marcador manual)
```txt
!suizo_admin_resultado 1 2 8 manual 2 1
```

---

## 6) Drops y altas tardías

### Drop (retirada)
```txt
!suizo_drop 1 @CoachTres abandono por inactividad
```

### Alta tardía
```txt
!suizo_add_tardio 1 @CoachNuevo
!suizo_add_tardio 1 @CoachNuevo "Skaven"
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
!actualiza_suizo 1
```

### Comandos `/` para seguimiento final
```txt
/suizo_consulta_clasificacion torneo_id:1
/suizo_consulta_desempates torneo_id:1
/suizo_consulta_jugador torneo_id:1 usuario:@CoachUno

En phpadmin Procedimientos-> GeneralTorneoSuizo Para panorámica general
```

---


