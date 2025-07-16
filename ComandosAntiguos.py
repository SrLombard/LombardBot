# #Función para agregar las ids de los jugadores a googleSheets
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
@commands.has_any_role('Moderadores', 'Administrador', 'Comisario')
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

#Comando para agregar partidos al excel para ponernos al día
@bot.command()
@commands.has_any_role('Moderadores', 'Administrador', 'Comisario')
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

@bot.command(name="EnviarInvitacion")
@commands.has_any_role('Moderadores', 'Administrador', 'Comisario')
async def enviarInvitacion(ctx):
    guild = ctx.guild
    role_name = "Butter Cup"
    role = discord.utils.get(guild.roles, name=role_name)

    mensaje = """¡Bienvenido a la Butter Cup!

Hemos abierto las inscripciones. Si ya estabas en el servidor de SrLombard te hemos asignado automáticamente el rol de Butter Cup. Si no aquí tienes una invitación https://discord.gg/CmzY8ZSvp3

Si solo estás interesado en la Butter Cup puedes quitarte el resto de roles porque publicaremos todo lo relacionado en esos canales

Recuerda que empezamos el 26 de marzo así que no lo dejes pasar

Si no quieres que te escriba más reacciona con ❌ a este mensaje"""

    sheetIds = GestionExcel.sheetIds
    records = sheetIds.get_all_records()  

    rows_to_update = []
    for index, record in enumerate(records, start=2):  # Empieza en 2 para ajustar el índice a las filas de Sheets
        user_id = record.get("id_discord")
        if user_id:
            user_id = int(user_id)
            try:
                user = await bot.fetch_user(user_id)  # Usa bot.fetch_user aquí
                if user:
                    await user.send(mensaje)
                    # Envía el mensaje en el canal de texto
                    await ctx.send(f"Enviada invitación a {user.name}#{user.discriminator}")
                    member = guild.get_member(user_id)
                    if member and role:
                        await member.add_roles(role)
                # Espera 1 minuto antes de enviar el siguiente mensaje
                await asyncio.sleep(60)
            except Exception as e:
                print(f"Error al enviar invitación a {user_id}: {e}")
                await ctx.send(f"Error al enviar invitación a {user_id}: {e}")
                





@bot.command()
@commands.has_any_role('Moderadores', 'Administrador', 'Comisario')
async def actualiza_clasificacion(ctx,todos=0):
    sheetPartidosJugados = GestionExcel.sheetPartidosJugados
    sheetJornadas = GestionExcel.sheetJornadas
    sheetCalendarioResultados = GestionExcel.sheetCalendarioResultados
    sheetLesiones = GestionExcel.sheetLesiones

    # Crea un conjunto con los IDs existentes
    ids_existentes = set(row["Id"] for row in sheetPartidosJugados.get_all_records())
 
    matches = APIBbowl.obtener_partido_ButterCup(bbowl_API_token)
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
                await UtilesDiscord.mensaje_administradores(f"No se pudo completar la actualización de clasificación para el partido {match['uuid']}. Los coaches no están en la misma jornada.")
                continue           

            # Actualizaciones en la hoja 'Calendario y Resultados'
            n = 2 + (jornada_coach1 - 1) * 8  # Fila del primer partido de la jornada
            jornada_encontrada = sheetCalendarioResultados.cell(n, 1).value

            if str(jornada_coach1) != jornada_encontrada:
                await UtilesDiscord.mensaje_administradores(f"Error en la hoja de Calendario y Resultados: La jornada {jornada_coach1} no coincide en la fila {n}.")
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
                await UtilesDiscord.mensaje_administradores(f"No se encontró el partido entre {match['coaches'][0]['coachname']} y {match['coaches'][1]['coachname']} en la jornada {jornada_coach1}.")
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


