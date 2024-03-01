from asyncio.windows_events import NULL
import discord
from discord.ext import commands
from discord import File
import os
from dotenv import load_dotenv
import requests
import asyncio
import APIBbowl
import UtilesDiscord
from UtilesDiscord import DiscordClientSingleton
import GestionExcel
import aiohttp
import Imagenes
import threading
import random


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

# Crear e inicializar el bot
bot = DiscordClientSingleton.initialize(discord_bot_token, intents)

#Lista de usuarios con permisos
maestros = ["208239645014753280"]

# Lista de IDs de canales permitidos
canales_permitidos = ['457740100097540106']

# Lista de comandos a los que el bot reaccionará
comandos = ['eco', 'otroComando']

@bot.event
async def on_ready():
    await GestionExcel.ActualizarExcels()

    print(f'{bot.user.name} se ha conectado a Discord!')

@bot.event
async def on_message(message):
    print(message.content)
    print(message.attachments)

    # Evitar que el bot responda a sus propios mensajes
    if message.author == bot.user:
        return
    
    # Comando eco de testeo
    ## Comprobar si el mensaje proviene de un canal permitido
    #if str(message.channel.id) in canales_permitidos:
    #    # Comprobar si el mensaje comienza con alguno de los comandos
    #    for comando in comandos:
    #        if message.content.startswith(f'!{comando}'):
    #            # Realizar acción dependiendo del comando
    #            if comando == 'eco':
    #                # Eliminar el prefijo y enviar el resto del mensaje
    #                await message.channel.send(message.content[len(comando)+2:])
    #            # Añadir aquí más acciones para otros comandos
    await bot.process_commands(message)


@bot.command()
@commands.has_permissions(manage_messages=True)  # Asegúrate de que el usuario tiene permisos.
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


#AddRow agrega una nueva fila, es un comando de prueba tecnica para usar en un futuro
@bot.command()
async def addRow(ctx):
    sheetIds = GestionExcel.sheetIds
    try:
        # Para agregar una nueva fila
        sheetIds.append_row(["Pikoleto", "2", "pikobowl", "12"])


    except Exception as e:
        print(f'Ocurrió un error: {type(e).__name__}, {e.args}')

#Función para agregar las ids de los jugadores a googleSheets
@bot.command()
async def addCoach(ctx, coach_name=None):
    try:
        if coach_name is None:
            await ctx.send("Debes especificar tu usuario de blood bowl después de !addCoach")
            return
    except Exception as e:
        await ctx.send("Debes especificar tu usuario de blood bowl después de !addCoach")
        return

    sheetIds = GestionExcel.sheetIds
    discord_id = str(ctx.author.id)
    discord_name = str(ctx.author)

    # Obtener todas las IDs de Discord de la columna específica
    discord_ids = sheetIds.col_values(2)  

    # Verificar si el usuario ya existe en la hoja de Excel
    if discord_id in discord_ids:
        await ctx.send("Error: Ya estás registrado en la hoja de Excel.")
        return


    player_data = APIBbowl.obtener_entrenadores(bbowl_API_token,coach_name)
    if not player_data:
        await ctx.send(f"No se puedo buscar a {bbowl_name} en el API.")
        return
    bbowl_id = player_data['id']
    bbowl_name = player_data['name']

    # Insertar datos en la hoja de Excel
    row = [discord_name, discord_id, bbowl_name, bbowl_id]
    sheetIds.append_row(row)

    await ctx.send(f"Entrenador {bbowl_name} añadido con éxito.")

@bot.command()
async def recolectarReacciones(ctx, message_id: int):
    sheetIds = GestionExcel.sheetIds
    channel = ctx.channel
    try:
        msg = await channel.fetch_message(message_id)
    except discord.NotFound:
        await ctx.send("Mensaje no encontrado.")
        return
    except discord.Forbidden:
        await ctx.send("No tengo permisos para ver el mensaje.")
        return

    usuarios_unicos = {}
    for reaction in msg.reactions:
        async for user in reaction.users():
            if user.id not in usuarios_unicos:
                usuarios_unicos[user.id] = user.name

    # Leer los IDs existentes para evitar duplicados
    existentes = sheetIds.col_values(2) 

    nuevos_usuarios = []
    for discord_id, discord_name in usuarios_unicos.items():
        if str(discord_id) not in existentes:
            # Prepende un apóstrofo a la ID de Discord para forzar el formato de texto
            nuevos_usuarios.append([discord_name, str(discord_id)])   
            
    if nuevos_usuarios:
        sheetIds.append_rows(nuevos_usuarios)

