import json
import os
from PIL import Image, ImageDraw, ImageFont,ImageColor
import random
import math
import unidecode
from unidecode import unidecode

import GestorSQL
from sqlalchemy import BIGINT, create_engine, Column, Integer, String, ForeignKey, false, true,text
from sqlalchemy import and_, or_ 
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.orm import aliased
from sqlalchemy.sql import case,func

def cargar_configuracion(nombre_plantilla):
    with open('configuracion.json', 'r') as archivo_json:
        configuracion = json.load(archivo_json)
        return configuracion.get(nombre_plantilla)

def recalcular_x(draw, texto, fuente, x_inicial, y, alineacion):
    if alineacion == "centrado":
        # Obtiene el cuadro delimitador del texto
        bbox = draw.textbbox((0, 0), texto, font=fuente)
        # Calcula el ancho del texto
        texto_ancho = bbox[2] - bbox[0]
        # Recalcula x para centrar el texto
        x_nuevo = x_inicial - (texto_ancho / 2)
        return x_nuevo
    return x_inicial

def crear_imagen(nombre_plantilla, apellidos, **datos):
    configuracion = cargar_configuracion(nombre_plantilla)
    if configuracion is None:
        print("Plantilla no encontrada.")
        return None
    
    ruta_plantilla = f"./plantillas/{nombre_plantilla}{apellidos}.png"
    imagen = Image.open(ruta_plantilla)
    draw = ImageDraw.Draw(imagen)
    
    for elemento in configuracion:
        x = elemento['posicion_x']
        y = elemento['posicion_y']
        alineacion = elemento['alineacion']

        if 'piramide' in elemento:
            # Dibujar trapezoide
            color = elemento.get('color', '#FFFFFF')
            ancho_banner = int(elemento.get('ancho', 200))
            alto_banner = int(elemento.get('alto', 50))
            inclinacion = int(elemento.get('inclinacion', 20))

            puntos = [
                (x - inclinacion, y),  # Esquina superior izquierda (m�s ancha)
                (x + ancho_banner + inclinacion, y),  # Esquina superior derecha (m�s ancha)
                (x + ancho_banner, y + alto_banner),  # Esquina inferior derecha (m�s estrecha)
                (x, y + alto_banner)  # Esquina inferior izquierda (m�s estrecha)
            ]

            # Dibujar el trapezoide
            draw.polygon(puntos, fill=color)
        elif 'banner' in elemento:

            ancho_banner = int(elemento.get('ancho', 200))
            alto_banner = int(elemento.get('alto', 50))
            transparencia = int(elemento.get('transparencia', 0))  # Porcentaje de transparencia
            lado = elemento.get('lado', 'izquierdo')
            nombre_diccionario = 'lado'          
            diccionario_datos = datos.get(nombre_diccionario, {})
            color = diccionario_datos.get(lado, "")


            # Convertir el color hexadecimal a RGBA
            r, g, b = ImageColor.getrgb(color)

            # Crear una nueva capa para el rect�ngulo
            capa_trapezoide = Image.new("RGBA", (ancho_banner, alto_banner), (0, 0, 0, 0))
            draw_capa = ImageDraw.Draw(capa_trapezoide)

            # Aplicar transparencia progresiva
            for i in range(ancho_banner):
                # Calcular transparencia seg�n la posici�n y el lado
                if lado == 'izquierdo':
                    alpha = int(255 * (i / ancho_banner)) if transparencia > 0 else 255
                elif lado == 'derecho':
                    alpha = int(255 * ((ancho_banner - i) / ancho_banner)) if transparencia > 0 else 255
                else:
                    alpha = 255  # Sin transparencia si el lado no est� especificado correctamente
            
                # Dibujar l�neas verticales con el color calculado
                draw_capa.line([(i, 0), (i, alto_banner)], fill=(r, g, b, alpha))

            # Pegar el rect�ngulo en la imagen principal
            imagen.paste(capa_trapezoide, (x, y), capa_trapezoide)        
        elif 'ganador' in elemento:
            nombre_diccionario = 'ganador'          
            diccionario_datos = datos.get(nombre_diccionario, {})
            icono_ruta = diccionario_datos.get("ruta", "")
            x=diccionario_datos.get("x", "")
            y=diccionario_datos.get("y", "")
            try:
                icono_victoria = Image.open(icono_ruta)
            except IOError:
                print(f"No se pudo abrir el archivo: {icono_ruta}")
                continue
            imagen.paste(icono_victoria, (x, y), icono_victoria)

        elif  'icono' in elemento:
            # Procesar icono           
            nombre_diccionario = elemento['nombre_diccionario']           
            clave = elemento['clave']
            diccionario_datos = datos.get(nombre_diccionario, {})
            texto = diccionario_datos.get(clave, "")
            texto = unidecode(texto) 
            icono_ruta = f"./Iconos/{texto}.png"
            try:
                icono_imagen = Image.open(icono_ruta)
            except IOError:
                print(f"No se pudo abrir el archivo: {icono_ruta}")
                continue
            
            ancho_icono = int(elemento.get('ancho_icono', 100))  
            alto_icono = int(elemento.get('alto_icono', 100))  
            icono_imagen = icono_imagen.resize((ancho_icono,alto_icono), Image.LANCZOS)

            if alineacion == "centrado":
                x_icono = x - (ancho_icono) // 2
            else:
                x_icono = x
            imagen.paste(icono_imagen, (x_icono, y), icono_imagen)
        else:
            # Procesar texto
            if apellidos:
                grupo= apellidos
            else:
                datos_grupo = datos.get('grupo', {})
                grupo = datos_grupo.get("0", "")

            if 'funcionColor' in elemento and elemento['funcionColor']:
                color = seleccionar_color(grupo)
            else:
                color = elemento.get('color', '#FFFFFF')

            fuente = ImageFont.truetype(f"./fonts/{elemento['fuente']}", elemento['size'])   
            if  'titulo' in elemento:
                texto = seleccionarTitulo(grupo)
            elif 'mitexto' in elemento:
                texto = elemento.get('texto', '')
            else:
                nombre_diccionario = elemento['nombre_diccionario']
                clave = elemento['clave']
                diccionario_datos = datos.get(nombre_diccionario, {})
                texto = str(diccionario_datos.get(clave, ""))
            
            x_texto = recalcular_x(draw, texto, fuente, x, y, alineacion)
            if elemento.get('efecto') == 'contorno':
                outline_color = elemento.get('outlineColor','#FFFFFF')
                outline_width = int(elemento.get('ancho_contorno', 2))
                dibujaContorno(draw, x_texto, y, texto, f"./fonts/{elemento['fuente']}", color, outline_color, outline_width,elemento['size'])                                      
            draw.text((x_texto, y), texto, fill=color, font=fuente)
                
    numero_aleatorio = random.randint(100000, 999999)
    ruta_imagen_final = f"./temp/imagenes/{nombre_plantilla}_{numero_aleatorio}.png"
    imagen.save(ruta_imagen_final)

    imagen.close()
    return ruta_imagen_final

