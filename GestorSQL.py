import mysql.connector
from dotenv import load_dotenv
import os
from sqlalchemy import (
    create_engine, Column, Integer, String, ForeignKey, DateTime, BigInteger,
    Text, Numeric, Boolean, Enum, JSON, SmallInteger, ForeignKeyConstraint, UniqueConstraint,
    CheckConstraint, Index, text, func,
)
from sqlalchemy import inspect
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

from SpinConstantes import AMBITO_SPIN_GENERAL, normalizar_ambito_spin


Base = declarative_base()

class Usuario(Base):
    __tablename__ = 'usuarios'
    idUsuarios = Column(Integer, primary_key=True)
    nombre_discord = Column(String)
    id_discord = Column(BigInteger)
    nombre_bloodbowl = Column(String)
    id_bloodbowl = Column(Integer)
    jornada_actual = Column(Integer)
    grupo = Column(Integer, ForeignKey('grupos.id_grupo'))
    raza = Column(String)
    nombreAMostrar = Column(String)
    color = Column(String)
    grupo_grupo = relationship("Grupo", foreign_keys=[grupo])
    preferencias_fecha = relationship("PreferenciasFecha", uselist=False, back_populates="usuario")
    resultados_encuesta = relationship("ResultadoEncuesta", back_populates="usuario")
    equipos_reformados= relationship("equiposReformados", back_populates="usuario")

class Desertor(Base):
    __tablename__ = 'desertores'
    idUsuarios = Column(Integer, primary_key=True)
    nombre_discord = Column(String)
    id_discord = Column(BigInteger)
    nombre_bloodbowl = Column(String)
    id_bloodbowl = Column(String)
    motivo = Column(Text)


class PreferenciasFecha(Base):
    __tablename__ = 'preferenciasFecha'
    idPref = Column(Integer, primary_key=True)
    preferencia = Column(Text)
    idUsuarios = Column(Integer, ForeignKey('usuarios.idUsuarios'), unique=True)
    usuario = relationship("Usuario", back_populates="preferencias_fecha")


class Grupo(Base):
    __tablename__ = 'grupos'
    id_grupo = Column(Integer, primary_key=True)
    nombre_grupo = Column(String)
    

class Partidos(Base):
    __tablename__ = 'partidos'
    
    idPartidos = Column(Integer, primary_key=True)
    resultado1 = Column(Integer)
    resultado2 = Column(Integer)
    lesiones1 = Column(Integer)
    lesiones2 = Column(Integer)
    muertes1 = Column(Integer)
    muertes2 = Column(Integer)
    idPartidoBbowl = Column(String)
    pases1 = Column(Integer)
    pases2 = Column(Integer)
    catches1 = Column(Integer)
    catches2 = Column(Integer)
    interceptions1 = Column(Integer)
    interceptions2 = Column(Integer)
    ko1 = Column(Integer)
    ko2 = Column(Integer)
    push1 = Column(Integer)
    push2 = Column(Integer)
    mRun1 = Column(Integer)
    mRun2 = Column(Integer)
    mPass1 = Column(Integer)
    mPass2 = Column(Integer)
    roster1 = Column(Integer, ForeignKey('Rosters.idRosters'), nullable=True)
    roster2 = Column(Integer, ForeignKey('Rosters.idRosters'), nullable=True)
    logo1 = Column(String)
    logo2 = Column(String)
    nombreEquipo1 = Column(String)
    nombreEquipo2 = Column(String)




class Calendario(Base):
    __tablename__ = 'calendario'
    
    idCalendario = Column('idCalendario', Integer, primary_key=True)
    jornada = Column('jornada', Integer)
    canalAsociado = Column('canalAsociado', BigInteger)
    coach1 = Column('coach1', Integer, ForeignKey('usuarios.idUsuarios'))
    coach2 = Column('coach2', Integer, ForeignKey('usuarios.idUsuarios'))
    fecha = Column('fecha', DateTime)
    fechaFinal = Column('fechaFinal', DateTime)
    partidos_idPartidos = Column('Partidos_idPartidos', Integer, ForeignKey('partidos.idPartidos'))
    partido = relationship("Partidos", foreign_keys=[partidos_idPartidos])
    usuario_coach1 = relationship("Usuario", foreign_keys=[coach1])
    usuario_coach2 = relationship("Usuario", foreign_keys=[coach2])
    
class Ticket(Base):
    __tablename__ = 'ticket'
    
    idTicket = Column('idTicket', Integer, primary_key=True)
    jornada = Column('jornada', Integer)
    canalAsociado = Column('canalAsociado', BigInteger)
    coach1 = Column('coach1', Integer, ForeignKey('usuarios.idUsuarios'))
    coach2 = Column('coach2', Integer, ForeignKey('usuarios.idUsuarios'))
    fecha = Column('fecha', DateTime)
    fechaFinal = Column('fechaFinal', DateTime)
    PuestoCoach1 = Column(Text)
    PuestoCoach2 = Column(Text)
    partidos_idPartidos = Column('Partidos_idPartidos', Integer, ForeignKey('partidos.idPartidos'))
    partido = relationship("Partidos", foreign_keys=[partidos_idPartidos])
    usuario_coach1 = relationship("Usuario", foreign_keys=[coach1])
    usuario_coach2 = relationship("Usuario", foreign_keys=[coach2])


class Rosters(Base):
    __tablename__ = 'Rosters'
    
    idRosters = Column(Integer, primary_key=True)

class Spin(Base):
    __tablename__ = 'Spin'
    
    idSpin = Column('idCalendario', Integer, primary_key=True)
    user = Column('user', String)
    fecha = Column('fecha', DateTime)
    tipo = Column('tipo', String)
    ambito = Column('ambito', String(32), nullable=False, default=AMBITO_SPIN_GENERAL, server_default=AMBITO_SPIN_GENERAL)
    usuario_discord_id = Column('usuario_discord_id', BigInteger, nullable=True)


def asegurar_columnas_historial_spin(engine=None):
    """Garantiza las columnas de auditoría en el historial de Spin.

    Según ``logicaSpin.md``, el historial debe distinguir el ámbito con los
    valores internos ``GENERAL`` y ``COMUNIDADES``. Además, para las liberaciones
    manuales debe quedar registrado el usuario de Discord que pulsó
    ``Encontrado``. Los registros previos a ``ambito`` pertenecen al Spin
    General, por lo que se rellenan como ``GENERAL``.
    """
    engine = engine or conexionEngine()
    inspector = inspect(engine)
    columnas_spin = {columna["name"] for columna in inspector.get_columns(Spin.__tablename__)}

    with engine.begin() as conexion:
        if "ambito" not in columnas_spin:
            conexion.execute(
                text(
                    "ALTER TABLE Spin ADD COLUMN ambito VARCHAR(32) NOT NULL DEFAULT 'GENERAL'"
                )
            )
        if "usuario_discord_id" not in columnas_spin:
            conexion.execute(
                text(
                    "ALTER TABLE Spin ADD COLUMN usuario_discord_id BIGINT NULL"
                )
            )
        conexion.execute(
            text(
                "UPDATE Spin SET ambito = :ambito_general "
                "WHERE ambito IS NULL OR ambito = ''"
            ),
            {"ambito_general": AMBITO_SPIN_GENERAL},
        )


def asegurar_columna_ambito_spin(engine=None):
    """Compatibilidad: delega en la rutina completa de historial Spin."""
    asegurar_columnas_historial_spin(engine)


def insertar_spin(usuario, fecha, tipo, ambito=AMBITO_SPIN_GENERAL, usuario_discord_id=None):
    # Esta es la función que inserta un nuevo Spin en la base de datos.
    # Los Spins heredados son Spin General, pero el despliegue puede convivir
    # temporalmente con bases de datos donde aún no exista la columna `ambito`.
    ambito_normalizado = normalizar_ambito_spin(ambito) or AMBITO_SPIN_GENERAL
    engine = conexionEngine()
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        asegurar_columnas_historial_spin(engine)
        valores = {
            "usuario": usuario,
            "fecha": fecha,
            "tipo": tipo,
            "ambito": ambito_normalizado,
            "usuario_discord_id": usuario_discord_id,
        }
        session.execute(
            text(
                "INSERT INTO Spin (`user`, fecha, tipo, ambito, usuario_discord_id) "
                "VALUES (:usuario, :fecha, :tipo, :ambito, :usuario_discord_id)"
            ),
            valores,
        )
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"Error al insertar en la tabla Spin: {e}")
    finally:
        session.close()

