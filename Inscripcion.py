import discord
from discord.ui import Modal, TextInput
from discord import TextStyle
from sqlalchemy import and_, or_ ,null
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.orm import aliased
from sqlalchemy.sql import case,func
import GestorSQL
import UtilesDiscord
import asyncio

racesConEmojiIniciales = [
    "👴🏻Alianza del viejo mundo👴🏻","🏹Amazonas🏹", "🐐Caos Elegido🐐", "⛏Enanos⛏", "🔮Elfos oscuros🔮",
    "🌲Elfos silvanos🌲", "🦎Hombres lagarto🦎", "🐺Horror nigromántico🐺", "🙎🏻‍Humanos🙎🏻‍",
    "🤢Inframundo🤢","🩸Khrone🩸", "💀No muertos💀", "👲🏻Nobleza Imperial👲🏻","❄Nordicos❄", "🤮Nurgle🤮",
    "🐸Orcos🐸", "👹Orcos negros👹", "👨‍👧‍👦Renegados👨‍👨‍👧", "🐀Skaven🐀", "🤾🏻‍Unión elfica🤾","🧚🏻‍♂️Stunty🌜","🎲Nueva raza🎲"
]
racesIniciales = [
    "Alianza del viejo mundo","Amazonas,", "Caos Elegido", "Enanos", "Elfos oscuros",
    "Elfos silvanos", "Hombres lagarto", "Horror nigromántico", "Humanos",
    "Inframundo","Khorne", "No muertos", "Nobleza Imperial", "Nordicos","Nurgle",
    "Orcos", "Orcos negros", "Renegados", "Skaven", "Unión elfica","Stunty","Nueva raza"
]

NUM_PREFERENCIAS = 5
NUM_BANS = 5

# tipoPreferenciaOptions = [
#     ("Nuevo", "Nuevo"),
#     ("Nuevo/Reformado", "Prefiero nuevo pero tengo existente"),
#     ("Reformado/Nuevo", "Prefiero existente pero puedo nuevo"),
#     ("Reformado", "Existente")
# ]

async def handle_registration(user):
    Session = sessionmaker(bind=GestorSQL.conexionEngine())
    session = Session()
    usuario = session.query(GestorSQL.Usuario).filter_by(id_discord=user.id).first()
    if usuario:
        inscripcion = session.query(GestorSQL.Inscripcion).filter_by(id_usuario_discord=user.id).first()
        if not inscripcion:
            nueva_inscripcion = GestorSQL.Inscripcion(id_usuario_discord=user.id, nombre_bloodbowl=usuario.nombre_bloodbowl)
            session.add(nueva_inscripcion)
            session.commit()
            await user.send(f"Gracias por inscribirte en la Quinta edición de la Butter Cup, {usuario.nombre_bloodbowl}!")
            # Temporada 25/26: todos los equipos deben ser nuevos
            await registroEquipoNuevo(user)
        else:
            await user.send(f"Ya tiene un registro comenzado {usuario.nombre_bloodbowl}, si continua sus datos se sobreescribirán")
            # Temporada 25/26: se omite la elección de tipo de equipo
            await registroEquipoNuevo(user)
    else:
        view = WelcomeView(user.id)
        await user.send("""Bienvenido a la quinta edición de la BUTTER CUP.
                        
Estamos emocionados por contar contigo. Vamos a empezar tu inscripción.

                                                
Primero necesitamos saber tu nombre EXACTO en blood bowl, pulsa EMPEZAR y escribelo (¡importan las mayúsculas!)""", view=view)
    session.close()
    
# async def seleccionar_tipo_preferencia(user):
#     view = TipoPreferenciaView(user.id)
#     await user.send("Elija su preferencia de equipo:", view=view)


# class TipoPreferenciaView(discord.ui.View):
#     def __init__(self, usuario_id):
#         super().__init__(timeout=None)
#         self.usuario_id = usuario_id
#         for label, desc in tipoPreferenciaOptions:
#             button = discord.ui.Button(label=desc, style=discord.ButtonStyle.primary, custom_id=label)
#             button.callback = self.select_preference
#             self.add_item(button)
#
#     async def select_preference(self, interaction: discord.Interaction):
#         preference = interaction.data['custom_id']
#         await interaction.response.defer()
#
#         Session = sessionmaker(bind=GestorSQL.conexionEngine())
#         session = Session()
#         try:
#             inscripcion = session.query(GestorSQL.Inscripcion).filter_by(id_usuario_discord=self.usuario_id).first()
#             if not inscripcion:
#                 inscripcion = GestorSQL.Inscripcion(id_usuario_discord=self.usuario_id)
#                 session.add(inscripcion)
#             inscripcion.tipoPreferencia = preference
#             session.commit()
#
#             if preference == 'Nuevo':
#                 await registroEquipoNuevo(interaction.user)
#             elif preference == 'Reformado':
#                 await registroEquipoExistente(interaction.user)
#             else:
#                 await registroEquipoExistente(interaction.user, next_step='preferencias')
#         except Exception as e:
#             session.rollback()
#             await interaction.followup.send("Error al registrar la preferencia.", ephemeral=True)
#         finally:
#             session.close()

