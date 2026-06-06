-- Esquema independiente para el torneo suizo por parejas y comunidades.
-- No reutiliza ni referencia ninguna tabla suizo_*.
--
-- Invariantes que debe completar la capa de dominio, porque MySQL no puede
-- expresarlas de forma declarativa entre varias filas/tablas:
--   * cada equipo debe tener exactamente dos miembros;
--   * cada enfrentamiento debe producir exactamente dos partidos individuales;
--   * no se pueden enfrentar equipos de la misma comunidad;
--   * cada equipo solo puede aparecer una vez por ronda, sin importar su lado;
--   * las fechas y transiciones de estado deben respetar el ciclo del torneo.

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
  CONSTRAINT pk_comunidades_torneo PRIMARY KEY (id),
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
  CONSTRAINT pk_comunidades_comunidad PRIMARY KEY (id),
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
  CONSTRAINT pk_comunidades_equipo PRIMARY KEY (id),
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
    ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS comunidades_miembro (
  id INT AUTO_INCREMENT,
  torneo_id INT NOT NULL,
  equipo_id INT NOT NULL,
  usuario_id INT NOT NULL,
  raza VARCHAR(80) NOT NULL,
  posicion TINYINT UNSIGNED NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT pk_comunidades_miembro PRIMARY KEY (id),
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
  estado ENUM('ABIERTA','BLOQUEADA','CERRADA') NOT NULL DEFAULT 'ABIERTA',
  fecha_inicio DATETIME NOT NULL,
  fecha_fin DATETIME NOT NULL,
  generada_por_discord_id BIGINT NOT NULL,
  cerrada_en DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT pk_comunidades_ronda PRIMARY KEY (id),
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
  CONSTRAINT pk_comunidades_enfrentamiento PRIMARY KEY (id),
  CONSTRAINT uk_comunidades_enfrentamiento_ronda_mesa UNIQUE (ronda_id, mesa_numero),
  CONSTRAINT uk_comunidades_enfrentamiento_ronda_equipo_a UNIQUE (ronda_id, equipo_a_id),
  CONSTRAINT uk_comunidades_enfrentamiento_ronda_equipo_b UNIQUE (ronda_id, equipo_b_id),
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
    ON DELETE RESTRICT,
  CONSTRAINT fk_comunidades_enfrentamiento_equipo_b_torneo
    FOREIGN KEY (equipo_b_id, torneo_id)
    REFERENCES comunidades_equipo(id, torneo_id)
    ON DELETE RESTRICT,
  CONSTRAINT fk_comunidades_enfrentamiento_ganador_torneo
    FOREIGN KEY (ganador_equipo_id, torneo_id)
    REFERENCES comunidades_equipo(id, torneo_id)
    ON DELETE RESTRICT
) ENGINE=InnoDB;