@bot.command()
async def updateMissingBbowlIds(ctx):
    sheetIds = GestionExcel.sheetIds
    records = sheetIds.get_all_records()  

    rows_to_update = []
    for index, record in enumerate(records, start=2):  # Empieza en 2 para ajustar el índice a las filas de Sheets
        discord_name = record.get("nombre_discord")
        bbowl_name = record.get("nombre_bbowl")
        bbowl_id = record.get("id_bbowl")

        # Verifica si la fila cumple con los criterios especificados
        if discord_name and bbowl_name and not bbowl_id:
            player_data = APIBbowl.obtener_entrenadores(bbowl_API_token,bbowl_name)
            if player_data:
                bbowl_id_new = player_data['id']
                rows_to_update.append((index, bbowl_id_new))
            else:
                await ctx.send(f"No se pudo encontrar el ID de Blood Bowl para {bbowl_name}")

    # Actualiza la hoja de cálculo en una sola llamada por cada fila
    for row_index, bbowl_id_new in rows_to_update:
        sheetIds.update_cell(row_index, 4, bbowl_id_new)
        await asyncio.sleep(10)

    if rows_to_update:
        await ctx.send(f"Se actualizaron {len(rows_to_update)} registros con éxito.")
    else:
        await ctx.send("No se encontraron registros para actualizar.")

#Función para encontrar la última partida de un jugador y publicarla
@bot.command()
async def LastMatch(ctx, arg0=None):
    discord_id = arg0 or ctx.author.id
    id_bbowl = buscar_en_google_sheets(discord_id)  

    if id_bbowl is None:
        await ctx.reply("Por favor, usa el comando !addCoach para registrarte.")
        return

    matches = APIBbowl.obtener_partido_fantasbulosoLadder(bbowl_API_token)

    if not matches:
        await ctx.reply("No se pudo recuperar la lista de usuarios")
        return

    for match in matches:
        propietario = 0
        for coach in match['coaches']:
            if coach['idcoach'] == id_bbowl:     
                    
                embed = UtilesDiscord.crearEmbedPartido(coach,match,propietario)

                await ctx.reply(embed=embed)
                return
            propietario =1

    await ctx.reply("No se ha encontrado ningún partido reciente.")

# Función para buscar el id_bbowl en Google Sheets
def buscar_en_google_sheets(discord_id): 
    sheetIds = GestionExcel.sheetIds
    try:
        valores = sheetIds.get_all_records()  # Obtener todos los registros de la hoja
        for row in valores:
            if row["id_discord"] == discord_id:  
                return row["id_bbowl"]  
    except Exception as e:
        print(f"Error al acceder a Google Sheets: {e}")
    return None

def buscarNombreAMostrar(nombreBB): 
    sheetIds = GestionExcel.sheetIds
    try:
        valores = sheetIds.get_all_records()  # Obtener todos los registros de la hoja
        for row in valores:
            if row["nombre_bbowl"] == nombreBB:  
                return row["nombreAMostrar"]  
    except Exception as e:
        print(f"Error al acceder a Google Sheets: {e}")
    return nombreBB


#comando de Prueba para publicar en hilos
@bot.command()
#async def Prueba(ctx,titulo,*,mensaje):
async def Prueba(ctx):
    #await UtilesDiscord.publicar(ctx,'Jornada ' + titulo + '!',mensaje)
    await UtilesDiscord.menmsaje_administradores('Prueba')
    return


#Comando para agregar partidos al excel para ponernos al día
@bot.command()
async def AgregarPartidos(ctx, arg0=None):
    sheetPartidosJugados = GestionExcel.sheetPartidosJugados
    sheetJornadas = GestionExcel.sheetJornadas

    # Crea un conjunto con los IDs existentes
    ids_existentes = set(row["Id"] for row in sheetPartidosJugados.get_all_records())
 
    matches = APIBbowl.obtener_partido_lombarda(bbowl_API_token)
    agregadas = 0
    if matches:
        for match in matches:
            if match['uuid'] in ids_existentes:
                break
            else:
                #agregamos el partido
                sheetPartidosJugados.append_row([match['uuid'], match['coaches'][0]['coachname'], match['coaches'][1]['coachname'], match['teams'][0]['score'], match['teams'][1]['score']])
                ids_existentes.add(match['uuid'])
                agregadas += 1

                # Actualizar sheetJornadas para cada coach
                for coach in match['coaches']:
                    await actualizar_o_agregar_coach(sheetJornadas, coach)
    else:
        await ctx.reply("Error al obtener los partidos desde la API.")

    await ctx.reply(f"Se han agregado {agregadas} partidos")


