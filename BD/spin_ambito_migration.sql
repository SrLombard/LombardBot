-- Migración idempotente para distinguir el historial de Spin por ámbito.
-- logicaSpin.md define los valores internos soportados: GENERAL y COMUNIDADES.
-- Los registros anteriores a esta columna pertenecen al Spin General.

SET @spin_ambito_columna := (
  SELECT COUNT(*)
  FROM INFORMATION_SCHEMA.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'Spin'
    AND COLUMN_NAME = 'ambito'
);

SET @spin_ambito_sql := IF(
  @spin_ambito_columna = 0,
  'ALTER TABLE Spin ADD COLUMN ambito VARCHAR(32) NOT NULL DEFAULT ''GENERAL''',
  'SELECT 1'
);

PREPARE spin_ambito_stmt FROM @spin_ambito_sql;
EXECUTE spin_ambito_stmt;
DEALLOCATE PREPARE spin_ambito_stmt;

UPDATE Spin
SET ambito = 'GENERAL'
WHERE ambito IS NULL OR ambito = '';

SET @spin_usuario_discord_columna := (
  SELECT COUNT(*)
  FROM INFORMATION_SCHEMA.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'Spin'
    AND COLUMN_NAME = 'usuario_discord_id'
);

SET @spin_usuario_discord_sql := IF(
  @spin_usuario_discord_columna = 0,
  'ALTER TABLE Spin ADD COLUMN usuario_discord_id BIGINT NULL',
  'SELECT 1'
);

PREPARE spin_usuario_discord_stmt FROM @spin_usuario_discord_sql;
EXECUTE spin_usuario_discord_stmt;
DEALLOCATE PREPARE spin_usuario_discord_stmt;
