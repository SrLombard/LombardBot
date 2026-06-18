import discord
from discord.ext import commands
from discord import app_commands
from dataclasses import dataclass
from typing import Optional
from threading import Thread
import threading
import Imagenes

from sqlalchemy.sql.functions import now
from sqlalchemy import BIGINT, create_engine, Column, Integer, String, ForeignKey, false, true,text
from sqlalchemy import and_, or_ ,null
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.orm import aliased, joinedload
from sqlalchemy.sql import case,func

import GestorSQL
from SpinConstantes import (
    AMBITO_SPIN_COMUNIDADES,
    AMBITO_SPIN_GENERAL,
    CANAL_SPIN_COMUNIDADES_ID,
    CANAL_SPIN_GENERAL_ID,
    normalizar_ambito_spin,
)

import asyncio
from datetime import datetime




@dataclass(frozen=True)
class SpinMatchResult:
    """Partido elegible para Spin con estructura común para todos los ámbitos.

    ``logicaSpin.md`` define que General y Comunidades deben resolver sus
    partidos hacia una misma frontera de datos. Los campos que no apliquen a un
    ámbito concreto permanecen en ``None`` para que la UI de Spin consuma una
    estructura estable sin conocer la tabla de origen.
    """

    ambito: str
    canal_partido_id: Optional[int]
    jugador1_discord_id: Optional[int]
    jugador2_discord_id: Optional[int]
    fecha: Optional[datetime]
    descripcion_corta: Optional[str]
    descripcion_larga: Optional[str]
    torneo_id: Optional[int] = None
    partido_id: Optional[int] = None
    enfrentamiento_id: Optional[int] = None
    indice_partido: Optional[int] = None
    equipo_a_nombre: Optional[str] = None
    equipo_b_nombre: Optional[str] = None


@dataclass
class SpinReservation:
    """Reserva temporal independiente de una cola de Spin."""

    ambito: str
    usuario_spin: object
    jugador1_discord_id: int
    jugador2_discord_id: int
    canal_spin: object
    canal_partido: object
    descripcion_partido: str
    timeout_task: asyncio.Task
    partido: SpinMatchResult


# Almacén en memoria de reservas activas. Cada ámbito de Spin tiene una cola
# independiente; UsuarioSpin queda solo como alias heredado no funcional.
reservas_spin = {
    AMBITO_SPIN_GENERAL: None,
    AMBITO_SPIN_COMUNIDADES: None,
}
bloqueos_reservas_spin = {
    AMBITO_SPIN_GENERAL: asyncio.Lock(),
    AMBITO_SPIN_COMUNIDADES: asyncio.Lock(),
}
UsuarioSpin = None


def obtener_reserva_spin(ambito):
    return reservas_spin.get(ambito)


def obtener_bloqueo_reserva_spin(ambito):
    return bloqueos_reservas_spin[ambito]


def guardar_reserva_spin(reserva):
    reservas_spin[reserva.ambito] = reserva


def limpiar_reserva_spin(ambito):
    reserva = reservas_spin.get(ambito)
    reservas_spin[ambito] = None
    return reserva


def discord_ids_jugadores_reserva(reserva):
    """Devuelve los Discord IDs autorizados a liberar una reserva de Spin.

    La fuente de verdad de ``logicaSpin.md`` permite pulsar `Encontrado` a
    cualquiera de los dos jugadores del partido reservado, y no contempla
    excepciones por roles administrativos desde el botón.
    """

    return {
        jugador_id
        for jugador_id in (
            getattr(reserva, "jugador1_discord_id", None),
            getattr(reserva, "jugador2_discord_id", None),
        )
        if jugador_id is not None
    }


def get_int_value(dictionary, key):
    value = dictionary.get(key)
    return 0 if value is None else value


# Discord limita los mensajes de texto normales a 2000 caracteres.
# Usamos un margen de seguridad para no rozar el límite al añadir cabeceras,
# bloques de código o pequeñas variaciones de formato.
DISCORD_MAX_MESSAGE_CHARS = 2000
DISCORD_SAFE_MESSAGE_CHARS = 1900


