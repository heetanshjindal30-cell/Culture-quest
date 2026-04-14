"""
CultureQuest — app.py
"""
import os, json
from flask import Flask, session, redirect, request, send_from_directory, render_template_string
from flask_cors import CORS
from config import Config

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

def create_app():
    app = Flask(__name__, static_folder=STATIC_DIR)
    app.secret_key = Config.SECRET_KEY
    app.config.from_object(Config)
    CORS(app)

    from api import api_blueprint
    app.register_blueprint(api_blueprint, url_prefix="/api")

    @app.route("/")
    def index(): return send_from_directory(STATIC_DIR, "index.html")

    @app.route("/collab")
    def collab(): return send_from_directory(STATIC_DIR, "collab.html")

    @app.route("/expenses")
    def expenses(): return send_from_directory(STATIC_DIR, "expenses.html")

    @app.route("/admin")
    def admin_page():
        if not session.get("admin_logged_in"):
            return send_from_directory(STATIC_DIR, "admin_login.html")
        return send_from_directory(STATIC_DIR, "admin.html")

    @app.route("/trip/<sid>")
    def shared_trip(sid):
        """Public shareable trip page."""
        shares_file = os.path.join(BASE_DIR, "data", "shared_trips.json")
        try:
            with open(shares_file,"r") as f: shares = json.load(f)
            trip = shares.get(sid)
        except: trip = None
        if not trip:
            return "<h2>Trip not found or link expired.</h2>", 404
        content_html = trip["content"].replace("\n","<br>")
        return render_template_string("""<!DOCTYPE html>
<html><head><meta charset="UTF-8"/>
<title>{{ title }}</title>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=DM+Sans:wght@400;500&display=swap" rel="stylesheet"/>
<style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:'DM Sans',sans-serif;background:#f5f0e8;min-height:100vh;padding:40px 20px}
.card{max-width:680px;margin:0 auto;background:#fff;border-radius:16px;padding:36px;box-shadow:0 4px 24px rgba(0,0,0,.08)}
h1{font-family:'Playfair Display',serif;color:#1a2e1a;margin-bottom:6px}
.sub{color:#7a9e68;font-size:.82rem;margin-bottom:24px}
.body{font-size:.92rem;line-height:1.8;color:#333}
.foot{margin-top:28px;padding-top:16px;border-top:1px solid #e8dcc8;font-size:.76rem;color:#aaa}
.foot a{color:#3d5c2e;text-decoration:none;font-weight:600}</style>
</head><body><div class="card">
<h1>{{ title }}</h1>
<div class="sub">🗺️ Shared via CultureQuest · {{ created_at }}</div>
<div class="body">{{ content_html | safe }}</div>
<div class="foot">Plan your own trip at <a href="/">CultureQuest</a></div>
</div></body></html>""", title=trip["title"], content_html=content_html,
            created_at=trip["created_at"])

    @app.route("/static/<path:fn>")
    def static_files(fn): return send_from_directory(STATIC_DIR, fn)

    return app

if __name__ == "__main__":
    app = create_app()
    print("\n🌿 CultureQuest starting...")
    print(f"📁  Static dir : {STATIC_DIR}")
    print("🗺️   Main app  : http://localhost:5000")
    print("👥  Collab    : http://localhost:5000/collab")
    print("💰  Expenses  : http://localhost:5000/expenses")
    print("⚙️   Admin     : http://localhost:5000/admin")
    print("🛑  Stop      : CTRL+C\n")
    app.run(debug=False, host=Config.HOST, port=Config.PORT)