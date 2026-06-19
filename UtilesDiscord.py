import discord
from discord.ext import commands
from discord import app_commands
from dataclasses import dataclass, replace
from typing import Optional
from threading import Thread
import threading
import logging
import Imagenes

from sqlalchemy.sql.functions import now
from sqlalchemy import BIGINT, create_engine, Column, Integer, String, ForeignKey, false, true,text
from sqlalchemy import and_, or_ ,null
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.orm import aliased, joinedload
from sqlalchemy.sql import case,func

import GestorSQL
from ComunidadesConstantes import (
    PARTIDO_ADMINISTRADO,
    PARTIDO_EN_CURSO,
    PARTIDO_FINALIZADO,
    PARTIDO_PENDIENTE,
)
from SpinConstantes import (
    AMBITO_SPIN_COMUNIDADES,
    AMBITO_SPIN_GENERAL,
    TIPO_SPIN,
    TIPO_SPIN_AUTO_RELEASE,
    TIPO_SPIN_ADMIN_RELEASE,
    TIPO_SPIN_ENCONTRADO,
    CANAL_SPIN_COMUNIDADES_ID,
    CANAL_SPIN_GENERAL_ID,
    mensaje_canal_partido_liberacion_administrativa,
    mensaje_canal_partido_liberacion_automatica,
    mensaje_canal_partido_liberacion_manual,
    mensaje_spin_libre,
    normalizar_ambito_spin,
)

import asyncio
from datetime import datetime


LOGGER = logging.getLogger(__name__)


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
    descripcion_corta: Optional[str] = None
    descripcion_larga: Optional[str] = None
    torneo_id: Optional[int] = None
    partido_id: Optional[int] = None
    ronda_id: Optional[int] = None
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
    timeout_task: Optional[asyncio.Task]
    partido: SpinMatchResult


@dataclass(frozen=True)
class SpinEstadoTransitorio:
    """Estado interno no reservable mientras una cola se está liberando."""

    ambito: str
    estado: str = "LIBERANDO"


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


def reserva_spin_activa(reserva):
    if isinstance(reserva, SpinReservation):
        return True
    if reserva is None or isinstance(reserva, SpinEstadoTransitorio):
        return False
    return (
        bool(discord_ids_jugadores_reserva(reserva))
        or hasattr(reserva, "canal_spin")
        or hasattr(reserva, "canal_partido")
    )


def guardar_reserva_spin(reserva):
    reservas_spin[reserva.ambito] = reserva


def marcar_liberando_spin(ambito):
    reservas_spin[ambito] = SpinEstadoTransitorio(ambito)


def limpiar_reserva_spin(ambito):
    reserva = reservas_spin.get(ambito)
    reservas_spin[ambito] = None
    return reserva


async def tomar_reserva_para_liberar_spin(ambito, reserva_esperada=None):
    """Marca una reserva como ``LIBERANDO`` de forma idempotente.

    Devuelve la reserva activa que debe liberar el llamador, o ``None`` si la
    cola ya estaba libre, ya estaba en proceso de liberación, o la reserva
    activa no coincide con ``reserva_esperada``. No toca otras colas porque el
    bloqueo y el estado están indexados por ámbito.
    """

    async with obtener_bloqueo_reserva_spin(ambito):
        reserva = obtener_reserva_spin(ambito)
        if not reserva_spin_activa(reserva):
            return None
        if reserva_esperada is not None and reserva is not reserva_esperada:
            return None
        marcar_liberando_spin(ambito)
        if reserva.timeout_task and reserva.timeout_task is not asyncio.current_task():
            reserva.timeout_task.cancel()
        return reserva


async def finalizar_liberacion_spin(ambito):
    """Deja libre una cola tras una liberación ya tomada."""

    async with obtener_bloqueo_reserva_spin(ambito):
        limpiar_reserva_spin(ambito)


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


def usuario_tiene_rol_administrativo_spin(usuario):
    """Indica si un usuario debe ser dirigido al comando administrativo.

    Esto no autoriza el botón `Encontrado`: solo permite mostrar una respuesta
    más útil a administradores/comisarios que no sean jugadores del partido.
    """

    permisos = getattr(usuario, "guild_permissions", None)
    if getattr(permisos, "administrator", False):
        return True

    roles_administrativos = {"Comisario", "Administrador", "Moderadores"}
    return any(
        getattr(rol, "name", "") in roles_administrativos
        for rol in getattr(usuario, "roles", [])
    )


