from datetime import datetime, timedelta
from pathlib import Path
import re
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

import pytest
from sqlalchemy import create_engine, event, inspect
from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy.orm import Session

from GestorSQL import (
    Base,
    Usuario,
    ComunidadesTorneo,
    ComunidadesComunidad,
    ComunidadesEquipo,
    ComunidadesMiembro,
    ComunidadesRonda,
    ComunidadesEnfrentamiento,
    ComunidadesCategoriaEnfrentamiento,
    ComunidadesCategoriaPartido,
    ComunidadesEleccionAtacante,
    ComunidadesPartido,
    ComunidadesFotografiaEstado,
    ComunidadesHistorialTransicion,
    ComunidadesHistorialTransferencia,
    ComunidadesSnapshotClasificacionEquipo,
    ComunidadesSnapshotClasificacionComunidad,
    ComunidadesTrazaEmparejamiento,
)


TABLAS_COMUNIDADES = {
    'comunidades_torneo',
    'comunidades_comunidad',
    'comunidades_equipo',
    'comunidades_miembro',
    'comunidades_ronda',
    'comunidades_enfrentamiento',
    'comunidades_categoria_enfrentamiento',
    'comunidades_categoria_partido',
    'comunidades_eleccion_atacante',
    'comunidades_partido',
    'comunidades_fotografia_estado',
    'comunidades_historial_transicion',
    'comunidades_historial_transferencia',
    'comunidades_snapshot_clasificacion_equipo',
    'comunidades_snapshot_clasificacion_comunidad',
    'comunidades_traza_emparejamiento',
}


def _engine():
    engine = create_engine('sqlite:///:memory:')

    @event.listens_for(engine, 'connect')
    def _activar_foreign_keys(dbapi_connection, _):
        dbapi_connection.execute('PRAGMA foreign_keys=ON')

    Base.metadata.create_all(engine)
    return engine


def _torneo(nombre='Copa de Comunidades'):
    ahora = datetime(2026, 7, 1, 20, 0)
    return ComunidadesTorneo(
        nombre=nombre,
        rondas_totales=3,
        fecha_fin_ronda1=ahora + timedelta(days=7),
        plantilla_mensaje_ronda1='Primera ronda',
        plantilla_mensaje_rondas_siguientes='Siguiente ronda',
        creado_por_discord_id=100,
    )


def test_create_all_crea_todas_las_tablas_del_esquema():
    tablas = set(inspect(_engine()).get_table_names())
    assert TABLAS_COMUNIDADES <= tablas


def test_columnas_orm_coinciden_con_el_ddl():
    ddl = (Path(__file__).resolve().parents[1] / 'BD' / 'comunidades_schema.sql').read_text()
    tablas_ddl = re.findall(
        r'CREATE TABLE IF NOT EXISTS (comunidades_\w+) \((.*?)\n\) ENGINE',
        ddl,
        re.DOTALL,
    )

    for nombre_tabla, cuerpo in tablas_ddl:
        columnas_ddl = [
            coincidencia.group(1)
            for linea in cuerpo.splitlines()
            if (coincidencia := re.match(
                r'\s{2}([a-z]\w*)\s+(?:BIGINT|DATETIME|DECIMAL|ENUM|INT|TEXT|TINYINT|VARCHAR)',
                linea,
            ))
        ]
        assert list(Base.metadata.tables[nombre_tabla].columns.keys()) == columnas_ddl


def test_modelos_de_comunidades_no_dependen_de_modelos_suizos():
    for tabla_nombre in TABLAS_COMUNIDADES:
        tabla = Base.metadata.tables[tabla_nombre]
        assert all(not fk.target_fullname.startswith('suizo_') for fk in tabla.foreign_keys)