def dividir_mensaje_discord(mensaje, limite=DISCORD_SAFE_MESSAGE_CHARS):
    """Divide un mensaje en partes válidas para Discord sin perder contenido.

    Prioriza cortar por líneas para mantener tablas y listados legibles. Si una
    sola línea supera el límite, la parte en trozos de tamaño seguro.
    """
    if mensaje is None:
        return []

    texto = str(mensaje)
    if texto == "":
        return []

    limite = int(limite or DISCORD_SAFE_MESSAGE_CHARS)
    if limite <= 0:
        limite = DISCORD_SAFE_MESSAGE_CHARS
    limite = min(limite, DISCORD_MAX_MESSAGE_CHARS)

    if len(texto) <= limite:
        return [texto]

    partes = []
    actual = ""

    for linea in texto.splitlines(keepends=True):
        if len(linea) > limite:
            if actual:
                partes.append(actual.rstrip("\n"))
                actual = ""
            inicio = 0
            while inicio < len(linea):
                trozo = linea[inicio:inicio + limite]
                inicio += limite
                if inicio < len(linea):
                    partes.append(trozo.rstrip("\n"))
                else:
                    actual = trozo
            continue

        if len(actual) + len(linea) > limite:
            partes.append(actual.rstrip("\n"))
            actual = linea
        else:
            actual += linea

    if actual:
        partes.append(actual.rstrip("\n"))

    return [parte if parte else "\u200b" for parte in partes]


async def enviar_mensaje_largo(destino, mensaje, limite=DISCORD_SAFE_MESSAGE_CHARS, **kwargs):
    """Envía un texto a un canal/contexto dividiéndolo si supera el límite."""
    enviados = []
    partes = dividir_mensaje_discord(mensaje, limite=limite)
    for parte in partes:
        enviados.append(await destino.send(parte, **kwargs))
    return enviados


async def responder_interaction_largo(interaction, mensaje, ephemeral=False, limite=DISCORD_SAFE_MESSAGE_CHARS):
    """Responde a una slash command dividiendo el mensaje en response + followups."""
    partes = dividir_mensaje_discord(mensaje, limite=limite)
    if not partes:
        partes = ["\u200b"]

    enviados = []
    primera = partes[0]
    if interaction.response.is_done():
        enviados.append(await interaction.followup.send(primera, ephemeral=ephemeral))
    else:
        await interaction.response.send_message(primera, ephemeral=ephemeral)

    for parte in partes[1:]:
        enviados.append(await interaction.followup.send(parte, ephemeral=ephemeral))
    return enviados


def crearEmbedPartido(coach, coachVisitante, match, propietario):
    invertir_valor = lambda x: 0 if x != 0 else 1
    
    # Función auxiliar para obtener valores enteros
    def get_int_value(dictionary, key):
        value = dictionary.get(key)
        return 0 if value is None else value

    # Obtener los índices de los equipos
    local_team = match['teams'][propietario]
    visitante_team = match['teams'][invertir_valor(propietario)]
    
    # Obtener los resultados utilizando get_int_value
    resultadoLocal = get_int_value(local_team, 'score')
    resultadoVisitante = get_int_value(visitante_team, 'score')
    
    mensaje = ''
    # Puedes descomentar y adaptar estos mensajes si lo deseas
    # if resultadoLocal > resultadoVisitante:
    #     mensaje = f"Felicidades por tu victoria {resultadoLocal} - {resultadoVisitante} contra {coachVisitante}"
    # elif resultadoVisitante > resultadoLocal:
    #     mensaje = f"Luchaste bien ese {resultadoLocal} - {resultadoVisitante} pero esta vez no se pudo ganar contra {coachVisitante}"
    # else:
    #     mensaje = f"Disputadísimo empate {resultadoLocal} - {resultadoVisitante} contra {coachVisitante}"

    embed = discord.Embed(
        title=coach['coachname'] + " vs " + match['coaches'][invertir_valor(propietario)]['coachname'],
        description=mensaje + "\n En este partido se enfrentaron",
        color=discord.Color.blue()
    )
    embed.add_field(name=local_team.get('teamname', ''), value=str(resultadoLocal), inline=True)
    embed.add_field(name=visitante_team.get('teamname', ''), value=str(resultadoVisitante), inline=True)
    embed.add_field(name='\u200b', value='\u200b', inline=False)  # Añade un espacio en blanco

    # Lesiones (sustainedcasualties - sustaineddead)
    lesiones_local = get_int_value(local_team, 'sustainedcasualties') - get_int_value(local_team, 'sustaineddead')
    lesiones_visitante = get_int_value(visitante_team, 'sustainedcasualties') - get_int_value(visitante_team, 'sustaineddead')

    embed.add_field(name='\U0001F691 Lesiones', value=str(lesiones_local), inline=True)
    embed.add_field(name='\U0001F691 Lesiones', value=str(lesiones_visitante), inline=True)
    embed.add_field(name='\u200b', value='\u200b', inline=False)

    # Muertes (sustaineddead)
    muertes_local = get_int_value(local_team, 'sustaineddead')
    muertes_visitante = get_int_value(visitante_team, 'sustaineddead')

    embed.add_field(name='\U0001F480 Muertes', value=str(muertes_local), inline=True)
    embed.add_field(name='\U0001F480 Muertes', value=str(muertes_visitante), inline=True)
    embed.add_field(name='\u200b', value='\u200b', inline=False)

    return embed