class ResultadoEncuesta(Base):
    __tablename__ = 'resultadosEncuesta'

    id = Column(Integer, primary_key=True)
    id_usuario = Column(Integer, ForeignKey('usuarios.idUsuarios'))
    id_pregunta = Column(Integer)
    respuesta = Column(Text)

    usuario = relationship("Usuario", back_populates="resultados_encuesta")

class Inscripcion(Base):
    __tablename__ = 'Inscripcion'

    id = Column(Integer, primary_key=True)
    id_usuario_discord = Column(Integer)
    division = Column(Text)
    pref1 = Column(Text)
    pref2 = Column(Text)
    pref3 = Column(Text)
    pref4 = Column(Text)
    pref5 = Column(Text)
    ban1 = Column(Text)
    ban2 = Column(Text)
    ban3 = Column(Text)
    ban4 = Column(Text)
    ban5 = Column(Text)
    nombre_bloodbowl = Column(Text)
    nombre_equipo = Column(Text)
    tipoPreferencia = Column(Text)


class equiposReformados(Base):
    __tablename__ = 'equiposReformados'

    id = Column(Integer, primary_key=True)
    id_usuario = Column(Integer, ForeignKey('usuarios.idUsuarios'))
    id_equipo = Column(Integer)
    nombre_equipo = Column(Text)
    raza = Column(Text)
    edicionesJugadas = Column(Integer)
    registro_partidos = relationship("RegistroPartidos", back_populates="equipo_reformado")
    recompensas       = relationship("Recompensas",     back_populates="equipo_reformado")

    usuario = relationship("Usuario", back_populates="equipos_reformados")
    

class PlayOffsOro(Base):
    __tablename__ = 'PlayOffsOro'
    
    idCalendario = Column('idCalendario', Integer, primary_key=True)
    jornada = Column('jornada', Integer)
    canalAsociado = Column('canalAsociado', BigInteger)
    coach1 = Column('coach1', Integer, ForeignKey('usuarios.idUsuarios'))
    coach2 = Column('coach2', Integer, ForeignKey('usuarios.idUsuarios'))
    fecha = Column('fecha', DateTime)
    fechaFinal = Column('fechaFinal', DateTime)
    PuestoCoach1 = Column(Text)
    PuestoCoach2 = Column(Text)
    partidos_idPartidos = Column('Partidos_idPartidos', Integer, ForeignKey('partidos.idPartidos'))
    partido = relationship("Partidos", foreign_keys=[partidos_idPartidos])
    usuario_coach1 = relationship("Usuario", foreign_keys=[coach1])
    usuario_coach2 = relationship("Usuario", foreign_keys=[coach2])

class PlayOffsPlata(Base):
    __tablename__ = 'PlayOffsPlata'
    
    idCalendario = Column('idCalendario', Integer, primary_key=True)
    jornada = Column('jornada', Integer)
    canalAsociado = Column('canalAsociado', BigInteger)
    coach1 = Column('coach1', Integer, ForeignKey('usuarios.idUsuarios'))
    coach2 = Column('coach2', Integer, ForeignKey('usuarios.idUsuarios'))
    fecha = Column('fecha', DateTime)
    fechaFinal = Column('fechaFinal', DateTime)
    PuestoCoach1 = Column(Text)
    PuestoCoach2 = Column(Text)
    partidos_idPartidos = Column('Partidos_idPartidos', Integer, ForeignKey('partidos.idPartidos'))
    partido = relationship("Partidos", foreign_keys=[partidos_idPartidos])
    usuario_coach1 = relationship("Usuario", foreign_keys=[coach1])
    usuario_coach2 = relationship("Usuario", foreign_keys=[coach2])
    
class PlayOffsBronce(Base):
    __tablename__ = 'PlayOffsBronce'
    
    idCalendario = Column('idCalendario', Integer, primary_key=True)
    jornada = Column('jornada', Integer)
    canalAsociado = Column('canalAsociado', BigInteger)
    coach1 = Column('coach1', Integer, ForeignKey('usuarios.idUsuarios'))
    coach2 = Column('coach2', Integer, ForeignKey('usuarios.idUsuarios'))
    fecha = Column('fecha', DateTime)
    fechaFinal = Column('fechaFinal', DateTime)
    PuestoCoach1 = Column(Text)
    PuestoCoach2 = Column(Text)
    partidos_idPartidos = Column('Partidos_idPartidos', Integer, ForeignKey('partidos.idPartidos'))
    partido = relationship("Partidos", foreign_keys=[partidos_idPartidos])
    usuario_coach1 = relationship("Usuario", foreign_keys=[coach1])
    usuario_coach2 = relationship("Usuario", foreign_keys=[coach2])

class RegistroPartidos(Base):
    __tablename__ = 'registroPartidos'

    id = Column(Integer, primary_key=True, autoincrement=True)
    idEquiposReformados = Column(Integer, ForeignKey('equiposReformados.id'), nullable=False)
    Edicion = Column(Integer, nullable=False)
    ganados = Column(Integer, nullable=False, default=0)
    empatados = Column(Integer, nullable=False, default=0)
    perdidos = Column(Integer, nullable=False, default=0)
    usado = Column(Boolean, nullable=False, default=False)

    equipo_reformado = relationship("equiposReformados", back_populates="registro_partidos")

class Recompensas(Base):
    __tablename__ = 'recompensas'

    id                   = Column(Integer, primary_key=True, autoincrement=True)
    idEquiposReformados  = Column(Integer, ForeignKey('equiposReformados.id'), nullable=False)
    sesion               = Column(Integer, nullable=False)
    recompensa           = Column(Numeric(10,2), nullable=False)

    # Relación con equiposReformados
    equipo_reformado     = relationship("equiposReformados", back_populates="recompensas")


