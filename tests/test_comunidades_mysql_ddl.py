from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, inspect


TABLAS_CRITICAS = {
    "comunidades_torneo",
    "comunidades_comunidad",
    "comunidades_equipo",
    "comunidades_ronda",
    "comunidades_enfrentamiento",
    "comunidades_partido",
    "comunidades_historial_transicion",
    "comunidades_snapshot_clasificacion_equipo",
    "comunidades_snapshot_clasificacion_comunidad",
}


def _sentencias_mysql(sql: str):
    acumulado = []
    for linea in sql.splitlines():
        limpia = linea.strip()
        if not limpia or limpia.startswith("--"):
            continue
        acumulado.append(linea)
        if limpia.endswith(";"):
            yield "\n".join(acumulado)
            acumulado = []
    if acumulado:
        yield "\n".join(acumulado)


@pytest.mark.mysql_ddl
def test_ddl_comunidades_se_aplica_en_mysql_compatible(ddl_mysql_path):
    dsn = os.getenv("LOMBARDBOT_TEST_MYSQL_DSN")
    if not dsn:
        pytest.skip(
            "Define LOMBARDBOT_TEST_MYSQL_DSN para validar el DDL en MySQL/MariaDB."
        )

    engine = create_engine(dsn)
    try:
        assert engine.dialect.name in {"mysql", "mariadb"}
        ddl = ddl_mysql_path.read_text(encoding="utf-8")
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "CREATE TABLE IF NOT EXISTS usuarios ("
                "idUsuarios INT NOT NULL AUTO_INCREMENT, PRIMARY KEY (idUsuarios)"
                ") ENGINE=InnoDB"
            )
            connection.exec_driver_sql("SET FOREIGN_KEY_CHECKS = 0")
            for tabla in reversed(inspect(connection).get_table_names()):
                if tabla.startswith("comunidades_"):
                    connection.exec_driver_sql(f"DROP TABLE IF EXISTS `{tabla}`")
            connection.exec_driver_sql("SET FOREIGN_KEY_CHECKS = 1")
            for sentencia in _sentencias_mysql(ddl):
                connection.exec_driver_sql(sentencia)

        tablas = set(inspect(engine).get_table_names())
        assert TABLAS_CRITICAS <= tablas
        columnas_equipo = {
            columna["name"]
            for columna in inspect(engine).get_columns("comunidades_equipo")
        }
        assert {"estado_temporal", "es_zombie", "cantidad_byes"} <= columnas_equipo
    finally:
        engine.dispose()