def mensaje_encontrado_no_autorizado(usuario):
    if usuario_tiene_rol_administrativo_spin(usuario):
        return (
            "Solo uno de los jugadores del partido reservado puede liberar este Spin. "
            "Si necesitas liberarlo como administración, usa `/liberarspin`."
        )
    return "Solo uno de los jugadores del partido reservado puede liberar este Spin."


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
                


def _valor_orden_determinista_spin(valor):
    """Normaliza identificadores opcionales para desempatar de forma estable."""

    return valor if valor is not None else 0


def _clave_orden_spin(partido: SpinMatchResult):
    """Ordena partidos según el criterio común de ``logicaSpin.md``.

    Primero van los partidos con fecha, ordenados por cercanía al momento
    actual. Los partidos sin fecha quedan detrás y todos los empates se
    resuelven por identificadores estables: torneo, ronda, enfrentamiento,
    índice de partido e ID interno.
    """

    ahora = datetime.utcnow()
    tiene_fecha = partido.fecha is not None
    distancia_fecha = abs((partido.fecha - ahora).total_seconds()) if tiene_fecha else float("inf")
    return (
        0 if tiene_fecha else 1,
        distancia_fecha,
        _valor_orden_determinista_spin(partido.torneo_id),
        _valor_orden_determinista_spin(partido.ronda_id),
        _valor_orden_determinista_spin(partido.enfrentamiento_id),
        _valor_orden_determinista_spin(partido.indice_partido),
        _valor_orden_determinista_spin(partido.partido_id),
    )


def mensaje_spin_reservado(partido: SpinMatchResult):
    """Construye el mensaje principal reservado desde ``SpinMatchResult``.

    ``logicaSpin.md`` define el texto público de reserva por ámbito. Para
    Comunidades se usa el texto completo solo si el resultado trae partido
    individual y ambos equipos; si falta algún dato descriptivo, se degrada a
    un mensaje seguro sin mostrar ``None``.
    """

    menciones = f"<@{partido.jugador1_discord_id}> y <@{partido.jugador2_discord_id}>"
    if partido.ambito == AMBITO_SPIN_COMUNIDADES:
        datos_descriptivos_completos = (
            partido.indice_partido is not None
            and bool(partido.equipo_a_nombre)
            and bool(partido.equipo_b_nombre)
        )
        if datos_descriptivos_completos:
            return (
                f"Spin de comunidades reservado para el partido individual {partido.indice_partido} "
                f"del enfrentamiento {partido.equipo_a_nombre} vs {partido.equipo_b_nombre}: "
                f"{menciones} pueden buscar partido."
            )

        LOGGER.warning(
            "Spin Comunidades reservado con datos descriptivos incompletos",
            extra={
                "spin_torneo_id": partido.torneo_id,
                "spin_partido_id": partido.partido_id,
                "spin_enfrentamiento_id": partido.enfrentamiento_id,
                "spin_indice_partido": partido.indice_partido,
                "spin_equipo_a_nombre": partido.equipo_a_nombre,
                "spin_equipo_b_nombre": partido.equipo_b_nombre,
            },
        )
        return f"Spin Comunidades reservado: {menciones} pueden buscar partido."
    return f"Spin General reservado: {menciones} pueden buscar partido."


