import GestorSQL
import UtilesDiscord
import discord
import APIBbowl
from sqlalchemy.orm import sessionmaker
from sqlalchemy import func

RAZA_COSTES = {
    4:    {'reroll': 60, 'lineman': 50},
    18:   {'reroll': 70, 'lineman': 35},
    1000: {'reroll': 60, 'lineman': 45},
    1002: {'reroll': 70, 'lineman': 50},
    6:    {'reroll': 60, 'lineman': 40},
    1:    {'reroll': 50, 'lineman': 50},
    17:   {'reroll': 70, 'lineman': 40},
    1001: {'reroll': 70, 'lineman': 50},
    24:   {'reroll': 70, 'lineman': 45},
    11:   {'reroll': 60, 'lineman': 30},
    2:    {'reroll': 50, 'lineman': 70},
    3:    {'reroll': 50, 'lineman': 50},
    9:    {'reroll': 50, 'lineman': 70},
    8:    {'reroll': 60, 'lineman': 60},
    14:   {'reroll': 50, 'lineman': 60},
    5:    {'reroll': 70, 'lineman': 60},
    22:   {'reroll': 70, 'lineman': 40},
    10:   {'reroll': 70, 'lineman': 40},
    7:    {'reroll': 50, 'lineman': 70},
    12:   {'reroll': 60, 'lineman': 50},
    15:   {'reroll': 60, 'lineman': 50},
}

def calcular_dinero_reforma(session, equipo_id):
    victorias = empates = derrotas = 0
    reward_points = 0.0

    # Traer todos los registros de partidos de este equipo
    partidos = session.query(GestorSQL.RegistroPartidos).filter(
        GestorSQL.RegistroPartidos.idEquiposReformados == equipo_id
    ).all()

    for partido in partidos:
        # Sumar triunfos/empates/derrotas
        victorias += partido.ganados
        empates    += partido.empatados
        derrotas   += partido.perdidos

        # Obtener las recompensas para esta edición de reforma
        recompensas = session.query(GestorSQL.Recompensas).filter(
            GestorSQL.Recompensas.idEquiposReformados == equipo_id,
            GestorSQL.Recompensas.sesion               == partido.Edicion
        ).all()

        # Acumular puntos de recompensa (1 ó 0.5)
        for rec in recompensas:
            reward_points += float(rec.recompensa)

    # Calcular cuánto añade el sistema de recompensas
    full_points   = int(reward_points)                    # puntos completos
    has_half_point = (reward_points - full_points) >= 0.5 # si hay medio punto sobrante
    reward_money  = full_points * 30000
    if has_half_point:
        reward_money += 10000

    # Base de 1 000 000 + por resultados + por recompensas
    return (
        1000000
        + victorias * 15000
        + empates    * 10000
        + derrotas   * 5000
        + reward_money
    )

# Función principal para lanzar las reformas
async def lanzar_reformas(bot):
    Session = sessionmaker(bind=GestorSQL.conexionEngine())
    session = Session()

    equipos_a_reformar = (
        session.query(
            GestorSQL.RegistroPartidos.idEquiposReformados.label('equipo_id'),
            GestorSQL.equiposReformados.nombre_equipo,
            GestorSQL.equiposReformados.id_usuario
        )
        .join(GestorSQL.equiposReformados, GestorSQL.RegistroPartidos.idEquiposReformados == GestorSQL.equiposReformados.id)
        .group_by(
            GestorSQL.RegistroPartidos.idEquiposReformados,
            GestorSQL.equiposReformados.nombre_equipo,
            GestorSQL.equiposReformados.id_usuario
        )
        .having(func.count(GestorSQL.RegistroPartidos.id) == 2)
        .all()
    )

    for equipo_id, nombre_equipo, id_usuario in equipos_a_reformar:
        usuario_discord_id = session.query(GestorSQL.Usuario.id_discord).filter(
            GestorSQL.Usuario.idUsuarios == id_usuario
        ).scalar()

        # Obtenemos el objeto User de Discord y su nombre
        miembro = bot.get_user(int(usuario_discord_id))
        nombre_usuario = miembro.name if miembro else "¡Usuario!"

        dinero = calcular_dinero_reforma(session, equipo_id)

        mensaje = (
            f"👋 ¡Hola **{nombre_usuario}**!\n\n"
            f"📰 Tu equipo **{nombre_equipo}** debe ser reformado.\n\n"
            f"💰 Tienes **{dinero} monedas** para gastar.\n\n"
            "📝 **Reglas para la reforma:**\n"
            "• ⚽ **Equipo mínimo**: al menos 11 jugadores y respetar las reglas estándar.\n"
            "• 🚫 **Re-Rolls**: no se pueden vender.\n"
            "• 🧓 **Veteranos**: cuestan su valor actual + 20 K.\n"
            "• 🔄 **Recompras**: pierden experiencia, salvo que pagues + 20 K para mantenerla (o + 40 K si puede comprar habilidades primarias).\n"
            "• 💼 El dinero que sobre será tu **nueva tesorería**.\n"
            "• 🏅 Si fuiste **finalista** de algún playoff se te ha agregado directamente al dinero. Si prefieres otro premio ¡Diselo a Pikoleto!\n\n"
            "✏️ Envía `/reforma` por privado para empezar tu reforma."
        )

        if miembro:
            try:
                await miembro.send(mensaje)
            except discord.Forbidden:
                print(f"No se pudo enviar mensaje a {usuario_discord_id}")

        aviso_admin = (
            f"El usuario <@{usuario_discord_id}> ({nombre_usuario}) debe reformar el equipo {nombre_equipo}.\n"
            f"Fondos disponibles: {dinero} monedas."
        )
        await UtilesDiscord.mensaje_administradores(aviso_admin)

    session.close()
    
