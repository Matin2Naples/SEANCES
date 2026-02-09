from flask import Flask, jsonify, request
from flask_cors import CORS
from allocineAPI.allocineAPI import allocineAPI
from datetime import datetime, timedelta
import logging

app = Flask(__name__)
CORS(app)  # Permet à ton app React d'appeler cette API

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# IDs des cinémas Allociné pour Paris
# Ces IDs doivent être trouvés en cherchant chaque cinéma dans l'API Allociné
CINEMA_IDS = {
    'Filmothèque du Quartier Latin': 'P0031',  # À vérifier
    'Le Champo': 'P0159',  # À vérifier
    'Reflet Médicis': 'P0160',  # À vérifier
    'Écoles Cinéma Club': 'P0050',  # À vérifier
    'Le Grand Action': 'P0051',  # À vérifier
    'Christine Cinéma Club': 'P0052',  # À vérifier
    'UGC Les Halles': 'C0159',  # À vérifier
    'La Cinémathèque': 'P0072',  # À vérifier
    'MK2 Quai de Seine': 'P2324',  # À vérifier
    'MK2 Quai de Loire': 'P2325',  # À vérifier
    'Le Louxor': 'P2087',  # À vérifier
}

api = allocineAPI()

@app.route('/')
def home():
    return jsonify({
        'message': 'API Séance(s) - Récupération des horaires de cinéma à Paris',
        'endpoints': {
            '/cinemas': 'Liste des cinémas disponibles',
            '/showtimes?date=YYYY-MM-DD': 'Horaires pour tous les cinémas (date optionnelle)',
            '/search-cinema?name=...': 'Rechercher un cinéma sur Allociné'
        }
    })

@app.route('/cinemas')
def get_cinemas():
    """Retourne la liste des cinémas disponibles"""
    return jsonify({
        'cinemas': list(CINEMA_IDS.keys())
    })

@app.route('/showtimes')
def get_showtimes():
    """
    Récupère les horaires pour tous les cinémas
    Paramètre optionnel: date (format YYYY-MM-DD)
    """
    date_param = request.args.get('date')
    
    # Si pas de date fournie, utiliser aujourd'hui
    if date_param:
        try:
            target_date = datetime.strptime(date_param, '%Y-%m-%d')
        except ValueError:
            return jsonify({'error': 'Format de date invalide. Utilisez YYYY-MM-DD'}), 400
    else:
        target_date = datetime.now()
    
    date_str = target_date.strftime('%Y-%m-%d')
    
    all_showtimes = {}
    
    for cinema_name, cinema_id in CINEMA_IDS.items():
        try:
            logger.info(f"Récupération des horaires pour {cinema_name} ({cinema_id})")
            showtimes = api.get_showtime(cinema_id, date_str)
            
            # Formatter les données pour correspondre à notre interface
            formatted_showtimes = []
            for movie in showtimes:
                # Combiner VF et VO
                all_times = []
                
                for time_str in movie.get('VF', []):
                    time_obj = datetime.fromisoformat(time_str)
                    duration = parse_duration(movie.get('duration', '0h 00min'))
                    end_time = time_obj + timedelta(minutes=duration)
                    all_times.append({
                        'start': time_obj.strftime('%H:%M'),
                        'end': end_time.strftime('%H:%M')
                    })
                
                for time_str in movie.get('VO', []):
                    time_obj = datetime.fromisoformat(time_str)
                    duration = parse_duration(movie.get('duration', '0h 00min'))
                    end_time = time_obj + timedelta(minutes=duration)
                    all_times.append({
                        'start': time_obj.strftime('%H:%M'),
                        'end': end_time.strftime('%H:%M')
                    })
                
                # Trier par heure de début
                all_times.sort(key=lambda x: x['start'])
                
                if all_times:  # N'ajouter que les films avec des horaires
                    formatted_showtimes.append({
                        'title': movie.get('title', 'Titre inconnu'),
                        'director': movie.get('director', 'Réalisateur inconnu'),
                        'duration': movie.get('duration', ''),
                        'showtimes': all_times
                    })
            
            all_showtimes[cinema_name] = formatted_showtimes
            
        except Exception as e:
            logger.error(f"Erreur pour {cinema_name}: {str(e)}")
            all_showtimes[cinema_name] = []
    
    return jsonify({
        'date': date_str,
        'showtimes': all_showtimes
    })

@app.route('/search-cinema')
def search_cinema():
    """
    Recherche un cinéma pour trouver son ID Allociné
    Paramètre: name (nom du cinéma)
    """
    cinema_name = request.args.get('name')
    
    if not cinema_name:
        return jsonify({'error': 'Paramètre "name" requis'}), 400
    
    try:
        # Rechercher dans Paris (on suppose que c'est ville-75056 ou similaire)
        # Cette partie nécessiterait d'explorer l'API pour trouver l'ID de Paris
        cinemas = api.get_cinema("ville-75056")  # ID à vérifier pour Paris
        
        # Filtrer les résultats
        results = [
            {'id': cinema['id'], 'name': cinema['name'], 'address': cinema.get('address', '')}
            for cinema in cinemas
            if cinema_name.lower() in cinema['name'].lower()
        ]
        
        return jsonify({
            'query': cinema_name,
            'results': results
        })
    
    except Exception as e:
        logger.error(f"Erreur de recherche: {str(e)}")
        return jsonify({'error': str(e)}), 500

def parse_duration(duration_str):
    """
    Parse une durée au format '1h 30min' et retourne le nombre total de minutes
    """
    minutes = 0
    parts = duration_str.split()
    
    for part in parts:
        if 'h' in part:
            minutes += int(part.replace('h', '')) * 60
        elif 'min' in part:
            minutes += int(part.replace('min', ''))
    
    return minutes

if __name__ == '__main__':
    # En développement
    app.run(debug=True, host='0.0.0.0', port=5000)
