# Séance(s) Backend - API Horaires Cinéma

Serveur Python qui récupère les horaires des cinémas parisiens via les endpoints Allociné (JSON + HTML fallback), enrichis avec TMDB.

## Installation locale

### 1. Prérequis
- Python 3.8 ou supérieur
- pip (gestionnaire de paquets Python)

### 2. Installation
```bash
# Créer un environnement virtuel
python -m venv venv

# Activer l'environnement (macOS/Linux)
source venv/bin/activate

# Activer l'environnement (Windows)
venv\Scripts\activate

# Installer les dépendances
pip install -r requirements.txt
```

### 3. Lancer le serveur
```bash
python app.py
```

Le serveur démarre sur `http://localhost:5001`

## Endpoints disponibles

### `GET /`
Informations sur l'API

### `GET /cinemas`
Liste des cinémas disponibles

**Réponse:**
```json
{
  "cinemas": ["Le Champo", "Reflet Médicis", ...]
}
```

### `GET /showtimes?date=YYYY-MM-DD`
Horaires de tous les cinémas pour une date donnée (optionnel)

**Paramètres:**
- `date` (optionnel): Date au format YYYY-MM-DD (par défaut: aujourd'hui)

**Réponse:**
```json
{
  "date": "2026-01-17",
  "showtimes": {
    "Le Champo": [
      {
        "title": "Vertigo",
        "director": "Alfred Hitchcock",
        "duration": "2h08",
        "showtimes": [
          {"start": "20:15", "end": "22:38"}
        ]
      }
    ]
  }
}
```

## ⚠️ IMPORTANT - IDs des cinémas

Les IDs des cinémas dans `CINEMA_IDS` doivent rester à jour (Allociné peut changer ses IDs).
Le fichier `cinema_ids.json` contient une copie de référence.

## Déploiement gratuit

### Option 1 : Render.com
1. Crée un compte sur [render.com](https://render.com)
2. "New +" → "Web Service"
3. Connecte ton dépôt GitHub
4. Build Command: `pip install -r requirements.txt`
5. Start Command: `gunicorn app:app`

### Option 2 : Railway.app
1. Crée un compte sur [railway.app](https://railway.app)
2. "New Project" → "Deploy from GitHub repo"
3. Railway détecte automatiquement Python

### Option 3 : Vercel (avec Python)
1. Crée un compte sur [vercel.com](https://vercel.com)
2. Ajoute un fichier `vercel.json` :
```json
{
  "builds": [
    {
      "src": "app.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "app.py"
    }
  ]
}
```

## Prochaines étapes

1. **Tester localement** avec `python app.py`
2. **Trouver les vrais IDs** des cinémas via `/search-cinema`
3. **Déployer** sur Render/Railway/Vercel
4. **Connecter la PWA** à l'URL de ton serveur
