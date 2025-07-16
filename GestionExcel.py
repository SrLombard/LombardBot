import gspread
from oauth2client.service_account import ServiceAccountCredentials
import asyncio

# Define el alcance y carga las credenciales
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("buttercup.json", scope)
client = gspread.authorize(creds)
sheetIds = None
sheetPartidosJugados = None
sheetJornadas = None
sheetCalendarioResultados = None
sheetLesiones = None

#hacer esto un singleton y no variables globales raras
async def ActualizarExcels():
    global sheetIds
    global sheetPartidosJugados
    global sheetJornadas
    global sheetCalendarioResultados
    global sheetLesiones


    # Abre la hoja de cálculo
    spreadsheet = client.open_by_key("16hh4SSjf7o1z_gpWj-GDYPCTg8WOvNIBywAQa_auD98")
    # Ahora selecciona la hoja específica por su nombre
    sheetCalendarioResultados = spreadsheet.worksheet("Calendario y Resultados")
    sheetLesiones = spreadsheet.worksheet("Lesiones")


    # Abre la hoja de cálculo
    spreadsheet = client.open_by_key("1smAg7UeXODaRvNOGFjcqRRFyld9e0S7alxYECi4WXAA")
    # Ahora selecciona la hoja específica por su nombre
    sheetIds = spreadsheet.worksheet("idsBbowl")
    sheetPartidosJugados = spreadsheet.worksheet("Partidos_jugados")
    sheetJornadas = spreadsheet.worksheet("Jornadas")

    
async def actualizar_hoja_lesiones(coach_name, jornada, total_lesiones, total_muertes,sheetLesiones):
    # Obtener todos los registros de la hoja para encontrar la fila del coach
    lesiones_valores = sheetLesiones.get_all_records()  
    # Encontrar la fila correspondiente al coach. Asumimos que cada coach tiene dos filas: una para lesiones y otra para muertes
    fila_lesion = None
    fila_muerte = None
    for index, row in enumerate(lesiones_valores, start=2):  # Asumiendo que la primera fila es el encabezado y los datos empiezan en la fila 2
        if row["Jugador"] == coach_name:           
                fila_lesion = index
                fila_muerte = index + 1  # Asumimos que la fila de muertes está justo después de la de lesiones

    # Actualizar la hoja con los totales de lesiones y muertes
    if fila_lesion and fila_muerte:
        # Calcular la columna correcta basada en la jornada. Asumiendo que cada jornada se mueve una columna a la derecha
        columna_lesion = 2 + jornada
        columna_muerte =2 + jornada

        # Actualizar celdas con el total de lesiones y muertes
        sheetLesiones.update_cell(fila_lesion, columna_lesion, total_lesiones)
        sheetLesiones.update_cell(fila_muerte, columna_muerte, total_muertes)
    else:
        print(f"No se encontró el coach {coach_name} en la hoja de Lesiones.")
    
    await asyncio.sleep(10)
    
async def actualizaExcel(nombre_hoja):
    global sheetIds, sheetPartidosJugados, sheetJornadas, sheetCalendarioResultados, sheetLesiones

    # Define aquí el mapeo de los nombres de las hojas a las claves de las hojas de cálculo
    hojas_a_spreadsheet_keys = {
        "Calendario y Resultados": "16hh4SSjf7o1z_gpWj-GDYPCTg8WOvNIBywAQa_auD98",
        "Lesiones": "16hh4SSjf7o1z_gpWj-GDYPCTg8WOvNIBywAQa_auD98",
        "idsBbowl": "1smAg7UeXODaRvNOGFjcqRRFyld9e0S7alxYECi4WXAA",
        "Partidos_jugados": "1smAg7UeXODaRvNOGFjcqRRFyld9e0S7alxYECi4WXAA",
        "Jornadas": "1smAg7UeXODaRvNOGFjcqRRFyld9e0S7alxYECi4WXAA"
    }

    if nombre_hoja in hojas_a_spreadsheet_keys:
        # Abre la hoja de cálculo correspondiente
        spreadsheet_key = hojas_a_spreadsheet_keys[nombre_hoja]
        spreadsheet = client.open_by_key(spreadsheet_key)
        # Selecciona la hoja específica por su nombre
        hoja_actualizada = spreadsheet.worksheet(nombre_hoja)

        # Actualiza la variable global correspondiente
        if nombre_hoja == "Calendario y Resultados":
            global sheetCalendarioResultados
            sheetCalendarioResultados = hoja_actualizada
        elif nombre_hoja == "Lesiones":
            global sheetLesiones
            sheetLesiones = hoja_actualizada
        elif nombre_hoja == "idsBbowl":
            global sheetIds
            sheetIds = hoja_actualizada
        elif nombre_hoja == "Partidos_jugados":
            global sheetPartidosJugados
            sheetPartidosJugados = hoja_actualizada
        elif nombre_hoja == "Jornadas":
            global sheetJornadas
            sheetJornadas = hoja_actualizada
        else:
            print(f"Nombre de hoja '{nombre_hoja}' no reconocido.")
    else:
        print(f"No se encontró el nombre de la hoja '{nombre_hoja}' en la configuración.")