#Función para actualizar la jornada de un coach
async def actualizar_o_agregar_coach(sheet, coach):
    valores = sheet.get_all_records()
    fila_actual = 2
    encontrado = False
    for row in valores:
        if row["Id"] == coach['idcoach']:
            # Actualizar jornada
            nueva_jornada = row["jornada"] + 1
            sheet.update_cell(fila_actual, 3, nueva_jornada)
            encontrado = True
            break
        fila_actual += 1  

    if not encontrado:
        # Agregar nuevo coach
        sheet.append_row([coach['coachname'], coach['idcoach'], 1])
    
    await asyncio.sleep(10)



# async def ActualizarClasificacion(ctx):
#     sheetPartidosJugados = GestionExcel.sheetPartidosJugados
#     sheetJornadas = GestionExcel.sheetJornadas

#     # Crea un conjunto con los IDs existentes
#     ids_existentes = set(row["Id"] for row in sheetPartidosJugados.get_all_records())
#     competition_id = 'f24067ad-15df-11ee-8d38-020000a4d571' #Liga Andaluza de Lombard
#     url = f"https://web.cyanide-studio.com/ws/bb3/matches/?key={bbowl_API_token}&competition_id={competition_id}&sort=LastMatchDate"
#     print(f"LLamada al Api de bloodbowl {url}")
#     #Recuperamos los últimos partidos de 
#     response = requests.get(url)
@bot.command()
async def actualiza_clasificacion(ctx):
    sheetPartidosJugados = GestionExcel.sheetPartidosJugados
    sheetJornadas = GestionExcel.sheetJornadas
    sheetCalendarioResultados = GestionExcel.sheetCalendarioResultados
    sheetLesiones = GestionExcel.sheetLesiones

    # Crea un conjunto con los IDs existentes
    ids_existentes = set(row["Id"] for row in sheetPartidosJugados.get_all_records())
 
    matches = APIBbowl.obtener_partido_lombarda(bbowl_API_token)
    if not matches:    
        return
    
    # Comprobaciones en la hoja 'Jornadas'
    jornadas_valores = sheetJornadas.get_all_records()
    for match in matches:
        if match['uuid'] in ids_existentes:
                continue #sería mejor break pero no nos va la vida en esto
        else:
            #agregamos el partido
            sheetPartidosJugados.append_row([match['uuid'], match['coaches'][0]['coachname'], match['coaches'][1]['coachname'], match['teams'][0]['score'], match['teams'][1]['score']])
            ids_existentes.add(match['uuid'])

            coach1_id = match['coaches'][0]['idcoach']
            coach2_id = match['coaches'][1]['idcoach']
            # Actualizar sheetJornadas para cada coach
            for coach in match['coaches']:
                await actualizar_o_agregar_coach(sheetJornadas, coach)
             
                
            await GestionExcel.actualizaExcel('Jornadas')
            jornadas_valores = sheetJornadas.get_all_records()
            jornada_coach1 = next((row["jornada"] for row in jornadas_valores if row["Id"] == coach1_id), None)
            jornada_coach2 = next((row["jornada"] for row in jornadas_valores if row["Id"] == coach2_id), None)

            if jornada_coach1 is None or jornada_coach2 is None or jornada_coach1 != jornada_coach2:
                await UtilesDiscord.menmsaje_administradores(f"No se pudo completar la actualización de clasificación para el partido {match['uuid']}. Los coaches no están en la misma jornada.")
                continue           

            # Actualizaciones en la hoja 'Calendario y Resultados'
            n = 2 + (jornada_coach1 - 1) * 8  # Fila del primer partido de la jornada
            jornada_encontrada = sheetCalendarioResultados.cell(n, 1).value

            if str(jornada_coach1) != jornada_encontrada:
                await UtilesDiscord.menmsaje_administradores(f"Error en la hoja de Calendario y Resultados: La jornada {jornada_coach1} no coincide en la fila {n}.")
                continue

            # Recorrer los 8 partidos de esa jornada para encontrar a los dos coaches
            partido_encontrado = False
            coach_names = [match['coaches'][0]['coachname'], match['coaches'][1]['coachname']]
            for i in range(n, n + 8):
                coach_local = sheetCalendarioResultados.cell(i, 3).value
                coach_visitante = sheetCalendarioResultados.cell(i, 7).value
            
                if coach_local in coach_names and coach_visitante in coach_names:
                    # Determinar las posiciones correctas de los coaches y actualizar resultados
                    local_index = coach_names.index(coach_local)
                    visitante_index = 1 - local_index  # 0 si local_index es 1, y 1 si local_index es 0
                    sheetCalendarioResultados.update_cell(i, 4, match['teams'][local_index]['score'])
                    sheetCalendarioResultados.update_cell(i, 6, match['teams'][visitante_index]['score'])
                    partido_encontrado = True
                    break

            if not partido_encontrado:
                await UtilesDiscord.menmsaje_administradores(f"No se encontró el partido entre {match['coaches'][0]['coachname']} y {match['coaches'][1]['coachname']} en la jornada {jornada_coach1}.")
                continue
                
            total_muertes_coach1 = match['teams'][0]['sustaineddead']
            total_lesiones_coach1 = match['teams'][0]['sustainedcasualties'] 
            total_lesiones_coach1 = total_lesiones_coach1 - total_muertes_coach1
           
            total_muertes_coach2 = match['teams'][1]['sustaineddead']
            total_lesiones_coach2 = match['teams'][1]['sustainedcasualties']
            total_lesiones_coach2 = total_lesiones_coach2 - total_muertes_coach2

            # Actualizar hoja "Lesiones" para cada coach
            # Necesitarás encontrar la fila correspondiente al coach y luego actualizar las celdas para la jornada actual
            # Asumiendo que tienes funciones o métodos para encontrar la fila del coach y para actualizar las celdas
            await GestionExcel.actualizar_hoja_lesiones(match['coaches'][0]['coachname'], jornada_coach1, total_lesiones_coach1, total_muertes_coach1,sheetLesiones)
            await GestionExcel.actualizar_hoja_lesiones(match['coaches'][1]['coachname'], jornada_coach2, total_lesiones_coach2, total_muertes_coach2,sheetLesiones)
            
            embed =UtilesDiscord.crearEmbedPartido( match['coaches'][0],match,0)
            await UtilesDiscord.publicar(ctx,'Jornada ' + str(jornada_coach1) + '!',embed=embed)
            
            for coach in match['coaches']:
                jornadaProxima = jornada_coach1 + 1
                coach_name = coach['coachname']
                coachLocal, coachVisitante, fila_encontrada = await buscar_proximo_rival(sheetCalendarioResultados, coach_name, jornadaProxima)
    
                if coachLocal and coachVisitante:
                    # Aquí necesitaríamos obtener los IDs de Discord de los entrenadores para pasarlos a la función de gestionar canales
                    proximaJornada_coach1 = next((row["jornada"] for row in jornadas_valores if row["coach"] == coach_name), None)
                    proximaJornada_rival = next((row["jornada"] for row in jornadas_valores if row["coach"] in [coachLocal, coachVisitante] and row["coach"] != coach_name), None)
        
                    if proximaJornada_coach1 == proximaJornada_rival:
                        coach1_id_discord = UtilesDiscord.buscar_idDiscord(bbowl_name=coachLocal)
                        coach2_id_discord = UtilesDiscord.buscar_idDiscord(bbowl_name=coachVisitante)
                        nombre_canal = f"J{jornadaProxima}-{coachLocal}vs{coachVisitante}"
                        await UtilesDiscord.gestionar_canal_discord(ctx, "crear", nombre_canal, coach1_id_discord, coach2_id_discord)
                    else:
                        print(f"{coach_name}({proximaJornada_coach1}) y {rival_name}({proximaJornada_rival}) no están en la misma jornada")
                else:
                    print(f"No se encontró un partido para {coach_name} en la jornada {jornadaProxima}, no se creará un canal.")

            # Borrar el canal de la jornada anterior si existe
            nombre_canal_anterior = f"J{jornada_coach1}-{match['coaches'][0]['coachname']}vs{match['coaches'][1]['coachname']}"

            await UtilesDiscord.gestionar_canal_discord(ctx,"eliminar", nombre_canal_anterior, '', '')

    await ctx.reply("Actualización de clasificación completada.")

