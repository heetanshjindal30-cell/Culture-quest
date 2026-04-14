"""
api.py — All Flask routes
"""
from flask import Blueprint, request, jsonify, current_app, session, redirect, Response, make_response
from chat import get_chat_response
from csv_manager import CSVManager
from weather_distance import get_weather, get_distance, weather_emoji
from recommender import get_recommendations, explain_recommendation
from collab import (create_room, get_room, join_room, add_message as collab_add_message,
                    add_itinerary_stop, remove_itinerary_stop,
                    add_expense, settle_expense, get_balances)
from geocoder import geocode_locations
from memory import (get_or_create_user, add_message as mem_add,
                    get_history_for_llm, get_interest_summary,
                    get_sessions, get_session_messages,
                    clear_user_history, get_all_users,
                    save_trip, get_saved_trips, delete_trip,
                    add_review, get_reviews, verify_place)
import uuid

api_blueprint = Blueprint("api", __name__)
csv_manager   = CSVManager()


def _get_user_ip():
    """Get real IP, works behind proxies."""
    return (request.headers.get("X-Forwarded-For","").split(",")[0].strip()
            or request.headers.get("X-Real-IP","")
            or request.remote_addr
            or "0.0.0.0")


# ── Admin auth ─────────────────────────────────────────────
@api_blueprint.route("/admin-login", methods=["POST"])
def admin_login():
    if request.form.get("password","").strip() == current_app.config.get("ADMIN_PASSWORD",""):
        session["admin_logged_in"] = True; session.modified = True
        return redirect("/admin")
    return redirect("/admin?error=1")

@api_blueprint.route("/admin-logout")
def admin_logout():
    session.clear(); return redirect("/admin")

def _admin():
    if not session.get("admin_logged_in"):
        return jsonify({"error":"Unauthorized"}), 401
    return None


# ── Chat ───────────────────────────────────────────────────
@api_blueprint.route("/chat", methods=["POST"])
def chat():
    body = request.get_json(silent=True) or {}
    msg  = body.get("message","").strip()
    lang = body.get("language","English")
    if not msg: return jsonify({"error":"message required"}),400
    key = current_app.config.get("GROQ_API_KEY","")
    if not key: return jsonify({"error":"Groq API key not set in .env"}),500

    ip  = _get_user_ip()
    uid, _ = get_or_create_user(ip)
    history  = get_history_for_llm(uid)
    summary  = get_interest_summary(uid)
    locations = csv_manager.load_locations()

    reply = get_chat_response(msg, locations, key,
                              current_app.config.get("GROQ_MODEL","llama-3.1-8b-instant"),
                              current_app.config.get("MAX_TOKENS",500),
                              lang, history=history, interest_summary=summary)

    mem_add(uid, "user",      msg)
    mem_add(uid, "assistant", reply)

    return jsonify({"reply": reply, "user_id": uid})


# ── Sessions (chat history sidebar) ───────────────────────
@api_blueprint.route("/sessions")
def get_user_sessions():
    ip  = _get_user_ip()
    uid, _ = get_or_create_user(ip)
    sessions = get_sessions(uid)
    # Return only metadata for sidebar (no full messages)
    sidebar = [{"id": s["id"], "title": s["title"], "date": s["date"]} for s in sessions]
    return jsonify({"sessions": sidebar, "user_id": uid})

@api_blueprint.route("/sessions/<sid>")
def get_session(sid):
    ip  = _get_user_ip()
    uid, _ = get_or_create_user(ip)
    msgs = get_session_messages(uid, sid)
    return jsonify({"messages": msgs})

@api_blueprint.route("/clear-history", methods=["POST"])
def clear_history():
    ip  = _get_user_ip()
    uid, _ = get_or_create_user(ip)
    clear_user_history(uid)
    session.pop("view_history", None); session.modified = True
    return jsonify({"ok": True})


# ── Saved Trips ────────────────────────────────────────────
@api_blueprint.route("/trips", methods=["GET"])
def list_trips():
    ip  = _get_user_ip()
    uid, _ = get_or_create_user(ip)
    return jsonify({"trips": get_saved_trips(uid)})

@api_blueprint.route("/trips", methods=["POST"])
def create_trip():
    ip   = _get_user_ip()
    uid, _ = get_or_create_user(ip)
    body = request.get_json(silent=True) or {}
    title   = body.get("title","My Trip").strip()
    content = body.get("content","").strip()
    if not content: return jsonify({"error":"content required"}),400
    trip = save_trip(uid, title, content)
    return jsonify({"trip": trip})

@api_blueprint.route("/trips/<tid>", methods=["DELETE"])
def remove_trip(tid):
    ip  = _get_user_ip()
    uid, _ = get_or_create_user(ip)
    delete_trip(uid, tid)
    return jsonify({"ok": True})


