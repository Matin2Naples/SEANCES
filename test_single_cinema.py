from allocineAPI.allocineAPI import allocineAPI
from datetime import datetime

api = allocineAPI()

cinema_id = 'C0073'
today = datetime.now().strftime('%Y-%m-%d')

print(f"Test pour Le Champo (ID: {cinema_id})")
print(f"Date: {today}")
print("=" * 60)

try:
    showtimes = api.get_showtime(cinema_id, today)
    print(f"Résultat: {len(showtimes)} films trouvés\n")
    
    for movie in showtimes:
        print(f"Titre: {movie.get('title', 'N/A')}")
        print(f"Durée: {movie.get('duration', 'N/A')}")
        print(f"VF: {movie.get('VF', [])}")
        print(f"VO: {movie.get('VO', [])}")
        print("-" * 60)
        
except Exception as e:
    print(f"Erreur: {e}")
    import traceback
    traceback.print_exc()