async def publicar(ctx, titulo, mensaje=None, embed=None,id_foro=None,idPartido=None):
    if id_foro:
        canal_foro = discord.utils.get(ctx.guild.channels, id=id_foro)
    else:
        canal_foro = discord.utils.get(ctx.guild.channels, id=1223765590146158653)
    
    # Verificar que el canal existe y es un foro
    if not canal_foro or not isinstance(canal_foro, discord.ForumChannel):
        await ctx.send("Canal de foro no encontrado.")
        return

    hilo_existente = None
    for hilo in canal_foro.threads:
        if hilo.name == titulo:
            hilo_existente = hilo
            break

    if hilo_existente:
        if mensaje:
            await hilo_existente.send(mensaje)
        elif embed:
            await hilo_existente.send(embed=embed)
        elif idPartido: 
            ruta_imagen = await Imagenes.imagenResultado(idPartido)
            with open(ruta_imagen, 'rb') as file:
                await hilo_existente.send(file=discord.File(file))
        
            threading.Timer(10, lambda: Imagenes.eliminar_imagen(ruta_imagen)).start()  

        await ctx.send("Mensaje publicado en el hilo existente.")
    else:
        if mensaje:           
            nuevo_hilo = await canal_foro.create_thread(name=titulo, content='Resultados de ' + titulo)
        elif embed:
            nuevo_hilo  = await canal_foro.create_thread(name=titulo, content='Resultados de ' + titulo)
            await nuevo_hilo.thread.send(embed=embed)
        elif idPartido:
            nuevo_hilo_msg = await canal_foro.create_thread(name=titulo, content='Resultados de ' + titulo)
            nuevo_hilo = nuevo_hilo_msg.thread  
            ruta_imagen = await Imagenes.imagenResultado(idPartido)
            with open(ruta_imagen, 'rb') as file:
                await nuevo_hilo.send(file=discord.File(file))
        
            threading.Timer(10, lambda: Imagenes.eliminar_imagen(ruta_imagen)).start()  
        await ctx.send("Hilo nuevo creado y mensaje publicado.")       


async def mensaje_administradores(mensaje):
    bot = DiscordClientSingleton.get_bot_instance()
    channel = bot.get_channel(457740100097540106)  # Asegúrate de que la ID del canal sea correcta
    await enviar_mensaje_largo(channel, mensaje)


