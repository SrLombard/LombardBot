CREATE TABLE IF NOT EXISTS suizo_torneo (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(120) NOT NULL,
  idCompBbowl VARCHAR(45) NULL,
  activo TINYINT(1) NOT NULL DEFAULT 1,
  estado ENUM('CREADO','EN_CURSO','FINALIZADO') NOT NULL DEFAULT 'CREADO',
  rondas_totales INT NOT NULL,
  ida_vuelta TINYINT(1) NOT NULL DEFAULT 0,
  formato_serie ENUM('BO1','BO3','BO5') NOT NULL DEFAULT 'BO1',
  puntos_win DECIMAL(4,2) NOT NULL DEFAULT 3.00,
  puntos_draw DECIMAL(4,2) NOT NULL DEFAULT 1.00,
  puntos_loss DECIMAL(4,2) NOT NULL DEFAULT 0.00,
  puntos_bye DECIMAL(4,2) NOT NULL DEFAULT 1.50,
  fecha_fin_ronda1 DATETIME NOT NULL,
  dias_por_ronda INT NOT NULL DEFAULT 7,
  canal_hub_id BIGINT NULL,
  creado_por_discord_id BIGINT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS suizo_participante (
  id INT AUTO_INCREMENT PRIMARY KEY,
  torneo_id INT NOT NULL,
  usuario_id INT NOT NULL,
  estado ENUM('ACTIVO','RETIRADO') NOT NULL DEFAULT 'ACTIVO',
  tiene_bye TINYINT(1) NOT NULL DEFAULT 0,
  cantidad_byes INT NOT NULL DEFAULT 0,
  late_join_ronda INT NULL,
  puntos_ajuste_inicial DECIMAL(6,2) NOT NULL DEFAULT 0.00,
  raza_competicion VARCHAR(80) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_suizo_participante_torneo_usuario (torneo_id, usuario_id),
  KEY idx_suizo_participante_torneo_estado (torneo_id, estado),
  CONSTRAINT fk_suizo_participante_torneo
    FOREIGN KEY (torneo_id) REFERENCES suizo_torneo(id)
    ON DELETE CASCADE,
  CONSTRAINT fk_suizo_participante_usuario
    FOREIGN KEY (usuario_id) REFERENCES usuarios(idUsuarios)
    ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS suizo_ronda (
  id INT AUTO_INCREMENT PRIMARY KEY,
  torneo_id INT NOT NULL,
  numero INT NOT NULL,
  estado ENUM('ABIERTA','BLOQUEADA','CERRADA') NOT NULL DEFAULT 'ABIERTA',
  fecha_inicio DATETIME NOT NULL,
  fecha_fin DATETIME NOT NULL,
  generada_por_discord_id BIGINT NULL,
  cerrada_en DATETIME NULL,
  UNIQUE KEY uk_suizo_ronda_torneo_numero (torneo_id, numero),
  CONSTRAINT fk_suizo_ronda_torneo
    FOREIGN KEY (torneo_id) REFERENCES suizo_torneo(id)
    ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS suizo_emparejamiento (
  id INT AUTO_INCREMENT PRIMARY KEY,
  torneo_id INT NOT NULL,
  ronda_id INT NOT NULL,
  mesa_numero INT NOT NULL,
  coach1_usuario_id INT NOT NULL,
  coach2_usuario_id INT NULL,
  canal_id BIGINT NULL,
  estado ENUM('PENDIENTE','REPORTADO','ADMINISTRADO','CERRADO') NOT NULL DEFAULT 'PENDIENTE',
  es_bye TINYINT(1) NOT NULL DEFAULT 0,
  forfeit_tipo ENUM('NONE','LOCAL','VISITANTE','DOBLE') NOT NULL DEFAULT 'NONE',
  partidos_requeridos INT NOT NULL DEFAULT 1,
  partidos_reportados INT NOT NULL DEFAULT 0,
  score_final_c1 INT NOT NULL DEFAULT 0,
  score_final_c2 INT NOT NULL DEFAULT 0,
  puntos_c1 DECIMAL(6,2) NOT NULL DEFAULT 0.00,
  puntos_c2 DECIMAL(6,2) NOT NULL DEFAULT 0.00,
  ganador_usuario_id INT NULL,
  resultado_origen ENUM('API','ADMIN','BYE') NULL,
  UNIQUE KEY uk_suizo_emparejamiento_ronda_mesa (ronda_id, mesa_numero),
  KEY idx_suizo_emparejamiento_torneo_ronda_estado (torneo_id, ronda_id, estado),
  CONSTRAINT fk_suizo_emparejamiento_torneo
    FOREIGN KEY (torneo_id) REFERENCES suizo_torneo(id)
    ON DELETE CASCADE,
  CONSTRAINT fk_suizo_emparejamiento_ronda
    FOREIGN KEY (ronda_id) REFERENCES suizo_ronda(id)
    ON DELETE CASCADE,
  CONSTRAINT fk_suizo_emparejamiento_coach1
    FOREIGN KEY (coach1_usuario_id) REFERENCES usuarios(idUsuarios),
  CONSTRAINT fk_suizo_emparejamiento_coach2
    FOREIGN KEY (coach2_usuario_id) REFERENCES usuarios(idUsuarios),
  CONSTRAINT fk_suizo_emparejamiento_ganador
    FOREIGN KEY (ganador_usuario_id) REFERENCES usuarios(idUsuarios)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS suizo_game (
  id INT AUTO_INCREMENT PRIMARY KEY,
  emparejamiento_id INT NOT NULL,
  game_index INT NOT NULL,
  id_partido_bbowl VARCHAR(64) NULL,
  score_c1 INT NOT NULL DEFAULT 0,
  score_c2 INT NOT NULL DEFAULT 0,
  origen ENUM('API','ADMIN') NOT NULL,
  confirmado TINYINT(1) NOT NULL DEFAULT 1,
  fecha_registro DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_suizo_game_emparejamiento_index (emparejamiento_id, game_index),
  UNIQUE KEY uk_suizo_game_id_partido_bbowl (id_partido_bbowl),
  KEY idx_suizo_game_emparejamiento_id_partido (emparejamiento_id, id_partido_bbowl),
  CONSTRAINT fk_suizo_game_emparejamiento
    FOREIGN KEY (emparejamiento_id) REFERENCES suizo_emparejamiento(id)
    ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS suizo_standing_snapshot (
  id INT AUTO_INCREMENT PRIMARY KEY,
  torneo_id INT NOT NULL,
  ronda_numero INT NOT NULL,
  usuario_id INT NOT NULL,
  estado_participante ENUM('ACTIVO','RETIRADO') NOT NULL,
  pj INT NOT NULL DEFAULT 0,
  pg INT NOT NULL DEFAULT 0,
  pe INT NOT NULL DEFAULT 0,
  pp INT NOT NULL DEFAULT 0,
  puntos DECIMAL(6,2) NOT NULL DEFAULT 0.00,
  score_favor INT NOT NULL DEFAULT 0,
  score_contra INT NOT NULL DEFAULT 0,
  diff_score INT NOT NULL DEFAULT 0,
  buchholz_cut DECIMAL(8,2) NOT NULL DEFAULT 0.00,
  h2h_valor DECIMAL(8,2) NULL,
  rank_ronda INT NOT NULL,
  json_detalle_tiebreak JSON NULL,
  KEY idx_suizo_standing_torneo_ronda_rank (torneo_id, ronda_numero, rank_ronda),
  KEY idx_suizo_standing_torneo_ronda_usuario (torneo_id, ronda_numero, usuario_id),
  CONSTRAINT fk_suizo_standing_torneo
    FOREIGN KEY (torneo_id) REFERENCES suizo_torneo(id)
    ON DELETE CASCADE,
  CONSTRAINT fk_suizo_standing_usuario
    FOREIGN KEY (usuario_id) REFERENCES usuarios(idUsuarios)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS suizo_pairing_trace (
  id INT AUTO_INCREMENT PRIMARY KEY,
  torneo_id INT NOT NULL,
  ronda_id INT NOT NULL,
  seed_snapshot_id INT NULL,
  intento INT NOT NULL,
  resultado ENUM('OK','FALLBACK_REPETIDO','FALLBACK_MIRROR','SIN_SOLUCION') NOT NULL,
  reglas_aplicadas JSON NULL,
  conflictos JSON NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_suizo_pairing_trace_torneo
    FOREIGN KEY (torneo_id) REFERENCES suizo_torneo(id)
    ON DELETE CASCADE,
  CONSTRAINT fk_suizo_pairing_trace_ronda
    FOREIGN KEY (ronda_id) REFERENCES suizo_ronda(id)
    ON DELETE CASCADE,
  CONSTRAINT fk_suizo_pairing_trace_seed_snapshot
    FOREIGN KEY (seed_snapshot_id) REFERENCES suizo_standing_snapshot(id)
) ENGINE=InnoDB;