async def iniciar_reforma(interaction: discord.Interaction, api_token: str):
    # —— Preparar sesión y usuario —— 
    Session = sessionmaker(bind=GestorSQL.conexionEngine())
    session = Session()
    usuario_db = session.query(GestorSQL.Usuario).filter_by(
        id_discord=interaction.user.id
    ).first()
    if not usuario_db:
        await interaction.response.send_message(
            "Usuario no encontrado en la base de datos.", ephemeral=True
        )
        return session.close()

    # —— Buscar equipo a reformar —— 
    equipos = session.query(GestorSQL.equiposReformados).filter_by(
        id_usuario=usuario_db.idUsuarios
    ).all()
    equipo_reformar = None
    for eq in equipos:
        cnt = session.query(func.count(GestorSQL.RegistroPartidos.id)).filter(
            GestorSQL.RegistroPartidos.idEquiposReformados == eq.id
        ).scalar()
        if cnt == 2:
            equipo_reformar = eq
            break
    if not equipo_reformar:
        await interaction.response.send_message(
            "No tienes equipos que reformar.", ephemeral=True
        )
        return session.close()

    # —— Dinero base de la reforma —— 
    dinero = calcular_dinero_reforma(session, equipo_reformar.id)

    # —— Datos del equipo desde la API —— 
    datos_api = APIBbowl.buscarequipo(api_token, equipo_reformar.id_equipo)
    if not datos_api:
        await interaction.response.send_message(
            "Error al obtener datos del equipo en la API.", ephemeral=True
        )
        return session.close()

    team_info = datos_api.get("team", {})
    idrace    = team_info.get("idraces", None)
    rerolls   = team_info.get("rerolls", 0)

    # —— Descontar rerolls al inicio —— 
    precio_rr_k      = RAZA_COSTES.get(idrace, {}).get('reroll', 0)
    total_rr_cost_k  = rerolls * precio_rr_k
    dinero_restante_k = dinero//1000 - total_rr_cost_k
    dinero_restante   = dinero_restante_k * 1000

    # —— 1) Mensaje inicial con reglas —— 
    reglas = (
        "📋 **Reglas de la Reforma**\n"
        "• Tienes un dinero inicial del que se resta automáticamente el coste de los RR.\n"
        "• Debes seleccionar con los botones los jugadores que quieras mantener. Su coste es su valor normal +20k.\n"
        "• Si quieres mantener la **experiencia** de un jugador, debes pagar **20k** (o **40k** si puede comprar habilidad general). "
        "Para ello, envía un mensaje privado a **Pikoleto** indicando qué jugadores mantienen experiencia.\n"
        "• El dinero sobrante se añadirá a tu **tesorería** para comprar jugadores, médico, etc.\n"
        "• Debes mantener al menos **11 jugadores** (el sistema ya comprueba que puedas completar el equipo con lineas).\n\n"
        "¡Empecemos!"
    )
    await interaction.response.send_message(reglas, ephemeral=True)

    # —— 2) Informar del descuento de RR —— 
    await interaction.followup.send(
        f"💸 Se han descontado los **{rerolls} RR** a **{precio_rr_k}k** cada uno "
        f"(total **{total_rr_cost_k}k**).\n"
        f"💰 Dinero disponible para recompras: **{dinero_restante_k}k**.",
        ephemeral=True
    )

    # —— 3) Construir lista de jugadores —— 
    roster = datos_api.get("roster", [])
    jugadores = []
    for p in roster:
        jugadores.append({
            "idraces": p.get("idraces"),
            "name":    p.get("name", ""),
            "value":   (p.get("value", 0) + 20)  # ya en 'k'
        })

    # —— 4) Lanzar la vista interactiva —— 
    view = ReformaView(
        jugadores,
        dinero_restante,
        idrace,
        discord_name=usuario_db.nombre_discord,
        bloodbowl_name=usuario_db.nombre_bloodbowl,
        team_name=equipo_reformar.nombre_equipo
    )
    await interaction.followup.send(
        "Selecciona los jugadores que deseas **mantener** (mínimo 11).",
        view=view, ephemeral=True
    )
    session.close()