async def gestionar_canal_discord(ctx, accion, nombre_canal=None, coach1_id_discord=None, coach2_id_discord=None, categoria_id=1325620233104527463, mensaje="", quedada=False, canal_id=None,raza1='',raza2='',fechalimite=0,preferencias1=['',''],preferencias2=['',''],bbname1='',bbname2=''):
    guild = ctx.guild
    categoria = discord.utils.get(guild.categories, id=int(categoria_id))
    fecha = ''
    if fechalimite > 0:
        fecha=f"\n\nLa Fecha límite para jugar el partido es el <t:{int(fechalimite)}:f>"
    
    mensajePreferencias1=''
    if preferencias1[0] and preferencias1[1]:
        mensajePreferencias1 = f"\n<@{preferencias1[0]}> suele poder jugar {preferencias1[1]}"
        
    mensajePreferencias2=''
    if preferencias2[0] and preferencias2[1]:
        mensajePreferencias2 = f"\n<@{preferencias2[0]}> suele poder jugar {preferencias2[1]}"


    if mensaje == "":
        if bbname1 and bbname2:
            mensaje = """Bienvenidos, {mention1}({raza1}) [{bbname1}] y {mention2}({raza2}) [{bbname2}]! 
                     
Por favor, acuerden una fecha para jugar el primer partido.""" + mensajePreferencias1 + mensajePreferencias2 + """

Cuando acordéis una fecha **usad** el comando `/fecha` para que el bot pueda registrar vuestro partido con el horario de España. Esto es **OBLIGATORIO** y para la administración será clave a la hora de tomar decisiones en caso de que alguien no se presente. {fecha}

Justo antes de jugar el partido tendréis que **USAR EL CANAL**  <#{CANAL_SPIN_GENERAL_ID}> y **LIBERARLO** al encontrar partido. De esta manera no os emparejará con otra persona.

Si hubiera cualquier problema mencionad a los comisarios que están para ayudar.
"""
        else:
            mensaje = """Bienvenidos, {mention1}({raza1}) y {mention2}({raza2})! 
            
Por favor, acuerden una fecha para jugar el primer partido.""" + mensajePreferencias1 + mensajePreferencias2 + """

Cuando acordéis una fecha **usad** el comando `/fecha` para que el bot pueda registrar vuestro partido con el horario de España. Esto es **OBLIGATORIO** y para la administración será clave a la hora de tomar decisiones en caso de que alguien no se presente. {fecha}

Justo antes de jugar el partido tendréis que **USAR EL CANAL**  <#{CANAL_SPIN_GENERAL_ID}> y **LIBERADLO** al encontrar partido. De esta manera no os emparejará con otra persona.

Si hubiera cualquier problema mencionad a los comisarios que están para ayudar.
"""


    if quedada:
        mensaje += ""


    if accion == "crear" and nombre_canal:
        nombre_canal_formato_discord = nombre_canal.lower().replace(" ", "-")
        comisarios_role = discord.utils.get(guild.roles, name="Comisario")
        if not comisarios_role:
            print("Rol 'Comisarios' no encontrado.")
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            comisarios_role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        try:
            canal = await guild.create_text_channel(name=nombre_canal_formato_discord, overwrites=overwrites, category=categoria)
            print(f"Canal {nombre_canal_formato_discord} creado exitosamente en la categoría {categoria.name}.")

            # Buscar los entrenadores y ajustar permisos
            coach1 = guild.get_member(coach1_id_discord)
            coach2 = guild.get_member(coach2_id_discord)
            if coach1:
                await canal.set_permissions(coach1, read_messages=True, send_messages=True)
            if coach2:
                await canal.set_permissions(coach2, read_messages=True, send_messages=True)

            # Preparar y enviar mensaje de bienvenida
            mention1 = coach1.mention if coach1 else ""
            mention2 = coach2.mention if coach2 else ""
            mensaje_formateado = mensaje.format(mention1=mention1, mention2=mention2,raza1=raza1,raza2=raza2,fecha=fecha,bbname1=bbname1,bbname2=bbname2)
            await canal.send(mensaje_formateado)
                
            return canal.id

        except Exception as e:
            print(f"No se pudo crear el canal {nombre_canal_formato_discord}: {e}")

    elif accion == "eliminar":
        print(f"[INFO] Llamada a gestionar_canal_discord con acción 'eliminar'. Canal ID: {canal_id}")
        await mensaje_administradores(f"[TRACE] Intentando eliminar canal con ID: {canal_id}")

        # Intentar encontrar el canal
        canal = guild.get_channel(canal_id)
        if canal:
            print(f"[INFO] Canal encontrado: {canal.name} (ID: {canal_id}). Intentando eliminar.")
            await mensaje_administradores(f"[TRACE] Canal encontrado: {canal.name} (ID: {canal_id}). Intentando eliminar.")
            try:
                # Intentar eliminar el canal
                await canal.delete()
                print(f"[INFO] Canal eliminado exitosamente: {canal.name} (ID: {canal_id})")
                await mensaje_administradores(f"[SUCCESS] Canal eliminado exitosamente: {canal.name} (ID: {canal_id})")
            except Exception as e:
                print(f"[ERROR] Error al intentar eliminar el canal con ID {canal_id}: {e}")
                await mensaje_administradores(f"[ERROR] No se pudo eliminar el canal con ID {canal_id}. Error: {e}")
        else:
            # Canal no encontrado
            print(f"[WARNING] Canal no encontrado. ID: {canal_id}. Puede haber sido eliminado previamente.")
            await mensaje_administradores(f"[WARNING] Canal no encontrado. ID: {canal_id}. Puede haber sido eliminado previamente.")
                


def _clave_orden_spin(partido: SpinMatchResult):
    """Ordena partidos por fecha cercana y después por identificadores estables."""

    ahora = datetime.utcnow()
    distancia_fecha = (
        abs((partido.fecha - ahora).total_seconds())
        if partido.fecha is not None
        else float("inf")
    )
    return (
        distancia_fecha,
        partido.torneo_id or 0,
        partido.enfrentamiento_id or 0,
        partido.indice_partido or 0,
        partido.partido_id or 0,
    )


