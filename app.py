from flask import Flask, jsonify, request
import requests
from flask_cors import CORS
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import logging
import os
import re
import sqlite3
import unicodedata
from difflib import SequenceMatcher
from functools import lru_cache
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Clé API TMDB
TMDB_API_KEY = os.getenv('TMDB_API_KEY', '8d8890d0c3bb35e59b72e11b119e951f')
TMDB_BASE_URL = 'https://api.themoviedb.org/3'
LETTERBOXD_BASE_URL = 'https://letterboxd.com'
ENABLE_LIVE_LETTERBOXD = os.getenv('ENABLE_LIVE_LETTERBOXD', '0') in ('1', 'true', 'True')
PREFETCH_TOKEN = os.getenv('PREFETCH_TOKEN', '')
DB_PATH = os.path.join(os.path.dirname(__file__), 'seances_cache.db')

# IDs des cinémas Allociné pour Paris (ordre préféré)
CINEMA_IDS = {
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
    'Le Grand Rex': 'C0065',
    'Le Louxor': 'W7510',
}

SESSION = requests.Session()
SESSION_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
}

# Simple in-memory cache for daily showtimes
SHOWTIMES_CACHE = {}
SHOWTIMES_TTL_SECONDS = 15 * 60  # 15 minutes
LETTERBOXD_CACHE = {}
LETTERBOXD_TTL_SECONDS = 24 * 60 * 60  # 24 hours
LETTERBOXD_BLOCKED_UNTIL = 0
LETTERBOXD_403_LOGGED = False