async def registroEquipoNuevo(user):
    await user.send("""Para crear un nuevo equipo en la Butter Cup primero te tenemos que adjudicar una raza por __**sorteo**__.
                    
 El sorteo se realizará en directo aproximadamente el <t:1757790000:F> en canal de twitch de SrLombard.
                    
Para que te podamos asignar una raza deberás elegir __5 favoritas__ y __banear otras 5__.
Intentaremos asignarte una de tus razas favoritas, pero hay un número limitado de plazas por raza. Si no se pudiera se te asignaría cualquier otra raza pero nunca una de las baneadas asi que... ¡elige sabiamente!""")
    await registroPreferencias(user)
    
# async def registroEquipoExistente(user, next_step=None):
#     Session = sessionmaker(bind=GestorSQL.conexionEngine())
#     session = Session()
#     usuario = session.query(GestorSQL.Usuario).filter_by(id_discord=user.id).first()
#     if usuario:
#         equipos = session.query(GestorSQL.equiposReformados).filter_by(id_usuario=usuario.idUsuarios).all()
#         if equipos:
#             view = EquiposView(user.id, equipos, next_step)
#             await user.send("Selecciona uno de tus equipos existentes:", view=view)
#         else:
#             await user.send("No tiene equipos creados, continuaremos con un equipo nuevo.")
#             await registroEquipoNuevo(user)
#     session.close()

async def registroPreferencias(user):
    view = RazasView(racesIniciales, racesConEmojiIniciales, user.id, tipo='preferencias')
    await user.send("Seleccione sus razas favoritas en orden de preferencia:", view=view)
    
