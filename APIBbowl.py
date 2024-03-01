import requests


def obtener_partidos(api_token, competition_id):
    url = f"https://web.cyanide-studio.com/ws/bb3/matches/?key={api_token}&competition_id={competition_id}&sort=LastMatchDate"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()['matches']
    else:
        # Manejo de errores o devolver algo que indique que la solicitud falló
        return None


def obtener_partido_lombarda(api_token):
    competition_id = 'f24067ad-15df-11ee-8d38-020000a4d571' #Liga Andaluza de Lombard
    return obtener_partidos(api_token, competition_id)

def obtener_partido_fantasbulosoLadder(api_token):
    competition_id = '5d198cbc-9996-11ee-a745-02000090a64f' #id del fantasbuloso ladder
    return obtener_partidos(api_token, competition_id)

def obtener_entrenadores(api_token, coach_name):
    # Llamada a la API de Blood Bowl
    url = f"https://web.cyanide-studio.com/ws/bb3/lookup/?key={api_token}&coach_name={coach_name}"
    response = requests.get(url)
    if response.status_code == 200:
        coaches = response.json().get('coaches', [])
        if coaches:  
            return coaches[0]  # Devuelve el primer entrenador si existe
        else:
            return ''    
    else:
        # Manejo de errores o devolver algo que indique que la solicitud falló
        return None