def mensaje_canal_partido_spin_reservado(partido: SpinMatchResult):
    """Construye el aviso en el canal del partido al reservar Spin.

    ``logicaSpin.md`` fija textos distintos para General y Comunidades. Para
    Comunidades se añade el contexto de partido individual y enfrentamiento
    solo cuando están disponibles todos los datos necesarios.
    """

    menciones = f"<@{partido.jugador1_discord_id}> y <@{partido.jugador2_discord_id}>"
    if partido.ambito == AMBITO_SPIN_COMUNIDADES:
        mensaje = f"{menciones}, podéis spinear vuestro partido de comunidades"
        if partido.indice_partido and partido.equipo_a_nombre and partido.equipo_b_nombre:
            mensaje += (
                f": partido individual {partido.indice_partido} "
                f"del enfrentamiento {partido.equipo_a_nombre} vs {partido.equipo_b_nombre}"
            )
        return f"{mensaje}."
    return f"{menciones}, podéis spinear."


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

    resultado = SpinMatchResult(
        ambito=AMBITO_SPIN_GENERAL,
        canal_partido_id=canal_partido_id,
        jugador1_discord_id=jugador1_discord_id,
        jugador2_discord_id=jugador2_discord_id,
        fecha=fecha,
        torneo_id=getattr(partido, "torneo_id", None),
        partido_id=partido_id,
        ronda_id=getattr(partido, "ronda_id", None) or getattr(partido, "jornada", None),
        enfrentamiento_id=getattr(partido, "id", None),
        indice_partido=getattr(partido, "mesa_numero", None),
    )
    descripcion = mensaje_spin_reservado(resultado)
    return replace(resultado, descripcion_corta=descripcion, descripcion_larga=descripcion)


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
        GestorSQL.ComunidadesPartido.estado.in_(
            (PARTIDO_PENDIENTE, PARTIDO_EN_CURSO)
        ),
        ~GestorSQL.ComunidadesPartido.estado.in_(
            (PARTIDO_FINALIZADO, PARTIDO_ADMINISTRADO)
        ),
        GestorSQL.ComunidadesPartido.partido_bloodbowl_id.is_(None),
    ).all()

    resultados = []
    for partido in partidos:
        enfrentamiento = partido.enfrentamiento
        equipo_a_nombre = getattr(getattr(enfrentamiento, "equipo_a", None), "nombre", None)
        equipo_b_nombre = getattr(getattr(enfrentamiento, "equipo_b", None), "nombre", None)
        jugador1_discord_id = getattr(partido.usuario_local, "id_discord", None)
        jugador2_discord_id = getattr(partido.usuario_visitante, "id_discord", None)
        resultado = SpinMatchResult(
            ambito=AMBITO_SPIN_COMUNIDADES,
            canal_partido_id=partido.canal_discord_id,
            jugador1_discord_id=jugador1_discord_id,
            jugador2_discord_id=jugador2_discord_id,
            fecha=partido.fecha,
            torneo_id=partido.torneo_id,
            partido_id=partido.id,
            ronda_id=getattr(enfrentamiento, "ronda_id", None),
            enfrentamiento_id=partido.enfrentamiento_id,
            indice_partido=partido.indice,
            equipo_a_nombre=equipo_a_nombre,
            equipo_b_nombre=equipo_b_nombre,
        )
        descripcion = mensaje_spin_reservado(resultado)
        resultados.append(replace(resultado, descripcion_corta=descripcion, descripcion_larga=descripcion))
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


async def obtener_primer_mensaje_canal(channel):
    """Devuelve el primer mensaje del canal de Spin, o ``None`` si no existe.

    La decisión operativa de ``logicaSpin.md`` es no persistir ni usar como
    fuente de verdad el ID del mensaje de Spin: el mensaje editable es siempre
    el primer mensaje visible del canal.
    """

    if channel is None:
        return None

    async for mensaje in channel.history(oldest_first=True, limit=1):
        return mensaje
    return None


async def editar_primer_mensaje_spin(channel, *, content=None, view=None):
    """Edita el primer mensaje del canal de Spin sin depender de IDs guardados.

    Lanza ``LookupError`` si no hay mensaje principal para que el flujo que
    reserva/libera pueda decidir cómo degradar sin dejar estado interno
    atascado.
    """

    primer_mensaje = await obtener_primer_mensaje_canal(channel)
    if primer_mensaje is None:
        raise LookupError("No se encontró el primer mensaje del canal de Spin")

    kwargs = {}
    if content is not None:
        kwargs["content"] = content
    if view is not None:
        kwargs["view"] = view
    if kwargs:
        await primer_mensaje.edit(**kwargs)
    return primer_mensaje