def dibujaContorno(draw, x, y, texto, fuente, fill, outline_color, outline_width, sizeOriginal):
    fuente_base = ImageFont.truetype(fuente, sizeOriginal)
    # Definir desplazamientos para el contorno
    desplazamientos = [
        (-outline_width, 0), (outline_width, 0), (0, -outline_width), (0, outline_width),
        (-outline_width, -outline_width), (outline_width, -outline_width),
        (-outline_width, outline_width), (outline_width, outline_width)
    ]

    # Dibujar el contorno alrededor del texto
    for dx, dy in desplazamientos:
        draw.text((x + dx, y + dy), texto, font=fuente_base, fill=outline_color)


def eliminar_imagen(ruta_imagen):
    try:
        os.remove(ruta_imagen)
        print(f"Imagen {ruta_imagen} eliminada correctamente.")
    except Exception as e:
        print(f"Error al eliminar la imagen {ruta_imagen}: {e}")
        
def seleccionar_color(apellidos):
    if apellidos in [1, 2, 3,4]:
        return '#B69200'
    elif apellidos in [5, 6,7,8,9]:
        return '#A6A6A6'
    elif apellidos in [10,11,12,13,14,15]:
        return '#CD7F32'

def seleccionarTitulo(apellidos):
    if apellidos == 1:
        return "División Oro A"
    if apellidos == 2:
        return "División Oro B"
    if apellidos == 3:
        return "División Oro C"
    if apellidos == 4:
        return "División Oro D"
    if apellidos == 5:
        return "División Plata A"
    if apellidos == 6:
        return "División Plata B"
    if apellidos == 7:
        return "División Plata C"
    if apellidos == 8:
        return "División Plata D"
    if apellidos == 9:
        return "División Plata E"
    if apellidos == 10:
        return "División Bronce A"
    if apellidos == 11:
        return "División Bronce B"
    if apellidos == 12:
        return "División Bronce C"
    if apellidos == 13:
        return "División Bronce D"
    if apellidos == 14:
        return "División Bronce E"
    if apellidos == 15:
        return "División Bronce F"
    