#BACKUP FUNCIONAL DEL SPIN
class SpinButtonsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Spin",style=discord.ButtonStyle.green, custom_id='your_bot:spin')
    async def Spin_callback(self, interaction: discord.Interaction,button: discord.ui.Button):
        global UsuarioSpin
                       
        user = interaction.user
        channel = interaction.channel
        message = interaction.message

        # Comprueba si UsuarioSpin ya está ocupado
        if UsuarioSpin is not None:
            # Informa al usuario que el spin ha fracasado
            await interaction.response.send_message(f'{user.mention}, ya hay un usuario buscando partido.', ephemeral=True)
            return
        else:
            # Actualiza UsuarioSpin con el usuario actual
            UsuarioSpin = user
            await interaction.response.defer() 
            encontrado_button = None
            for child in self.children:        
                if type(child) == discord.ui.Button and child.label == "Encontrado":
                    encontrado_button = child
                    child.disabled = False
                    break

            button.disabled = True 
            await interaction.message.edit(content=message.content, view=self)
            
            # Edita el mensaje con el estado actual (se asume que tienes el ID del mensaje a editar)
            mensaje_id = idMensajeSpin
            mensaje = await channel.fetch_message(mensaje_id)
            await mensaje.edit(content=f'**{UsuarioSpin} puede buscar partido**')
            
            thread = Thread(target=GestorSQL.insertar_spin, args=(UsuarioSpin, now, 'Spin'))
            thread.start()

    @discord.ui.button(label="Encontrado",style=discord.ButtonStyle.blurple, custom_id='your_bot:encontrado')
    async def Encontrado_callback(self, interaction: discord.Interaction,button: discord.ui.Button):
        global UsuarioSpin
        
        await interaction.response.defer()            

        user = interaction.user
        channel = interaction.channel
        message = interaction.message
        
        # Comprueba si el usuario es UsuarioSpin
        if interaction.user == UsuarioSpin:
            # Limpia UsuarioSpin
            UsuarioSpin = None
            # Actualiza los botones
            spin_button = None
            for child in self.children:        
                if type(child) == discord.ui.Button and child.label == "Spin":
                    spin_button = child
                    child.disabled = False
                    break
                
            button.disabled = True 
            await interaction.message.edit(content=message.content, view=self)
            # Edita el mensaje para reflejar el cambio de estado
            mensaje_id = idMensajeSpin
            mensaje = await channel.fetch_message(mensaje_id)
            await mensaje.edit(content='El spin está **LIBRE**')
        # Si no es UsuarioSpin, ignora la pulsación



    # subquery = session.query(
    #     GestorSQL.Calendario.coach1.label("coach"),
    #     GestorSQL.Partidos.resultado1.label("td_favor"),
    #     GestorSQL.Partidos.resultado2.label("td_contra"),
    #     case(
    #         (GestorSQL.Partidos.resultado1 > GestorSQL.Partidos.resultado2, 3),
    #         (GestorSQL.Partidos.resultado1 == GestorSQL.Partidos.resultado2, 1),
    #         else_=0
    #     ).label("puntos")
    # ).join(GestorSQL.Partidos, GestorSQL.Calendario.partidos_idPartidos == GestorSQL.Partidos.idPartidos
    # ).join(GestorSQL.Usuario, GestorSQL.Usuario.idUsuarios == GestorSQL.Calendario.coach1
    # ).filter(GestorSQL.Calendario.jornada <= jornada,
    #          GestorSQL.Calendario.partidos_idPartidos.isnot(None),
    #          GestorSQL.Usuario.grupo == grupo
    # ).union(
    #     session.query(
    #         GestorSQL.Calendario.coach2.label("coach"),
    #         GestorSQL.Partidos.resultado2.label("td_favor"),
    #         GestorSQL.Partidos.resultado1.label("td_contra"),
    #         case(
    #             (GestorSQL.Partidos.resultado2 > GestorSQL.Partidos.resultado1, 3),
    #             (GestorSQL.Partidos.resultado2 == GestorSQL.Partidos.resultado1, 1),
    #             else_=0
    #         ).label("puntos")
    #     ).join(GestorSQL.Partidos, GestorSQL.Calendario.partidos_idPartidos == GestorSQL.Partidos.idPartidos
    #     ).join(GestorSQL.Usuario, GestorSQL.Usuario.idUsuarios == GestorSQL.Calendario.coach2
    #     ).filter(GestorSQL.Calendario.jornada <= jornada, 
    #              GestorSQL.Calendario.partidos_idPartidos.isnot(None),
    #              GestorSQL.Usuario.grupo == grupo)
    # ).subquery()    
    # # Consulta para sumar los puntos y ordenar
    # resultados = session.query(
    #     GestorSQL.Usuario.nombre_bloodbowl,
    #     func.sum(subquery.c.td_favor).label("td"),
    #     func.sum(subquery.c.td_contra).label("tdc"),
    #     (func.sum(subquery.c.td_favor) - func.sum(subquery.c.td_contra)).label("DDT"),
    #     func.sum(subquery.c.puntos).label("Puntos")
    # ).join(GestorSQL.Usuario, GestorSQL.Usuario.idUsuarios == subquery.c.coach
    # ).group_by(GestorSQL.Usuario.nombre_bloodbowl
    # ).order_by(func.sum(subquery.c.puntos).desc(), func.sum(subquery.c.td_favor).desc()
    # ).all()


class InteractionButtonsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Confirmar partido",style=discord.ButtonStyle.green, custom_id='your_bot:confirm')
    async def Confirm_callback(self, interaction: discord.Interaction,button: discord.ui.Button):
        try:
            user = interaction.user
            channel = interaction.channel
            message = interaction.message

            await channel.edit(name="🟢" + channel.name)
            await channel.send(f"{user.mention} confirmó la fecha del partido el día")

            cancel_button = None
            for child in self.children:
                if type(child) == discord.ui.Button and child.label == "Cancelar":
                    cancel_button = child
                    child.disabled = False
                    break
                
            button.disabled = True
            await interaction.message.edit(content=message.content, view=self)
            
        except Exception as e:
            print(f"Error al manejar la interacción del botón: {e}")
            await channel.send("Se produjo un error al procesar la interacción del botón. Por favor, inténtalo de nuevo más tarde.")

    @discord.ui.button(label="Cancelar",style=discord.ButtonStyle.red,disabled=True, custom_id='your_bot:cancel')
    async def Cancel_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:    
            await interaction.response.defer()            

            user = interaction.user
            channel = interaction.channel
            message = interaction.message

            nuevoNombre = channel.name[1:]
            nuevoNombre = "🔴" + nuevoNombre

            await channel.edit(name=nuevoNombre)
            await channel.send(f"{user.mention} canceló la fecha del partido")

            cconfirm_button = None
            for child in self.children:
                if type(child) == discord.ui.Button and child.label == "Confirmar partido":
                    cconfirm_button = child
                    child.disabled = False
                    break
                
            button.disabled = True

            await interaction.message.edit(content=message.content, view=self)

        except Exception as e:
            print(f"Error al manejar la interacción del botón: {e}")
            await channel.send("Se produjo un error al procesar la interacción del botón. Por favor, inténtalo de nuevo más tarde.")