class WelcomeView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id

    @discord.ui.button(label="Empezar", style=discord.ButtonStyle.green, custom_id="start_registration")
    async def start_registration(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = ModalNuevoUsuario(self.user_id)
        await interaction.response.send_modal(modal)


class ModalNuevoUsuario(discord.ui.Modal, title="Registro de Usuario"):
    nombre_bloodbowl = discord.ui.TextInput(
        label="Tu nombre en Blood Bowl:",
        style=discord.TextStyle.short,
        placeholder="Ingresa tu nombre aquí...",
        required=True
    )

    def __init__(self, usuario_id):
        super().__init__()
        self.usuario_id = usuario_id

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        Session = sessionmaker(bind=GestorSQL.conexionEngine())
        session = Session()
        nuevo_usuario = GestorSQL.Inscripcion(id_usuario_discord=self.usuario_id, nombre_bloodbowl=self.nombre_bloodbowl.value)
        session.add(nuevo_usuario)
        session.commit()
        session.close()
        division_view = DivisionView(self.usuario_id)
        await interaction.followup.send("Como aún no te conocemos no sabemos cuales son tus habilidades como entrenador. ¡Elige una división para tu bautismo de sangre!:", view=division_view)

                
# class EquiposView(discord.ui.View):
#     def __init__(self, usuario_id, equipos, next_step=None):
#         super().__init__()
#         self.usuario_id = usuario_id
#         self.next_step = next_step
#         for equipo in equipos:
#             self.add_item(discord.ui.Button(label=equipo.nombre_equipo, style=discord.ButtonStyle.primary, custom_id=f"equipo_{equipo.id}"))
#
#     async def interaction_check(self, interaction: discord.Interaction):
#         if 'custom_id' in interaction.data and interaction.data['custom_id'].startswith("equipo_"):
#             await self.elegir_equipo(interaction)
#         return True
#
#     async def elegir_equipo(self, interaction: discord.Interaction):
#         equipo_id = interaction.data['custom_id'].split('_')[1]
#         await interaction.response.defer()
#         Session = sessionmaker(bind=GestorSQL.conexionEngine())
#         session = Session()
#         try:
#             equipo = session.query(GestorSQL.equiposReformados).filter_by(id=equipo_id).first()
#             inscripcion = session.query(GestorSQL.Inscripcion).filter_by(id_usuario_discord=self.usuario_id).first()
#             if inscripcion:
#                 inscripcion.nombre_equipo = equipo.nombre_equipo
#                 session.commit()
#                 if self.next_step == 'preferencias':
#                     await registroPreferencias(interaction.user)
#                 else:
#                     await interaction.followup.send("Ha terminado la inscripción para la cuarta edición de la Butter Cup. ¡Nos vemos el 12 de mayo!. Te avisaré de todo por mp 😉")
#                     await asyncio.sleep(60)
#                     await interaction.followup.send("¡Se me olvidaba! La Butter Cup tiene premios y sorteos alucinantes, lamentablemente el Lombard es un vago y aún no ha hecho el sorteo anterior. ¡Pásate por el canal 💰premios💰 para echarles un ojo! ¡Te avisaremos cuando se abran los de esta edición!")
#         except Exception as e:
#             session.rollback()
#             await interaction.followup.send("Error al registrar el equipo.", ephemeral=True)
#         finally:
#             session.close()

class RazasView(discord.ui.View):
    def __init__(self, races, racesConEmoji, usuario_id, tipo, preferencias=None):
        super().__init__(timeout=None)
        self.usuario_id   = usuario_id
        self.races        = races
        self.racesConEmoji= racesConEmoji
        self.tipo         = tipo
        self.seleccionados= []
        self.preferencias = preferencias or []
        self.max_selecciones = NUM_PREFERENCIAS if tipo == 'preferencias' else NUM_BANS

        # Recorremos ambos arrays juntos
        for race, emoji in zip(races, racesConEmoji):
            btn = discord.ui.Button(
                label=emoji,
                style=discord.ButtonStyle.primary,
                custom_id=race
            )
            btn.callback = self.select_race
            self.add_item(btn)
    
    async def select_race(self, interaction: discord.Interaction):
        race_selected = interaction.data['custom_id']
        self.seleccionados.append(race_selected)
        if len(self.seleccionados) < self.max_selecciones:
            for item in self.children:
                if getattr(item, "custom_id", None) == race_selected:
                    item.disabled = True
                    break
            await interaction.response.edit_message(view=self)

        if len(self.seleccionados) == self.max_selecciones:
            for item in self.children:
                item.disabled = True

            await interaction.response.edit_message(view=self)
            
            if self.tipo == 'preferencias':
                mensaje = f"Sus preferencias son: {', '.join(self.seleccionados)}"
                await interaction.followup.send(mensaje)
                new_races = [r for r in self.races if r not in self.seleccionados]
                new_racesConEmoji = [emoji for r, emoji in zip(self.races, self.racesConEmoji) if r not in self.seleccionados]
                new_view = RazasView(new_races, new_racesConEmoji, self.usuario_id, 'bans',preferencias=self.seleccionados)
                await interaction.followup.send("Ahora debe banear 5 razas con las que no quiere jugar:", view=new_view)
            else:
                mensaje = f"Sus bans son: {', '.join(self.seleccionados)}"
                guardar_preferencias_bans(self.usuario_id,self.preferencias,self.seleccionados)
                await interaction.followup.send(mensaje)
                await interaction.followup.send("Ha terminado la inscripción para la quinta edición de la Butter Cup. ¡Nos vemos el 13 de septiembre!. Te avisaré de todo por mp 😉")
                await asyncio.sleep(60)
                await interaction.followup.send("¡Se me olvidaba! La Butter Cup tiene premios y sorteos alucinantes, lamentablemente el Lombard es un vago y aún no ha hecho el sorteo anterior. ¡Pásate por el canal <#1218155443252105258> para echarles un ojo! ¡Te avisaremos cuando se abran los de esta edición!")
        
def guardar_preferencias_bans(usuario_id, preferencias, bans):
    Session = sessionmaker(bind=GestorSQL.conexionEngine())
    session = Session()
    try:
        inscripcion = session.query(GestorSQL.Inscripcion).filter_by(id_usuario_discord=usuario_id).first()
        if not inscripcion:
            inscripcion = GestorSQL.Inscripcion(id_usuario_discord=usuario_id)
            session.add(inscripcion)
        
        preferencias_ext = (preferencias + [None] * NUM_PREFERENCIAS)[:NUM_PREFERENCIAS]
        bans_ext = (bans + [None] * NUM_BANS)[:NUM_BANS]

        inscripcion.pref1 = preferencias_ext[0]
        inscripcion.pref2 = preferencias_ext[1]
        inscripcion.pref3 = preferencias_ext[2]
        inscripcion.pref4 = preferencias_ext[3]
        inscripcion.pref5 = preferencias_ext[4]

        inscripcion.ban1 = bans_ext[0]
        inscripcion.ban2 = bans_ext[1]
        inscripcion.ban3 = bans_ext[2]
        inscripcion.ban4 = bans_ext[3]
        inscripcion.ban5 = bans_ext[4]
        
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"Error al guardar preferencias y bans: {str(e)}")
    finally:
        session.close()
        

class DivisionView(discord.ui.View):
    def __init__(self, usuario_id):
        super().__init__(timeout=None)
        self.usuario_id = usuario_id
    
    @discord.ui.button(label="Plata", style=discord.ButtonStyle.primary, custom_id="plata")
    async def select_plata(self, interaction: discord.Interaction,button: discord.ui.Button):
        await self.save_division(interaction, "Plata")
    
    @discord.ui.button(label="Bronce", style=discord.ButtonStyle.secondary, custom_id="bronce")
    async def select_bronce(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.save_division(interaction, "Bronce")
    
    async def save_division(self, interaction: discord.Interaction, division: str):
        await interaction.response.defer()
        Session = sessionmaker(bind=GestorSQL.conexionEngine())
        session = Session()
        try:
            inscripcion = session.query(GestorSQL.Inscripcion).filter_by(id_usuario_discord=self.usuario_id).first()
            inscripcion.division = division
            session.commit()
            await registroEquipoNuevo(interaction.user)
        except Exception as e:
            session.rollback()
            await interaction.followup.send_message("Error al guardar la división.", ephemeral=True)
        finally:
            session.close()