async def imagenResultado(idPartido):
    Session = sessionmaker(bind=GestorSQL.conexionEngine())
    session = Session()
    try:
        entrenadores = {}
        nombre_equipos = {}
        escudos = {}
        resultados = {}
        razas = {}
        kos = {}
        heridos = {}
        muertos = {}
        ganador = {}
        grupo = {}
        lado = {}

        partido = session.query(GestorSQL.Partidos).filter_by(idPartidos=idPartido).first()
        if not partido:
            print(f"No se encontró partido con el id {idPartido}")
            return None

        UsuarioAlias1 = aliased(GestorSQL.Usuario)
        UsuarioAlias2 = aliased(GestorSQL.Usuario)

        # Buscar coach1 y coach2 desde distintas tablas
        registro = (
            session.query(GestorSQL.Calendario)
            .filter(GestorSQL.Calendario.partidos_idPartidos == idPartido)
            .first()
            or session.query(GestorSQL.PlayOffsOro)
            .filter(GestorSQL.PlayOffsOro.partidos_idPartidos == idPartido)
            .first()
            or session.query(GestorSQL.PlayOffsPlata)
            .filter(GestorSQL.PlayOffsPlata.partidos_idPartidos == idPartido)
            .first()
            or session.query(GestorSQL.PlayOffsBronce)
            .filter(GestorSQL.PlayOffsBronce.partidos_idPartidos == idPartido)
            .first()
            or session.query(GestorSQL.Ticket)
            .filter(GestorSQL.Ticket.partidos_idPartidos == idPartido)
            .first()
        )

        if not registro:
            print(f"No se encontró registro de calendario para el partido {idPartido}")
            return None

        coach1 = session.query(UsuarioAlias1).filter_by(idUsuarios=registro.coach1).first()
        coach2 = session.query(UsuarioAlias2).filter_by(idUsuarios=registro.coach2).first()

        if not coach1 or not coach2:
            print(f"No se encontraron usuarios asociados al partido {idPartido}")
            return None

        entrenadores["0"] = coach1.nombreAMostrar or coach1.nombre_bloodbowl
        entrenadores["1"] = coach2.nombreAMostrar or coach2.nombre_bloodbowl
        resultados["0"] = partido.resultado1
        resultados["1"] = partido.resultado2
        razas["0"] = coach1.raza
        razas["1"] = coach2.raza
        nombre_equipos["0"] = partido.nombreEquipo1
        nombre_equipos["1"] = partido.nombreEquipo2
        escudos["0"] = f"Logos/{partido.logo1.replace('.png','')}"
        escudos["1"] = f"Logos/{partido.logo2.replace('.png','')}"
        kos["0"] = partido.ko2
        kos["1"] = partido.ko1
        heridos["0"] = partido.lesiones1
        heridos["1"] = partido.lesiones2
        muertos["0"] = partido.muertes1
        muertos["1"] = partido.muertes2
        grupo["0"] = coach1.grupo
        lado["izquierdo"] = coach1.color
        lado["derecho"] = coach2.color

        # Ganador
        if partido.resultado1 > partido.resultado2:
            ganador = {"ruta": "./plantillas/Victoria_Izquierda.png", "x": 50, "y": 220}
        elif partido.resultado1 < partido.resultado2:
            ganador = {"ruta": "./plantillas/Victoria_Derecha.png", "x": 1400, "y": 220}
        else:
            ganador = {"ruta": "./plantillas/Empate.png", "x": 729, "y": 241}

        ruta_imagen = crear_imagen(
            "resultado", "",
            entrenadores=entrenadores,
            resultados=resultados,
            escudos=escudos,
            razas=razas,
            nombre_equipos=nombre_equipos,
            kos=kos,
            heridos=heridos,
            muertos=muertos,
            ganador=ganador,
            grupo=grupo,
            lado=lado,
        )

        return ruta_imagen

    except Exception as e:
        print(f"Ocurrió un error en imagenResultado: {str(e)}")
        return None
    finally:
        session.close()