def test_navegacion_torneo_comunidades_equipos_rondas_y_usuarios():
    engine = _engine()
    ahora = datetime(2026, 7, 1, 20, 0)

    with Session(engine) as session:
        usuarios = [
            Usuario(idUsuarios=1, nombre_discord='Uno'),
            Usuario(idUsuarios=2, nombre_discord='Dos'),
            Usuario(idUsuarios=3, nombre_discord='Tres'),
            Usuario(idUsuarios=4, nombre_discord='Cuatro'),
        ]
        torneo = _torneo()
        comunidad_a = ComunidadesComunidad(nombre='Butter')
        comunidad_b = ComunidadesComunidad(nombre='Hispana')
        equipo_a = ComunidadesEquipo(nombre='Equipo A')
        equipo_b = ComunidadesEquipo(nombre='Equipo B')
        equipo_a.miembros = [
            ComunidadesMiembro(usuario=usuarios[0], posicion=1, raza='Orcos'),
            ComunidadesMiembro(usuario=usuarios[1], posicion=2, raza='Skaven'),
        ]
        equipo_b.miembros = [
            ComunidadesMiembro(usuario=usuarios[2], posicion=1, raza='Humanos'),
            ComunidadesMiembro(usuario=usuarios[3], posicion=2, raza='Enanos'),
        ]
        comunidad_a.equipos.append(equipo_a)
        comunidad_b.equipos.append(equipo_b)
        torneo.comunidades.extend([comunidad_a, comunidad_b])
        ronda = ComunidadesRonda(
            numero=1,
            fecha_inicio=ahora,
            fecha_fin=ahora + timedelta(days=7),
            generada_por_discord_id=101,
        )
        torneo.rondas.append(ronda)
        session.add(torneo)
        session.flush()

        enfrentamiento = ComunidadesEnfrentamiento(
            torneo_id=torneo.id,
            ronda=ronda,
            mesa_numero=1,
            equipo_a=equipo_a,
            equipo_b=equipo_b,
        )
        eleccion = ComunidadesEleccionAtacante(
            torneo_id=torneo.id,
            equipo=equipo_a,
            atacante_usuario=usuarios[0],
            defensor_usuario=usuarios[1],
            elegido_por_discord_id=usuarios[0].id_discord or 1001,
        )
        partido = ComunidadesPartido(
            torneo_id=torneo.id,
            indice=1,
            equipo_local=equipo_a,
            equipo_visitante=equipo_b,
            usuario_local=usuarios[0],
            usuario_visitante=usuarios[3],
            atacante_usuario=usuarios[0],
            defensor_usuario=usuarios[3],
        )
        enfrentamiento.elecciones_atacante.append(eleccion)
        enfrentamiento.partidos.append(partido)
        session.add(enfrentamiento)
        session.commit()

        session.expire_all()
        cargado = session.get(ComunidadesTorneo, torneo.id)
        assert [c.nombre for c in cargado.comunidades] == ['Butter', 'Hispana']
        assert {e.nombre for e in cargado.equipos} == {'Equipo A', 'Equipo B'}
        assert cargado.rondas[0].enfrentamientos[0].equipo_a.nombre == 'Equipo A'
        assert [m.usuario.nombre_discord for m in equipo_a.miembros] == ['Uno', 'Dos']
        assert eleccion.atacante_usuario.nombre_discord == 'Uno'
        assert eleccion.defensor_usuario.nombre_discord == 'Dos'
        assert partido.usuario_local.nombre_discord == 'Uno'
        assert partido.usuario_visitante.nombre_discord == 'Cuatro'
        assert partido.atacante_usuario.nombre_discord == 'Uno'
        assert partido.defensor_usuario.nombre_discord == 'Cuatro'


def test_unicidad_de_nombre_de_equipo_dentro_del_torneo():
    engine = _engine()
    with Session(engine) as session:
        torneo = _torneo()
        comunidad = ComunidadesComunidad(nombre='Butter')
        torneo.comunidades.append(comunidad)
        session.add(torneo)
        session.flush()
        session.add_all([
            ComunidadesEquipo(torneo_id=torneo.id, comunidad=comunidad, nombre='Duplicado'),
            ComunidadesEquipo(torneo_id=torneo.id, comunidad=comunidad, nombre='Duplicado'),
        ])
        with pytest.raises(IntegrityError):
            session.commit()


