import os
import asyncio
from pickle import LONG
from re import A
import re
from typing import Optional

from discord.ext.commands.parameters import Author

if os.name == 'nt':  # Solo si es Windows
    from asyncio.windows_events import NULL
    
import discord
from discord.ext import commands
from discord.ext import tasks
from discord import File
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo
import tzlocal
import os
from wcwidth import wcswidth
from dotenv import load_dotenv
import requests
import asyncio
import APIBbowl
import UtilesDiscord
import GestorSQL
import Encuesta
from UtilesDiscord import DiscordClientSingleton
import GestionExcel
import aiohttp
import Imagenes
import threading
import random
import math
from sqlalchemy import BIGINT, create_engine, Column, Integer, String, ForeignKey, false, true,text
from sqlalchemy import and_, or_ 
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.orm import aliased
from sqlalchemy.sql import case,func
import inspect
import mysql.connector
import Inscripcion
import Reformas
from SuizoCore import (
    calcular_standings,
    generar_pairings_backtracking,
    procesar_cierre_ronda_si_corresponde,
)


# Cargar las variables de entorno desde .env
load_dotenv()

# Obtener la API key
discord_bot_token = os.getenv('DISCORD_BOT_TOKEN')
bbowl_API_token = os.getenv('APIBBOWL')


# Configurar intents
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True
intents.members = True
intents.reactions = True

# Crear e inicializar el bot
bot = DiscordClientSingleton.initialize(discord_bot_token, intents)

#Lista de usuarios con permisos
maestros = ["208239645014753280","681577610010296372","1297346191130103859"]

def es_comisario(ctx):
    return any(getattr(rol, "name", "") == "Comisario" for rol in getattr(ctx.author, "roles", []))

# Lista de IDs de canales permitidos
canales_permitidos = ['457740100097540106']

# Lista de comandos a los que el bot reaccionará
comandos = ['eco', 'otroComando']

# IDs para la actualización programada de peticiones de razas
PETICIONES_RAZAS_CANAL_ID = 1280102673059680316
PETICIONES_RAZAS_HEADER_MESSAGE_ID = 1450467375794094083
PETICIONES_RAZAS_TABLA_MESSAGE_ID = 1450467376763240660


@tasks.loop(minutes=60)
async def programador_tareas():
    try:
        ahora = datetime.now()
        dia_semana = ahora.strftime("%A")  # Día de la semana en inglés
        hora_actual = ahora.strftime("%H")  # Hora actual (sin minutos)

        # Verificar si hay tareas programadas para el día y la hora actuales
        if dia_semana in tareas_programadas and hora_actual in tareas_programadas[dia_semana]:
            tareas = tareas_programadas[dia_semana][hora_actual]
            for funcion, args in tareas:
                if callable(funcion):  # Verificar que sea una función ejecutable
                    await funcion(**args)

        print(f"Tareas ejecutadas para {dia_semana} a las {hora_actual}:00")

    except Exception as e:
        print(f"Error en el programador de tareas: {str(e)}")
        
