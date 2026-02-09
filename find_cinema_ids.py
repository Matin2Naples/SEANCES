from allocineAPI.allocineAPI import allocineAPI
import json

api = allocineAPI()

print("=" * 60)
print("EXPLORATION DE L'API ALLOCINE")
print("=" * 60)

# 1. Trouver l'ID de Paris
print("\n1. Recherche de Paris...")
try:
    villes = api.get_top_villes()
    print(f"Nombre de villes trouvées: {len(villes)}")
    
    # Chercher Paris
    paris_id = None
    for ville in villes:
        if 'Paris' in ville.get('name', ''):
            print(f"✓ Paris trouvé: {ville}")
            paris_id = ville.get('id')
            break
    
    if paris_id:
        print(f"\n2. Récupération des cinémas pour {paris_id}...")
        cinemas = api.get_cinema(paris_id)
        print(f"✓ {len(cinemas)} cinémas trouvés à Paris !")
        
        # Chercher nos cinémas cibles
        target_cinemas = {
            'Champo': 'Le Champo',
            'Filmothèque': 'Filmothèque du Quartier Latin',
            'Reflet': 'Reflet Médicis',
            'Christine': 'Christine Cinéma Club',
            'Grand Action': 'Le Grand Action',
            'Louxor': 'Le Louxor',
            'MK2 Quai de Seine': 'MK2 Quai de Seine',
            'MK2 Quai de Loire': 'MK2 Quai de Loire',
            'Cinémathèque': 'La Cinémathèque',
            'UGC Les Halles': 'UGC Les Halles',
            'Écoles': 'Écoles Cinéma Club'
        }
        
        print("\n" + "=" * 60)
        print("CINÉMAS TROUVÉS:")
        print("=" * 60)
        
        found_cinemas = {}
        
        for cinema in cinemas:
            name = cinema.get('name', '')
            cinema_id = cinema.get('id', '')
            address = cinema.get('address', '')
            
            # Vérifier si c'est un de nos cinémas cibles
            for keyword, full_name in target_cinemas.items():
                if keyword.lower() in name.lower():
                    print(f"\n✓ {name}")
                    print(f"  ID: {cinema_id}")
                    print(f"  Adresse: {address}")
                    found_cinemas[full_name] = cinema_id
                    break
        
        # Afficher le code Python à copier
        print("\n" + "=" * 60)
        print("CODE À COPIER DANS app.py:")
        print("=" * 60)
        print("\nCINEMA_IDS = {")
        for name, cinema_id in sorted(found_cinemas.items()):
            print(f"    '{name}': '{cinema_id}',")
        print("}")
        
        # Sauvegarder dans un fichier JSON
        with open('cinema_ids.json', 'w', encoding='utf-8') as f:
            json.dump(found_cinemas, f, indent=2, ensure_ascii=False)
        
        print("\n✓ IDs sauvegardés dans cinema_ids.json")
        
        # Afficher quelques autres cinémas intéressants
        print("\n" + "=" * 60)
        print("AUTRES CINÉMAS PARISIENS (premiers 10):")
        print("=" * 60)
        for i, cinema in enumerate(cinemas[:10]):
            print(f"{i+1}. {cinema.get('name', 'N/A')} (ID: {cinema.get('id', 'N/A')})")
        
    else:
        print("❌ Paris non trouvé")
        
except Exception as e:
    print(f"❌ Erreur: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("RECHERCHE TERMINÉE")
print("=" * 60)