def test_un_usuario_no_puede_pertenecer_a_dos_equipos_del_mismo_torneo():
    engine = _engine()
    with Session(engine) as session:
        usuario = Usuario(idUsuarios=1, nombre_discord='Uno')
        torneo = _torneo()
        comunidad = ComunidadesComunidad(nombre='Butter')
        torneo.comunidades.append(comunidad)
        session.add_all([usuario, torneo])
        session.flush()
        equipo_a = ComunidadesEquipo(torneo_id=torneo.id, comunidad=comunidad, nombre='A')
        equipo_b = ComunidadesEquipo(torneo_id=torneo.id, comunidad=comunidad, nombre='B')
        session.add_all([equipo_a, equipo_b])
        session.flush()
        session.add_all([
            ComunidadesMiembro(torneo_id=torneo.id, equipo=equipo_a, usuario=usuario, posicion=1, raza='Orcos'),
            ComunidadesMiembro(torneo_id=torneo.id, equipo=equipo_b, usuario=usuario, posicion=1, raza='Skaven'),
        ])
        with pytest.raises(IntegrityError):
            session.commit()


@pytest.mark.parametrize(
    ('modelo', 'columna', 'valores'),
    [
        (ComunidadesTorneo, 'estado', {'CREADO', 'EN_CURSO', 'FINALIZADO'}),
        (ComunidadesEquipo, 'estado_temporal', {'NEUTRO', 'CAZADOR', 'CAZADOR_Z', 'HERIDO'}),
        (ComunidadesRonda, 'estado', {'ABIERTA', 'BLOQUEADA', 'CERRADA'}),
        (ComunidadesEnfrentamiento, 'estado', {'PENDIENTE_ELECCIONES', 'ELECCIONES_COMPLETAS', 'PARTIDOS_CREADOS', 'EN_CURSO', 'CERRADO', 'ADMINISTRADO'}),
        (ComunidadesPartido, 'estado', {'PENDIENTE', 'EN_CURSO', 'FINALIZADO', 'ADMINISTRADO'}),
        (ComunidadesHistorialTransicion, 'motivo', {'VICTORIA', 'DERROTA', 'EMPATE', 'BYE', 'ZOMBIFICACION', 'KILL', 'DOBLE_FORFAIT', 'TRANSFERENCIA'}),
        (ComunidadesHistorialTransferencia, 'tipo', {'CAZADOR', 'CAZADOR_Z'}),
        (ComunidadesTrazaEmparejamiento, 'etapa', {'BASE', 'PERMITIR_MIRRORS', 'PERMITIR_ESTADOS_NO_DESEADOS', 'PERMITIR_REPETIDOS', 'SELECCION_BYE', 'SELECCION_FINAL', 'CANCELACION'}),
    ],
)
def test_enums_contienen_todos_los_valores_del_ddl(modelo, columna, valores):
    assert set(modelo.__table__.c[columna].type.enums) == valores


def test_enum_rechaza_un_estado_invalido():
    engine = _engine()
    with Session(engine) as session:
        torneo = _torneo()
        torneo.estado = 'DESCONOCIDO'
        session.add(torneo)
        with pytest.raises(StatementError):
            session.commit()


def test_clases_para_todas_las_tablas_son_importables():
    modelos = {
        ComunidadesTorneo,
        ComunidadesComunidad,
        ComunidadesEquipo,
        ComunidadesMiembro,
        ComunidadesRonda,
        ComunidadesEnfrentamiento,
        ComunidadesCategoriaEnfrentamiento,
        ComunidadesCategoriaPartido,
        ComunidadesEleccionAtacante,
        ComunidadesPartido,
        ComunidadesFotografiaEstado,
        ComunidadesHistorialTransicion,
        ComunidadesHistorialTransferencia,
        ComunidadesSnapshotClasificacionEquipo,
        ComunidadesSnapshotClasificacionComunidad,
        ComunidadesTrazaEmparejamiento,
    }
    assert {modelo.__tablename__ for modelo in modelos} == TABLAS_COMUNIDADES