class SuizoTorneo(Base):
    __tablename__ = 'suizo_torneo'

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(120), nullable=False)
    idCompBbowl = Column(String(45), nullable=True)
    activo = Column(Boolean, nullable=False, default=True)
    estado = Column(Enum('CREADO', 'EN_CURSO', 'FINALIZADO', name='suizo_torneo_estado'), nullable=False, default='CREADO')
    rondas_totales = Column(Integer, nullable=False)
    ida_vuelta = Column(Boolean, nullable=False, default=False)
    formato_serie = Column(Enum('BO1', 'BO3', 'BO5', name='suizo_torneo_formato_serie'), nullable=False, default='BO1')
    puntos_win = Column(Numeric(4, 2), nullable=False, default=3.00)
    puntos_draw = Column(Numeric(4, 2), nullable=False, default=1.00)
    puntos_loss = Column(Numeric(4, 2), nullable=False, default=0.00)
    puntos_bye = Column(Numeric(4, 2), nullable=False, default=1.50)
    fecha_fin_ronda1 = Column(DateTime, nullable=False)
    dias_por_ronda = Column(Integer, nullable=False, default=7)
    canal_hub_id = Column(BigInteger, nullable=True)
    mensajeInicial = Column(Text, nullable=True)
    mensajesSubsiguientes = Column(Text, nullable=True)
    creado_por_discord_id = Column(BigInteger, nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    participantes = relationship("SuizoParticipante", back_populates="torneo", cascade="all, delete-orphan")
    rondas = relationship("SuizoRonda", back_populates="torneo", cascade="all, delete-orphan")
    emparejamientos = relationship("SuizoEmparejamiento", back_populates="torneo", cascade="all, delete-orphan")


class SuizoParticipante(Base):
    __tablename__ = 'suizo_participante'

    id = Column(Integer, primary_key=True, autoincrement=True)
    torneo_id = Column(Integer, ForeignKey('suizo_torneo.id'), nullable=False)
    usuario_id = Column(Integer, ForeignKey('usuarios.idUsuarios'), nullable=False)
    estado = Column(Enum('ACTIVO', 'RETIRADO', name='suizo_participante_estado'), nullable=False, default='ACTIVO')
    tiene_bye = Column(Boolean, nullable=False, default=False)
    cantidad_byes = Column(Integer, nullable=False, default=0)
    late_join_ronda = Column(Integer, nullable=True)
    puntos_ajuste_inicial = Column(Numeric(6, 2), nullable=False, default=0.00)
    raza_competicion = Column(String(80), nullable=True)
    created_at = Column(DateTime, nullable=False)

    torneo = relationship("SuizoTorneo", back_populates="participantes")
    usuario = relationship("Usuario", foreign_keys=[usuario_id])


class SuizoRonda(Base):
    __tablename__ = 'suizo_ronda'

    id = Column(Integer, primary_key=True, autoincrement=True)
    torneo_id = Column(Integer, ForeignKey('suizo_torneo.id'), nullable=False)
    numero = Column(Integer, nullable=False)
    estado = Column(Enum('ABIERTA', 'BLOQUEADA', 'CERRADA', name='suizo_ronda_estado'), nullable=False, default='ABIERTA')
    fecha_inicio = Column(DateTime, nullable=False)
    fecha_fin = Column(DateTime, nullable=False)
    generada_por_discord_id = Column(BigInteger, nullable=True)
    cerrada_en = Column(DateTime, nullable=True)

    torneo = relationship("SuizoTorneo", back_populates="rondas")
    emparejamientos = relationship("SuizoEmparejamiento", back_populates="ronda", cascade="all, delete-orphan")


class SuizoEmparejamiento(Base):
    __tablename__ = 'suizo_emparejamiento'

    id = Column(Integer, primary_key=True, autoincrement=True)
    torneo_id = Column(Integer, ForeignKey('suizo_torneo.id'), nullable=False)
    ronda_id = Column(Integer, ForeignKey('suizo_ronda.id'), nullable=False)
    mesa_numero = Column(Integer, nullable=False)
    coach1_usuario_id = Column(Integer, ForeignKey('usuarios.idUsuarios'), nullable=False)
    coach2_usuario_id = Column(Integer, ForeignKey('usuarios.idUsuarios'), nullable=True)
    canal_id = Column(BigInteger, nullable=True)
    fecha = Column(DateTime, nullable=True)
    estado = Column(Enum('PENDIENTE', 'REPORTADO', 'ADMINISTRADO', 'CERRADO', name='suizo_emparejamiento_estado'), nullable=False, default='PENDIENTE')
    es_bye = Column(Boolean, nullable=False, default=False)
    forfeit_tipo = Column(Enum('NONE', 'LOCAL', 'VISITANTE', 'DOBLE', name='suizo_emparejamiento_forfeit_tipo'), nullable=False, default='NONE')
    partidos_requeridos = Column(Integer, nullable=False, default=1)
    partidos_reportados = Column(Integer, nullable=False, default=0)
    score_final_c1 = Column(Integer, nullable=False, default=0)
    score_final_c2 = Column(Integer, nullable=False, default=0)
    puntos_c1 = Column(Numeric(6, 2), nullable=False, default=0.00)
    puntos_c2 = Column(Numeric(6, 2), nullable=False, default=0.00)
    ganador_usuario_id = Column(Integer, ForeignKey('usuarios.idUsuarios'), nullable=True)
    resultado_origen = Column(Enum('API', 'ADMIN', 'BYE', name='suizo_emparejamiento_resultado_origen'), nullable=True)

    torneo = relationship("SuizoTorneo", back_populates="emparejamientos")
    ronda = relationship("SuizoRonda", back_populates="emparejamientos")
    coach1_usuario = relationship("Usuario", foreign_keys=[coach1_usuario_id])
    coach2_usuario = relationship("Usuario", foreign_keys=[coach2_usuario_id])
    ganador_usuario = relationship("Usuario", foreign_keys=[ganador_usuario_id])
    games = relationship("SuizoGame", back_populates="emparejamiento", cascade="all, delete-orphan")


class SuizoGame(Base):
    __tablename__ = 'suizo_game'

    id = Column(Integer, primary_key=True, autoincrement=True)
    emparejamiento_id = Column(Integer, ForeignKey('suizo_emparejamiento.id'), nullable=False)
    game_index = Column(Integer, nullable=False)
    id_partido_bbowl = Column(String(64), nullable=True)
    score_c1 = Column(Integer, nullable=False, default=0)
    score_c2 = Column(Integer, nullable=False, default=0)
    origen = Column(Enum('API', 'ADMIN', name='suizo_game_origen'), nullable=False)
    confirmado = Column(Boolean, nullable=False, default=True)
    fecha_registro = Column(DateTime, nullable=False)

    emparejamiento = relationship("SuizoEmparejamiento", back_populates="games")


class SuizoStandingSnapshot(Base):
    __tablename__ = 'suizo_standing_snapshot'

    id = Column(Integer, primary_key=True, autoincrement=True)
    torneo_id = Column(Integer, ForeignKey('suizo_torneo.id'), nullable=False)
    ronda_numero = Column(Integer, nullable=False)
    usuario_id = Column(Integer, ForeignKey('usuarios.idUsuarios'), nullable=False)
    estado_participante = Column(Enum('ACTIVO', 'RETIRADO', name='suizo_standing_snapshot_estado_participante'), nullable=False)
    pj = Column(Integer, nullable=False, default=0)
    pg = Column(Integer, nullable=False, default=0)
    pe = Column(Integer, nullable=False, default=0)
    pp = Column(Integer, nullable=False, default=0)
    puntos = Column(Numeric(6, 2), nullable=False, default=0.00)
    score_favor = Column(Integer, nullable=False, default=0)
    score_contra = Column(Integer, nullable=False, default=0)
    diff_score = Column(Integer, nullable=False, default=0)
    buchholz_cut = Column(Numeric(8, 2), nullable=False, default=0.00)
    h2h_valor = Column(Numeric(8, 2), nullable=True)
    rank_ronda = Column(Integer, nullable=False)
    json_detalle_tiebreak = Column(JSON, nullable=True)

    torneo = relationship("SuizoTorneo")
    usuario = relationship("Usuario", foreign_keys=[usuario_id])


class SuizoPairingTrace(Base):
    __tablename__ = 'suizo_pairing_trace'

    id = Column(Integer, primary_key=True, autoincrement=True)
    torneo_id = Column(Integer, ForeignKey('suizo_torneo.id'), nullable=False)
    ronda_id = Column(Integer, ForeignKey('suizo_ronda.id'), nullable=False)
    seed_snapshot_id = Column(Integer, ForeignKey('suizo_standing_snapshot.id'), nullable=True)
    intento = Column(Integer, nullable=False)
    resultado = Column(Enum('OK', 'FALLBACK_REPETIDO', 'FALLBACK_MIRROR', 'SIN_SOLUCION', name='suizo_pairing_trace_resultado'), nullable=False)
    reglas_aplicadas = Column(JSON, nullable=True)
    conflictos = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False)

    torneo = relationship("SuizoTorneo")
    ronda = relationship("SuizoRonda")
    seed_snapshot = relationship("SuizoStandingSnapshot")



_COMUNIDADES_RELATIONSHIP_OVERLAPS = (
    'torneo,comunidades,equipos,rondas,enfrentamientos,ronda,comunidad,miembros,'
    'equipo,equipo_a,equipo_b,ganador_equipo,elecciones_atacante,partidos,'
    'fotografias_estado,transferencias,snapshots_clasificacion,trazas_emparejamiento,'
    'equipo_local,equipo_visitante,equipo_origen,equipo_destino'
)


def _comunidades_enum(*values, name):
    """Enum del esquema de comunidades, validado también cuando se usa SQLite."""
    return Enum(
        *values,
        name=name,
        validate_strings=True,
        create_constraint=True,
    )


