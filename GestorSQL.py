import mysql.connector
from dotenv import load_dotenv
import os
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime, BigInteger, Text, Numeric, Boolean
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

def conexionEngine():
    # Conectarse a la base de datos y crear una sesión
    load_dotenv()
    user = os.getenv('UsuBD')
    password = os.getenv('PassBD')
    engine = create_engine(f'mysql+mysqlconnector://{user}:{password}@localhost/ButterCup')
    return engine
    