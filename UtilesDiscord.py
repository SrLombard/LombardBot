import discord
from discord.ext import commands
import GestionExcel

def crearEmbedPartido(coach,match,propietario):
    invertir_valor = lambda x: 0 if x != 0 else 1
    resultadoLocal = match['teams'][propietario]['score']
    resultadoVisitante = match['teams'][invertir_valor(propietario)]['score']        
    
    coachVisitante= mencionar_idDiscord(match['coaches'][invertir_valor(propietario)]['idcoach'],match['coaches'][invertir_valor(propietario)]['coachname'])

    mensaje = ''
    if resultadoLocal > resultadoVisitante:
        mensaje = f"Felicidades por tú victoria {resultadoLocal} - {resultadoVisitante} contra @{coachVisitante}"
    elif resultadoVisitante > resultadoLocal:
        mensaje = f"Luchaste bien ese {resultadoLocal} - {resultadoVisitante} pero esta vez no se pudo ganar contra @{coachVisitante}"
    else:
        mensaje = f"Disputadísimo empate {resultadoLocal} - {resultadoVisitante} contra @{coachVisitante}"
                    

    embed = discord.Embed(
        title=coach['coachname'] + " vs " + match['coaches'][invertir_valor(propietario)]['coachname'],
        description=mensaje + "\n En este partido se enfrentaron",
        color=discord.Color.blue()
    )
    embed.add_field(name=match['teams'][propietario]['teamname'], value=str(resultadoLocal), inline=True)
    embed.add_field(name=match['teams'][invertir_valor(propietario)]['teamname'], value=str(resultadoVisitante), inline=True)
    embed.add_field(name='',value='')

    embed.add_field(name='\U0001F691', value=(match['teams'][propietario]['sustainedcasualties']-match['teams'][propietario]['sustaineddead']), inline=True)
    embed.add_field(name='\U0001F691', value=(match['teams'][invertir_valor(propietario)]['sustainedcasualties']-match['teams'][invertir_valor(propietario)]['sustaineddead']), inline=True)
    embed.add_field(name='',value='')

    embed.add_field(name='\U0001F480', value=match['teams'][propietario]['sustaineddead'], inline=True)
    embed.add_field(name='\U0001F480', value=match['teams'][invertir_valor(propietario)]['sustaineddead'], inline=True)
    embed.add_field(name='',value='')

    return embed

#Función para mencionar en discord a un entrenador de bbowl
def mencionar_idDiscord(bbowl_id=None, bbowl_name=None):
    discord_id = buscar_idDiscord(bbowl_id=bbowl_id, bbowl_name=bbowl_name)
    if discord_id:
        return f'<@{discord_id}>'
    else:
        return bbowl_name


def buscar_idDiscord(bbowl_id=None, bbowl_name=None):
    sheetIds = GestionExcel.sheetIds    
    try:
        valores = sheetIds.get_all_records()
        if bbowl_id is not None:
            for row in valores:
                if str(row["id_bbowl"]) == str(bbowl_id):
                    return row["id_discord"]
        elif bbowl_name is not None:
            for row in valores:
                if row["nombre_bbowl"] == bbowl_name:
                    return row["id_discord"]
    except Exception as e:
        print(f"Error al acceder a Google Sheets: {e}")
    return None


async def publicar(ctx, titulo, mensaje=None, embed=None):
    canal_foro = discord.utils.get(ctx.guild.channels, id=1158436598728368249)
    
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
        await ctx.send("Mensaje publicado en el hilo existente.")
    else:
        if mensaje:
            nuevo_hilo = await canal_foro.create_thread(name=titulo, content='Resultados de ' + titulo)
        elif embed:
            nuevo_hilo  = await canal_foro.create_thread(name=titulo, content=embed.description)
            await nuevo_hilo.thread.send(embed=embed)
        await ctx.send("Hilo nuevo creado y mensaje publicado.")       


async def menmsaje_administradores(mensaje):
    bot = DiscordClientSingleton.get_bot_instance()
    channel = bot.get_channel(457740100097540106)  # Asegúrate de que la ID del canal sea correcta
    await channel.send(mensaje)


async def gestionar_canal_discord(ctx, accion, nombre_canal, coach1_id_discord, coach2_id_discord, categoria_id=1090321674609623142,mensaje=""):
    guild = ctx.guild
    categoria = discord.utils.get(guild.categories, id=int(categoria_id))

    if mensaje == "":
        mensaje = "Bienvenidos, {mention1} y {mention2}! Por favor, acuerden una fecha para jugar el siguiente partido."

    if categoria:
        # Transformar el nombre del canal a minúsculas y reemplazar espacios por guiones
        nombre_canal_formato_discord = nombre_canal.lower().replace(" ", "-")
        
        if accion == "crear":
            admin_id = 681577610010296372
            admin_member = guild.get_member(admin_id)
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                admin_member: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
            try:
                canal = await guild.create_text_channel(name=nombre_canal_formato_discord, overwrites=overwrites, category=categoria)
                print(f"Canal {nombre_canal_formato_discord} creado exitosamente en la categoría {categoria.name}.")
                # Ajusta los permisos específicos para los entrenadores después de la creación del canal
                coach1 = guild.get_member(coach1_id_discord)
                coach2 = guild.get_member(coach2_id_discord)
                if coach1:
                    await canal.set_permissions(coach1, read_messages=True, send_messages=True)
                if coach2:
                    await canal.set_permissions(coach2, read_messages=True, send_messages=True)
                
                # Enviar mensaje de bienvenida en el canal
                if coach1 and coach2:
                    mensaje_formateado = mensaje.format(coach1=coach1, coach2=coach2,mention1 = coach1.mention,mention2=coach2.mention)
                    await canal.send(mensaje_formateado)
                
            except Exception as e:
                print(f"No se pudo crear el canal {nombre_canal_formato_discord}: {e}")

        elif accion == "eliminar":
            canal = discord.utils.get(categoria.text_channels, name=nombre_canal_formato_discord)
            if canal:
                try:
                    await canal.delete()
                    print(f"Canal {nombre_canal_formato_discord} eliminado exitosamente de la categoría {categoria.name}.")
                except Exception as e:
                    print(f"No se pudo eliminar el canal {nombre_canal_formato_discord}: {e}")
            else:
                print(f"No se encontró el canal {nombre_canal_formato_discord} en la categoría {categoria.name}.")
    else:
        print("Categoría no encontrada en el servidor.")   

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