class ComunidadesTorneo(Base):
    __tablename__ = 'comunidades_torneo'
    __table_args__ = (
        CheckConstraint('rondas_totales > 0', name='ck_comunidades_torneo_rondas'),
        CheckConstraint('dias_por_ronda > 0', name='ck_comunidades_torneo_dias'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(120), nullable=False)
    estado = Column(_comunidades_enum('CREADO', 'EN_CURSO', 'FINALIZADO', name='comunidades_torneo_estado'), nullable=False, server_default=text("'CREADO'"))
    rondas_totales = Column(Integer, nullable=False)
    fecha_fin_ronda1 = Column(DateTime, nullable=False)
    dias_por_ronda = Column(Integer, nullable=False, server_default=text('7'))
    id_competicion_bbowl = Column(String(45), nullable=True)
    canal_hub_id = Column(BigInteger, nullable=True)
    puntos_clasificacion_victoria = Column(Numeric(6, 2), nullable=False, server_default=text('3.00'))
    puntos_clasificacion_empate = Column(Numeric(6, 2), nullable=False, server_default=text('1.00'))
    puntos_clasificacion_derrota = Column(Numeric(6, 2), nullable=False, server_default=text('0.00'))
    puntos_clasificacion_bye = Column(Numeric(6, 2), nullable=False, server_default=text('1.50'))
    puntos_individuales_victoria = Column(Numeric(6, 2), nullable=False, server_default=text('3.00'))
    puntos_individuales_empate = Column(Numeric(6, 2), nullable=False, server_default=text('1.00'))
    puntos_individuales_derrota = Column(Numeric(6, 2), nullable=False, server_default=text('0.00'))
    plantilla_mensaje_ronda1 = Column(Text, nullable=False)
    plantilla_mensaje_rondas_siguientes = Column(Text, nullable=False)
    creado_por_discord_id = Column(BigInteger, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())
    updated_at = Column(DateTime, nullable=False, server_default=func.current_timestamp(), onupdate=func.current_timestamp())

    comunidades = relationship('ComunidadesComunidad', back_populates='torneo', cascade='all, delete-orphan', overlaps=_COMUNIDADES_RELATIONSHIP_OVERLAPS)
    equipos = relationship('ComunidadesEquipo', back_populates='torneo', cascade='all, delete-orphan', overlaps=_COMUNIDADES_RELATIONSHIP_OVERLAPS)
    rondas = relationship('ComunidadesRonda', back_populates='torneo', cascade='all, delete-orphan', overlaps=_COMUNIDADES_RELATIONSHIP_OVERLAPS)
    enfrentamientos = relationship('ComunidadesEnfrentamiento', back_populates='torneo', cascade='all, delete-orphan', overlaps=_COMUNIDADES_RELATIONSHIP_OVERLAPS)
    categorias_enfrentamiento = relationship('ComunidadesCategoriaEnfrentamiento', back_populates='torneo', cascade='all, delete-orphan', overlaps=_COMUNIDADES_RELATIONSHIP_OVERLAPS)
    categorias_partido = relationship('ComunidadesCategoriaPartido', back_populates='torneo', cascade='all, delete-orphan', overlaps=_COMUNIDADES_RELATIONSHIP_OVERLAPS)


class ComunidadesComunidad(Base):
    __tablename__ = 'comunidades_comunidad'
    __table_args__ = (
        UniqueConstraint('id', 'torneo_id', name='uk_comunidades_comunidad_id_torneo'),
        UniqueConstraint('torneo_id', 'nombre', name='uk_comunidades_comunidad_torneo_nombre'),
        CheckConstraint('zombies_matados >= 0', name='ck_comunidades_comunidad_zombies_matados'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    torneo_id = Column(Integer, ForeignKey('comunidades_torneo.id', ondelete='CASCADE'), nullable=False)
    nombre = Column(String(120), nullable=False)
    puntos_zombificaciones = Column(Numeric(8, 2), nullable=False, server_default=text('0.00'))
    zombies_matados = Column(Integer, nullable=False, server_default=text('0'))
    created_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())
    updated_at = Column(DateTime, nullable=False, server_default=func.current_timestamp(), onupdate=func.current_timestamp())

    torneo = relationship('ComunidadesTorneo', back_populates='comunidades', overlaps=_COMUNIDADES_RELATIONSHIP_OVERLAPS)
    equipos = relationship('ComunidadesEquipo', back_populates='comunidad', cascade='all, delete-orphan', overlaps=_COMUNIDADES_RELATIONSHIP_OVERLAPS)
    fotografias_estado = relationship('ComunidadesFotografiaEstado', back_populates='comunidad', overlaps=_COMUNIDADES_RELATIONSHIP_OVERLAPS)
    transferencias = relationship('ComunidadesHistorialTransferencia', back_populates='comunidad', overlaps=_COMUNIDADES_RELATIONSHIP_OVERLAPS)
    snapshots_clasificacion = relationship('ComunidadesSnapshotClasificacionComunidad', back_populates='comunidad', overlaps=_COMUNIDADES_RELATIONSHIP_OVERLAPS)


class ComunidadesEquipo(Base):
    __tablename__ = 'comunidades_equipo'
    __table_args__ = (
        UniqueConstraint('id', 'torneo_id', name='uk_comunidades_equipo_id_torneo'),
        UniqueConstraint('torneo_id', 'nombre', name='uk_comunidades_equipo_torneo_nombre'),
        CheckConstraint('es_zombie IN (0, 1)', name='ck_comunidades_equipo_es_zombie'),
        CheckConstraint('cantidad_byes >= 0 AND partidos_jugados >= 0 AND victorias >= 0 AND empates >= 0 AND derrotas >= 0', name='ck_comunidades_equipo_contadores'),
        ForeignKeyConstraint(['comunidad_id', 'torneo_id'], ['comunidades_comunidad.id', 'comunidades_comunidad.torneo_id'], name='fk_comunidades_equipo_comunidad_torneo', ondelete='CASCADE'),
        Index('idx_comunidades_equipo_torneo_comunidad', 'torneo_id', 'comunidad_id'),
        Index('idx_comunidades_equipo_comunidad_torneo', 'comunidad_id', 'torneo_id'),
        Index('idx_comunidades_equipo_clasificacion', 'torneo_id', 'puntos_clasificacion', 'buchholz_cut'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    torneo_id = Column(Integer, ForeignKey('comunidades_torneo.id', ondelete='CASCADE'), nullable=False)
    comunidad_id = Column(Integer, nullable=False)
    nombre = Column(String(120), nullable=False)
    es_zombie = Column(Boolean, nullable=False, server_default=text('0'))
    estado_temporal = Column(_comunidades_enum('NEUTRO', 'CAZADOR', 'CAZADOR_Z', 'HERIDO', name='comunidades_estado_temporal'), nullable=False, server_default=text("'NEUTRO'"))
    cantidad_byes = Column(Integer, nullable=False, server_default=text('0'))
    partidos_jugados = Column(Integer, nullable=False, server_default=text('0'))
    victorias = Column(Integer, nullable=False, server_default=text('0'))
    empates = Column(Integer, nullable=False, server_default=text('0'))
    derrotas = Column(Integer, nullable=False, server_default=text('0'))
    puntos_clasificacion = Column(Numeric(8, 2), nullable=False, server_default=text('0.00'))
    td_favor = Column(Integer, nullable=False, server_default=text('0'))
    td_contra = Column(Integer, nullable=False, server_default=text('0'))
    buchholz_cut = Column(Numeric(10, 2), nullable=False, server_default=text('0.00'))
    created_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())
    updated_at = Column(DateTime, nullable=False, server_default=func.current_timestamp(), onupdate=func.current_timestamp())

    torneo = relationship('ComunidadesTorneo', back_populates='equipos', foreign_keys=[torneo_id], overlaps=_COMUNIDADES_RELATIONSHIP_OVERLAPS)
    comunidad = relationship('ComunidadesComunidad', back_populates='equipos', foreign_keys=[comunidad_id, torneo_id], overlaps=_COMUNIDADES_RELATIONSHIP_OVERLAPS)
    miembros = relationship('ComunidadesMiembro', back_populates='equipo', cascade='all, delete-orphan', overlaps=_COMUNIDADES_RELATIONSHIP_OVERLAPS)


class ComunidadesMiembro(Base):
    __tablename__ = 'comunidades_miembro'
    __table_args__ = (
        UniqueConstraint('equipo_id', 'posicion', name='uk_comunidades_miembro_equipo_posicion'),
        UniqueConstraint('torneo_id', 'usuario_id', name='uk_comunidades_miembro_torneo_usuario'),
        CheckConstraint('posicion IN (1, 2)', name='ck_comunidades_miembro_posicion'),
        ForeignKeyConstraint(['equipo_id', 'torneo_id'], ['comunidades_equipo.id', 'comunidades_equipo.torneo_id'], name='fk_comunidades_miembro_equipo_torneo', ondelete='CASCADE'),
        Index('idx_comunidades_miembro_equipo_torneo', 'equipo_id', 'torneo_id'),
        Index('idx_comunidades_miembro_usuario', 'usuario_id'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    torneo_id = Column(Integer, nullable=False)
    equipo_id = Column(Integer, nullable=False)
    usuario_id = Column(Integer, ForeignKey('usuarios.idUsuarios', ondelete='RESTRICT'), nullable=False)
    raza = Column(String(80), nullable=False)
    posicion = Column(SmallInteger, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())

    equipo = relationship('ComunidadesEquipo', back_populates='miembros', foreign_keys=[equipo_id, torneo_id], overlaps=_COMUNIDADES_RELATIONSHIP_OVERLAPS)
    usuario = relationship('Usuario', foreign_keys=[usuario_id], overlaps=_COMUNIDADES_RELATIONSHIP_OVERLAPS)


class ComunidadesRonda(Base):
    __tablename__ = 'comunidades_ronda'
    __table_args__ = (
        UniqueConstraint('id', 'torneo_id', name='uk_comunidades_ronda_id_torneo'),
        UniqueConstraint('torneo_id', 'numero', name='uk_comunidades_ronda_torneo_numero'),
        CheckConstraint('numero > 0', name='ck_comunidades_ronda_numero'),
        CheckConstraint('fecha_fin >= fecha_inicio', name='ck_comunidades_ronda_fechas'),
        Index('idx_comunidades_ronda_torneo_estado', 'torneo_id', 'estado'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    torneo_id = Column(Integer, ForeignKey('comunidades_torneo.id', ondelete='CASCADE'), nullable=False)
    numero = Column(Integer, nullable=False)
    estado = Column(_comunidades_enum('ABIERTA', 'BLOQUEADA', 'PENDIENTE_TRANSFERENCIAS', 'CERRADA', name='comunidades_ronda_estado'), nullable=False, server_default=text("'ABIERTA'"))
    fecha_inicio = Column(DateTime, nullable=False)
    fecha_fin = Column(DateTime, nullable=False)
    generada_por_discord_id = Column(BigInteger, nullable=False)
    cerrada_en = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())
    updated_at = Column(DateTime, nullable=False, server_default=func.current_timestamp(), onupdate=func.current_timestamp())

    torneo = relationship('ComunidadesTorneo', back_populates='rondas', overlaps=_COMUNIDADES_RELATIONSHIP_OVERLAPS)
    enfrentamientos = relationship('ComunidadesEnfrentamiento', back_populates='ronda', cascade='all, delete-orphan', overlaps=_COMUNIDADES_RELATIONSHIP_OVERLAPS)
    trazas_emparejamiento = relationship('ComunidadesTrazaEmparejamiento', back_populates='ronda', cascade='all, delete-orphan', overlaps=_COMUNIDADES_RELATIONSHIP_OVERLAPS)


class ComunidadesEnfrentamiento(Base):
    __tablename__ = 'comunidades_enfrentamiento'
    __table_args__ = (
        UniqueConstraint('id', 'torneo_id', name='uk_comunidades_enfrentamiento_id_torneo'),
        UniqueConstraint('ronda_id', 'mesa_numero', name='uk_comunidades_enfrentamiento_ronda_mesa'),
        UniqueConstraint('ronda_id', 'equipo_a_id', name='uk_comunidades_enfrentamiento_ronda_equipo_a'),
        UniqueConstraint('ronda_id', 'equipo_b_id', name='uk_comunidades_enfrentamiento_ronda_equipo_b'),
        UniqueConstraint('canal_general_discord_id', name='uk_com_enfrentamiento_canal'),
        CheckConstraint('mesa_numero > 0', name='ck_comunidades_enfrentamiento_mesa'),
        CheckConstraint('equipo_a_id <> equipo_b_id', name='ck_comunidades_enfrentamiento_equipos'),
        CheckConstraint('ganador_equipo_id IS NULL OR ganador_equipo_id IN (equipo_a_id, equipo_b_id)', name='ck_comunidades_enfrentamiento_ganador'),
        CheckConstraint('es_doble_forfait IN (0, 1)', name='ck_comunidades_enfrentamiento_doble_forfait'),
        ForeignKeyConstraint(['ronda_id', 'torneo_id'], ['comunidades_ronda.id', 'comunidades_ronda.torneo_id'], name='fk_comunidades_enfrentamiento_ronda_torneo', ondelete='CASCADE'),
        ForeignKeyConstraint(['equipo_a_id', 'torneo_id'], ['comunidades_equipo.id', 'comunidades_equipo.torneo_id'], name='fk_comunidades_enfrentamiento_equipo_a_torneo', ondelete='CASCADE'),
        ForeignKeyConstraint(['equipo_b_id', 'torneo_id'], ['comunidades_equipo.id', 'comunidades_equipo.torneo_id'], name='fk_comunidades_enfrentamiento_equipo_b_torneo', ondelete='CASCADE'),
        ForeignKeyConstraint(['ganador_equipo_id', 'torneo_id'], ['comunidades_equipo.id', 'comunidades_equipo.torneo_id'], name='fk_comunidades_enfrentamiento_ganador_torneo', ondelete='CASCADE'),
        Index('idx_comunidades_enfrentamiento_torneo_ronda_estado', 'torneo_id', 'ronda_id', 'estado'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    torneo_id = Column(Integer, ForeignKey('comunidades_torneo.id', ondelete='CASCADE'), nullable=False)
    ronda_id = Column(Integer, nullable=False)
    mesa_numero = Column(Integer, nullable=False)
    equipo_a_id = Column(Integer, nullable=False)
    equipo_b_id = Column(Integer, nullable=False)
    canal_general_discord_id = Column(BigInteger, nullable=True)
    estado = Column(_comunidades_enum('PENDIENTE_ELECCIONES', 'ELECCIONES_COMPLETAS', 'PARTIDOS_CREADOS', 'EN_CURSO', 'CERRADO', 'ADMINISTRADO', name='comunidades_enfrentamiento_estado'), nullable=False, server_default=text("'PENDIENTE_ELECCIONES'"))
    puntos_internos_a = Column(Numeric(8, 2), nullable=False, server_default=text('0.00'))
    puntos_internos_b = Column(Numeric(8, 2), nullable=False, server_default=text('0.00'))
    td_favor_a = Column(Integer, nullable=False, server_default=text('0'))
    td_contra_a = Column(Integer, nullable=False, server_default=text('0'))
    td_favor_b = Column(Integer, nullable=False, server_default=text('0'))
    td_contra_b = Column(Integer, nullable=False, server_default=text('0'))
    td_atacante_a = Column(Integer, nullable=False, server_default=text('0'))
    td_atacante_b = Column(Integer, nullable=False, server_default=text('0'))
    ganador_equipo_id = Column(Integer, nullable=True)
    puntos_clasificacion_a = Column(Numeric(8, 2), nullable=False, server_default=text('0.00'))
    puntos_clasificacion_b = Column(Numeric(8, 2), nullable=False, server_default=text('0.00'))
    resultado_origen = Column(_comunidades_enum('API', 'ADMIN', name='comunidades_resultado_origen'), nullable=True)
    es_doble_forfait = Column(Boolean, nullable=False, server_default=text('0'))
    created_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())
    updated_at = Column(DateTime, nullable=False, server_default=func.current_timestamp(), onupdate=func.current_timestamp())

    torneo = relationship('ComunidadesTorneo', back_populates='enfrentamientos', foreign_keys=[torneo_id], overlaps=_COMUNIDADES_RELATIONSHIP_OVERLAPS)
    ronda = relationship('ComunidadesRonda', back_populates='enfrentamientos', foreign_keys=[ronda_id, torneo_id], overlaps=_COMUNIDADES_RELATIONSHIP_OVERLAPS)
    equipo_a = relationship('ComunidadesEquipo', foreign_keys=[equipo_a_id, torneo_id], overlaps=_COMUNIDADES_RELATIONSHIP_OVERLAPS)
    equipo_b = relationship('ComunidadesEquipo', foreign_keys=[equipo_b_id, torneo_id], overlaps=_COMUNIDADES_RELATIONSHIP_OVERLAPS)
    ganador_equipo = relationship('ComunidadesEquipo', foreign_keys=[ganador_equipo_id, torneo_id], overlaps=_COMUNIDADES_RELATIONSHIP_OVERLAPS)
    elecciones_atacante = relationship('ComunidadesEleccionAtacante', back_populates='enfrentamiento', cascade='all, delete-orphan', overlaps=_COMUNIDADES_RELATIONSHIP_OVERLAPS)
    partidos = relationship('ComunidadesPartido', back_populates='enfrentamiento', cascade='all, delete-orphan', overlaps=_COMUNIDADES_RELATIONSHIP_OVERLAPS)
    fotografias_estado = relationship('ComunidadesFotografiaEstado', back_populates='enfrentamiento', cascade='all, delete-orphan', overlaps=_COMUNIDADES_RELATIONSHIP_OVERLAPS)


class ComunidadesCategoriaEnfrentamiento(Base):
    __tablename__ = 'comunidades_categoria_enfrentamiento'
    __table_args__ = (
        UniqueConstraint('torneo_id', 'categoria_discord_id', name='uk_com_cat_enf_torneo_categoria'),
        UniqueConstraint('torneo_id', 'orden_alta', name='uk_com_cat_enf_torneo_orden'),
        CheckConstraint('orden_alta > 0', name='ck_com_cat_enf_orden'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    torneo_id = Column(Integer, ForeignKey('comunidades_torneo.id', ondelete='CASCADE'), nullable=False)
    categoria_discord_id = Column(BigInteger, nullable=False)
    orden_alta = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())

    torneo = relationship('ComunidadesTorneo', back_populates='categorias_enfrentamiento', overlaps=_COMUNIDADES_RELATIONSHIP_OVERLAPS)


class ComunidadesCategoriaPartido(Base):
    __tablename__ = 'comunidades_categoria_partido'
    __table_args__ = (
        UniqueConstraint('torneo_id', 'categoria_discord_id', name='uk_com_cat_par_torneo_categoria'),
        UniqueConstraint('torneo_id', 'orden_alta', name='uk_com_cat_par_torneo_orden'),
        CheckConstraint('orden_alta > 0', name='ck_com_cat_par_orden'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    torneo_id = Column(Integer, ForeignKey('comunidades_torneo.id', ondelete='CASCADE'), nullable=False)
    categoria_discord_id = Column(BigInteger, nullable=False)
    orden_alta = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())

    torneo = relationship('ComunidadesTorneo', back_populates='categorias_partido', overlaps=_COMUNIDADES_RELATIONSHIP_OVERLAPS)


class ComunidadesEleccionAtacante(Base):
    __tablename__ = 'comunidades_eleccion_atacante'
    __table_args__ = (
        UniqueConstraint('enfrentamiento_id', 'equipo_id', name='uk_com_eleccion_enfrentamiento_equipo'),
        CheckConstraint('atacante_usuario_id <> defensor_usuario_id', name='ck_com_eleccion_jugadores'),
        CheckConstraint('bloqueada IN (0, 1)', name='ck_com_eleccion_bloqueada'),
        ForeignKeyConstraint(['enfrentamiento_id', 'torneo_id'], ['comunidades_enfrentamiento.id', 'comunidades_enfrentamiento.torneo_id'], name='fk_com_eleccion_enfrentamiento', ondelete='CASCADE'),
        ForeignKeyConstraint(['equipo_id', 'torneo_id'], ['comunidades_equipo.id', 'comunidades_equipo.torneo_id'], name='fk_com_eleccion_equipo_torneo', ondelete='CASCADE'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    torneo_id = Column(Integer, ForeignKey('comunidades_torneo.id', ondelete='CASCADE'), nullable=False)
    enfrentamiento_id = Column(Integer, nullable=False)
    equipo_id = Column(Integer, nullable=False)
    atacante_usuario_id = Column(Integer, ForeignKey('usuarios.idUsuarios', ondelete='RESTRICT'), nullable=False)
    defensor_usuario_id = Column(Integer, ForeignKey('usuarios.idUsuarios', ondelete='RESTRICT'), nullable=False)
    elegido_por_discord_id = Column(BigInteger, nullable=False)
    elegido_en = Column(DateTime, nullable=False, server_default=func.current_timestamp())
    bloqueada = Column(Boolean, nullable=False, server_default=text('0'))

    enfrentamiento = relationship('ComunidadesEnfrentamiento', back_populates='elecciones_atacante', foreign_keys=[enfrentamiento_id, torneo_id], overlaps=_COMUNIDADES_RELATIONSHIP_OVERLAPS)
    equipo = relationship('ComunidadesEquipo', foreign_keys=[equipo_id, torneo_id], overlaps=_COMUNIDADES_RELATIONSHIP_OVERLAPS)
    atacante_usuario = relationship('Usuario', foreign_keys=[atacante_usuario_id], overlaps=_COMUNIDADES_RELATIONSHIP_OVERLAPS)
    defensor_usuario = relationship('Usuario', foreign_keys=[defensor_usuario_id], overlaps=_COMUNIDADES_RELATIONSHIP_OVERLAPS)


class ComunidadesPartido(Base):
    __tablename__ = 'comunidades_partido'
    __table_args__ = (
        UniqueConstraint('enfrentamiento_id', 'indice', name='uk_com_partido_enfrentamiento_indice'),
        UniqueConstraint('partido_bloodbowl_id', name='uk_com_partido_bloodbowl'),
        UniqueConstraint('canal_discord_id', name='uk_com_partido_canal'),
        CheckConstraint('indice IN (1, 2)', name='ck_com_partido_indice'),
        CheckConstraint('equipo_local_id <> equipo_visitante_id', name='ck_com_partido_equipos'),
        CheckConstraint('usuario_local_id <> usuario_visitante_id', name='ck_com_partido_usuarios'),
        CheckConstraint('atacante_usuario_id <> defensor_usuario_id', name='ck_com_partido_roles'),
        CheckConstraint('(td_local IS NULL AND td_visitante IS NULL) OR (td_local >= 0 AND td_visitante >= 0)', name='ck_com_partido_td'),
        ForeignKeyConstraint(['enfrentamiento_id', 'torneo_id'], ['comunidades_enfrentamiento.id', 'comunidades_enfrentamiento.torneo_id'], name='fk_com_partido_enfrentamiento', ondelete='CASCADE'),
        ForeignKeyConstraint(['equipo_local_id', 'torneo_id'], ['comunidades_equipo.id', 'comunidades_equipo.torneo_id'], name='fk_com_partido_equipo_local', ondelete='CASCADE'),
        ForeignKeyConstraint(['equipo_visitante_id', 'torneo_id'], ['comunidades_equipo.id', 'comunidades_equipo.torneo_id'], name='fk_com_partido_equipo_visitante', ondelete='CASCADE'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    torneo_id = Column(Integer, ForeignKey('comunidades_torneo.id', ondelete='CASCADE'), nullable=False)
    enfrentamiento_id = Column(Integer, nullable=False)
    indice = Column(SmallInteger, nullable=False)
    equipo_local_id = Column(Integer, nullable=False)
    equipo_visitante_id = Column(Integer, nullable=False)
    usuario_local_id = Column(Integer, ForeignKey('usuarios.idUsuarios', ondelete='RESTRICT'), nullable=False)
    usuario_visitante_id = Column(Integer, ForeignKey('usuarios.idUsuarios', ondelete='RESTRICT'), nullable=False)
    atacante_usuario_id = Column(Integer, ForeignKey('usuarios.idUsuarios', ondelete='RESTRICT'), nullable=False)
    defensor_usuario_id = Column(Integer, ForeignKey('usuarios.idUsuarios', ondelete='RESTRICT'), nullable=False)
    canal_discord_id = Column(BigInteger, nullable=True)
    partido_bloodbowl_id = Column(String(45), nullable=True)
    fecha = Column(DateTime, nullable=True)
    td_local = Column(Integer, nullable=True)
    td_visitante = Column(Integer, nullable=True)
    puntos_internos_local = Column(Numeric(8, 2), nullable=True)
    puntos_internos_visitante = Column(Numeric(8, 2), nullable=True)
    estado = Column(_comunidades_enum('PENDIENTE', 'EN_CURSO', 'FINALIZADO', 'ADMINISTRADO', name='comunidades_partido_estado'), nullable=False, server_default=text("'PENDIENTE'"))
    resultado_origen = Column(_comunidades_enum('API', 'ADMIN', name='comunidades_partido_resultado_origen'), nullable=True)
    tipo_forfait = Column(_comunidades_enum('LOCAL', 'VISITANTE', 'DOBLE', name='comunidades_partido_tipo_forfait'), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())
    updated_at = Column(DateTime, nullable=False, server_default=func.current_timestamp(), onupdate=func.current_timestamp())

    enfrentamiento = relationship('ComunidadesEnfrentamiento', back_populates='partidos', foreign_keys=[enfrentamiento_id, torneo_id], overlaps=_COMUNIDADES_RELATIONSHIP_OVERLAPS)
    equipo_local = relationship('ComunidadesEquipo', foreign_keys=[equipo_local_id, torneo_id], overlaps=_COMUNIDADES_RELATIONSHIP_OVERLAPS)
    equipo_visitante = relationship('ComunidadesEquipo', foreign_keys=[equipo_visitante_id, torneo_id], overlaps=_COMUNIDADES_RELATIONSHIP_OVERLAPS)
    usuario_local = relationship('Usuario', foreign_keys=[usuario_local_id], overlaps=_COMUNIDADES_RELATIONSHIP_OVERLAPS)
    usuario_visitante = relationship('Usuario', foreign_keys=[usuario_visitante_id], overlaps=_COMUNIDADES_RELATIONSHIP_OVERLAPS)
    atacante_usuario = relationship('Usuario', foreign_keys=[atacante_usuario_id], overlaps=_COMUNIDADES_RELATIONSHIP_OVERLAPS)
    defensor_usuario = relationship('Usuario', foreign_keys=[defensor_usuario_id], overlaps=_COMUNIDADES_RELATIONSHIP_OVERLAPS)


class ComunidadesFotografiaEstado(Base):
    __tablename__ = 'comunidades_fotografia_estado'
    __table_args__ = (
        UniqueConstraint('enfrentamiento_id', 'equipo_id', name='uk_com_foto_enfrentamiento_equipo'),
        CheckConstraint('es_zombie IN (0, 1)', name='ck_com_foto_zombie'),
        ForeignKeyConstraint(['ronda_id', 'torneo_id'], ['comunidades_ronda.id', 'comunidades_ronda.torneo_id'], name='fk_com_foto_ronda', ondelete='CASCADE'),
        ForeignKeyConstraint(['enfrentamiento_id', 'torneo_id'], ['comunidades_enfrentamiento.id', 'comunidades_enfrentamiento.torneo_id'], name='fk_com_foto_enfrentamiento', ondelete='CASCADE'),
        ForeignKeyConstraint(['equipo_id', 'torneo_id'], ['comunidades_equipo.id', 'comunidades_equipo.torneo_id'], name='fk_com_foto_equipo', ondelete='CASCADE'),
        ForeignKeyConstraint(['comunidad_id', 'torneo_id'], ['comunidades_comunidad.id', 'comunidades_comunidad.torneo_id'], name='fk_com_foto_comunidad', ondelete='CASCADE'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    torneo_id = Column(Integer, ForeignKey('comunidades_torneo.id', ondelete='CASCADE'), nullable=False)
    ronda_id = Column(Integer, nullable=False)
    enfrentamiento_id = Column(Integer, nullable=False)
    equipo_id = Column(Integer, nullable=False)
    comunidad_id = Column(Integer, nullable=False)
    es_zombie = Column(Boolean, nullable=False)
    estado_temporal = Column(_comunidades_enum('NEUTRO', 'CAZADOR', 'CAZADOR_Z', 'HERIDO', name='comunidades_fotografia_estado_temporal'), nullable=False)
    fotografiado_en = Column(DateTime, nullable=False, server_default=func.current_timestamp())

    ronda = relationship('ComunidadesRonda', foreign_keys=[ronda_id, torneo_id], overlaps=_COMUNIDADES_RELATIONSHIP_OVERLAPS)
    enfrentamiento = relationship('ComunidadesEnfrentamiento', back_populates='fotografias_estado', foreign_keys=[enfrentamiento_id, torneo_id], overlaps=_COMUNIDADES_RELATIONSHIP_OVERLAPS)
    equipo = relationship('ComunidadesEquipo', foreign_keys=[equipo_id, torneo_id], overlaps=_COMUNIDADES_RELATIONSHIP_OVERLAPS)
    comunidad = relationship('ComunidadesComunidad', back_populates='fotografias_estado', foreign_keys=[comunidad_id, torneo_id], overlaps=_COMUNIDADES_RELATIONSHIP_OVERLAPS)


class ComunidadesHistorialTransicion(Base):
    __tablename__ = 'comunidades_historial_transicion'
    __table_args__ = (
        UniqueConstraint(
            'enfrentamiento_id',
            'equipo_id',
            name='uk_com_transicion_enfrentamiento_equipo',
        ),
        CheckConstraint('es_zombie_anterior IN (0, 1)', name='ck_com_transicion_zombie_anterior'),
        CheckConstraint('es_zombie_posterior IN (0, 1)', name='ck_com_transicion_zombie_posterior'),
        CheckConstraint('puntos_comunitarios_generados >= 0 AND kills_generadas >= 0', name='ck_com_transicion_contadores'),
        ForeignKeyConstraint(['ronda_id', 'torneo_id'], ['comunidades_ronda.id', 'comunidades_ronda.torneo_id'], name='fk_com_transicion_ronda', ondelete='CASCADE'),
        ForeignKeyConstraint(['enfrentamiento_id', 'torneo_id'], ['comunidades_enfrentamiento.id', 'comunidades_enfrentamiento.torneo_id'], name='fk_com_transicion_enfrentamiento', ondelete='CASCADE'),
        ForeignKeyConstraint(['equipo_id', 'torneo_id'], ['comunidades_equipo.id', 'comunidades_equipo.torneo_id'], name='fk_com_transicion_equipo', ondelete='CASCADE'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    torneo_id = Column(Integer, ForeignKey('comunidades_torneo.id', ondelete='CASCADE'), nullable=False)
    ronda_id = Column(Integer, nullable=False)
    enfrentamiento_id = Column(Integer, nullable=True)
    equipo_id = Column(Integer, nullable=False)
    estado_temporal_anterior = Column(_comunidades_enum('NEUTRO', 'CAZADOR', 'CAZADOR_Z', 'HERIDO', name='comunidades_transicion_estado_anterior'), nullable=False)
    es_zombie_anterior = Column(Boolean, nullable=False)
    estado_temporal_posterior = Column(_comunidades_enum('NEUTRO', 'CAZADOR', 'CAZADOR_Z', 'HERIDO', name='comunidades_transicion_estado_posterior'), nullable=False)
    es_zombie_posterior = Column(Boolean, nullable=False)
    motivo = Column(_comunidades_enum('VICTORIA', 'DERROTA', 'EMPATE', 'BYE', 'ZOMBIFICACION', 'KILL', 'DOBLE_FORFAIT', 'TRANSFERENCIA', name='comunidades_transicion_motivo'), nullable=False)
    puntos_comunitarios_generados = Column(Numeric(10, 2), nullable=False, server_default=text('0.00'))
    kills_generadas = Column(Integer, nullable=False, server_default=text('0'))
    created_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())

    ronda = relationship('ComunidadesRonda', foreign_keys=[ronda_id, torneo_id], overlaps=_COMUNIDADES_RELATIONSHIP_OVERLAPS)
    enfrentamiento = relationship('ComunidadesEnfrentamiento', foreign_keys=[enfrentamiento_id, torneo_id], overlaps=_COMUNIDADES_RELATIONSHIP_OVERLAPS)
    equipo = relationship('ComunidadesEquipo', foreign_keys=[equipo_id, torneo_id], overlaps=_COMUNIDADES_RELATIONSHIP_OVERLAPS)


class ComunidadesHistorialTransferencia(Base):
    __tablename__ = 'comunidades_historial_transferencia'
    __table_args__ = (
        UniqueConstraint(
            'clave_idempotencia', name='uk_com_transferencia_idempotencia'
        ),
        CheckConstraint('equipo_origen_id <> equipo_destino_id', name='ck_com_transferencia_equipos'),
        ForeignKeyConstraint(['comunidad_id', 'torneo_id'], ['comunidades_comunidad.id', 'comunidades_comunidad.torneo_id'], name='fk_com_transferencia_comunidad', ondelete='CASCADE'),
        ForeignKeyConstraint(['equipo_origen_id', 'torneo_id'], ['comunidades_equipo.id', 'comunidades_equipo.torneo_id'], name='fk_com_transferencia_origen', ondelete='CASCADE'),
        ForeignKeyConstraint(['equipo_destino_id', 'torneo_id'], ['comunidades_equipo.id', 'comunidades_equipo.torneo_id'], name='fk_com_transferencia_destino', ondelete='CASCADE'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    torneo_id = Column(Integer, ForeignKey('comunidades_torneo.id', ondelete='CASCADE'), nullable=False)
    ronda_id = Column(Integer, nullable=False)
    comunidad_id = Column(Integer, nullable=False)
    equipo_origen_id = Column(Integer, nullable=False)
    equipo_destino_id = Column(Integer, nullable=False)
    tipo = Column(_comunidades_enum('CAZADOR', 'CAZADOR_Z', name='comunidades_transferencia_tipo'), nullable=False)
    ejecutada_por_discord_id = Column(BigInteger, nullable=False)
    clave_idempotencia = Column(String(190), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())

    comunidad = relationship('ComunidadesComunidad', back_populates='transferencias', foreign_keys=[comunidad_id, torneo_id], overlaps=_COMUNIDADES_RELATIONSHIP_OVERLAPS)
    equipo_origen = relationship('ComunidadesEquipo', foreign_keys=[equipo_origen_id, torneo_id], overlaps=_COMUNIDADES_RELATIONSHIP_OVERLAPS)
    equipo_destino = relationship('ComunidadesEquipo', foreign_keys=[equipo_destino_id, torneo_id], overlaps=_COMUNIDADES_RELATIONSHIP_OVERLAPS)


class ComunidadesSnapshotClasificacionEquipo(Base):
    __tablename__ = 'comunidades_snapshot_clasificacion_equipo'
    __table_args__ = (
        UniqueConstraint('ronda_id', 'equipo_id', name='uk_com_snap_equipo_ronda_equipo'),
        CheckConstraint('posicion > 0', name='ck_com_snap_equipo_posicion'),
        CheckConstraint('td_favor >= 0 AND td_contra >= 0 AND partidos_jugados >= 0 AND victorias >= 0 AND empates >= 0 AND derrotas >= 0 AND cantidad_byes >= 0', name='ck_com_snap_equipo_contadores'),
        ForeignKeyConstraint(['equipo_id', 'torneo_id'], ['comunidades_equipo.id', 'comunidades_equipo.torneo_id'], name='fk_com_snap_equipo_equipo', ondelete='CASCADE'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    torneo_id = Column(Integer, ForeignKey('comunidades_torneo.id', ondelete='CASCADE'), nullable=False)
    ronda_id = Column(Integer, nullable=False)
    equipo_id = Column(Integer, nullable=False)
    posicion = Column(Integer, nullable=False)
    puntos_clasificacion = Column(Numeric(10, 2), nullable=False)
    buchholz_cut = Column(Numeric(10, 2), nullable=False)
    puntos_enfrentamiento_directo = Column(Numeric(10, 2), nullable=True)
    td_favor = Column(Integer, nullable=False)
    td_contra = Column(Integer, nullable=False)
    partidos_jugados = Column(Integer, nullable=False)
    victorias = Column(Integer, nullable=False)
    empates = Column(Integer, nullable=False)
    derrotas = Column(Integer, nullable=False)
    cantidad_byes = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())

    equipo = relationship('ComunidadesEquipo', foreign_keys=[equipo_id, torneo_id], overlaps=_COMUNIDADES_RELATIONSHIP_OVERLAPS)


class ComunidadesSnapshotClasificacionComunidad(Base):
    __tablename__ = 'comunidades_snapshot_clasificacion_comunidad'
    __table_args__ = (
        UniqueConstraint('ronda_id', 'comunidad_id', name='uk_com_snap_comunidad_ronda_comunidad'),
        CheckConstraint('posicion > 0', name='ck_com_snap_comunidad_posicion'),
        CheckConstraint('puntos_zombificaciones >= 0 AND zombies_matados >= 0', name='ck_com_snap_comunidad_contadores'),
        ForeignKeyConstraint(['comunidad_id', 'torneo_id'], ['comunidades_comunidad.id', 'comunidades_comunidad.torneo_id'], name='fk_com_snap_comunidad', ondelete='CASCADE'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    torneo_id = Column(Integer, ForeignKey('comunidades_torneo.id', ondelete='CASCADE'), nullable=False)
    ronda_id = Column(Integer, nullable=False)
    comunidad_id = Column(Integer, nullable=False)
    posicion = Column(Integer, nullable=False)
    puntos_zombificaciones = Column(Numeric(10, 2), nullable=False)
    zombies_matados = Column(Integer, nullable=False)
    suma_puntos_equipos = Column(Numeric(10, 2), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())

    comunidad = relationship('ComunidadesComunidad', back_populates='snapshots_clasificacion', foreign_keys=[comunidad_id, torneo_id], overlaps=_COMUNIDADES_RELATIONSHIP_OVERLAPS)


class ComunidadesOperacionIdempotente(Base):
    """Reserva persistida para coordinar efectos externos y reintentos.

    La clave es estable y legible (por ejemplo ``publicacion:global-hub:42`` o
    ``canal-partido:81``). El estado PENDIENTE actúa como lease recuperable y
    COMPLETADA conserva el identificador del recurso externo creado.
    """

    __tablename__ = 'comunidades_operacion_idempotente'
    __table_args__ = (
        UniqueConstraint('clave', name='uk_com_operacion_clave'),
        CheckConstraint(
            "estado IN ('PENDIENTE','COMPLETADA')",
            name='ck_com_operacion_estado',
        ),
        Index(
            'idx_com_operacion_contexto',
            'torneo_id', 'ronda_id', 'enfrentamiento_id', 'partido_id',
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    clave = Column(String(190), nullable=False)
    tipo = Column(String(45), nullable=False)
    estado = Column(
        _comunidades_enum(
            'PENDIENTE', 'COMPLETADA', name='comunidades_operacion_estado'
        ),
        nullable=False,
        server_default=text("'PENDIENTE'"),
    )
    torneo_id = Column(Integer, ForeignKey('comunidades_torneo.id', ondelete='CASCADE'), nullable=False)
    ronda_id = Column(Integer, nullable=True)
    enfrentamiento_id = Column(Integer, nullable=True)
    partido_id = Column(Integer, nullable=True)
    recurso_externo_id = Column(String(120), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())
    updated_at = Column(DateTime, nullable=False, server_default=func.current_timestamp(), onupdate=func.current_timestamp())


class ComunidadesTrazaEmparejamiento(Base):
    __tablename__ = 'comunidades_traza_emparejamiento'
    __table_args__ = (
        UniqueConstraint('ronda_id', 'secuencia', name='uk_com_traza_ronda_secuencia'),
        CheckConstraint('secuencia > 0', name='ck_com_traza_secuencia'),
        CheckConstraint('equipo_a_id IS NULL OR equipo_b_id IS NULL OR equipo_a_id <> equipo_b_id', name='ck_com_traza_equipos'),
        CheckConstraint('es_mirror IS NULL OR es_mirror IN (0, 1)', name='ck_com_traza_mirror'),
        CheckConstraint('es_rival_repetido IS NULL OR es_rival_repetido IN (0, 1)', name='ck_com_traza_repetido'),
        ForeignKeyConstraint(['ronda_id', 'torneo_id'], ['comunidades_ronda.id', 'comunidades_ronda.torneo_id'], name='fk_com_traza_ronda', ondelete='CASCADE'),
        ForeignKeyConstraint(['equipo_a_id', 'torneo_id'], ['comunidades_equipo.id', 'comunidades_equipo.torneo_id'], name='fk_com_traza_equipo_a', ondelete='CASCADE'),
        ForeignKeyConstraint(['equipo_b_id', 'torneo_id'], ['comunidades_equipo.id', 'comunidades_equipo.torneo_id'], name='fk_com_traza_equipo_b', ondelete='CASCADE'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    torneo_id = Column(Integer, ForeignKey('comunidades_torneo.id', ondelete='CASCADE'), nullable=False)
    ronda_id = Column(Integer, nullable=False)
    secuencia = Column(Integer, nullable=False)
    etapa = Column(_comunidades_enum('BASE', 'PERMITIR_MIRRORS', 'PERMITIR_ESTADOS_NO_DESEADOS', 'PERMITIR_REPETIDOS', 'SELECCION_BYE', 'SELECCION_FINAL', 'CANCELACION', name='comunidades_traza_etapa'), nullable=False)
    equipo_a_id = Column(Integer, nullable=True)
    equipo_b_id = Column(Integer, nullable=True)
    diferencia_puntos = Column(Numeric(10, 2), nullable=True)
    es_mirror = Column(Boolean, nullable=True)
    es_rival_repetido = Column(Boolean, nullable=True)
    prioridad_estado = Column(Integer, nullable=True)
    desempate_aleatorio = Column(Numeric(18, 17), nullable=True)
    detalle = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())

    ronda = relationship('ComunidadesRonda', back_populates='trazas_emparejamiento', foreign_keys=[ronda_id, torneo_id], overlaps=_COMUNIDADES_RELATIONSHIP_OVERLAPS)
    equipo_a = relationship('ComunidadesEquipo', foreign_keys=[equipo_a_id, torneo_id], overlaps=_COMUNIDADES_RELATIONSHIP_OVERLAPS)
    equipo_b = relationship('ComunidadesEquipo', foreign_keys=[equipo_b_id, torneo_id], overlaps=_COMUNIDADES_RELATIONSHIP_OVERLAPS)


# Alias singulares para mantener importaciones directas legibles y compatibles.
ComunidadTorneo = ComunidadesTorneo
Comunidad = ComunidadesComunidad
ComunidadEquipo = ComunidadesEquipo
ComunidadMiembro = ComunidadesMiembro
ComunidadRonda = ComunidadesRonda
ComunidadEnfrentamiento = ComunidadesEnfrentamiento
ComunidadCategoriaEnfrentamiento = ComunidadesCategoriaEnfrentamiento
ComunidadCategoriaPartido = ComunidadesCategoriaPartido
ComunidadEleccionAtacante = ComunidadesEleccionAtacante
ComunidadPartido = ComunidadesPartido
ComunidadFotografiaEstado = ComunidadesFotografiaEstado
ComunidadHistorialTransicion = ComunidadesHistorialTransicion
ComunidadHistorialTransferencia = ComunidadesHistorialTransferencia
ComunidadSnapshotClasificacionEquipo = ComunidadesSnapshotClasificacionEquipo
ComunidadSnapshotClasificacionComunidad = ComunidadesSnapshotClasificacionComunidad
ComunidadTrazaEmparejamiento = ComunidadesTrazaEmparejamiento


def conexionEngine():
    # Conectarse a la base de datos y crear una sesión
    load_dotenv()
    user = os.getenv('UsuBD')
    password = os.getenv('PassBD')
    engine = create_engine(f'mysql+mysqlconnector://{user}:{password}@localhost/ButterCup')
    return engine
    
