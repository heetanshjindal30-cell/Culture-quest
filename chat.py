"""
chat.py - Groq AI with multilingual support + persistent memory awareness
"""
from groq import Groq


def _is_hidden_gem(loc):
    v = loc.get("type of location", "").lower()
    return "hidden" in v or "local" in v


def _is_itinerary_request(message):
    m = message.lower()
    keywords = ["itinerary", "plan a trip", "day trip", "days in", "days at",
                "what to do in", "places to visit", "plan my trip", "schedule"]
    return any(k in m for k in keywords)


def _build_context(locations, message=""):
    if not locations:
        return "No locations loaded yet."
    msg_lower  = message.lower()
    is_planning = _is_itinerary_request(message)
    cap = 15 if is_planning else 8

    relevant = [
        loc for loc in locations
        if loc.get("City", "").lower() in msg_lower
        or loc.get("Place Name", "").lower() in msg_lower
    ]
    pool = (relevant if relevant else locations)[:cap]

    lines = []
    for loc in pool:
        badge = "GEM" if _is_hidden_gem(loc) else "Official"
        area  = loc.get("Area", "").strip() or loc.get("area", "").strip()
        parts = [loc.get("Place Name", ""), loc.get("City", "")]
        if area: parts.append(f"[{area}]")
        parts += [
            loc.get("Category", ""),
            loc.get("Vibe Description", "")[:60],
            f"Budget:{loc.get('Budget','').replace('?','Rs.').replace('₹','Rs.')}",
            badge,
        ]
        lines.append(" | ".join(p for p in parts if p))
    return "\n".join(lines)


def _build_system_prompt(locations, language="English", message="", interest_summary=""):
    ctx  = _build_context(locations, message)
    lang = f"Respond in {language} only." if language != "English" else ""

    memory_block = ""
    if interest_summary:
        memory_block = f"""
RETURNING USER CONTEXT (use this to personalise suggestions):
{interest_summary}
If they ask for suggestions without specifying a city, recommend from their previously explored cities.
If they ask "what else" or "anything similar", use their interest profile to guide recommendations.
"""

    return f"""You are a local travel friend. Casual, warm, punchy. No formal tone.{' ' + lang if lang else ''}
{memory_block}
Rules: greet briefly if just hi/hello. Only make itineraries when explicitly asked. Keep replies short.
For itineraries: cluster each day by zone/neighbourhood — all stops within 15 min of each other. Name the zone per day.
Format: Day N — [Zone]: 🌅Morning→place | ☀️Afternoon→place | 🌆Evening→place

Locations:
{ctx}"""


def get_chat_response(message, locations, api_key,
                      model="llama-3.1-8b-instant",
                      max_tokens=500, language="English",
                      history=None, interest_summary=""):
    try:
        client = Groq(api_key=api_key)
        prompt = _build_system_prompt(locations, language, message, interest_summary)
        msgs   = [{"role": "system", "content": prompt}]
        if history:
            msgs.extend(history)   # already capped by memory.py
        msgs.append({"role": "user", "content": message})
        resp = client.chat.completions.create(
            model=model, max_tokens=max_tokens, messages=msgs
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"Error: {str(e)}"