import urllib.request, urllib.parse, json

def get_weather(city, api_key):
    if not city or not api_key: return None
    try:
        q   = urllib.parse.quote(city+", India")
        url = f"http://api.weatherapi.com/v1/current.json?key={api_key}&q={q}&aqi=no"
        req = urllib.request.Request(url, headers={"User-Agent":"TripQuests/1.0"})
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read().decode())
        c = data["current"]
        return {"city":data["location"]["name"],"region":data["location"]["region"],
                "temp_c":c["temp_c"],"feels_like":c["feelslike_c"],"condition":c["condition"]["text"],
                "icon":"https:"+c["condition"]["icon"],"humidity":c["humidity"],
                "wind_kph":c["wind_kph"],"is_day":c["is_day"]}
    except Exception as e:
        print(f"Weather error: {e}"); return None

def weather_emoji(condition, is_day):
    c = condition.lower()
    if "sunny" in c or "clear" in c: return "☀️" if is_day else "🌙"
    if "partly" in c or "overcast" in c: return "⛅"
    if "cloud" in c: return "☁️"
    if "rain" in c or "drizzle" in c: return "🌧️"
    if "thunder" in c or "storm" in c: return "⛈️"
    if "snow" in c or "sleet" in c: return "❄️"
    if "fog" in c or "mist" in c: return "🌫️"
    return "🌤️"

def geocode_city(city):
    try:
        q   = urllib.parse.quote(city+", India")
        url = f"https://nominatim.openstreetmap.org/search?q={q}&format=json&limit=1"
        req = urllib.request.Request(url, headers={"User-Agent":"TripQuests/1.0"})
        with urllib.request.urlopen(req, timeout=6) as r:
            res = json.loads(r.read().decode())
        if res: return float(res[0]["lat"]), float(res[0]["lon"])
    except Exception as e:
        print(f"Geocode error: {e}")
    return None, None

def get_distance(origin, dest, ors_key):
    if not ors_key: return None
    try:
        o_lat,o_lng = geocode_city(origin)
        d_lat,d_lng = geocode_city(dest)
        if not all([o_lat,o_lng,d_lat,d_lng]): return None
        payload = json.dumps({"coordinates":[[o_lng,o_lat],[d_lng,d_lat]]}).encode()
        req = urllib.request.Request(
            "https://api.openrouteservice.org/v2/directions/driving-car",
            data=payload, method="POST",
            headers={"Authorization":ors_key,"Content-Type":"application/json","User-Agent":"TripQuests/1.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read().decode())
        seg = data["routes"][0]["segments"][0]
        dist_km = round(seg["distance"]/1000,1)
        dur_min = int(seg["duration"]/60)
        h,m = divmod(dur_min,60)
        return {"from":origin,"to":dest,"distance_km":dist_km,"duration_min":dur_min,
                "duration_text":f"{h}h {m}m" if h>0 else f"{m} min"}
    except Exception as e:
        print(f"Distance error: {e}"); return None