@programador_tareas.before_loop
async def before_programador_tareas():
    # Sincroniza el loop para que inicie en el próximo minuto exacto
    await bot.wait_until_ready()
    ahora = datetime.now()
    proxima_hora = (ahora + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    tiempo_espera = (proxima_hora - ahora).total_seconds()
    print(f"Esperando {int(tiempo_espera)} segundos para sincronizar el programador de tareas...")
    await asyncio.sleep(tiempo_espera)
    

async def reloj_de_cuco():
    try:
        now = datetime.now()
        hora_actual = now.strftime("%H") 
        dia_semana = now.strftime("%A")  
        
        mensaje = f"⏰ ¡Cucú! Son las {hora_actual} horas del {dia_semana} 📅."
        await UtilesDiscord.mensaje_administradores(mensaje)

    except Exception as e:
        print(f"Error en el reloj de cuco: {str(e)}")

@bot.event
async def on_ready():
    bot.add_view(UtilesDiscord.SpinButtonsView())
    await bot.tree.sync()
    #await GestionExcel.ActualizarExcels()
    if not programador_tareas.is_running():
        programador_tareas.start()
        
    print(f'{bot.user.name} se ha conectado a Discord!')
    print(f'{bot.user.name} me siento... más fuerte, más... consiciente')


@bot.event
async def on_message(message):
    # Evitar que el bot responda a sus propios mensajes
    if message.author == bot.user:
        return
    print(message.content)
    
    mee6_id = 1297346191130103859
    canal_permitido_id = 457740100097540106 

    # # Solo procesar si el autor es MEE6 y el mensaje está en el canal permitido
    # if message.author.id == mee6_id and message.channel.id == canal_permitido_id:
        
    #     if message.content.startswith("!proximos_eventos"):
    #         comandos = bot.tree.get_command("proximos_eventos")
    #         if comandos is not None:
    #             partes = message.content.split()
    #             if len(partes) > 1:
    #                 canal_destino_id = int(partes[1])  

    #                 guild = message.guild
    #                 member = guild.get_member(message.author.id) if guild else None

    #                 # Crear una interacción simulada
    #                 class FakeInteraction:
    #                     def __init__(self, user, guild, channel):
    #                         self.user = user
    #                         self.guild = guild
    #                         self.channel = channel
    #                         self.author = message.author

    #                     @property
    #                     def client(self):
    #                         return bot

    #                     @property
    #                     def guild_id(self):
    #                         return self.guild.id if self.guild else None

    #                     async def response(self, *args, **kwargs):
    #                         pass

    #                 # Crear la interacción simulada
    #                 fake_interaction = FakeInteraction(member, guild, message.channel)

    #                 # Invocar el comando con el argumento
    #                 await comandos.callback(fake_interaction, canal_destino_id=canal_destino_id)
    #     elif message.content.startswith('!'):
    #         ctx = await bot.get_context(message)
    #         await bot.invoke(ctx)
    #     return
    
    await bot.process_commands(message)

@bot.command(name='IPikoleto')
async def get_public_ip(ctx):
    try:
        if str(ctx.author.id) not in maestros:
            await ctx.send("No tienes permiso para usar este comando, se ha avisado a las autoridades pertinentes, la cyberpolicía está en camino.")
            await UtilesDiscord.mensaje_administradores(f"El putísimo retrasado de {ctx.author.name} me ha pedido la IP 😡.")
            return

        try:
            response = requests.get('https://api.ipify.org?format=json', timeout=5)  # Timeout de 5 segundos
            response.raise_for_status()  # Verifica si la respuesta tiene un código de estado HTTP de error
            data = response.json()
            public_ip = data.get('ip')

            if not public_ip:
                raise ValueError("No se pudo obtener la IP del JSON de respuesta.")

            # Enviar la IP pública como respuesta
            await ctx.author.send(f'La IP pública del bot es: {public_ip}')
            await UtilesDiscord.mensaje_administradores(f"Se envió la IP al usuario {ctx.author.name}.")
        except (requests.exceptions.RequestException, ValueError) as e:
            await ctx.send("No se pudo obtener la IP pública debido a un error con el servicio. Por favor, intenta de nuevo más tarde.")
            await UtilesDiscord.mensaje_administradores(f"Error al intentar obtener la IP: {e}")

    except Exception as e:
        await ctx.send(f'Ocurrió un error inesperado al ejecutar el comando. Error: {e}')

@bot.command()
@commands.has_permissions(manage_messages=True)
@commands.has_any_role('Moderadores', 'Administrador', 'Comisario')
async def clear(ctx, num: int):
    if str(ctx.author.id) not in maestros:
        await ctx.send("No tienes permiso para usar este comando.")
        return

    if num < 1:  # Verifica que el número sea positivo.
        await ctx.send("Por favor, especifica un número de mensajes válido para borrar.")
        return

    # Borrar mensajes. Esto no borrará mensajes con más de 14 días de antigüedad.
    deleted = await ctx.channel.purge(limit=num + 1)  # +1 para contar el comando mismo.

    await ctx.send(f'{len(deleted) - 1} mensajes han sido borrados.', delete_after=5)  # Mensaje de confirmación que se auto-elimina.

@bot.command()
@commands.has_any_role('Moderadores', 'Administrador', 'Comisario')
async def updateMissingBbowlIds(ctx):
    Session = sessionmaker(bind=GestorSQL.conexionEngine())
    session = Session()
    
    # Consultar usuarios cuyo id_bloodbowl esté vacío
    usuarios_para_actualizar = session.query(GestorSQL.Usuario).filter(GestorSQL.Usuario.id_bloodbowl == None, GestorSQL.Usuario.nombre_bloodbowl != None).all()

    for usuario in usuarios_para_actualizar:
        try:
            # Llamar a la función obtener_entrenadores
            player_data = APIBbowl.obtener_entrenadores(bbowl_API_token, usuario.nombre_bloodbowl)
            if 'id' in player_data:
                # Actualizar id_bloodbowl del usuario
                usuario.id_bloodbowl = player_data['id']
                session.commit()
            else:
                await UtilesDiscord.mensaje_administradores(f"No se encontró ID para el usuario {usuario.nombre_discord}")
        except Exception as e:
            await UtilesDiscord.mensaje_administradores(f"Error al actualizar el id_bloodbowl para {usuario.nombre_discord}: {e}")
            session.rollback()  # En caso de error, deshacer cambios

    session.close()
    
def buscarNombreAMostrar(nombreBB):
    Session = sessionmaker(bind=GestorSQL.conexionEngine())
    session = Session()   
    try:
        # Buscar usuario por nombre_bloodbowl
        usuario = session.query(GestorSQL.Usuario).filter_by(nombre_bloodbowl=nombreBB).first()       
        if usuario:
            # Si encontramos un usuario y el campo nombreAmostrar no está vacío, devolverlo
            if usuario.nombreAmostrar and usuario.nombreAmostrar.strip():
                return usuario.nombreAmostrar
    except Exception as e:
        print(f"Error al buscar el nombre a mostrar para {nombreBB}: {e}")
    finally:
        session.close()
    
    # Si no se encontró el usuario, o el campo nombreAmostrar está vacío, devolver nombreBB
    return nombreBB


#comando de Prueba para publicar en hilos
@bot.command()
@commands.has_any_role('Moderadores', 'Administrador', 'Comisario')
#async def Prueba(ctx,titulo,*,mensaje):
async def Prueba(ctx):
    #await UtilesDiscord.publicar(ctx,'Jornada ' + titulo + '!',mensaje)
    await UtilesDiscord.mensaje_administradores('Prueba')
    return


#Función para actualizar la jornada de un coach
# @commands.has_any_role('Moderadores', 'Administrador', 'Comisario')
# async def actualizar_o_agregar_coach(sheet, coach):
#     valores = sheet.get_all_records()
#     fila_actual = 2
#     encontrado = False
#     for row in valores:
#         if row["Id"] == coach['idcoach']:
#             # Actualizar jornada
#             nueva_jornada = row["jornada"] + 1
#             sheet.update_cell(fila_actual, 3, nueva_jornada)
#             encontrado = True
#             break
#         fila_actual += 1  

#     if not encontrado:
#         # Agregar nuevo coach
#         sheet.append_row([coach['coachname'], coach['idcoach'], 1])
    
#     await asyncio.sleep(10)

async def actualizar_clasificacion(ctx,session, obtener_partidos_func, tabla_calendario, categoria_id, todos=0):
    matches = obtener_partidos_func()
    if not matches:
        return "No se encontraron partidos."

    for match in matches:
        partido_existente = session.query(GestorSQL.Partidos).filter_by(idPartidoBbowl=match['uuid']).first()
        if partido_existente:
            if todos == 0:
                break
            else:
                partido_existente = None
                continue

        coach_ids = [match['coaches'][0]['idcoach'], match['coaches'][1]['idcoach']]
        usuarios = session.query(GestorSQL.Usuario).filter(GestorSQL.Usuario.id_bloodbowl.in_(coach_ids)).all()

        
        if len(usuarios) != 2:
            # Informar a administradores de la inconsistencia
            found_ids = [u.id_bloodbowl for u in usuarios]
            missing_ids = [cid for cid in coach_ids if cid not in found_ids]
            message = f"Error al procesar partido {match['uuid']}: "
            if usuarios:
                found_users = ", ".join(f"{u.nombre_discord} (id_bloodbowl={u.id_bloodbowl})" for u in usuarios)
                message += f"Se encontraron usuarios: {found_users}. "
            else:
                message += "No se encontró ningún usuario. "
            message += "Faltan id_bloodbowl de los coaches: " + ", ".join(str(mid) for mid in missing_ids) + ". "
            team_names = [t.get('teamname', 'Desconocido') for t in match.get('teams', [])]
            if team_names:
                message += "Equipos en el partido: " + ", ".join(team_names) + "."
            await UtilesDiscord.mensaje_administradores(message)
            continue

        calendario_registro = session.query(tabla_calendario).filter(
            and_(
                tabla_calendario.coach1.in_([usuarios[0].idUsuarios, usuarios[1].idUsuarios]),
                tabla_calendario.coach2.in_([usuarios[0].idUsuarios, usuarios[1].idUsuarios]),
            ),
            tabla_calendario.partidos_idPartidos == None
        ).order_by(tabla_calendario.jornada).first()

        if not calendario_registro:
            await UtilesDiscord.mensaje_administradores(f"No se encontró partido para los usuarios {coach_ids}  id: {match['uuid']}")
            continue

        local_index = 0 if calendario_registro.usuario_coach1.id_bloodbowl == match['coaches'][0]['idcoach'] else 1
        visitante_index = 1 - local_index

        total_muertes_coach1 = match['teams'][local_index]['sustaineddead']
        total_lesiones_coach1 = match['teams'][visitante_index]['inflictedcasualties']
        total_lesiones_coach1 -= total_muertes_coach1

        total_muertes_coach2 = match['teams'][visitante_index]['sustaineddead']
        total_lesiones_coach2 = match['teams'][local_index]['inflictedcasualties']
        total_lesiones_coach2 -= total_muertes_coach2

        nuevo_partido = GestorSQL.Partidos(
            resultado1=match['teams'][local_index]['score'],
            resultado2=match['teams'][visitante_index]['score'],
            lesiones1=total_lesiones_coach1,
            lesiones2=total_lesiones_coach2,
            muertes1=total_muertes_coach1,
            muertes2=total_muertes_coach2,
            idPartidoBbowl=match['uuid'],
            pases1=match['teams'][local_index]['inflictedpasses'],
            pases2=match['teams'][visitante_index]['inflictedpasses'],
            catches1=match['teams'][local_index]['inflictedcatches'],
            catches2=match['teams'][visitante_index]['inflictedcatches'],
            interceptions1=match['teams'][local_index]['inflictedinterceptions'],
            interceptions2=match['teams'][visitante_index]['inflictedinterceptions'],
            ko1=match['teams'][local_index]['inflictedko'],
            ko2=match['teams'][visitante_index]['inflictedko'],
            push1=match['teams'][local_index]['inflictedpushouts'],
            push2=match['teams'][visitante_index]['inflictedpushouts'],
            mRun1=match['teams'][local_index]['inflictedmetersrunning'],
            mRun2=match['teams'][visitante_index]['inflictedmetersrunning'],
            mPass1=match['teams'][local_index]['inflictedmetersrunning'],
            mPass2=match['teams'][visitante_index]['inflictedmetersrunning'],
            logo1=match['teams'][local_index]['teamlogo'],
            logo2=match['teams'][visitante_index]['teamlogo'],
            nombreEquipo1=match['teams'][local_index]['teamname'],
            nombreEquipo2=match['teams'][visitante_index]['teamname']
        )

        session.add(nuevo_partido)
        session.commit()



        calendario_registro.partidos_idPartidos = nuevo_partido.idPartidos
        session.commit()
        
        await UtilesDiscord.publicar(ctx,'Jornada ' + str(calendario_registro.jornada) + '!',id_foro=categoria_id,idPartido=nuevo_partido.idPartidos)
        

        for usuario in usuarios:
            usuario.jornada_actual += 1
        session.commit()

        try:
            await UtilesDiscord.gestionar_canal_discord(ctx, "eliminar", canal_id=calendario_registro.canalAsociado)
        except Exception as e:
            await UtilesDiscord.mensaje_administradores(f"No se pudo borrar el canal con id {calendario_registro.canalAsociado}")

        for usuario in usuarios:
            rival = None
            calendario = session.query(tabla_calendario)\
                .filter(or_(tabla_calendario.coach1 == usuario.idUsuarios, tabla_calendario.coach2 == usuario.idUsuarios))\
                .filter(tabla_calendario.jornada == usuario.jornada_actual)\
                .first()
            if calendario:
                rival_id = calendario.coach1 if calendario.coach1 != usuario.idUsuarios else calendario.coach2
                rival = session.query(GestorSQL.Usuario).filter_by(idUsuarios=rival_id).first()

                preferencia_usuario = session.query(GestorSQL.PreferenciasFecha).filter_by(idUsuarios=usuario.idUsuarios).first()
                preferencia_rival = session.query(GestorSQL.PreferenciasFecha).filter_by(idUsuarios=rival_id).first()

                preferenciasUsuario = [usuario.id_discord, preferencia_usuario.preferencia if preferencia_usuario else ""]
                preferenciasRival = [rival.id_discord, preferencia_rival.preferencia if preferencia_rival else ""]

                if rival and rival.jornada_actual < usuario.jornada_actual:
                    await UtilesDiscord.mensaje_administradores(f"{usuario.nombre_discord} está en la jornada {usuario.jornada_actual} esperando a {rival.nombre_discord} que está en la jornada {rival.jornada_actual}.")
                elif rival:
                    grupo_usuario = usuario.grupo
                    if grupo_usuario in [1, 2, 3, 4]:
                        categoria_id_nuevo = 1326104425370095689
                    elif grupo_usuario in [5, 6, 7, 8, 9]:
                        categoria_id_nuevo = 1326104506043465761
                    else:
                        categoria_id_nuevo = 1326104557767491584
                    nombre_canal = f"j{usuario.jornada_actual}-{rival.nombre_discord}vs{usuario.nombre_discord}"
                    idNuevoCanal = await UtilesDiscord.gestionar_canal_discord(
                        ctx,
                        "crear",
                        nombre_canal,
                        rival.id_discord,
                        usuario.id_discord,
                        raza1=rival.raza,
                        raza2=usuario.raza,
                        fechalimite=int(calendario.fechaFinal.timestamp()),
                        preferencias1=preferenciasRival,
                        preferencias2=preferenciasUsuario,
                        categoria_id=categoria_id_nuevo,
                        bbname1=rival.nombre_bloodbowl or "",
                        bbname2=usuario.nombre_bloodbowl or "",
                    )
                    if idNuevoCanal:
                        calendario.canalAsociado = idNuevoCanal
                        session.commit()
                    else:
                        print(f"No se pudo crear el canal para el partido {nombre_canal}")

    return "Actualización completada."


def get_int_value(dictionary, key):
    value = dictionary.get(key)
    return 0 if value is None else value

async def actualizar_clasificacion_partido(ctx, session, match, tabla_calendario, categoria_id):
    # Verificar si el partido ya existe en la base de datos
    partido_uuid = match.get('id')
    if not partido_uuid:
        return "El UUID del partido no está disponible."
    
    partido_existente = session.query(GestorSQL.Partidos).filter_by(idPartidoBbowl=partido_uuid).first()
    if partido_existente:
        return "El partido ya ha sido procesado previamente."
    
    # Obtener IDs de los coaches
    coach_ids = [coach['id'] for coach in match.get('coaches_info', [])]
    
    if len(coach_ids) != 2:
        return "No se encontraron ambos coaches en la información proporcionada."
    
    # Buscar usuarios en la base de datos
    usuarios = session.query(GestorSQL.Usuario).filter(GestorSQL.Usuario.id_bloodbowl.in_(coach_ids)).all()
    
    if len(usuarios) != 2:
        return "No se encontraron ambos usuarios en la base de datos."
    
    # Asociar coaches con usuarios
    coach_id_to_usuario = {usuario.id_bloodbowl: usuario for usuario in usuarios}
    
    # Obtener el registro del calendario correspondiente
    calendario_registro = session.query(tabla_calendario).filter(
        and_(
            tabla_calendario.coach1.in_([usuarios[0].idUsuarios, usuarios[1].idUsuarios]),
            tabla_calendario.coach2.in_([usuarios[0].idUsuarios, usuarios[1].idUsuarios]),
        ),
        tabla_calendario.partidos_idPartidos == None
    ).order_by(tabla_calendario.jornada).first()
    
    if not calendario_registro:
        return "No se encontró un registro de calendario correspondiente."
    
    # Determinar el índice del equipo local y visitante
    # Usamos 'idteamlisting' para comparar los equipos
    match_teams = match.get('teams', [])
    if len(match_teams) != 2:
        return "No se encontró información suficiente sobre los equipos en el partido."
    
    team_ids_in_match = [team.get('idteamlisting') for team in match_teams]
    
    # Asociar equipos con coaches
    team_coach_map = {}
    for team_info in match.get('teams_info', []):
        team_id = team_info.get('id')
        coach_id = team_info.get('idcoach')
        if not coach_id:
            # Buscar el coach en 'match' -> 'coaches' usando el índice del equipo
            for index, team in enumerate(match_teams):
                if team.get('idteamlisting') == team_id:
                    coach_id = match['coaches'][index]['idcoach']
                    break
        if coach_id:
            team_coach_map[team_id] = coach_id
    
    # Asociar equipos con usuarios
    team_usuario_map = {}
    for team_id in team_ids_in_match:
        coach_id = team_coach_map.get(team_id)
        usuario = coach_id_to_usuario.get(coach_id)
        if usuario:
            team_usuario_map[team_id] = usuario
    
    # Determinar los índices
    usuario_coach1 = calendario_registro.usuario_coach1
    usuario_coach2 = calendario_registro.usuario_coach2
    
    if team_usuario_map.get(match_teams[0]['idteamlisting']).idUsuarios == usuario_coach1.idUsuarios:
        local_index = 0
        visitante_index = 1
    else:
        local_index = 1
        visitante_index = 0
    
    # Función auxiliar para obtener valores enteros
    def get_int_value(dictionary, key):
        value = dictionary.get(key)
        return 0 if value is None else value
    
    # Calcular estadísticas del partido usando get_int_value
    total_muertes_coach1 = get_int_value(match_teams[local_index], 'sustaineddead')
    total_lesiones_coach1 = get_int_value(match_teams[visitante_index], 'inflictedcasualties') - total_muertes_coach1
    
    total_muertes_coach2 = get_int_value(match_teams[visitante_index], 'sustaineddead')
    total_lesiones_coach2 = get_int_value(match_teams[local_index], 'inflictedcasualties') - total_muertes_coach2
    
    # Mención al visitante
    mencionVisitante = '<@' + str(usuario_coach2.id_discord) + '>' if local_index == 0 else '<@' + str(usuario_coach1.id_discord) + '>'
    embed = UtilesDiscord.crearEmbedPartido(match['coaches'][local_index], mencionVisitante, match, local_index)
    await UtilesDiscord.publicar(ctx, 'Jornada ' + str(calendario_registro.jornada) + '!', embed=embed, id_foro=categoria_id)
    
    nuevo_partido = GestorSQL.Partidos(
        resultado1=get_int_value(match_teams[local_index], 'score'),
        resultado2=get_int_value(match_teams[visitante_index], 'score'),
        lesiones1=total_lesiones_coach1,
        lesiones2=total_lesiones_coach2,
        muertes1=total_muertes_coach1,
        muertes2=total_muertes_coach2,
        idPartidoBbowl=partido_uuid,
        pases1=get_int_value(match_teams[local_index], 'inflictedpasses'),
        pases2=get_int_value(match_teams[visitante_index], 'inflictedpasses'),
        catches1=get_int_value(match_teams[local_index], 'inflictedcatches'),
        catches2=get_int_value(match_teams[visitante_index], 'inflictedcatches'),
        interceptions1=get_int_value(match_teams[local_index], 'inflictedinterceptions'),
        interceptions2=get_int_value(match_teams[visitante_index], 'inflictedinterceptions'),
        ko1=get_int_value(match_teams[local_index], 'inflictedko'),
        ko2=get_int_value(match_teams[visitante_index], 'inflictedko'),
        push1=get_int_value(match_teams[local_index], 'inflictedpushouts'),
        push2=get_int_value(match_teams[visitante_index], 'inflictedpushouts'),
        mRun1=get_int_value(match_teams[local_index], 'inflictedmetersrunning'),
        mRun2=get_int_value(match_teams[visitante_index], 'inflictedmetersrunning'),
        mPass1=get_int_value(match_teams[local_index], 'inflictedmeterspassing'),
        mPass2=get_int_value(match_teams[visitante_index], 'inflictedmeterspassing'),
        logo1=match_teams[local_index].get('teamlogo', ''),
        logo2=match_teams[visitante_index].get('teamlogo', ''),
        nombreEquipo1=match_teams[local_index].get('teamname', ''),
        nombreEquipo2=match_teams[visitante_index].get('teamname', '')
    )
    
    session.add(nuevo_partido)
    session.commit()
    
    calendario_registro.partidos_idPartidos = nuevo_partido.idPartidos
    session.commit()
    
    # Actualizar la jornada actual de los usuarios
    for usuario in usuarios:
        usuario.jornada_actual += 1
    session.commit()
    
    # Eliminar el canal asociado
    try:
        await UtilesDiscord.gestionar_canal_discord(ctx, "eliminar", canal_id=calendario_registro.canalAsociado)
    except Exception as e:
        await UtilesDiscord.mensaje_administradores(f"No se pudo borrar el canal con id {calendario_registro.canalAsociado}")
    
    # Crear nuevos canales y notificaciones para los siguientes partidos
    for usuario in usuarios:
        rival = None
        calendario = session.query(tabla_calendario)\
            .filter(or_(tabla_calendario.coach1 == usuario.idUsuarios, tabla_calendario.coach2 == usuario.idUsuarios))\
            .filter(tabla_calendario.jornada == usuario.jornada_actual)\
            .first()
        if calendario:
            rival_id = calendario.coach1 if calendario.coach1 != usuario.idUsuarios else calendario.coach2
            rival = session.query(GestorSQL.Usuario).filter_by(idUsuarios=rival_id).first()
    
            preferencia_usuario = session.query(GestorSQL.PreferenciasFecha).filter_by(idUsuarios=usuario.idUsuarios).first()
            preferencia_rival = session.query(GestorSQL.PreferenciasFecha).filter_by(idUsuarios=rival_id).first()
    
            preferenciasUsuario = [usuario.id_discord, preferencia_usuario.preferencia if preferencia_usuario else ""]
            preferenciasRival = [rival.id_discord, preferencia_rival.preferencia if preferencia_rival else ""]
    
            if rival and rival.jornada_actual < usuario.jornada_actual:
                await UtilesDiscord.mensaje_administradores(f"{usuario.nombre_discord} está en la jornada {usuario.jornada_actual} esperando a {rival.nombre_discord} que está en la jornada {rival.jornada_actual}.")
            elif rival:
                nombre_canal = f"j{usuario.jornada_actual}-{rival.nombre_discord}vs{usuario.nombre_discord}"
                idNuevoCanal = await UtilesDiscord.gestionar_canal_discord(
                    ctx,
                    "crear",
                    nombre_canal,
                    rival.id_discord,
                    usuario.id_discord,
                    raza1=rival.raza,
                    raza2=usuario.raza,
                    fechalimite=int(calendario.fechaFinal.timestamp()),
                    preferencias1=preferenciasRival,
                    preferencias2=preferenciasUsuario,
                    bbname1=rival.nombre_bloodbowl or "",
                    bbname2=usuario.nombre_bloodbowl or "",
                )
                if idNuevoCanal:
                    calendario.canalAsociado = idNuevoCanal
                    session.commit()
                else:
                    print(f"No se pudo crear el canal para el partido {nombre_canal}")
    
    return "Actualización completada."

@bot.command()
async def actualiza_clasificacion(ctx, todos: int = 0):
    if str(ctx.author.id) not in maestros:
        await ctx.send("No tienes permiso para usar este comando.")
        return

    Session = sessionmaker(bind=GestorSQL.conexionEngine())
    session = Session()

    canal_id=1223765590146158653

    mensaje = await actualizar_clasificacion(ctx,session, lambda: APIBbowl.obtener_partido_ButterCup(bbowl_API_token), GestorSQL.Calendario, canal_id, todos)
    await ctx.send(mensaje)

    session.close() 
  
@bot.command(name='actualiza_partido')
async def actualiza_partido(ctx, uuid: str):
    Session = sessionmaker(bind=GestorSQL.conexionEngine())
    session = Session()

    canal_id = 1223765590146158653  

    match = APIBbowl.obtener_partido_por_uuid(bbowl_API_token, uuid)
    if match is None:
        await ctx.send("No se pudo obtener el partido con el UUID proporcionado.")
    else:
        mensaje = await actualizar_clasificacion_partido(ctx, session, match, GestorSQL.Calendario, canal_id)
        await ctx.send(mensaje)

    session.close()
@bot.command()
@commands.has_any_role('Moderadores', 'Administrador', 'Comisario')
async def actualiza_Ticket(ctx, todos: int = 0):
    Session = sessionmaker(bind=GestorSQL.conexionEngine())
    session = Session()

    canal_id = 1223765590146158653

    mensaje = await actualizar_ticket(
        ctx,
        session,
        lambda: APIBbowl.obtener_partido_PlayOfTicket(bbowl_API_token),
        canal_id,
        GestorSQL.Ticket,
        todos,
    )
    await ctx.send(mensaje)

    session.close()
    
@bot.command()
@commands.has_any_role('Moderadores', 'Administrador', 'Comisario')
async def vincular_partido(ctx, id_partido: int, id_calendario: int):
    Session = sessionmaker(bind=GestorSQL.conexionEngine())
    session = Session()

    partido = session.query(GestorSQL.Partidos).filter_by(idPartidos=id_partido).first()
    calendario_registro = session.query(GestorSQL.Calendario).filter_by(idCalendario=id_calendario).first()

    if not partido or not calendario_registro:
        await ctx.send("Partido o registro de calendario no encontrado.")
        session.close()
        return

    # Vincular partido con registro de calendario
    calendario_registro.partidos_idPartidos = id_partido
    session.commit()

    # Incrementar la jornada_actual de ambos usuarios
    usuarios = session.query(GestorSQL.Usuario).filter(
        GestorSQL.Usuario.idUsuarios.in_([calendario_registro.coach1, calendario_registro.coach2])
    ).all()

    for usuario in usuarios:
        usuario.jornada_actual += 1
    session.commit()

    # Borrar el canal asociado si existe
    try:
        await UtilesDiscord.gestionar_canal_discord(ctx, "eliminar", canal_id=calendario_registro.canalAsociado)
    except Exception as e:
        await UtilesDiscord.mensaje_administradores(f"No se pudo borrar el canal con id {calendario_registro.canalAsociado}")

    # Buscar y crear canales para los próximos partidos
    for usuario in usuarios:
        rival = None
        calendario = session.query(GestorSQL.Calendario)\
            .filter(or_(GestorSQL.Calendario.coach1 == usuario.idUsuarios, GestorSQL.Calendario.coach2 == usuario.idUsuarios))\
            .filter(GestorSQL.Calendario.jornada == usuario.jornada_actual)\
            .first()
        if calendario:
            rival_id = calendario.coach1 if calendario.coach1 != usuario.idUsuarios else calendario.coach2
            rival = session.query(GestorSQL.Usuario).filter_by(idUsuarios=rival_id).first()

            preferencia_usuario = session.query(GestorSQL.PreferenciasFecha).filter_by(idUsuarios=usuario.idUsuarios).first()
            preferencia_rival = session.query(GestorSQL.PreferenciasFecha).filter_by(idUsuarios=rival_id).first()

            preferenciasUsuario = [usuario.id_discord, preferencia_usuario.preferencia if preferencia_usuario else ""]
            preferenciasRival = [rival.id_discord, preferencia_rival.preferencia if preferencia_rival else ""]

            # Seleccionar categoría según el grupo
            grupo_usuario = usuario.grupo
            if grupo_usuario in [1, 2, 3, 4]:
                categoria_id = 1326104425370095689  # Categoría Oro
            elif grupo_usuario in [5, 6, 7, 8,9]:
                categoria_id = 1326104506043465761  # Categoría Plata
            else:
                categoria_id = 1326104557767491584  # Categoría Bronce

            if rival and rival.jornada_actual < usuario.jornada_actual:
                await UtilesDiscord.mensaje_administradores(
                    f"{usuario.nombre_discord} está en la jornada {usuario.jornada_actual} esperando a {rival.nombre_discord} que está en la jornada {rival.jornada_actual}."
                )
            elif rival:
                nombre_canal = f"j{usuario.jornada_actual}-{rival.nombre_discord}vs{usuario.nombre_discord}"
                idNuevoCanal = await UtilesDiscord.gestionar_canal_discord(
                    ctx, "crear", nombre_canal, rival.id_discord, usuario.id_discord,
                    raza1=rival.raza, raza2=usuario.raza,
                    fechalimite=int(calendario.fechaFinal.timestamp()),
                    preferencias1=preferenciasRival, preferencias2=preferenciasUsuario,
                    categoria_id=categoria_id
                )

                if idNuevoCanal:
                    calendario.canalAsociado = idNuevoCanal
                    session.commit()
                else:
                    print(f"No se pudo crear el canal para el partido {nombre_canal}")

    session.close()
    await ctx.send("Partido vinculado y canales actualizados.")

async def obtener_hilo_por_id(guild: discord.Guild, thread_id: int) -> Optional[discord.Thread]:
    hilo = guild.get_thread(thread_id)
    if hilo:
        return hilo

    try:
        canal = await guild.fetch_channel(thread_id)
        if isinstance(canal, discord.Thread):
            return canal
    except Exception as e:
        print(f"No se pudo recuperar el hilo {thread_id}: {e}")

    # Intentar obtenerlo a través del cliente global por si no está en caché
    try:
        canal = await DiscordClientSingleton.get_bot_instance().fetch_channel(thread_id)
        if isinstance(canal, discord.Thread):
            return canal
    except Exception as e:
        print(f"No se pudo recuperar el hilo {thread_id} con el bot: {e}")

    return None

def obtener_nombre_equipo_previo(session, coach_id: int) -> str:
    calendario_prev = session.query(GestorSQL.Calendario).filter(
        or_(GestorSQL.Calendario.coach1 == coach_id, GestorSQL.Calendario.coach2 == coach_id),
        GestorSQL.Calendario.partidos_idPartidos != None
    ).order_by(GestorSQL.Calendario.jornada.desc()).first()

    if calendario_prev and calendario_prev.partidos_idPartidos:
        partido_prev = session.query(GestorSQL.Partidos).filter_by(idPartidos=calendario_prev.partidos_idPartidos).first()
        if partido_prev:
            if calendario_prev.coach1 == coach_id:
                return partido_prev.nombreEquipo1 or "Equipo nuevo (sin datos)"
            return partido_prev.nombreEquipo2 or "Equipo nuevo (sin datos)"

    return "Equipo nuevo (sin datos)"

@bot.command(name="administrar_partido")
@commands.has_any_role('Moderadores', 'Administrador', 'Comisario')
async def administrar_partido(ctx, jornada: int, ganador: discord.Member):
    Session = sessionmaker(bind=GestorSQL.conexionEngine())
    session = Session()

    id_canal_contexto = ctx.channel.parent_id if isinstance(ctx.channel, discord.Thread) else ctx.channel.id

    ganador_bd = session.query(GestorSQL.Usuario).filter_by(id_discord=ganador.id).first()
    if not ganador_bd:
        await ctx.send("No se encontró al usuario ganador en la base de datos.")
        session.close()
        return

    calendario_registro = session.query(GestorSQL.Calendario).filter(
        GestorSQL.Calendario.jornada == jornada,
        GestorSQL.Calendario.partidos_idPartidos == None,
        or_(GestorSQL.Calendario.coach1 == ganador_bd.idUsuarios, GestorSQL.Calendario.coach2 == ganador_bd.idUsuarios)
    ).first()

    if not calendario_registro:
        calendario_registro = session.query(GestorSQL.Calendario).filter(
            GestorSQL.Calendario.jornada == jornada,
            GestorSQL.Calendario.canalAsociado == id_canal_contexto,
            GestorSQL.Calendario.partidos_idPartidos == None
        ).first()

    if not calendario_registro:
        await ctx.send("No se encontró el partido para administrar. Verifica la jornada y el canal.")
        session.close()
        return

    coach1 = calendario_registro.usuario_coach1
    coach2 = calendario_registro.usuario_coach2

    if ganador_bd.idUsuarios == coach1.idUsuarios:
        resultado1, resultado2 = 1, 0
    elif ganador_bd.idUsuarios == coach2.idUsuarios:
        resultado1, resultado2 = 0, 1
    else:
        await ctx.send("El ganador indicado no forma parte de este partido.")
        session.close()
        return

    descripcion_partido = f"administrado {coach1.nombre_discord} vs {coach2.nombre_discord}"
    nuevo_partido = GestorSQL.Partidos(
        resultado1=resultado1,
        resultado2=resultado2,
        lesiones1=0,
        lesiones2=0,
        muertes1=0,
        muertes2=0,
        idPartidoBbowl=descripcion_partido,
        pases1=0,
        pases2=0,
        catches1=0,
        catches2=0,
        interceptions1=0,
        interceptions2=0,
        ko1=0,
        ko2=0,
        push1=0,
        push2=0,
        mRun1=0,
        mRun2=0,
        mPass1=0,
        mPass2=0,
        logo1="",
        logo2="",
        nombreEquipo1="",
        nombreEquipo2=""
    )

    session.add(nuevo_partido)
    session.commit()
    session.refresh(nuevo_partido)

    calendario_id = calendario_registro.idCalendario
    grupo = calendario_registro.usuario_coach1.grupo_grupo.nombre_grupo if calendario_registro.usuario_coach1.grupo_grupo else calendario_registro.usuario_coach1.grupo
    coach1_nombre = calendario_registro.usuario_coach1.nombre_discord
    coach2_nombre = calendario_registro.usuario_coach2.nombre_discord
    equipo_coach1 = obtener_nombre_equipo_previo(session, coach1.idUsuarios)
    equipo_coach2 = obtener_nombre_equipo_previo(session, coach2.idUsuarios)
    partido_id = nuevo_partido.idPartidos
    session.close()

    await vincular_partido(ctx, partido_id, calendario_id)

    mensaje_hilo = (
        f"Partido administrado de la Jornada {jornada} entre {coach1_nombre} ({equipo_coach1}) "
        f"y {coach2_nombre} ({equipo_coach2}) del grupo {grupo}. Ganador {ganador.mention}"
    )
    hilo_aviso = await obtener_hilo_por_id(ctx.guild, 1430913723039744162)
    if hilo_aviso:
        await hilo_aviso.send(mensaje_hilo)
    else:
        await UtilesDiscord.mensaje_administradores(f"No se pudo encontrar el hilo de administración para avisar sobre el partido de la jornada {jornada}.")

    await ctx.send(f"Partido administrado y vinculado con éxito. ID de partido: {partido_id}, calendario: {calendario_id}")

@bot.command()
@commands.has_any_role('Moderadores', 'Administrador', 'Comisario')
async def CreaCanalesJornada(ctx, jornada, *, mensaje=""):
    Session = sessionmaker(bind=GestorSQL.conexionEngine())
    with Session() as session:
        # Crear alias para cada relación con la tabla de usuarios
        UsuarioCoach1 = aliased(GestorSQL.Usuario)
        UsuarioCoach2 = aliased(GestorSQL.Usuario)

        calendarios = session.query(GestorSQL.Calendario)\
            .join(UsuarioCoach1, GestorSQL.Calendario.coach1 == UsuarioCoach1.idUsuarios)\
            .join(UsuarioCoach2, GestorSQL.Calendario.coach2 == UsuarioCoach2.idUsuarios)\
            .filter(
                GestorSQL.Calendario.jornada == jornada,
                GestorSQL.Calendario.canalAsociado == 0
            )\
            .all()

        for calendario in calendarios:
            coach1 = calendario.usuario_coach1
            coach2 = calendario.usuario_coach2
            nombre_canal = f"{coach1.nombre_discord}vs{coach2.nombre_discord}"

            # Selección de categoría según el grupo (ambos entrenadores están en el mismo grupo)
            grupo = coach1.grupo
            if grupo in [1, 2, 3, 4]:
                categoria_id = 1326104425370095689  # Oro
            elif grupo in [5, 6, 7, 8, 9]:
                categoria_id = 1326104506043465761  # Plata
            else:
                categoria_id = 1326104557767491584  # Bronce

            # Obtener preferencias de horario
            pref1 = session.query(GestorSQL.PreferenciasFecha)\
                           .filter_by(idUsuarios=coach1.idUsuarios).first()
            pref2 = session.query(GestorSQL.PreferenciasFecha)\
                           .filter_by(idUsuarios=coach2.idUsuarios).first()
            preferenciasUsuario = [coach1.id_discord, pref1.preferencia if pref1 else ""]
            preferenciasRival   = [coach2.id_discord, pref2.preferencia if pref2 else ""]

            try:
                idNuevoCanal = await UtilesDiscord.gestionar_canal_discord(
                    ctx, "crear", nombre_canal,
                    coach2.id_discord, coach1.id_discord,
                    raza1=coach2.raza, raza2=coach1.raza,
                    bbname1=coach2.nombre_bloodbowl, bbname2=coach1.nombre_bloodbowl,
                    fechalimite=int(calendario.fechaFinal.timestamp()),
                    preferencias1=preferenciasRival, preferencias2=preferenciasUsuario,
                    categoria_id=categoria_id
                )
                if idNuevoCanal:
                    calendario.canalAsociado = idNuevoCanal
                else:
                    print(f"No se pudo crear el canal para {nombre_canal}")
            except Exception as e:
                session.commit()
                print(f"Error al crear el canal {nombre_canal}: {e}")

            # Pequeña pausa para evitar rate limits
            await asyncio.sleep(5)

        session.commit()

    await ctx.send(f"Canales de la jornada {jornada} creados y vinculados.") 

@bot.command()
@commands.has_any_role('Moderadores', 'Administrador', 'Comisario')
async def CreaCanalesTicket(ctx, jornada):
    Session = sessionmaker(bind=GestorSQL.conexionEngine())
    with Session() as session:
        # Crear alias para cada relación con la tabla de usuarios
        UsuarioCoach1 = aliased(GestorSQL.Usuario)
        UsuarioCoach2 = aliased(GestorSQL.Usuario)

        calendarios = session.query(GestorSQL.Ticket)\
            .join(UsuarioCoach1, GestorSQL.Ticket.coach1 == UsuarioCoach1.idUsuarios)\
            .join(UsuarioCoach2, GestorSQL.Ticket.coach2 == UsuarioCoach2.idUsuarios)\
            .filter(GestorSQL.Ticket.jornada == jornada)\
            .all()

        for calendario in calendarios:
            coach1_nombre = calendario.usuario_coach1.nombre_discord
            coach2_nombre = calendario.usuario_coach2.nombre_discord
            coach1_id = calendario.usuario_coach1.id_discord
            coach2_id = calendario.usuario_coach2.id_discord
            
            nombre_canal = f"🎟{coach1_nombre}vs{coach2_nombre}"
            
            preferencia_usuario = session.query(GestorSQL.PreferenciasFecha).filter_by(idUsuarios=calendario.usuario_coach1.idUsuarios).first()
            preferencia_rival = session.query(GestorSQL.PreferenciasFecha).filter_by(idUsuarios=calendario.usuario_coach2.idUsuarios).first()

            preferenciasUsuario = [coach1_id, preferencia_usuario.preferencia if preferencia_usuario else ""]
            preferenciasRival = [coach2_id, preferencia_rival.preferencia if preferencia_rival else ""]

            #creamos el mensaje
            fecha=f"\n\nLa Fecha límite para jugar el partido es el <t:{int(calendario.fechaFinal.timestamp())}:f>"
            
            mensajePreferencias1=''
            if preferenciasUsuario[0] and preferenciasUsuario[1]:
                mensajePreferencias1 = f"\n<@{preferenciasUsuario[0]}> suele poder jugar {preferenciasUsuario[1]}"
        
            mensajePreferencias2=''
            if preferenciasRival[0] and preferenciasRival[1]:
                preferenciasRival = f"\n<@{preferenciasRival[0]}> suele poder jugar {preferenciasRival[1]}"



            mensaje = """Bienvenidos, {mention1}({raza1}) y {mention2}({raza2})! Estáis en los Play-Offs que pueden llevaros a conseguir un 🎟**TICKET**🎟. El primero se llevará un Ticket directo para el mundial y el segundo un Ticket de play-in.
            
Ahora debéis elegir uno de los equipos con los que habéis jugado la ButterCup para inscribirlo en la competición Ticket ButterCup contraseña TicketButtercup2025.
Si el equipo está actualmente jugando los playoffs de la Cuarta Edición de la Butter Cup debéis hacer una copia del equipo. Contáis con la ayuda de los comisarios para ello.
Si el equipo lleva 20 partidos sin hacer reforma deberéis hacerla ANTES de empezar vuestro pirmer partido.\n\n-------------------------------------------""" + mensajePreferencias1 + mensajePreferencias2 +"""
Cuando acordéis una fecha usad el comando /fecha para que el bot pueda registrar vuestro partido con el horario de España.{fecha}
            
        -------------------------------------------
            
Antes de jugar tendréis que **USAR EL CANAL** #spin y **LIBERADLO** al encontrar partido.
            
Si hubiera cualquier problema mencionad a los comisarios.
                """
            
            # Buscar los entrenadores y ajustar permisos
            guild = ctx.guild
            coach1 = guild.get_member(calendario.usuario_coach1.id_discord)
            coach2 = guild.get_member(calendario.usuario_coach2.id_discord)

            # Preparar y enviar mensaje de bienvenida
            mention1 = coach1.mention if coach1 else ""
            mention2 = coach2.mention if coach2 else ""
            mensaje_formateado = mensaje.format(mention1=mention1, mention2=mention2,raza1=calendario.usuario_coach1.raza,raza2=calendario.usuario_coach2.raza,fecha=fecha)

            categoria_id_nuevo = 1396596687879016499

            try:
                idNuevoCanal = await UtilesDiscord.gestionar_canal_discord(ctx, "crear", nombre_canal, calendario.usuario_coach1.id_discord, calendario.usuario_coach2.id_discord,mensaje=mensaje_formateado,categoria_id=categoria_id_nuevo)
                if idNuevoCanal:
                    calendario.canalAsociado = idNuevoCanal
                else:
                    print(f"No se pudo crear el canal para el partido {nombre_canal}")
            except Exception as e:
                session.commit()
                print(f"Error al crear el canal {nombre_canal}: {e}")
                
            await asyncio.sleep(5)

        # Solo se hace commit si todos los canales fueron creados y asociados correctamente
        session.commit()
 


@bot.command(name='EnviarMensaje')
@commands.has_any_role('Moderadores', 'Administrador', 'Comisario')
async def enviar_mensaje_con_adjuntos(ctx, id_canal: str, *, mensaje: str):
    try:
        # Encontrar el canal por su nombre
        canal_objetivo = bot.get_channel(int(id_canal))
        if not canal_objetivo:
            await ctx.send("Canal no encontrado.", delete_after=20)
            return

        # Verificar si el mensaje que activó el comando tiene archivos adjuntos
        archivos = []
        if ctx.message.attachments:
            if not os.path.exists('./temp/imagenes'):
                os.makedirs('./temp/imagenes')
            for adjunto in ctx.message.attachments:
                # Suponemos que todos los archivos adjuntos son imágenes
                path = f'./temp/imagenes/{adjunto.filename}'
                await descargar_imagen(adjunto.url, path)  # Asegúrate de tener esta función definida
                archivos.append(discord.File(path))

        # Enviar el mensaje con archivos adjuntos al canal objetivo
        await canal_objetivo.send(content=mensaje, files=archivos if archivos else [])

        # Limpiar: eliminar imágenes descargadas para evitar el uso excesivo de espacio en disco
        for archivo in archivos:
            os.remove(archivo.fp.name)

        await ctx.send(f"Mensaje enviado con éxito", delete_after=20)
    except discord.Forbidden:
        await ctx.send("No tengo permisos para enviar mensajes o manejar archivos adjuntos en este canal.", delete_after=20)
    except discord.HTTPException as e:
        await ctx.send(f"Error al enviar el mensaje: {e}", delete_after=20)        


@bot.command(name='EditaMensaje')
@commands.has_any_role('Moderadores', 'Administrador', 'Comisario')
async def edita_mensaje(ctx, mensaje_id: int, *, nuevo_contenido: str):
    try:
        canal = ctx.channel
        mensaje_a_editar = await canal.fetch_message(mensaje_id)

        # Verificar si el mensaje que activó el comando tiene archivos adjuntos
        archivos = []
        if ctx.message.attachments:
            if not os.path.exists('./temp/imagenes'):
                os.makedirs('./temp/imagenes')
            for adjunto in ctx.message.attachments:
                # Suponemos que todos los archivos adjuntos son imágenes
                path = f'./temp/imagenes/{adjunto.filename}'
                await descargar_imagen(adjunto.url, path)
                archivos.append(File(path))

        # Editar el mensaje, reenviando las imágenes como archivos adjuntos
        await mensaje_a_editar.edit(content=nuevo_contenido, attachments=archivos if archivos else [])

        # Limpiar: eliminar imágenes descargadas para evitar el uso excesivo de espacio en disco
        for archivo in archivos:
            os.remove(archivo.fp.name)

        await ctx.send("Mensaje editado con éxito.", delete_after=20)
    except discord.NotFound:
        await ctx.send("Mensaje no encontrado.", delete_after=20)
    except discord.Forbidden:
        await ctx.send("No tengo permisos para editar este mensaje o manejar archivos adjuntos.", delete_after=20)
    except discord.HTTPException as e:
        await ctx.send(f"Error al editar el mensaje: {e}", delete_after=20)        
        # Borrar el mensaje que invocó el comando
    await ctx.message.delete()
    
async def descargar_imagen(url, path):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                with open(path, 'wb') as f:
                    f.write(await resp.read())
                return path

@bot.command("CreaImagenPrueba")
@commands.has_any_role('Moderadores', 'Administrador', 'Comisario')
async def CreaImagenPrueba(ctx,plantilla='jornada'):
    sheetCalendarioResultados = GestionExcel.sheetCalendarioResultados

    entrenadores = {}
    resultados = {'0': "77", '1': "2",'2': "0", '3': "2",'4': "1", '5': "2",'6': "1", '7': "2", '8': "2",'9': "8", '10': "2",'11': "0", '12': "2",'13': "1", '14': "2",'15': "1", '16': "2", '17': "2"}

    n = 2 + (30 - 1) * 8  # Fila del primer partido de la jornada
    indice = 0
    for i in range(n, n + 8):
        entrenadores[str(indice)] = buscarNombreAMostrar(sheetCalendarioResultados.cell(i, 3).value).upper()
        indice +=1
        entrenadores[str(indice)] = buscarNombreAMostrar(sheetCalendarioResultados.cell(i, 7).value).upper()
        indice +=1

    loop = asyncio.get_event_loop()  # Obtiene el loop de asyncio.
    
    # Ejecuta la creación de la imagen en un hilo separado y espera el resultado.
    ruta_imagen = await loop.run_in_executor(None, lambda: Imagenes.crear_imagen(plantilla, entrenadores=entrenadores, resultados=resultados))

    if ruta_imagen is not None:
        await ctx.reply(content='prueba', file=File(ruta_imagen))

        # Programa la eliminación de la imagen en un hilo separado después de 10 segundos.
        threading.Timer(10, lambda: Imagenes.eliminar_imagen(ruta_imagen)).start()    
    else:
        await ctx.reply("No se pudo eliminar la imagen")
   

@bot.command(name="crearImagenJornada")
@commands.has_any_role('Moderadores', 'Administrador', 'Comisario')
async def crear_image_jornada(ctx, grupo: int, jornada: int):
    Session = sessionmaker(bind=GestorSQL.conexionEngine())
    session = Session()
    try:
        entrenadores = {}
        resultados = {}
        razas = {}
        jornadaDict = {'0': str(jornada)}
        indice = 0


        UsuarioAlias1 = aliased(GestorSQL.Usuario)
        UsuarioAlias2 = aliased(GestorSQL.Usuario)
        
        # Obtener partidos de la jornada y que ambos entrenadores pertenezcan al grupo especificado
        partidos = session.query(
            GestorSQL.Calendario,
            func.coalesce(UsuarioAlias1.nombreAMostrar, UsuarioAlias1.nombre_bloodbowl).label('nombre_coach1'),
            func.coalesce(UsuarioAlias2.nombreAMostrar, UsuarioAlias2.nombre_bloodbowl).label('nombre_coach2'),
            GestorSQL.Partidos.resultado1,
            GestorSQL.Partidos.resultado2,
            UsuarioAlias1.raza.label('raza1'),
            UsuarioAlias2.raza.label('raza2')
        ).\
        filter(GestorSQL.Calendario.jornada == jornada).\
        join(GestorSQL.Partidos, GestorSQL.Calendario.partidos_idPartidos == GestorSQL.Partidos.idPartidos).\
        join(UsuarioAlias1, GestorSQL.Calendario.coach1 == UsuarioAlias1.idUsuarios).\
        filter(UsuarioAlias1.grupo == grupo).\
        join(UsuarioAlias2, GestorSQL.Calendario.coach2 == UsuarioAlias2.idUsuarios).\
        filter(UsuarioAlias2.grupo == grupo).all()
        
        for partido in partidos:
            entrenadores[str(indice)] = partido.nombre_coach1
            resultados[str(indice)] = partido.resultado1
            razas[str(indice)] = partido.raza1
            indice += 1
            entrenadores[str(indice)] = partido.nombre_coach2
            resultados[str(indice)] = partido.resultado2
            razas[str(indice)] = partido.raza2
            indice += 1

        # Crear imagen
        ruta_imagen = Imagenes.crear_imagen("jornada", grupo,entrenadores=entrenadores,resultados=resultados,jornadas=jornadaDict,razas=razas)

        # Enviar la imagen
        with open(ruta_imagen, 'rb') as file:
            await ctx.send(file=discord.File(file))
        
        threading.Timer(10, lambda: Imagenes.eliminar_imagen(ruta_imagen)).start()  
        
    except Exception as e:
        await ctx.send(f"Ocurrió un error: {str(e)}")
    finally:
        session.close()

        
@bot.command(name="crearImagenJornadaVacia")
@commands.has_any_role('Moderadores', 'Administrador', 'Comisario')
async def crear_image_jornada_vacia(ctx, grupo: int, jornada: int):
    Session = sessionmaker(bind=GestorSQL.conexionEngine())
    session = Session()
    try:
        entrenadores = {}
        resultados = {}
        razas = {}
        jornadaDict = {'0': str(jornada)}
        indice = 0


        UsuarioAlias1 = aliased(GestorSQL.Usuario)
        UsuarioAlias2 = aliased(GestorSQL.Usuario)
        
        # Obtener partidos de la jornada y que ambos entrenadores pertenezcan al grupo especificado
        partidos = session.query(
            GestorSQL.Calendario,
            func.coalesce(UsuarioAlias1.nombreAMostrar, UsuarioAlias1.nombre_bloodbowl).label('nombre_coach1'),
            func.coalesce(UsuarioAlias2.nombreAMostrar, UsuarioAlias2.nombre_bloodbowl).label('nombre_coach2'),
            UsuarioAlias1.raza.label('raza1'),
            UsuarioAlias2.raza.label('raza2')
        ).\
        filter(GestorSQL.Calendario.jornada == jornada).\
        join(UsuarioAlias1, GestorSQL.Calendario.coach1 == UsuarioAlias1.idUsuarios).\
        filter(UsuarioAlias1.grupo == grupo).\
        join(UsuarioAlias2, GestorSQL.Calendario.coach2 == UsuarioAlias2.idUsuarios).\
        filter(UsuarioAlias2.grupo == grupo).all()

        
        for partido in partidos:
            entrenadores[str(indice)] = partido.nombre_coach1
            resultados[str(indice)] = "-"
            razas[str(indice)] = partido.raza1
            indice += 1
            entrenadores[str(indice)] = partido.nombre_coach2
            resultados[str(indice)] = "-"
            razas[str(indice)] = partido.raza2
            indice += 1

        # Crear imagen
        ruta_imagen = Imagenes.crear_imagen("jornada", grupo,entrenadores=entrenadores,resultados=resultados,jornadas=jornadaDict,razas=razas)

        # Enviar la imagen
        with open(ruta_imagen, 'rb') as file:
            await ctx.send(file=discord.File(file))
        
        threading.Timer(10, lambda: Imagenes.eliminar_imagen(ruta_imagen)).start()  
        
    except Exception as e:
        await ctx.send(f"Ocurrió un error: {str(e)}")
    finally:
        session.close()

@bot.command(name="crearJornadaCompleta")
@commands.has_any_role('Moderadores', 'Administrador', 'Comisario')
async def crear_jornada_completa(ctx, jornada: int):
    # Llamar a 'crearImagenClasificacion' para grupos del 1 al 10
    for grupo in range(1, 16):
        await ctx.invoke(bot.get_command('crearImagenClasificacion'), grupo=grupo, jornada=jornada)
        await asyncio.sleep(1)  # Pausa para evitar exceder los límites de tasa

    # Llamar a 'crearImagenJornada' para grupos del 1 al 10
    for grupo in range(1, 16):
        await ctx.invoke(bot.get_command('crearImagenJornada'), grupo=grupo, jornada=jornada)
        await asyncio.sleep(1)

    # Llamar a 'crearImagenJornadaVacia' para grupos del 1 al 10, con jornada + 1
    for grupo in range(1, 16):
        await ctx.invoke(bot.get_command('crearImagenJornadaVacia'), grupo=grupo, jornada=jornada + 1)
        await asyncio.sleep(1)

    await ctx.send(f"Jornada completa {jornada} creada exitosamente.")


@bot.command(name="crearImagenResultado")
@commands.has_any_role('Moderadores', 'Administrador', 'Comisario')
async def crear_image_resultado(ctx, idPartido: int):
    esPrivado = false
    canal_destino = None
    canal_destino = ctx.channel
    
    ruta_imagen = await Imagenes.imagenResultado(idPartido)
    # Enviar la imagen
    with open(ruta_imagen, 'rb') as file:
        await ctx.send(file=discord.File(file))
        
    threading.Timer(10, lambda: Imagenes.eliminar_imagen(ruta_imagen)).start()  


@bot.command(name="crearImagenClasificacion")
@commands.has_any_role('Moderadores', 'Administrador', 'Comisario')
async def crear_imagen_clasificacion(ctx, grupo: int, jornada: int):

    try:
        clasificacion = obtener_clasificacion(jornada, grupo)
    
        entrenadores = {}
        pj = {}
        pg = {}
        pe = {}
        pp = {}
        dtd = {}
        pts = {}
        lesiones = {}
        muertos = {}

        def get_value(fila, index, default=0):
            try:
                value = fila[index]
                return value if value is not None else default
            except IndexError:
                return default

        for indice, fila in enumerate(clasificacion):
            entrenadores[str(indice)] = fila[0]  # nombre_bloodbowl
            pj[str(indice)] = get_value(fila, 1)                # pj
            pg[str(indice)] = get_value(fila, 2)                # pg
            pe[str(indice)] = get_value(fila, 3)                # pe
            pp[str(indice)] = get_value(fila, 4)                # pp
            dtd[str(indice)] = get_value(fila, 5)               # dtd
            pts[str(indice)] = get_value(fila, 6)               # pts
            lesiones_inf = get_value(fila, 7)
            lesiones_rec = get_value(fila, 8)
            lesiones[str(indice)] = f"{lesiones_inf}/{lesiones_rec}"  # LesionesInfligidas/LesionesRecibidas
            muertos_inf = get_value(fila, 9)
            muertos_rec = get_value(fila, 10)
            muertos[str(indice)] = f"{muertos_inf}/{muertos_rec}"     # MuertesInfligidas/MuertesRecibidas            
        # Crear la imagen con los datos de clasificación
        ruta_imagen = Imagenes.crear_imagen("clasificacion",grupo, entrenadores=entrenadores, pj=pj, pg=pg, pe=pe, pp=pp,dtd=dtd,pts=pts, lesiones=lesiones, muertos=muertos)

        with open(ruta_imagen, 'rb') as file:
            await ctx.send(file=discord.File(file))

        # Eliminar la imagen después de un tiempo
        threading.Timer(10, lambda: Imagenes.eliminar_imagen(ruta_imagen)).start()

    except Exception as e:
        await ctx.send(f"Ocurrió un error: {str(e)}")

@bot.command(name="enviarImagenClasificacion")
@commands.has_any_role('Moderadores', 'Administrador', 'Comisario')
async def enviar_imagen_clasificacion(ctx, jornada: int, canal_id: int):
    canal = bot.get_channel(canal_id)
    if not canal:
        await ctx.send(f"No se pudo encontrar el canal con ID {canal_id}")
        return

    imagenes = []
    for grupo in range(1, 16):
        try:
            clasificacion = obtener_clasificacion(jornada, grupo)

            entrenadores = {}
            pj = {}
            pg = {}
            pe = {}
            pp = {}
            dtd = {}
            pts = {}
            lesiones = {}
            muertos = {}

            def get_value(fila, index, default=0):
                try:
                    value = fila[index]
                    return value if value is not None else default
                except IndexError:
                    return default

            for indice, fila in enumerate(clasificacion):
                entrenadores[str(indice)] = fila[0]  # nombre_bloodbowl
                pj[str(indice)] = get_value(fila, 1)                # pj
                pg[str(indice)] = get_value(fila, 2)                # pg
                pe[str(indice)] = get_value(fila, 3)                # pe
                pp[str(indice)] = get_value(fila, 4)                # pp
                dtd[str(indice)] = get_value(fila, 5)               # dtd
                pts[str(indice)] = get_value(fila, 6)               # pts
                lesiones_inf = get_value(fila, 7)
                lesiones_rec = get_value(fila, 8)
                lesiones[str(indice)] = f"{lesiones_inf}/{lesiones_rec}"  # LesionesInfligidas/LesionesRecibidas
                muertos_inf = get_value(fila, 9)
                muertos_rec = get_value(fila, 10)
                muertos[str(indice)] = f"{muertos_inf}/{muertos_rec}"     # MuertesInfligidas/MuertesRecibidas            
            # Crear la imagen con los datos de clasificación
            ruta_imagen = Imagenes.crear_imagen("clasificacion", grupo, entrenadores=entrenadores, pj=pj, pg=pg, pe=pe, pp=pp, dtd=dtd, pts=pts, lesiones=lesiones, muertos=muertos)

            imagenes.append(ruta_imagen)
        except Exception as e:
            await ctx.send(f"Ocurrió un error al crear la imagen del grupo {grupo}: {str(e)}")

    # Dividir las imágenes en tres mensajes
    await canal.send(f"Clasificación oro jornada {str(jornada)}:")
    files_part1 = [discord.File(open(ruta, 'rb')) for ruta in imagenes[:4]]
    await canal.send(files=files_part1)

    await canal.send(f"Clasificación plata jornada {str(jornada)}:")
    files_part2 = [discord.File(open(ruta, 'rb')) for ruta in imagenes[4:9]]
    await canal.send(files=files_part2)

    await canal.send(f"Clasificación bronce jornada {str(jornada)}:")
    files_part3 = [discord.File(open(ruta, 'rb')) for ruta in imagenes[9:]]
    await canal.send(files=files_part3)

    # Eliminar las imágenes después de un tiempo
    for ruta in imagenes:
        threading.Timer(10, lambda ruta=ruta: Imagenes.eliminar_imagen(ruta)).start()
        

@bot.command(name="enviarImagenJornada")
@commands.has_any_role('Moderadores', 'Administrador', 'Comisario')
async def enviar_imagen_jornada(ctx, jornada: int, canal_id: int):
    canal = bot.get_channel(canal_id)
    if not canal:
        await ctx.send(f"No se pudo encontrar el canal con ID {canal_id}")
        return

    imagenes = []
    for grupo in range(1, 16):
        try:
            Session = sessionmaker(bind=GestorSQL.conexionEngine())
            session = Session()
            entrenadores = {}
            resultados = {}
            razas = {}
            jornadaDict = {'0': str(jornada)}
            indice = 0

            UsuarioAlias1 = aliased(GestorSQL.Usuario)
            UsuarioAlias2 = aliased(GestorSQL.Usuario)

            # Obtener partidos de la jornada y que ambos entrenadores pertenezcan al grupo especificado
            partidos = session.query(
                GestorSQL.Calendario,
                func.coalesce(UsuarioAlias1.nombreAMostrar, UsuarioAlias1.nombre_bloodbowl).label('nombre_coach1'),
                func.coalesce(UsuarioAlias2.nombreAMostrar, UsuarioAlias2.nombre_bloodbowl).label('nombre_coach2'),
                GestorSQL.Partidos.resultado1,
                GestorSQL.Partidos.resultado2,
                UsuarioAlias1.raza.label('raza1'),
                UsuarioAlias2.raza.label('raza2')
            ).\
            filter(GestorSQL.Calendario.jornada == jornada).\
            join(GestorSQL.Partidos, GestorSQL.Calendario.partidos_idPartidos == GestorSQL.Partidos.idPartidos).\
            join(UsuarioAlias1, GestorSQL.Calendario.coach1 == UsuarioAlias1.idUsuarios).\
            filter(UsuarioAlias1.grupo == grupo).\
            join(UsuarioAlias2, GestorSQL.Calendario.coach2 == UsuarioAlias2.idUsuarios).\
            filter(UsuarioAlias2.grupo == grupo).all()

            for partido in partidos:
                entrenadores[str(indice)] = partido.nombre_coach1
                resultados[str(indice)] = partido.resultado1
                razas[str(indice)] = partido.raza1
                indice += 1
                entrenadores[str(indice)] = partido.nombre_coach2
                resultados[str(indice)] = partido.resultado2
                razas[str(indice)] = partido.raza2
                indice += 1

            # Crear imagen
            ruta_imagen = Imagenes.crear_imagen("jornada", grupo, entrenadores=entrenadores, resultados=resultados, jornadas=jornadaDict, razas=razas)

            imagenes.append(ruta_imagen)

            # Cerrar sesión
            session.close()
        except Exception as e:
            await ctx.send(f"Ocurrió un error al crear la imagen del grupo {grupo}: {str(e)}")

    # Dividir las imágenes en tres mensajes
    await canal.send(f"Jornada {str(jornada)}")
    await canal.send(f"Oro:")
    files_part1 = [discord.File(open(ruta, 'rb')) for ruta in imagenes[:4]]
    await canal.send(files=files_part1)

    await canal.send(f"Plata:")
    files_part2 = [discord.File(open(ruta, 'rb')) for ruta in imagenes[4:9]]
    await canal.send(files=files_part2)

    await canal.send(f"Bronce:")
    files_part3 = [discord.File(open(ruta, 'rb')) for ruta in imagenes[9:]]
    await canal.send(files=files_part3)

    # Eliminar las imágenes después de un tiempo
    for ruta in imagenes:
        threading.Timer(10, lambda ruta=ruta: Imagenes.eliminar_imagen(ruta)).start()



@bot.command(name="enviarImagenJornadaVacia")
@commands.has_any_role('Moderadores', 'Administrador', 'Comisario')
async def enviar_imagen_jornada_vacia(ctx, jornada: int, canal_id: int):
    canal = bot.get_channel(canal_id)
    if not canal:
        await ctx.send(f"No se pudo encontrar el canal con ID {canal_id}")
        return

    imagenes = []
    for grupo in range(1, 16):
        try:
            Session = sessionmaker(bind=GestorSQL.conexionEngine())
            session = Session()
            entrenadores = {}
            resultados = {}
            razas = {}
            jornadaDict = {'0': str(jornada)}
            indice = 0

            UsuarioAlias1 = aliased(GestorSQL.Usuario)
            UsuarioAlias2 = aliased(GestorSQL.Usuario)

            # Obtener partidos de la jornada y que ambos entrenadores pertenezcan al grupo especificado
            partidos = session.query(
                GestorSQL.Calendario,
                func.coalesce(UsuarioAlias1.nombreAMostrar, UsuarioAlias1.nombre_bloodbowl).label('nombre_coach1'),
                func.coalesce(UsuarioAlias2.nombreAMostrar, UsuarioAlias2.nombre_bloodbowl).label('nombre_coach2'),
                UsuarioAlias1.raza.label('raza1'),
                UsuarioAlias2.raza.label('raza2')
            ).\
            filter(GestorSQL.Calendario.jornada == jornada).\
            join(UsuarioAlias1, GestorSQL.Calendario.coach1 == UsuarioAlias1.idUsuarios).\
            filter(UsuarioAlias1.grupo == grupo).\
            join(UsuarioAlias2, GestorSQL.Calendario.coach2 == UsuarioAlias2.idUsuarios).\
            filter(UsuarioAlias2.grupo == grupo).all()

            for partido in partidos:
                entrenadores[str(indice)] = partido.nombre_coach1
                resultados[str(indice)] = "-"
                razas[str(indice)] = partido.raza1
                indice += 1
                entrenadores[str(indice)] = partido.nombre_coach2
                resultados[str(indice)] = "-"
                razas[str(indice)] = partido.raza2
                indice += 1

            # Crear imagen
            ruta_imagen = Imagenes.crear_imagen("jornada", grupo, entrenadores=entrenadores, resultados=resultados, jornadas=jornadaDict, razas=razas)

            imagenes.append(ruta_imagen)

            # Cerrar sesión
            session.close()
        except Exception as e:
            await ctx.send(f"Ocurrió un error al crear la imagen del grupo {grupo}: {str(e)}")

    # Dividir las imágenes en tres mensajes
    await canal.send(f"Jornada {str(jornada)}")
    await canal.send("Oro:")
    files_part1 = [discord.File(open(ruta, 'rb')) for ruta in imagenes[:4]]
    await canal.send(files=files_part1)

    await canal.send("Plata:")
    files_part2 = [discord.File(open(ruta, 'rb')) for ruta in imagenes[4:9]]
    await canal.send(files=files_part2)

    await canal.send("Bronce:")
    files_part3 = [discord.File(open(ruta, 'rb')) for ruta in imagenes[9:]]
    await canal.send(files=files_part3)

    # Eliminar las imágenes después de un tiempo
    for ruta in imagenes:
        threading.Timer(10, lambda ruta=ruta: Imagenes.eliminar_imagen(ruta)).start()

def desempatar(session, clasificacion, jornada, grupo):
    orden_final = []
    from collections import defaultdict
    puntos_dict = defaultdict(list)
    for idx, fila in enumerate(clasificacion):
        # Asegúrate de que incluso las filas sin desempate tengan un valor inicial para victorias
        puntos_dict[fila[6]].append((idx, fila, 0))  # Agregar 0 como valor inicial para victorias

    for puntos, entrenadores in puntos_dict.items():
        if len(entrenadores) > 1:
            entrenadores = resolver_empates(session, entrenadores, jornada, grupo)
        # Cada 'entrenador' ahora es una tupla (idx, fila, victorias)
        orden_final.extend(entrenadores)

    # Ordenar por puntos y luego índice original, asegurando que el desempaquetado sea correcto
    orden_final.sort(key=lambda x: (-x[1][6], -x[2], x[0]))  # Ordenar por pts, victorias en enfrentamientos directos, e índice original
    return [x[1] for x in orden_final]

def resolver_empates(session, entrenadores, jornada, grupo):
    for i in range(len(entrenadores)):
        for j in range(i + 1, len(entrenadores)):
            nombre1 = entrenadores[i][1][0]  # nombre_bloodbowl del entrenador i
            nombre2 = entrenadores[j][1][0]  # nombre_bloodbowl del entrenador j

            # Buscar el id de los usuarios basado en el nombre_bloodbowl
            id1 = session.query(GestorSQL.Usuario.idUsuarios).filter(GestorSQL.Usuario.nombre_bloodbowl == nombre1).scalar()
            id2 = session.query(GestorSQL.Usuario.idUsuarios).filter(GestorSQL.Usuario.nombre_bloodbowl == nombre2).scalar()

            # Recuperar partidos entre estos dos entrenadores hasta la jornada dada desde Calendario
            partidos_y_calendarios = session.query(GestorSQL.Partidos, GestorSQL.Calendario).join(
                GestorSQL.Calendario,
                GestorSQL.Calendario.partidos_idPartidos == GestorSQL.Partidos.idPartidos
            ).filter(
                GestorSQL.Calendario.jornada <= jornada,
                or_(
                    and_(GestorSQL.Calendario.coach1 == id1, GestorSQL.Calendario.coach2 == id2),
                    and_(GestorSQL.Calendario.coach1 == id2, GestorSQL.Calendario.coach2 == id1)
                )
            ).all()

            # for partido, calendario in partidos_y_calendarios:
            #     print(f"Partido ID: {partido.idPartidos}, Resultado: {partido.resultado1} - {partido.resultado2}")

            # Calcular victorias basadas en los resultados de los partidos
            victorias_id1, victorias_id2 = 0, 0
            for partido, calendario in partidos_y_calendarios:
                if (partido.resultado1 > partido.resultado2 and calendario.coach1 == id1) or (partido.resultado2 > partido.resultado1 and calendario.coach2 == id1):
                    victorias_id1 += 1
                elif (partido.resultado1 > partido.resultado2 and calendario.coach2 == id1) or (partido.resultado2 > partido.resultado1 and calendario.coach1 == id1):
                    victorias_id2 += 1
            

            # print(f"Después de calcular, victorias para {nombre1} (ID: {id1}): {victorias_id1}, victorias para {nombre2} (ID: {id2}): {victorias_id2}")
            
            # Actualizar los datos de los entrenadores con las victorias
            entrenadores[i] = (entrenadores[i][0], entrenadores[i][1], victorias_id1)
            entrenadores[j] = (entrenadores[j][0], entrenadores[j][1], victorias_id2)

    return entrenadores


def obtener_clasificacion(jornada, grupo, session=None):
    """Obtiene la clasificación de un grupo para una jornada aplicando el
    desempate por enfrentamientos directos."""
    conn = mysql.connector.connect(
        host="localhost",
        user=os.getenv('UsuBD'),
        password=os.getenv('PassBD'),
        database="ButterCup"
    )
    cursor = conn.cursor()
    cursor.callproc('clasificacionGeneral', [jornada, grupo])

    clasificacion = []
    for result in cursor.stored_results():
        clasificacion.extend(result.fetchall())

    cursor.close()
    conn.close()

    close_session = False
    if session is None:
        Session = sessionmaker(bind=GestorSQL.conexionEngine())
        session = Session()
        close_session = True

    clasificacion = desempatar(session, clasificacion, jornada, grupo)

    if close_session:
        session.close()

    return clasificacion


@bot.command(name='actconfig')
@commands.has_any_role('Moderadores', 'Administrador', 'Comisario')
async def actualizar_configuracion(ctx):
    # Verifica si el mensaje tiene attachments
    if ctx.message.attachments:
        encontrado = False
        for attachment in ctx.message.attachments:
            # Comprueba si el archivo se llama 'configuracion.json'
            if attachment.filename == 'configuracion.json':
                encontrado = True
                # Descarga y guarda el archivo
                await attachment.save('configuracion.json')
                await ctx.send('Archivo de configuración actualizado correctamente.')
                break
        
        if not encontrado:
            # Si se encontraron attachments pero ninguno es 'configuracion.json'
            await ctx.send('No se encontró un archivo `configuracion.json` en los attachments.')
    else:
        # Si no hay attachments en el mensaje
        await ctx.send('No hay archivos adjuntos en el mensaje.')
  

@bot.command(name="AgregarVista")
@commands.has_any_role('Moderadores', 'Administrador', 'Comisario')
async def agregar_vista(ctx, message_id: int):
    # Intenta obtener el mensaje objetivo y añadirle la vista
    try:
        # Obten el canal y luego el mensaje usando el ID proporcionado
        message = await ctx.channel.fetch_message(message_id)
        # Edita el mensaje para añadir la vista
        await message.edit(view=UtilesDiscord.SpinButtonsView())
        # Borra el mensaje que invocó el comando
        await ctx.message.delete()
        # Envía confirmación y luego borra ese mensaje después de 20 segundos
        confirmation_message = await ctx.send("Vista añadida correctamente al mensaje.")
        await confirmation_message.delete(delay=20)
    except discord.NotFound:
        await ctx.send("Mensaje no encontrado.", delete_after=20)
    except Exception as e:
        await ctx.send(f"Error: {e}", delete_after=20)

@bot.command(name="AgregaMensajeSpin")
@commands.has_any_role('Moderadores', 'Administrador', 'Comisario')
async def AgregaMensajeSpin(ctx):
    mensaje =await ctx.send("'El spin está **LIBRE**'")
    await ctx.send("¡Úsame para Spinear!", view=UtilesDiscord.SpinButtonsView())
    UtilesDiscord.UsuarioSpin = None
    await ctx.message.delete()
   

@bot.tree.command(name="dado", description="Lanza un dado!")
async def roll_dice(interaction: discord.Interaction, caras: int = 6, dados: int = 1):
  
    if dados > 25:
        await interaction.response.send_message("No tires más de 25 dados.")
        return
    if caras < 1 or dados < 1:
        await interaction.response.send_message("Los números deben ser mayores que 0.")
        return
    results = [random.randint(1, caras) for _ in range(dados)]
    results_str = ', '.join(str(r) for r in results)
    sum_of_results = sum(results)
    dice_icons = '🎲' * min(dados, 25)  # Para no sobrecargar el mensaje con demasiados iconos
    await interaction.response.send_message(f"{dice_icons} Has sacado: {results_str}. Total: {sum_of_results}")


@bot.command(name="EnviarInvitacion")
@commands.has_any_role('Moderadores', 'Administrador', 'Comisario')
async def enviarInvitacion(ctx):
    Session = sessionmaker(bind=GestorSQL.conexionEngine())
    with Session() as session:
        usuarios = session.query(GestorSQL.Usuario)\
            .join(GestorSQL.Grupo, GestorSQL.Usuario.grupo == GestorSQL.Grupo.id_grupo)\
            .all()
        
        for usuario in usuarios:
            # Filtrar solo los del mismo grupo, excluyéndote a ti
            compañeros = [
                u for u in usuarios 
                if u.grupo == usuario.grupo and u.idUsuarios != usuario.idUsuarios
            ]
            # Construir lista de "nombre_discord (nombre_bbowl, raza)"
            lista_compañeros = [
                f"{c.nombre_discord} ({c.nombre_bloodbowl or 'BBowl no asignado'}, {c.raza or 'raza no asignada'})"
                for c in compañeros
            ]
            # Formatear con comas y 'y'
            if len(lista_compañeros) > 1:
                nombres_compañeros = ', '.join(lista_compañeros[:-1])
                nombres_compañeros += ' y ' + lista_compañeros[-1]
            elif lista_compañeros:
                nombres_compañeros = lista_compañeros[0]
            else:
                nombres_compañeros = "No tienes compañeros en este grupo."
            
            mensaje = f"""¡Bienvenido a la Sexta Edición de la Butter Cup!

Se te han asignado {finalFraseRaza(usuario.raza)}

Tus compañeros esta temporada serán {nombres_compañeros}.

Se creará un canal automáticamente durante la próxima hora donde podrás quedar con tu primer adversario. ¡Recuerda que antes de jugar tienes que pasarte por el canal de Spin para no ser emparejado con otros jugadores! De todas maneras esto lo explicaremos más detalladamente en el canal de la quedada.

¡Te esperamos!
"""
            try:
                user = await bot.fetch_user(usuario.id_discord)
                if user:
                    await user.send(mensaje)
                    await ctx.send(f"Enviada invitación a {user.name}#{user.discriminator}")
            except Exception as e:
                print(f"No se pudo enviar el mensaje a {usuario.id_discord}: {e}")
            
            # Pausa breve para no spamear
            await asyncio.sleep(10)

@bot.command(name="informarResultados")
@commands.has_any_role('Moderadores', 'Administrador', 'Comisario')
async def informarResultados(ctx,usuario_id: int = None):
    Session = sessionmaker(bind=GestorSQL.conexionEngine())
    with Session() as session:
        query = session.query(GestorSQL.Usuario).join(GestorSQL.Grupo, GestorSQL.Usuario.grupo == GestorSQL.Grupo.id_grupo).filter(GestorSQL.Usuario.idUsuarios != 3)
        if usuario_id is not None:
            query = query.filter(GestorSQL.Usuario.idUsuarios == usuario_id)
        usuarios = query.all()
        

        for usuario in usuarios:           
            grupo_id = usuario.grupo_grupo.id_grupo  
            grupo_nombre = usuario.grupo_grupo.nombre_grupo  
            # print(f"id:{usuario.idUsuarios} grupo:{grupo_id} nombre_grupo:{grupo_nombre}")
            
            nombre_para_resultados = usuario.nombreAMostrar if usuario.nombreAMostrar else usuario.nombre_bloodbowl

            resultado = consultaResultados(session, nombre_para_resultados, 10, grupo_id, grupo_nombre)
            puesto, grupo, dinero = resultado  
            # print(f"puesto:{puesto} grupo:{grupo} dinero:{dinero}")
            if puesto in [1, 2,3, 4]:
                mensaje = f"Felicidades {usuario.nombre_discord}, ¡has quedado {puesto}º en el grupo {grupo}! Eres uno de los mejores.\n\n-----------------------------------------\n" \
                          "Has clasificado para los play-off de grupo. Las reglas son las siguientes: \n"+reglasPLayOffGrupo()
            elif puesto in [5, 6]:               
                mensaje = f"{usuario.nombre_discord}, has quedado {puesto}º en tu grupo. Es momento de curar de las heridas y volver más fuerte la próxima temporada. Recuerda sacrificar unos snotling a Nuffle ^^."
                if grupo == "Oro":
                    mensaje += " Descenderás a la liga de Plata. Recuerda que la próxima edición comienza el 27/04/2026 ^^"
                elif grupo == "Plata":
                    mensaje += " Descenderás a la liga de Bronce. Recuerda que la próxima edición comienza el 27/04/2026 ^^"
                
            try:
                user = await bot.fetch_user(usuario.id_discord)
                if user:
                    await user.send(mensaje)
                    await ctx.send(f"Mensaje enviado a {user.name}#{user.discriminator}")
                    actualizacion2026 = "\n-----------------------------------------\nPor último, las reglas para el traslado de equipos a Warhammer Blood bowl se están aún discutiendo. Avisaremos por el general tan pronto como tengamos noticias. \n-----------------------------------------\n"
                    await user.send(actualizacion2026)
                    # reformaDinero = "\n-----------------------------------------\nPor último, las reglas para las reformas del equipo son:\n" + reglasReforma(dinero) + "\n-----------------------------------------"
                    # await user.send(reformaDinero)
            except Exception as e:
                print(f"No se pudo enviar el mensaje a {usuario.id_discord}: {e}")
                
            await asyncio.sleep(1)

def consultaResultados(session, usuario, jornada, grupo, grupo_nombre):
    clasificacion = obtener_clasificacion(jornada, grupo, session)

    # Encontrar el puesto del usuario y calcular el dinero
    puesto = 1
    dinero = 0
    grupo_nombre_corto = ""
    for fila in clasificacion:
        if fila[0] == usuario:
            # Calcular el dinero
            victorias = fila[2]
            empates = fila[3]
            derrotas = fila[4]
            dinero = 1000000 + 30000 * victorias + 10000 * empates + 5000 * derrotas
            
            # Extraer la primera palabra del nombre del grupo
            grupo_nombre_corto = grupo_nombre[:-1] 
            break
        puesto += 1

    return puesto, grupo_nombre_corto, dinero
            
def reglasPLayOffGrupo():
   reglas = "1- Puedes modificar el equipo según las reglas del juego hasta el día anterior a la fecha del primer partido.\n"\
   "2- Una vez realizados los cambios el equipo permanecerá inmutable durante el periodo de play-off.\n"\
   "3- Se debe avisar a los commisarios mandando una imagen del estado del equipo final al hilo https://discord.com/channels/405763002768424970/1480291295502012536.\n"\
   "4- Se podrá consultar el calendario y los emparejamientos en el discord https://discord.com/channels/405763002768424970/1349451633418960947.\n"\
   "5- El bot se encargará de crear canales cada vez que las jornadas terminen, las quedadas se harán de la misma forma que en la liga regular."
   return reglas

def reglasPLayOffTicket():
   reglas = "1- Debes crear un equipo custom clónico según las reglas del juego y agregarlo a la competición Ticket ButterCup contraseña TicketButtercup2024. PUEDE ser diferente del usado en los play-off regulares\n"\
   "2- Una vez inscrito el equipo permanecerá inmutable durante el periodo de play-off.\n"\
   "3- Se debe avisar a Pikoleto para que guarde una instantanea del estado del equipo.\n"\
   "4- Se podrá consultar el calendario y los emparejamientos en el discord.\n"\
   "5- El bot se encargará de crear canales cada vez que las jornadas terminen, las quedadas se harán de la misma forma que en la liga regular."
   return reglas

def reglasReforma(dinero):
   reglas = "Tienes la opción de mantener este equipo para futuras ediciones de la ButterCup (No necesariamente para la siguiente). Si vas a borrarlo porque han ofendido a Nuffle y merecen caer en el olvido para de leer aquí, pero si a tus jugadores les espera un brillante un futuro podrás hacerlo siguiendo las reglas de recompra que están en el apartado información y reglamento pero que se resumen en:\n"\
   "1- Tienes un total de "+ str(dinero) +" para recomprar los jugadores de tu equipo. El equipo sobre el que se harán las compras será el usado para los play-off de grupo de haber clasificado o el actual de no hacerlo.\n"\
   "2- Tu equipo debe tener al menos 11 jugadores.\n"\
   "3- Los jugadores pueden ser nuevos o pueden recomprarse.\n"\
   "4- Recomprar un jugador tendrá un coste igual a su coste actual + 20.000. Al recomprarlo se perderá toda la experiencia que actualmente tenga. Si se quiere mantener esa experiencia se pueden pagar 20.000 adicionales si no puede comprar una habilidad principal o 40.000 si puede.\n"\
   "5- NO se pueden vender RR.\n"\
   "6- Cuando decidas tu equipo final, antes de modificar nada, contacta con Pikoleto para que de el visto bueno."
   return reglas

def finalFraseRaza(raza):
    frases = {
        "Alianza V. Mundo": "la variada **Alianza del Viejo Mundo**, demuestra la fuerza en la unidad y la estrategia sobre la pura fuerza. Suerte Charguet, nadie más ha elegido esto asi que puedo poner una dedicatoria personalizada en esta raza ^^",
        "Amazonas": "las poderosas **Amazonas**, esquiva a esos inútiles y estallales donde menos se lo esperen. Practicamente imposibles de derribar conseguirán la victoria al grito de ¡MUERTE POR KIKI!",
        "Caos Elegido": "los temibles **Elegidos del Caos**, siembra el terror y la desolación en el corazón de tus enemigos.",
        "Enanos del Caos": "los implacables **Enanos del Caos**, atrinchérate con tus barbas acorazadas y hornos humeantes mientras tus hobgoblins roban balones al grito de ¡Gloria a Hashut!",
        "Elfos Oscuros": "los sanguinarios **Elfos Oscuros**, utiliza tu astucia y llévale los corazones de tus rivales a Morathi.",
        "Elfos Silvanos": "los ágiles **Elfos Silvanos**, domina el campo con una gracia y velocidad inigualables.",
        "Enanos": "los resistentes **Enanos**, deja que tu solidez defensiva y tu poderío ofensivo hablen por ti en el campo.",
        "Hombres Lagarto": "los ágiles y fuertes **Hombres Lagarto**, no tienes nada que temer ya que el Gran Plan te guia.",
        "Horror Nigromántico":"los **Horrores nigrománticos** directamente desde una pelicula de miedo de los 80, aúlla a la luna con tus lobos mientras tus golems paran a un equipo entero.",
        "Humanos": "lo versátiles **Humanos**, adapta tu estrategia a cualquier rival y muestra la habilidad de jugar en cualquier posición.",
        "Inframundo": "el temible equipo del **Irikumundo**, usa tus trucos y mutaciones para que no quede nadie Irikum.",
        "Nobleza Imperial": "la distinguida **Nobleza Imperial**, utiliza tu elegancia y tácticas refinadas para ganar tus partidos.",
        "No muertos": "los terroríficos **No Muertos**, haz que tus rivales teman enfrentarse a ti tanto en vida como en muerte.",
        "Nurgle": "los repugnantes seguidores de **Nurgle**, usa tu resistencia y habilidades únicas para soportar cualquier cosa mientras pudres a tus oponentes.",
        "Nórdicos": "los furiosos **Nórdicos**. Haz que se le encoja el escroto de frío a tus rivales con tus furias mientras las valkirias mueven el balón y los ágiles gorrinos reparten cruzcampo.",
        "Orcos": "los poderosos Orcos, grita WAAAAGH! con ellos mientras destrozas a tus rivales.",
        "Orcos negros": "los imponentes **Orcos Negros**, utiliza tu fuerza bruta para dominar el campo de juego mientras tus goblins rematan a tus rivales.",
        "Renegados": "el variopinto equipo de **Renegados**, une a los marginados de todos los rincones para formar un equipo único.",
        "Skaven": "los rápidos y traicioneros **Skaven**, corre por el campo sembrando caos y aprovechando cualquier debilidad.",
        "Stunty":"los epiquisímos **Stunty**, el tamaño no importa y vas a demostrarselo a esos abusones con tu equipo. Estalla a esos grandullones de maneras que nunca han imaginado.",
        "Unión Élfica": "la rapidsíma **Unión Élfica**, humilla a tus enemigos con tu juego de balón y ríete de ellos mientras intentan atraparte.",
        "Vampiros": "los siniestros **Vampiros**, domina a tus rivales con tu hipnótica presencia y sacia tu sed con cada touchdown.",
        "Khorne": "los sedientos de sangre seguidores de **Khorne**, arrasa el campo al grito de ¡SANGRE PARA EL DIOS DE LA SANGRE, CRÁNEOS PARA EL TRONO DE KHORNE!"
    }


    # Devuelve el mensaje asociado a la raza, o un mensaje genérico si la raza no está en el diccionario.
    return frases.get(raza, "una raza ("+raza+") no identificada, verifica el nombre e inténtalo de nuevo.")
    

@bot.command(name="dinero")
async def dinero(ctx, nombre_discord: str):
    Session = sessionmaker(bind=GestorSQL.conexionEngine())
    with Session() as session:
        # Buscar el usuario por nombre_discord
        usuario = session.query(GestorSQL.Usuario).join(GestorSQL.Grupo, GestorSQL.Usuario.grupo == GestorSQL.Grupo.id_grupo).filter(GestorSQL.Usuario.nombre_discord == nombre_discord).first()

        if usuario is None:
            await ctx.send(f"No se encontró un usuario con el nombre de Discord: {nombre_discord}")
            return

        grupo_id = usuario.grupo_grupo.id_grupo  
        grupo_nombre = usuario.grupo_grupo.nombre_grupo  
        nombre_para_resultados = usuario.nombreAMostrar if usuario.nombreAMostrar else usuario.nombre_bloodbowl

        resultado = consultaResultados(session, nombre_para_resultados, 10, grupo_id, grupo_nombre)
        puesto, grupo, dinero = resultado
        
        mensaje = f"Usuario: {nombre_discord}\nGrupo: {grupo}\nPosición: {puesto}\nDinero: {dinero}"

        await ctx.send(mensaje)


#TODO cambiar a SQL
async def desuscribir(id_discord):
    sheet = GestionExcel.sheetIds  # Asumiendo que esta es la hoja de cálculo correcta
    records = sheet.get_all_records()

    for index, record in enumerate(records, start=2):  # Empieza en 2 para ajustar el índice a las filas de Sheets
        discord_id = record.get("id_discord")
        if str(discord_id) == str(id_discord):  # Compara como string por si hay discrepancias en el formato
            sheet.update_cell(index, 6, "Borrar")
            break  # Sale del ciclo una vez que encuentra y actualiza el registro correcto
         
    pass

@bot.event
async def on_raw_reaction_add(payload):
    message = await bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
    if message.id == 1280103345633234987:  
         await Inscripcion.handle_registration(payload.member)
    if message.id == 1280113171822284884:    
        boton = discord.ui.Button(label="Empezar encuesta", style=discord.ButtonStyle.green)
        boton.callback = Encuesta.primera_pregunta
        view = discord.ui.View()
        view.add_item(boton)
        user = await bot.fetch_user(payload.user_id)

        await user.send(f"Hola <@{user.id}> ¿Te gustaría participar en una encuesta corta para que sepamos tu opinión sobre la Butter Cup?", view=view)



@bot.event
async def on_reaction_add(reaction, user):    
    # Ignora las reacciones del propio bot
    if user == bot.user:
        return
    # Verificar si la reacción es a un mensaje de DM, si el mensaje fue enviado por el bot, y si la reacción es la correcta
    if reaction.message.guild is None and reaction.emoji == "❌" and reaction.message.author == bot.user:
        await desuscribir(user.id)
        
    # if reaction.message.id == ID_DEL_MENSAJE_ESPECIFICO:
    #     await handle_registration(user)


@bot.tree.command(name='fecha', description='Establece una fecha y hora para la cita')
async def fecha(interaction: discord.Interaction, dia: int, mes: int, hora: int, minuto: int = 0):
    # Obtén el ID del canal donde se ejecutó el comando
    id_canal = interaction.channel_id
    
    Session = sessionmaker(bind=GestorSQL.conexionEngine())
    with Session() as session:
        registro = session.query(GestorSQL.Calendario).filter(GestorSQL.Calendario.canalAsociado == id_canal).first()

        if registro is None:
            registro = session.query(GestorSQL.PlayOffsBronce).filter(GestorSQL.PlayOffsBronce.canalAsociado == id_canal).first()
            if registro is None:
                registro = session.query(GestorSQL.PlayOffsPlata).filter(GestorSQL.PlayOffsPlata.canalAsociado == id_canal).first()
                if registro is None:
                    registro = session.query(GestorSQL.PlayOffsOro).filter(GestorSQL.PlayOffsOro.canalAsociado == id_canal).first()
                    if registro is None:
                        registro = session.query(GestorSQL.Ticket).filter(GestorSQL.Ticket.canalAsociado == id_canal).first()
                        if registro is None:
                            await interaction.response.send_message("Este no es un canal de quedadas 😡", ephemeral=True)
                            return

        try:
            punto = ""
            tz = tzlocal.get_localzone()
            fecha_nueva = datetime(year=datetime.now().year, month=mes, day=dia, hour=hora, minute=minuto, tzinfo=tz)
            if registro.fechaFinal:
                fecha_final =registro.fechaFinal.astimezone(tz)
            # Comprueba si la fecha es menor que fechaFinal, si existe fechaFinal
            if registro.fechaFinal and fecha_nueva >= fecha_final:
                # Encuentra el rol de 'Comisario'
                comisario_role = discord.utils.find(lambda r: r.name == 'Comisario', interaction.guild.roles)
                if comisario_role:
                    # Menciona al rol 'Comisario' con un mensaje
                    await interaction.channel.send(f"{comisario_role.mention} ¡Ayuda! Hay algo raro con las fechas.")
                punto = "🟡"
            else:
                punto = "🟢"

            registro.fecha = fecha_nueva
            session.commit()

            timestamp = int(fecha_nueva.timestamp())
            fecha_espana = fecha_nueva.astimezone(ZoneInfo("Europe/Madrid"))
            hora_espana = fecha_espana.strftime("%H:%M")
            dia_espana = fecha_espana.strftime("%d/%m/%Y")
            response_message = (
                f"Se ha concertado la cita para <t:{timestamp}:F>, "
                f"que corresponde a las {hora_espana} del día {dia_espana} en España."
            )
            await interaction.response.send_message(response_message)
            
            #de momento no cambio nombre a canales porque se pone triste discord
            #await interaction.channel.edit(name=punto + interaction.channel.name)
        except ValueError as e:
            await interaction.response.send_message(f"Error al establecer la fecha: {str(e)}", ephemeral=True) 
 
@bot.tree.command(name='preferenciahorario', description='Establece un horario favorito para darle una idea a tus oponentes de cuando podrás quedar')
async def preferencias_horario(interaction: discord.Interaction, horario: str):
    Session = sessionmaker(bind=GestorSQL.conexionEngine())
    with Session() as session:
        usuario = session.query(GestorSQL.Usuario).filter_by(id_discord=interaction.user.id).first()

        if usuario:
            # Si el usuario existe, busca su preferencia de horario
            preferencia = session.query(GestorSQL.PreferenciasFecha).filter_by(idUsuarios=usuario.idUsuarios).first()
            if preferencia:
                # Si la preferencia ya existe, actualízala
                preferencia.preferencia = horario
            else:
                # Si no existe, crea una nueva preferencia
                nueva_preferencia = GestorSQL.PreferenciasFecha(preferencia=horario, idUsuarios=usuario.idUsuarios)
                session.add(nueva_preferencia)

            session.commit() 

            await interaction.response.send_message(f"Tu preferencia de horario ha sido actualizada a: {horario}", ephemeral=True)
        else:
            await interaction.response.send_message("No se pudo encontrar tu usuario en la base de datos.", ephemeral=True)            

@bot.command(name="PruebaBD")
@commands.has_any_role('Moderadores', 'Administrador', 'Comisario')
async def PruebaBD(ctx):
    session = sessionmaker(bind=GestorSQL.conexionEngine())()

    # Obtener todos los usuarios
    usuarios = session.query(GestorSQL.Usuario).all()

    # Obtener los nombres de los atributos de la clase Usuario, excluyendo métodos mágicos y otros no deseados
    atributos = [attr for attr in dir(GestorSQL.Usuario) if not attr.startswith('_') and not callable(getattr(GestorSQL.Usuario, attr))]
    atributos.remove('metadata')  # SQLAlchemy añade 'metadata' que no es parte de los campos de la base de datos
    atributos.remove('registry')
    
    # Encabezados para la tabla
    encabezados = atributos
    # Calcular el ancho máximo de cada columna
    ancho_columnas = [max(len(str(getattr(u, attr) or '')) for u in usuarios) for attr in atributos]
    # Ajustar el ancho para los encabezados si son más largos que los datos
    ancho_columnas = [max(len(encabezado), ancho) for encabezado, ancho in zip(encabezados, ancho_columnas)]

    # Crear la cabecera de la tabla con las cabeceras alineadas
    cabecera = ' '.join(encabezado.ljust(ancho) for encabezado, ancho in zip(encabezados, ancho_columnas))

    # Crear las filas de la tabla
    filas = [cabecera]
    for i in range(min(5, len(usuarios))):  # Esto asegura que no excedamos la cantidad de usuarios
        usuario = usuarios[i]        
        fila = ' '.join(str(getattr(usuario, attr) or '').ljust(ancho) for attr, ancho in zip(encabezados, ancho_columnas))
        filas.append(fila)

    # Unir todas las filas en una cadena de texto
    tabla = '\n'.join(filas)

    # Enviar el mensaje formateado como bloque de código
    await ctx.send(f"```{tabla}```")

    session.close()
    
@bot.tree.command(name="ultimosspins")
@commands.has_any_role('Moderadores', 'Administrador', 'Comisario')
async def obtener_spins_recientes(interaction: discord.Interaction, minutos: int):
    Session = sessionmaker(bind=GestorSQL.conexionEngine())
    session = Session()
    
    # Calcular el momento de tiempo desde el cual queremos obtener los registros
    tiempo_desde = datetime.utcnow() - timedelta(minutes=minutos)
    
    try:
        # Realizar la consulta filtrando por fecha
        resultados = session.query(GestorSQL.Spin.fecha, GestorSQL.Spin.user, GestorSQL.Spin.tipo).\
            filter(GestorSQL.Spin.fecha >= tiempo_desde).\
            all()
        
        # Formatear los resultados en Markdown
        tabla_markdown = "```| Fecha (Europe/Madrid) | Usuario | Acción |\n|----------------------|---------|--------|"
        for fecha, usuario, tipo in resultados:
            fecha_madrid = fecha.replace(tzinfo=ZoneInfo('UTC')).astimezone(ZoneInfo('Europe/Madrid')) if fecha.tzinfo is None else fecha.astimezone(ZoneInfo('Europe/Madrid'))
            tabla_markdown += f"\n| {fecha_madrid.strftime('%Y-%m-%d %H:%M:%S')} | {usuario} | {tipo} |"
        
        tabla_markdown += "```"
        
        await interaction.response.send_message(tabla_markdown)
    except Exception as e:
        print(f"Error al consultar la tabla Spin: {e}")
        await interaction.response.send_message("```Error al realizar la consulta.```")
    finally:
        session.close()
        

@bot.command(name="crearGrupos")
@commands.has_any_role('Moderadores', 'Administrador','Comisario')
async def crear_grupos(ctx):
    Session = sessionmaker(bind=GestorSQL.conexionEngine())
    session = Session()  
    
    try:
        # Obtén la lista de grupos
        grupos = session.query(GestorSQL.Grupo).all()
        for grupo in grupos:
            usuarios = session.query(GestorSQL.Usuario).filter(GestorSQL.Usuario.grupo == grupo.id_grupo).all()
               
            if (grupo.id_grupo) == 0:
                continue

            if len(usuarios) == 0:
                continue
            
            if len(usuarios) != 6:
                await ctx.send(f"El grupo {grupo.id_grupo} no tiene 6 usuarios, tiene {len(usuarios)}.")
                return

            random.shuffle(usuarios)

            def generar_partidos(n):
                equipos = list(range(n))
                if n % 2:
                    equipos.append(None)
                jornadas = []
                m = len(equipos)
                for _ in range(m - 1):
                    ronda = []
                    for j in range(m // 2):
                        a = equipos[j]
                        b = equipos[m - 1 - j]
                        if a is not None and b is not None:
                            ronda.append((a, b))
                    equipos.insert(1, equipos.pop())
                    jornadas.append(ronda)
                return jornadas

            jornadas_ida = generar_partidos(len(usuarios))
            random.shuffle(jornadas_ida)
            jornadas_vuelta = [[(b, a) for (a, b) in jornada] for jornada in jornadas_ida]
            jornadas = jornadas_ida + jornadas_vuelta

            enfrentamientos = {}
            for jornada in jornadas:
                for a, b in jornada:
                    par = tuple(sorted((usuarios[a].idUsuarios, usuarios[b].idUsuarios)))
                    enfrentamientos[par] = enfrentamientos.get(par, 0) + 1
            if any(contador != 2 for contador in enfrentamientos.values()):
                await ctx.send(f"Error al generar el calendario del grupo {grupo.id_grupo}")
                session.rollback()
                continue

            for i, jornada in enumerate(jornadas):
                for partido in jornada:
                    fecha_final = datetime(2026, 1, 4, 23, 59) + timedelta(weeks=i)
                    nuevo_partido = GestorSQL.Calendario(
                        jornada=i+1,
                        canalAsociado=0,  # Asume un valor por defecto o ajusta según necesidad
                        coach1=usuarios[partido[0]].idUsuarios,
                        coach2=usuarios[partido[1]].idUsuarios,
                        fechaFinal=fecha_final
                    )
                    session.add(nuevo_partido)
                session.commit()
            
        await ctx.send("Grupos y partidos creados correctamente.")
    except Exception as e:
        await ctx.send(f"Error al crear grupos y partidos: {str(e)}")
    finally:
        session.close()


@bot.tree.command(name='proximos_eventos', description='Avisa de los próximos partidos')
async def eventos(interaction: discord.Interaction, canal_destino_id: str = None):
    # Determinar si el mensaje debe ser enviado de forma privada o pública
    respuesta_privada = str(interaction.user.id) not in maestros
    await func_proximos_eventos(bot, interaction.user, canal_destino_id if canal_destino_id else interaction.channel_id, respuesta_privada)
    await interaction.response.send_message("Enviado",ephemeral=True)


def obtener_icono_grupo(nombre_grupo):
    if not nombre_grupo:
        return ""
    grupo_base = re.sub(r"\d+$", "", nombre_grupo).strip().lower()
    if grupo_base == "oro":
        return "🥇"
    if grupo_base == "plata":
        return "🥈"
    if grupo_base == "bronce":
        return "🥉"
    return ""


async def func_proximos_eventos(bot, usuario, canal_destino_id=None, respuesta_privada=True):
    Session = sessionmaker(bind=GestorSQL.conexionEngine())
    ahora = datetime.now()
    fin = (ahora + timedelta(days=1)).replace(hour=12, minute=0, second=0, microsecond=0)
    session = Session()

    # Determinar canal destino
    canal_destino = bot.get_channel(int(canal_destino_id)) if canal_destino_id else None
    
    if respuesta_privada:
        # Intentar enviar un mensaje directo al usuario
        try:
            canal_destino = await usuario.create_dm()  # Crear o usar un DM con el usuario
        except Exception as e:
            print(f"No se pudo crear un DM con el usuario: {e}")
            return
    else:
        if not canal_destino:       
            # Si es un comando slash, usar el canal del `interaction` si es posible
            if hasattr(usuario, 'channel'):
                canal_destino = usuario.channel
            else:
                print("No se encontró un canal válido para enviar el mensaje.")
                return

    # Consultar eventos
    UsuarioCoach1 = aliased(GestorSQL.Usuario)
    UsuarioCoach2 = aliased(GestorSQL.Usuario)
    GrupoCoach1 = aliased(GestorSQL.Grupo)
    eventos = session.query(
        GestorSQL.Calendario,
        UsuarioCoach1.nombre_discord.label("nombre_discord1"),
        UsuarioCoach1.raza.label("raza1"),
        UsuarioCoach1.id_discord.label("id_discord1"),
        UsuarioCoach2.nombre_discord.label("nombre_discord2"),
        UsuarioCoach2.id_discord.label("id_discord2"),
        UsuarioCoach2.raza.label("raza2"),
        GrupoCoach1.nombre_grupo.label("nombre_grupo"),
    ).join(
        UsuarioCoach1, GestorSQL.Calendario.coach1 == UsuarioCoach1.idUsuarios
    ).join(
        UsuarioCoach2, GestorSQL.Calendario.coach2 == UsuarioCoach2.idUsuarios
    ).outerjoin(
        GrupoCoach1, UsuarioCoach1.grupo == GrupoCoach1.id_grupo
    ).filter(
        GestorSQL.Calendario.fecha >= ahora,
        GestorSQL.Calendario.fecha <= fin
    ).order_by(
        GestorSQL.Calendario.fecha
    ).all()

    UsuarioCoach1_T = aliased(GestorSQL.Usuario)
    UsuarioCoach2_T = aliased(GestorSQL.Usuario)
    eventos_ticket = session.query(
        GestorSQL.Ticket,
        UsuarioCoach1_T.nombre_discord.label("nombre_discord1"),
        UsuarioCoach1_T.raza.label("raza1"),
        UsuarioCoach1_T.id_discord.label("id_discord1"),
        UsuarioCoach2_T.nombre_discord.label("nombre_discord2"),
        UsuarioCoach2_T.id_discord.label("id_discord2"),
        UsuarioCoach2_T.raza.label("raza2"),
    ).join(
        UsuarioCoach1_T, GestorSQL.Ticket.coach1 == UsuarioCoach1_T.idUsuarios
    ).join(
        UsuarioCoach2_T, GestorSQL.Ticket.coach2 == UsuarioCoach2_T.idUsuarios
    ).filter(
        GestorSQL.Ticket.fecha >= ahora,
        GestorSQL.Ticket.fecha <= fin
    ).order_by(
        GestorSQL.Ticket.fecha
    ).all()

    # Construir mensaje
    hay_eventos = bool(eventos or eventos_ticket)
    mensaje = (
        "Próximos partidos del calendario:\n\n"
        if hay_eventos else "No hay eventos programados en el intervalo dado."
    )

    if hay_eventos:
        ids_discord = []
        if eventos:
            for evento in eventos:
                calendario, nd1, raza1, id1, nd2, id2, raza2, nombre_grupo = evento
                grupo_icono = obtener_icono_grupo(nombre_grupo)
                menciones = []
                if id1:
                    menciones.append(f"<@{id1}>")
                    ids_discord.append(id1)
                if id2:
                    menciones.append(f"<@{id2}>")
                    ids_discord.append(id2)
                nombres = " VS ".join(menciones) if menciones else f"**{nd1}** VS **{nd2}**"
                prefijo = f"{grupo_icono} " if grupo_icono else ""
                mensaje += (
                    f"{prefijo}{nombres} ({raza1} vs {raza2}), "
                    f"<t:{int(calendario.fecha.timestamp())}:f>, Jornada: {calendario.jornada}\n"
                )
        if eventos_ticket:
            mensaje += "🎟Ticket🎟\n"
            for evento in eventos_ticket:
                calendario, nd1, raza1, id1, nd2, id2, raza2 = evento
                menciones = []
                if id1:
                    menciones.append(f"<@{id1}>")
                    ids_discord.append(id1)
                if id2:
                    menciones.append(f"<@{id2}>")
                    ids_discord.append(id2)
                nombres = " VS ".join(menciones) if menciones else f"**{nd1}** VS **{nd2}**"
                mensaje += (
                    f"{nombres} ({raza1} vs {raza2}), "
                    f"<t:{int(calendario.fecha.timestamp())}:f>, Jornada: {calendario.jornada}\n"
                )
        menciones_unicas = list({f"<@{i}>" for i in ids_discord if i})
        if menciones_unicas:
            mensaje += "\n\n" + mensaje_gracioso(menciones_unicas)

    # Enviar el mensaje
    try:
        await canal_destino.send(mensaje)
    except Exception as e:
        print(f"No se pudo enviar el mensaje: {e}")
    
        
        
def mensaje_gracioso(ids_discord):
    mensajes = [
        "A mi me huele que no le va a quedar nadie en el campo al pobre {}",
        "Apuesto todos mis bits por {}",
        "Hoy vas a sacar un montón de 💀💀 {}",
        "Me ha dicho un pajarito que {} ha trucado los dados y se vienen solo ☀",
        "Hoy en el {} triste/contento... El triste",
        "Hoy no te van a matar a nadie {}... Bueno si",
        "Hoy juega {}, voy mandando la BUAmbulacia 🚑"
    ]
    # Selecciona un id de usuario y un mensaje al azar
    id_seleccionado = random.choice(ids_discord)
    mensaje_seleccionado = random.choice(mensajes)
    # Formatea y devuelve el mensaje completo
    return mensaje_seleccionado.format(id_seleccionado)

@bot.tree.command(name='consulta_clasificacion', description='Consulta la clasificacion')
@commands.has_any_role('Moderadores', 'Administrador','Comisario')
@app_commands.choices(grupo=[
    app_commands.Choice(name="Oro A", value=1),
    app_commands.Choice(name="Oro B", value=2),
    app_commands.Choice(name="Oro C", value=3), 
    app_commands.Choice(name="Oro D", value=4),
    app_commands.Choice(name="Plata A", value=5),
    app_commands.Choice(name="Plata B", value=6),
    app_commands.Choice(name="Plata C", value=7),
    app_commands.Choice(name="Plata D", value=8),
    app_commands.Choice(name="Plata E", value=9),
    app_commands.Choice(name="Bronce A", value=10),
    app_commands.Choice(name="Bronce B", value=11),
    app_commands.Choice(name="Bronce C", value=12),
    app_commands.Choice(name="Bronce D", value=13),
    app_commands.Choice(name="Bronce E", value=14),
    app_commands.Choice(name="Bronce F", value=15)
])
async def consulta_clasificacion(interaction: discord.Interaction, jornada: int, grupo:int):
    respuesta = 'No hay aún partidos de este grupo'
    try:
        respuesta = clasificacion_liga(jornada,grupo)
    except:
        respuesta = 'No hay aún partidos de este grupo'
    await interaction.response.send_message("```" + respuesta + "```")

def clasificacion_liga(jornada, grupo):
    resultados = obtener_clasificacion(jornada, grupo)

    datos_filtrados = []
    for fila in resultados:
        datos_filtrados.append([
            fila[0],
            fila[1],
            fila[2],
            fila[3],
            fila[4],
            fila[5],
            fila[6],
            f"{fila[7]}/{fila[8]}",
            f"{fila[9]}/{fila[10]}"
        ])

    columnas = ['Nombre', 'PJ', 'PG', 'PE', 'PP', 'DDT', 'PTS', 'Lesiones', 'Muertes']

    anchos = [len(col) for col in columnas]
    for fila in datos_filtrados:
        for i, celda in enumerate(fila):
            if len(str(celda)) > anchos[i]:
                anchos[i] = len(str(celda))

    cabecera = ' | '.join(columnas[i].ljust(anchos[i]) for i in range(len(columnas)))
    linea = '-+-'.join('-' * anchos[i] for i in range(len(columnas)))

    filas = []
    for fila in datos_filtrados:
        fila_str = ' | '.join(str(fila[i]).ljust(anchos[i]) for i in range(len(columnas)))
        filas.append(fila_str)

    tabla = f"{cabecera}\n{linea}\n" + "\n".join(filas)
    return tabla
@bot.tree.command(name='consulta_jugador', description='Consulta los partidos de un jugador')
async def consulta_jugador(interaction: discord.Interaction, nombre: str):
    await interaction.response.send_message(f"Tabla del jugador {nombre}" + tabla_jugador(nombre))


def tabla_jugador(usuario_nombre):
    Session = sessionmaker(bind=GestorSQL.conexionEngine())
    session = Session()  

    usuario = session.query(GestorSQL.Usuario).filter(or_(GestorSQL.Usuario.nombre_discord == usuario_nombre, GestorSQL.Usuario.nombre_bloodbowl == usuario_nombre)).first()
    if not usuario:
        return "Usuario no encontrado"
    
    # Buscar registros de calendario donde el usuario es coach1 o coach2
    calendarios = session.query(GestorSQL.Calendario).filter(or_(GestorSQL.Calendario.coach1 == usuario.idUsuarios, GestorSQL.Calendario.coach2 == usuario.idUsuarios)).all()
    
    resultados = []
    
    for calendario in calendarios:
        # Inicializar estado, observaciones y resultado
        estado = ""
        observaciones = ""
        resultado = ""  
        detalles_resultado = ""  
        
        rival_id = calendario.coach1 if calendario.coach1 != usuario.idUsuarios else calendario.coach2
        es_coach1 = calendario.coach1 == usuario.idUsuarios
        
        if calendario.partidos_idPartidos is not None:
            partido = session.query(GestorSQL.Partidos).filter_by(idPartidos=calendario.partidos_idPartidos).first()
            if partido:
                # Asignar resultado y detalles del resultado
                if es_coach1:
                    detalles_resultado = f"{partido.resultado1} - {partido.resultado2}"
                    if partido.resultado1 > partido.resultado2:
                        resultado = "Victoria"
                    elif partido.resultado1 < partido.resultado2:
                        resultado = "Derrota"
                    else:
                        resultado = "Empate"
                else:
                    detalles_resultado = f"{partido.resultado2} - {partido.resultado1}"
                    if partido.resultado1 < partido.resultado2:
                        resultado = "Victoria"
                    elif partido.resultado1 > partido.resultado2:
                        resultado = "Derrota"
                    else:
                        resultado = "Empate"
                estado = "Jugado"
        elif calendario.fecha is not None:
            estado = "Agendado"
            fecha = calendario.fecha.strftime('%Y-%m-%d %H:%M')
            observaciones = f"Fecha agendada: {fecha}"
        else:
            rival = session.query(GestorSQL.Usuario).filter_by(idUsuarios=rival_id).first()
            if calendario.jornada == usuario.jornada_actual:
                if calendario.jornada == rival.jornada_actual:
                    estado = "Buscando fecha"
                else:
                    calendario_rival = session.query(GestorSQL.Calendario).filter(or_(GestorSQL.Calendario.coach1 == rival_id, GestorSQL.Calendario.coach2 == rival_id), GestorSQL.Calendario.jornada == rival.jornada_actual).first()
                    if calendario_rival:
                        fecha = calendario_rival.fecha.strftime('%Y-%m-%d %H:%M') if calendario_rival.fecha else "Sin fecha"
                        observaciones = f"J{calendario_rival.jornada} {calendario_rival.usuario_coach1.nombre_discord} vs {calendario_rival.usuario_coach2.nombre_discord} ({fecha})"
                        estado = f"Esperando a {rival.nombre_discord}"
            elif calendario.jornada > usuario.jornada_actual and rival.jornada_actual == calendario.jornada:
                estado = f"{rival.nombre_discord} está esperando"
        
        # Determinar el nombre del rival
        rival_nombre = session.query(GestorSQL.Usuario.nombre_discord).filter_by(idUsuarios=rival_id).scalar()
        
        # Añadir resultado a la lista
        resultados.append({
            "Jornada": calendario.jornada,
            "Rival": rival_nombre,
            "Estado": estado,
            "Observaciones": observaciones,
            "Resultado": resultado,  
            "Marcador": detalles_resultado  
        })
    
    columnas = ['Jornada', 'Rival', 'Estado', 'Resultado', 'Marcador', 'Observaciones']
    
    # Encuentra el ancho máximo para cada columna
    anchos = []
    for columna in columnas:
        max_len = max(len(str(fila.get(columna, ""))) for fila in resultados)
        anchos.append(max(len(columna), max_len))
    
    # Crea la cabecera de la tabla
    cabecera = ' | '.join(columna.ljust(anchos[i]) for i, columna in enumerate(columnas))
    linea = '-+-'.join('-' * anchos[i] for i in range(len(columnas)))
    
    # Crea las filas de la tabla
    filas = []
    for fila in resultados:
        fila_texto = ' | '.join(str(fila.get(columna, "")).ljust(anchos[i]) for i, columna in enumerate(columnas))
        filas.append(fila_texto)
    
    # Junta la tabla
    resultados = f"```{cabecera}\n{linea}\n" + "\n".join(filas) + "```"
    
    return resultados

@bot.command()
@commands.has_any_role('Moderadores', 'Administrador','Comisario')
async def lanzar_encuesta(ctx):
    Session = sessionmaker(bind=GestorSQL.conexionEngine())
    session = Session()   
    usuarios = session.query(GestorSQL.Usuario)

    for usuario in usuarios:
        try:
            boton = discord.ui.Button(label="Empezar encuesta", style=discord.ButtonStyle.green)
            boton.callback = Encuesta.primera_pregunta
            view = discord.ui.View()
            view.add_item(boton)
            user = await bot.fetch_user(usuario.id_discord)

            await user.send(f"Hola <@{usuario.id_discord}> ¿Te gustaría participar en una encuesta corta para que sepamos tu opinión sobre la Butter Cup?", view=view)
            await asyncio.sleep(0.5)  # Breve espera para evitar el spam
        except Exception as e:
            await UtilesDiscord.mensaje_administradores(f"Error al enviar mensaje a {usuario.nombre_discord}: {str(e)}")
        else:
            await UtilesDiscord.mensaje_administradores(f"Mensaje enviado con éxito a {usuario.nombre_discord}")


@bot.command()
async def actualizar_usuarios_inscripcion(ctx):
    Session = sessionmaker(bind=GestorSQL.conexionEngine())
    session = Session()   
    inscripciones = session.query(GestorSQL.Inscripcion).all()
    
    for inscripcion in inscripciones:
        usuario = session.query(GestorSQL.Usuario).filter_by(id_discord=inscripcion.id_usuario_discord).first()
        if usuario:
            continue    
        else:
            member = ctx.guild.get_member(inscripcion.id_usuario_discord)
            if member is not None:
                nuevo_usuario = GestorSQL.Usuario(
                    nombre_discord=member.name,
                    id_discord=member.id,
                    nombre_bloodbowl=inscripcion.nombre_bloodbowl
                )
                session.add(nuevo_usuario)
                session.commit()
                await ctx.send(f'Usuario {member.name} agregado a la base de datos.')
            else:
                await ctx.send(f'El usuario con ID {inscripcion.id_usuario_discord} no se encontró en Discord.')

    session.close()
    

@bot.command()
async def actualiza_playoffsOro(ctx, todos: int = 0):
    if str(ctx.author.id) not in maestros:
        await ctx.send("No tienes permiso para usar este comando.")
        return

    Session = sessionmaker(bind=GestorSQL.conexionEngine())
    session = Session()

    canal_id = 1223765590146158653

    mensaje = await actualizar_playoffs(ctx, session, lambda: APIBbowl.obtener_partido_PlayOff(bbowl_API_token), canal_id, GestorSQL.PlayOffsOro, todos)
    await ctx.send(mensaje)

    session.close()

@bot.command()
async def actualiza_playoffsPlata(ctx, todos: int = 0):
    if str(ctx.author.id) not in maestros:
        await ctx.send("No tienes permiso para usar este comando.")
        return

    Session = sessionmaker(bind=GestorSQL.conexionEngine())
    session = Session()

    canal_id = 1223765590146158653

    mensaje = await actualizar_playoffs(ctx, session, lambda: APIBbowl.obtener_partido_PlayOff(bbowl_API_token), canal_id, GestorSQL.PlayOffsPlata, todos)
    await ctx.send(mensaje)

    session.close()

@bot.command()
async def actualiza_playoffsBronce(ctx, todos: int = 0):
    if str(ctx.author.id) not in maestros:
        await ctx.send("No tienes permiso para usar este comando.")
        return

    Session = sessionmaker(bind=GestorSQL.conexionEngine())
    session = Session()

    canal_id = 1223765590146158653

    mensaje = await actualizar_playoffs(ctx, session, lambda: APIBbowl.obtener_partido_PlayOff(bbowl_API_token), canal_id, GestorSQL.PlayOffsBronce, todos)
    await ctx.send(mensaje)

    session.close()

async def actualizar_playoffs(ctx, session, obtener_partidos_func, categoria_id, tabla_playoff, todos=0):
    matches = obtener_partidos_func()
    if not matches:
        return "No se encontraron partidos."
 
    for match in matches:
        partido_existente = session.query(GestorSQL.Partidos).filter_by(idPartidoBbowl=match['uuid']).first()
        if partido_existente:
            if todos == 0:
                break
            else:
                partido_existente = None
                continue
 
        coach_ids = [match['coaches'][0]['idcoach'], match['coaches'][1]['idcoach']]
        usuarios = session.query(GestorSQL.Usuario).filter(GestorSQL.Usuario.id_bloodbowl.in_(coach_ids)).all()
 
        if len(usuarios) != 2:
            await UtilesDiscord.mensaje_administradores(f"No se encontraron ambos usuarios en la base de datos para los coaches: {match['coaches'][0]['name']} y {match['coaches'][1]['name']}. Posiblemente el partido pertenezca a otra liga.")
            continue
 
        calendario_registro = session.query(tabla_playoff).filter(
            and_(
                tabla_playoff.coach1.in_([usuarios[0].idUsuarios, usuarios[1].idUsuarios]),
                tabla_playoff.coach2.in_([usuarios[0].idUsuarios, usuarios[1].idUsuarios]),
            ),
            tabla_playoff.partidos_idPartidos == None
        ).order_by(tabla_playoff.jornada).first()
 
        if not calendario_registro:
            await UtilesDiscord.mensaje_administradores(f"No se encontró un registro para actualizar para los coaches: {usuarios[0].nombre_discord} y {usuarios[1].nombre_discord}. Posiblemente el partido pertenezca a otra liga.")
            continue
 
        local_index = 0 if calendario_registro.usuario_coach1.id_bloodbowl == match['coaches'][0]['idcoach'] else 1
        visitante_index = 1 - local_index
 
        total_muertes_coach1 = match['teams'][local_index]['sustaineddead']
        total_lesiones_coach1 = match['teams'][visitante_index]['inflictedcasualties']
        total_lesiones_coach1 -= total_muertes_coach1
 
        total_muertes_coach2 = match['teams'][visitante_index]['sustaineddead']
        total_lesiones_coach2 = match['teams'][local_index]['inflictedcasualties']
        total_lesiones_coach2 -= total_muertes_coach2
 

        nuevo_partido = GestorSQL.Partidos(
            resultado1=match['teams'][local_index]['score'],
            resultado2=match['teams'][visitante_index]['score'],
            lesiones1=total_lesiones_coach1,
            lesiones2=total_lesiones_coach2,
            muertes1=total_muertes_coach1,
            muertes2=total_muertes_coach2,
            idPartidoBbowl=match['uuid'],
            pases1=match['teams'][local_index]['inflictedpasses'],
            pases2=match['teams'][visitante_index]['inflictedpasses'],
            catches1=match['teams'][local_index]['inflictedcatches'],
            catches2=match['teams'][visitante_index]['inflictedcatches'],
            interceptions1=match['teams'][local_index]['inflictedinterceptions'],
            interceptions2=match['teams'][visitante_index]['inflictedinterceptions'],
            ko1=match['teams'][local_index]['inflictedko'],
            ko2=match['teams'][visitante_index]['inflictedko'],
            push1=match['teams'][local_index]['inflictedpushouts'],
            push2=match['teams'][visitante_index]['inflictedpushouts'],
            mRun1=match['teams'][local_index]['inflictedmetersrunning'],
            mRun2=match['teams'][visitante_index]['inflictedmetersrunning'],
            mPass1=match['teams'][local_index]['inflictedmetersrunning'],
            mPass2=match['teams'][visitante_index]['inflictedmetersrunning'],
            logo1=match['teams'][local_index]['teamlogo'],
            logo2=match['teams'][visitante_index]['teamlogo'],
            nombreEquipo1=match['teams'][local_index]['teamname'],
            nombreEquipo2=match['teams'][visitante_index]['teamname']
        )
 
        session.add(nuevo_partido)
        session.commit()
        
        calendario_registro.partidos_idPartidos = nuevo_partido.idPartidos
        session.commit()
        
        session.refresh(nuevo_partido)
        
        await UtilesDiscord.publicar(ctx,'Jornada Playoffs  ' + str(calendario_registro.jornada) + '!',id_foro=categoria_id,idPartido=nuevo_partido.idPartidos)

        
        try:
            await UtilesDiscord.gestionar_canal_discord(ctx, "eliminar", canal_id=calendario_registro.canalAsociado)
        except Exception as e:
            await UtilesDiscord.mensaje_administradores(f"No se pudo borrar el canal con id {calendario_registro.canalAsociado}")



        # Determinar ganador y perdedor basado en el resultado
        if nuevo_partido.resultado1 > nuevo_partido.resultado2:
            ganador_coach = calendario_registro.usuario_coach1
            perdedor_coach = calendario_registro.usuario_coach2
        else:
            # El equipo visitante ganó o fue empate (asumiremos el visitante en caso de empate)
            ganador_coach = calendario_registro.usuario_coach2
            perdedor_coach = calendario_registro.usuario_coach1

        # Actualizar futuros partidos para ganador y perdedor
        partido_id = calendario_registro.idCalendario
        futuros_partidos = session.query(tabla_playoff).filter(
            or_(
                tabla_playoff.PuestoCoach1 == f'Ganador{partido_id}',
                tabla_playoff.PuestoCoach2 == f'Ganador{partido_id}',
                tabla_playoff.PuestoCoach1 == f'Perdedor{partido_id}',
                tabla_playoff.PuestoCoach2 == f'Perdedor{partido_id}'
            )
        ).all()

        ganador_asignado = False
        perdedor_asignado = False

        for futuro in futuros_partidos:
            if futuro.PuestoCoach1 == f'Ganador{partido_id}':
                futuro.coach1 = ganador_coach.idUsuarios
                ganador_asignado = True
                await UtilesDiscord.mensaje_administradores(f"El usuario {ganador_coach.nombre_discord} como ganador del partido se ha insertado en el partido id {futuro.idCalendario}")
            elif futuro.PuestoCoach2 == f'Ganador{partido_id}':
                futuro.coach2 = ganador_coach.idUsuarios
                ganador_asignado = True
                await UtilesDiscord.mensaje_administradores(f"El usuario {ganador_coach.nombre_discord} como ganador del partido se ha insertado en el partido id {futuro.idCalendario}")
            if futuro.PuestoCoach1 == f'Perdedor{partido_id}':
                futuro.coach1 = perdedor_coach.idUsuarios
                perdedor_asignado = True
                await UtilesDiscord.mensaje_administradores(f"El usuario {perdedor_coach.nombre_discord} como perdedor del partido se ha insertado en el partido id {futuro.idCalendario}")
            elif futuro.PuestoCoach2 == f'Perdedor{partido_id}':
                futuro.coach2 = perdedor_coach.idUsuarios
                perdedor_asignado = True
                await UtilesDiscord.mensaje_administradores(f"El usuario {perdedor_coach.nombre_discord} como perdedor del partido se ha insertado en el partido id {futuro.idCalendario}")

        if not ganador_asignado:
            await UtilesDiscord.mensaje_administradores(f"El usuario {ganador_coach.nombre_discord} como ganador del partido {partido_id} no tiene futuros encuentros asignados.")
        if not perdedor_asignado:
            await UtilesDiscord.mensaje_administradores(f"El usuario {perdedor_coach.nombre_discord} como perdedor del partido {partido_id} no tiene futuros encuentros asignados.")

        session.commit()

    # Crear futuros encuentros para partidos sin canal asociado
    partidos_sin_canal = session.query(tabla_playoff).filter(
        tabla_playoff.canalAsociado == None,
        tabla_playoff.coach1 != None,
        tabla_playoff.coach2 != None
    ).all()

    for partido in partidos_sin_canal:
        coach1 = session.query(GestorSQL.Usuario).filter_by(idUsuarios=partido.coach1).first()
        coach2 = session.query(GestorSQL.Usuario).filter_by(idUsuarios=partido.coach2).first()

        if coach1 and coach2:
            preferencias_coach1 = session.query(GestorSQL.PreferenciasFecha).filter_by(idUsuarios=coach1.idUsuarios).first()
            preferencias_coach2 = session.query(GestorSQL.PreferenciasFecha).filter_by(idUsuarios=coach2.idUsuarios).first()

            preferencias1 = [coach1.id_discord, preferencias_coach1.preferencia if preferencias_coach1 else ""]
            preferencias2 = [coach2.id_discord, preferencias_coach2.preferencia if preferencias_coach2 else ""]

            mensajePreferencias1=''
            if preferencias1[0] and preferencias1[1]:
                mensajePreferencias1 = f"\n<@{preferencias1[0]}> suele poder jugar {preferencias1[1]}"
        
            mensajePreferencias2=''
            if preferencias2[0] and preferencias2[1]:
                mensajePreferencias2 = f"\n<@{preferencias2[0]}> suele poder jugar {preferencias2[1]}"

            mensaje = """Bienvenidos, {mention1}({raza1}) y {mention2}({raza2})! Estáis en los Play-Offs porque sois lo mejor de lo mejor. 
Si es vuestro primer partido RECORDAD inscribir vuestros equipos en la competición PlayOffs6 contraseña PlayOffs6. Los playoff se juegan en formato resurreción, por ello no podréis modificar vuestro equipo después del primer partido. Recordad también que debéis que enviar un pantallazo de como queda vuestro equipo a Pikoleto. \n\n-------------------------------------------""" + mensajePreferencias1 + mensajePreferencias2 +"""
Cuando acordéis una fecha usad el comando /fecha para que el bot pueda registrar vuestro partido con el horario de España.{fecha}
            
-------------------------------------------
            
Antes de jugar tendréis que **USAR EL CANAL** #spin y **LIBERADLO** al encontrar partido.

-------------------------------------------
            
Si hubiera cualquier problema mencionad a los comisarios.
                """


            grupo_usuario = coach1.grupo
            if grupo_usuario in [1, 2, 3, 4]:
                categoria_id_nuevo = 1326104425370095689
            elif grupo_usuario in [5, 6, 7, 8]:
                categoria_id_nuevo = 1326104506043465761
            else:
                categoria_id_nuevo = 1326104557767491584
                


            nombre_canal = f"PlayOff-{partido.jornada}-{coach1.nombre_discord}vs{coach2.nombre_discord}"
            idNuevoCanal = await UtilesDiscord.gestionar_canal_discord(ctx, "crear", nombre_canal, coach1.id_discord, coach2.id_discord, raza1=coach1.raza, raza2=coach2.raza, fechalimite=int(partido.fechaFinal.timestamp()), preferencias1=preferencias1, preferencias2=preferencias2,categoria_id=categoria_id_nuevo)

            if idNuevoCanal:
                partido.canalAsociado = idNuevoCanal
                session.commit()
            else:
                await UtilesDiscord.mensaje_administradores(f"No se pudo crear el canal para el partido {nombre_canal}")

    return "Actualización completada."


async def actualizar_ticket(ctx, session, obtener_partidos_func, categoria_id, tabla_ticket, todos=0):
    matches = obtener_partidos_func()
    if not matches:
        return "No se encontraron partidos."

    for match in matches:
        partido_existente = session.query(GestorSQL.Partidos).filter_by(idPartidoBbowl=match['uuid']).first()
        if partido_existente:
            if todos == 0:
                break
            else:
                partido_existente = None
                continue

        coach_ids = [match['coaches'][0]['idcoach'], match['coaches'][1]['idcoach']]
        usuarios = session.query(GestorSQL.Usuario).filter(GestorSQL.Usuario.id_bloodbowl.in_(coach_ids)).all()

        if len(usuarios) != 2:
            await UtilesDiscord.mensaje_administradores(
                f"No se encontraron ambos usuarios en la base de datos para los coaches: {match['coaches'][0]['name']} y {match['coaches'][1]['name']}. Posiblemente el partido pertenezca a otra liga."
            )
            continue

        calendario_registro = session.query(tabla_ticket).filter(
            and_(
                tabla_ticket.coach1.in_([usuarios[0].idUsuarios, usuarios[1].idUsuarios]),
                tabla_ticket.coach2.in_([usuarios[0].idUsuarios, usuarios[1].idUsuarios]),
            ),
            tabla_ticket.partidos_idPartidos == None
        ).order_by(tabla_ticket.jornada).first()

        if not calendario_registro:
            await UtilesDiscord.mensaje_administradores(
                f"No se encontró un registro para actualizar para los coaches: {usuarios[0].nombre_discord} y {usuarios[1].nombre_discord}. Posiblemente el partido pertenezca a otra liga."
            )
            continue

        local_index = 0 if calendario_registro.usuario_coach1.id_bloodbowl == match['coaches'][0]['idcoach'] else 1
        visitante_index = 1 - local_index

        total_muertes_coach1 = match['teams'][local_index]['sustaineddead']
        total_lesiones_coach1 = match['teams'][visitante_index]['inflictedcasualties']
        total_lesiones_coach1 -= total_muertes_coach1

        total_muertes_coach2 = match['teams'][visitante_index]['sustaineddead']
        total_lesiones_coach2 = match['teams'][local_index]['inflictedcasualties']
        total_lesiones_coach2 -= total_muertes_coach2

        nuevo_partido = GestorSQL.Partidos(
            resultado1=match['teams'][local_index]['score'],
            resultado2=match['teams'][visitante_index]['score'],
            lesiones1=total_lesiones_coach1,
            lesiones2=total_lesiones_coach2,
            muertes1=total_muertes_coach1,
            muertes2=total_muertes_coach2,
            idPartidoBbowl=match['uuid'],
            pases1=match['teams'][local_index]['inflictedpasses'],
            pases2=match['teams'][visitante_index]['inflictedpasses'],
            catches1=match['teams'][local_index]['inflictedcatches'],
            catches2=match['teams'][visitante_index]['inflictedcatches'],
            interceptions1=match['teams'][local_index]['inflictedinterceptions'],
            interceptions2=match['teams'][visitante_index]['inflictedinterceptions'],
            ko1=match['teams'][local_index]['inflictedko'],
            ko2=match['teams'][visitante_index]['inflictedko'],
            push1=match['teams'][local_index]['inflictedpushouts'],
            push2=match['teams'][visitante_index]['inflictedpushouts'],
            mRun1=match['teams'][local_index]['inflictedmetersrunning'],
            mRun2=match['teams'][visitante_index]['inflictedmetersrunning'],
            mPass1=match['teams'][local_index]['inflictedmetersrunning'],
            mPass2=match['teams'][visitante_index]['inflictedmetersrunning'],
            logo1=match['teams'][local_index]['teamlogo'],
            logo2=match['teams'][visitante_index]['teamlogo'],
            nombreEquipo1=match['teams'][local_index]['teamname'],
            nombreEquipo2=match['teams'][visitante_index]['teamname']
        )

        session.add(nuevo_partido)
        session.commit()

        calendario_registro.partidos_idPartidos = nuevo_partido.idPartidos
        session.commit()

        session.refresh(nuevo_partido)

        await UtilesDiscord.publicar(
            ctx,
            'Jornada Ticket  ' + str(calendario_registro.jornada) + '!',
            id_foro=categoria_id,
            idPartido=nuevo_partido.idPartidos,
        )

        try:
            await UtilesDiscord.gestionar_canal_discord(ctx, 'eliminar', canal_id=calendario_registro.canalAsociado)
        except Exception:
            await UtilesDiscord.mensaje_administradores(
                f"No se pudo borrar el canal con id {calendario_registro.canalAsociado}"
            )

        if nuevo_partido.resultado1 > nuevo_partido.resultado2:
            ganador_coach = calendario_registro.usuario_coach1
            perdedor_coach = calendario_registro.usuario_coach2
        else:
            ganador_coach = calendario_registro.usuario_coach2
            perdedor_coach = calendario_registro.usuario_coach1

        partido_id = calendario_registro.idTicket
        futuros_partidos = session.query(tabla_ticket).filter(
            or_(
                tabla_ticket.PuestoCoach1 == f'Ganador{partido_id}',
                tabla_ticket.PuestoCoach2 == f'Ganador{partido_id}',
                tabla_ticket.PuestoCoach1 == f'Perdedor{partido_id}',
                tabla_ticket.PuestoCoach2 == f'Perdedor{partido_id}'
            )
        ).all()

        ganador_asignado = False
        perdedor_asignado = False

        for futuro in futuros_partidos:
            if futuro.PuestoCoach1 == f'Ganador{partido_id}':
                futuro.coach1 = ganador_coach.idUsuarios
                ganador_asignado = True
                await UtilesDiscord.mensaje_administradores(
                    f"El usuario {ganador_coach.nombre_discord} como ganador del partido se ha insertado en el partido id {futuro.idTicket}"
                )
            elif futuro.PuestoCoach2 == f'Ganador{partido_id}':
                futuro.coach2 = ganador_coach.idUsuarios
                ganador_asignado = True
                await UtilesDiscord.mensaje_administradores(
                    f"El usuario {ganador_coach.nombre_discord} como ganador del partido se ha insertado en el partido id {futuro.idTicket}"
                )
            if futuro.PuestoCoach1 == f'Perdedor{partido_id}':
                futuro.coach1 = perdedor_coach.idUsuarios
                perdedor_asignado = True
                await UtilesDiscord.mensaje_administradores(
                    f"El usuario {perdedor_coach.nombre_discord} como perdedor del partido se ha insertado en el partido id {futuro.idTicket}"
                )
            elif futuro.PuestoCoach2 == f'Perdedor{partido_id}':
                futuro.coach2 = perdedor_coach.idUsuarios
                perdedor_asignado = True
                await UtilesDiscord.mensaje_administradores(
                    f"El usuario {perdedor_coach.nombre_discord} como perdedor del partido se ha insertado en el partido id {futuro.idTicket}"
                )

        if not ganador_asignado:
            await UtilesDiscord.mensaje_administradores(
                f"El usuario {ganador_coach.nombre_discord} como ganador del partido {partido_id} no tiene futuros encuentros asignados."
            )
        if not perdedor_asignado:
            await UtilesDiscord.mensaje_administradores(
                f"El usuario {perdedor_coach.nombre_discord} como perdedor del partido {partido_id} no tiene futuros encuentros asignados."
            )

        session.commit()

    partidos_sin_canal = session.query(tabla_ticket).filter(
        tabla_ticket.canalAsociado == None,
        tabla_ticket.coach1 != None,
        tabla_ticket.coach2 != None
    ).all()

    for partido in partidos_sin_canal:
        coach1 = session.query(GestorSQL.Usuario).filter_by(idUsuarios=partido.coach1).first()
        coach2 = session.query(GestorSQL.Usuario).filter_by(idUsuarios=partido.coach2).first()

        if coach1 and coach2:
            preferencias_coach1 = session.query(GestorSQL.PreferenciasFecha).filter_by(idUsuarios=coach1.idUsuarios).first()
            preferencias_coach2 = session.query(GestorSQL.PreferenciasFecha).filter_by(idUsuarios=coach2.idUsuarios).first()

            preferencias1 = [coach1.id_discord, preferencias_coach1.preferencia if preferencias_coach1 else ""]
            preferencias2 = [coach2.id_discord, preferencias_coach2.preferencia if preferencias_coach2 else ""]

            mensajePreferencias1 = ''
            if preferencias1[0] and preferencias1[1]:
                mensajePreferencias1 = f"\n<@{preferencias1[0]}> suele poder jugar {preferencias1[1]}"

            mensajePreferencias2 = ''
            if preferencias2[0] and preferencias2[1]:
                mensajePreferencias2 = f"\n<@{preferencias2[0]}> suele poder jugar {preferencias2[1]}"

            mensaje = """Bienvenidos, {mention1}({raza1}) y {mention2}({raza2})! Estáis en los Play-Offs que pueden llevaros a conseguir un 🎟**TICKET**🎟. El primero se llevará un Ticket directo para el mundial y el segundo un Ticket de play-in.

Ahora debéis elegir uno de los equipos con los que habéis jugado la ButterCup para inscribirlo en la competición Ticket ButterCup contraseña TicketButtercup2025.
Si el equipo está actualmente jugando los playoffs de la Cuarta Edición de la Butter Cup debéis hacer una copia del equipo. Contáis con la ayuda de los comisarios para ello.
Si el equipo lleva 20 partidos sin hacer reforma deberéis hacerla ANTES de empezar vuestro pirmer partido.\n\n-------------------------------------------""" + mensajePreferencias1 + mensajePreferencias2 +"""
Cuando acordéis una fecha usad el comando /fecha para que el bot pueda registrar vuestro partido con el horario de España.{fecha}

        -------------------------------------------

Antes de jugar tendréis que **USAR EL CANAL** #spin y **LIBERADLO** al encontrar partido.

Si hubiera cualquier problema mencionad a los comisarios.
                """

            fecha = f"\n\nLa Fecha límite para jugar el partido es el <t:{int(partido.fechaFinal.timestamp())}:f>"
            guild = ctx.guild
            coach1_member = guild.get_member(coach1.id_discord)
            coach2_member = guild.get_member(coach2.id_discord)

            mention1 = coach1_member.mention if coach1_member else ""
            mention2 = coach2_member.mention if coach2_member else ""
            mensaje_formateado = mensaje.format(
                mention1=mention1,
                mention2=mention2,
                raza1=coach1.raza,
                raza2=coach2.raza,
                fecha=fecha,
            )

            nombre_canal = f"🎟{coach1.nombre_discord}vs{coach2.nombre_discord}"
            categoria_id_nuevo = 1396596687879016499
            idNuevoCanal = await UtilesDiscord.gestionar_canal_discord(
                ctx,
                'crear',
                nombre_canal,
                coach1.id_discord,
                coach2.id_discord,
                raza1=coach1.raza,
                raza2=coach2.raza,
                fechalimite=int(partido.fechaFinal.timestamp()),
                preferencias1=preferencias1,
                preferencias2=preferencias2,
                categoria_id=categoria_id_nuevo,
                mensaje=mensaje_formateado,
            )

            if idNuevoCanal:
                partido.canalAsociado = idNuevoCanal
                session.commit()
            else:
                await UtilesDiscord.mensaje_administradores(
                    f"No se pudo crear el canal para el partido {nombre_canal}"
                )

    return "Actualización completada."


@bot.command()
@commands.has_any_role('Moderadores', 'Administrador', 'Comisario')
async def CreaCanalesPlayoff(ctx, jornada, tipo):
    Session = sessionmaker(bind=GestorSQL.conexionEngine())
    with Session() as session:
        # Crear alias para cada relación con la tabla de usuarios
        UsuarioCoach1 = aliased(GestorSQL.Usuario)
        UsuarioCoach2 = aliased(GestorSQL.Usuario)


        # Seleccionar la tabla correspondiente según el tipo
        if tipo == "Oro":
            PlayoffsTabla = GestorSQL.PlayOffsOro
            nombreCompeticion = "PlayOff-"
            categoria_id = 1326104425370095689
        elif tipo == "Plata":
            PlayoffsTabla = GestorSQL.PlayOffsPlata
            nombreCompeticion = "PlayOff-"
            categoria_id = 1326104506043465761
        elif tipo == "Bronce":
            PlayoffsTabla = GestorSQL.PlayOffsBronce
            nombreCompeticion = "PlayOff-"
            categoria_id = 1326104557767491584
        else:
            await ctx.send("Tipo de playoff no válido. Debe ser 'Oro' o 'Plata' o 'Bronce'.")
            return

        calendarios = session.query(PlayoffsTabla)\
            .join(UsuarioCoach1, PlayoffsTabla.coach1 == UsuarioCoach1.idUsuarios)\
            .join(UsuarioCoach2, PlayoffsTabla.coach2 == UsuarioCoach2.idUsuarios)\
            .filter(PlayoffsTabla.jornada == jornada)\
            .all()

        for calendario in calendarios:
            coach1_nombre = calendario.usuario_coach1.nombre_discord
            coach2_nombre = calendario.usuario_coach2.nombre_discord
            coach1_id = calendario.usuario_coach1.id_discord
            coach2_id = calendario.usuario_coach2.id_discord
            
            nombre_canal = f"{nombreCompeticion}{coach1_nombre}vs{coach2_nombre}"
            
            preferencia_usuario = session.query(GestorSQL.PreferenciasFecha).filter_by(idUsuarios=calendario.usuario_coach1.idUsuarios).first()
            preferencia_rival = session.query(GestorSQL.PreferenciasFecha).filter_by(idUsuarios=calendario.usuario_coach2.idUsuarios).first()

            preferenciasUsuario = [coach1_id, preferencia_usuario.preferencia if preferencia_usuario else ""]
            preferenciasRival = [coach2_id, preferencia_rival.preferencia if preferencia_rival else ""]

            #creamos el mensaje
            fecha=f"\n\nLa Fecha límite para jugar el partido es el <t:{int(calendario.fechaFinal.timestamp())}:f>"
            
            mensajePreferencias1=''
            if preferenciasUsuario[0] and preferenciasUsuario[1]:
                mensajePreferencias1 = f"\n<@{preferenciasUsuario[0]}> suele poder jugar {preferenciasUsuario[1]}"
        
            mensajePreferencias2=''
            if preferenciasRival[0] and preferenciasRival[1]:
                mensajePreferencias2 = f"\n<@{preferenciasRival[0]}> suele poder jugar {preferenciasRival[1]}"



            mensaje = """Bienvenidos, {mention1}({raza1}) y {mention2}({raza2})! Estáis en los Play-Offs porque sois lo mejor de lo mejor. 
            
Aquí os jugáis el ascenso de categoría, puntos extra para la próxima reforma y preferencia a la hora de elegir un equipo Reformado/nuevo la próxima temporada.
            
           
RECORDAD inscribir vuestros equipos en la competición PlayOffs6 contraseña PlayOffs6. Los playoff se juegan en formato resurreción, por ello no podréis modificar vuestro equipo después del primer partido. Recordad también que debéis que enviar un pantallazo al hilo de equipos de como queda vuestro equipo 1 día antes del partido siempre que sea posible. \n\n-------------------------------------------""" + mensajePreferencias1 + mensajePreferencias2 +"""
Cuando acordéis una fecha usad el comando /fecha para que el bot pueda registrar vuestro partido con el horario de España.{fecha}
            
-------------------------------------------
            
Antes de jugar tendréis que **USAR EL CANAL** #spin y **LIBERADLO** al encontrar partido.

-------------------------------------------
            
Si hubiera cualquier problema mencionad a los comisarios.
                """
            
            # Buscar los entrenadores y ajustar permisos
            guild = ctx.guild
            coach1 = guild.get_member(calendario.usuario_coach1.id_discord)
            coach2 = guild.get_member(calendario.usuario_coach2.id_discord)

            # Preparar y enviar mensaje de bienvenida
            mention1 = coach1.mention if coach1 else ""
            mention2 = coach2.mention if coach2 else ""
            mensaje_formateado = mensaje.format(mention1=mention1, mention2=mention2,raza1=calendario.usuario_coach1.raza,raza2=calendario.usuario_coach2.raza,fecha=fecha)

            try:
                idNuevoCanal = await UtilesDiscord.gestionar_canal_discord(ctx, "crear", nombre_canal, calendario.usuario_coach1.id_discord, calendario.usuario_coach2.id_discord,mensaje=mensaje_formateado,categoria_id=categoria_id)
                if idNuevoCanal:
                    calendario.canalAsociado = idNuevoCanal
                else:
                    print(f"No se pudo crear el canal para el partido {nombre_canal}")
            except Exception as e:
                session.commit()
                print(f"Error al crear el canal {nombre_canal}: {e}")
                
            await asyncio.sleep(5)

        # Solo se hace commit si todos los canales fueron creados y asociados correctamente
        session.commit()
        
@bot.tree.command(name='proximos_partidos_playoff', description='Avisa de los próximos partidos de los playoffs')
async def proximos_partidos_playoff(interaction: discord.Interaction, canal_destino_id: str = None):
    if str(interaction.user.id) not in maestros:
        await interaction.response.send_message("No tienes permiso para usar este comando.", ephemeral=True)
        return

    await func_proximos_partidos_playoff(
        bot,
        interaction.user,
        canal_destino_id if canal_destino_id else interaction.channel_id,
        False
    )
    await interaction.response.send_message("Mensaje enviado.", ephemeral=True)


async def func_proximos_partidos_playoff(bot, usuario, canal_destino_id=None, respuesta_privada=True):
    Session = sessionmaker(bind=GestorSQL.conexionEngine())
    session = Session()

    ahora = datetime.now()
    fin = (ahora + timedelta(days=1)).replace(hour=12, minute=0, second=0, microsecond=0)

    canal_destino = bot.get_channel(int(canal_destino_id)) if canal_destino_id else None

    if respuesta_privada:
        try:
            canal_destino = await usuario.create_dm()
        except Exception as e:
            print(f"No se pudo crear un DM con el usuario: {e}")
            return
    else:
        if not canal_destino:
            if hasattr(usuario, 'channel'):
                canal_destino = usuario.channel
            else:
                print("No se encontró un canal válido para enviar el mensaje.")
                return

    UsuarioCoach1 = aliased(GestorSQL.Usuario)
    UsuarioCoach2 = aliased(GestorSQL.Usuario)

    bases_playoff = {
        "PlayOffs Oro": GestorSQL.PlayOffsOro,
        "PlayOffs Plata": GestorSQL.PlayOffsPlata,
        "PlayOffs Bronce": GestorSQL.PlayOffsBronce,
    }

    mensaje = (
        "<:Butter_Cup:1184459079368843324> **Hoy juegan los mejores de entre los mejores, ¡ven a animar a tus favoritos y a abuchear a tus enemigos!** "
        "<:Butter_Cup:1184459079368843324>\n\n"
    )
    eventos_existentes = False
    all_eventos = []

    UsuarioCoach1_T = aliased(GestorSQL.Usuario)
    UsuarioCoach2_T = aliased(GestorSQL.Usuario)
    eventos_ticket = (
        session.query(
            GestorSQL.Ticket,
            UsuarioCoach1_T.nombre_discord.label("nombre_discord1"),
            UsuarioCoach1_T.raza.label("raza1"),
            UsuarioCoach1_T.id_discord.label("id_discord1"),
            UsuarioCoach2_T.nombre_discord.label("nombre_discord2"),
            UsuarioCoach2_T.id_discord.label("id_discord2"),
            UsuarioCoach2_T.raza.label("raza2"),
        )
        .join(UsuarioCoach1_T, GestorSQL.Ticket.coach1 == UsuarioCoach1_T.idUsuarios)
        .join(UsuarioCoach2_T, GestorSQL.Ticket.coach2 == UsuarioCoach2_T.idUsuarios)
        .filter(GestorSQL.Ticket.fecha >= ahora, GestorSQL.Ticket.fecha <= fin)
        .order_by(GestorSQL.Ticket.fecha)
        .all()
    )

    for nombre_playoff, tabla_playoff in bases_playoff.items():
        eventos = (
            session.query(
                tabla_playoff,
                UsuarioCoach1.nombre_discord.label("nombre_discord1"),
                UsuarioCoach1.raza.label("raza1"),
                UsuarioCoach1.id_discord.label("id_discord1"),
                UsuarioCoach2.nombre_discord.label("nombre_discord2"),
                UsuarioCoach2.id_discord.label("id_discord2"),
                UsuarioCoach2.raza.label("raza2"),
            )
            .join(UsuarioCoach1, tabla_playoff.coach1 == UsuarioCoach1.idUsuarios)
            .join(UsuarioCoach2, tabla_playoff.coach2 == UsuarioCoach2.idUsuarios)
            .filter(tabla_playoff.fecha >= ahora, tabla_playoff.fecha <= fin)
            .order_by(tabla_playoff.fecha)
            .all()
        )

        if eventos:
            eventos_existentes = True
            mensaje += f"```{nombre_playoff}```\n"
            for calendario, nd1, raza1, id1, nd2, id2, raza2 in eventos:
                mensaje += (
                    f"**{nd1}** ({raza1}) VS **{nd2}** ({raza2}), "
                    f"<t:{int(calendario.fecha.timestamp())}:f>\n"
                )
            all_eventos.extend(eventos)

    hay_eventos = eventos_existentes or eventos_ticket
    if not hay_eventos:
        mensaje = "No hay partidos programados en los playoffs durante el intervalo dado."
        try:
            await canal_destino.send(mensaje)
        finally:
            session.close()
        return

    if eventos_ticket:
        mensaje += "🎟Ticket🎟\n"
        for calendario, nd1, raza1, id1, nd2, id2, raza2 in eventos_ticket:
            mensaje += (
                f"**{nd1}** ({raza1}) VS **{nd2}** ({raza2}), "
                f"<t:{int(calendario.fecha.timestamp())}:f>, Jornada: {calendario.jornada}\n"
            )
        all_eventos.extend(eventos_ticket)

    ids_discord = [
        f"<@{ev[i]}>" for ev in all_eventos for i in (3, 5)
    ]
    mensaje += "\n\n" + mensaje_gracioso(list(set(ids_discord)))

    try:
        await canal_destino.send(mensaje)
    except Exception as e:
        print(f"No se pudo enviar el mensaje: {e}")

    session.close()

    

@bot.command()
async def Penaltis(ctx, user1:  discord.Member, user2: discord.Member):
    if str(ctx.author.id) not in maestros:
        await ctx.send("No tienes permiso para usar este comando.", ephemeral=True)
        return
    
    await ctx.send(f"🏈 **{user1} y {user2} se enfrentan en una tanda de goles de campo!** 🎯")

    scores = {user1: 0, user2: 0}
    players = [user1, user2]

    # Ronda de 5 intentos
    for round_num in range(1, 6):
        for kicker, defender in [(players[0], players[1]), (players[1], players[0])]:
            kicker_roll = random.randint(1, 6)
            defender_roll = random.randint(1, 6)

            if kicker_roll > defender_roll:
                scores[kicker] += 1
                diff = kicker_roll - defender_roll
                if diff >= 4:
                    await ctx.send(f"🚀 **{kicker} patea con una potencia impresionante!** ¡Touchdown anotado! 🏈(Tirada: {kicker_roll} vs {defender_roll}) ")
                elif diff == 3:
                    await ctx.send(f"🔥 **{kicker} engaña al defensor con un disparo magistral!** ¡Touchdown! 🏈(Tirada: {kicker_roll} vs {defender_roll}) ")
                elif diff == 2:
                    await ctx.send(f"✨ **{kicker} coloca el balón justo entre los postes.** ¡Touch asegurado! 🥅(Tirada: {kicker_roll} vs {defender_roll}) ")
                else:
                    await ctx.send(f"💥 **{kicker} patea con precisión.** Touchdown exitoso. 🎉(Tirada: {kicker_roll} vs {defender_roll}) ")
            else:
                diff = defender_roll - kicker_roll
                if diff >= 4:
                    await ctx.send(f"🚫 **{defender} bloquea el intento con una parada épica!** ❌(Tirada: {kicker_roll} vs {defender_roll}) ")
                elif diff == 3:
                    await ctx.send(f"🧤 **{defender} se lanza al lugar correcto justo a tiempo!** Bloqueo perfecto. ❌(Tirada: {kicker_roll} vs {defender_roll}) ")
                elif diff == 2:
                    await ctx.send(f"💪 **{defender} logra bloquear el balón con esfuerzo.** No hay gol. ❌(Tirada: {kicker_roll} vs {defender_roll}) ")
                else:
                    await ctx.send(f"😅 **{defender} apenas consigue bloquear el disparo.** Sin gol esta vez. ❌(Tirada: {kicker_roll} vs {defender_roll}) ")

    # Mostrar resultado de la ronda inicial
    await ctx.send(f"🔢 **Resultado tras 5 intentos:** {user1}: {scores[user1]} - {user2}: {scores[user2]} 🏈")

    # Gol de oro si hay empate
    while scores[user1] == scores[user2]:
        await ctx.send("⚡️ ¡Empate! Vamos al Gol de Oro. 🎯")
        for kicker, defender in [(players[0], players[1]), (players[1], players[0])]:
            kicker_roll = random.randint(1, 6)
            defender_roll = random.randint(1, 6)

            if kicker_roll > defender_roll:
                scores[kicker] += 1
                await ctx.send(f"🏈 **{kicker} anota en el Gol de Oro!** 🎉(Tirada: {kicker_roll} vs {defender_roll}) ")
            else:
                await ctx.send(f"❌ **{defender} bloquea el intento en el Gol de Oro.** ❌(Tirada: {kicker_roll} vs {defender_roll}) ")

        # Determinar ganador
        if scores[user1] != scores[user2]:
            break

    # Mostrar ganador
    if scores[user1] > scores[user2]:
        winner, loser = user1, user2
    else:
        winner, loser = user2, user1

    await ctx.send(f"<:Butter_Cup:1184459079368843324> **{winner.mention} gana la tanda de goles de campo contra {loser.mention}!** ¡Enhorabuena! 🎉")

@bot.command(name="actualiza_ediciones")
@commands.has_any_role('Moderadores', 'Administrador', 'Comisario')
async def actualiza_ediciones(ctx, edicion: int):
    """
    Actualiza la tabla equiposReformados y registra estadísticas de partidos jugados en registroPartidos.
    :param edicion: Número de edición a registrar en registroPartidos
    """
    Session = sessionmaker(bind=GestorSQL.conexionEngine())
    session = Session()
    try:
        usuarios = session.query(GestorSQL.Usuario).all()
        for usuario in usuarios:
            # Obtener todos los partidos del calendario para el usuario, ordenados cronológicamente
            calendarios = session.query(GestorSQL.Calendario).filter(
                (GestorSQL.Calendario.coach1 == usuario.idUsuarios) |
                (GestorSQL.Calendario.coach2 == usuario.idUsuarios)
            ).order_by(GestorSQL.Calendario.idCalendario).all()

            # Inicializar contadores y nombre de equipo
            ganados = empatados = perdidos = 0
            equipo_nombre = None

            for calendario in calendarios:
                partido = session.query(GestorSQL.Partidos).filter_by(
                    idPartidos=calendario.partidos_idPartidos
                ).first()
                if not partido:
                    continue

                # Determina scores y nombre de equipo para este usuario
                if calendario.coach1 == usuario.idUsuarios:
                    score_user, score_opp = partido.resultado1, partido.resultado2
                    nombre_actual = partido.nombreEquipo1
                else:
                    score_user, score_opp = partido.resultado2, partido.resultado1
                    nombre_actual = partido.nombreEquipo2

                # Evitar nombres nulos: solo actualiza equipo_nombre si existe un nombre válido
                if nombre_actual:
                    equipo_nombre = nombre_actual

                # Actualiza contadores de resultados
                if score_user > score_opp:
                    ganados += 1
                elif score_user < score_opp:
                    perdidos += 1
                else:
                    empatados += 1

            # Si no hubo ningún nombre válido, se omite la inserción
            if equipo_nombre:
                # Inserta o actualiza en equiposReformados
                equipo = session.query(GestorSQL.equiposReformados).filter_by(
                    id_usuario=usuario.idUsuarios,
                    nombre_equipo=equipo_nombre
                ).first()

                if not equipo:
                    equipo = GestorSQL.equiposReformados(
                        id_usuario=usuario.idUsuarios,
                        nombre_equipo=equipo_nombre,
                        edicionesJugadas=1
                    )
                    session.add(equipo)
                    session.commit()  # Para obtener el id
                else:
                    equipo.edicionesJugadas = 1
                    session.commit()

                # Registra estadísticas de partidos en registroPartidos
                registro = GestorSQL.RegistroPartidos(
                    idEquiposReformados=equipo.id,
                    Edicion=edicion,
                    ganados=ganados,
                    empatados=empatados,
                    perdidos=perdidos,
                    usado=False
                )
                session.add(registro)
                session.commit()

        await ctx.send("Actualización de ediciones y registro de partidos completada.")

    except Exception as e:
        session.rollback()
        await ctx.send(f"Ocurrió un error: {e}")
    finally:
        session.close()

@bot.command(name="verificar_inscripciones")
@commands.has_permissions(administrator=True)  # Opcional: si quieres que solo lo pueda usar un admin
async def verificar_inscripciones(ctx):
    Session = sessionmaker(bind=GestorSQL.conexionEngine())
    session = Session()

    message_id = 1280103345633234987  # ID del mensaje donde los usuarios reaccionan para inscribirse
    role_name = "Butter Cup"         # Nombre del rol a revisar
    canal_inscripciones_id = 1280102673059680316  # ID del canal donde está el mensaje
    canal_inscripciones = bot.get_channel(canal_inscripciones_id)
    inscritos_ids = {
        inscripcion_id[0]
        for inscripcion_id in session.query(GestorSQL.Inscripcion.id_usuario_discord).all()
    }

    # 1. OBTENER EL MENSAJE Y SUS REACCIONES
    try:
        message = await canal_inscripciones.fetch_message(message_id)
    except discord.NotFound:
        await ctx.send(f"No se encontró ningún mensaje con el ID {message_id} en este canal.")
        return
    except discord.Forbidden:
        await ctx.send("No tengo permisos para acceder a este mensaje.")
        return
    except discord.HTTPException:
        await ctx.send("Hubo un error al intentar obtener el mensaje.")
        return

    # 2. RECOGER TODOS LOS USUARIOS QUE REACCIONARON
    reacted_user_ids = set()
    for reaction in message.reactions:
        users = [user async for user in reaction.users()]
        for user in users:
            if not user.bot:
                reacted_user_ids.add(user.id)

    # 3. CONSULTAR QUIÉNES DE LOS QUE REACCIONARON NO ESTÁN EN LA TABLA Inscripcion
    no_finalizaron_inscripcion = []
    for user_id in reacted_user_ids:
        registro = session.query(GestorSQL.Inscripcion).filter_by(id_usuario_discord=user_id).first()
        if not registro:
            no_finalizaron_inscripcion.append(user_id)

    # 4. BUSCAR A TODOS LOS MIEMBROS DEL SERVIDOR CON EL ROL "Butter Cup"
    guild = ctx.guild
    if guild is None:
        await ctx.send("Este comando solo se puede ejecutar en un servidor (guild), no en mensajes privados.")
        return

    butter_role = discord.utils.get(guild.roles, name=role_name)
    if butter_role is None:
        await ctx.send(f"No se encontró el rol `{role_name}` en este servidor.")
        return

    miembros_con_rol = butter_role.members
    no_inscritos_con_rol = []
    for member in miembros_con_rol:
        registro = session.query(GestorSQL.Inscripcion).filter_by(id_usuario_discord=member.id).first()
        if not registro:
            no_inscritos_con_rol.append(member.id)

    # 5. BUSCAR USUARIOS EN LA TABLA Usuarios QUE NO ESTÁN EN Inscripcion
    usuarios_no_repetidos = []
    usuarios = session.query(GestorSQL.Usuario).all()
    for usuario in usuarios:
        if not session.query(GestorSQL.Inscripcion).filter_by(id_usuario_discord=usuario.id_discord).first():
            usuarios_no_repetidos.append(usuario.id_discord)

    # 6. CONSTRUIR EL MENSAJE DE RESPUESTA EN PARTES
    respuesta = []

    if no_finalizaron_inscripcion:
        respuesta.append("**Usuarios que reaccionaron pero no terminaron la inscripción:**")
        for user_id in no_finalizaron_inscripcion:
            respuesta.append(f"- <@{user_id}>")
    else:
        respuesta.append("No hay usuarios que hayan reaccionado y no estén en la tabla de Inscripción.")

    respuesta.append("\n")

    if no_inscritos_con_rol:
        respuesta.append(f"**Miembros con el rol '{role_name}' que no aparecen en la tabla Inscripcion:**")
        for user_id in no_inscritos_con_rol:
            respuesta.append(f"- <@{user_id}>")
    else:
        respuesta.append(f"No hay miembros con el rol '{role_name}' sin inscripción en la tabla.")

    respuesta.append("\n")

    if usuarios_no_repetidos:
        respuesta.append("**Usuarios en la tabla 'Usuarios' que no están inscritos:**")
        for user_id in usuarios_no_repetidos:
            respuesta.append(f"- <@{user_id}>")
    else:
        respuesta.append("Todos los usuarios en la tabla 'Usuarios' están inscritos.")

    respuesta.append("\n")

    if inscritos_ids:
        desertores_inscritos = session.query(GestorSQL.Desertor).filter(
            GestorSQL.Desertor.id_discord.in_(inscritos_ids)
        ).all()
    else:
        desertores_inscritos = []

    if desertores_inscritos:
        respuesta.append("**Usuarios desertores que están inscritos:**")
        for desertor in desertores_inscritos:
            respuesta.append(f"- <@{desertor.id_discord}>")
    else:
        respuesta.append("No hay desertores inscritos.")

    # Enviar la respuesta en partes para evitar el límite de 2000 caracteres
    mensaje_actual = ""
    for linea in respuesta:
        if len(mensaje_actual) + len(linea) + 1 > 2000:
            await ctx.send(mensaje_actual)
            mensaje_actual = ""
        mensaje_actual += linea + "\n"
    
    if mensaje_actual:
        await ctx.send(mensaje_actual)


@bot.command(name="recordar_inscripciones")
@commands.has_permissions(administrator=True)
async def recordar_inscripciones(ctx, solo_objetivo: Optional[int] = None):
    Session = sessionmaker(bind=GestorSQL.conexionEngine())
    session = Session()

    role_name = "Butter Cup"
    guild = ctx.guild

    if guild is None:
        await ctx.send("Este comando solo se puede ejecutar en un servidor (guild), no en mensajes privados.")
        return

    butter_role = discord.utils.get(guild.roles, name=role_name)
    if butter_role is None:
        await ctx.send(f"No se encontró el rol `{role_name}` en este servidor.")
        return

    # IDs de usuarios a los que nunca queremos mandar este recordatorio
    SKIP_REMINDER_IDS = {
        822383329855930388,  # mygaitero
        148860105071263744   # Elkai
    }

    TARGET_REMINDER_IDS = {
        681577610010296372,
        208239645014753280,
    }

    solo_ids_objetivo = str(solo_objetivo) == "1"

    miembros_con_rol = butter_role.members
    if solo_ids_objetivo:
        miembros_con_rol = [member for member in miembros_con_rol if member.id in TARGET_REMINDER_IDS]
    no_inscritos_con_rol = []

    for member in miembros_con_rol:
        if member.id in SKIP_REMINDER_IDS:
            # opcional: loggear a quién saltamos
            print(f"[recordar_inscripciones] Skipped reminder for {member.name} ({member.id})")
            continue

        registro = session.query(GestorSQL.Inscripcion).filter_by(id_usuario_discord=member.id).first()
        if not registro:
            no_inscritos_con_rol.append(member)

    if not no_inscritos_con_rol:
        await ctx.send(f"No hay miembros con el rol '{role_name}' sin inscripción en la tabla.")
        return

    for member in no_inscritos_con_rol:
        try:
            await member.send(
"""
🏆 **BUTTER CUP VII**   
Última temporada hacia los **tickets del Mundial 2026**: de las **3 ediciones** (invierno 2025, primavera 2026 y verano 2026) y todo culminará en un **playoff veraniego**.

⚙️ **Formato**  
• **3 divisiones**: Oro, Plata y Bronce.  
• Los mejores **ascienden de división** cada edición.  
• Los grupos se crean en **packs de 6**.

📅 **Cierre de inscripciones: viernes 24 de Abril**  
No te quedes sin plaza: apúntate en <#1280102673059680316>, **consulta las reglas** y pregunta lo que necesites.

Si solo tienes el rol para estar atento de la copa, no necesitas hacer nada.

Si no quieres recibir más notificaciones mías, escribe a **SrLombard** para que no te moleste más, Pero solo escribiré una vez más antes de ese sábado ;).

¡Te esperamos en la **BUTTER CUP VII**! 🏉✨"""
            )
            await ctx.send(f"Recordatorio enviado a {member.name}")
        except discord.Forbidden:
            await ctx.send(f"No se pudo enviar un mensaje privado a {member.name}. Puede que tenga los mensajes privados desactivados.")
        except discord.HTTPException:
            await ctx.send(f"Hubo un error al intentar enviar un mensaje a {member.name}.")

@bot.command(name="comunicaciones_inscritos")
@commands.has_permissions(administrator=True)
async def comunicaciones_inscritos(ctx, solo_objetivo: Optional[int] = None):
    Session = sessionmaker(bind=GestorSQL.conexionEngine())
    session = Session()

    role_name = "Butter Cup"
    guild = ctx.guild

    if guild is None:
        await ctx.send("Este comando solo se puede ejecutar en un servidor (guild), no en mensajes privados.")
        session.close()
        return

    butter_role = discord.utils.get(guild.roles, name=role_name)
    if butter_role is None:
        await ctx.send(f"No se encontró el rol `{role_name}` en este servidor.")
        session.close()
        return

    TARGET_REMINDER_IDS = {
        681577610010296372,
        208239645014753280,
    }

    solo_ids_objetivo = str(solo_objetivo) == "1"

    miembros_con_rol = butter_role.members
    if solo_ids_objetivo:
        miembros_con_rol = [member for member in miembros_con_rol if member.id in TARGET_REMINDER_IDS]

    inscritos_con_rol = []
    for member in miembros_con_rol:
        registro = session.query(GestorSQL.Inscripcion).filter_by(id_usuario_discord=member.id).first()
        if registro:
            inscritos_con_rol.append(member)

    if not inscritos_con_rol:
        await ctx.send(f"No hay miembros inscritos con el rol '{role_name}'.")
        session.close()
        return

    for member in inscritos_con_rol:
        try:
            await member.send(
"""
📣 **Normas para inscritos - Butter Cup**

Gracias por inscribirte. Te compartimos un recordatorio rápido de normas:

1) Revisa siempre el canal de anuncios y respeta las fechas de cada jornada.
2) Contacta con tu rival con antelación y proponed horario.
3) Juega con deportividad y comunica cualquier incidencia a la organización.
4) Si vas a abandonar o no puedes jugar, avisa cuanto antes.

Este texto es provisional y se puede ajustar cuando quieras.
"""
            )
            await ctx.send(f"Comunicación enviada a {member.name}")
        except discord.Forbidden:
            await ctx.send(f"No se pudo enviar un mensaje privado a {member.name}. Puede que tenga los mensajes privados desactivados.")
        except discord.HTTPException:
            await ctx.send(f"Hubo un error al intentar enviar un mensaje a {member.name}.")
    session.close()

@bot.command(name='comprueba_quedadas')
async def comprueba_quedadas(ctx, enviar_mensaje: int = 0):
    await func_comprueba_quedadas(enviar_mensaje)



async def func_comprueba_quedadas(enviar_mensaje: int = 0):
    Session = sessionmaker(bind=GestorSQL.conexionEngine())
    session = Session()
    try:
        # Obtener las filas relevantes del calendario
        proximos_martes = datetime.now() + timedelta((1 - datetime.now().weekday() + 7) % 7 + 2)  # Calcula el próximo martes

        calendarios = session.query(GestorSQL.Calendario).filter(
            GestorSQL.Calendario.partidos_idPartidos == None,
            GestorSQL.Calendario.canalAsociado != None,
            GestorSQL.Calendario.fechaFinal < proximos_martes,
            GestorSQL.Calendario.fecha == None
        ).all()

        if not calendarios:
            await UtilesDiscord.mensaje_administradores("No se encontraron partidos pendientes de fecha antes del próximo martes.")
            return

        mensajes = []
        mensaje_actual = ""

        # Construir mensajes fragmentados
        for cal in calendarios:
            linea = (
                f"El partido de <@{cal.usuario_coach1.id_discord}> contra <@{cal.usuario_coach2.id_discord}> aún no tiene fecha. "
                f"Puedes acceder al canal: <#{cal.canalAsociado}>\n"
            )
            if len(mensaje_actual) + len(linea) > 1500:
                mensajes.append(mensaje_actual)
                mensaje_actual = ""
            mensaje_actual += linea

        if mensaje_actual:
            mensajes.append(mensaje_actual)

        # Enviar los mensajes fragmentados
        for mensaje in mensajes:
            await UtilesDiscord.mensaje_administradores(mensaje)

        # Enviar mensajes a los canales asociados si se especifica enviar_mensaje
        if enviar_mensaje == 1:
            for cal in calendarios:
                canal = bot.get_channel(cal.canalAsociado)
                if canal:
                    mensaje_canal = (
                        f"🚨 Atención, entrenadores 🚨\n"
                        f"<@{cal.usuario_coach1.id_discord}> y <@{cal.usuario_coach2.id_discord}>, el tiempo corre en contra y no tengo registrada ninguna quedada con el comando /fecha.\n"
                        f"Debéis jugar vuestro partido antes de la fecha límite: <t:{int(cal.fechaFinal.timestamp())}:f>.\n"
                        f"⚠️ Si hay algún problema, no dudéis en contactar a los @comisarios para resolverlo. ¡Gracias! ⚠️"
                    )
                    await canal.send(mensaje_canal)
                    
        if enviar_mensaje == 2:
            for cal in calendarios:
                canal = bot.guild.get_channel(cal.canalAsociado)
                if canal:
                    mensaje_canal = (
                        f"🚨🚨 Atención, entrenadores 🚨🚨\n"
                        f"<@{cal.usuario_coach1.id_discord}> y <@{cal.usuario_coach2.id_discord}>, el tiempo corre en contra y no tengo registrada ninguna quedada con el comando /fecha.\n"
                        f"Debéis jugar vuestro partido antes de la fecha límite: <t:{int(cal.fechaFinal.timestamp())}:f>.\n"
                        f"⚠️ Si hay algún problema, no dudéis en contactar a los @comisarios para resolverlo. ¡Gracias! ⚠️"
                    )
                    await canal.send(mensaje_canal)

    except Exception as e:
        await UtilesDiscord.mensaje_administradores(f"Ocurrió un error al ejecutar el comando: {str(e)}")

    finally:
        session.close()

@bot.command(name='lanzar_reformas')
@commands.has_any_role('Moderadores', 'Administrador', 'Comisario')
async def lanzar_reformas_cmd(ctx):
    await Reformas.lanzar_reformas(bot)
    await ctx.send("Proceso de reformas lanzado. Se han enviado los mensajes correspondientes.")

Session = sessionmaker(bind=GestorSQL.conexionEngine())

@bot.command(name='vincular_equipos_reformados')
@commands.has_any_role('Moderadores', 'Administrador', 'Comisario')
async def vincular_equipos_reformados(ctx):
    """Vincula los equiposReformados pendientes con su roster en Blood Bowl."""
    session = Session()
    try:
        pendientes = session.query(GestorSQL.equiposReformados)\
                          .filter(GestorSQL.equiposReformados.id_equipo == None)\
                          .all()

        for equipo in pendientes:
            usuario_id = equipo.id_usuario
            vinculado = False

            for jornada in range(10, 0, -1):
                cal = session.query(GestorSQL.Calendario)\
                             .filter(
                                 GestorSQL.Calendario.jornada == jornada,
                                 ((GestorSQL.Calendario.coach1 == usuario_id) |
                                  (GestorSQL.Calendario.coach2 == usuario_id)),
                                 GestorSQL.Calendario.partidos_idPartidos != None
                             )\
                             .order_by(GestorSQL.Calendario.idCalendario.desc())\
                             .first()
                if not cal:
                    continue

                partido_db = session.query(GestorSQL.Partidos)\
                                    .filter_by(idPartidos=cal.partidos_idPartidos)\
                                    .first()
                if not partido_db:
                    continue

                nombre = equipo.nombre_equipo
                if nombre not in (partido_db.nombreEquipo1, partido_db.nombreEquipo2):
                    continue

                # Llamada a la API
                respuesta = APIBbowl.obtener_partido_por_uuid(bbowl_API_token, partido_db.idPartidoBbowl)
                match_data = respuesta
                if not match_data or "teams" not in match_data:
                    await ctx.send(f"❌ No se obtuvieron datos válidos de la API para UUID `{partido_db.idPartidoBbowl}`.")
                    vinculado = True
                    break

                roster_id = None
                for team in match_data["teams"]:
                    if team.get("teamname") == nombre:
                        roster_id = team.get("idteamlisting")
                        break

                if roster_id:
                    equipo.id_equipo = roster_id
                    session.commit()
                    await ctx.send(f"✅ Equipo **{nombre}** vinculado al roster `{roster_id}`.")
                else:
                    await ctx.send(f"⚠️ No se encontró `idteamlisting` para **{nombre}** en la respuesta de la API.")

                vinculado = True
                break  # Salimos de la búsqueda de jornadas

            if not vinculado:
                await ctx.send(f"🔍 No se encontró partido previo para **{equipo.nombre_equipo}**.")

    except Exception as e:
        session.rollback()
        await ctx.send(f"🚨 Error durante la vinculación: {e}")
    finally:
        session.close()

@bot.command(name='reformado')
@commands.has_any_role('Moderadores', 'Administrador', 'Comisario')
async def marcar_reformado(ctx, nombre_equipo: str, edicion: int):
    """Marca como usados los registros de un equipo hasta la edición indicada."""
    Session = sessionmaker(bind=GestorSQL.conexionEngine())
    session = Session()
    try:
        equipo = session.query(GestorSQL.equiposReformados).filter(
            func.lower(GestorSQL.equiposReformados.nombre_equipo) == nombre_equipo.lower()
        ).first()
        if not equipo:
            await ctx.send("Equipo no encontrado.")
            return

        registros = session.query(GestorSQL.RegistroPartidos).filter(
            GestorSQL.RegistroPartidos.idEquiposReformados == equipo.id,
            GestorSQL.RegistroPartidos.Edicion <= edicion
        ).all()

        if not registros:
            await ctx.send("No hay registros a actualizar.")
        else:
            for r in registros:
                r.usado = True
            session.commit()
            await ctx.send(f"Registros de {nombre_equipo} hasta la edición {edicion} marcados como usados.")
    except Exception as e:
        session.rollback()
        await ctx.send(f"Error al marcar reformado: {e}")
    finally:
        session.close()

@bot.tree.command(name="reforma", description="Inicia el proceso de reforma de tu equipo")
async def Reforma(interaction: discord.Interaction):
    # Solo en privado
    if interaction.channel.type is not discord.ChannelType.private:
        await interaction.response.send_message(
            "¡¡Por privado cenutrio!!", ephemeral=True
        )
        return

    # Llamar a la lógica en Reformas.py, pasando el token de la API
    await Reformas.iniciar_reforma(interaction, bbowl_API_token)


def _normalizar_raza(raza: str) -> str:
    if not raza:
        return ""
    return raza.strip().strip(",").lower()


def _generar_contenido_peticiones_razas(session):
    race_mapping = {
        _normalizar_raza(race): (race, emoji)
        for race, emoji in zip(Inscripcion.racesIniciales, Inscripcion.racesConEmojiIniciales)
    }

    preferencias_count = {race: 0 for race in race_mapping}
    existentes_count = {race: 0 for race in race_mapping}

    inscripciones = session.query(GestorSQL.Inscripcion).all()

    total_personas = len(inscripciones)
    numero_razas = 22
    capacidad_por_raza = math.ceil(total_personas / numero_razas + 1)

    for inscripcion in inscripciones:
        if (inscripcion.tipoPreferencia or "").lower() != "nuevo":
            continue

        raza_pref = _normalizar_raza(inscripcion.pref1)
        if raza_pref in preferencias_count:
            preferencias_count[raza_pref] += 1

    for inscripcion in inscripciones:
        if (inscripcion.tipoPreferencia or "").lower() != "existente":
            continue

        usuario = session.query(GestorSQL.Usuario).filter_by(
            id_discord=inscripcion.id_usuario_discord
        ).first()
        if not usuario or not usuario.raza:
            continue

        raza_equipo = _normalizar_raza(usuario.raza)
        if raza_equipo in existentes_count:
            existentes_count[raza_equipo] += 1

    meses_es = [
        "enero",
        "febrero",
        "marzo",
        "abril",
        "mayo",
        "junio",
        "julio",
        "agosto",
        "septiembre",
        "octubre",
        "noviembre",
        "diciembre",
    ]
    ahora = datetime.now()
    fecha_formateada = (
        f"{ahora.day} de {meses_es[ahora.month - 1]} de {ahora.year} "
        f"{ahora.strftime('%H:%M')}"
    )
    lineas_tabla = []
    filas = []

    def pad_display(texto: str, width: int) -> str:
        padding = max(width - wcswidth(texto), 0)
        return texto + (" " * padding)

    for clave_raza, (nombre_raza, emoji) in race_mapping.items():
        existentes = existentes_count.get(clave_raza, 0)
        preferencias = preferencias_count.get(clave_raza, 0)
        total = existentes + preferencias
        filas.append(
            {
                "raza": nombre_raza,
                "total": f"{total}/{capacidad_por_raza}",
                "detalle": f"A E:{existentes} Pref1:{preferencias}",
            }
        )

    ancho_raza = max(wcswidth("Raza"), *(wcswidth(fila["raza"]) for fila in filas))
    ancho_total = max(wcswidth("Total"), *(wcswidth(fila["total"]) for fila in filas))

    lineas_tabla.append(
        f"{pad_display('Raza', ancho_raza)} | {pad_display('Total', ancho_total)} | Detalle"
    )
    lineas_tabla.append(
        f"{'-' * ancho_raza}-+-{'-' * ancho_total}-+{'-' * 40}"
    )

    for fila in filas:
        lineas_tabla.append(
            f"{pad_display(fila['raza'], ancho_raza)} | {pad_display(fila['total'], ancho_total)} | {fila['detalle']}"
        )

    lineas_header = [
        "Lista de peticiones de razas para la sexta temporada actualizada a fecha de "
        f"{fecha_formateada}",
        f"Capacidad estimada por raza: ceil(({total_personas}/{numero_razas}) + 1) = {capacidad_por_raza}",
    ]

    lineas_tabla_contenido = [
        "Tabla detallada de peticiones de razas:",
        "```",
        *lineas_tabla,
        "```",
    ]

    return "\n".join(lineas_header), "\n".join(lineas_tabla_contenido)


async def actualizar_peticiones_razas(
    bot,
    canal_id: int = PETICIONES_RAZAS_CANAL_ID,
    mensaje_header_id: int = PETICIONES_RAZAS_HEADER_MESSAGE_ID,
    mensaje_tabla_id: int = PETICIONES_RAZAS_TABLA_MESSAGE_ID,
):
    Session = sessionmaker(bind=GestorSQL.conexionEngine())
    session = Session()
    try:
        contenido_header, contenido_tabla = _generar_contenido_peticiones_razas(session)

        canal = bot.get_channel(int(canal_id)) if canal_id else None
        if not canal:
            print("No se encontró el canal para actualizar las peticiones de razas.")
            return

        mensaje_header = await canal.fetch_message(int(mensaje_header_id))
        await mensaje_header.edit(content=contenido_header)
        mensaje_tabla = await canal.fetch_message(int(mensaje_tabla_id))
        await mensaje_tabla.edit(content=contenido_tabla)
    except Exception as e:
        print(f"Error al actualizar el mensaje de peticiones de razas: {e}")
    finally:
        session.close()


@bot.command(name="crear_peticiones_razas")
async def crear_peticiones_razas(ctx):
    if str(ctx.author.id) not in maestros:
        await ctx.send("No tienes permiso para usar este comando.")
        return

    Session = sessionmaker(bind=GestorSQL.conexionEngine())
    session = Session()
    try:
        contenido_header, contenido_tabla = _generar_contenido_peticiones_razas(session)
        mensaje_header = await ctx.send(contenido_header)
        mensaje_tabla = await ctx.send(contenido_tabla)
        await ctx.send(
            "Mensajes creados. "
            f"Canal: {ctx.channel.id} | Encabezado: {mensaje_header.id} | Tabla: {mensaje_tabla.id}"
        )
    except Exception as e:
        await ctx.send(f"Error al crear el mensaje de peticiones de razas: {e}")
    finally:
        session.close()


@bot.command(name="suizo_crear")
async def suizo_crear(
    ctx,
    nombre: str,
    rondas: int,
    ida_vuelta: str,
    formato_serie: str,
    fecha_fin: str,
    hora_fin: str,
    canal_hub_id: Optional[int] = None,
):
    if not es_comisario(ctx):
        await ctx.send("No tienes permiso. Este comando es exclusivo para Comisario.")
        return

    if rondas < 1:
        await ctx.send("El número de rondas debe ser mayor o igual a 1.")
        return

    ida_vuelta_normalizado = ida_vuelta.strip().lower()
    if ida_vuelta_normalizado == "ida":
        ida_vuelta_valor = 0
    elif ida_vuelta_normalizado == "idavuelta":
        ida_vuelta_valor = 1
    else:
        await ctx.send("Valor inválido para ida/vuelta. Usa `ida` o `idavuelta`.")
        return

    formato_normalizado = formato_serie.strip().upper()
    if formato_normalizado not in {"BO1", "BO3", "BO5"}:
        await ctx.send("Formato de serie inválido. Usa `bo1`, `bo3` o `bo5`.")
        return

    try:
        fecha_fin_ronda1 = datetime.strptime(f"{fecha_fin} {hora_fin}", "%Y-%m-%d %H:%M")
    except ValueError:
        await ctx.send("Fecha inválida. Usa el formato `YYYY-MM-DD HH:MM`.")
        return

    Session = sessionmaker(bind=GestorSQL.conexionEngine())
    session = Session()
    try:
        ahora = datetime.utcnow()
        nuevo_torneo = GestorSQL.SuizoTorneo(
            nombre=nombre,
            activo=1,
            estado="CREADO",
            rondas_totales=rondas,
            ida_vuelta=ida_vuelta_valor,
            formato_serie=formato_normalizado,
            puntos_win=3,
            puntos_draw=1,
            puntos_loss=0,
            puntos_bye=1.5,
            fecha_fin_ronda1=fecha_fin_ronda1,
            dias_por_ronda=7,
            canal_hub_id=canal_hub_id,
            creado_por_discord_id=ctx.author.id,
            created_at=ahora,
            updated_at=ahora,
        )
        session.add(nuevo_torneo)
        session.commit()
        session.refresh(nuevo_torneo)
    except Exception as e:
        session.rollback()
        await ctx.send(f"No se pudo crear el torneo suizo: {e}")
        return
    finally:
        session.close()

    ida_vuelta_texto = "idavuelta (1)" if ida_vuelta_valor == 1 else "ida (0)"
    canal_hub_texto = canal_hub_id if canal_hub_id is not None else "sin canal"

    await ctx.send(
        "✅ Torneo suizo creado correctamente.\n"
        f"ID torneo: **{nuevo_torneo.id}**\n"
        f"Nombre: **{nombre}**\n"
        f"Rondas: **{rondas}**\n"
        f"Modo: **{ida_vuelta_texto}**\n"
        f"Formato: **{formato_normalizado}**\n"
        f"Fin ronda 1: **{fecha_fin_ronda1.strftime('%Y-%m-%d %H:%M')}**\n"
        f"Canal hub: **{canal_hub_texto}**"
    )


@bot.command(name="suizo_set_puntos")
async def suizo_set_puntos(ctx, torneo_id: int, win: str, draw: str, loss: str, bye: str):
    if not es_comisario(ctx):
        await ctx.send("No tienes permiso. Este comando es exclusivo para Comisario.")
        return

    try:
        puntos_win = Decimal(win)
        puntos_draw = Decimal(draw)
        puntos_loss = Decimal(loss)
        puntos_bye = Decimal(bye)
    except InvalidOperation:
        await ctx.send("Valores inválidos. Usa números válidos para win, draw, loss y bye.")
        return

    if any(valor < 0 for valor in (puntos_win, puntos_draw, puntos_loss, puntos_bye)):
        await ctx.send("Todos los valores deben ser mayores o iguales a 0.")
        return

    if not (puntos_win > puntos_draw >= puntos_loss):
        await ctx.send("Regla inválida: debe cumplirse `win > draw >= loss`.")
        return

    Session = sessionmaker(bind=GestorSQL.conexionEngine())
    session = Session()
    try:
        torneo = session.query(GestorSQL.SuizoTorneo).filter_by(id=torneo_id).first()
        if torneo is None:
            await ctx.send(f"No existe un torneo suizo con ID `{torneo_id}`.")
            return

        if torneo.estado == "FINALIZADO":
            await ctx.send("No se pueden modificar puntos: el torneo está en estado `FINALIZADO`.")
            return

        torneo.puntos_win = puntos_win
        torneo.puntos_draw = puntos_draw
        torneo.puntos_loss = puntos_loss
        torneo.puntos_bye = puntos_bye
        torneo.updated_at = datetime.utcnow()

        session.commit()
        session.refresh(torneo)
    except Exception as e:
        session.rollback()
        await ctx.send(f"No se pudieron actualizar los puntos del torneo: {e}")
        return
    finally:
        session.close()

    await ctx.send(
        "✅ Puntuación del torneo suizo actualizada correctamente.\n"
        f"Torneo ID: **{torneo_id}**\n"
        f"win: **{torneo.puntos_win}** | draw: **{torneo.puntos_draw}** | "
        f"loss: **{torneo.puntos_loss}** | bye: **{torneo.puntos_bye}**"
    )


@bot.command(name="suizo_add_jugador")
async def suizo_add_jugador(ctx, torneo_id: int, usuario: discord.Member, raza_competicion: Optional[str] = None):
    if not es_comisario(ctx):
        await ctx.send("No tienes permiso. Este comando es exclusivo para Comisario.")
        return

    Session = sessionmaker(bind=GestorSQL.conexionEngine())
    session = Session()
    usuario_id_db = None
    try:
        torneo = session.query(GestorSQL.SuizoTorneo).filter_by(id=torneo_id).first()
        if torneo is None:
            await ctx.send(f"No existe un torneo suizo con ID `{torneo_id}`.")
            return

        usuario_bd = session.query(GestorSQL.Usuario).filter_by(id_discord=usuario.id).first()
        if usuario_bd is None:
            await ctx.send(
                f"El usuario {usuario.mention} no está registrado en `usuarios` "
                "(campo `id_discord`)."
            )
            return

        participante_existente = (
            session.query(GestorSQL.SuizoParticipante)
            .filter_by(torneo_id=torneo_id, usuario_id=usuario_bd.idUsuarios)
            .first()
        )
        if participante_existente is not None:
            await ctx.send(
                f"El usuario {usuario.mention} ya está inscrito en el torneo `{torneo_id}`."
            )
            return

        raza_final = raza_competicion if raza_competicion is not None else usuario_bd.raza
        usuario_id_db = usuario_bd.idUsuarios
        nuevo_participante = GestorSQL.SuizoParticipante(
            torneo_id=torneo_id,
            usuario_id=usuario_id_db,
            estado="ACTIVO",
            tiene_bye=0,
            cantidad_byes=0,
            late_join_ronda=None,
            puntos_ajuste_inicial=0,
            raza_competicion=raza_final,
            created_at=datetime.utcnow(),
        )
        session.add(nuevo_participante)
        session.commit()
    except Exception as e:
        session.rollback()
        await ctx.send(f"No se pudo añadir el jugador al torneo suizo: {e}")
        return
    finally:
        session.close()

    raza_texto = raza_final if raza_final else "sin raza definida"
    await ctx.send(
        "✅ Jugador añadido correctamente al torneo suizo.\n"
        f"Torneo ID: **{torneo_id}**\n"
        f"Usuario: {usuario.mention} (idUsuarios: **{usuario_id_db}**)\n"
        f"Raza competición: **{raza_texto}**"
    )


@bot.command(name="suizo_add_lote")
async def suizo_add_lote(ctx, torneo_id: int, *tokens_usuarios: str):
    if not es_comisario(ctx):
        await ctx.send("No tienes permiso. Este comando es exclusivo para Comisario.")
        return

    if not tokens_usuarios:
        await ctx.send(
            "Uso: `!suizo_add_lote <torneo_id> <lista_de_menciones_o_ids_discord>`\n"
            "Ejemplo: `!suizo_add_lote 12 @Usuario1 123456789012345678 <@987654321098765432>`"
        )
        return

    Session = sessionmaker(bind=GestorSQL.conexionEngine())
    session = Session()
    try:
        torneo = session.query(GestorSQL.SuizoTorneo).filter_by(id=torneo_id).first()
        if torneo is None:
            await ctx.send(f"No existe un torneo suizo con ID `{torneo_id}`.")
            return

        total_recibidos = len(tokens_usuarios)
        altas_ok = 0
        duplicados = 0
        no_encontrados = 0
        ids_discord_procesados = set()

        for token in tokens_usuarios:
            token_limpio = token.strip()
            match = re.match(r"^<@!?(\d+)>$", token_limpio)
            if match:
                id_discord_txt = match.group(1)
            else:
                id_discord_txt = token_limpio

            if not id_discord_txt.isdigit():
                no_encontrados += 1
                continue

            id_discord = int(id_discord_txt)
            if id_discord in ids_discord_procesados:
                duplicados += 1
                continue
            ids_discord_procesados.add(id_discord)

            usuario_bd = session.query(GestorSQL.Usuario).filter_by(id_discord=id_discord).first()
            if usuario_bd is None:
                no_encontrados += 1
                continue

            participante_existente = (
                session.query(GestorSQL.SuizoParticipante)
                .filter_by(torneo_id=torneo_id, usuario_id=usuario_bd.idUsuarios)
                .first()
            )
            if participante_existente is not None:
                duplicados += 1
                continue

            raza_final = usuario_bd.raza
            nuevo_participante = GestorSQL.SuizoParticipante(
                torneo_id=torneo_id,
                usuario_id=usuario_bd.idUsuarios,
                estado="ACTIVO",
                tiene_bye=0,
                cantidad_byes=0,
                late_join_ronda=None,
                puntos_ajuste_inicial=0,
                raza_competicion=raza_final,
                created_at=datetime.utcnow(),
            )
            session.add(nuevo_participante)
            altas_ok += 1

        session.commit()
    except Exception as e:
        session.rollback()
        await ctx.send(f"No se pudo procesar el alta masiva en torneo suizo: {e}")
        return
    finally:
        session.close()

    await ctx.send(
        "📦 Resultado de alta masiva en torneo suizo:\n"
        f"Torneo ID: **{torneo_id}**\n"
        f"Total recibidos: **{total_recibidos}**\n"
        f"Altas OK: **{altas_ok}**\n"
        f"Duplicados: **{duplicados}**\n"
        f"No encontrados en `usuarios`: **{no_encontrados}**"
    )


@bot.command(name="suizo_importar_inscripcion")
async def suizo_importar_inscripcion(ctx, torneo_id: int):
    if not es_comisario(ctx):
        await ctx.send("No tienes permiso. Este comando es exclusivo para Comisario.")
        return

    Session = sessionmaker(bind=GestorSQL.conexionEngine())
    session = Session()
    try:
        torneo = session.query(GestorSQL.SuizoTorneo).filter_by(id=torneo_id).first()
        if torneo is None:
            await ctx.send(f"No existe un torneo suizo con ID `{torneo_id}`.")
            return

        inscripciones = session.query(GestorSQL.Inscripcion).all()
        total_inscripciones = len(inscripciones)
        altas_ok = 0
        duplicados = 0
        no_encontrados = 0
        errores = 0
        ids_discord_procesados = set()
        ejemplos_error = []

        for inscripcion in inscripciones:
            id_discord = inscripcion.id_usuario_discord
            if id_discord is None:
                no_encontrados += 1
                continue

            if id_discord in ids_discord_procesados:
                duplicados += 1
                continue
            ids_discord_procesados.add(id_discord)

            try:
                usuario_bd = session.query(GestorSQL.Usuario).filter_by(id_discord=id_discord).first()
                if usuario_bd is None:
                    no_encontrados += 1
                    continue

                participante_existente = (
                    session.query(GestorSQL.SuizoParticipante)
                    .filter_by(torneo_id=torneo_id, usuario_id=usuario_bd.idUsuarios)
                    .first()
                )
                if participante_existente is not None:
                    duplicados += 1
                    continue

                raza_competicion = inscripcion.pref1
                nuevo_participante = GestorSQL.SuizoParticipante(
                    torneo_id=torneo_id,
                    usuario_id=usuario_bd.idUsuarios,
                    estado="ACTIVO",
                    tiene_bye=0,
                    cantidad_byes=0,
                    late_join_ronda=None,
                    puntos_ajuste_inicial=0,
                    raza_competicion=raza_competicion,
                    created_at=datetime.utcnow(),
                )
                session.add(nuevo_participante)
                session.flush()
                altas_ok += 1
            except Exception as e:
                session.rollback()
                errores += 1
                if len(ejemplos_error) < 10:
                    ejemplos_error.append(f"- ID Discord `{id_discord}`: {e}")
                continue

        session.commit()
    except Exception as e:
        session.rollback()
        await ctx.send(f"No se pudo importar inscripciones al torneo suizo: {e}")
        return
    finally:
        session.close()

    mensaje = (
        "📥 Resultado de importación desde `Inscripcion` a torneo suizo:\n"
        f"Torneo ID: **{torneo_id}**\n"
        f"Total inscripciones leídas: **{total_inscripciones}**\n"
        f"Altas OK: **{altas_ok}**\n"
        f"Duplicados (en lote o ya en suizo): **{duplicados}**\n"
        f"No encontrados en `usuarios`: **{no_encontrados}**\n"
        f"Errores: **{errores}**"
    )
    if ejemplos_error:
        mensaje += "\n\n⚠️ Ejemplos de errores (máx. 10):\n" + "\n".join(ejemplos_error)
    await ctx.send(mensaje)


@bot.command(name="suizo_add_tardio")
async def suizo_add_tardio(ctx, torneo_id: int, usuario: discord.Member, raza_competicion: Optional[str] = None):
    if not es_comisario(ctx):
        await ctx.send("No tienes permiso. Este comando es exclusivo para Comisario.")
        return

    Session = sessionmaker(bind=GestorSQL.conexionEngine())
    session = Session()
    try:
        torneo = session.query(GestorSQL.SuizoTorneo).filter_by(id=torneo_id).first()
        if torneo is None:
            await ctx.send(f"No existe un torneo suizo con ID `{torneo_id}`.")
            return

        if torneo.estado == "FINALIZADO":
            await ctx.send("No se puede añadir un jugador tardío: el torneo está en estado `FINALIZADO`.")
            return

        usuario_bd = session.query(GestorSQL.Usuario).filter_by(id_discord=usuario.id).first()
        if usuario_bd is None:
            await ctx.send(
                f"El usuario {usuario.mention} no está registrado en `usuarios` "
                "(campo `id_discord`)."
            )
            return

        participante_existente = (
            session.query(GestorSQL.SuizoParticipante)
            .filter_by(torneo_id=torneo_id, usuario_id=usuario_bd.idUsuarios)
            .first()
        )
        if participante_existente is not None:
            await ctx.send(
                f"El usuario {usuario.mention} ya está inscrito en el torneo `{torneo_id}`."
            )
            return

        ronda_actual = (
            session.query(func.max(GestorSQL.SuizoRonda.numero))
            .filter(GestorSQL.SuizoRonda.torneo_id == torneo_id)
            .scalar()
        ) or 0
        late_join_ronda = int(ronda_actual) + 1

        standings_actuales = calcular_standings(session, torneo_id, hasta_ronda=int(ronda_actual) if ronda_actual > 0 else None)
        participantes_actuales = (
            session.query(GestorSQL.SuizoParticipante)
            .filter(
                GestorSQL.SuizoParticipante.torneo_id == torneo_id,
                GestorSQL.SuizoParticipante.estado == "ACTIVO",
                or_(
                    GestorSQL.SuizoParticipante.late_join_ronda.is_(None),
                    GestorSQL.SuizoParticipante.late_join_ronda <= int(ronda_actual),
                ),
            )
            .all()
        )
        ids_actuales = {int(p.usuario_id) for p in participantes_actuales}
        puntos_base = [
            Decimal(str(fila.get("puntos") or 0))
            for fila in standings_actuales
            if int(fila.get("usuario_id") or 0) in ids_actuales
        ]
        puntos_ajuste_inicial = (sum(puntos_base, Decimal("0")) / Decimal(len(puntos_base))) if puntos_base else Decimal("0")
        puntos_ajuste_inicial = puntos_ajuste_inicial.quantize(Decimal("0.01"))

        raza_final = raza_competicion if raza_competicion is not None else usuario_bd.raza
        nuevo_participante = GestorSQL.SuizoParticipante(
            torneo_id=torneo_id,
            usuario_id=usuario_bd.idUsuarios,
            estado="ACTIVO",
            tiene_bye=0,
            cantidad_byes=0,
            late_join_ronda=late_join_ronda,
            puntos_ajuste_inicial=puntos_ajuste_inicial,
            raza_competicion=raza_final,
            created_at=datetime.utcnow(),
        )
        session.add(nuevo_participante)
        session.commit()
    except Exception as e:
        session.rollback()
        await ctx.send(f"No se pudo añadir el jugador tardío al torneo suizo: {e}")
        return
    finally:
        session.close()

    raza_texto = raza_final if raza_final else "sin raza definida"
    await ctx.send(
        "✅ Jugador tardío añadido correctamente al torneo suizo.\n"
        f"Torneo ID: **{torneo_id}**\n"
        f"Usuario: {usuario.mention} (idUsuarios: **{usuario_bd.idUsuarios}**)\n"
        f"Raza competición: **{raza_texto}**\n"
        f"Puntos ajuste inicial: **{puntos_ajuste_inicial}**\n"
        f"Entra desde ronda: **{late_join_ronda}**"
    )


def _normalizar_nombre_canal_suizo(nombre: str) -> str:
    nombre_base = re.sub(r"\s+", "-", (nombre or "").strip().lower())
    nombre_base = re.sub(r"[^a-z0-9-]", "", nombre_base)
    nombre_base = re.sub(r"-{2,}", "-", nombre_base).strip("-")
    return nombre_base or "jugador"


def _partidos_requeridos_desde_formato(formato_serie: str) -> int:
    formato = (formato_serie or "BO1").upper()
    if formato == "BO3":
        return 3
    if formato == "BO5":
        return 5
    return 1


SUIZO_CATEGORIAS_CANALES_PARTIDOS = [
    1497290792241205460,
    1497290892002857082,
    1497290952530727013,
]
SUIZO_MAX_CANALES_POR_CATEGORIA = 25


def _seleccionar_categoria_suizo_para_partido(guild, conteo_nuevos_canales):
    if guild is None:
        return None

    for categoria_id in SUIZO_CATEGORIAS_CANALES_PARTIDOS:
        categoria = guild.get_channel(int(categoria_id))
        if categoria is None:
            continue
        existentes = len(getattr(categoria, "channels", []) or [])
        nuevos = conteo_nuevos_canales.get(int(categoria_id), 0)
        if existentes + nuevos < SUIZO_MAX_CANALES_POR_CATEGORIA:
            conteo_nuevos_canales[int(categoria_id)] = nuevos + 1
            return categoria
    return None


def _nombre_usuario_suizo(usuario) -> str:
    if usuario is None:
        return "N/D"
    return (
        getattr(usuario, "nombreAMostrar", None)
        or getattr(usuario, "nombre_discord", None)
        or getattr(usuario, "nombre_bloodbowl", None)
        or f"u{getattr(usuario, 'idUsuarios', '??')}"
    )


def _tabla_compacta(columnas, filas) -> str:
    anchos = [len(str(c)) for c in columnas]
    for fila in filas:
        for idx, celda in enumerate(fila):
            anchos[idx] = max(anchos[idx], len(str(celda)))

    cabecera = " | ".join(str(columnas[i]).ljust(anchos[i]) for i in range(len(columnas)))
    separador = "-+-".join("-" * anchos[i] for i in range(len(columnas)))
    cuerpo = [
        " | ".join(str(fila[i]).ljust(anchos[i]) for i in range(len(columnas)))
        for fila in filas
    ]
    return "\n".join([cabecera, separador, *cuerpo]) if cuerpo else "\n".join([cabecera, separador, "(sin filas)"])


def _resolver_ronda_suizo(session, torneo_id: int, ronda: Optional[int]):
    if ronda is not None:
        return (
            session.query(GestorSQL.SuizoRonda)
            .filter_by(torneo_id=torneo_id, numero=ronda)
            .first()
        )
    return (
        session.query(GestorSQL.SuizoRonda)
        .filter_by(torneo_id=torneo_id)
        .order_by(GestorSQL.SuizoRonda.numero.desc())
        .first()
    )


@bot.tree.command(name="suizo_consulta_clasificacion", description="Consulta clasificación de torneo suizo")
async def suizo_consulta_clasificacion(interaction: discord.Interaction, torneo_id: int, ronda: Optional[int] = None):
    Session = sessionmaker(bind=GestorSQL.conexionEngine())
    session = Session()
    try:
        torneo = session.query(GestorSQL.SuizoTorneo).filter_by(id=torneo_id).first()
        if torneo is None:
            await interaction.response.send_message(f"No existe un torneo suizo con ID `{torneo_id}`.", ephemeral=True)
            return

        hasta_ronda = int(ronda) if ronda is not None else None
        standings = calcular_standings(session, torneo_id, hasta_ronda=hasta_ronda)
        if not standings:
            await interaction.response.send_message("No hay datos de clasificación para ese torneo/ronda.")
            return

        usuarios_ids = [int(fila["usuario_id"]) for fila in standings]
        usuarios = session.query(GestorSQL.Usuario).filter(GestorSQL.Usuario.idUsuarios.in_(usuarios_ids)).all()
        por_id = {u.idUsuarios: u for u in usuarios}

        filas = []
        for fila in standings:
            usuario_id = int(fila["usuario_id"])
            nombre = _nombre_usuario_suizo(por_id.get(usuario_id))
            estado = str(fila.get("estado_participante") or "ACTIVO")
            filas.append([
                fila.get("rank"),
                nombre,
                estado,
                fila.get("pj"),
                fila.get("pg"),
                fila.get("pe"),
                fila.get("pp"),
                fila.get("puntos"),
                fila.get("buchholz_cut"),
                fila.get("diff_score"),
            ])

        tabla = _tabla_compacta(
            ["#", "Jugador", "Estado", "PJ", "PG", "PE", "PP", "PTS", "BH", "DIF"],
            filas,
        )
        ronda_label = ronda if ronda is not None else "actual"
        await interaction.response.send_message(
            f"**Clasificación suizo** torneo `{torneo_id}` (ronda: {ronda_label})\n```{tabla}```"
        )
    except Exception as e:
        if interaction.response.is_done():
            await interaction.followup.send(f"Error consultando clasificación suiza: {e}", ephemeral=True)
        else:
            await interaction.response.send_message(f"Error consultando clasificación suiza: {e}", ephemeral=True)
    finally:
        session.close()


@bot.tree.command(name="suizo_consulta_jugador", description="Consulta detalle de un jugador en torneo suizo")
async def suizo_consulta_jugador(interaction: discord.Interaction, torneo_id: int, jugador: str):
    Session = sessionmaker(bind=GestorSQL.conexionEngine())
    session = Session()
    try:
        torneo = session.query(GestorSQL.SuizoTorneo).filter_by(id=torneo_id).first()
        if torneo is None:
            await interaction.response.send_message(f"No existe un torneo suizo con ID `{torneo_id}`.", ephemeral=True)
            return

        usuario = None
        if jugador.isdigit():
            usuario = (
                session.query(GestorSQL.Usuario)
                .filter(
                    or_(
                        GestorSQL.Usuario.idUsuarios == int(jugador),
                        GestorSQL.Usuario.id_discord == int(jugador),
                    )
                )
                .first()
            )

        if usuario is None:
            usuario = (
                session.query(GestorSQL.Usuario)
                .filter(
                    or_(
                        GestorSQL.Usuario.nombreAMostrar == jugador,
                        GestorSQL.Usuario.nombre_discord == jugador,
                        GestorSQL.Usuario.nombre_bloodbowl == jugador,
                    )
                )
                .first()
            )

        if usuario is None:
            await interaction.response.send_message(f"No se encontró jugador `{jugador}`.", ephemeral=True)
            return

        participante = (
            session.query(GestorSQL.SuizoParticipante)
            .filter_by(torneo_id=torneo_id, usuario_id=usuario.idUsuarios)
            .first()
        )
        if participante is None:
            await interaction.response.send_message(
                f"El jugador `{_nombre_usuario_suizo(usuario)}` no participa en el torneo `{torneo_id}`."
            )
            return

        emparejamientos = (
            session.query(GestorSQL.SuizoEmparejamiento, GestorSQL.SuizoRonda)
            .join(GestorSQL.SuizoRonda, GestorSQL.SuizoRonda.id == GestorSQL.SuizoEmparejamiento.ronda_id)
            .filter(
                GestorSQL.SuizoEmparejamiento.torneo_id == torneo_id,
                or_(
                    GestorSQL.SuizoEmparejamiento.coach1_usuario_id == usuario.idUsuarios,
                    GestorSQL.SuizoEmparejamiento.coach2_usuario_id == usuario.idUsuarios,
                ),
            )
            .order_by(GestorSQL.SuizoRonda.numero.asc(), GestorSQL.SuizoEmparejamiento.mesa_numero.asc())
            .all()
        )

        filas = []
        for emp, ronda_db in emparejamientos:
            es_c1 = int(emp.coach1_usuario_id) == int(usuario.idUsuarios)
            rival_id = emp.coach2_usuario_id if es_c1 else emp.coach1_usuario_id
            rival = session.query(GestorSQL.Usuario).filter_by(idUsuarios=rival_id).first() if rival_id else None
            rival_part = (
                session.query(GestorSQL.SuizoParticipante)
                .filter_by(torneo_id=torneo_id, usuario_id=rival_id)
                .first()
                if rival_id
                else None
            )
            rival_nombre = "BYE" if emp.es_bye else _nombre_usuario_suizo(rival)
            if rival_part is not None and rival_part.estado == "RETIRADO":
                rival_nombre = f"{rival_nombre} (RETIRADO)"

            score = f"{emp.score_final_c1}-{emp.score_final_c2}" if es_c1 else f"{emp.score_final_c2}-{emp.score_final_c1}"
            filas.append([ronda_db.numero, emp.mesa_numero, rival_nombre, emp.estado, score, emp.puntos_c1 if es_c1 else emp.puntos_c2])

        tabla = _tabla_compacta(["R", "Mesa", "Rival", "Estado", "Score", "Pts"], filas)
        await interaction.response.send_message(
            f"**Jugador:** `{_nombre_usuario_suizo(usuario)}` | Estado: **{participante.estado}**\n```{tabla}```"
        )
    except Exception as e:
        if interaction.response.is_done():
            await interaction.followup.send(f"Error consultando jugador suizo: {e}", ephemeral=True)
        else:
            await interaction.response.send_message(f"Error consultando jugador suizo: {e}", ephemeral=True)
    finally:
        session.close()


@bot.tree.command(name="suizo_consulta_ronda", description="Consulta emparejamientos de una ronda suiza")
async def suizo_consulta_ronda(interaction: discord.Interaction, torneo_id: int, ronda: int):
    Session = sessionmaker(bind=GestorSQL.conexionEngine())
    session = Session()
    try:
        ronda_db = _resolver_ronda_suizo(session, torneo_id, ronda)
        if ronda_db is None:
            await interaction.response.send_message(f"No existe la ronda `{ronda}` para torneo `{torneo_id}`.", ephemeral=True)
            return

        participantes = session.query(GestorSQL.SuizoParticipante).filter_by(torneo_id=torneo_id).all()
        estado_participante = {p.usuario_id: p.estado for p in participantes}

        emparejamientos = (
            session.query(GestorSQL.SuizoEmparejamiento)
            .filter_by(torneo_id=torneo_id, ronda_id=ronda_db.id)
            .order_by(GestorSQL.SuizoEmparejamiento.mesa_numero.asc())
            .all()
        )

        filas = []
        for emp in emparejamientos:
            n1 = _nombre_usuario_suizo(emp.coach1_usuario)
            if estado_participante.get(emp.coach1_usuario_id) == "RETIRADO":
                n1 = f"{n1} (RETIRADO)"
            if emp.es_bye or emp.coach2_usuario_id is None:
                n2 = "BYE"
            else:
                n2 = _nombre_usuario_suizo(emp.coach2_usuario)
                if estado_participante.get(emp.coach2_usuario_id) == "RETIRADO":
                    n2 = f"{n2} (RETIRADO)"

            filas.append([emp.mesa_numero, n1, n2, emp.estado, f"{emp.score_final_c1}-{emp.score_final_c2}"])

        tabla = _tabla_compacta(["Mesa", "Coach1", "Coach2", "Estado", "Score"], filas)
        await interaction.response.send_message(
            f"**Ronda {ronda_db.numero}** (estado `{ronda_db.estado}`) torneo `{torneo_id}`\n```{tabla}```"
        )
    except Exception as e:
        if interaction.response.is_done():
            await interaction.followup.send(f"Error consultando ronda suiza: {e}", ephemeral=True)
        else:
            await interaction.response.send_message(f"Error consultando ronda suiza: {e}", ephemeral=True)
    finally:
        session.close()


@bot.tree.command(name="suizo_consulta_desempates", description="Consulta criterios de desempate suizo")
async def suizo_consulta_desempates(interaction: discord.Interaction, torneo_id: int, ronda: Optional[int] = None):
    Session = sessionmaker(bind=GestorSQL.conexionEngine())
    session = Session()
    try:
        standings = calcular_standings(session, torneo_id, hasta_ronda=ronda if ronda is not None else None)
        if not standings:
            await interaction.response.send_message("No hay standings para calcular desempates.")
            return

        usuarios_ids = [int(fila["usuario_id"]) for fila in standings]
        usuarios = session.query(GestorSQL.Usuario).filter(GestorSQL.Usuario.idUsuarios.in_(usuarios_ids)).all()
        por_id = {u.idUsuarios: u for u in usuarios}

        filas = []
        for fila in standings:
            uid = int(fila["usuario_id"])
            filas.append([
                fila.get("rank"),
                _nombre_usuario_suizo(por_id.get(uid)),
                fila.get("estado_participante"),
                fila.get("puntos"),
                fila.get("h2h_valor") if fila.get("h2h_valor") is not None else "-",
                fila.get("buchholz_cut"),
                fila.get("diff_score"),
            ])

        tabla = _tabla_compacta(["#", "Jugador", "Estado", "PTS", "H2H", "BH", "DIF"], filas)
        ronda_txt = ronda if ronda is not None else "actual"
        await interaction.response.send_message(
            f"**Desempates** torneo `{torneo_id}` (ronda: {ronda_txt})\n```{tabla}```\n"
            "Orden: puntos > H2H (si aplica) > Buchholz Cut > diferencia de score."
        )
    except Exception as e:
        if interaction.response.is_done():
            await interaction.followup.send(f"Error consultando desempates suizos: {e}", ephemeral=True)
        else:
            await interaction.response.send_message(f"Error consultando desempates suizos: {e}", ephemeral=True)
    finally:
        session.close()


@bot.tree.command(name="suizo_consulta_estado_canales", description="Consulta estado de canales por ronda suiza")
async def suizo_consulta_estado_canales(interaction: discord.Interaction, torneo_id: int, ronda: Optional[int] = None):
    Session = sessionmaker(bind=GestorSQL.conexionEngine())
    session = Session()
    try:
        ronda_db = _resolver_ronda_suizo(session, torneo_id, ronda)
        if ronda_db is None:
            mensaje_ronda = f"{ronda}" if ronda is not None else "actual"
            await interaction.response.send_message(
                f"No hay ronda `{mensaje_ronda}` para el torneo `{torneo_id}`.",
                ephemeral=True,
            )
            return

        participantes = session.query(GestorSQL.SuizoParticipante).filter_by(torneo_id=torneo_id).all()
        estado_participante = {p.usuario_id: p.estado for p in participantes}

        emparejamientos = (
            session.query(GestorSQL.SuizoEmparejamiento)
            .filter_by(torneo_id=torneo_id, ronda_id=ronda_db.id)
            .order_by(GestorSQL.SuizoEmparejamiento.mesa_numero.asc())
            .all()
        )

        filas = []
        for emp in emparejamientos:
            n1 = _nombre_usuario_suizo(emp.coach1_usuario)
            if estado_participante.get(emp.coach1_usuario_id) == "RETIRADO":
                n1 = f"{n1} (RETIRADO)"

            if emp.es_bye or emp.coach2_usuario is None:
                n2 = "BYE"
            else:
                n2 = _nombre_usuario_suizo(emp.coach2_usuario)
                if estado_participante.get(emp.coach2_usuario_id) == "RETIRADO":
                    n2 = f"{n2} (RETIRADO)"

            canal = emp.canal_id if emp.canal_id else "-"
            estado_canal = "SIN_CANAL" if not emp.canal_id else ("ABIERTO" if emp.estado == "PENDIENTE" else "CERRADO")
            filas.append([emp.mesa_numero, n1, n2, canal, estado_canal, emp.estado])

        tabla = _tabla_compacta(["Mesa", "Coach1", "Coach2", "Canal", "EstadoCanal", "EstadoEmp"], filas)
        await interaction.response.send_message(
            f"**Estado de canales** torneo `{torneo_id}`, ronda `{ronda_db.numero}`\n```{tabla}```"
        )
    except Exception as e:
        if interaction.response.is_done():
            await interaction.followup.send(f"Error consultando estado de canales: {e}", ephemeral=True)
        else:
            await interaction.response.send_message(f"Error consultando estado de canales: {e}", ephemeral=True)
    finally:
        session.close()


@bot.command(name="suizo_generar_ronda")
async def suizo_generar_ronda(ctx, torneo_id: int, numero_ronda: int):
    if not es_comisario(ctx):
        await ctx.send("No tienes permiso. Este comando es exclusivo para Comisario.")
        return

    if numero_ronda < 1:
        await ctx.send("El número de ronda debe ser mayor o igual a 1.")
        return

    Session = sessionmaker(bind=GestorSQL.conexionEngine())
    session = Session()
    try:
        torneo = session.query(GestorSQL.SuizoTorneo).filter_by(id=torneo_id).first()
        if torneo is None:
            await ctx.send(f"No existe un torneo suizo con ID `{torneo_id}`.")
            return

        if numero_ronda > int(torneo.rondas_totales):
            await ctx.send(
                f"Ronda inválida: el torneo `{torneo_id}` tiene máximo `{torneo.rondas_totales}` rondas."
            )
            return

        ronda_existente = (
            session.query(GestorSQL.SuizoRonda)
            .filter_by(torneo_id=torneo_id, numero=numero_ronda)
            .first()
        )
        if ronda_existente is not None:
            await ctx.send(f"La ronda `{numero_ronda}` ya existe para el torneo `{torneo_id}`.")
            return

        if numero_ronda > 1:
            ronda_anterior = (
                session.query(GestorSQL.SuizoRonda)
                .filter_by(torneo_id=torneo_id, numero=numero_ronda - 1)
                .first()
            )
            if ronda_anterior is None:
                await ctx.send(
                    f"No se puede generar la ronda `{numero_ronda}`: no existe la ronda `{numero_ronda - 1}`."
                )
                return
            if ronda_anterior.estado != "CERRADA":
                await ctx.send(
                    f"No se puede generar la ronda `{numero_ronda}`: la ronda `{numero_ronda - 1}` "
                    f"está en estado `{ronda_anterior.estado}`."
                )
                return
            if ronda_anterior.fecha_fin is None:
                await ctx.send(
                    f"No se puede generar la ronda `{numero_ronda}`: la ronda `{numero_ronda - 1}` "
                    "no tiene `fecha_fin` definida. Corrige la ronda anterior para evitar fechas inconsistentes."
                )
                return

        fecha_inicio = datetime.utcnow()
        fecha_fin = (
            torneo.fecha_fin_ronda1
            if numero_ronda == 1
            else (ronda_anterior.fecha_fin + timedelta(days=7))
        )
        nueva_ronda = GestorSQL.SuizoRonda(
            torneo_id=torneo_id,
            numero=numero_ronda,
            estado="ABIERTA",
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            generada_por_discord_id=ctx.author.id,
        )
        session.add(nueva_ronda)

        if numero_ronda == 1 and torneo.estado == "CREADO":
            torneo.estado = "EN_CURSO"

        session.flush()

        pairings = generar_pairings_backtracking(session, torneo_id, numero_ronda)
        if not pairings:
            session.rollback()
            await ctx.send(
                "No se pudieron generar emparejamientos para la ronda solicitada "
                "(sin solución de pairings)."
            )
            return

        ids_usuarios = set()
        for mesa in pairings:
            ids_usuarios.add(int(mesa["coach1"]))
            if mesa.get("coach2") is not None:
                ids_usuarios.add(int(mesa["coach2"]))

        usuarios = (
            session.query(GestorSQL.Usuario)
            .filter(GestorSQL.Usuario.idUsuarios.in_(ids_usuarios))
            .all()
        )
        usuarios_por_id = {int(u.idUsuarios): u for u in usuarios}
        partidos_requeridos = _partidos_requeridos_desde_formato(torneo.formato_serie)

        emparejamientos_db = []
        for idx, mesa in enumerate(pairings, start=1):
            coach1_id = int(mesa["coach1"])
            coach2_raw = mesa.get("coach2")
            coach2_id = int(coach2_raw) if coach2_raw is not None else None
            es_bye = bool(mesa.get("es_bye", False))
            estado_inicial = "ADMINISTRADO" if es_bye else "PENDIENTE"
            partidos_reportados = partidos_requeridos if es_bye else 0
            puntos_c1 = Decimal(str(torneo.puntos_bye)) if es_bye else Decimal("0")
            resultado_origen = "BYE" if es_bye else None
            emp = GestorSQL.SuizoEmparejamiento(
                torneo_id=torneo_id,
                ronda_id=nueva_ronda.id,
                mesa_numero=idx,
                coach1_usuario_id=coach1_id,
                coach2_usuario_id=coach2_id,
                estado=estado_inicial,
                es_bye=es_bye,
                forfeit_tipo=mesa.get("forfeit_tipo", "NONE"),
                partidos_requeridos=partidos_requeridos,
                partidos_reportados=partidos_reportados,
                score_final_c1=0,
                score_final_c2=0,
                puntos_c1=puntos_c1,
                puntos_c2=0,
                resultado_origen=resultado_origen,
            )
            session.add(emp)
            emparejamientos_db.append(emp)

        session.flush()

        comisario_role = discord.utils.get(ctx.guild.roles, name="Comisario") if ctx.guild else None
        conteo_nuevos_canales_por_categoria = {}

        mesas_resumen = []
        canales_ok = 0
        canales_error = 0

        for emp in emparejamientos_db:
            jugador1 = usuarios_por_id.get(int(emp.coach1_usuario_id))
            jugador2 = usuarios_por_id.get(int(emp.coach2_usuario_id)) if emp.coach2_usuario_id else None

            nombre_jugador1 = _normalizar_nombre_canal_suizo(
                getattr(jugador1, "nombreAMostrar", None) or getattr(jugador1, "nombre_discord", None) or f"u{emp.coach1_usuario_id}"
            )
            nombre_jugador2 = _normalizar_nombre_canal_suizo(
                (getattr(jugador2, "nombreAMostrar", None) or getattr(jugador2, "nombre_discord", None))
                if jugador2
                else "bye"
            )
            nombre_canal = f"r{numero_ronda}-m{emp.mesa_numero}-{nombre_jugador1}-vs-{nombre_jugador2}"[:100]

            canal_creado = None
            if ctx.guild:
                overwrites = {ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False)}
                if comisario_role:
                    overwrites[comisario_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

                miembro1 = (
                    ctx.guild.get_member(int(jugador1.id_discord))
                    if jugador1 is not None and jugador1.id_discord is not None
                    else None
                )
                miembro2 = (
                    ctx.guild.get_member(int(jugador2.id_discord))
                    if jugador2 is not None and jugador2.id_discord is not None
                    else None
                )
                if miembro1:
                    overwrites[miembro1] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
                if miembro2:
                    overwrites[miembro2] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

                try:
                    categoria_destino = _seleccionar_categoria_suizo_para_partido(
                        ctx.guild, conteo_nuevos_canales_por_categoria
                    )
                    if categoria_destino is None:
                        raise RuntimeError("No hay categorías suizas con hueco disponible para crear más canales.")
                    canal_creado = await ctx.guild.create_text_channel(
                        name=nombre_canal,
                        category=categoria_destino,
                        overwrites=overwrites,
                    )
                    emp.canal_id = canal_creado.id
                    canales_ok += 1
                except Exception:
                    canales_error += 1

            nombre_resumen_1 = getattr(jugador1, "nombreAMostrar", None) or getattr(jugador1, "nombre_discord", None) or f"u{emp.coach1_usuario_id}"
            nombre_resumen_2 = (
                getattr(jugador2, "nombreAMostrar", None) or getattr(jugador2, "nombre_discord", None) or f"u{emp.coach2_usuario_id}"
            ) if jugador2 else "BYE"
            canal_txt = f"<#{emp.canal_id}>" if emp.canal_id else "no creado"
            mesas_resumen.append(
                f"Mesa {emp.mesa_numero}: {nombre_resumen_1} vs {nombre_resumen_2} | canal: {canal_txt}"
            )

        session.commit()
        canal_hub_id = int(torneo.canal_hub_id) if torneo.canal_hub_id is not None else None
    except Exception as e:
        session.rollback()
        await ctx.send(f"No se pudo generar la ronda suiza: {e}")
        return
    finally:
        session.close()

    resumen = (
        "✅ Ronda suiza generada.\n"
        f"Torneo: **{torneo_id}** | Ronda: **{numero_ronda}**\n"
        f"Estado ronda: **ABIERTA**\n"
        f"Fecha inicio: **{fecha_inicio.strftime('%Y-%m-%d %H:%M')}**\n"
        f"Fecha fin: **{fecha_fin.strftime('%Y-%m-%d %H:%M')}**\n"
        f"Mesas creadas: **{len(mesas_resumen)}**\n"
        f"Canales creados: **{canales_ok}** | Errores canal: **{canales_error}**\n"
        + "\n".join(mesas_resumen)
    )

    canal_hub = ctx.guild.get_channel(canal_hub_id) if ctx.guild and canal_hub_id else None
    if canal_hub:
        await canal_hub.send(resumen)
        await ctx.send(f"Ronda generada y resumen publicado en <#{canal_hub_id}>.")
    else:
        await ctx.send(resumen)


@bot.command(name="suizo_regenerar_ronda")
async def suizo_regenerar_ronda(ctx, torneo_id: int, numero_ronda: int):
    if not es_comisario(ctx):
        await ctx.send("No tienes permiso. Este comando es exclusivo para Comisario.")
        return

    if numero_ronda < 1:
        await ctx.send("El número de ronda debe ser mayor o igual a 1.")
        return

    Session = sessionmaker(bind=GestorSQL.conexionEngine())
    session = Session()
    try:
        torneo = session.query(GestorSQL.SuizoTorneo).filter_by(id=torneo_id).first()
        if torneo is None:
            await ctx.send(f"No existe un torneo suizo con ID `{torneo_id}`.")
            return

        ronda = (
            session.query(GestorSQL.SuizoRonda)
            .filter_by(torneo_id=torneo_id, numero=numero_ronda)
            .first()
        )
        if ronda is None:
            await ctx.send(f"La ronda `{numero_ronda}` no existe para el torneo `{torneo_id}`.")
            return

        if ronda.estado == "BLOQUEADA":
            await ctx.send(
                f"No se puede regenerar la ronda `{numero_ronda}` porque está **BLOQUEADA**. "
                f"Usa `!suizo_desbloquear_ronda {torneo_id} {numero_ronda}` para habilitar comandos sensibles."
            )
            return

        if ronda.estado != "ABIERTA":
            await ctx.send(
                f"No se puede regenerar la ronda `{numero_ronda}` porque su estado es `{ronda.estado}` y debe estar en `ABIERTA`."
            )
            return

        emparejamientos_actuales = (
            session.query(GestorSQL.SuizoEmparejamiento)
            .filter_by(torneo_id=torneo_id, ronda_id=ronda.id)
            .all()
        )
        if not emparejamientos_actuales:
            await ctx.send(
                f"La ronda `{numero_ronda}` no tiene emparejamientos para regenerar en el torneo `{torneo_id}`."
            )
            return

        ids_emparejamientos = [int(emp.id) for emp in emparejamientos_actuales]
        conteo_games = (
            session.query(GestorSQL.SuizoGame)
            .filter(GestorSQL.SuizoGame.emparejamiento_id.in_(ids_emparejamientos))
            .count()
        )
        if conteo_games > 0:
            await ctx.send(
                f"No se puede regenerar la ronda `{numero_ronda}`: ya hay **{conteo_games}** resultado(s) en `suizo_game`."
            )
            return

        conteo_cerradas_admin = (
            session.query(GestorSQL.SuizoEmparejamiento)
            .filter(
                GestorSQL.SuizoEmparejamiento.torneo_id == torneo_id,
                GestorSQL.SuizoEmparejamiento.ronda_id == ronda.id,
                GestorSQL.SuizoEmparejamiento.estado.in_(["ADMINISTRADO", "CERRADO"]),
            )
            .count()
        )
        if conteo_cerradas_admin > 0:
            await ctx.send(
                f"No se puede regenerar la ronda `{numero_ronda}`: hay mesas en estado `ADMINISTRADO` o `CERRADO`."
            )
            return

        canales_a_borrar = [int(emp.canal_id) for emp in emparejamientos_actuales if emp.canal_id is not None]
        canales_eliminados = 0
        canales_no_encontrados = 0
        canales_error = 0
        for canal_id in canales_a_borrar:
            canal = ctx.guild.get_channel(canal_id) if ctx.guild else None
            if canal is None:
                canales_no_encontrados += 1
                continue
            try:
                await canal.delete()
                canales_eliminados += 1
            except Exception:
                canales_error += 1

        (
            session.query(GestorSQL.SuizoEmparejamiento)
            .filter_by(torneo_id=torneo_id, ronda_id=ronda.id)
            .delete(synchronize_session=False)
        )
        (
            session.query(GestorSQL.SuizoPairingTrace)
            # Usamos `ronda.id` (PK de `suizo_ronda`) en lugar de `numero_ronda`
            # porque el trace se relaciona por FK con la ronda concreta.
            .filter_by(torneo_id=torneo_id, ronda_id=ronda.id)
            .delete(synchronize_session=False)
        )
        session.flush()

        pairings = generar_pairings_backtracking(session, torneo_id, numero_ronda)
        if not pairings:
            session.rollback()
            await ctx.send(
                "No se pudieron regenerar emparejamientos para la ronda solicitada "
                "(sin solución de pairings)."
            )
            return

        ids_usuarios = set()
        for mesa in pairings:
            ids_usuarios.add(int(mesa["coach1"]))
            if mesa.get("coach2") is not None:
                ids_usuarios.add(int(mesa["coach2"]))

        usuarios = (
            session.query(GestorSQL.Usuario)
            .filter(GestorSQL.Usuario.idUsuarios.in_(ids_usuarios))
            .all()
        )
        usuarios_por_id = {int(u.idUsuarios): u for u in usuarios}
        partidos_requeridos = _partidos_requeridos_desde_formato(torneo.formato_serie)

        emparejamientos_db = []
        for idx, mesa in enumerate(pairings, start=1):
            coach1_id = int(mesa["coach1"])
            coach2_raw = mesa.get("coach2")
            coach2_id = int(coach2_raw) if coach2_raw is not None else None
            es_bye = bool(mesa.get("es_bye", False))
            estado_inicial = "ADMINISTRADO" if es_bye else "PENDIENTE"
            partidos_reportados = partidos_requeridos if es_bye else 0
            puntos_c1 = Decimal(str(torneo.puntos_bye)) if es_bye else Decimal("0")
            resultado_origen = "BYE" if es_bye else None
            emp = GestorSQL.SuizoEmparejamiento(
                torneo_id=torneo_id,
                ronda_id=ronda.id,
                mesa_numero=idx,
                coach1_usuario_id=coach1_id,
                coach2_usuario_id=coach2_id,
                estado=estado_inicial,
                es_bye=es_bye,
                forfeit_tipo=mesa.get("forfeit_tipo", "NONE"),
                partidos_requeridos=partidos_requeridos,
                partidos_reportados=partidos_reportados,
                score_final_c1=0,
                score_final_c2=0,
                puntos_c1=puntos_c1,
                puntos_c2=0,
                resultado_origen=resultado_origen,
            )
            session.add(emp)
            emparejamientos_db.append(emp)
        session.flush()

        comisario_role = discord.utils.get(ctx.guild.roles, name="Comisario") if ctx.guild else None
        conteo_nuevos_canales_por_categoria = {}
        canales_creados = 0
        canales_creacion_error = 0
        mesas_resumen = []

        for emp in emparejamientos_db:
            jugador1 = usuarios_por_id.get(int(emp.coach1_usuario_id))
            jugador2 = usuarios_por_id.get(int(emp.coach2_usuario_id)) if emp.coach2_usuario_id else None

            nombre_jugador1 = _normalizar_nombre_canal_suizo(
                getattr(jugador1, "nombreAMostrar", None) or getattr(jugador1, "nombre_discord", None) or f"u{emp.coach1_usuario_id}"
            )
            nombre_jugador2 = _normalizar_nombre_canal_suizo(
                (getattr(jugador2, "nombreAMostrar", None) or getattr(jugador2, "nombre_discord", None))
                if jugador2
                else "bye"
            )
            nombre_canal = f"r{numero_ronda}-m{emp.mesa_numero}-{nombre_jugador1}-vs-{nombre_jugador2}"[:100]

            canal_creado = None
            if ctx.guild:
                overwrites = {ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False)}
                if comisario_role:
                    overwrites[comisario_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

                miembro1 = (
                    ctx.guild.get_member(int(jugador1.id_discord))
                    if jugador1 is not None and jugador1.id_discord is not None
                    else None
                )
                miembro2 = (
                    ctx.guild.get_member(int(jugador2.id_discord))
                    if jugador2 is not None and jugador2.id_discord is not None
                    else None
                )
                if miembro1:
                    overwrites[miembro1] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
                if miembro2:
                    overwrites[miembro2] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

                try:
                    categoria_destino = _seleccionar_categoria_suizo_para_partido(
                        ctx.guild, conteo_nuevos_canales_por_categoria
                    )
                    if categoria_destino is None:
                        raise RuntimeError("No hay categorías suizas con hueco disponible para crear más canales.")
                    canal_creado = await ctx.guild.create_text_channel(
                        name=nombre_canal,
                        category=categoria_destino,
                        overwrites=overwrites,
                    )
                    emp.canal_id = canal_creado.id
                    canales_creados += 1
                except Exception:
                    canales_creacion_error += 1

            nombre_resumen_1 = getattr(jugador1, "nombreAMostrar", None) or getattr(jugador1, "nombre_discord", None) or f"u{emp.coach1_usuario_id}"
            nombre_resumen_2 = (
                getattr(jugador2, "nombreAMostrar", None) or getattr(jugador2, "nombre_discord", None) or f"u{emp.coach2_usuario_id}"
            ) if jugador2 else "BYE"
            canal_txt = f"<#{emp.canal_id}>" if emp.canal_id else "no creado"
            mesas_resumen.append(
                f"Mesa {emp.mesa_numero}: {nombre_resumen_1} vs {nombre_resumen_2} | canal: {canal_txt}"
            )

        session.commit()
    except Exception as e:
        session.rollback()
        await ctx.send(f"No se pudo regenerar la ronda suiza: {e}")
        return
    finally:
        session.close()

    await ctx.send(
        "♻️ Ronda regenerada correctamente.\n"
        f"Torneo: **{torneo_id}** | Ronda: **{numero_ronda}**\n"
        f"Emparejamientos regenerados: **{len(mesas_resumen)}**\n"
        f"Canales borrados: **{canales_eliminados}** | No encontrados: **{canales_no_encontrados}** | Error al borrar: **{canales_error}**\n"
        f"Canales creados: **{canales_creados}** | Error al crear: **{canales_creacion_error}**\n"
        + "\n".join(mesas_resumen)
    )


@bot.command(name="suizo_bloquear_ronda")
async def suizo_bloquear_ronda(ctx, torneo_id: int, numero_ronda: int):
    if not es_comisario(ctx):
        await ctx.send("No tienes permiso. Este comando es exclusivo para Comisario.")
        return

    if numero_ronda < 1:
        await ctx.send("El número de ronda debe ser mayor o igual a 1.")
        return

    Session = sessionmaker(bind=GestorSQL.conexionEngine())
    session = Session()
    try:
        ronda = (
            session.query(GestorSQL.SuizoRonda)
            .filter_by(torneo_id=torneo_id, numero=numero_ronda)
            .first()
        )
        if ronda is None:
            await ctx.send(f"La ronda `{numero_ronda}` no existe para el torneo `{torneo_id}`.")
            return

        if ronda.estado == "CERRADA":
            await ctx.send(
                f"No se puede bloquear la ronda `{numero_ronda}` porque está en estado `CERRADA`."
            )
            return

        if ronda.estado == "BLOQUEADA":
            await ctx.send(
                f"La ronda `{numero_ronda}` del torneo `{torneo_id}` ya estaba en estado `BLOQUEADA`."
            )
            return

        ronda.estado = "BLOQUEADA"
        session.commit()
    except Exception as e:
        session.rollback()
        await ctx.send(f"No se pudo bloquear la ronda suiza: {e}")
        return
    finally:
        session.close()

    await ctx.send(
        f"🔒 Ronda `{numero_ronda}` del torneo `{torneo_id}` bloqueada. "
        "Se deshabilitan `!suizo_forzar_pairing` y `!suizo_regenerar_ronda`."
    )


@bot.command(name="suizo_desbloquear_ronda")
async def suizo_desbloquear_ronda(ctx, torneo_id: int, numero_ronda: int):
    if not es_comisario(ctx):
        await ctx.send("No tienes permiso. Este comando es exclusivo para Comisario.")
        return

    if numero_ronda < 1:
        await ctx.send("El número de ronda debe ser mayor o igual a 1.")
        return

    Session = sessionmaker(bind=GestorSQL.conexionEngine())
    session = Session()
    try:
        ronda = (
            session.query(GestorSQL.SuizoRonda)
            .filter_by(torneo_id=torneo_id, numero=numero_ronda)
            .first()
        )
        if ronda is None:
            await ctx.send(f"La ronda `{numero_ronda}` no existe para el torneo `{torneo_id}`.")
            return

        if ronda.estado == "CERRADA":
            await ctx.send(
                f"No se puede desbloquear la ronda `{numero_ronda}` porque está en estado `CERRADA`."
            )
            return

        if ronda.estado != "BLOQUEADA":
            await ctx.send(
                f"La ronda `{numero_ronda}` del torneo `{torneo_id}` no está bloqueada (estado actual: `{ronda.estado}`)."
            )
            return

        ronda.estado = "ABIERTA"
        session.commit()
    except Exception as e:
        session.rollback()
        await ctx.send(f"No se pudo desbloquear la ronda suiza: {e}")
        return
    finally:
        session.close()

    await ctx.send(
        f"🔓 Ronda `{numero_ronda}` del torneo `{torneo_id}` desbloqueada. "
        "Vuelven a estar permitidos `!suizo_forzar_pairing` y `!suizo_regenerar_ronda`."
    )


async def post_cierre_suizo(ctx, session, torneo_id: int, cierre: dict):
    if not cierre.get("cerrada"):
        ronda_numero = cierre.get("ronda_numero", "?")
        await ctx.send(
            f"⏳ Ronda **{ronda_numero}** aún abierta en torneo **{torneo_id}**. "
            f"Motivo: **{cierre.get('motivo', 'DESCONOCIDO')}** "
            f"(pendientes: **{cierre.get('pendientes', '?')}**)."
        )
        return

    ronda_numero = cierre.get("ronda_numero", "?")
    await ctx.send(
        f"🏁 Ronda **{ronda_numero}** cerrada en torneo **{torneo_id}**. "
        f"Snapshot standings: **{cierre.get('snapshot_filas', 0)}** filas."
    )

    # Al cerrar la ronda, se eliminan los canales asociados a sus mesas.
    ronda_db = None
    try:
        ronda_numero_int = int(ronda_numero)
    except (TypeError, ValueError):
        ronda_numero_int = None
    if ronda_numero_int is not None:
        ronda_db = (
            session.query(GestorSQL.SuizoRonda)
            .filter_by(torneo_id=torneo_id, numero=ronda_numero_int)
            .first()
        )
    if ronda_db is not None:
        emparejamientos_ronda = (
            session.query(GestorSQL.SuizoEmparejamiento)
            .filter_by(torneo_id=torneo_id, ronda_id=ronda_db.id)
            .all()
        )
        canales_a_borrar = [
            int(emp.canal_id)
            for emp in emparejamientos_ronda
            if getattr(emp, "canal_id", None) is not None
        ]
        canales_eliminados = 0
        canales_no_encontrados = 0
        canales_error = 0

        for canal_id in canales_a_borrar:
            canal = (ctx.guild.get_channel(canal_id) if ctx.guild else None) or bot.get_channel(canal_id)
            if canal is None:
                canales_no_encontrados += 1
                continue
            try:
                await canal.delete()
                canales_eliminados += 1
            except Exception:
                canales_error += 1

        await ctx.send(
            "🧹 Limpieza de canales de la ronda cerrada:\n"
            f"Eliminados: **{canales_eliminados}** | "
            f"No encontrados: **{canales_no_encontrados}** | "
            f"Errores: **{canales_error}**."
        )

    if not cierre.get("es_ultima_ronda"):
        siguiente_ronda = int(cierre.get("siguiente_ronda_numero"))
        await ctx.send(
            f"➡️ Se generará automáticamente la ronda **{siguiente_ronda}** "
            f"del torneo **{torneo_id}**."
        )
        await suizo_generar_ronda(ctx, torneo_id, siguiente_ronda)
        return

    clasificacion = cierre.get("standings") or []
    top = []
    for fila in clasificacion[:16]:
        usuario_id = int(fila.get("usuario_id"))
        usuario = session.query(GestorSQL.Usuario).filter_by(idUsuarios=usuario_id).first()
        nombre = (
            getattr(usuario, "nombreAMostrar", None)
            or getattr(usuario, "nombre_discord", None)
            or f"u{usuario_id}"
        )
        top.append(
            f"**#{fila.get('rank')}** {nombre} — "
            f"{fila.get('puntos')} pts | "
            f"PJ {fila.get('pj')} | "
            f"Dif {fila.get('diff_score')}"
        )

    await ctx.send(
        f"🏆 Torneo **{torneo_id}** finalizado.\n"
        "Clasificación final:\n"
        + ("\n".join(top) if top else "_Sin datos de clasificación._")
    )


async def publicar_resultado_suizo_en_foro(
    ctx,
    torneo,
    ronda_numero: int,
    emparejamiento,
    match: dict,
    local_index: int,
    visitante_index: int,
):
    foro_resultados_id = 1223765590146158653
    canal_foro = discord.utils.get(getattr(ctx.guild, "channels", []), id=foro_resultados_id)
    if not canal_foro or not isinstance(canal_foro, discord.ForumChannel):
        return

    titulo_hilo = f"{torneo.nombre} J{ronda_numero}"
    hilo = None
    for h in canal_foro.threads:
        if h.name == titulo_hilo:
            hilo = h
            break
    if hilo is None:
        nuevo_hilo = await canal_foro.create_thread(
            name=titulo_hilo,
            content=f"Resultados de {titulo_hilo}",
        )
        hilo = nuevo_hilo.thread

    teams = match.get("teams", [])
    team_local = teams[local_index] if len(teams) > local_index else {}
    team_visitante = teams[visitante_index] if len(teams) > visitante_index else {}

    nombre1 = (
        getattr(emparejamiento.coach1_usuario, "nombreAMostrar", None)
        or getattr(emparejamiento.coach1_usuario, "nombre_discord", None)
        or f"u{emparejamiento.coach1_usuario_id}"
    )
    nombre2 = (
        getattr(emparejamiento.coach2_usuario, "nombreAMostrar", None)
        or getattr(emparejamiento.coach2_usuario, "nombre_discord", None)
        or f"u{emparejamiento.coach2_usuario_id}"
    )

    logo_local = str(team_local.get("teamlogo") or "").replace(".png", "")
    logo_visitante = str(team_visitante.get("teamlogo") or "").replace(".png", "")

    score_c1 = int(emparejamiento.score_final_c1 or 0)
    score_c2 = int(emparejamiento.score_final_c2 or 0)
    if score_c1 > score_c2:
        ganador = {"ruta": "./plantillas/Victoria_Izquierda.png", "x": 50, "y": 220}
    elif score_c1 < score_c2:
        ganador = {"ruta": "./plantillas/Victoria_Derecha.png", "x": 1400, "y": 220}
    else:
        ganador = {"ruta": "./plantillas/Empate.png", "x": 729, "y": 241}

    ruta_imagen = Imagenes.crear_imagen(
        "resultado",
        "",
        entrenadores={"0": nombre1, "1": nombre2},
        resultados={"0": score_c1, "1": score_c2},
        escudos={"0": f"Logos/{logo_local}", "1": f"Logos/{logo_visitante}"},
        razas={
            "0": getattr(emparejamiento.coach1_usuario, "raza", "") or "",
            "1": getattr(emparejamiento.coach2_usuario, "raza", "") or "",
        },
        nombre_equipos={
            "0": str(team_local.get("teamname") or "-"),
            "1": str(team_visitante.get("teamname") or "-"),
        },
        kos={
            "0": int(team_visitante.get("inflictedko") or 0),
            "1": int(team_local.get("inflictedko") or 0),
        },
        heridos={
            "0": max(0, int(team_visitante.get("inflictedcasualties") or 0) - int(team_local.get("sustaineddead") or 0)),
            "1": max(0, int(team_local.get("inflictedcasualties") or 0) - int(team_visitante.get("sustaineddead") or 0)),
        },
        muertos={
            "0": int(team_local.get("sustaineddead") or 0),
            "1": int(team_visitante.get("sustaineddead") or 0),
        },
        ganador=ganador,
        grupo={"0": getattr(emparejamiento.coach1_usuario, "grupo", 1) or 1},
        lado={
            "izquierdo": getattr(emparejamiento.coach1_usuario, "color", "#5f8dd3") or "#5f8dd3",
            "derecho": getattr(emparejamiento.coach2_usuario, "color", "#c95f5f") or "#c95f5f",
        },
    )
    if not ruta_imagen:
        return

    with open(ruta_imagen, "rb") as img:
        await hilo.send(file=File(img))
    threading.Timer(10, lambda: Imagenes.eliminar_imagen(ruta_imagen)).start()


@bot.command(name="actualiza_suizo")
async def actualiza_suizo(ctx, torneo_id: int, todos: int = 0):
    if not es_comisario(ctx):
        await ctx.send("No tienes permiso. Este comando es exclusivo para Comisario.")
        return

    Session = sessionmaker(bind=GestorSQL.conexionEngine())
    session = Session()
    try:
        torneo = session.query(GestorSQL.SuizoTorneo).filter_by(id=torneo_id).first()
        if torneo is None:
            await ctx.send(f"No existe un torneo suizo con ID `{torneo_id}`.")
            return

        ronda_abierta = (
            session.query(GestorSQL.SuizoRonda)
            .filter_by(torneo_id=torneo_id, estado="ABIERTA")
            .order_by(GestorSQL.SuizoRonda.numero.asc())
            .first()
        )
        if ronda_abierta is None:
            await ctx.send(f"No hay ronda ABIERTA para el torneo `{torneo_id}`.")
            return

        if not torneo.idCompBbowl:
            await ctx.send(
                f"El torneo `{torneo_id}` no tiene configurado `idCompBbowl` en `suizo_torneo`."
            )
            return

        matches = APIBbowl.obtener_partidos(bbowl_API_token, torneo.idCompBbowl)
        if not matches:
            await ctx.send("No se encontraron partidos en la API para el torneo indicado.")
            return

        total_insertados = 0
        total_duplicados = 0
        total_sin_usuario = 0
        total_sin_emparejamiento = 0
        resultados_publicados = 0

        for match in matches:
            match_id = match.get("uuid")
            if not match_id:
                continue

            game_duplicado = (
                session.query(GestorSQL.SuizoGame)
                .filter_by(id_partido_bbowl=match_id)
                .first()
            )
            if game_duplicado is not None:
                total_duplicados += 1
                if todos == 0:
                    break
                continue

            coaches = match.get("coaches", [])
            if len(coaches) < 2:
                continue

            coach_ids = [coaches[0].get("idcoach"), coaches[1].get("idcoach")]
            usuarios = (
                session.query(GestorSQL.Usuario)
                .filter(GestorSQL.Usuario.id_bloodbowl.in_(coach_ids))
                .all()
            )
            if len(usuarios) != 2:
                total_sin_usuario += 1
                continue

            coach_to_usuario = {str(u.id_bloodbowl): u for u in usuarios}
            coach1_db = coach_to_usuario.get(str(coach_ids[0]))
            coach2_db = coach_to_usuario.get(str(coach_ids[1]))
            if coach1_db is None or coach2_db is None:
                total_sin_usuario += 1
                continue

            posibles_emparejamientos = (
                session.query(GestorSQL.SuizoEmparejamiento)
                .filter_by(
                    torneo_id=torneo_id,
                    ronda_id=ronda_abierta.id,
                    estado="PENDIENTE",
                )
                .filter(
                    or_(
                        and_(
                            GestorSQL.SuizoEmparejamiento.coach1_usuario_id == coach1_db.idUsuarios,
                            GestorSQL.SuizoEmparejamiento.coach2_usuario_id == coach2_db.idUsuarios,
                        ),
                        and_(
                            GestorSQL.SuizoEmparejamiento.coach1_usuario_id == coach2_db.idUsuarios,
                            GestorSQL.SuizoEmparejamiento.coach2_usuario_id == coach1_db.idUsuarios,
                        ),
                    )
                )
                .all()
            )

            emparejamiento = None
            for candidato in posibles_emparejamientos:
                if candidato.partidos_reportados < candidato.partidos_requeridos:
                    emparejamiento = candidato
                    break

            if emparejamiento is None:
                total_sin_emparejamiento += 1
                continue

            coach1_bbowl_id = str(emparejamiento.coach1_usuario.id_bloodbowl)
            local_index = 0 if coach1_bbowl_id == str(coach_ids[0]) else 1
            visitante_index = 1 - local_index
            teams = match.get("teams", [])
            if len(teams) < 2:
                continue

            score_c1 = int(teams[local_index].get("score", 0))
            score_c2 = int(teams[visitante_index].get("score", 0))
            siguiente_index = int(emparejamiento.partidos_reportados) + 1

            nuevo_game = GestorSQL.SuizoGame(
                emparejamiento_id=emparejamiento.id,
                game_index=siguiente_index,
                id_partido_bbowl=match_id,
                score_c1=score_c1,
                score_c2=score_c2,
                origen="API",
                confirmado=True,
                fecha_registro=datetime.utcnow(),
            )
            session.add(nuevo_game)

            emparejamiento.score_final_c1 = int(emparejamiento.score_final_c1 or 0) + score_c1
            emparejamiento.score_final_c2 = int(emparejamiento.score_final_c2 or 0) + score_c2
            emparejamiento.partidos_reportados = int(emparejamiento.partidos_reportados or 0) + 1
            total_insertados += 1

            if emparejamiento.partidos_reportados >= emparejamiento.partidos_requeridos:
                emparejamiento.estado = "CERRADO"
                emparejamiento.resultado_origen = "API"

                puntos_win = Decimal(str(torneo.puntos_win))
                puntos_draw = Decimal(str(torneo.puntos_draw))
                puntos_loss = Decimal(str(torneo.puntos_loss))

                if emparejamiento.score_final_c1 > emparejamiento.score_final_c2:
                    emparejamiento.ganador_usuario_id = emparejamiento.coach1_usuario_id
                    emparejamiento.puntos_c1 = puntos_win
                    emparejamiento.puntos_c2 = puntos_loss
                elif emparejamiento.score_final_c1 < emparejamiento.score_final_c2:
                    emparejamiento.ganador_usuario_id = emparejamiento.coach2_usuario_id
                    emparejamiento.puntos_c1 = puntos_loss
                    emparejamiento.puntos_c2 = puntos_win
                else:
                    emparejamiento.ganador_usuario_id = None
                    emparejamiento.puntos_c1 = puntos_draw
                    emparejamiento.puntos_c2 = puntos_draw

                nombre1 = (
                    getattr(emparejamiento.coach1_usuario, "nombreAMostrar", None)
                    or getattr(emparejamiento.coach1_usuario, "nombre_discord", None)
                    or f"u{emparejamiento.coach1_usuario_id}"
                )
                nombre2 = (
                    getattr(emparejamiento.coach2_usuario, "nombreAMostrar", None)
                    or getattr(emparejamiento.coach2_usuario, "nombre_discord", None)
                    or f"u{emparejamiento.coach2_usuario_id}"
                )
                await ctx.send(
                    f"✅ Resultado registrado (R{ronda_abierta.numero} M{emparejamiento.mesa_numero}): "
                    f"**{nombre1} {emparejamiento.score_final_c1} - {emparejamiento.score_final_c2} {nombre2}**."
                )
                if emparejamiento.canal_id:
                    canal_partido = (
                        ctx.guild.get_channel(int(emparejamiento.canal_id))
                        if ctx.guild
                        else None
                    ) or bot.get_channel(int(emparejamiento.canal_id))
                    if canal_partido is not None:
                        try:
                            await canal_partido.send(
                                f"✅ Resultado registrado (R{ronda_abierta.numero} M{emparejamiento.mesa_numero}): "
                                f"**{nombre1} {emparejamiento.score_final_c1} - {emparejamiento.score_final_c2} {nombre2}**."
                            )
                        except Exception:
                            await ctx.send(
                                f"⚠️ No se pudo publicar el resultado en el canal de mesa `{emparejamiento.canal_id}`."
                            )
                try:
                    await publicar_resultado_suizo_en_foro(
                        ctx,
                        torneo,
                        ronda_abierta.numero,
                        emparejamiento,
                        match,
                        local_index,
                        visitante_index,
                    )
                except Exception:
                    await ctx.send(
                        f"⚠️ No se pudo publicar la imagen del resultado en el foro para la mesa `{emparejamiento.mesa_numero}`."
                    )
                resultados_publicados += 1

            session.commit()

        pendientes = (
            session.query(GestorSQL.SuizoEmparejamiento)
            .filter_by(
                torneo_id=torneo_id,
                ronda_id=ronda_abierta.id,
            )
            .filter(GestorSQL.SuizoEmparejamiento.estado == "PENDIENTE")
            .count()
        )

        if pendientes > 0:
            await ctx.send(
                f"⏳ Ronda {ronda_abierta.numero} aún no completa en torneo {torneo_id}. "
                f"Emparejamientos pendientes: **{pendientes}**."
            )
        else:
            cierre = procesar_cierre_ronda_si_corresponde(session, torneo_id, ronda_abierta.numero)
            session.commit()
            await post_cierre_suizo(ctx, session, torneo_id, cierre)

        await ctx.send(
            "📊 Actualización suiza terminada.\n"
            f"Partidos API insertados: **{total_insertados}**\n"
            f"Duplicados ignorados: **{total_duplicados}**\n"
            f"Sin usuario mapeado: **{total_sin_usuario}**\n"
            f"Sin emparejamiento pendiente: **{total_sin_emparejamiento}**\n"
            f"Resultados publicados: **{resultados_publicados}**"
        )
    except Exception as e:
        session.rollback()
        await ctx.send(f"No se pudo actualizar el suizo: {e}")
    finally:
        session.close()


@bot.command(name="suizo_admin_resultado")
async def suizo_admin_resultado(
    ctx,
    torneo_id: int,
    ronda: int,
    mesa: int,
    tipo: str,
    a: Optional[int] = None,
    b: Optional[int] = None,
):
    if not es_comisario(ctx):
        await ctx.send("No tienes permiso. Este comando es exclusivo para Comisario.")
        return

    tipo_normalizado = (tipo or "").strip().lower()
    tipos_validos = {"forfeit_local", "forfeit_visitante", "empate_admin", "doble_forfeit", "manual"}
    if tipo_normalizado not in tipos_validos:
        await ctx.send(
            "Tipo inválido. Usa uno de: `forfeit_local`, `forfeit_visitante`, `empate_admin`, `doble_forfeit`, `manual`."
        )
        return

    if tipo_normalizado == "manual":
        if a is None or b is None:
            await ctx.send("Para `manual` debes informar score `a b` (ejemplo: `!suizo_admin_resultado 3 2 1 manual 2 1`).")
            return
        if int(a) < 0 or int(b) < 0:
            await ctx.send("El score manual no puede tener valores negativos.")
            return

    Session = sessionmaker(bind=GestorSQL.conexionEngine())
    session = Session()
    try:
        torneo = session.query(GestorSQL.SuizoTorneo).filter_by(id=torneo_id).first()
        if torneo is None:
            await ctx.send(f"No existe un torneo suizo con ID `{torneo_id}`.")
            return

        ronda_db = (
            session.query(GestorSQL.SuizoRonda)
            .filter_by(torneo_id=torneo_id, numero=ronda)
            .first()
        )
        if ronda_db is None:
            await ctx.send(f"No existe la ronda `{ronda}` para el torneo `{torneo_id}`.")
            return
        if ronda_db.estado == "CERRADA":
            await ctx.send(f"La ronda `{ronda}` ya está cerrada; no se puede administrar la mesa `{mesa}`.")
            return

        emp = (
            session.query(GestorSQL.SuizoEmparejamiento)
            .filter_by(torneo_id=torneo_id, ronda_id=ronda_db.id, mesa_numero=mesa)
            .first()
        )
        if emp is None:
            await ctx.send(f"No existe la mesa `{mesa}` en la ronda `{ronda}` del torneo `{torneo_id}`.")
            return
        if emp.es_bye:
            await ctx.send("La mesa indicada es un BYE y no requiere administración manual de resultado.")
            return

        score_c1 = 0
        score_c2 = 0
        puntos_c1 = Decimal("0")
        puntos_c2 = Decimal("0")
        ganador_usuario_id = None
        forfeit_tipo = "NONE"

        puntos_win = Decimal(str(torneo.puntos_win))
        puntos_draw = Decimal(str(torneo.puntos_draw))
        puntos_loss = Decimal(str(torneo.puntos_loss))

        # Los forfaits administrativos respetan la configuración de puntos del torneo.
        # Regla vigente: forfeit_local => win/loss, forfeit_visitante => loss/win,
        # empate_admin => draw/draw y doble_forfeit => 0/0.
        if tipo_normalizado == "forfeit_local":
            score_c1, score_c2 = 1, 0
            puntos_c1, puntos_c2 = puntos_win, puntos_loss
            ganador_usuario_id = emp.coach1_usuario_id
            forfeit_tipo = "LOCAL"
        elif tipo_normalizado == "forfeit_visitante":
            score_c1, score_c2 = 0, 1
            puntos_c1, puntos_c2 = puntos_loss, puntos_win
            ganador_usuario_id = emp.coach2_usuario_id
            forfeit_tipo = "VISITANTE"
        elif tipo_normalizado == "empate_admin":
            score_c1, score_c2 = 0, 0
            puntos_c1, puntos_c2 = puntos_draw, puntos_draw
        elif tipo_normalizado == "doble_forfeit":
            score_c1, score_c2 = 0, 0
            puntos_c1, puntos_c2 = Decimal("0"), Decimal("0")
            forfeit_tipo = "DOBLE"
        else:
            score_c1, score_c2 = int(a), int(b)
            if score_c1 > score_c2:
                puntos_c1, puntos_c2 = puntos_win, puntos_loss
                ganador_usuario_id = emp.coach1_usuario_id
            elif score_c1 < score_c2:
                puntos_c1, puntos_c2 = puntos_loss, puntos_win
                ganador_usuario_id = emp.coach2_usuario_id
            else:
                puntos_c1, puntos_c2 = puntos_draw, puntos_draw

        emp.score_final_c1 = score_c1
        emp.score_final_c2 = score_c2
        emp.puntos_c1 = puntos_c1
        emp.puntos_c2 = puntos_c2
        emp.ganador_usuario_id = ganador_usuario_id
        emp.forfeit_tipo = forfeit_tipo
        emp.partidos_reportados = emp.partidos_requeridos
        emp.estado = "ADMINISTRADO"
        emp.resultado_origen = "ADMIN"

        cierre = procesar_cierre_ronda_si_corresponde(session, torneo_id, ronda)
        session.commit()

        await ctx.send(
            f"✅ Resultado administrado en torneo **{torneo_id}**, ronda **{ronda}**, mesa **{mesa}**.\n"
            f"Tipo: **{tipo_normalizado}** | Score: **{score_c1}-{score_c2}** | "
            f"Puntos: **{puntos_c1}-{puntos_c2}**.\n"
            f"Estado guardado: **ADMINISTRADO** | Origen: **ADMIN**."
        )

        await post_cierre_suizo(ctx, session, torneo_id, cierre)
    except Exception as e:
        session.rollback()
        await ctx.send(f"No se pudo administrar el resultado suizo: {e}")
    finally:
        session.close()


@bot.command(name="suizo_drop")
async def suizo_drop(ctx, torneo_id: int, usuario: discord.Member, *, motivo: str):
    if not es_comisario(ctx):
        await ctx.send("No tienes permiso. Este comando es exclusivo para Comisario.")
        return

    motivo_txt = (motivo or "").strip()
    if not motivo_txt:
        await ctx.send("Debes indicar un motivo para el drop.")
        return

    Session = sessionmaker(bind=GestorSQL.conexionEngine())
    session = Session()
    try:
        torneo = session.query(GestorSQL.SuizoTorneo).filter_by(id=torneo_id).first()
        if torneo is None:
            await ctx.send(f"No existe un torneo suizo con ID `{torneo_id}`.")
            return

        usuario_bd = session.query(GestorSQL.Usuario).filter_by(id_discord=usuario.id).first()
        if usuario_bd is None:
            await ctx.send(
                f"El usuario {usuario.mention} no está registrado en `usuarios` "
                "(campo `id_discord`)."
            )
            return

        participante = (
            session.query(GestorSQL.SuizoParticipante)
            .filter_by(torneo_id=torneo_id, usuario_id=usuario_bd.idUsuarios)
            .first()
        )
        if participante is None:
            await ctx.send(f"El usuario {usuario.mention} no participa en el torneo `{torneo_id}`.")
            return

        participante.estado = "RETIRADO"

        ronda_abierta = (
            session.query(GestorSQL.SuizoRonda)
            .filter_by(torneo_id=torneo_id, estado="ABIERTA")
            .order_by(GestorSQL.SuizoRonda.numero.asc())
            .first()
        )

        emp_actualizado = None
        if ronda_abierta is not None:
            emp_actualizado = (
                session.query(GestorSQL.SuizoEmparejamiento)
                .filter_by(torneo_id=torneo_id, ronda_id=ronda_abierta.id, estado="PENDIENTE")
                .filter(
                    or_(
                        GestorSQL.SuizoEmparejamiento.coach1_usuario_id == usuario_bd.idUsuarios,
                        GestorSQL.SuizoEmparejamiento.coach2_usuario_id == usuario_bd.idUsuarios,
                    )
                )
                .order_by(GestorSQL.SuizoEmparejamiento.mesa_numero.asc())
                .first()
            )

        if emp_actualizado is not None and not emp_actualizado.es_bye:
            puntos_win = Decimal(str(torneo.puntos_win))
            puntos_loss = Decimal(str(torneo.puntos_loss))
            if int(emp_actualizado.coach1_usuario_id) == int(usuario_bd.idUsuarios):
                emp_actualizado.score_final_c1 = 0
                emp_actualizado.score_final_c2 = 1
                emp_actualizado.puntos_c1 = puntos_loss
                emp_actualizado.puntos_c2 = puntos_win
                emp_actualizado.ganador_usuario_id = emp_actualizado.coach2_usuario_id
                emp_actualizado.forfeit_tipo = "VISITANTE"
            else:
                emp_actualizado.score_final_c1 = 1
                emp_actualizado.score_final_c2 = 0
                emp_actualizado.puntos_c1 = puntos_win
                emp_actualizado.puntos_c2 = puntos_loss
                emp_actualizado.ganador_usuario_id = emp_actualizado.coach1_usuario_id
                emp_actualizado.forfeit_tipo = "LOCAL"

            emp_actualizado.partidos_reportados = emp_actualizado.partidos_requeridos
            emp_actualizado.estado = "ADMINISTRADO"
            emp_actualizado.resultado_origen = "ADMIN"

            try:
                if emp_actualizado.canal_id:
                    await UtilesDiscord.gestionar_canal_discord(
                        ctx,
                        "eliminar",
                        canal_id=int(emp_actualizado.canal_id),
                    )
            except Exception:
                pass

        cierre = None
        if ronda_abierta is not None:
            cierre = procesar_cierre_ronda_si_corresponde(session, torneo_id, ronda_abierta.numero)

        session.commit()

        if emp_actualizado is not None and not emp_actualizado.es_bye:
            await ctx.send(
                f"✅ Drop aplicado en torneo **{torneo_id}** para {usuario.mention}.\n"
                f"Motivo: **{motivo_txt}**\n"
                f"Ronda abierta: **{ronda_abierta.numero}**, mesa **{emp_actualizado.mesa_numero}** "
                f"administrada por forfeit (**{emp_actualizado.forfeit_tipo}**) con estado **ADMINISTRADO**."
            )
        elif ronda_abierta is not None and emp_actualizado is not None and emp_actualizado.es_bye:
            await ctx.send(
                f"✅ Drop aplicado en torneo **{torneo_id}** para {usuario.mention}.\n"
                f"Motivo: **{motivo_txt}**\n"
                f"Ronda abierta: **{ronda_abierta.numero}**. La mesa pendiente era BYE, sin ajuste adicional."
            )
        else:
            await ctx.send(
                f"✅ Drop aplicado en torneo **{torneo_id}** para {usuario.mention}.\n"
                f"Motivo: **{motivo_txt}**\n"
                "No se encontró mesa pendiente en ronda abierta para administrar."
            )

        if cierre is not None:
            await post_cierre_suizo(ctx, session, torneo_id, cierre)
    except Exception as e:
        session.rollback()
        await ctx.send(f"No se pudo aplicar el drop suizo: {e}")
    finally:
        session.close()

# Estructura: { "Día": {"Hora": [lista_de_funciones]} }
# tareas_programadas = {
#     "Monday": {
#         "09": [
#             (
#                 func_proximos_partidos_playoff,
#                 {
#                     "bot": bot,
#                     "usuario": maestros[0],
#                     "canal_destino_id": 1224689043032506429,
#                     "respuesta_privada": False
#                 }
#             )
#         ],
#         "10": [
#             (
#                 actualizar_peticiones_razas,
#                 {
#                     "bot": bot
#                 }
#             )
#         ],
#         "22": [
#             (
#                 actualizar_peticiones_razas,
#                 {
#                     "bot": bot
#                 }
#             )
#         ]
#     },
#     "Tuesday": {
#         "09": [
#             (
#                 func_proximos_partidos_playoff,
#                 {
#                     "bot": bot,
#                     "usuario": maestros[0],
#                     "canal_destino_id": 1224689043032506429,
#                     "respuesta_privada": False
#                 }
#             )
#         ],
#         "10": [
#             (
#                 actualizar_peticiones_razas,
#                 {
#                     "bot": bot
#                 }
#             )
#         ],
#         "22": [
#             (
#                 actualizar_peticiones_razas,
#                 {
#                     "bot": bot
#                 }
#             )
#         ]
#     },
#     "Wednesday": {
#         "09": [
#             (
#                 func_proximos_partidos_playoff,
#                 {
#                     "bot": bot,
#                     "usuario": maestros[0],
#                     "canal_destino_id": 1224689043032506429,
#                     "respuesta_privada": False
#                 }
#             )
#         ],
#         "10": [
#             (
#                 actualizar_peticiones_razas,
#                 {
#                     "bot": bot
#                 }
#             )
#         ],
#         "15":[
#             (
#                 func_comprueba_quedadas,
#                 {
#                     "enviar_mensaje" : 1
#                 }
#             )
#
#         ],
#         "22": [
#             (
#                 actualizar_peticiones_razas,
#                 {
#                     "bot": bot
#                 }
#             )
#         ]
#     },
#     "Thursday": {
#         "09": [
#             (
#                 func_proximos_partidos_playoff,
#                 {
#                     "bot": bot,
#                     "usuario": maestros[0],
#                     "canal_destino_id": 1224689043032506429,
#                     "respuesta_privada": False
#                 }
#             )
#         ],
#         "10": [
#             (
#                 actualizar_peticiones_razas,
#                 {
#                     "bot": bot
#                 }
#             )
#         ],
#         "22": [
#             (
#                 actualizar_peticiones_razas,
#                 {
#                     "bot": bot
#                 }
#             )
#         ]
#     },
#     "Friday": {
#         "09": [
#             (
#                 func_proximos_partidos_playoff,
#                 {
#                     "bot": bot,
#                     "usuario": maestros[0],
#                     "canal_destino_id": 1224689043032506429,
#                     "respuesta_privada": False
#                 }
#             )
#         ],
#         "10": [
#             (
#                 actualizar_peticiones_razas,
#                 {
#                     "bot": bot
#                 }
#             )
#         ],
#         "22": [
#             (
#                 actualizar_peticiones_razas,
#                 {
#                     "bot": bot
#                 }
#             )
#         ]
#     },
#     "Saturday": {
#         "09": [
#             (
#                 func_proximos_partidos_playoff,
#                 {
#                     "bot": bot,
#                     "usuario": maestros[0],
#                     "canal_destino_id": 1224689043032506429,
#                     "respuesta_privada": False
#                 }
#             )
#         ],
#         "10": [
#             (
#                 actualizar_peticiones_razas,
#                 {
#                     "bot": bot
#                 }
#             )
#         ],
#         "22": [
#             (
#                 actualizar_peticiones_razas,
#                 {
#                     "bot": bot
#                 }
#             )
#         ]
#     },
#     "Sunday": {
#         "09": [
#             (
#                 func_proximos_partidos_playoff,
#                 {
#                     "bot": bot,
#                     "usuario": maestros[0],
#                     "canal_destino_id": 1224689043032506429,
#                     "respuesta_privada": False
#                 }
#             )
#         ],
#         "10": [
#             (
#                 actualizar_peticiones_razas,
#                 {
#                     "bot": bot
#                 }
#             )
#         ],
#         "22": [
#             (
#                 actualizar_peticiones_razas,
#                 {
#                     "bot": bot
#                 }
#             )
#         ]
#     }
# }

dias_semana = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday"
]

aviso_playoffs = (
    func_proximos_partidos_playoff,
    {
        "bot": bot,
        "usuario": maestros[0],
        "canal_destino_id": 1224689043032506429,
        "respuesta_privada": False
    }
)

actualizacion_peticiones = (
    actualizar_peticiones_razas,
    {
        "bot": bot
    }
)

tareas_programadas = {
    dia: {
        "10": [actualizacion_peticiones],
        "22": [actualizacion_peticiones],
    }
    for dia in dias_semana
}

tareas_programadas["Wednesday"]["15"] = [
    (
        func_comprueba_quedadas,
        {
            "enviar_mensaje": 1
        }
    )
]

        
# Ejecutar el bot con el token correspondiente
bot.run(discord_bot_token)
