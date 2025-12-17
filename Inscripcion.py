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
    "👴🏻Alianza del viejo mundo👴🏻","🏹Amazonas🏹", "🐐Caos Elegido🐐", "⛏Enanos⛏","🎠Enanos del Caos🎠", "🔮Elfos oscuros🔮",
    "🌲Elfos silvanos🌲", "🦎Hombres lagarto🦎", "🐺Horror nigromántico🐺", "🙎🏻‍Humanos🙎🏻‍",
    "🤢Inframundo🤢","🩸Khrone🩸", "💀No muertos💀", "👲🏻Nobleza Imperial👲🏻","❄Nordicos❄", "🤮Nurgle🤮",
    "🐸Orcos🐸", "👹Orcos negros👹", "👨‍👧‍👦Renegados👨‍👨‍👧", "🐀Skaven🐀", "🤾🏻‍Unión elfica🤾","🦇Vampiros🦇","🧚🏻‍♂️Stunty🌜"
]
racesIniciales = [
    "Alianza del viejo mundo","Amazonas", "Caos Elegido", "Enanos","Enanos del Caos", "Elfos oscuros",
    "Elfos silvanos", "Hombres lagarto", "Horror nigromántico", "Humanos",
    "Inframundo","Khorne", "No muertos", "Nobleza Imperial", "Nordicos","Nurgle",
    "Orcos", "Orcos negros", "Renegados", "Skaven", "Unión elfica","Vampiros","Stunty"
]

tipoPreferenciaOptions = [
    ("Nuevo", "Nuevo"),
    ("Existente", "Existente")
]


async def enviar_mensaje_flexibilidad(user):
    await user.send(
"A continuación te explicamos, de forma clara y rápida, cómo se organizarán los equipos y los grupos:\n\n1️⃣ EQUIPOS NUEVOS\nTras el sorteo de los equipos para quienes hayan elegido la opción \"nuevo\", los grupos se crearán automáticamente.\n\n2️⃣ EVITAR MIRRORS\nSe intentará, siempre que sea posible, que no haya dos equipos iguales dentro del mismo grupo.\n\n3️⃣ BALANCE DE GRUPOS\nBuscaremos grupos equilibrados, con una composición aproximada de:\n- 2 equipos de fuerza\n- 2 equipos equilibrados\n- 2 equipos de agilidad\n(Este equilibrio se aplicará en la medida de lo posible).\n\n4️⃣ SI NO SON MÚLTIPLOS DE 6\nSi el número de equipos nuevos no es múltiplo de 6, se intentará que los equipos nuevos se enfrenten a los equipos de menor valoración disponible.\n\n5️⃣ __FLEXIBILIDAD NUEVO / EXISTENTE__\nSi alguien puede darnos flexibilidad para usar nuevo o existente, se lo agradeceremos mucho.\nNuestro objetivo es que los equipos nuevos sean múltiplos de 6 dentro de su división.\n👉 Para ofrecer esta flexibilidad, envía un MP a Pikoleto.\n\n"
    )

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
            await user.send(f"Gracias por inscribirte en la Sexta edición de la Butter Cup, {usuario.nombre_bloodbowl}!")
            await seleccionar_tipo_preferencia(user)
        else:
            await user.send(f"Ya tiene un registro comenzado {usuario.nombre_bloodbowl}, si continua sus datos se sobreescribirán")
            await seleccionar_tipo_preferencia(user)
    else:
        view = WelcomeView(user.id)
        await user.send("""Bienvenido a la sexta edición de la BUTTER CUP.
                        
Estamos emocionados por contar contigo. Vamos a empezar tu inscripción.

                                                
Primero necesitamos saber tu nombre EXACTO en blood bowl, pulsa EMPEZAR y escribelo (¡importan las mayúsculas!)""", view=view)
    session.close()
    
async def seleccionar_tipo_preferencia(user):
    view = TipoPreferenciaView(user.id)
    await user.send("Elija su preferencia de equipo:", view=view)


class TipoPreferenciaView(discord.ui.View):
    def __init__(self, usuario_id):
        super().__init__(timeout=None)
        self.usuario_id = usuario_id
        for label, desc in tipoPreferenciaOptions:
            button = discord.ui.Button(label=desc, style=discord.ButtonStyle.primary, custom_id=label)
            button.callback = self.select_preference
            self.add_item(button)

    async def select_preference(self, interaction: discord.Interaction):
        preference = interaction.data['custom_id']
        await interaction.response.defer()

        Session = sessionmaker(bind=GestorSQL.conexionEngine())
        session = Session()
        try:
            inscripcion = session.query(GestorSQL.Inscripcion).filter_by(id_usuario_discord=self.usuario_id).first()
            if not inscripcion:
                inscripcion = GestorSQL.Inscripcion(id_usuario_discord=self.usuario_id)
                session.add(inscripcion)
            inscripcion.tipoPreferencia = preference
            session.commit()

            await enviar_mensaje_flexibilidad(interaction.user)

            if preference == 'Nuevo':
                await registroEquipoNuevo(interaction.user)
            elif preference == 'Existente':
                await registroEquipoExistente(interaction.user)
        except Exception as e:
            session.rollback()
            await interaction.followup.send("Error al registrar la preferencia.", ephemeral=True)
        finally:
            session.close()