class ReformaView(discord.ui.View):
    def __init__(self, jugadores, dinero, raza,
                 discord_name, bloodbowl_name, team_name):
        super().__init__(timeout=None)
        self.jugadores = jugadores
        self.dinero_restante = dinero
        self.raza = raza
        self.discord_name = discord_name
        self.bloodbowl_name = bloodbowl_name
        self.team_name = team_name
        self.seleccionados = set()

        # Etiqueta de dinero
        self.dinero_label = discord.ui.Button(
            label=f"Dinero restante: {self.dinero_restante//1000}k",
            disabled=True
        )
        self.add_item(self.dinero_label)

        # Botones de cada jugador
        for idx, j in enumerate(jugadores):
            btn = discord.ui.Button(
                label=f"{j['name']} — {j['value']}k",
                style=discord.ButtonStyle.green,
                custom_id=f"contratar_{idx}"
            )
            btn.callback = self.generar_callback(j, btn, idx)
            self.add_item(btn)

        # Botón Finalizar
        aceptar = discord.ui.Button(
            label="✅ Aceptar selección",
            style=discord.ButtonStyle.blurple
        )
        aceptar.callback = self.finalizar_reforma
        self.add_item(aceptar)

    def generar_callback(self, jugador, boton, idx):
        async def callback(interaction: discord.Interaction):
            if idx in self.seleccionados:
                return  # ya seleccionado

            # Coste del jugador
            cost_jugador = jugador['value'] * 1000

            # ¿Cuántos jugadores habremos tras esta compra?
            nuevos_seleccionados = len(self.seleccionados) + 1
            faltan_para_11 = max(0, 11 - nuevos_seleccionados)

            # Coste de linemen necesarios
            coste_lineman_k = RAZA_COSTES.get(self.raza, {}).get('lineman', 0)
            cost_lineman = faltan_para_11 * coste_lineman_k * 1000

            total_needed = cost_jugador + cost_lineman

            if total_needed > self.dinero_restante:
                await interaction.response.send_message(
                    f"❌ No puedes mantener **{jugador['name']}**. "
                    f"Necesitarás {cost_jugador//1000}k + {faltan_para_11}×{coste_lineman_k}k "
                    f"(lineas) = **{total_needed//1000}k**, "
                    f"pero sólo te quedan **{self.dinero_restante//1000}k**.",
                    ephemeral=True
                )
                return

            # Aplicar selección
            self.seleccionados.add(idx)
            self.dinero_restante -= cost_jugador
            boton.label = f"✔️ {jugador['name']} — {jugador['value']}k"
            boton.disabled = True
            self.dinero_label.label = f"Dinero restante: {self.dinero_restante//1000}k"

            await interaction.response.edit_message(view=self)

        return callback

    async def finalizar_reforma(self, interaction: discord.Interaction):
        # Número de jugadores seleccionados
        seleccion_count = len(self.seleccionados)
        # Linemen que faltan hasta 11 plazas
        faltan = max(0, 11 - seleccion_count)

        # Coste de cada lineman (en k) según la raza
        coste_lin_k = RAZA_COSTES.get(self.raza, {}).get('lineman', 0)
        total_lin_k = faltan * coste_lin_k

        # Dinero antes y después de añadir linemen
        antes_k = self.dinero_restante // 1000
        self.dinero_restante -= total_lin_k * 1000
        despues_k = self.dinero_restante // 1000

        # Nombres elegidos
        elegidos = [self.jugadores[i]['name'] for i in self.seleccionados]

        # Mensaje final
        mensaje = [
            "🔧 **Reforma completada**. Has mantenido a:",
            *[f"- {n}" for n in elegidos]
        ]
        if faltan > 0:
            mensaje += [
                f"\n⚙️ Faltan **{faltan} jugadores** hasta 11. Coste mínimo: **{total_lin_k}k**.",
                f"💰 Si compras sólo lineas, quedarían **{despues_k}k** para la tesorería "
                f"(tenías {antes_k}k antes de completar el equipo que se te agregarán)."
            ]

        # —— Recordatorios adicionales —— 
        mensaje += [
            "\n❗️ **Importante**: No borres a ningún jugador hasta que Pikoleto te lo confirme por privado.",
            "✉️ Si quieres mantener **experiencia**, escríbele un mensaje privado a Pikoleto "
            "para que te descuente el coste correspondiente."
        ]

        # Confirmación al usuario
        await interaction.response.send_message("\n".join(mensaje))

        # Notificación a administradores
        admin_msg = (
            "**Reforma completada**\n"
            f"• Discord: {self.discord_name}\n"
            f"• BloodBowl: {self.bloodbowl_name}\n"
            f"• Equipo: {self.team_name}\n"
            f"• Jugadores mantenidos: {', '.join(elegidos)}\n"
            f"• Dinero restante antes de linemen: {antes_k}k"
        )
        await UtilesDiscord.mensaje_administradores(admin_msg)

        self.stop()