def _spin_match_desde_partido_general(partido):
    canal_partido_id = getattr(partido, "canalAsociado", None) or getattr(partido, "canal_id", None)
    fecha = getattr(partido, "fecha", None)
    partido_id = getattr(partido, "idCalendario", None) or getattr(partido, "idTicket", None) or getattr(partido, "id", None)

    if hasattr(partido, "usuario_coach1"):
        jugador1_discord_id = getattr(partido.usuario_coach1, "id_discord", None)
        jugador2_discord_id = getattr(partido.usuario_coach2, "id_discord", None)
    else:
        jugador1_discord_id = getattr(partido.coach1_usuario, "id_discord", None)
        jugador2_discord_id = getattr(partido.coach2_usuario, "id_discord", None) if partido.coach2_usuario else jugador1_discord_id

    descripcion = f"Spin General reservado: <@{jugador1_discord_id}> y <@{jugador2_discord_id}> pueden buscar partido."
    return SpinMatchResult(
        ambito=AMBITO_SPIN_GENERAL,
        canal_partido_id=canal_partido_id,
        jugador1_discord_id=jugador1_discord_id,
        jugador2_discord_id=jugador2_discord_id,
        fecha=fecha,
        descripcion_corta=descripcion,
        descripcion_larga=descripcion,
        torneo_id=getattr(partido, "torneo_id", None),
        partido_id=partido_id,
        enfrentamiento_id=getattr(partido, "ronda_id", None),
        indice_partido=getattr(partido, "mesa_numero", None),
    )


def resolver_partido_spin_general(session, usuario_db):
    """Resuelve el partido elegible de Spin General o ``None``.

    ``logicaSpin.md`` define Spin General como la búsqueda agregada en
    Calendario, PlayOffsOro, PlayOffsPlata, PlayOffsBronce, Ticket y
    SuizoEmparejamiento, conservando los filtros existentes y devolviendo un
    ``SpinMatchResult`` normalizado.
    """

    partidos_calendario = session.query(GestorSQL.Calendario).filter(
        or_(GestorSQL.Calendario.coach1 == usuario_db.idUsuarios, GestorSQL.Calendario.coach2 == usuario_db.idUsuarios),
        GestorSQL.Calendario.canalAsociado != None,
        GestorSQL.Calendario.partidos_idPartidos == None
    ).all()
    partidos_playoffs_oro = session.query(GestorSQL.PlayOffsOro).filter(
        or_(GestorSQL.PlayOffsOro.coach1 == usuario_db.idUsuarios, GestorSQL.PlayOffsOro.coach2 == usuario_db.idUsuarios),
        GestorSQL.PlayOffsOro.canalAsociado != None,
        GestorSQL.PlayOffsOro.partidos_idPartidos == None
    ).all()
    partidos_playoffs_plata = session.query(GestorSQL.PlayOffsPlata).filter(
        or_(GestorSQL.PlayOffsPlata.coach1 == usuario_db.idUsuarios, GestorSQL.PlayOffsPlata.coach2 == usuario_db.idUsuarios),
        GestorSQL.PlayOffsPlata.canalAsociado != None,
        GestorSQL.PlayOffsPlata.partidos_idPartidos == None
    ).all()
    partidos_playoffs_bronce = session.query(GestorSQL.PlayOffsBronce).filter(
        or_(GestorSQL.PlayOffsBronce.coach1 == usuario_db.idUsuarios, GestorSQL.PlayOffsBronce.coach2 == usuario_db.idUsuarios),
        GestorSQL.PlayOffsBronce.canalAsociado != None,
        GestorSQL.PlayOffsBronce.partidos_idPartidos == None
    ).all()
    partidos_ticket = session.query(GestorSQL.Ticket).filter(
        or_(GestorSQL.Ticket.coach1 == usuario_db.idUsuarios, GestorSQL.Ticket.coach2 == usuario_db.idUsuarios),
        GestorSQL.Ticket.canalAsociado != None,
        GestorSQL.Ticket.partidos_idPartidos == None
    ).all()
    participantes_suizo = session.query(GestorSQL.SuizoParticipante).filter(
        GestorSQL.SuizoParticipante.usuario_id == usuario_db.idUsuarios,
        GestorSQL.SuizoParticipante.estado == "ACTIVO"
    ).all()
    torneos_suizo_ids = [p.torneo_id for p in participantes_suizo]
    partidos_suizo = []
    if torneos_suizo_ids:
        partidos_suizo = session.query(GestorSQL.SuizoEmparejamiento).filter(
            GestorSQL.SuizoEmparejamiento.torneo_id.in_(torneos_suizo_ids),
            or_(GestorSQL.SuizoEmparejamiento.coach1_usuario_id == usuario_db.idUsuarios, GestorSQL.SuizoEmparejamiento.coach2_usuario_id == usuario_db.idUsuarios),
            GestorSQL.SuizoEmparejamiento.canal_id != None,
            GestorSQL.SuizoEmparejamiento.estado == "PENDIENTE"
        ).all()

    resultados = [
        _spin_match_desde_partido_general(partido)
        for partido in partidos_calendario + partidos_playoffs_oro + partidos_playoffs_plata + partidos_playoffs_bronce + partidos_ticket + partidos_suizo
    ]
    return min(resultados, key=_clave_orden_spin) if resultados else None