async def buscar_proximo_rival(sheetCalendarioResultados, coach_name, jornada_actual):
    # Calcular la fila inicial para la jornada siguiente
    n = 2 + (jornada_actual-1) * 8  

    # Leer el valor de la jornada en la fila inicial para asegurarse de que estamos en la jornada correcta
    jornada_encontrada = sheetCalendarioResultados.cell(n, 1).value

    if str(jornada_actual) != jornada_encontrada:
        print(f"Error o no hay partidos programados para la jornada {jornada_actual} en la fila {n}.")
        return None, None, None  # No se encontró partido

    # Recorrer los partidos de esa jornada para encontrar al coach
    for i in range(n, n + 8):
        coach_local = sheetCalendarioResultados.cell(i, 2).value
        coach_visitante = sheetCalendarioResultados.cell(i, 6).value

        # Comprobar si el coach es el local o el visitante en alguno de los partidos
        if coach_name == coach_local or coach_name == coach_visitante:
            # Devolver los nombres de ambos coaches y la fila donde se encontró el partido
            return coach_local, coach_visitante, i

    # Si se recorren todos los partidos y no se encuentra al coach, significa que no tiene partido en esa jornada
    return None, None, None

@bot.command()
async def CreaCanalesJornada(ctx, jornada, *, mensaje):
    sheetCalendarioResultados = GestionExcel.sheetCalendarioResultados
    n = 2 + (int(jornada) - 1) * 8  # Fila del primer partido de la jornada
    jornada_encontrada = sheetCalendarioResultados.cell(n, 1).value

    if str(jornada) != jornada_encontrada:
        await UtilesDiscord.menmsaje_administradores(f"Error en la hoja de Calendario y Resultados: La jornada {jornada} no coincide en la fila {n}.")
        return
    
    for x in range(n, n+8):
        coachLocal = sheetCalendarioResultados.cell(x, 3).value
        coachVisitante = sheetCalendarioResultados.cell(x, 7).value
        if coachLocal and coachVisitante:
            coach1_id_discord = UtilesDiscord.buscar_idDiscord(bbowl_name=coachLocal)
            coach2_id_discord = UtilesDiscord.buscar_idDiscord(bbowl_name=coachVisitante)
            nombre_canal = f"J{jornada}-{coachLocal}vs{coachVisitante}"
            await UtilesDiscord.gestionar_canal_discord(ctx, "crear", nombre_canal, coach1_id_discord, coach2_id_discord,mensaje=mensaje)



