import requests
from bs4 import BeautifulSoup

cinema_id = 'C0073'  # Le Champo
url = f"https://www.allocine.fr/seance/salle_gen_csalle={cinema_id}.html"

print(f"URL: {url}")
print("=" * 60)

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
}

try:
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    
    print(f"Status: {response.status_code}")
    print(f"Content length: {len(response.content)}")
    print("=" * 60)
    
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Sauvegarder le HTML pour inspection
    with open('allocine_page.html', 'w', encoding='utf-8') as f:
        f.write(soup.prettify())
    
    print("✓ HTML sauvegardé dans allocine_page.html")
    
    # Chercher différentes structures possibles
    print("\n1. Recherche de 'card'...")
    cards = soup.find_all('div', class_=lambda x: x and 'card' in x)
    print(f"   Trouvé {len(cards)} éléments avec 'card'")
    
    print("\n2. Recherche de 'movie'...")
    movies = soup.find_all('div', class_=lambda x: x and 'movie' in x)
    print(f"   Trouvé {len(movies)} éléments avec 'movie'")
    
    print("\n3. Recherche de 'entity'...")
    entities = soup.find_all('div', class_=lambda x: x and 'entity' in x)
    print(f"   Trouvé {len(entities)} éléments avec 'entity'")
    
    print("\n4. Recherche de 'seance' ou 'showtime'...")
    seances = soup.find_all('div', class_=lambda x: x and ('seance' in x.lower() if x else False))
    print(f"   Trouvé {len(seances)} éléments avec 'seance'")
    
    print("\n5. Recherche de liens de films...")
    film_links = soup.find_all('a', href=lambda x: x and '/film/' in x if x else False)
    print(f"   Trouvé {len(film_links)} liens vers des films")
    if film_links:
        print("   Exemples:")
        for link in film_links[:3]:
            print(f"   - {link.get_text(strip=True)}: {link.get('href')}")
    
    print("\n6. Recherche d'horaires (format HH:MM)...")
    import re
    time_pattern = re.compile(r'\b\d{1,2}[h:]\d{2}\b')
    times = soup.find_all(string=time_pattern)
    print(f"   Trouvé {len(times)} horaires potentiels")
    if times:
        print("   Exemples:")
        for time in times[:5]:
            print(f"   - {time.strip()}")
    
    print("\n7. Structure générale de la page:")
    # Trouver les principaux containers
    main_containers = soup.find_all(['div', 'section'], class_=True, limit=10)
    for i, container in enumerate(main_containers[:5]):
        classes = ' '.join(container.get('class', []))
        print(f"   Container {i+1}: {container.name} class='{classes}'")
    
    print("\n" + "=" * 60)
    print("Ouvre allocine_page.html dans un navigateur pour voir la structure")
    
except Exception as e:
    print(f"❌ Erreur: {e}")
    import traceback
    traceback.print_exc()
