"""
memory.py — Persistent per-user chat history using IP as user ID.
Stores in data/user_memories.json
Each IP gets: full chat history (grouped into sessions), interest profile.
"""
import json, os, hashlib
from datetime import datetime

DATA_DIR    = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
MEMORY_FILE = os.path.join(DATA_DIR, "user_memories.json")
TRIPS_FILE  = os.path.join(DATA_DIR, "saved_trips.json")
REVIEWS_FILE= os.path.join(DATA_DIR, "reviews.json")

MAX_HISTORY_STORED = 500
MAX_HISTORY_TO_LLM = 6


def _ip_to_uid(ip):
    """Hash IP for privacy — never store raw IPs."""
    return "u_" + hashlib.md5(ip.encode()).hexdigest()[:10]


def _load(path=None):
    p = path or MEMORY_FILE
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(p):
        _save({}, p); return {}
    try:
        with open(p, "r", encoding="utf-8") as f: return json.load(f)
    except: return {}


def _save(data, path=None):
    p = path or MEMORY_FILE
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ── User / History ─────────────────────────────────────────

def get_or_create_user(ip):
    uid  = _ip_to_uid(ip)
    data = _load()
    if uid not in data:
        data[uid] = {
            "id": uid, "ip_hint": ip[:6]+"***",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "last_seen":  datetime.now().strftime("%Y-%m-%d %H:%M"),
            "sessions": [],      # list of session objects [{id, title, date, messages:[]}]
            "history":  [],      # flat list for LLM context
            "interests": {"cities": [], "categories": [], "style": []}
        }
        _save(data)
    return uid, data[uid]


def _current_session(user_data):
    """Return today's session, creating one if needed."""
    today = datetime.now().strftime("%Y-%m-%d")
    sessions = user_data.get("sessions", [])
    for s in sessions:
        if s.get("date") == today:
            return s
    # New session for today
    new_session = {
        "id":       today + "_" + str(len(sessions)),
        "date":     today,
        "title":    "Chat on " + datetime.now().strftime("%d %b %Y"),
        "messages": []
    }
    sessions.append(new_session)
    user_data["sessions"] = sessions
    return new_session


def add_message(uid, role, content):
    data = _load()
    if uid not in data:
        return
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    data[uid]["last_seen"] = now

    msg = {"role": role, "content": content, "ts": now}

    # Add to flat history (for LLM)
    data[uid]["history"].append(msg)
    data[uid]["history"] = data[uid]["history"][-MAX_HISTORY_STORED:]

    # Add to today's session (for sidebar display)
    session = _current_session(data[uid])
    session["messages"].append(msg)

    # Auto-update session title from first user message
    if role == "user" and len(session["messages"]) <= 2:
        title = content[:40] + ("…" if len(content) > 40 else "")
        session["title"] = title

    # Extract interests
    if role == "user":
        _extract_interests(data[uid], content)

    _save(data)


def _extract_interests(profile, message):
    msg = message.lower()
    known_cities = [
        "mumbai","bombay","delhi","bangalore","bengaluru","chandigarh",
        "jaipur","goa","kolkata","hyderabad","pune","ahmedabad","surat",
        "ropar","amritsar","ludhiana","shimla","manali","dharamshala",
        "agra","varanasi","udaipur","jodhpur","kochi","mysore","ooty",
        "darjeeling","rishikesh","haridwar","mussoorie","nainital"
    ]
    for city in known_cities:
        if city in msg:
            d = city.title()
            if d not in profile["interests"]["cities"]:
                profile["interests"]["cities"].insert(0, d)
                profile["interests"]["cities"] = profile["interests"]["cities"][:10]
    cat_map = {
        "cafe":"cafes","coffee":"cafes","chai":"cafes",
        "food":"food","eat":"food","restaurant":"food",
        "heritage":"heritage","fort":"heritage","temple":"heritage",
        "nature":"nature","trek":"trekking","hike":"trekking",
        "beach":"beaches","sea":"beaches",
        "hidden":"hidden gems","offbeat":"hidden gems","local":"hidden gems",
        "budget":"budget travel","cheap":"budget travel",
        "luxury":"luxury","resort":"luxury",
        "solo":"solo travel","family":"family trips","kids":"family trips",
        "art":"art & culture","museum":"art & culture",
        "shopping":"shopping","market":"shopping",
    }
    for kw, cat in cat_map.items():
        if kw in msg and cat not in profile["interests"]["categories"]:
            profile["interests"]["categories"].insert(0, cat)
            profile["interests"]["categories"] = profile["interests"]["categories"][:8]


