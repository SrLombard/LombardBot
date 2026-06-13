-- Esquema compatible con MySQL 8.0.16+ y MariaDB 10.11+ para el torneo suizo por parejas y comunidades.
-- No reutiliza ni referencia ninguna tabla suizo_*.
--
-- Invariantes que debe completar la capa de dominio, porque MySQL no puede
-- expresarlas de forma declarativa entre varias filas/tablas:
--   * cada equipo debe tener exactamente dos miembros;
--   * cada enfrentamiento debe producir exactamente dos partidos individuales;
--   * no se pueden enfrentar equipos de la misma comunidad;
--   * cada equipo solo puede aparecer una vez por ronda, sin importar su lado;
--   * las fechas y transiciones de estado deben respetar el ciclo del torneo.

-- Los snowflakes de Discord superan el rango de INT; la tabla compartida de
-- usuarios debe usar BIGINT antes de recibir altas automáticas de este formato.
ALTER TABLE usuarios MODIFY COLUMN id_discord BIGINT NULL;

CREATE TABLE IF NOT EXISTS comunidades_torneo (
  id INT AUTO_INCREMENT,
  nombre VARCHAR(120) NOT NULL,
  estado ENUM('CREADO','EN_CURSO','FINALIZADO') NOT NULL DEFAULT 'CREADO',
  rondas_totales INT NOT NULL,
  fecha_fin_ronda1 DATETIME NOT NULL,
  dias_por_ronda INT NOT NULL DEFAULT 7,
  id_competicion_bbowl VARCHAR(45) NULL,
  canal_hub_id BIGINT NULL,
  puntos_clasificacion_victoria DECIMAL(6,2) NOT NULL DEFAULT 3.00,
  puntos_clasificacion_empate DECIMAL(6,2) NOT NULL DEFAULT 1.00,
  puntos_clasificacion_derrota DECIMAL(6,2) NOT NULL DEFAULT 0.00,
  puntos_clasificacion_bye DECIMAL(6,2) NOT NULL DEFAULT 1.50,
  puntos_individuales_victoria DECIMAL(6,2) NOT NULL DEFAULT 3.00,
  puntos_individuales_empate DECIMAL(6,2) NOT NULL DEFAULT 1.00,
  puntos_individuales_derrota DECIMAL(6,2) NOT NULL DEFAULT 0.00,
  plantilla_mensaje_ronda1 TEXT NOT NULL,
  plantilla_mensaje_rondas_siguientes TEXT NOT NULL,
  creado_por_discord_id BIGINT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  CONSTRAINT ck_comunidades_torneo_rondas CHECK (rondas_totales > 0),
  CONSTRAINT ck_comunidades_torneo_dias CHECK (dias_por_ronda > 0)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS comunidades_comunidad (
  id INT AUTO_INCREMENT,
  torneo_id INT NOT NULL,
  nombre VARCHAR(120) NOT NULL,
  puntos_zombificaciones DECIMAL(8,2) NOT NULL DEFAULT 0.00,
  zombies_matados INT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  CONSTRAINT uk_comunidades_comunidad_id_torneo UNIQUE (id, torneo_id),
  CONSTRAINT uk_comunidades_comunidad_torneo_nombre UNIQUE (torneo_id, nombre),
  CONSTRAINT ck_comunidades_comunidad_zombies_matados CHECK (zombies_matados >= 0),
  CONSTRAINT fk_comunidades_comunidad_torneo
    FOREIGN KEY (torneo_id) REFERENCES comunidades_torneo(id)
    ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS comunidades_equipo (
  id INT AUTO_INCREMENT,
  torneo_id INT NOT NULL,
  comunidad_id INT NOT NULL,
  nombre VARCHAR(120) NOT NULL,
  es_zombie TINYINT(1) NOT NULL DEFAULT 0,
  estado_temporal ENUM('NEUTRO','CAZADOR','CAZADOR_Z','HERIDO') NOT NULL DEFAULT 'NEUTRO',
  cantidad_byes INT NOT NULL DEFAULT 0,
  partidos_jugados INT NOT NULL DEFAULT 0,
  victorias INT NOT NULL DEFAULT 0,
  empates INT NOT NULL DEFAULT 0,
  derrotas INT NOT NULL DEFAULT 0,
  puntos_clasificacion DECIMAL(8,2) NOT NULL DEFAULT 0.00,
  td_favor INT NOT NULL DEFAULT 0,
  td_contra INT NOT NULL DEFAULT 0,
  buchholz_cut DECIMAL(10,2) NOT NULL DEFAULT 0.00,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  CONSTRAINT uk_comunidades_equipo_id_torneo UNIQUE (id, torneo_id),
  CONSTRAINT uk_comunidades_equipo_torneo_nombre UNIQUE (torneo_id, nombre),
  CONSTRAINT ck_comunidades_equipo_es_zombie CHECK (es_zombie IN (0, 1)),
  CONSTRAINT ck_comunidades_equipo_contadores CHECK (
    cantidad_byes >= 0 AND partidos_jugados >= 0 AND victorias >= 0
    AND empates >= 0 AND derrotas >= 0
  ),
  KEY idx_comunidades_equipo_torneo_comunidad (torneo_id, comunidad_id),
  KEY idx_comunidades_equipo_comunidad_torneo (comunidad_id, torneo_id),
  KEY idx_comunidades_equipo_clasificacion (torneo_id, puntos_clasificacion, buchholz_cut),
  CONSTRAINT fk_comunidades_equipo_torneo
    FOREIGN KEY (torneo_id) REFERENCES comunidades_torneo(id)
    ON DELETE CASCADE,
  CONSTRAINT fk_comunidades_equipo_comunidad_torneo
    FOREIGN KEY (comunidad_id, torneo_id)
    REFERENCES comunidades_comunidad(id, torneo_id)
    ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS comunidades_miembro (
  id INT AUTO_INCREMENT,
  torneo_id INT NOT NULL,
  equipo_id INT NOT NULL,
  usuario_id INT NOT NULL,
  raza VARCHAR(80) NOT NULL,
  posicion TINYINT UNSIGNED NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  CONSTRAINT uk_comunidades_miembro_equipo_posicion UNIQUE (equipo_id, posicion),
  CONSTRAINT uk_comunidades_miembro_torneo_usuario UNIQUE (torneo_id, usuario_id),
  CONSTRAINT ck_comunidades_miembro_posicion CHECK (posicion IN (1, 2)),
  KEY idx_comunidades_miembro_equipo_torneo (equipo_id, torneo_id),
  KEY idx_comunidades_miembro_usuario (usuario_id),
  CONSTRAINT fk_comunidades_miembro_equipo_torneo
    FOREIGN KEY (equipo_id, torneo_id)
    REFERENCES comunidades_equipo(id, torneo_id)
    ON DELETE CASCADE,
  CONSTRAINT fk_comunidades_miembro_usuario
    FOREIGN KEY (usuario_id) REFERENCES usuarios(idUsuarios)
    ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS comunidades_ronda (
  id INT AUTO_INCREMENT,
  torneo_id INT NOT NULL,
  numero INT NOT NULL,
  estado ENUM('ABIERTA','BLOQUEADA','PENDIENTE_TRANSFERENCIAS','CERRADA') NOT NULL DEFAULT 'ABIERTA',
  fecha_inicio DATETIME NOT NULL,
  fecha_fin DATETIME NOT NULL,
  generada_por_discord_id BIGINT NOT NULL,
  cerrada_en DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  CONSTRAINT uk_comunidades_ronda_id_torneo UNIQUE (id, torneo_id),
  CONSTRAINT uk_comunidades_ronda_torneo_numero UNIQUE (torneo_id, numero),
  CONSTRAINT ck_comunidades_ronda_numero CHECK (numero > 0),
  CONSTRAINT ck_comunidades_ronda_fechas CHECK (fecha_fin >= fecha_inicio),
  KEY idx_comunidades_ronda_torneo_estado (torneo_id, estado),
  CONSTRAINT fk_comunidades_ronda_torneo
    FOREIGN KEY (torneo_id) REFERENCES comunidades_torneo(id)
    ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS comunidades_enfrentamiento (
  id INT AUTO_INCREMENT,
  torneo_id INT NOT NULL,
  ronda_id INT NOT NULL,
  mesa_numero INT NOT NULL,
  equipo_a_id INT NOT NULL,
  equipo_b_id INT NOT NULL,
  canal_general_discord_id BIGINT NULL,
  estado ENUM(
    'PENDIENTE_ELECCIONES',
    'ELECCIONES_COMPLETAS',
    'PARTIDOS_CREADOS',
    'EN_CURSO',
    'CERRADO',
    'ADMINISTRADO'
  ) NOT NULL DEFAULT 'PENDIENTE_ELECCIONES',
  puntos_internos_a DECIMAL(8,2) NOT NULL DEFAULT 0.00,
  puntos_internos_b DECIMAL(8,2) NOT NULL DEFAULT 0.00,
  td_favor_a INT NOT NULL DEFAULT 0,
  td_contra_a INT NOT NULL DEFAULT 0,
  td_favor_b INT NOT NULL DEFAULT 0,
  td_contra_b INT NOT NULL DEFAULT 0,
  td_atacante_a INT NOT NULL DEFAULT 0,
  td_atacante_b INT NOT NULL DEFAULT 0,
  ganador_equipo_id INT NULL,
  puntos_clasificacion_a DECIMAL(8,2) NOT NULL DEFAULT 0.00,
  puntos_clasificacion_b DECIMAL(8,2) NOT NULL DEFAULT 0.00,
  resultado_origen ENUM('API','ADMIN') NULL,
  es_doble_forfait TINYINT(1) NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  CONSTRAINT uk_comunidades_enfrentamiento_id_torneo UNIQUE (id, torneo_id),
  CONSTRAINT uk_comunidades_enfrentamiento_ronda_mesa UNIQUE (ronda_id, mesa_numero),
  CONSTRAINT uk_comunidades_enfrentamiento_ronda_equipo_a UNIQUE (ronda_id, equipo_a_id),
  CONSTRAINT uk_comunidades_enfrentamiento_ronda_equipo_b UNIQUE (ronda_id, equipo_b_id),
  CONSTRAINT uk_com_enfrentamiento_canal UNIQUE (canal_general_discord_id),
  CONSTRAINT ck_comunidades_enfrentamiento_mesa CHECK (mesa_numero > 0),
  CONSTRAINT ck_comunidades_enfrentamiento_equipos CHECK (equipo_a_id <> equipo_b_id),
  CONSTRAINT ck_comunidades_enfrentamiento_ganador CHECK (
    ganador_equipo_id IS NULL OR ganador_equipo_id IN (equipo_a_id, equipo_b_id)
  ),
  CONSTRAINT ck_comunidades_enfrentamiento_doble_forfait CHECK (es_doble_forfait IN (0, 1)),
  KEY idx_comunidades_enfrentamiento_torneo_ronda_estado (torneo_id, ronda_id, estado),
  KEY idx_comunidades_enfrentamiento_ronda_torneo (ronda_id, torneo_id),
  KEY idx_comunidades_enfrentamiento_equipo_a (equipo_a_id, torneo_id),
  KEY idx_comunidades_enfrentamiento_equipo_b (equipo_b_id, torneo_id),
  KEY idx_comunidades_enfrentamiento_ganador (ganador_equipo_id, torneo_id),
  CONSTRAINT fk_comunidades_enfrentamiento_ronda_torneo
    FOREIGN KEY (ronda_id, torneo_id)
    REFERENCES comunidades_ronda(id, torneo_id)
    ON DELETE CASCADE,
  CONSTRAINT fk_comunidades_enfrentamiento_equipo_a_torneo
    FOREIGN KEY (equipo_a_id, torneo_id)
    REFERENCES comunidades_equipo(id, torneo_id)
    ON DELETE CASCADE,
  CONSTRAINT fk_comunidades_enfrentamiento_equipo_b_torneo
    FOREIGN KEY (equipo_b_id, torneo_id)
    REFERENCES comunidades_equipo(id, torneo_id)
    ON DELETE CASCADE,
  CONSTRAINT fk_comunidades_enfrentamiento_ganador_torneo
    FOREIGN KEY (ganador_equipo_id, torneo_id)
    REFERENCES comunidades_equipo(id, torneo_id)
    ON DELETE CASCADE
) ENGINE=InnoDB;

-- Mantiene instalaciones existentes alineadas con el estado intermedio que
-- separa el bloqueo atómico de elecciones de la materialización de partidos.
ALTER TABLE comunidades_enfrentamiento MODIFY COLUMN estado ENUM(
  'PENDIENTE_ELECCIONES',
  'ELECCIONES_COMPLETAS',
  'PARTIDOS_CREADOS',
  'EN_CURSO',
  'CERRADO',
  'ADMINISTRADO'
) NOT NULL DEFAULT 'PENDIENTE_ELECCIONES';

-- Configuración ordenada de categorías. El orden_alta se asigna al insertar y
-- permite recorrer las categorías en el mismo orden en que se configuraron.
CREATE TABLE IF NOT EXISTS comunidades_categoria_enfrentamiento (
  id INT AUTO_INCREMENT,
  torneo_id INT NOT NULL,
  categoria_discord_id BIGINT NOT NULL,
  orden_alta INT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  CONSTRAINT uk_com_cat_enf_torneo_categoria UNIQUE (torneo_id, categoria_discord_id),
  CONSTRAINT uk_com_cat_enf_torneo_orden UNIQUE (torneo_id, orden_alta),
  CONSTRAINT ck_com_cat_enf_orden CHECK (orden_alta > 0),
  CONSTRAINT fk_com_cat_enf_torneo
    FOREIGN KEY (torneo_id) REFERENCES comunidades_torneo(id)
    ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS comunidades_categoria_partido (
  id INT AUTO_INCREMENT,
  torneo_id INT NOT NULL,
  categoria_discord_id BIGINT NOT NULL,
  orden_alta INT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  CONSTRAINT uk_com_cat_par_torneo_categoria UNIQUE (torneo_id, categoria_discord_id),
  CONSTRAINT uk_com_cat_par_torneo_orden UNIQUE (torneo_id, orden_alta),
  CONSTRAINT ck_com_cat_par_orden CHECK (orden_alta > 0),
  CONSTRAINT fk_com_cat_par_torneo
    FOREIGN KEY (torneo_id) REFERENCES comunidades_torneo(id)
    ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS comunidades_eleccion_atacante (
  id INT AUTO_INCREMENT,
  torneo_id INT NOT NULL,
  enfrentamiento_id INT NOT NULL,
  equipo_id INT NOT NULL,
  atacante_usuario_id INT NOT NULL,
  defensor_usuario_id INT NOT NULL,
  elegido_por_discord_id BIGINT NOT NULL,
  elegido_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  bloqueada TINYINT(1) NOT NULL DEFAULT 0,
  PRIMARY KEY (id),
  CONSTRAINT uk_com_eleccion_enfrentamiento_equipo
    UNIQUE (enfrentamiento_id, equipo_id),
  CONSTRAINT ck_com_eleccion_jugadores
    CHECK (atacante_usuario_id <> defensor_usuario_id),
  CONSTRAINT ck_com_eleccion_bloqueada CHECK (bloqueada IN (0, 1)),
  KEY idx_com_eleccion_enfrentamiento_torneo (enfrentamiento_id, torneo_id),
  KEY idx_com_eleccion_equipo_torneo (equipo_id, torneo_id),
  KEY idx_com_eleccion_atacante (atacante_usuario_id),
  KEY idx_com_eleccion_defensor (defensor_usuario_id),
  CONSTRAINT fk_com_eleccion_enfrentamiento
    FOREIGN KEY (enfrentamiento_id, torneo_id)
    REFERENCES comunidades_enfrentamiento(id, torneo_id)
    ON DELETE CASCADE,
  CONSTRAINT fk_com_eleccion_torneo
    FOREIGN KEY (torneo_id) REFERENCES comunidades_torneo(id)
    ON DELETE CASCADE,
  CONSTRAINT fk_com_eleccion_equipo_torneo
    FOREIGN KEY (equipo_id, torneo_id)
    REFERENCES comunidades_equipo(id, torneo_id)
    ON DELETE CASCADE,
  CONSTRAINT fk_com_eleccion_atacante
    FOREIGN KEY (atacante_usuario_id) REFERENCES usuarios(idUsuarios)
    ON DELETE RESTRICT,
  CONSTRAINT fk_com_eleccion_defensor
    FOREIGN KEY (defensor_usuario_id) REFERENCES usuarios(idUsuarios)
    ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS comunidades_partido (
  id INT AUTO_INCREMENT,
  torneo_id INT NOT NULL,
  enfrentamiento_id INT NOT NULL,
  indice TINYINT UNSIGNED NOT NULL,
  equipo_local_id INT NOT NULL,
  equipo_visitante_id INT NOT NULL,
  usuario_local_id INT NOT NULL,
  usuario_visitante_id INT NOT NULL,
  atacante_usuario_id INT NOT NULL,
  defensor_usuario_id INT NOT NULL,
  canal_discord_id BIGINT NULL,
  partido_bloodbowl_id VARCHAR(45) NULL,
  td_local INT NULL,
  td_visitante INT NULL,
  puntos_internos_local DECIMAL(8,2) NULL,
  puntos_internos_visitante DECIMAL(8,2) NULL,
  estado ENUM('PENDIENTE','EN_CURSO','FINALIZADO','ADMINISTRADO')
    NOT NULL DEFAULT 'PENDIENTE',
  resultado_origen ENUM('API','ADMIN') NULL,
  tipo_forfait ENUM('LOCAL','VISITANTE','DOBLE') NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  CONSTRAINT uk_com_partido_enfrentamiento_indice
    UNIQUE (enfrentamiento_id, indice),
  CONSTRAINT uk_com_partido_bloodbowl UNIQUE (partido_bloodbowl_id),
  CONSTRAINT uk_com_partido_canal UNIQUE (canal_discord_id),
  CONSTRAINT ck_com_partido_indice CHECK (indice IN (1, 2)),
  CONSTRAINT ck_com_partido_equipos CHECK (equipo_local_id <> equipo_visitante_id),
  CONSTRAINT ck_com_partido_usuarios CHECK (usuario_local_id <> usuario_visitante_id),
  CONSTRAINT ck_com_partido_roles CHECK (atacante_usuario_id <> defensor_usuario_id),
  CONSTRAINT ck_com_partido_td CHECK (
    (td_local IS NULL AND td_visitante IS NULL)
    OR (td_local >= 0 AND td_visitante >= 0)
  ),
  KEY idx_com_partido_enfrentamiento_torneo (enfrentamiento_id, torneo_id),
  KEY idx_com_partido_equipo_local (equipo_local_id, torneo_id),
  KEY idx_com_partido_equipo_visitante (equipo_visitante_id, torneo_id),
  KEY idx_com_partido_usuario_local (usuario_local_id),
  KEY idx_com_partido_usuario_visitante (usuario_visitante_id),
  KEY idx_com_partido_atacante (atacante_usuario_id),
  KEY idx_com_partido_defensor (defensor_usuario_id),
  CONSTRAINT fk_com_partido_enfrentamiento
    FOREIGN KEY (enfrentamiento_id, torneo_id)
    REFERENCES comunidades_enfrentamiento(id, torneo_id)
    ON DELETE CASCADE,
  CONSTRAINT fk_com_partido_torneo
    FOREIGN KEY (torneo_id) REFERENCES comunidades_torneo(id)
    ON DELETE CASCADE,
  CONSTRAINT fk_com_partido_equipo_local
    FOREIGN KEY (equipo_local_id, torneo_id)
    REFERENCES comunidades_equipo(id, torneo_id)
    ON DELETE CASCADE,
  CONSTRAINT fk_com_partido_equipo_visitante
    FOREIGN KEY (equipo_visitante_id, torneo_id)
    REFERENCES comunidades_equipo(id, torneo_id)
    ON DELETE CASCADE,
  CONSTRAINT fk_com_partido_usuario_local
    FOREIGN KEY (usuario_local_id) REFERENCES usuarios(idUsuarios)
    ON DELETE RESTRICT,
  CONSTRAINT fk_com_partido_usuario_visitante
    FOREIGN KEY (usuario_visitante_id) REFERENCES usuarios(idUsuarios)
    ON DELETE RESTRICT,
  CONSTRAINT fk_com_partido_atacante
    FOREIGN KEY (atacante_usuario_id) REFERENCES usuarios(idUsuarios)
    ON DELETE RESTRICT,
  CONSTRAINT fk_com_partido_defensor
    FOREIGN KEY (defensor_usuario_id) REFERENCES usuarios(idUsuarios)
    ON DELETE RESTRICT
) ENGINE=InnoDB;

-- Copia inmutable desde la perspectiva del dominio: no contiene columnas que
-- dependan de consultar el estado vivo del equipo al resolver el resultado.
CREATE TABLE IF NOT EXISTS comunidades_fotografia_estado (
  id INT AUTO_INCREMENT,
  torneo_id INT NOT NULL,
  ronda_id INT NOT NULL,
  enfrentamiento_id INT NOT NULL,
  equipo_id INT NOT NULL,
  comunidad_id INT NOT NULL,
  es_zombie TINYINT(1) NOT NULL,
  estado_temporal ENUM('NEUTRO','CAZADOR','CAZADOR_Z','HERIDO') NOT NULL,
  fotografiado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  CONSTRAINT uk_com_foto_enfrentamiento_equipo
    UNIQUE (enfrentamiento_id, equipo_id),
  CONSTRAINT ck_com_foto_zombie CHECK (es_zombie IN (0, 1)),
  KEY idx_com_foto_ronda_torneo (ronda_id, torneo_id),
  KEY idx_com_foto_enfrentamiento (enfrentamiento_id),
  KEY idx_com_foto_equipo_torneo (equipo_id, torneo_id),
  KEY idx_com_foto_comunidad_torneo (comunidad_id, torneo_id),
  CONSTRAINT fk_com_foto_ronda
    FOREIGN KEY (ronda_id, torneo_id)
    REFERENCES comunidades_ronda(id, torneo_id)
    ON DELETE CASCADE,
  CONSTRAINT fk_com_foto_enfrentamiento
    FOREIGN KEY (enfrentamiento_id, torneo_id)
    REFERENCES comunidades_enfrentamiento(id, torneo_id)
    ON DELETE CASCADE,
  CONSTRAINT fk_com_foto_torneo
    FOREIGN KEY (torneo_id) REFERENCES comunidades_torneo(id)
    ON DELETE CASCADE,
  CONSTRAINT fk_com_foto_equipo
    FOREIGN KEY (equipo_id, torneo_id)
    REFERENCES comunidades_equipo(id, torneo_id)
    ON DELETE CASCADE,
  CONSTRAINT fk_com_foto_comunidad
    FOREIGN KEY (comunidad_id, torneo_id)
    REFERENCES comunidades_comunidad(id, torneo_id)
    ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS comunidades_historial_transicion (
  id INT AUTO_INCREMENT,
  torneo_id INT NOT NULL,
  ronda_id INT NOT NULL,
  enfrentamiento_id INT NULL,
  equipo_id INT NOT NULL,
  estado_temporal_anterior ENUM('NEUTRO','CAZADOR','CAZADOR_Z','HERIDO') NOT NULL,
  es_zombie_anterior TINYINT(1) NOT NULL,
  estado_temporal_posterior ENUM('NEUTRO','CAZADOR','CAZADOR_Z','HERIDO') NOT NULL,
  es_zombie_posterior TINYINT(1) NOT NULL,
  motivo ENUM(
    'VICTORIA','DERROTA','EMPATE','BYE','ZOMBIFICACION','KILL',
    'DOBLE_FORFAIT','TRANSFERENCIA'
  ) NOT NULL,
  puntos_comunitarios_generados DECIMAL(10,2) NOT NULL DEFAULT 0.00,
  kills_generadas INT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  CONSTRAINT uk_com_transicion_enfrentamiento_equipo
    UNIQUE (enfrentamiento_id, equipo_id),
  CONSTRAINT ck_com_transicion_zombie_anterior CHECK (es_zombie_anterior IN (0, 1)),
  CONSTRAINT ck_com_transicion_zombie_posterior CHECK (es_zombie_posterior IN (0, 1)),
  CONSTRAINT ck_com_transicion_contadores CHECK (
    puntos_comunitarios_generados >= 0 AND kills_generadas >= 0
  ),
  KEY idx_com_transicion_ronda_torneo (ronda_id, torneo_id),
  KEY idx_com_transicion_enfrentamiento (enfrentamiento_id),
  KEY idx_com_transicion_equipo_torneo (equipo_id, torneo_id),
  CONSTRAINT fk_com_transicion_ronda
    FOREIGN KEY (ronda_id, torneo_id)
    REFERENCES comunidades_ronda(id, torneo_id)
    ON DELETE CASCADE,
  CONSTRAINT fk_com_transicion_enfrentamiento
    FOREIGN KEY (enfrentamiento_id, torneo_id)
    REFERENCES comunidades_enfrentamiento(id, torneo_id)
    ON DELETE CASCADE,
  CONSTRAINT fk_com_transicion_torneo
    FOREIGN KEY (torneo_id) REFERENCES comunidades_torneo(id)
    ON DELETE CASCADE,
  CONSTRAINT fk_com_transicion_equipo
    FOREIGN KEY (equipo_id, torneo_id)
    REFERENCES comunidades_equipo(id, torneo_id)
    ON DELETE CASCADE
) ENGINE=InnoDB;

-- Auditoría consolidada: ronda_id se conserva como dato histórico y no se
-- enlaza con borrado en cascada a la fila regenerable de la ronda. La FK del
-- torneo elimina el historial únicamente al borrar el torneo completo.
CREATE TABLE IF NOT EXISTS comunidades_historial_transferencia (
  id INT AUTO_INCREMENT,
  torneo_id INT NOT NULL,
  ronda_id INT NOT NULL,
  comunidad_id INT NOT NULL,
  equipo_origen_id INT NOT NULL,
  equipo_destino_id INT NOT NULL,
  tipo ENUM('CAZADOR','CAZADOR_Z') NOT NULL,
  ejecutada_por_discord_id BIGINT NOT NULL,
  clave_idempotencia VARCHAR(190) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  CONSTRAINT uk_com_transferencia_idempotencia UNIQUE (clave_idempotencia),
  CONSTRAINT ck_com_transferencia_equipos
    CHECK (equipo_origen_id <> equipo_destino_id),
  KEY idx_com_transferencia_ronda_torneo (ronda_id, torneo_id),
  KEY idx_com_transferencia_comunidad_torneo (comunidad_id, torneo_id),
  KEY idx_com_transferencia_origen (equipo_origen_id, torneo_id),
  KEY idx_com_transferencia_destino (equipo_destino_id, torneo_id),
  CONSTRAINT fk_com_transferencia_torneo
    FOREIGN KEY (torneo_id) REFERENCES comunidades_torneo(id)
    ON DELETE CASCADE,
  CONSTRAINT fk_com_transferencia_comunidad
    FOREIGN KEY (comunidad_id, torneo_id)
    REFERENCES comunidades_comunidad(id, torneo_id)
    ON DELETE CASCADE,
  CONSTRAINT fk_com_transferencia_origen
    FOREIGN KEY (equipo_origen_id, torneo_id)
    REFERENCES comunidades_equipo(id, torneo_id)
    ON DELETE CASCADE,
  CONSTRAINT fk_com_transferencia_destino
    FOREIGN KEY (equipo_destino_id, torneo_id)
    REFERENCES comunidades_equipo(id, torneo_id)
    ON DELETE CASCADE
) ENGINE=InnoDB;

-- Los snapshots contienen todos los valores necesarios para reproducir el
-- orden publicado sin consultar estadísticas acumuladas actuales. ronda_id se
-- conserva como dato histórico independiente de la fila regenerable.
CREATE TABLE IF NOT EXISTS comunidades_snapshot_clasificacion_equipo (
  id INT AUTO_INCREMENT,
  torneo_id INT NOT NULL,
  ronda_id INT NOT NULL,
  equipo_id INT NOT NULL,
  posicion INT NOT NULL,
  puntos_clasificacion DECIMAL(10,2) NOT NULL,
  buchholz_cut DECIMAL(10,2) NOT NULL,
  puntos_enfrentamiento_directo DECIMAL(10,2) NULL,
  td_favor INT NOT NULL,
  td_contra INT NOT NULL,
  partidos_jugados INT NOT NULL,
  victorias INT NOT NULL,
  empates INT NOT NULL,
  derrotas INT NOT NULL,
  cantidad_byes INT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  CONSTRAINT uk_com_snap_equipo_ronda_equipo UNIQUE (ronda_id, equipo_id),
  CONSTRAINT ck_com_snap_equipo_posicion CHECK (posicion > 0),
  CONSTRAINT ck_com_snap_equipo_contadores CHECK (
    td_favor >= 0 AND td_contra >= 0 AND partidos_jugados >= 0
    AND victorias >= 0 AND empates >= 0 AND derrotas >= 0
    AND cantidad_byes >= 0
  ),
  KEY idx_com_snap_equipo_torneo_ronda_posicion (torneo_id, ronda_id, posicion),
  KEY idx_com_snap_equipo_equipo_torneo (equipo_id, torneo_id),
  CONSTRAINT fk_com_snap_equipo_torneo
    FOREIGN KEY (torneo_id) REFERENCES comunidades_torneo(id)
    ON DELETE CASCADE,
  CONSTRAINT fk_com_snap_equipo_equipo
    FOREIGN KEY (equipo_id, torneo_id)
    REFERENCES comunidades_equipo(id, torneo_id)
    ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS comunidades_snapshot_clasificacion_comunidad (
  id INT AUTO_INCREMENT,
  torneo_id INT NOT NULL,
  ronda_id INT NOT NULL,
  comunidad_id INT NOT NULL,
  posicion INT NOT NULL,
  puntos_zombificaciones DECIMAL(10,2) NOT NULL,
  zombies_matados INT NOT NULL,
  suma_puntos_equipos DECIMAL(10,2) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  CONSTRAINT uk_com_snap_comunidad_ronda_comunidad
    UNIQUE (ronda_id, comunidad_id),
  CONSTRAINT ck_com_snap_comunidad_posicion CHECK (posicion > 0),
  CONSTRAINT ck_com_snap_comunidad_contadores CHECK (
    puntos_zombificaciones >= 0 AND zombies_matados >= 0
  ),
  KEY idx_com_snap_com_torneo_ronda_posicion (torneo_id, ronda_id, posicion),
  KEY idx_com_snap_com_comunidad_torneo (comunidad_id, torneo_id),
  CONSTRAINT fk_com_snap_com_torneo
    FOREIGN KEY (torneo_id) REFERENCES comunidades_torneo(id)
    ON DELETE CASCADE,
  CONSTRAINT fk_com_snap_com_comunidad
    FOREIGN KEY (comunidad_id, torneo_id)
    REFERENCES comunidades_comunidad(id, torneo_id)
    ON DELETE CASCADE
) ENGINE=InnoDB;

-- Claves idempotentes persistidas para efectos que no comparten transacción
-- con MySQL (Discord/API). Una clave PENDIENTE funciona como lease recuperable;
-- COMPLETADA conserva el ID externo y evita repetir el efecto tras reinicios.
CREATE TABLE IF NOT EXISTS comunidades_operacion_idempotente (
  id INT AUTO_INCREMENT,
  clave VARCHAR(190) NOT NULL,
  tipo VARCHAR(45) NOT NULL,
  estado ENUM('PENDIENTE','COMPLETADA') NOT NULL DEFAULT 'PENDIENTE',
  torneo_id INT NOT NULL,
  ronda_id INT NULL,
  enfrentamiento_id INT NULL,
  partido_id INT NULL,
  recurso_externo_id VARCHAR(120) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  CONSTRAINT uk_com_operacion_clave UNIQUE (clave),
  KEY idx_com_operacion_contexto
    (torneo_id, ronda_id, enfrentamiento_id, partido_id),
  CONSTRAINT fk_com_operacion_torneo
    FOREIGN KEY (torneo_id) REFERENCES comunidades_torneo(id)
    ON DELETE CASCADE
) ENGINE=InnoDB;

-- Traza regenerable de las decisiones del algoritmo de emparejamiento. Puede
-- registrar candidatos descartados, relajaciones y la selección final.
CREATE TABLE IF NOT EXISTS comunidades_traza_emparejamiento (
  id INT AUTO_INCREMENT,
  torneo_id INT NOT NULL,
  ronda_id INT NOT NULL,
  secuencia INT NOT NULL,
  etapa ENUM(
    'BASE','PERMITIR_MIRRORS','PERMITIR_ESTADOS_NO_DESEADOS',
    'PERMITIR_REPETIDOS','SELECCION_BYE','SELECCION_FINAL','CANCELACION'
  ) NOT NULL,
  equipo_a_id INT NULL,
  equipo_b_id INT NULL,
  diferencia_puntos DECIMAL(10,2) NULL,
  es_mirror TINYINT(1) NULL,
  es_rival_repetido TINYINT(1) NULL,
  prioridad_estado INT NULL,
  desempate_aleatorio DECIMAL(18,17) NULL,
  detalle TEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  CONSTRAINT uk_com_traza_ronda_secuencia UNIQUE (ronda_id, secuencia),
  CONSTRAINT ck_com_traza_secuencia CHECK (secuencia > 0),
  CONSTRAINT ck_com_traza_equipos CHECK (
    equipo_a_id IS NULL OR equipo_b_id IS NULL OR equipo_a_id <> equipo_b_id
  ),
  CONSTRAINT ck_com_traza_mirror CHECK (es_mirror IS NULL OR es_mirror IN (0, 1)),
  CONSTRAINT ck_com_traza_repetido CHECK (
    es_rival_repetido IS NULL OR es_rival_repetido IN (0, 1)
  ),
  KEY idx_com_traza_torneo_ronda_etapa (torneo_id, ronda_id, etapa),
  KEY idx_com_traza_equipo_a (equipo_a_id, torneo_id),
  KEY idx_com_traza_equipo_b (equipo_b_id, torneo_id),
  CONSTRAINT fk_com_traza_ronda
    FOREIGN KEY (ronda_id, torneo_id)
    REFERENCES comunidades_ronda(id, torneo_id)
    ON DELETE CASCADE,
  CONSTRAINT fk_com_traza_torneo
    FOREIGN KEY (torneo_id) REFERENCES comunidades_torneo(id)
    ON DELETE CASCADE,
  CONSTRAINT fk_com_traza_equipo_a
    FOREIGN KEY (equipo_a_id, torneo_id)
    REFERENCES comunidades_equipo(id, torneo_id)
    ON DELETE CASCADE,
  CONSTRAINT fk_com_traza_equipo_b
    FOREIGN KEY (equipo_b_id, torneo_id)
    REFERENCES comunidades_equipo(id, torneo_id)
    ON DELETE CASCADE
) ENGINE=InnoDB;
