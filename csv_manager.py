import csv, os, uuid, json
from datetime import datetime
from io import StringIO
from config import Config

CSV_COLUMNS = ["City","Place Name","Category","Vibe Description","Budget",
               "Best time to visit in each season","type of location",
               "detailed description","food to try"]
PENDING_FILE = os.path.join(os.path.dirname(__file__), "data", "pending_gems.json")

def _is_hidden_gem(loc):
    v = loc.get("type of location","").lower()
    return "hidden" in v or "local" in v

class CSVManager:
    def __init__(self, csv_path=None):
        self.csv_path = csv_path or Config.CSV_FILE_PATH
        os.makedirs(os.path.dirname(self.csv_path), exist_ok=True)
        self._ensure_csv_exists()
        self._ensure_pending_file()

    def _ensure_csv_exists(self):
        if not os.path.exists(self.csv_path):
            self._write_locations([
                {"City":"Ropar","Place Name":"Ropar Wetland","Category":"Nature Spot",
                 "Vibe Description":"Peaceful misty mornings with migratory birds. Zero crowds.",
                 "Budget":"Free","Best time to visit in each season":"Winter (Oct-Feb)",
                 "type of location":"local hidden gem",
                 "detailed description":"Hidden birding paradise along the Sutlej. 150+ migratory species.",
                 "food to try":"Carry snacks - no stalls nearby"},
                {"City":"Chandigarh","Place Name":"Rock Garden","Category":"Art / Culture",
                 "Vibe Description":"Surreal sculptures from industrial waste.",
                 "Budget":"Rs.30-50","Best time to visit in each season":"Winter (Nov-Feb)",
                 "type of location":"official",
                 "detailed description":"40-acre sculpture garden by Nek Chand. A uniquely Indian art experience.",
                 "food to try":"Chaat stalls outside entrance"},
                {"City":"Ropar","Place Name":"Old Anaj Mandi Chai Corner","Category":"Cafe / Tea Stall",
                 "Vibe Description":"60-year-old tea stall. Real kulhad chai.",
                 "Budget":"Rs.10-20","Best time to visit in each season":"Any season",
                 "type of location":"local hidden gem",
                 "detailed description":"Same family for 60 years. Kulhad chai locals swear by.",
                 "food to try":"Kulhad chai with butter biscuits"},
            ])

    def _ensure_pending_file(self):
        if not os.path.exists(PENDING_FILE):
            with open(PENDING_FILE,"w") as f: json.dump([],f)

    def load_locations(self):
        if not os.path.exists(self.csv_path): return []
        rows = []
        with open(self.csv_path, newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                clean = {k.strip():v.strip() for k,v in row.items() if k and k.strip()}
                if clean.get("Place Name"): rows.append(clean)
        return rows

    def _write_locations(self, locations):
        with open(self.csv_path,"w",newline="",encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
            w.writeheader()
            for loc in locations:
                w.writerow({col:loc.get(col,"") for col in CSV_COLUMNS})

    def _append_location(self, loc):
        existing = self.load_locations()
        existing.append(loc)
        self._write_locations(existing)

    def upload_csv(self, file_obj):
        raw_bytes = file_obj.read()
        raw = None
        for enc in ["utf-8-sig","utf-8","cp1252","latin-1"]:
            try: raw = raw_bytes.decode(enc); break
            except: continue
        if not raw: raise ValueError("Cannot decode CSV. Save as UTF-8.")
        new_rows = []
        for row in csv.DictReader(StringIO(raw)):
            clean = {k.strip():v.strip() for k,v in row.items() if k and k.strip()}
            if clean.get("Place Name"): new_rows.append(clean)
        if not new_rows: raise ValueError("No valid rows found.")
        existing_gems = [l for l in self.load_locations() if _is_hidden_gem(l)]
        new_names = {r.get("Place Name","").lower() for r in new_rows}
        preserved = [g for g in existing_gems if g.get("Place Name","").lower() not in new_names]
        final = new_rows + preserved
        self._write_locations(final)
        return len(final), final

    def get_pending_gems(self):
        with open(PENDING_FILE,"r",encoding="utf-8") as f: return json.load(f)

    def _save_pending(self, p):
        with open(PENDING_FILE,"w",encoding="utf-8") as f: json.dump(p,f,indent=2,ensure_ascii=False)

    def add_pending_gem(self, data):
        pending = self.get_pending_gems()
        gid = str(uuid.uuid4())[:8]
        pending.append({"id":gid,"City":data.get("city",""),"Place Name":data.get("name",""),
            "Category":data.get("category",""),"Vibe Description":data.get("vibe",""),
            "Budget":data.get("budget",""),"Best time to visit in each season":data.get("timing",""),
            "type of location":"local hidden gem","detailed description":data.get("description",""),
            "food to try":data.get("food",""),"submitter":data.get("submitter","Anonymous"),
            "contact":data.get("contact",""),"submitted_at":datetime.now().strftime("%Y-%m-%d %H:%M"),"status":"pending"})
        self._save_pending(pending)
        return gid

    def approve_gem(self, gid):
        pending = self.get_pending_gems()
        gem = next((g for g in pending if g["id"]==gid), None)
        if not gem: raise ValueError(f"Gem '{gid}' not found.")
        self._append_location({col:gem.get(col,"") for col in CSV_COLUMNS})
        self._save_pending([g for g in pending if g["id"]!=gid])
        return gem

    def reject_gem(self, gid):
        pending = self.get_pending_gems()
        new = [g for g in pending if g["id"]!=gid]
        if len(new)==len(pending): raise ValueError(f"Gem '{gid}' not found.")
        self._save_pending(new)

    def export_csv(self):
        out = StringIO()
        w = csv.DictWriter(out, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        w.writeheader()
        for loc in self.load_locations():
            w.writerow({col:loc.get(col,"") for col in CSV_COLUMNS})
        return out.getvalue()

    def stats(self):
        locs = self.load_locations()
        gems = [l for l in locs if _is_hidden_gem(l)]
        return {"total":len(locs),"hidden_gems":len(gems),"official":len(locs)-len(gems)}