async def registroEquipoNuevo(user):
    await user.send("""Para crear un nuevo equipo en la Butter Cup primero te tenemos que adjudicar una raza por __**sorteo**__.
                    
 El sorteo se realizará en directo aproximadamente el <t:1766950200:F> en canal de twitch de SrLombard.
                    
Para que te podamos asignar una raza deberás elegir __5 favoritas__ y __banear otras 5__.
Intentaremos asignarte una de tus razas favoritas, pero hay un número limitado de plazas por raza. Si no se pudiera se te asignaría cualquier otra raza pero nunca una de las baneadas asi que... ¡elige sabiamente!""")
    await registroPreferencias(user)
    
async def registroEquipoExistente(user, next_step=None):
    Session = sessionmaker(bind=GestorSQL.conexionEngine())
    session = Session()
    usuario = session.query(GestorSQL.Usuario).filter_by(id_discord=user.id).first()
    if usuario:
        equipos = session.query(GestorSQL.equiposReformados).filter_by(id_usuario=usuario.idUsuarios).all()
        if equipos:
            view = EquiposView(user.id, equipos, next_step)
            await user.send("Selecciona uno de tus equipos existentes:", view=view)
        else:
            await user.send("No tiene equipos creados, continuaremos con un equipo nuevo.")
            await registroEquipoNuevo(user)
    session.close()

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


class EquiposView(discord.ui.View):
    def __init__(self, usuario_id, equipos, next_step=None):
        super().__init__()
        self.usuario_id = usuario_id
        self.next_step = next_step
        for equipo in equipos:
            self.add_item(discord.ui.Button(label=equipo.nombre_equipo, style=discord.ButtonStyle.primary, custom_id=f"equipo_{equipo.id}"))

    async def interaction_check(self, interaction: discord.Interaction):
        if 'custom_id' in interaction.data and interaction.data['custom_id'].startswith("equipo_"):
            await self.elegir_equipo(interaction)
        return True

    async def elegir_equipo(self, interaction: discord.Interaction):
        equipo_id = interaction.data['custom_id'].split('_')[1]
        await interaction.response.defer()
        Session = sessionmaker(bind=GestorSQL.conexionEngine())
        session = Session()
        try:
            equipo = session.query(GestorSQL.equiposReformados).filter_by(id=equipo_id).first()
            inscripcion = session.query(GestorSQL.Inscripcion).filter_by(id_usuario_discord=self.usuario_id).first()
            if inscripcion:
                inscripcion.nombre_equipo = equipo.nombre_equipo
                session.commit()
                if self.next_step == 'preferencias':
                    await registroPreferencias(interaction.user)
                else:
                    await interaction.followup.send("Ha terminado la inscripción para la quinta edición de la Butter Cup. ¡Nos vemos el 28 de Diciembre!. Te avisaré de todo por mp 😉")
                    await asyncio.sleep(60)
                    await interaction.followup.send("¡Se me olvidaba! La Butter Cup tiene premios y sorteos alucinantes, Es totalmente opcional y sirve para financiar los premios físicos. ¡Pásate por el canal <#1218155443252105258> para echarles un ojo!")
        except Exception as e:
            session.rollback()
            await interaction.followup.send("Error al registrar el equipo.", ephemeral=True)
        finally:
            session.close()

class RazasView(discord.ui.View):
    def __init__(self, races, racesConEmoji, usuario_id, tipo, preferencias=None):
        super().__init__(timeout=None)
        self.usuario_id   = usuario_id
        self.races        = races
        self.racesConEmoji= racesConEmoji
        self.tipo         = tipo
        self.seleccionados= []
        self.preferencias = preferencias or []

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
        if len(self.seleccionados) < 5:
            for item in self.children:
                if getattr(item, "custom_id", None) == race_selected:
                    item.disabled = True
                    break
            await interaction.response.edit_message(view=self)

        if len(self.seleccionados) == 5:
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
                await interaction.followup.send("Ha terminado la inscripción para la quinta edición de la Butter Cup. ¡Nos vemos el 28 de Diciembre!. Te avisaré de todo por mp 😉")
                await asyncio.sleep(60)
                await interaction.followup.send("¡Se me olvidaba! La Butter Cup tiene premios y sorteos alucinantes, Es totalmente opcional y sirve para financiar los premios físicos. ¡Pásate por el canal <#1218155443252105258> para echarles un ojo!")
        
def guardar_preferencias_bans(usuario_id, preferencias, bans):
    Session = sessionmaker(bind=GestorSQL.conexionEngine())
    session = Session()
    try:
        inscripcion = session.query(GestorSQL.Inscripcion).filter_by(id_usuario_discord=usuario_id).first()
        if not inscripcion:
            inscripcion = GestorSQL.Inscripcion(id_usuario_discord=usuario_id)
            session.add(inscripcion)
        
        inscripcion.pref1 = preferencias[0]
        inscripcion.pref2 = preferencias[1]
        inscripcion.pref3 = preferencias[2]
        inscripcion.pref4 = preferencias[3]
        inscripcion.pref5 = preferencias[4]

        inscripcion.ban1 = bans[0]
        inscripcion.ban2 = bans[1]
        inscripcion.ban3 = bans[2]
        inscripcion.ban4 = bans[3]
        inscripcion.ban5 = bans[4]
        
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
            await seleccionar_tipo_preferencia(interaction.user)
        except Exception as e:
            session.rollback()
            await interaction.followup.send_message("Error al guardar la división.", ephemeral=True)
        finally:
            session.close()