async def liberar_reserva_spin_administrativa(ambito, usuario_admin):
    """Libera explícitamente una cola de Spin por acción administrativa.

    ``logicaSpin.md`` exige que administradores/comisarios usen un comando
    específico en vez del botón `Encontrado`. La operación libera primero el
    estado interno y después intenta actualizar Discord, para no dejar la cola
    bloqueada si falla una acción secundaria.
    """

    ambito_normalizado = normalizar_ambito_spin(ambito)
    if not ambito_normalizado:
        raise ValueError(f"Ámbito de Spin no válido: {ambito!r}")

    reserva = await tomar_reserva_para_liberar_spin(ambito_normalizado)
    if not reserva:
        return False

    await finalizar_liberacion_spin(ambito_normalizado)
    nombre_ambito = "Spin Comunidades" if ambito_normalizado == AMBITO_SPIN_COMUNIDADES else "Spin General"

    if reserva.canal_partido:
        try:
            await reserva.canal_partido.send(mensaje_canal_partido_liberacion_administrativa(ambito_normalizado))
        except Exception as exc:
            print(f"No se pudo enviar el mensaje de liberación administrativa de {nombre_ambito}: {exc}")

    try:
        vista = SpinButtonsView(ambito_normalizado)
        vista.actualizar_botones(spin_habilitado=True)
        await editar_primer_mensaje_spin(
            reserva.canal_spin,
            content=mensaje_spin_libre(ambito_normalizado),
            view=vista,
        )
    except Exception as exc:
        print(f"No se pudo editar el primer mensaje de {nombre_ambito} tras liberación administrativa: {exc}")

    nombre_usuario = getattr(usuario_admin, "name", str(usuario_admin))
    usuario_discord_id = getattr(usuario_admin, "id", None)
    thread = Thread(
        target=GestorSQL.insertar_spin,
        args=(nombre_usuario, datetime.utcnow(), TIPO_SPIN_ADMIN_RELEASE, ambito_normalizado, usuario_discord_id),
    )
    thread.start()
    return True


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

    async def auto_release_spin(self, reserva_esperada, mensaje_botones=None):
        """Libera por timeout únicamente la reserva concreta que creó la tarea.

        Cada cola mantiene su propia tarea de timeout. Tras esperar los 5
        minutos exigidos por ``logicaSpin.md``, la tarea comprueba que la
        reserva activa del ámbito sigue siendo exactamente la misma instancia.
        Así una tarea antigua no puede liberar una reserva posterior del mismo
        ámbito ni tocar la otra cola.
        """

        await asyncio.sleep(300)  # Espera 5 minutos
        ambito = reserva_esperada.ambito

        reserva = await tomar_reserva_para_liberar_spin(ambito, reserva_esperada=reserva_esperada)
        if not reserva:
            return

        await finalizar_liberacion_spin(ambito)
        nombre_ambito = self.nombre_ambito()
        if reserva.canal_partido:
            try:
                await reserva.canal_partido.send(mensaje_canal_partido_liberacion_automatica(ambito))
            except Exception as exc:
                print(f"No se pudo enviar el mensaje de timeout de {nombre_ambito} al canal del partido: {exc}")

        try:
            await reserva.usuario_spin.send('Tu spin ha sido liberado automáticamente debido a la inactividad.')
        except Exception as exc:
            print(f"No se pudo enviar DM de timeout de {nombre_ambito}: {exc}")

        try:
            self.actualizar_botones(spin_habilitado=True)
            await editar_primer_mensaje_spin(
                reserva.canal_spin,
                content=mensaje_spin_libre(ambito),
                view=self,
            )
        except Exception as exc:
            print(f"No se pudo editar el primer mensaje de {nombre_ambito} tras timeout: {exc}")

        thread = Thread(target=GestorSQL.insertar_spin, args=('LOMBARDBOT', datetime.utcnow(), TIPO_SPIN_AUTO_RELEASE, ambito))
        thread.start()

    def actualizar_botones(self, spin_habilitado):
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                if child.label == "Spin":
                    child.disabled = not spin_habilitado
                elif child.label == "Encontrado":
                    child.disabled = spin_habilitado

    async def obtener_primer_mensaje(self, channel):
        return await obtener_primer_mensaje_canal(channel)

    @discord.ui.button(label="Spin", style=discord.ButtonStyle.green, custom_id='lombardbot:spin:general')
    async def spin_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        ambito = self.ambito
        user = interaction.user

        # Primera comprobación rápida por ámbito. No mantenemos el bloqueo
        # durante la búsqueda SQL para no retener la cola mientras hacemos I/O;
        # por eso se repite la comprobación justo antes de crear la reserva.
        async with obtener_bloqueo_reserva_spin(ambito):
            if obtener_reserva_spin(ambito) is not None:
                await interaction.followup.send('Ya hay un usuario buscando partido en esta cola.', ephemeral=True)
                return

        Session = GestorSQL.sessionmaker(bind=GestorSQL.conexionEngine())
        session = Session()
        try:
            usuario_db = session.query(GestorSQL.Usuario).filter(GestorSQL.Usuario.id_discord == user.id).first()
            if not usuario_db:
                partido_spin = None
                mensaje_error = "No se encontró tu usuario en la base de datos."
            else:
                try:
                    partido_spin = buscar_partido_spin(session, usuario_db, ambito)
                    mensaje_error = None if partido_spin else "No tienes ningún partido pendiente en esta cola de Spin."
                except ValueError:
                    partido_spin = None
                    mensaje_error = "El ámbito de Spin no es válido. Avise a un administrador."
        finally:
            session.close()

        if mensaje_error:
            await interaction.followup.send(mensaje_error, ephemeral=True)
            return

        canal_partido_id = partido_spin.canal_partido_id
        coach1_id_discord = partido_spin.jugador1_discord_id
        coach2_id_discord = partido_spin.jugador2_discord_id
        canal_partido = interaction.guild.get_channel(canal_partido_id) if canal_partido_id else None
        descripcion_partido = partido_spin.descripcion_corta
        reserva = SpinReservation(
            ambito,
            user,
            coach1_id_discord,
            coach2_id_discord,
            interaction.channel,
            canal_partido,
            descripcion_partido,
            None,
            partido_spin,
        )

        async with obtener_bloqueo_reserva_spin(ambito):
            # Revalidación requerida antes de crear la reserva: otra interacción
            # simultánea pudo reservar o iniciar LIBERANDO mientras buscábamos.
            if obtener_reserva_spin(ambito) is not None:
                await interaction.followup.send('Ya hay un usuario buscando partido en esta cola.', ephemeral=True)
                return
            timeout_task = asyncio.create_task(self.auto_release_spin(reserva))
            reserva.timeout_task = timeout_task
            guardar_reserva_spin(reserva)

        self.actualizar_botones(spin_habilitado=False)
        try:
            await editar_primer_mensaje_spin(
                interaction.channel,
                content=descripcion_partido,
                view=self,
            )
        except Exception as exc:
            async with obtener_bloqueo_reserva_spin(ambito):
                if obtener_reserva_spin(ambito) is reserva:
                    limpiar_reserva_spin(ambito)
            if reserva.timeout_task:
                reserva.timeout_task.cancel()
            self.actualizar_botones(spin_habilitado=True)
            await interaction.followup.send(
                "No se pudo localizar o editar el mensaje principal de Spin. "
                "La reserva interna ha quedado liberada; recrea el mensaje con "
                f"`!AgregarMensajeSpin {ambito.title()}` si es necesario.",
                ephemeral=True,
            )
            print(f"No se pudo reservar {self.nombre_ambito()} al editar el primer mensaje: {exc}")
            return

        if canal_partido:
            await canal_partido.send(mensaje_canal_partido_spin_reservado(partido_spin))

        await interaction.followup.send(f"Ahora puedes buscar partido en {self.nombre_ambito()}.", ephemeral=True)
        thread = Thread(target=GestorSQL.insertar_spin, args=(user.name, datetime.utcnow(), TIPO_SPIN, ambito, user.id))
        thread.start()

    @discord.ui.button(label="Encontrado", style=discord.ButtonStyle.blurple, custom_id='lombardbot:encontrado:general', disabled=True)
    async def encontrado_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        user = interaction.user
        ambito = self.ambito

        async with obtener_bloqueo_reserva_spin(ambito):
            reserva = obtener_reserva_spin(ambito)
            if not reserva_spin_activa(reserva):
                await interaction.followup.send("No hay ningún Spin reservado en esta cola.", ephemeral=True)
                return
            if user.id not in discord_ids_jugadores_reserva(reserva):
                await interaction.followup.send(mensaje_encontrado_no_autorizado(user), ephemeral=True)
                return

        reserva = await tomar_reserva_para_liberar_spin(ambito, reserva_esperada=reserva)
        if not reserva:
            await interaction.followup.send("No hay ningún Spin reservado en esta cola.", ephemeral=True)
            return

        await finalizar_liberacion_spin(ambito)
        if reserva.canal_partido:
            try:
                await reserva.canal_partido.send(mensaje_canal_partido_liberacion_manual(ambito))
            except Exception as exc:
                print(f"No se pudo enviar el mensaje de liberación de {self.nombre_ambito()}: {exc}")

        self.actualizar_botones(spin_habilitado=True)
        try:
            await editar_primer_mensaje_spin(
                reserva.canal_spin,
                content=mensaje_spin_libre(ambito),
                view=self,
            )
        except Exception as exc:
            print(f"No se pudo editar el primer mensaje de {self.nombre_ambito()} al liberar: {exc}")

        await interaction.followup.send(f"Has liberado el {self.nombre_ambito()}.", ephemeral=True)
        thread = Thread(target=GestorSQL.insertar_spin, args=(user.name, datetime.utcnow(), TIPO_SPIN_ENCONTRADO, ambito, user.id))
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


    
