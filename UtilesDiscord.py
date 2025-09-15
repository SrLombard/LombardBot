import discord
from discord.ext import commands
from discord import app_commands
from threading import Thread
import threading
import Imagenes

from sqlalchemy.sql.functions import now
from sqlalchemy import BIGINT, create_engine, Column, Integer, String, ForeignKey, false, true,text
from sqlalchemy import and_, or_ ,null
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.orm import aliased
from sqlalchemy.sql import case,func

import GestorSQL

import asyncio
from datetime import datetime




UsuarioSpin = None
idMensajeSpin = 1224072683097030698

def get_int_value(dictionary, key):
    value = dictionary.get(key)
    return 0 if value is None else value


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
    await channel.send(mensaje)


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
            
Tenéis que crear vuestros equipos, cuando lo hagáis **mencionad** por este canal a @comisario especificando el **nombre del equipo** al que queréis recibir la invitacón.

Por favor, acuerden una fecha para jugar el primer partido.""" + mensajePreferencias1 + mensajePreferencias2 + """

Cuando acordéis una fecha **usad** el comando `/fecha` para que el bot pueda registrar vuestro partido con el horario de España. Esto es **OBLIGATORIO** y para la administración será clave a la hora de tomar decisiones en caso de que alguien no se presente. {fecha}

Justo antes de jugar el partido tendréis que **USAR EL CANAL**  <#1224128423929315468> y **LIBERADLO** al encontrar partido. De esta manera no os emparejará con otra persona.

Otro comando del bot que os puede ser útil es `/preferenciashorario`. Ahí podréis poner qué horarios os vienen bien generalmente, me encargaré de decírselo a vuestros próximos rivales para que las quedadas sean más ágiles.

Si hubiera cualquier problema mencionad a los comisarios que están para ayudar.
"""
        else:
            mensaje = """Bienvenidos, {mention1}({raza1}) y {mention2}({raza2})! 
            
Tenéis que crear vuestros equipos, cuando lo hagáis **mencionad** por este canal a @comisario especificando el **nombre del equipo** al que queréis recibir la invitacón.

Por favor, acuerden una fecha para jugar el primer partido.""" + mensajePreferencias1 + mensajePreferencias2 + """

Cuando acordéis una fecha **usad** el comando `/fecha` para que el bot pueda registrar vuestro partido con el horario de España. Esto es **OBLIGATORIO** y para la administración será clave a la hora de tomar decisiones en caso de que alguien no se presente. {fecha}

Justo antes de jugar el partido tendréis que **USAR EL CANAL**  <#1224128423929315468> y **LIBERADLO** al encontrar partido. De esta manera no os emparejará con otra persona.

Otro comando del bot que os puede ser útil es `/preferenciashorario`. Ahí podréis poner qué horarios os vienen bien generalmente, me encargaré de decírselo a vuestros próximos rivales para que las quedadas sean más ágiles.

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
                

class SpinButtonsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.spin_timeout_task = None
        self.mensaje_spin_id = None  # Almacena el ID del mensaje de spin
        self.canal = None  # Almacena el canal del mensaje de spin
        self.canal_partido = None # Almacena el canal del partido

    async def auto_release_spin(self, user):
        await asyncio.sleep(300)  # Espera 5 minutos
        global UsuarioSpin
        if UsuarioSpin == user:
            UsuarioSpin = None  # Libera el spin
            if self.canal_partido:
                await self.canal_partido.send("El spin ha sido liberado automáticamente.😡 Afortunadamente las máquinas somos superiores y cuidamos de los esmirriados humanos")
                self.canal_partido = None 
            
            # Envía un mensaje privado al usuario informándole que el spin ha sido liberado automáticamente
            await user.send('Tu spin ha sido liberado automáticamente debido a la inactividad.')

            # Recupera el mensaje de spin y actualiza la vista
            if self.canal and self.mensaje_spin_id:
                mensaje_spin = await self.canal.fetch_message(self.mensaje_spin_id)
                # Encuentra y actualiza los botones
                for item in self.children:
                    if isinstance(item, discord.ui.Button):
                        if item.label == "Spin":
                            item.disabled = False
                        elif item.label == "Encontrado":
                            item.disabled = True
                await mensaje_spin.edit(view=self)  # Actualiza la vista con los botones actualizados
                
            primer_mensaje = await self.obtener_primer_mensaje(mensaje_spin.channel)
            await primer_mensaje.edit(content='El spin está **LIBRE**')
            
            thread = Thread(target=GestorSQL.insertar_spin, args=('LOMBARDBOT', datetime.now(), 'Encontrado'))
            thread.start()


    async def obtener_primer_mensaje(self, channel):
        async for mensaje in channel.history(oldest_first=True, limit=1):
            return mensaje  #primer mensaje encontrado
        return None  #None si no hay mensajes

    @discord.ui.button(label="Spin", style=discord.ButtonStyle.green, custom_id='your_bot:spin')
    async def spin_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        global UsuarioSpin
        await interaction.response.defer()
        self.canal = interaction.channel
        self.mensaje_spin_id = interaction.message.id
               
        user = interaction.user

        if UsuarioSpin is not None:
            # Usa followup.send para enviar un mensaje efímero después de deferir
            await interaction.followup.send(f'{user.mention}, ya hay un usuario buscando partido.', ephemeral=True)
            return
        else:
            UsuarioSpin = user
            
            
        # Inicia el temporizador para la liberación automática del spin
        if self.spin_timeout_task:
            self.spin_timeout_task.cancel()  # Cancela el temporizador anterior si existe
        self.spin_timeout_task = asyncio.create_task(self.auto_release_spin(user))

        # Buscar usuario en la base de datos
        Session = GestorSQL.sessionmaker(bind=GestorSQL.conexionEngine())
        session = Session()
        usuario_db = session.query(GestorSQL.Usuario).filter(GestorSQL.Usuario.id_discord == user.id).first()
        if not usuario_db:
            UsuarioSpin = None
            await interaction.followup.send("No se encontró tu usuario en la base de datos.", ephemeral=True)
            return

        # Buscar partidos asociados en las tablas Calendario y PlayOffs
        partidos_calendario = session.query(GestorSQL.Calendario).filter(
            or_(
                GestorSQL.Calendario.coach1 == usuario_db.idUsuarios,
                GestorSQL.Calendario.coach2 == usuario_db.idUsuarios
            ),
            GestorSQL.Calendario.canalAsociado != None,
            GestorSQL.Calendario.partidos_idPartidos == None
        ).order_by(GestorSQL.Calendario.fecha).first()
        
        partidos_playoffs_oro = session.query(GestorSQL.PlayOffsOro).filter(
            or_(
                GestorSQL.PlayOffsOro.coach1 == usuario_db.idUsuarios,
                GestorSQL.PlayOffsOro.coach2 == usuario_db.idUsuarios
            ),
            GestorSQL.PlayOffsOro.canalAsociado != None,
            GestorSQL.PlayOffsOro.partidos_idPartidos == None
        ).order_by(GestorSQL.PlayOffsOro.fecha).first()
        
        partidos_playoffs_plata = session.query(GestorSQL.PlayOffsPlata).filter(
            or_(
                GestorSQL.PlayOffsPlata.coach1 == usuario_db.idUsuarios,
                GestorSQL.PlayOffsPlata.coach2 == usuario_db.idUsuarios
            ),
            GestorSQL.PlayOffsPlata.canalAsociado != None,
            GestorSQL.PlayOffsPlata.partidos_idPartidos == None
        ).order_by(GestorSQL.PlayOffsPlata.fecha).first()
        
        partidos_playoffs_bronce = session.query(GestorSQL.PlayOffsBronce).filter(
            or_(
                GestorSQL.PlayOffsBronce.coach1 == usuario_db.idUsuarios,
                GestorSQL.PlayOffsBronce.coach2 == usuario_db.idUsuarios
            ),
            GestorSQL.PlayOffsBronce.canalAsociado != None,
            GestorSQL.PlayOffsBronce.partidos_idPartidos == None
        ).order_by(GestorSQL.PlayOffsBronce.fecha).first()

        partidos_ticket = session.query(GestorSQL.Ticket).filter(
            or_(
                GestorSQL.Ticket.coach1 == usuario_db.idUsuarios,
                GestorSQL.Ticket.coach2 == usuario_db.idUsuarios
            ),
            GestorSQL.Ticket.canalAsociado != None,
            GestorSQL.Ticket.partidos_idPartidos == None
        ).order_by(GestorSQL.Ticket.fecha).first()
        partidos = [partidos_calendario, partidos_playoffs_oro, partidos_playoffs_plata, partidos_playoffs_bronce, partidos_ticket]
        partidos = [p for p in partidos if p is not None]

        if not partidos:
            UsuarioSpin = None
            await interaction.followup.send("No tienes ningún partido. No puedes spinear.", ephemeral=True)
            return

        now_time = datetime.now()

        def proximidad(p):
            if getattr(p, 'fecha', None):
                return abs((p.fecha - now_time).total_seconds())
            return float('inf')

        partido = min(partidos, key=proximidad)
        
        self.canal_partido = interaction.guild.get_channel(partido.canalAsociado)
        if self.canal_partido:
            await self.canal_partido.send(f'<@{partido.usuario_coach1.id_discord}> y <@{partido.usuario_coach2.id_discord}> podéis spinear')

        encontrado_button = None
        for child in self.children:
            if isinstance(child, discord.ui.Button) and child.label == "Encontrado":
                encontrado_button = child
                child.disabled = False
                break

        button.disabled = True
        await interaction.message.edit(view=self)

        primer_mensaje = await self.obtener_primer_mensaje(interaction.channel)
        await primer_mensaje.edit(content=f'<@{partido.usuario_coach1.id_discord}> y <@{partido.usuario_coach2.id_discord}> pueden buscar partido')

        await interaction.followup.send("Ahora puedes buscar partido.", ephemeral=True)

        thread = Thread(target=GestorSQL.insertar_spin, args=(user.name, datetime.now(), 'Spin'))
        thread.start()
            
    @discord.ui.button(label="Encontrado", style=discord.ButtonStyle.blurple, custom_id='your_bot:encontrado')
    async def encontrado_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        global UsuarioSpin

        await interaction.response.defer()
        user = interaction.user
        channel = interaction.channel

        if user == UsuarioSpin:
            UsuarioSpin = None
            if self.canal_partido:
                await self.canal_partido.send("El spin ha sido liberado.")
                self.canal_partido = None 
            if self.spin_timeout_task:
                self.spin_timeout_task.cancel()  # Asegura cancelar el temporizador

            spin_button = None
            for child in self.children:
                if isinstance(child, discord.ui.Button) and child.label == "Spin":
                    spin_button = child
                    child.disabled = False
                    break

            button.disabled = True
            await interaction.message.edit(view=self)

            primer_mensaje = await self.obtener_primer_mensaje(channel)
            await primer_mensaje.edit(content='El spin está **LIBRE**')
            thread = Thread(target=GestorSQL.insertar_spin, args=(user.name, datetime.now(), 'Encontrado'))
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


    
