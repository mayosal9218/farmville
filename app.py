"""FarmLedger: a small local, form-based farm record app. No packages needed."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs
import html
import sqlite3

ROOT = Path(__file__).parent
DB = ROOT / "farmledger.db"

def connection():
    if not DB.exists():
        with sqlite3.connect(DB) as db:
            db.executescript((ROOT / "database" / "schema.sql").read_text(encoding="utf-8"))
            db.executescript((ROOT / "database" / "seed.sql").read_text(encoding="utf-8"))
    return sqlite3.connect(DB)

def esc(value): return html.escape(str(value or ""))
def page(title, content):
    return f"""<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>{title} · FarmLedger</title><style>
body{{font-family:system-ui,sans-serif;max-width:1000px;margin:auto;padding:24px;background:#f5f7f1;color:#1d2a1c}} header{{background:#24613b;color:white;padding:22px;border-radius:14px}}nav a{{color:white;margin-right:14px;font-weight:700}}main{{margin-top:22px}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px}}.card,form{{background:white;border-radius:12px;padding:18px;box-shadow:0 1px 4px #0002}}label{{display:block;font-weight:650;margin-top:10px}}input,select,textarea{{box-sizing:border-box;width:100%;padding:9px;margin-top:4px;border:1px solid #b8c4b3;border-radius:7px}}button{{margin-top:16px;background:#24613b;color:white;border:0;border-radius:7px;padding:10px 16px;font-weight:700;cursor:pointer}}table{{width:100%;border-collapse:collapse;background:white}}th,td{{padding:10px;text-align:left;border-bottom:1px solid #dde5da}}.notice{{background:#e1f3e5;padding:12px;border-radius:8px}}</style></head><body>
<header><h1>🌱 FarmLedger</h1><nav><a href='/'>Dashboard</a><a href='/search'>Search</a><a href='/activity'>Daily activity</a><a href='/expense'>Expense</a><a href='/sale'>Sale</a><a href='/crop'>Crop</a><a href='/livestock'>Livestock</a></nav></header><main>{content}</main></body></html>"""

def options(db, table, label):
    return "".join(f"<option value='{row[0]}'>{esc(row[1])}</option>" for row in db.execute(f"SELECT id, {label} FROM {table} ORDER BY {label}"))

class Handler(BaseHTTPRequestHandler):
    def send_html(self, body):
        data = body.encode(); self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", len(data)); self.end_headers(); self.wfile.write(data)
    def do_GET(self):
        with connection() as db:
            if self.path.startswith("/search"):
                term = parse_qs(self.path.partition("?")[2]).get("q", [""])[0].strip()
                results = []
                if term:
                    match = f"%{term}%"
                    searches = [
                        ("Activity", "SELECT activity_date, description FROM daily_activities WHERE description LIKE ? OR worker_name LIKE ?", [match, match]),
                        ("Expense", "SELECT expense_date, category || ': ' || description FROM expenses WHERE category LIKE ? OR description LIKE ? OR vendor LIKE ?", [match, match, match]),
                        ("Sale", "SELECT sale_date, product_name || ' — ' || COALESCE(buyer, '') FROM sales WHERE product_name LIKE ? OR buyer LIKE ?", [match, match]),
                        ("Crop", "SELECT COALESCE(planted_on, ''), crop_name || ' ' || COALESCE(variety, '') FROM crops WHERE crop_name LIKE ? OR variety LIKE ?", [match, match]),
                        ("Livestock", "SELECT COALESCE(born_on, ''), species || ' · tag ' || COALESCE(tag_number, '') FROM livestock WHERE species LIKE ? OR tag_number LIKE ? OR breed LIKE ?", [match, match, match])
                    ]
                    for kind, query, parameters in searches:
                        results.extend((kind, date, detail) for date, detail in db.execute(query, parameters))
                rows = "".join(f"<tr><td>{esc(kind)}</td><td>{esc(date)}</td><td>{esc(detail)}</td></tr>" for kind, date, detail in results) or ("<tr><td colspan=3>Enter a word to search your records.</td></tr>" if not term else "<tr><td colspan=3>No matching records.</td></tr>")
                form = f"<h2>Search farm records</h2><form method='get'><label>Search word or tag<input name='q' value='{esc(term)}' placeholder='water, fuel, C-104…'></label><button>Search</button></form><table><tr><th>Record type</th><th>Date</th><th>Details</th></tr>{rows}</table>"
                return self.send_html(page("Search", form))
            if self.path == "/":
                activities = db.execute("SELECT activity_date, description, worker_name FROM daily_activities ORDER BY activity_date DESC, id DESC LIMIT 8").fetchall()
                low = db.execute("SELECT name, quantity_on_hand, unit FROM low_stock").fetchall()
                rows = "".join(f"<tr><td>{esc(a)}</td><td>{esc(b)}</td><td>{esc(c)}</td></tr>" for a,b,c in activities) or "<tr><td colspan=3>No activities yet.</td></tr>"
                stock = "<br>".join(f"{esc(n)}: {q} {esc(u)}" for n,q,u in low) or "Everything is above its reorder level."
                return self.send_html(page("Dashboard", f"<div class='grid'><div class='card'><h2>Quick start</h2><p>Choose a form above to log today’s work without writing SQL.</p></div><div class='card'><h2>Low stock</h2><p>{stock}</p></div></div><h2>Recent activities</h2><table><tr><th>Date</th><th>Work done</th><th>Worker</th></tr>{rows}</table>"))
            farms = options(db, "farms", "name"); fields = options(db, "fields", "name"); types = options(db, "activity_types", "name")
            forms = {
              "/activity": f"<h2>Log daily activity</h2><form method='post'><label>Farm<select name='farm_id'>{farms}</select></label><label>Activity type<select name='activity_type_id'>{types}</select></label><label>Field (optional)<select name='field_id'><option value=''>Not field-specific</option>{fields}</select></label><label>Date<input type='date' name='activity_date' required></label><label>Minutes spent<input type='number' min='0' name='duration_minutes'></label><label>What did you do?<textarea name='description' required></textarea></label><label>Worker name<input name='worker_name'></label><label>Weather notes<input name='weather_notes'></label><button>Save activity</button></form>",
              "/expense": f"<h2>Add expense</h2><form method='post'><label>Farm<select name='farm_id'>{farms}</select></label><label>Date<input type='date' name='expense_date' required></label><label>Category<input name='category' placeholder='Seed, fuel, repair…' required></label><label>Description<textarea name='description' required></textarea></label><label>Amount<input type='number' min='0' step='0.01' name='amount' required></label><label>Vendor<input name='vendor'></label><button>Save expense</button></form>",
              "/sale": f"<h2>Record sale</h2><form method='post'><label>Farm<select name='farm_id'>{farms}</select></label><label>Date<input type='date' name='sale_date' required></label><label>Product<input name='product_name' required></label><label>Quantity<input type='number' min='0.01' step='0.01' name='quantity' required></label><label>Unit<input name='unit' placeholder='kg, dozen, head…' required></label><label>Total received<input type='number' min='0' step='0.01' name='total_amount' required></label><label>Buyer<input name='buyer'></label><button>Save sale</button></form>",
              "/crop": f"<h2>Add crop</h2><form method='post'><label>Field<select name='field_id'>{fields}</select></label><label>Crop name<input name='crop_name' required></label><label>Variety<input name='variety'></label><label>Planted date<input type='date' name='planted_on'></label><label>Expected harvest<input type='date' name='expected_harvest_on'></label><button>Save crop</button></form>",
              "/livestock": f"<h2>Add livestock</h2><form method='post'><label>Farm<select name='farm_id'>{farms}</select></label><label>Tag number<input name='tag_number'></label><label>Species<input name='species' placeholder='Cow, chicken…' required></label><label>Breed<input name='breed'></label><label>Date of birth<input type='date' name='born_on'></label><button>Save livestock</button></form>"
            }
            return self.send_html(page("FarmLedger", forms.get(self.path, "<h2>Page not found</h2>")))
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0)); values = {k:v[0].strip() for k,v in parse_qs(self.rfile.read(length).decode()).items()}
        mapping = {
          "/activity": ("daily_activities", ["farm_id","activity_type_id","field_id","activity_date","duration_minutes","description","worker_name","weather_notes"]),
          "/expense": ("expenses", ["farm_id","expense_date","category","description","amount","vendor"]),
          "/sale": ("sales", ["farm_id","sale_date","product_name","quantity","unit","total_amount","buyer"]),
          "/crop": ("crops", ["field_id","crop_name","variety","planted_on","expected_harvest_on"]),
          "/livestock": ("livestock", ["farm_id","tag_number","species","breed","born_on"])
        }
        if self.path not in mapping: return self.send_html(page("Error", "<p>Unknown form.</p>"))
        table, columns = mapping[self.path]; data = [values.get(c) or None for c in columns]
        with connection() as db: db.execute(f"INSERT INTO {table} ({','.join(columns)}) VALUES ({','.join('?'*len(columns))})", data); db.commit()
        self.send_html(page("Saved", "<div class='notice'><strong>Saved.</strong> Your farm record has been added.</div><p><a href='/'>Return to dashboard</a> or <a href='" + self.path + "'>add another</a>.</p>"))

if __name__ == "__main__":
    print("Open http://localhost:8000 in your browser. Press Ctrl+C here to stop the app.")
    ThreadingHTTPServer(("127.0.0.1", 8000), Handler).serve_forever()