@bot.command(name='EditaMensaje')
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
   
@bot.command(name='actconfig')
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
  
@bot.command(name='dado')
async def roll_dice(ctx, *args):
    try:
        # Sin argumentos, devuelve un resultado entre 1 y 6
        if len(args) == 0:
            result = random.randint(1, 6)
            await ctx.send(f"🎲 Has sacado un {result}!")
        # Con un argumento, devuelve un resultado entre 1 y arg
        elif len(args) == 1:
            max_number = int(args[0])
            if max_number < 1:
                await ctx.send("El número debe ser mayor que 0.")
            else:
                result = random.randint(1, max_number)
                await ctx.send(f"🎲 Has sacado un {result}!")
        # Con dos argumentos, devuelve arg1 resultados de entre 1 y arg2
        elif len(args) == 2:
            rolls = int(args[0])
            if rolls > 25:
                await ctx.send("No tires más de 25 dados flipado.")
                return
            max_number = int(args[1])
            if rolls < 1 or max_number < 1:
                await ctx.send("Los números deben ser mayores que 0.")
            else:
                results = [random.randint(1, max_number) for _ in range(rolls)]
                results_str = ', '.join(str(r) for r in results)
                sum_of_results = sum(results)
                dice_icons = '🎲' * rolls
                await ctx.send(f"{dice_icons} Has sacado: {results_str}. Total: {sum_of_results}")
        # Con más de dos argumentos, devuelve un mensaje de error
        else:
            await ctx.send("Por favor, introduce un máximo de dos argumentos.")
    except ValueError:
        await ctx.send("Por favor, introduce números válidos.")        

# Ejecutar el bot con el token correspondiente
bot.run(discord_bot_token)

