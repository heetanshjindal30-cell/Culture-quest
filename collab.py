"""
collab.py - Manages collaborative trip planning rooms.
Stored in data/rooms.json
"""
import json, os, uuid
from datetime import datetime

DATA_DIR   = os.path.join(os.path.dirname(__file__), "data")
ROOMS_FILE = os.path.join(DATA_DIR, "rooms.json")


def _load():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(ROOMS_FILE):
        _save({})
        return {}
    try:
        with open(ROOMS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(ROOMS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def create_room(creator_name, trip_name):
    rooms = _load()
    room_id = str(uuid.uuid4())[:6].upper()
    rooms[room_id] = {
        "id":         room_id,
        "trip_name":  trip_name,
        "creator":    creator_name,
        "members":    [creator_name],
        "messages":   [],
        "itinerary":  [],
        "expenses":   [],
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    _save(rooms)
    return rooms[room_id]


def get_room(room_id):
    rooms = _load()
    return rooms.get(room_id.upper())


def join_room(room_id, member_name):
    rooms = _load()
    rid = room_id.upper()
    if rid not in rooms:
        raise ValueError(f"Room '{rid}' not found.")
    if member_name not in rooms[rid]["members"]:
        rooms[rid]["members"].append(member_name)
    _save(rooms)
    return rooms[rid]


def add_message(room_id, sender, text, msg_type="chat"):
    rooms = _load()
    rid = room_id.upper()
    if rid not in rooms:
        raise ValueError("Room not found.")
    msg = {
        "id":     str(uuid.uuid4())[:8],
        "sender": sender,
        "text":   text,
        "type":   msg_type,
        "ts":     datetime.now().strftime("%H:%M")
    }
    rooms[rid]["messages"].append(msg)
    rooms[rid]["messages"] = rooms[rid]["messages"][-100:]
    _save(rooms)
    return msg


def add_itinerary_stop(room_id, added_by, stop):
    rooms = _load()
    rid = room_id.upper()
    if rid not in rooms:
        raise ValueError("Room not found.")
    stop["id"]       = str(uuid.uuid4())[:8]
    stop["added_by"] = added_by
    rooms[rid]["itinerary"].append(stop)
    _save(rooms)
    return stop


def remove_itinerary_stop(room_id, stop_id):
    rooms = _load()
    rid = room_id.upper()
    if rid not in rooms:
        raise ValueError("Room not found.")
    rooms[rid]["itinerary"] = [s for s in rooms[rid]["itinerary"] if s["id"] != stop_id]
    _save(rooms)


def add_expense(room_id, paid_by, description, amount, split_among):
    rooms = _load()
    rid = room_id.upper()
    if rid not in rooms:
        raise ValueError("Room not found.")
    exp = {
        "id":          str(uuid.uuid4())[:8],
        "paid_by":     paid_by,
        "description": description,
        "amount":      float(amount),
        "split_among": split_among,
        "per_person":  round(float(amount) / len(split_among), 2),
        "ts":          datetime.now().strftime("%Y-%m-%d %H:%M"),
        "settled":     []
    }
    rooms[rid]["expenses"].append(exp)
    _save(rooms)
    return exp


def settle_expense(room_id, expense_id, member_name):
    rooms = _load()
    rid = room_id.upper()
    if rid not in rooms:
        raise ValueError("Room not found.")
    for exp in rooms[rid]["expenses"]:
        if exp["id"] == expense_id:
            if member_name not in exp["settled"]:
                exp["settled"].append(member_name)
            break
    _save(rooms)


def get_balances(room_id):
    room = get_room(room_id)
    if not room:
        return {}
    members = room["members"]
    net = {m: 0.0 for m in members}
    for exp in room["expenses"]:
        paid_by = exp["paid_by"]
        amount  = exp["amount"]
        split   = exp["split_among"]
        per     = amount / len(split)
        if paid_by in net:
            net[paid_by] += amount
        for m in split:
            if m in net:
                net[m] -= per

    creditors = sorted([(v, k) for k, v in net.items() if v > 0.01],  reverse=True)
    debtors   = sorted([(abs(v), k) for k, v in net.items() if v < -0.01], reverse=True)
    transactions = []
    i = j = 0
    while i < len(creditors) and j < len(debtors):
        ca, creditor = creditors[i]
        da, debtor   = debtors[j]
        amt = round(min(ca, da), 2)
        transactions.append({"from": debtor, "to": creditor, "amount": amt})
        creditors[i] = (ca - amt, creditor)
        debtors[j]   = (da - amt, debtor)
        if creditors[i][0] < 0.01: i += 1
        if debtors[j][0]  < 0.01: j += 1

    return {"net": net, "settlements": transactions}