# ── Share Itinerary ────────────────────────────────────────
@api_blueprint.route("/share", methods=["POST"])
def share_trip():
    """Create a public shareable link for an itinerary."""
    import json as _json
    body    = request.get_json(silent=True) or {}
    content = body.get("content","").strip()
    title   = body.get("title","Shared Trip").strip()
    if not content: return jsonify({"error":"content required"}),400
    share_id = str(uuid.uuid4())[:8]
    shares_file = __import__("os").path.join(
        __import__("os").path.dirname(__import__("os").path.abspath(__file__)),
        "data","shared_trips.json")
    try:
        with open(shares_file,"r") as f: shares = _json.load(f)
    except: shares = {}
    shares[share_id] = {
        "title": title, "content": content,
        "created_at": __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    with open(shares_file,"w") as f: _json.dump(shares, f, indent=2)
    return jsonify({"share_id": share_id, "url": f"/trip/{share_id}"})

@api_blueprint.route("/share/<sid>")
def get_shared(sid):
    import json as _json
    shares_file = __import__("os").path.join(
        __import__("os").path.dirname(__import__("os").path.abspath(__file__)),
        "data","shared_trips.json")
    try:
        with open(shares_file,"r") as f: shares = _json.load(f)
        if sid in shares: return jsonify(shares[sid])
    except: pass
    return jsonify({"error":"Not found"}), 404


# ── Reviews & Verify ──────────────────────────────────────
@api_blueprint.route("/reviews/<path:place>", methods=["GET"])
def place_reviews(place):
    return jsonify(get_reviews(place))

@api_blueprint.route("/reviews/<path:place>", methods=["POST"])
def post_review(place):
    ip  = _get_user_ip()
    uid, _ = get_or_create_user(ip)
    body   = request.get_json(silent=True) or {}
    rating  = int(body.get("rating", 5))
    comment = body.get("comment","").strip()
    verify  = bool(body.get("verify", False))
    if not 1 <= rating <= 5: return jsonify({"error":"rating must be 1-5"}),400
    add_review(place, uid, rating, comment, verify)
    return jsonify(get_reviews(place))

@api_blueprint.route("/verify/<path:place>", methods=["POST"])
def verify_gem(place):
    ip  = _get_user_ip()
    uid, _ = get_or_create_user(ip)
    count = verify_place(place, uid)
    return jsonify({"verify_count": count, "locally_verified": count >= 3})


# ── Surprise Me ────────────────────────────────────────────
@api_blueprint.route("/surprise", methods=["POST"])
def surprise_me():
    import random
    body = request.get_json(silent=True) or {}
    lang = body.get("language","English")
    locations = csv_manager.load_locations()
    # Pick from hidden gems preferably
    gems = [l for l in locations if "hidden" in l.get("type of location","").lower()
            or "local" in l.get("type of location","").lower()]
    pool = gems if gems else locations
    if not pool: return jsonify({"error":"No locations loaded"}),400
    pick = random.choice(pool)
    city = pick.get("City","")
    prompt = f"Surprise me with a fun day trip to {city} focusing on {pick.get('Place Name','')}. Plan one full day, keep it punchy and exciting!"
    key  = current_app.config.get("GROQ_API_KEY","")
    ip   = _get_user_ip()
    uid, _ = get_or_create_user(ip)
    reply = get_chat_response(prompt, locations, key,
                              current_app.config.get("GROQ_MODEL","llama-3.1-8b-instant"),
                              current_app.config.get("MAX_TOKENS",500), lang)
    mem_add(uid, "user",      "🎲 Surprise me!")
    mem_add(uid, "assistant", reply)
    return jsonify({"reply": reply, "destination": city, "place": pick.get("Place Name","")})


# ── Compare ────────────────────────────────────────────────
@api_blueprint.route("/compare", methods=["POST"])
def compare_trips():
    body = request.get_json(silent=True) or {}
    city1 = body.get("city1","").strip()
    city2 = body.get("city2","").strip()
    days  = body.get("days", 3)
    lang  = body.get("language","English")
    if not city1 or not city2: return jsonify({"error":"city1 and city2 required"}),400
    key   = current_app.config.get("GROQ_API_KEY","")
    locations = csv_manager.load_locations()
    prompt = (f"Compare {city1} vs {city2} for a {days}-day trip. "
              f"Give a punchy side-by-side: best for, vibe, budget, hidden gems, food. "
              f"End with a clear recommendation based on what each type of traveller would prefer.")
    reply = get_chat_response(prompt, locations, key,
                              current_app.config.get("GROQ_MODEL","llama-3.1-8b-instant"),
                              current_app.config.get("MAX_TOKENS",600), lang)
    return jsonify({"reply": reply})


# ── Locations ──────────────────────────────────────────────
@api_blueprint.route("/locations")
def get_locations():
    locs = csv_manager.load_locations()
    return jsonify({**csv_manager.stats(),"locations":locs})

# ── Locations with coords (for map) ───────────────────────
@api_blueprint.route("/locations/map")
def get_locations_map():
    locs = csv_manager.load_locations()
    # Geocode all locations (uses cache, only new ones hit the API)
    locs_with_coords = geocode_locations(locs)
    result = []
    for loc in locs_with_coords:
        if loc.get("lat") and loc.get("lng"):
            tp  = loc.get("type of location","").lower()
            gem = "hidden" in tp or "local" in tp
            result.append({
                "name":     loc.get("Place Name",""),
                "city":     loc.get("City",""),
                "category": loc.get("Category",""),
                "vibe":     loc.get("Vibe Description",""),
                "budget":   loc.get("Budget","").replace("?","Rs.").replace("₹","Rs."),
                "food":     loc.get("food to try",""),
                "type":     "gem" if gem else "official",
                "lat":      loc["lat"],
                "lng":      loc["lng"],
            })
    return jsonify({"locations": result, "total": len(result)})

# ── Weather ────────────────────────────────────────────────
@api_blueprint.route("/weather/<city>")
def weather(city):
    key = current_app.config.get("WEATHER_API_KEY","")
    if not key: return jsonify({"error":"Weather key not set"}),500
    d = get_weather(city, key)
    if not d: return jsonify({"error":"City not found"}),404
    d["emoji"] = weather_emoji(d["condition"], d["is_day"])
    return jsonify(d)

# ── Distance ───────────────────────────────────────────────
@api_blueprint.route("/distance")
def distance():
    orig = request.args.get("from","").strip()
    dest = request.args.get("to","").strip()
    if not orig or not dest: return jsonify({"error":"Need from and to"}),400
    key = current_app.config.get("ORS_API_KEY","")
    d = get_distance(orig, dest, key)
    if not d: return jsonify({"error":"Could not calculate"}),404
    return jsonify(d)

# ── Track view ─────────────────────────────────────────────
@api_blueprint.route("/track-view", methods=["POST"])
def track_view():
    name = (request.get_json(silent=True) or {}).get("place_name","").strip()
    if not name: return jsonify({"error":"place_name required"}),400
    history = session.get("view_history",[])
    history = [h for h in history if h.lower()!=name.lower()]
    history.insert(0,name); session["view_history"] = history[:20]; session.modified = True
    return jsonify({"ok":True})

# ── Recommendations ────────────────────────────────────────
@api_blueprint.route("/recommendations")
def recommendations():
    history   = session.get("view_history",[])
    locations = csv_manager.load_locations()
    recs      = get_recommendations(history, locations, top_n=int(request.args.get("n",4)))
    hist_locs = [l for l in locations if l.get("Place Name","") in history]
    result    = [{"Place Name":r.get("Place Name",""),"City":r.get("City",""),
                  "Category":r.get("Category",""),"Vibe Description":r.get("Vibe Description",""),
                  "Budget":r.get("Budget","").replace("₹","Rs.").replace("?","Rs."),
                  "type of location":r.get("type of location",""),
                  "reason":explain_recommendation(r,hist_locs)} for r in recs]
    return jsonify({"recommendations":result,"based_on":history[:5],"history_count":len(history)})

# ── Submit gem ─────────────────────────────────────────────
@api_blueprint.route("/submit-gem", methods=["POST"])
def submit_gem():
    data = request.get_json(silent=True) or {}
    for f in ["name","city","category","description"]:
        if not data.get(f): return jsonify({"error":f"'{f}' required"}),400
    return jsonify({"message":"Submitted!","gem_id":csv_manager.add_pending_gem(data)})

# ── Admin routes ───────────────────────────────────────────
@api_blueprint.route("/upload-csv", methods=["POST"])
def upload_csv():
    e=_admin()
    if e: return e
    if "csv_file" not in request.files: return jsonify({"error":"No file"}),400
    f = request.files["csv_file"]
    if not f.filename.lower().endswith(".csv"): return jsonify({"error":"CSV only"}),400
    try:
        count,preview = csv_manager.upload_csv(f)
        return jsonify({"message":f"CSV loaded — {count} locations.","count":count,"preview":preview[:10]})
    except Exception as ex: return jsonify({"error":str(ex)}),500

@api_blueprint.route("/pending-gems")
def get_pending_gems():
    e=_admin();
    if e: return e
    p=csv_manager.get_pending_gems(); return jsonify({"pending":p,"count":len(p)})

@api_blueprint.route("/approve-gem/<gid>", methods=["POST"])
def approve_gem(gid):
    e=_admin()
    if e: return e
    try: gem=csv_manager.approve_gem(gid); return jsonify({"message":f"'{gem['Place Name']}' approved!"})
    except ValueError as ex: return jsonify({"error":str(ex)}),404

@api_blueprint.route("/reject-gem/<gid>", methods=["POST"])
def reject_gem(gid):
    e=_admin()
    if e: return e
    try: csv_manager.reject_gem(gid); return jsonify({"message":"Rejected."})
    except ValueError as ex: return jsonify({"error":str(ex)}),404

@api_blueprint.route("/export-csv")
def export_csv():
    e=_admin()
    if e: return e
    return Response(csv_manager.export_csv(),mimetype="text/csv",
                    headers={"Content-Disposition":"attachment; filename=culturequest_locations.csv"})

@api_blueprint.route("/admin/users")
def admin_users():
    e=_admin()
    if e: return e
    return jsonify({"users": get_all_users()})

@api_blueprint.route("/admin/users/<uid>/clear", methods=["POST"])
def admin_clear_user(uid):
    e=_admin()
    if e: return e
    clear_user_history(uid)
    return jsonify({"ok": True})

# ── Collab rooms ───────────────────────────────────────────
@api_blueprint.route("/room/create", methods=["POST"])
def room_create():
    body=request.get_json(silent=True) or {}
    creator=body.get("creator","").strip(); trip_name=body.get("trip_name","My Trip").strip()
    if not creator: return jsonify({"error":"creator name required"}),400
    return jsonify(create_room(creator, trip_name))

@api_blueprint.route("/room/<rid>")
def room_get(rid):
    room=get_room(rid)
    if not room: return jsonify({"error":"Room not found"}),404
    return jsonify(room)

@api_blueprint.route("/room/<rid>/join", methods=["POST"])
def room_join(rid):
    name=(request.get_json(silent=True) or {}).get("name","").strip()
    if not name: return jsonify({"error":"name required"}),400
    try: return jsonify(join_room(rid, name))
    except ValueError as e: return jsonify({"error":str(e)}),404

@api_blueprint.route("/room/<rid>/message", methods=["POST"])
def room_message(rid):
    body=request.get_json(silent=True) or {}
    sender=body.get("sender","").strip(); text=body.get("text","").strip()
    if not sender or not text: return jsonify({"error":"sender and text required"}),400
    return jsonify(collab_add_message(rid, sender, text))

@api_blueprint.route("/room/<rid>/itinerary", methods=["POST"])
def room_add_stop(rid):
    body=request.get_json(silent=True) or {}
    added_by=body.get("added_by","").strip()
    stop={"day":body.get("day","Day 1"),"time":body.get("time",""),
          "place":body.get("place","").strip(),"city":body.get("city","").strip(),
          "note":body.get("note","").strip()}
    if not stop["place"]: return jsonify({"error":"place required"}),400
    return jsonify(add_itinerary_stop(rid, added_by, stop))

@api_blueprint.route("/room/<rid>/itinerary/<stop_id>", methods=["DELETE"])
def room_remove_stop(rid, stop_id):
    try: remove_itinerary_stop(rid, stop_id); return jsonify({"ok":True})
    except ValueError as e: return jsonify({"error":str(e)}),404

@api_blueprint.route("/room/<rid>/expense", methods=["POST"])
def room_add_expense(rid):
    body=request.get_json(silent=True) or {}
    paid_by=body.get("paid_by","").strip(); description=body.get("description","").strip()
    amount=body.get("amount",0); split_among=body.get("split_among",[])
    if not paid_by or not description or not amount or not split_among:
        return jsonify({"error":"paid_by, description, amount, split_among required"}),400
    try: return jsonify(add_expense(rid, paid_by, description, float(amount), split_among))
    except Exception as e: return jsonify({"error":str(e)}),500

@api_blueprint.route("/room/<rid>/expense/<eid>/settle", methods=["POST"])
def room_settle(rid, eid):
    member=(request.get_json(silent=True) or {}).get("member","").strip()
    if not member: return jsonify({"error":"member required"}),400
    settle_expense(rid, eid, member); return jsonify({"ok":True})

@api_blueprint.route("/room/<rid>/balances")
def room_balances(rid):
    try: return jsonify(get_balances(rid))
    except Exception as e: return jsonify({"error":str(e)}),500

@api_blueprint.route("/health")
def health():
    return jsonify({"status":"ok","groq":bool(current_app.config.get("GROQ_API_KEY")),
                    "weather":bool(current_app.config.get("WEATHER_API_KEY")),
                    "ors":bool(current_app.config.get("ORS_API_KEY")),**csv_manager.stats()})