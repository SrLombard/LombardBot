import mysql.connector
from dotenv import load_dotenv
import os
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime, BigInteger, Text, Numeric, Boolean, Enum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship


Base = declarative_base()

class Usuario(Base):
    __tablename__ = 'usuarios'
    idUsuarios = Column(Integer, primary_key=True)
    nombre_discord = Column(String)
    id_discord = Column(Integer)
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


def insertar_spin( usuario, fecha, tipo):
    # Esta es la función que inserta un nuevo Spin en la base de datos
    new_spin = Spin(user=usuario, fecha=fecha, tipo=tipo)
    Session = sessionmaker(bind=conexionEngine())
    session = Session()
    try:
        session.add(new_spin)
        session.commit()
    except Exception as e:
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

def conexionEngine():
    # Conectarse a la base de datos y crear una sesión
    load_dotenv()
    user = os.getenv('UsuBD')
    password = os.getenv('PassBD')
    engine = create_engine(f'mysql+mysqlconnector://{user}:{password}@localhost/ButterCup')
    return engine
    
