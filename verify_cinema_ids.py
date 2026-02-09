from allocineAPI.allocineAPI import allocineAPI

api = allocineAPI()

# IDs proposés
proposed_cinemas = {
    'Filmothèque du Quartier Latin': 'C0020',
    'Reflet Médicis': 'C0074',
    'Le Champo': 'C0073',
    'Le Grand Action': 'C0072',
    'Écoles Cinéma Club': 'C0071',
    'Christine Cinéma Club': 'C0015',
    'La Cinémathèque Française': 'C1559',
    'UGC Ciné Cité Les Halles': 'C0159',
    'UGC Gobelins': 'C0150',
    'UGC Ciné Cité Bercy': 'C0026',
    'MK2 Quai de Seine': 'C0003',
    'MK2 Quai de Loire': 'C1621',
    'Le Louxor': 'W7510',
}

print("=" * 60)
print("VÉRIFICATION DES IDs DE CINÉMAS")
print("=" * 60)

# Récupérer tous les cinémas de Paris
paris_id = 'ville-115755'
all_cinemas = api.get_cinema(paris_id)

print(f"\nTotal cinémas à Paris: {len(all_cinemas)}\n")

# Chercher Le Grand Rex
print("Recherche de 'Le Grand Rex'...")
for cinema in all_cinemas:
    if 'grand rex' in cinema.get('name', '').lower():
        print(f"✓ Trouvé: {cinema.get('name')} - ID: {cinema.get('id')}")

print("\n" + "=" * 60)
print("VÉRIFICATION DES IDs PROPOSÉS:")
print("=" * 60)

# Créer un dictionnaire des cinémas par ID
cinema_by_id = {c.get('id'): c.get('name') for c in all_cinemas}

for name, cinema_id in proposed_cinemas.items():
    if cinema_id in cinema_by_id:
        actual_name = cinema_by_id[cinema_id]
        print(f"\n✓ {name}")
        print(f"  ID: {cinema_id}")
        print(f"  Nom Allociné: {actual_name}")
    else:
        print(f"\n❌ {name}")
        print(f"  ID {cinema_id} non trouvé!")

print("\n" + "=" * 60)
print("CODE FINAL À UTILISER:")
print("=" * 60)
print("\nCINEMA_IDS = {")
for name, cinema_id in proposed_cinemas.items():
    print(f"    '{name}': '{cinema_id}',")
print("    'Le Grand Rex': 'XXXXX',  # À compléter")
print("}")
