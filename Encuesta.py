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

class VistaPrimeraPregunta(discord.ui.View):
    def __init__(self, usuario_id):
        super().__init__(timeout=None) 
        self.usuario_id = usuario_id

    @discord.ui.button(label="1", style=discord.ButtonStyle.red, custom_id="respuesta_1")
    async def respuesta_1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await guardar_respuesta(self.usuario_id,1,1, interaction)
        await segunda_pregunta(interaction)
    
    @discord.ui.button(label="2", style=discord.ButtonStyle.danger, custom_id="respuesta_2")
    async def respuesta_2(self, interaction: discord.Interaction, button: discord.ui.Button):
        await guardar_respuesta(self.usuario_id,1,2, interaction)
        await segunda_pregunta(interaction)

    @discord.ui.button(label="3", style=discord.ButtonStyle.grey, custom_id="respuesta_3")
    async def respuesta_3(self,  interaction: discord.Interaction, button: discord.ui.Button):
        await guardar_respuesta(self.usuario_id,1,3, interaction)
        await segunda_pregunta(interaction)

    @discord.ui.button(label="4", style=discord.ButtonStyle.green, custom_id="respuesta_4")
    async def respuesta_4(self, interaction: discord.Interaction, button: discord.ui.Button):
        await guardar_respuesta(self.usuario_id,1,4, interaction)
        await segunda_pregunta(interaction)

    @discord.ui.button(label="5", style=discord.ButtonStyle.blurple, custom_id="respuesta_5")
    async def respuesta_5(self, interaction: discord.Interaction, button: discord.ui.Button):
        await guardar_respuesta(self.usuario_id,1,5, interaction)
        await segunda_pregunta(interaction)


class VistaSegundaPregunta(discord.ui.View):
    def __init__(self, usuario_id):
        super().__init__(timeout=None)  
        self.usuario_id = usuario_id

    @discord.ui.button(label="1", style=discord.ButtonStyle.red, custom_id="respuesta_1")
    async def respuesta_1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await guardar_respuesta(self.usuario_id,2,1, interaction)
        await tercera_pregunta(interaction)
    
    @discord.ui.button(label="2", style=discord.ButtonStyle.danger, custom_id="respuesta_2")
    async def respuesta_2(self, interaction: discord.Interaction, button: discord.ui.Button):
        await guardar_respuesta(self.usuario_id,2,2, interaction)
        await tercera_pregunta(interaction)

    @discord.ui.button(label="3", style=discord.ButtonStyle.grey, custom_id="respuesta_3")
    async def respuesta_3(self, interaction: discord.Interaction, button: discord.ui.Button):
        await guardar_respuesta(self.usuario_id,2,3, interaction)
        await tercera_pregunta(interaction)

    @discord.ui.button(label="4", style=discord.ButtonStyle.green, custom_id="respuesta_4")
    async def respuesta_4(self, interaction: discord.Interaction, button: discord.ui.Button):
        await guardar_respuesta(self.usuario_id,2,4, interaction)
        await tercera_pregunta(interaction)

    @discord.ui.button(label="5", style=discord.ButtonStyle.blurple, custom_id="respuesta_5")
    async def respuesta_5(self, interaction: discord.Interaction, button: discord.ui.Button):
        await guardar_respuesta(self.usuario_id,2,5, interaction)
        await tercera_pregunta(interaction)


class VistaTerceraPregunta(discord.ui.View):
    def __init__(self, usuario_id):
        super().__init__(timeout=None)  
        self.usuario_id = usuario_id

    @discord.ui.button(label="No", style=discord.ButtonStyle.red, custom_id="respuesta_1")
    async def respuesta_1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await guardar_respuesta(self.usuario_id,3,"No", interaction)
        await cuarta_pregunta(interaction)
    
    @discord.ui.button(label="Si", style=discord.ButtonStyle.green, custom_id="respuesta_2")
    async def respuesta_2(self, interaction: discord.Interaction, button: discord.ui.Button):
        await guardar_respuesta(self.usuario_id,3,"Si", interaction)
        await cuarta_pregunta(interaction)