def _db_connect():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_cache_db():
    conn = _db_connect()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS letterboxd_ratings (
                tmdb_id INTEGER PRIMARY KEY,
                rating REAL,
                letterboxd_url TEXT,
                updated_at INTEGER NOT NULL
            )
        """)
        conn.commit()
    finally:
        conn.close()

def get_cached_letterboxd(tmdb_id, max_age_seconds=LETTERBOXD_TTL_SECONDS):
    if not tmdb_id:
        return None, None
    conn = _db_connect()
    try:
        row = conn.execute(
            "SELECT rating, letterboxd_url, updated_at FROM letterboxd_ratings WHERE tmdb_id = ?",
            (tmdb_id,)
        ).fetchone()
        if not row:
            return None, None
        rating, url, updated_at = row
        if time.time() - (updated_at or 0) > max_age_seconds:
            return None, url
        return rating, url
    finally:
        conn.close()

def save_cached_letterboxd(tmdb_id, rating, letterboxd_url):
    if not tmdb_id:
        return
    conn = _db_connect()
    try:
        conn.execute(
            """
            INSERT INTO letterboxd_ratings (tmdb_id, rating, letterboxd_url, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(tmdb_id) DO UPDATE SET
                rating = excluded.rating,
                letterboxd_url = excluded.letterboxd_url,
                updated_at = excluded.updated_at
            """,
            (tmdb_id, rating, letterboxd_url, int(time.time()))
        )
        conn.commit()
    finally:
        conn.close()

init_cache_db()

def normalize_key(value):
    value = value or ""
    value = unicodedata.normalize("NFD", value)
    value = "".join(ch for ch in value if unicodedata.category(ch) != "Mn")
    value = value.lower()
    value = re.sub(r"\s*\(.*?\)\s*", " ", value)
    value = re.sub(r"[^a-z0-9\s-]", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value

def token_overlap_ratio(query_key, cand_key):
    q_tokens = [t for t in query_key.split(" ") if t]
    c_tokens = [t for t in cand_key.split(" ") if t]
    if not q_tokens or not c_tokens:
        return 0.0
    q_set = set(q_tokens)
    c_set = set(c_tokens)
    return len(q_set & c_set) / max(1, len(q_set))

def pick_best_tmdb_match(results, clean_title, year_hint=None):
    clean_key = normalize_key(clean_title)
    best = None
    best_score = 0.0
    for cand in results:
        cand_title = cand.get('title') or ''
        cand_original = cand.get('original_title') or ''
        cand_key = normalize_key(cand_title)
        cand_orig_key = normalize_key(cand_original)
        # Hard reject overly short candidates when query has multiple words
        if len(clean_key.split()) >= 2:
            if len(cand_key) < max(4, int(len(clean_key) * 0.6)) and len(cand_orig_key) < max(4, int(len(clean_key) * 0.6)):
                continue
            overlap = max(
                token_overlap_ratio(clean_key, cand_key),
                token_overlap_ratio(clean_key, cand_orig_key),
            )
            if overlap < 0.6:
                continue
        if cand_key == clean_key or cand_orig_key == clean_key:
            score = 1.0
        else:
            score = max(
                SequenceMatcher(None, clean_key, cand_key).ratio(),
                SequenceMatcher(None, clean_key, cand_orig_key).ratio(),
            )
        # Boost if year matches (±1)
        if year_hint:
            try:
                y = int(year_hint)
                ry = (cand.get('release_date') or '')[:4]
                if ry.isdigit() and abs(int(ry) - y) <= 1:
                    score += 0.15
            except Exception:
                pass
        if score > best_score:
            best_score = score
            best = cand
    if not best or best_score < 0.70:
        return None
    return best

def normalize_title(title):
    """Nettoyer un titre pour augmenter les chances de match TMDB."""
    clean_title = title.split(':')[0].strip()
    clean_title = re.sub(r'\s*\(.*?\)\s*', ' ', clean_title)
    clean_title = re.sub(r'\s*-\s*.*$', '', clean_title)
    clean_title = re.sub(r'\s+', ' ', clean_title).strip()
    return clean_title

def fetch_letterboxd_rating_by_tmdb_id(tmdb_id, force_refresh=False):
    """Récupère la note Letterboxd via l'ID TMDB."""
    global LETTERBOXD_BLOCKED_UNTIL, LETTERBOXD_403_LOGGED
    if not tmdb_id:
        return None, None

    if not force_refresh:
        db_rating, db_url = get_cached_letterboxd(tmdb_id)
        if db_rating is not None or db_url:
            return db_rating, db_url

    # If Letterboxd is currently blocking requests, skip fetch attempts.
    if time.time() < LETTERBOXD_BLOCKED_UNTIL:
        return None, f"{LETTERBOXD_BASE_URL}/tmdb/{tmdb_id}"

    now = time.time()
    cached = LETTERBOXD_CACHE.get(tmdb_id)
    if cached and not force_refresh:
        cached_at, cached_value = cached
        if now - cached_at < LETTERBOXD_TTL_SECONDS:
            return cached_value

    url = f"{LETTERBOXD_BASE_URL}/tmdb/{tmdb_id}"
    try:
        headers = {
            **SESSION_HEADERS,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://letterboxd.com/',
        }
        response = SESSION.get(url, headers=headers, timeout=6, allow_redirects=True)
        response.raise_for_status()
        final_url = response.url or url
        html = response.text

        rating = None
        soup = BeautifulSoup(html, 'html.parser')

        # 1) JSON-LD
        for script in soup.find_all('script', {'type': 'application/ld+json'}):
            text = script.string or script.get_text() or ""
            if not text:
                continue
            m = re.search(r'"ratingValue"\s*:\s*"?(?P<v>\d(?:\.\d)?)"?', text)
            if m:
                rating = float(m.group('v'))
                break

        # 2) fallback regex patterns
        if rating is None:
            patterns = [
                r'data-average-rating="(?P<v>\d(?:\.\d)?)"',
                r'"averageRating"\s*:\s*"?(?P<v>\d(?:\.\d)?)"?',
                r'average-rating[^>]*>\s*(?P<v>\d(?:\.\d)?)\s*<',
            ]
            for pattern in patterns:
                m = re.search(pattern, html)
                if m:
                    rating = float(m.group('v'))
                    break

        # Clamp to Letterboxd scale
        if rating is not None:
            rating = max(0.0, min(5.0, round(rating, 1)))

        result = (rating, final_url)
        save_cached_letterboxd(tmdb_id, rating, final_url)
        LETTERBOXD_CACHE[tmdb_id] = (now, result)
        return result
    except requests.HTTPError as e:
        status = e.response.status_code if e.response is not None else None
        if status == 403:
            LETTERBOXD_BLOCKED_UNTIL = time.time() + (6 * 60 * 60)  # cooldown 6h
            if not LETTERBOXD_403_LOGGED:
                logger.warning("Letterboxd bloque les requêtes (403). Fallback TMDB activé pendant 6h.")
                LETTERBOXD_403_LOGGED = True
        else:
            logger.warning(f"Erreur Letterboxd pour TMDB {tmdb_id}: {e}")
        result = (None, url)
        LETTERBOXD_CACHE[tmdb_id] = (now, result)
        return result
    except Exception as e:
        logger.warning(f"Erreur Letterboxd pour TMDB {tmdb_id}: {e}")
        result = (None, url)
        LETTERBOXD_CACHE[tmdb_id] = (now, result)
        return result

@lru_cache(maxsize=512)
def search_movie_tmdb(title, year_hint=None):
    """Recherche un film sur TMDB et retourne ses infos"""
    try:
        if not TMDB_API_KEY:
            logger.warning("TMDB_API_KEY manquante, enrichissement désactivé.")
            return None
        # Nettoyer le titre (enlever les sous-titres)
        clean_title = normalize_title(title)
        
        search_url = f"{TMDB_BASE_URL}/search/movie"
        params = {
            'api_key': TMDB_API_KEY,
            'query': clean_title,
            'language': 'fr-FR'
        }
        
        response = SESSION.get(search_url, params=params, timeout=6, headers=SESSION_HEADERS)
        response.raise_for_status()
        data = response.json()
        
        if data.get('results') and len(data['results']) > 0:
            # Choisir le meilleur résultat (éviter les mauvais matchs)
            candidates = data['results']
            movie = pick_best_tmdb_match(candidates, clean_title, year_hint)
            if not movie:
                return None

            # Récupérer les détails complets du film
            movie_id = movie['id']
            details_url = f"{TMDB_BASE_URL}/movie/{movie_id}"
            details_params = {
                'api_key': TMDB_API_KEY,
                'language': 'fr-FR',
                'append_to_response': 'credits,images',
                            }
            
            details_response = SESSION.get(details_url, params=details_params, timeout=6, headers=SESSION_HEADERS)
            details_response.raise_for_status()
            details = details_response.json()
            
            # Extraire les infos
            runtime = details.get('runtime', 0) or 0
            duration = f"{runtime // 60}h{runtime % 60:02d}" if runtime > 0 else "Durée inconnue"
            
            # Réalisateur
            director = "Réalisateur inconnu"
            if 'credits' in details and 'crew' in details['credits']:
                for person in details['credits']['crew']:
                    if person.get('job') == 'Director':
                        director = person.get('name', 'Réalisateur inconnu')
                        break
            
            # Acteurs principaux (top 3)
            actors = []
            if 'credits' in details and 'cast' in details['credits']:
                actors = [actor['name'] for actor in details['credits']['cast'][:5]]
            
            # Affiche (préférer la langue originale, puis le français)
            poster_path = None
            posters = details.get('images', {}).get('posters', []) if isinstance(details, dict) else []
            original_lang = details.get('original_language') if isinstance(details, dict) else None
            preferred = []
            if original_lang:
                preferred.extend([p for p in posters if p.get('iso_639_1') == original_lang])
            preferred.extend([p for p in posters if p.get('iso_639_1') == 'fr'])
            preferred.extend([p for p in posters if p.get('iso_639_1') == 'en'])
            # Last resort: no-language posters
            preferred.extend([p for p in posters if p.get('iso_639_1') is None and p.get('width', 0) >= 300 and p.get('height', 0) >= 450])
            if preferred:
                poster_path = preferred[0].get('file_path')
            if not poster_path:
                poster_path = details.get('poster_path')
            poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else None
            
            # Genres (maximum 2)
            genres = []
            if 'genres' in details:
                genres = [genre['name'] for genre in details['genres'][:2]]

            letterboxd_rating, letterboxd_url = get_cached_letterboxd(movie_id)
            if ENABLE_LIVE_LETTERBOXD and letterboxd_rating is None:
                letterboxd_rating, letterboxd_url = fetch_letterboxd_rating_by_tmdb_id(movie_id)
            if not letterboxd_url:
                letterboxd_url = f"{LETTERBOXD_BASE_URL}/tmdb/{movie_id}"
            
            return {
                'tmdb_id': movie_id,
                'duration': duration,
                'duration_minutes': runtime,
                'director': director,
                'actors': actors,
                'poster_url': poster_url,
                'release_date': details.get('release_date', ''),
                'overview': details.get('overview', ''),
                'vote_average': details.get('vote_average', 0),
                'letterboxd_rating': letterboxd_rating,
                'letterboxd_url': letterboxd_url,
                'genres': genres
            }
        
        return None
        
    except Exception as e:
        logger.error(f"Erreur TMDB pour '{title}': {e}")
        return None

def fetch_allocine_showtimes_json(cinema_id, date_str):
    """Récupère les horaires depuis l'endpoint JSON d'Allociné."""
    try:
        page = 1
        total_pages = 1
        movies_map = {}
        while page <= total_pages:
            url = f"https://www.allocine.fr/_/showtimes/theater-{cinema_id}/d-{date_str}/p-{page}"
            response = SESSION.get(url, headers=SESSION_HEADERS, timeout=10)
            response.raise_for_status()
            data = response.json()

            pagination = data.get('pagination', {})
            total_pages = int(pagination.get('totalPages', total_pages))

            for element in data.get('results', []):
                title = element.get('movie', {}).get('title', 'Titre inconnu')
                showtimes = []
                for showtimes_key in element.get('showtimes', {}).keys():
                    for showtime in element.get('showtimes', {}).get(showtimes_key, []):
                        starts_at = showtime.get('startsAt')
                        if starts_at:
                            showtimes.append(starts_at)

                if showtimes:
                    movies_map.setdefault(title, set()).update(showtimes)

            page += 1

        movies = []
        for title, starts_at_set in movies_map.items():
            start_times = []
            for starts_at in starts_at_set:
                try:
                    start_dt = datetime.fromisoformat(starts_at)
                    start_times.append(start_dt.strftime('%H:%M'))
                except Exception:
                    continue

            if start_times:
                movies.append({
                    'title': title,
                    'start_times': sorted(set(start_times))
                })

        return movies
    except Exception as e:
        logger.warning(f"Endpoint JSON Allociné indisponible pour {cinema_id}: {e}")
        return None

def fetch_allocine_showtimes_html(cinema_id):
    """Scrape les horaires depuis l'HTML Allociné (fallback)."""
    try:
        url = f"https://www.allocine.fr/seance/salle_gen_csalle={cinema_id}.html"
        
        response = SESSION.get(url, headers=SESSION_HEADERS, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        movies = []
        movie_divs = soup.select('div.movie-card-theater')
        
        for movie_div in movie_divs:
            try:
                # Titre
                title = "Titre inconnu"
                title_link = movie_div.select_one('h2.meta-title a, a.meta-title-link')
                if title_link:
                    title = title_link.get_text(strip=True)
                
                # Horaires
                showtimes = []
                time_spans = movie_div.select('.showtimes-hour-item-value')
                time_pattern = re.compile(r'\b(\d{1,2})[:h](\d{2})\b')

                for span in time_spans:
                    text = span.get_text(strip=True)
                    match = time_pattern.search(text)
                    if match:
                        hour = int(match.group(1))
                        minute = int(match.group(2))
                        if 0 <= hour <= 23 and 0 <= minute <= 59:
                            showtimes.append({'start': f"{hour:02d}:{minute:02d}"})
                
                if not showtimes:
                    # Fallback: extraire les horaires du texte complet
                    for match in time_pattern.finditer(movie_div.get_text()):
                        hour = int(match.group(1))
                        minute = int(match.group(2))
                        if 0 <= hour <= 23 and 0 <= minute <= 59:
                            showtimes.append({'start': f"{hour:02d}:{minute:02d}"})
                
                # Dédupliquer
                seen = set()
                unique_showtimes = []
                for st in showtimes:
                    key = st['start']
                    if key not in seen:
                        seen.add(key)
                        unique_showtimes.append(st)
                
                if unique_showtimes:
                    movies.append({
                        'title': title,
                        'showtimes': sorted(unique_showtimes, key=lambda x: x['start'])
                    })
                    
            except Exception as e:
                logger.error(f"Erreur parsing film: {e}")
                continue
        
        return movies
        
    except Exception as e:
        logger.error(f"Erreur scraping {cinema_id}: {e}")
        return []

def scrape_allocine_showtimes(cinema_id, date_str):
    """Récupère les horaires depuis Allociné et enrichit avec TMDB"""
    movies = fetch_allocine_showtimes_json(cinema_id, date_str)
    # Fallback HTML si l'endpoint JSON est indisponible ou vide pour la date du jour
    if movies is None or (len(movies) == 0 and date_str == datetime.now().strftime('%Y-%m-%d')):
        movies = fetch_allocine_showtimes_html(cinema_id)

    enriched_movies = []
    for movie in movies:
        title = movie.get('title', 'Titre inconnu')
        showtimes = movie.get('showtimes')
        if not showtimes:
            start_times = movie.get('start_times', [])
            showtimes = [{'start': st} for st in start_times]

        if not showtimes:
            continue

        tmdb_data = search_movie_tmdb(title)
        duration_minutes = 120
        if tmdb_data and tmdb_data.get('duration_minutes'):
            duration_minutes = tmdb_data['duration_minutes']

        for showtime in showtimes:
            start_dt = datetime.strptime(showtime['start'], '%H:%M')
            end_dt = start_dt + timedelta(minutes=duration_minutes)
            showtime['end'] = end_dt.strftime('%H:%M')

        if tmdb_data:
            enriched_movies.append({
                'title': title,
                'tmdb_id': tmdb_data.get('tmdb_id'),
                'director': tmdb_data['director'],
                'duration': tmdb_data['duration'],
                'showtimes': sorted(showtimes, key=lambda x: x['start']),
                'actors': tmdb_data['actors'],
                'poster_url': tmdb_data['poster_url'],
                'release_date': tmdb_data['release_date'],
                'overview': tmdb_data['overview'],
                'vote_average': tmdb_data['vote_average'],
                'letterboxd_rating': tmdb_data.get('letterboxd_rating'),
                'letterboxd_url': tmdb_data.get('letterboxd_url'),
                'genres': tmdb_data['genres']
            })
        else:
            enriched_movies.append({
                'title': title,
                'tmdb_id': None,
                'director': 'Réalisateur inconnu',
                'duration': '2h00',
                'showtimes': sorted(showtimes, key=lambda x: x['start']),
                'actors': [],
                'poster_url': None,
                'release_date': '',
                'overview': '',
                'vote_average': 0,
                'letterboxd_rating': None,
                'letterboxd_url': None,
                'genres': []
            })

    return enriched_movies

@app.route('/')
def home():
    return jsonify({
        'message': 'API Séance(s) - Horaires de cinéma à Paris',
        'endpoints': {
            '/cinemas': 'Liste des cinémas',
            '/showtimes?date=YYYY-MM-DD': 'Horaires (scraping Allociné + TMDB)',
            '/test-cinema/<cinema_name>': 'Tester un seul cinéma',
            '/prefetch-letterboxd?date=YYYY-MM-DD&token=...': 'Batch de cache Letterboxd'
        }
    })

@app.route('/cinemas')
def get_cinemas():
    return jsonify({
        'cinemas': list(CINEMA_IDS.keys())
    })

@app.route('/showtimes')
def get_showtimes():
    """Récupère les horaires en scrapant Allociné et enrichit avec TMDB"""
    date_param = request.args.get('date')
    
    if date_param:
        try:
            target_date = datetime.strptime(date_param, '%Y-%m-%d')
        except ValueError:
            return jsonify({'error': 'Format de date invalide'}), 400
    else:
        target_date = datetime.now()
    
    date_str = target_date.strftime('%Y-%m-%d')

    # Cache hit
    cached = SHOWTIMES_CACHE.get(date_str)
    if cached:
        cached_at, cached_data = cached
        if time.time() - cached_at < SHOWTIMES_TTL_SECONDS:
            return jsonify({
                'date': date_str,
                'showtimes': cached_data
            })

    all_showtimes = {}

    # Parallel scraping for faster response
    with ThreadPoolExecutor(max_workers=6) as executor:
        future_map = {
            executor.submit(scrape_allocine_showtimes, cinema_id, date_str): cinema_name
            for cinema_name, cinema_id in CINEMA_IDS.items()
        }
        for future in as_completed(future_map):
            cinema_name = future_map[future]
            try:
                showtimes = future.result()
            except Exception as exc:
                logger.error(f"Erreur scraping {cinema_name}: {exc}")
                showtimes = []
            all_showtimes[cinema_name] = showtimes

    SHOWTIMES_CACHE[date_str] = (time.time(), all_showtimes)

    return jsonify({
        'date': date_str,
        'showtimes': all_showtimes
    })

@app.route('/test-cinema/<cinema_name>')
def test_cinema(cinema_name):
    """Teste un seul cinéma"""
    if cinema_name not in CINEMA_IDS:
        return jsonify({'error': f'Cinéma {cinema_name} non trouvé'}), 404
    
    cinema_id = CINEMA_IDS[cinema_name]
    showtimes = scrape_allocine_showtimes(cinema_id, datetime.now().strftime('%Y-%m-%d'))
    
    return jsonify({
        'cinema': cinema_name,
        'cinema_id': cinema_id,
        'showtimes': showtimes
    })

@app.route('/prefetch-letterboxd')
def prefetch_letterboxd():
    """Préchauffe/calcule les notes Letterboxd pour une date (batch admin)."""
    token = request.args.get('token', '')
    if PREFETCH_TOKEN and token != PREFETCH_TOKEN:
        return jsonify({'error': 'Unauthorized'}), 403

    date_param = request.args.get('date') or datetime.now().strftime('%Y-%m-%d')
    max_movies = int(request.args.get('max_movies', 80))
    offset = max(0, int(request.args.get('offset', 0)))
    sleep_seconds = float(request.args.get('sleep', 0.8))

    titles = []
    for _, cinema_id in CINEMA_IDS.items():
        movies = fetch_allocine_showtimes_json(cinema_id, date_param) or []
        for movie in movies:
            title = (movie or {}).get('title')
            if title:
                titles.append(title)

    unique_titles = []
    seen = set()
    for t in titles:
        key = normalize_key(t)
        if key and key not in seen:
            seen.add(key)
            unique_titles.append(t)

    batch_titles = unique_titles[offset:offset + max_movies]
    has_more = (offset + len(batch_titles)) < len(unique_titles)

    processed = 0
    fetched = 0
    cached = 0
    blocked_or_missing = 0

    for title in batch_titles:
        tmdb_data = search_movie_tmdb(title)
        tmdb_id = tmdb_data.get('tmdb_id') if tmdb_data else None
        if not tmdb_id:
            continue

        processed += 1
        rating, url = get_cached_letterboxd(tmdb_id)
        if rating is not None:
            cached += 1
            continue

        rating, _ = fetch_letterboxd_rating_by_tmdb_id(tmdb_id, force_refresh=True)
        if rating is not None:
            fetched += 1
        else:
            blocked_or_missing += 1

        time.sleep(max(0.0, sleep_seconds))

    return jsonify({
        'date': date_param,
        'offset': offset,
        'batch_size': len(batch_titles),
        'total_unique_titles': len(unique_titles),
        'has_more': has_more,
        'processed_tmdb_ids': processed,
        'from_cache': cached,
        'fetched_letterboxd': fetched,
        'blocked_or_missing': blocked_or_missing,
        'enable_live_letterboxd': ENABLE_LIVE_LETTERBOXD,
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
