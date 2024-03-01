import json
import os
from PIL import Image, ImageDraw, ImageFont
import random

def cargar_configuracion(nombre_plantilla):
    with open('configuracion.json', 'r') as archivo_json:
        configuracion = json.load(archivo_json)
        return configuracion.get(nombre_plantilla)

def recalcular_x(draw, texto, fuente, x_inicial, y, alineacion, imagen_ancho):
    if alineacion == "centrado":
        # Obtiene el cuadro delimitador del texto
        bbox = draw.textbbox((0, 0), texto, font=fuente)
        # Calcula el ancho del texto
        texto_ancho = bbox[2] - bbox[0]
        # Recalcula x para centrar el texto
        x_nuevo = x_inicial - (texto_ancho / 2)
        return x_nuevo
    return x_inicial

def crear_imagen(nombre_plantilla, **datos):
    configuracion = cargar_configuracion(nombre_plantilla)
    if configuracion is None:
        print("Plantilla no encontrada.")
        return None

    ruta_plantilla = f"./plantillas/{nombre_plantilla}.png"
    imagen = Image.open(ruta_plantilla)
    draw = ImageDraw.Draw(imagen)
    imagen_ancho = imagen.width

    for elemento in configuracion:
        nombre_diccionario = elemento['nombre_diccionario']
        clave = elemento['clave']
        x = elemento['posicion_x']
        y = elemento['posicion_y']
        alineacion = elemento['alineacion']
        fuente = ImageFont.truetype(f"./fonts/{elemento['fuente']}", elemento['size'])
        
        # Acceder al diccionario correspondiente basado en nombre_diccionario
        diccionario_datos = datos.get(nombre_diccionario, {})
        texto = diccionario_datos.get(clave, "")

        # Recalcular X si es necesario
        x = recalcular_x(draw, texto, fuente, x, y, alineacion, imagen_ancho)
        
        draw.text((x, y), texto, font=fuente)

    numero_aleatorio = random.randint(100000, 999999)
    ruta_imagen_final = f"./temp/imagenes/{nombre_plantilla}_{numero_aleatorio}.png"
    imagen.save(ruta_imagen_final)

    imagen.close()

    return ruta_imagen_final

def eliminar_imagen(ruta_imagen):
    try:
        os.remove(ruta_imagen)
        print(f"Imagen {ruta_imagen} eliminada correctamente.")
    except Exception as e:
        print(f"Error al eliminar la imagen {ruta_imagen}: {e}")