class VistaCuartaPregunta(discord.ui.View):
    def __init__(self, usuario_id):
        super().__init__(timeout=None)  
        self.usuario_id = usuario_id

    @discord.ui.button(label="😡 No", style=discord.ButtonStyle.red, custom_id="respuesta_1")
    async def respuesta_1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await guardar_respuesta(self.usuario_id,4,"No", interaction)
        await quinta_pregunta(interaction)
    
    @discord.ui.button(label="😃 Si", style=discord.ButtonStyle.green, custom_id="respuesta_2")
    async def respuesta_2(self, interaction: discord.Interaction, button: discord.ui.Button):
        await guardar_respuesta(self.usuario_id,4,"Si", interaction)
        await quinta_pregunta(interaction)
        
    @discord.ui.button(label="🤷‍♂ Aún no se como cojones va🤷‍", style=discord.ButtonStyle.grey, custom_id="respuesta_3")
    async def respuesta_3(self, interaction: discord.Interaction, button: discord.ui.Button):
        await guardar_respuesta(self.usuario_id,4,"No sé", interaction)
        await quinta_pregunta(interaction)

        
class AbrirModalQuintaPregunta(discord.ui.View):
    def __init__(self):
        super().__init__()
    
    @discord.ui.button(label="Sugerencias", style=discord.ButtonStyle.primary, custom_id="abrir_modal")
    async def abrir_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = ModalQuintaPregunta()
        await interaction.response.send_modal(modal)

async def primera_pregunta(interaction: discord.Interaction):
    view = VistaPrimeraPregunta(interaction.user.id)
    await interaction.response.send_message("¿Cómo calificarías tu experiencia general en la ButterCup?", view=view)

async def segunda_pregunta(interaction: discord.Interaction):
    view = VistaSegundaPregunta(interaction.user.id)
    await interaction.response.send_message("¿Te han parecido útiles las funciones del bot?", view=view)


async def tercera_pregunta(interaction: discord.Interaction):
    view = VistaTerceraPregunta(interaction.user.id)
    await interaction.response.send_message("¿Te ha parecido que había suficiente incentivo para quedar primero en la fase de grupo?", view=view)


async def cuarta_pregunta(interaction: discord.Interaction):
    view = VistaCuartaPregunta(interaction.user.id)
    await interaction.response.send_message("¿Te parece interesante el sistema de reformas?", view=view)

async def quinta_pregunta(interaction: discord.Interaction):
    await interaction.response.defer()
    view = AbrirModalQuintaPregunta()
    await interaction.followup.send("¿Tienes alguna sugerencia?", view=view)

async def guardar_respuesta(id_discord, id_pregunta, respuesta, interaction):
    Session = sessionmaker(bind=GestorSQL.conexionEngine())
    session = Session()
    try:
        usuario = session.query(GestorSQL.Usuario).filter_by(id_discord=id_discord).first()
        if usuario is None:
            await interaction.response.send_message("Usuario no encontrado en la base de datos.", ephemeral=True)
            return
        
        nuevo_resultado = GestorSQL.ResultadoEncuesta(
            id_usuario=usuario.idUsuarios,
            id_pregunta=id_pregunta,
            respuesta=respuesta
        )
        session.add(nuevo_resultado)
        session.commit()
    except SQLAlchemyError as e:
        session.rollback()
        await UtilesDiscord.mensaje_administradores(f"No se pudo guardar la respuesta a la pregunta {id_pregunta} del usuario {id_discord}. Error: {str(e)}")
    finally:
        session.close()


class ModalQuintaPregunta(discord.ui.Modal, title="Sugerencias"):
    respuesta = discord.ui.TextInput(
        label="¿Cuáles son tus sugerencias?",
        style=discord.TextStyle.paragraph,
        placeholder="Escribe aquí tu respuesta...",
        required=True,
        max_length=1024
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            await guardar_respuesta(interaction.user.id, 3, self.respuesta.value, interaction)
            await interaction.response.send_message(f"Gracias por tus respuestas, las tendremos en cuenta para mejorar")
        except Exception as e:
            await self.on_error(interaction, e)

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        await interaction.response.send_message(f"Ocurrió un error al procesar tu respuesta: {str(error)}", ephemeral=True)
        print(f"Error processing modal submission: {str(error)}")