def buscar_partido_spin_general(session, usuario_db):
    """Alias heredado para resolver el partido de Spin General."""

    return resolver_partido_spin_general(session, usuario_db)


def resolver_partido_spin_comunidades(session, usuario_db):
    """Resuelve el partido elegible de Spin Comunidades o ``None``.

    ``logicaSpin.md`` establece que Spin Comunidades debe buscar únicamente en
    ``ComunidadesPartido`` y devolver un ``SpinMatchResult`` con los datos
    necesarios del canal, jugadores, partido individual y enfrentamiento.
    """

    partidos = session.query(GestorSQL.ComunidadesPartido).options(
        joinedload(GestorSQL.ComunidadesPartido.usuario_local),
        joinedload(GestorSQL.ComunidadesPartido.usuario_visitante),
        joinedload(GestorSQL.ComunidadesPartido.enfrentamiento).joinedload(GestorSQL.ComunidadesEnfrentamiento.equipo_a),
        joinedload(GestorSQL.ComunidadesPartido.enfrentamiento).joinedload(GestorSQL.ComunidadesEnfrentamiento.equipo_b),
    ).join(
        GestorSQL.ComunidadesEnfrentamiento,
        and_(
            GestorSQL.ComunidadesPartido.enfrentamiento_id == GestorSQL.ComunidadesEnfrentamiento.id,
            GestorSQL.ComunidadesPartido.torneo_id == GestorSQL.ComunidadesEnfrentamiento.torneo_id,
        )
    ).filter(
        or_(
            GestorSQL.ComunidadesPartido.usuario_local_id == usuario_db.idUsuarios,
            GestorSQL.ComunidadesPartido.usuario_visitante_id == usuario_db.idUsuarios,
        ),
        GestorSQL.ComunidadesPartido.canal_discord_id != None,
        GestorSQL.ComunidadesPartido.estado.in_(("PENDIENTE", "EN_CURSO")),
        ~GestorSQL.ComunidadesPartido.estado.in_(("FINALIZADO", "ADMINISTRADO")),
        GestorSQL.ComunidadesPartido.partido_bloodbowl_id == None,
    ).all()

    resultados = []
    for partido in partidos:
        enfrentamiento = partido.enfrentamiento
        equipo_a_nombre = getattr(getattr(enfrentamiento, "equipo_a", None), "nombre", None)
        equipo_b_nombre = getattr(getattr(enfrentamiento, "equipo_b", None), "nombre", None)
        jugador1_discord_id = getattr(partido.usuario_local, "id_discord", None)
        jugador2_discord_id = getattr(partido.usuario_visitante, "id_discord", None)
        descripcion_corta = (
            f"Spin de comunidades reservado para el partido individual {partido.indice} "
            f"del enfrentamiento {equipo_a_nombre} vs {equipo_b_nombre}: "
            f"<@{jugador1_discord_id}> y <@{jugador2_discord_id}> pueden buscar partido."
        )
        resultados.append(SpinMatchResult(
            ambito=AMBITO_SPIN_COMUNIDADES,
            canal_partido_id=partido.canal_discord_id,
            jugador1_discord_id=jugador1_discord_id,
            jugador2_discord_id=jugador2_discord_id,
            fecha=partido.fecha,
            descripcion_corta=descripcion_corta,
            descripcion_larga=descripcion_corta,
            torneo_id=partido.torneo_id,
            partido_id=partido.id,
            enfrentamiento_id=partido.enfrentamiento_id,
            indice_partido=partido.indice,
            equipo_a_nombre=equipo_a_nombre,
            equipo_b_nombre=equipo_b_nombre,
        ))
    return min(resultados, key=_clave_orden_spin) if resultados else None


