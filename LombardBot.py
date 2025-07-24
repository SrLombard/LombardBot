import os
import asyncio
from pickle import LONG
from re import A

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
import tzlocal
import os
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

# Lista de IDs de canales permitidos
canales_permitidos = ['457740100097540106']

# Lista de comandos a los que el bot reaccionará
comandos = ['eco', 'otroComando']


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
                    idNuevoCanal = await UtilesDiscord.gestionar_canal_discord(ctx, "crear", nombre_canal, rival.id_discord, usuario.id_discord, raza1=rival.raza, raza2=usuario.raza, fechalimite=int(calendario.fechaFinal.timestamp()), preferencias1=preferenciasRival, preferencias2=preferenciasUsuario,categoria_id=categoria_id_nuevo)
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
                    ctx, "crear", nombre_canal, rival.id_discord, usuario.id_discord,
                    raza1=rival.raza, raza2=usuario.raza,
                    fechalimite=int(calendario.fechaFinal.timestamp()),
                    preferencias1=preferenciasRival, preferencias2=preferenciasUsuario
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

    canal_id=1251534986348073091

    mensaje = await actualizar_clasificacion(ctx,session, lambda: APIBbowl.obtener_partido_PlayOfTicket(bbowl_API_token), GestorSQL.Ticket, canal_id, todos)
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
            # Construir lista de "nombre_discord (raza)"
            lista_compañeros = [
                f"{c.nombre_discord} ({c.raza or 'raza no asignada'})"
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
            
            mensaje = f"""¡Bienvenido a la Cuarta Edición de la Butter Cup!

Se te han asignado {finalFraseRaza(usuario.raza)}

Tus compañeros esta temporada serán {nombres_compañeros}.

Se creará un canal automáticamente durante la próxima hora donde podrás quedar con tu primer adversario. ¡Recuerda que antes de jugar tienes que pasarte por el canal de Spin para no ser emparejado con otros jugadores! De todas maneras esto lo explicaremos más detalladamente en el canal de la quedada.

Puedes ir creando el equipo si no lo tienes ya hecho. Cuando lo tengas, envíale un privado a Pikoleto o SrLombard para que te manden una invitación.

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
                    mensaje += " Descenderás a la liga de Plata. Recuerda que la próxima edición comienza el 15/9/2025 ^^"
                elif grupo == "Plata":
                    mensaje += " Descenderás a la liga de Bronce. Recuerda que la próxima edición comienza el 15/9/2025 ^^"
                
            try:
                user = await bot.fetch_user(usuario.id_discord)
                if user:
                    await user.send(mensaje)
                    await ctx.send(f"Mensaje enviado a {user.name}#{user.discriminator}")
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
   "3- Se debe avisar a Pikoleto mandandole una imagen del estado del equipo final, además si tienes algún MNG avísale para que lo cure.\n"\
   "4- Se podrá consultar el calendario y los emparejamientos en el discord.\n"\
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
        "Elfos Oscuros": "los sanguinarios **Elfos Oscuros**, utiliza tu astucia y llévale los corazones de tus rivales a Morathi.",
        "Elfos Silvanos": "los ágiles **Elfos Silvanos**, domina el campo con una gracia y velocidad inigualables.",
        "Enano": "los resistentes **Enanos**, deja que tu solidez defensiva y tu poderío ofensivo hablen por ti en el campo.",
        "Hombres Lagarto": "los ágiles y fuertes **Hombres Lagarto**, no tienes nada que temer ya que el Gran Plan te guia.",
        "Horror Nigromántico":"los **Horrores nigrománticos** directamente desde una pelicula de miedo de los 80, aúlla a la luna con tus lobos mientras tus golems paran a un equipo entero.",
        "Humanos": "lo versátiles **Humanos**, adapta tu estrategia a cualquier rival y muestra la habilidad de jugar en cualquier posición.",
        "Inframundo": "el temible equipo del **Inframundo**, usa tus trucos y mutaciones para que no quede nadie.",
        "Nobleza Imperial": "la distinguida **Nobleza Imperial**, utiliza tu elegancia y tácticas refinadas para ganar tus partidos.",
        "No muerto": "los terroríficos **No Muertos**, haz que tus rivales teman enfrentarse a ti tanto en vida como en muerte.",
        "Nurgle": "los repugnantes seguidores de **Nurgle**, usa tu resistencia y habilidades únicas para soportar cualquier cosa mientras pudres a tus oponentes.",
        "Nordicos": "los furiosos **Nórdicos**. Haz que se le encoja el escroto de frío a tus rivales con tus furias mientras las valkirias mueven el balón y los ágiles gorrinos reparten cruzcampo.",
        "Orco": "los poderosos Orcos, grita WAAAAGH! con ellos mientras destrozas a tus rivales.",
        "Orco Negro": "los imponentes **Orcos Negros**, utiliza tu fuerza bruta para dominar el campo de juego mientras tus goblins rematan a tus rivales.",
        "Renegados": "el variopinto equipo de **Renegados**, une a los marginados de todos los rincones para formar un equipo único.",
        "Skaven": "los rápidos y traicioneros **Skaven**, corre por el campo sembrando caos y aprovechando cualquier debilidad.",
        "Stunty":"los epiquisímos **Stunty**, el tamaño no importa y vas a demostrarselo a esos abusones con tu equipo. Estalla a esos grandullones de maneras que nunca han imaginado.",
        "Unión Élfica": "la rapidsíma **Unión Élfica**, humilla a tus enemigos con tu juego de balón y ríete de ellos mientras intentan atraparte."
    }

    # Devuelve el mensaje asociado a la raza, o un mensaje genérico si la raza no está en el diccionario.
    return frases.get(raza, "una raza no identificada, verifica el nombre e inténtalo de nuevo.")
    

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
            response_message = f"Se ha concertado la cita para <t:{timestamp}:F>"
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
    tiempo_desde = datetime.now() - timedelta(minutes=minutos)
    
    try:
        # Realizar la consulta filtrando por fecha
        resultados = session.query(GestorSQL.Spin.fecha, GestorSQL.Spin.user, GestorSQL.Spin.tipo).\
            filter(GestorSQL.Spin.fecha >= tiempo_desde).\
            all()
        
        # Formatear los resultados en Markdown
        tabla_markdown = "```| Fecha                | Usuario | Acción |\n|---------------------|---------|--------|"
        for fecha, usuario, tipo in resultados:
            tabla_markdown += f"\n| {fecha.strftime('%Y-%m-%d %H:%M:%S')} | {usuario} | {tipo} |"
        
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
            
           # Suponiendo que 'usuarios' es una lista de los 6 usuarios de un grupo
            usuarios = session.query(GestorSQL.Usuario).filter(GestorSQL.Usuario.grupo == grupo.id_grupo).all()

            # Verifica que cada grupo tenga 6 usuarios
            if len(usuarios) != 6:
                await ctx.send(f"El grupo {grupo.id_grupo} no tiene 6 usuarios.")
            else:
                partidos = [(0, 1), (2, 3), (4, 5)],[(0,2),(1,5),(3,4)],[(0,3),(1,4),(2,5)],[(0,4),(1,2),(3,5)],[(0,5),(1,3),(2,4)],[(1,0), (3,2), (5,4)],[(2,0),(5,1),(4,3)],[(3,0),(4,1),(5,2)],[(4,0),(2,1),(5,3)],[(5,0),(3,1),(4,2)]
                for i in range(0, 10):
                    # Crea los partidos en la base de datos
                    for partido in partidos[i]:
                        fecha_final = datetime(2025, 5, 18,23,59) + timedelta(weeks=(i))
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
    eventos = session.query(
        GestorSQL.Calendario,
        UsuarioCoach1.nombre_discord.label("nombre_discord1"),
        UsuarioCoach1.raza.label("raza1"),
        UsuarioCoach1.id_discord.label("id_discord1"),
        UsuarioCoach2.nombre_discord.label("nombre_discord2"),
        UsuarioCoach2.id_discord.label("id_discord2"),
        UsuarioCoach2.raza.label("raza2"),
    ).join(
        UsuarioCoach1, GestorSQL.Calendario.coach1 == UsuarioCoach1.idUsuarios
    ).join(
        UsuarioCoach2, GestorSQL.Calendario.coach2 == UsuarioCoach2.idUsuarios
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
        "<@&1217130802572296315>, si os apetece un poco de Blood Bowl estos son los "
        if hay_eventos else "No hay eventos programados en el intervalo dado."
    )

    if hay_eventos:
        mensaje += "próximos partidos:\n\n"
        ids_discord = []
        if eventos:
            for evento in eventos:
                calendario, nd1, raza1, id1, nd2, id2, raza2 = evento
                mensaje += f"**{nd1}** ({raza1}) VS **{nd2}** ({raza2}), <t:{int(calendario.fecha.timestamp())}:f>, Jornada: {calendario.jornada}\n"
                ids_discord.extend([id1, id2])
        if eventos_ticket:
            mensaje += "🎟Ticket🎟\n"
            for evento in eventos_ticket:
                calendario, nd1, raza1, id1, nd2, id2, raza2 = evento
                mensaje += f"**{nd1}** ({raza1}) VS **{nd2}** ({raza2}), <t:{int(calendario.fecha.timestamp())}:f>, Jornada: {calendario.jornada}\n"
                ids_discord.extend([id1, id2])
        mensaje += "\n\n" + mensaje_gracioso(list(set(f"<@{i}>" for i in ids_discord)))

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

            mensaje = """Bienvenidos, {mention1}({raza1}) y {mention2}({raza2})! Estáis en los Play-Offs porque sois lo mejor de lo mejor. RECORDAD inscribir vuestros equipos en la competición PlayOffs3 contraseña PlayOffs3. Los playoff se juegan en formato resurreción, por ello no podréis modificar vuestro equipo después del primer partido. Recordad también que debéis que enviar un pantallazo de como queda vuestro equipo a Pikoleto. \n\n-------------------------------------------""" + mensajePreferencias1 + mensajePreferencias2 +"""
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
            
            RECORDAD inscribir vuestros equipos en la competición PlayOffs4 contraseña PlayOffs4. Los playoff se juegan en formato resurreción, por ello no podréis modificar vuestro equipo después del primer partido. Recordad también que debéis que enviar un pantallazo de como queda vuestro equipo a Pikoleto. \n\n-------------------------------------------""" + mensajePreferencias1 + mensajePreferencias2 +"""
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

    if not eventos_existentes:
        mensaje = "No hay partidos programados en los playoffs durante el intervalo dado."
        try:
            await canal_destino.send(mensaje)
        finally:
            session.close()
        return

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

    await ctx.send(f"<:Butter_Cup:1184459079368843324> **{user1.mention} gana la tanda de goles de campo contra {user2.mention}!** ¡Enhorabuena! 🎉")

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
async def recordar_inscripciones(ctx):
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
        822383329855930388  # mygaitero
    }

    miembros_con_rol = butter_role.members
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
                """Las esperadísimas **inscripciones** para la cuarta temporada de la BUTTER CUPacaban mañana **11 de mayo**. Corre a <#1280102673059680316>  🏃‍♀️💨 y asegura tu plaza 🌟.

Si solo tienes el rol para estar atento de la copa no hace falta que hagas nada.

Si no quieres recibir más notificaciones mías, escribe a SrLombard para no molestarte más.

¡Te esperamos!"""
            )
            await ctx.send(f"Recordatorio enviado a {member.name}")
        except discord.Forbidden:
            await ctx.send(f"No se pudo enviar un mensaje privado a {member.name}. Puede que tenga los mensajes privados desactivados.")
        except discord.HTTPException:
            await ctx.send(f"Hubo un error al intentar enviar un mensaje a {member.name}.")

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

