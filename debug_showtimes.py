import requests
from bs4 import BeautifulSoup
import re

cinema_id = 'C0073'  # Le Champo
url = f"https://www.allocine.fr/seance/salle_gen_csalle={cinema_id}.html"

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
}

response = requests.get(url, headers=headers, timeout=10)
soup = BeautifulSoup(response.content, 'html.parser')

# Trouver le premier film
movie_divs = soup.find_all('div', class_=lambda x: x and 'movie' in x.lower())

if movie_divs:
    first_movie = movie_divs[0]
    
    print("=" * 60)
    print("ANALYSE DU PREMIER FILM")
    print("=" * 60)
    
    # Titre
    title_link = first_movie.find('a', href=re.compile(r'/film/'))
    if title_link:
        print(f"\nTitre: {title_link.get_text(strip=True)}")
    
    # Chercher toutes les informations sur les horaires
    print("\n--- RECHERCHE DE DURÉE ---")
    
    # Chercher pattern durée
    duration_patterns = [
        r'(\d+h\s*\d+)',
        r'(\d+h\d+)',
        r'(\d+)h(\d+)',
    ]
    
    text = first_movie.get_text()
    print(f"\nTexte complet du bloc:\n{text[:500]}")
    
    for pattern in duration_patterns:
        matches = re.findall(pattern, text)
        if matches:
            print(f"\nPattern '{pattern}' trouvé: {matches}")
    
    # Chercher dans les attributs et classes
    print("\n--- STRUCTURE HTML ---")
    
    # Chercher tous les spans avec class contenant 'time' ou 'duration'
    time_spans = first_movie.find_all('span', class_=lambda x: x and ('time' in x.lower() or 'duration' in x.lower() or 'hour' in x.lower()))
    if time_spans:
        print("\nSpans avec 'time/duration/hour':")
        for span in time_spans:
            print(f"  - class={span.get('class')}: {span.get_text(strip=True)}")
    
    # Chercher tous les divs avec class contenant 'meta'
    meta_divs = first_movie.find_all('div', class_=lambda x: x and 'meta' in x.lower())
    if meta_divs:
        print("\nDivs avec 'meta':")
        for div in meta_divs:
            print(f"  - class={div.get('class')}: {div.get_text(strip=True)[:100]}")
    
    # Sauvegarder le HTML du premier film
    with open('first_movie_html.html', 'w', encoding='utf-8') as f:
        f.write(first_movie.prettify())
    
    print("\n✓ HTML du premier film sauvegardé dans 'first_movie_html.html'")
    print("Ouvre ce fichier pour voir la structure complète")

else:
    print("Aucun film trouvé")
