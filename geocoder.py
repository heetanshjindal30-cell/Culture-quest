"""
geocoder.py — Auto-geocode all CSV locations using Nominatim (free, no API key).
Results cached in data/geocache.json so each city is only looked up once ever.
"""
import json, os, time, urllib.request, urllib.parse

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
CACHE_FILE  = os.path.join(BASE_DIR, "data", "geocache.json")


def _load_cache():
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return {}


def _save_cache(cache):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)


def _nominatim_lookup(query):
    """Look up lat/lng for a place using OpenStreetMap Nominatim."""
    try:
        q   = urllib.parse.quote(query + ", India")
        url = f"https://nominatim.openstreetmap.org/search?q={q}&format=json&limit=1"
        req = urllib.request.Request(url, headers={"User-Agent": "CultureQuest/1.0"})
        with urllib.request.urlopen(req, timeout=5) as r:
            res = json.loads(r.read().decode())
        if res:
            return float(res[0]["lat"]), float(res[0]["lon"])
    except Exception as e:
        print(f"  Geocode failed for '{query}': {e}")
    return None, None


def geocode_locations(locations):
    """
    Takes a list of location dicts, returns the same list with
    'lat' and 'lng' added to each entry. Uses cache to avoid repeat lookups.
    """
    cache = _load_cache()
    updated = False

    for loc in locations:
        place = loc.get("Place Name", "").strip()
        city  = loc.get("City", "").strip()

        # Try place+city first, fall back to just city
        key_full = f"{place}|{city}"
        key_city = city

        if key_full in cache:
            loc["lat"], loc["lng"] = cache[key_full]
        elif key_city in cache:
            loc["lat"], loc["lng"] = cache[key_city]
        else:
            # Not cached — look up place+city
            print(f"  Geocoding: {place}, {city}...")
            lat, lng = _nominatim_lookup(f"{place}, {city}")
            if lat:
                cache[key_full] = [lat, lng]
                loc["lat"], loc["lng"] = lat, lng
            else:
                # Fall back to just city
                lat, lng = _nominatim_lookup(city)
                if lat:
                    cache[key_city] = [lat, lng]
                    loc["lat"], loc["lng"] = lat, lng
                else:
                    loc["lat"], loc["lng"] = None, None
            updated = True
            time.sleep(1)  # Nominatim rate limit: 1 req/sec

    if updated:
        _save_cache(cache)
        print(f"  Geocache updated: {len(cache)} entries saved.")

    return locations