def get_history_for_llm(uid):
    data = _load()
    if uid not in data: return []
    recent = data[uid].get("history", [])[-MAX_HISTORY_TO_LLM:]
    return [{"role": m["role"], "content": m["content"]} for m in recent]


def get_interest_summary(uid):
    data = _load()
    if uid not in data: return ""
    i = data[uid].get("interests", {})
    parts = []
    if i.get("cities"):     parts.append("Cities explored: " + ", ".join(i["cities"][:5]))
    if i.get("categories"): parts.append("Interests: " + ", ".join(i["categories"][:5]))
    return ("User profile: " + " | ".join(parts)) if parts else ""


def get_sessions(uid):
    """Return all sessions for sidebar display (newest first)."""
    data = _load()
    if uid not in data: return []
    sessions = data[uid].get("sessions", [])
    return list(reversed(sessions))


def get_session_messages(uid, session_id):
    """Return messages for a specific session."""
    data = _load()
    if uid not in data: return []
    for s in data[uid].get("sessions", []):
        if s["id"] == session_id:
            return s["messages"]
    return []


def clear_user_history(uid):
    data = _load()
    if uid in data:
        data[uid]["history"]  = []
        data[uid]["sessions"] = []
        data[uid]["interests"] = {"cities": [], "categories": [], "style": []}
        _save(data)


def get_all_users():
    data = _load()
    result = []
    for uid, u in data.items():
        result.append({
            "id": uid, "ip_hint": u.get("ip_hint",""),
            "created": u.get("created_at",""), "last_seen": u.get("last_seen",""),
            "messages": len(u.get("history",[])),
            "sessions": len(u.get("sessions",[])),
            "cities":   u.get("interests",{}).get("cities",[]),
            "interests":u.get("interests",{}).get("categories",[]),
        })
    return sorted(result, key=lambda x: x["last_seen"], reverse=True)


# ── Saved Trips ────────────────────────────────────────────

def save_trip(uid, title, content):
    import uuid
    data = _load(TRIPS_FILE)
    if uid not in data: data[uid] = []
    trip = {
        "id":      str(uuid.uuid4())[:8],
        "title":   title,
        "content": content,
        "saved_at":datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    data[uid].insert(0, trip)
    data[uid] = data[uid][:20]  # keep last 20 trips
    _save(data, TRIPS_FILE)
    return trip


def get_saved_trips(uid):
    data = _load(TRIPS_FILE)
    return data.get(uid, [])


def delete_trip(uid, trip_id):
    data = _load(TRIPS_FILE)
    if uid in data:
        data[uid] = [t for t in data[uid] if t["id"] != trip_id]
        _save(data, TRIPS_FILE)


# ── Reviews ────────────────────────────────────────────────

def add_review(place_name, uid, rating, comment, verify=False):
    import uuid
    data = _load(REVIEWS_FILE)
    if place_name not in data:
        data[place_name] = {"reviews": [], "verify_count": 0}
    # One review per user per place
    data[place_name]["reviews"] = [
        r for r in data[place_name]["reviews"] if r.get("uid") != uid
    ]
    data[place_name]["reviews"].append({
        "id":      str(uuid.uuid4())[:8],
        "uid":     uid,
        "rating":  rating,
        "comment": comment,
        "ts":      datetime.now().strftime("%Y-%m-%d %H:%M")
    })
    if verify:
        data[place_name]["verify_count"] = data[place_name].get("verify_count", 0) + 1
    _save(data, REVIEWS_FILE)


def get_reviews(place_name):
    data = _load(REVIEWS_FILE)
    place = data.get(place_name, {"reviews": [], "verify_count": 0})
    reviews = place.get("reviews", [])
    avg = round(sum(r["rating"] for r in reviews) / len(reviews), 1) if reviews else 0
    verified = place.get("verify_count", 0) >= 3  # 3+ locals = verified badge
    return {
        "reviews":      reviews,
        "avg_rating":   avg,
        "count":        len(reviews),
        "locally_verified": verified,
        "verify_count": place.get("verify_count", 0)
    }


def verify_place(place_name, uid):
    """User marks a place as locally verified."""
    data = _load(REVIEWS_FILE)
    if place_name not in data:
        data[place_name] = {"reviews": [], "verify_count": 0, "verifiers": []}
    verifiers = data[place_name].get("verifiers", [])
    if uid not in verifiers:
        verifiers.append(uid)
        data[place_name]["verifiers"]    = verifiers
        data[place_name]["verify_count"] = len(verifiers)
        _save(data, REVIEWS_FILE)
    return data[place_name]["verify_count"]