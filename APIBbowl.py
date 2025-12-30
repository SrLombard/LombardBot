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
    #competition_id = 'f24067ad-15df-11ee-8d38-020000a4d571' #Liga Andaluza de Lombard
    competition_id = '9bade735-da6f-11ee-a745-02000090a64f'
    return obtener_partidos(api_token, competition_id)

def obtener_partido_ButterCup(api_token):
    # competition_id = '41f8600b-eeaa-11ee-a745-02000090a64f'
    competition_id = '8d912ba4-e44e-11f0-a124-bc2411305479' #Butter Cup 6
    return obtener_partidos(api_token, competition_id)

def obtener_partido_PlayOfTicket(api_token):
    # competition_id = '41f8600b-eeaa-11ee-a745-02000090a64f'
    competition_id = '5f00f26f-65ab-11f0-a124-bc2411305479'
    return obtener_partidos(api_token, competition_id)

def obtener_partido_PlayOff(api_token):
    competition_id = 'ec5ad94d-cae3-11f0-a124-bc2411305479' #id del PLayoff
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

def obtener_partido_por_uuid(api_token, uuid):
    url = f"https://web.cyanide-studio.com/ws/bb3/match/?key={api_token}&uuid={uuid}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        # Combinar información del partido con información de entrenadores y equipos
        match = data.get('match', {})
        match['coaches_info'] = data.get('coaches', [])
        match['teams_info'] = data.get('teams', [])
        return match
    else:
        # Manejo de errores o devolver algo que indique que la solicitud falló
        return None

def buscarequipo(api_token, equipo_id):
    url = f"https://web.cyanide-studio.com/ws/bb3/team/?key={api_token}&id={equipo_id}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return {
            "team": data.get("team"),
            "coach": data.get("coach"),
            "roster": data.get("roster")
        }
    else:
        return None