# Estructura: { "Día": {"Hora": [lista_de_funciones]} }
tareas_programadas = {
    "Monday": {
        "09": [
            (
                func_proximos_partidos_playoff,
                {
                    "bot": bot,
                    "usuario": maestros[0],
                    "canal_destino_id": 1224689043032506429,
                    "respuesta_privada": False
                }
            )
        ]
    },
    "Tuesday": {
        "09": [
            (
                func_proximos_partidos_playoff,
                {
                    "bot": bot,
                    "usuario": maestros[0],
                    "canal_destino_id": 1224689043032506429,
                    "respuesta_privada": False
                }
            )
        ]
    },
    "Wednesday": {
        "09": [
            (
                func_proximos_partidos_playoff,
                {
                    "bot": bot,
                    "usuario": maestros[0],
                    "canal_destino_id": 1224689043032506429,
                    "respuesta_privada": False
                }
            )
        ],
        "15":[
            (
                func_comprueba_quedadas,
                {
                    "enviar_mensaje" : 1
                }
            )
            
        ]
    },    
    "Thursday": {
        "09": [
            (
                func_proximos_partidos_playoff,
                {
                    "bot": bot,
                    "usuario": maestros[0],
                    "canal_destino_id": 1224689043032506429,
                    "respuesta_privada": False
                }
            )
        ]
    },
    "Friday": {
        "09": [
            (
                func_proximos_partidos_playoff,
                {
                    "bot": bot,
                    "usuario": maestros[0],
                    "canal_destino_id": 1224689043032506429,
                    "respuesta_privada": False
                }
            )
        ]
    },
    "Saturday": {
        "09": [
            (
                func_proximos_partidos_playoff,
                {
                    "bot": bot,
                    "usuario": maestros[0],
                    "canal_destino_id": 1224689043032506429,
                    "respuesta_privada": False
                }
            )
        ]
    },
    "Sunday": {
        "09": [
            (
                func_proximos_partidos_playoff,
                {
                    "bot": bot,
                    "usuario": maestros[0],
                    "canal_destino_id": 1224689043032506429,
                    "respuesta_privada": False
                }
            )
        ]
    }
}

        
# Ejecutar el bot con el token correspondiente
bot.run(discord_bot_token)