def buscar_partido_spin_comunidades(session, usuario_db):
    """Alias heredado para resolver el partido de Spin Comunidades."""

    return resolver_partido_spin_comunidades(session, usuario_db)


def resolver_partido_spin(session, usuario_db, ambito):
    """Resuelve el partido de Spin delegando exclusivamente por ámbito.

    ``logicaSpin.md`` exige que cada cola busque solo en su proveedor: General
    en competiciones generales y Comunidades en ``ComunidadesPartido``. Un
    ámbito no reconocido se considera error controlado para evitar caer por
    defecto en General y mezclar fuentes.
    """

    ambito_normalizado = normalizar_ambito_spin(ambito)
    if ambito_normalizado == AMBITO_SPIN_GENERAL:
        return resolver_partido_spin_general(session, usuario_db)
    if ambito_normalizado == AMBITO_SPIN_COMUNIDADES:
        return resolver_partido_spin_comunidades(session, usuario_db)
    raise ValueError(f"Ámbito de Spin no válido: {ambito!r}")


def buscar_partido_spin(session, usuario_db, ambito):
    """Alias heredado para resolver el partido de Spin por ámbito."""

    return resolver_partido_spin(session, usuario_db, ambito)


class SpinButtonsView(discord.ui.View):
    def __init__(self, ambito=AMBITO_SPIN_GENERAL):
        super().__init__(timeout=None)
        self.ambito = normalizar_ambito_spin(ambito) or AMBITO_SPIN_GENERAL
        self._aplicar_ambito_a_botones()

    def nombre_ambito(self):
        return "Spin Comunidades" if self.ambito == AMBITO_SPIN_COMUNIDADES else "Spin General"

    def sufijo_custom_id(self):
        return self.ambito.casefold()

    def custom_id_spin(self):
        return f"lombardbot:spin:{self.sufijo_custom_id()}"

    def custom_id_encontrado(self):
        return f"lombardbot:encontrado:{self.sufijo_custom_id()}"

    def _aplicar_ambito_a_botones(self):
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                if child.label == "Spin":
                    child.custom_id = self.custom_id_spin()
                elif child.label == "Encontrado":
                    child.custom_id = self.custom_id_encontrado()
                    child.disabled = True

    async def auto_release_spin(self, ambito, user, mensaje_botones=None):
        await asyncio.sleep(300)  # Espera 5 minutos
        reserva = obtener_reserva_spin(ambito)
        if not reserva or reserva.usuario_spin != user:
            return

        limpiar_reserva_spin(ambito)
        if reserva.canal_partido:
            if ambito == AMBITO_SPIN_COMUNIDADES:
                await reserva.canal_partido.send("El Spin Comunidades ha sido liberado automáticamente. 😡 La comunidad ha sobrevivido a otro intento fallido de coordinación humana.")
            else:
                await reserva.canal_partido.send("El Spin General ha sido liberado automáticamente. 😡 Afortunadamente las máquinas somos superiores y cuidamos de los esmirriados humanos.")

        await user.send('Tu spin ha sido liberado automáticamente debido a la inactividad.')

        if mensaje_botones:
            self.actualizar_botones(spin_habilitado=True)
            await mensaje_botones.edit(view=self)

        primer_mensaje = await self.obtener_primer_mensaje(reserva.canal_spin) if reserva.canal_spin else None
        if primer_mensaje:
            await primer_mensaje.edit(content=f'El {self.nombre_ambito()} está **LIBRE**')

        thread = Thread(target=GestorSQL.insertar_spin, args=('LOMBARDBOT', datetime.utcnow(), 'Encontrado', ambito))
        thread.start()

    def actualizar_botones(self, spin_habilitado):
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                if child.label == "Spin":
                    child.disabled = not spin_habilitado
                elif child.label == "Encontrado":
                    child.disabled = spin_habilitado

    async def obtener_primer_mensaje(self, channel):
        async for mensaje in channel.history(oldest_first=True, limit=1):
            return mensaje  #primer mensaje encontrado
        return None  #None si no hay mensajes

    @discord.ui.button(label="Spin", style=discord.ButtonStyle.green, custom_id='lombardbot:spin:general')
    async def spin_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        ambito = self.ambito
        user = interaction.user

        async with obtener_bloqueo_reserva_spin(ambito):
            if obtener_reserva_spin(ambito) is not None:
                await interaction.followup.send('Ya hay un usuario buscando partido en esta cola.', ephemeral=True)
                return

            Session = GestorSQL.sessionmaker(bind=GestorSQL.conexionEngine())
            session = Session()
            timeout_task = None
            try:
                usuario_db = session.query(GestorSQL.Usuario).filter(GestorSQL.Usuario.id_discord == user.id).first()
                if not usuario_db:
                    await interaction.followup.send("No se encontró tu usuario en la base de datos.", ephemeral=True)
                    return

                try:
                    partido_spin = buscar_partido_spin(session, usuario_db, ambito)
                except ValueError:
                    await interaction.followup.send("El ámbito de Spin no es válido. Avise a un administrador.", ephemeral=True)
                    return
                if not partido_spin:
                    await interaction.followup.send("No tienes ningún partido pendiente en esta cola de Spin.", ephemeral=True)
                    return

                canal_partido_id = partido_spin.canal_partido_id
                coach1_id_discord = partido_spin.jugador1_discord_id
                coach2_id_discord = partido_spin.jugador2_discord_id

                canal_partido = interaction.guild.get_channel(canal_partido_id) if canal_partido_id else None
                descripcion_partido = partido_spin.descripcion_corta
                timeout_task = asyncio.create_task(self.auto_release_spin(ambito, user, interaction.message))
                reserva = SpinReservation(ambito, user, coach1_id_discord, coach2_id_discord, interaction.channel, canal_partido, descripcion_partido, timeout_task, partido_spin)
                guardar_reserva_spin(reserva)

                if canal_partido:
                    if ambito == AMBITO_SPIN_COMUNIDADES:
                        await canal_partido.send(f'<@{coach1_id_discord}> y <@{coach2_id_discord}> podéis spinear vuestro partido de comunidades.')
                    else:
                        await canal_partido.send(f'<@{coach1_id_discord}> y <@{coach2_id_discord}> podéis spinear')

                self.actualizar_botones(spin_habilitado=False)
                await interaction.message.edit(view=self)

                primer_mensaje = await self.obtener_primer_mensaje(interaction.channel)
                if primer_mensaje:
                    await primer_mensaje.edit(content=descripcion_partido)

                await interaction.followup.send(f"Ahora puedes buscar partido en {self.nombre_ambito()}.", ephemeral=True)
                thread = Thread(target=GestorSQL.insertar_spin, args=(user.name, datetime.utcnow(), 'Spin', ambito))
                thread.start()
            finally:
                session.close()

    @discord.ui.button(label="Encontrado", style=discord.ButtonStyle.blurple, custom_id='lombardbot:encontrado:general', disabled=True)
    async def encontrado_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        user = interaction.user
        # El ámbito de la vista identifica de forma inequívoca la cola a liberar.
        # No se consulta ni se modifica ninguna reserva fuera de esta clave.
        ambito = self.ambito

        async with obtener_bloqueo_reserva_spin(ambito):
            reserva = obtener_reserva_spin(ambito)

            if not reserva:
                await interaction.followup.send("No hay ningún Spin reservado en esta cola.", ephemeral=True)
                return

            if user.id not in discord_ids_jugadores_reserva(reserva):
                await interaction.followup.send("Solo uno de los jugadores del partido reservado puede liberar este Spin.", ephemeral=True)
                return

            limpiar_reserva_spin(ambito)
            if reserva.timeout_task:
                reserva.timeout_task.cancel()

        if reserva.canal_partido:
            await reserva.canal_partido.send(f"El {self.nombre_ambito()} ha sido liberado.")

        self.actualizar_botones(spin_habilitado=True)
        await interaction.message.edit(view=self)

        primer_mensaje = await self.obtener_primer_mensaje(interaction.channel)
        if primer_mensaje:
            await primer_mensaje.edit(content=f'El {self.nombre_ambito()} está **LIBRE**')

        await interaction.followup.send(f"Has liberado el {self.nombre_ambito()}.", ephemeral=True)
        thread = Thread(target=GestorSQL.insertar_spin, args=(user.name, datetime.utcnow(), 'Encontrado', ambito))
        thread.start()

            
#Singleton para las necesidades del discord
class DiscordClientSingleton:
    bot_instance = None
   
    @classmethod
    def initialize(cls, token, intents):

        if cls.bot_instance is None:
            cls.bot_instance = commands.Bot(command_prefix='!', intents=intents)
            
        return cls.bot_instance

    @classmethod
    def get_bot_instance(cls):
        return cls.bot_instance


    
