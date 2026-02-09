import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta

cinema_id = 'C0073'  # Le Champo
url = f"https://www.allocine.fr/seance/salle_gen_csalle={cinema_id}.html"

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
}

try:
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.content, 'html.parser')
    
    movies = []
    
    # Chercher les divs avec 'movie' dans la classe
    movie_divs = soup.find_all('div', class_=lambda x: x and 'movie' in x.lower())
    
    print(f"Trouvé {len(movie_divs)} films")
    print("=" * 60)
    
    for movie_div in movie_divs:
        try:
            # Titre du film
            title = "Titre inconnu"
            title_link = movie_div.find('a', href=re.compile(r'/film/'))
            if title_link:
                title = title_link.get_text(strip=True)
            
            # Réalisateur - chercher dans les métadonnées
            director = "Réalisateur inconnu"
            meta_body = movie_div.find('div', class_=lambda x: x and 'meta-body' in x.lower())
            if meta_body:
                # Chercher "De XXX"
                text = meta_body.get_text()
                director_match = re.search(r'De\s+(.+?)(?:\s*\||$)', text)
                if director_match:
                    director = director_match.group(1).strip()
            
            # Durée
            duration = ""
            duration_match = re.search(r'(\d+h\s*\d+min?)', movie_div.get_text())
            if duration_match:
                duration = duration_match.group(1)
            
            # Horaires - chercher tous les patterns de temps
            showtimes = []
            time_pattern = re.compile(r'\b(\d{1,2}):(\d{2})\b')
            
            # Chercher dans tout le texte du div
            for match in time_pattern.finditer(movie_div.get_text()):
                hour = int(match.group(1))
                minute = int(match.group(2))
                
                # Vérifier que c'est un horaire valide
                if 0 <= hour <= 23 and 0 <= minute <= 59:
                    start_time = f"{hour:02d}:{minute:02d}"
                    
                    # Calculer heure de fin (durée par défaut 2h)
                    duration_minutes = 120
                    if duration:
                        hours_match = re.search(r'(\d+)h', duration)
                        mins_match = re.search(r'(\d+)min?', duration)
                        duration_minutes = 0
                        if hours_match:
                            duration_minutes += int(hours_match.group(1)) * 60
                        if mins_match:
                            duration_minutes += int(mins_match.group(1))
                    
                    start_dt = datetime.strptime(start_time, '%H:%M')
                    end_dt = start_dt + timedelta(minutes=duration_minutes)
                    end_time = end_dt.strftime('%H:%M')
                    
                    showtimes.append({
                        'start': start_time,
                        'end': end_time
                    })
            
            # Dédupliquer les horaires
            seen = set()
            unique_showtimes = []
            for st in showtimes:
                key = st['start']
                if key not in seen:
                    seen.add(key)
                    unique_showtimes.append(st)
            
            if unique_showtimes:
                movie_data = {
                    'title': title,
                    'director': director,
                    'duration': duration,
                    'showtimes': sorted(unique_showtimes, key=lambda x: x['start'])
                }
                movies.append(movie_data)
                
                print(f"\n✓ {title}")
                print(f"  Réalisateur: {director}")
                print(f"  Durée: {duration}")
                print(f"  Horaires: {[st['start'] for st in unique_showtimes]}")
        
        except Exception as e:
            print(f"Erreur parsing: {e}")
            continue
    
    print("\n" + "=" * 60)
    print(f"TOTAL: {len(movies)} films avec horaires")
    print("=" * 60)
    
    # Afficher en JSON
    import json
    print("\nJSON:")
    print(json.dumps(movies, indent=2, ensure_ascii=False))
    
except Exception as e:
    print(f"❌ Erreur: {e}")
    import traceback
    traceback.print_exc()
