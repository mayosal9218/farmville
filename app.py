from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs
import html, sqlite3

ROOT, DB = Path(__file__).parent, Path(__file__).parent / "farmledger.db"

def db():
    if not DB.exists():
        with sqlite3.connect(DB) as c:
            c.executescript((ROOT/"database/schema.sql").read_text())
            c.executescript((ROOT/"database/seed.sql").read_text())
    return sqlite3.connect(DB)

def e(s): return html.escape(str(s or ""))
def layout(body):
    return f"""<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1"><title>FarmLedger</title>
<style>body{{font:16px system-ui;max-width:960px;margin:auto;padding:20px;background:#f3f6ef;color:#203225}}header{{background:#25613c;color:white;padding:18px;border-radius:12px}}a{{color:#25613c}}header a{{color:white;margin-right:12px}}form,table,.card{{background:#fff;padding:18px;border-radius:10px;margin:16px 0;box-sizing:border-box}}label{{display:block;font-weight:bold;margin-top:10px}}input,select,textarea{{width:100%;padding:9px;box-sizing:border-box;margin-top:4px}}button{{margin-top:16px;background:#25613c;color:#fff;border:0;padding:10px 15px;border-radius:7px}}td,th{{padding:8px;text-align:left}}</style>
<header><h1>🌱 FarmLedger</h1><a href="/">Dashboard</a><a href="/activity">Activity</a><a href="/expense">Expense</a><a href="/sale">Sale</a><a href="/crop">Crop</a><a href="/livestock">Livestock</a></header>{body}"""

def choices(c, table, label):
    return "".join(f"<option value='{r[0]}'>{e(r[1])}</option>" for r in c.execute(f"SELECT id,{label} FROM {table} ORDER BY {label}"))

class App(BaseHTTPRequestHandler):
    def html(self, body):
        data=body.encode(); self.send_response(200); self.send_header("Content-Type","text/html"); self.send_header("Content-Length",len(data)); self.end_headers(); self.wfile.write(data)
    def do_GET(self):
        with db() as c:
            farms, fields, types = choices(c,"farms","name"), choices(c,"fields","name"), choices(c,"activity_types","name")
            if self.path=="/":
                rows="".join(f"<tr><td>{e(d)}</td><td>{e(x)}</td><td>{e(w)}</td></tr>" for d,x,w in c.execute("SELECT activity_date,description,worker_name FROM daily_activities ORDER BY id DESC LIMIT 10"))
                return self.html(layout(f"<main><div class=card><h2>Welcome</h2><p>Log today’s work, money, crops, and animals without SQL.</p></div><table><tr><th>Date</th><th>Recent activity</th><th>Worker</th></tr>{rows}</table></main>"))
            forms={
"/activity":f"""<h2>Daily activity</h2><form method=post><label>Farm<select name=farm_id>{farms}</select></label><label>Type<select name=activity_type_id>{types}</select></label><label>Field<select name=field_id><option value=''>None</option>{fields}</select></label><label>Date<input type=date name=activity_date required></label><label>Minutes<input type=number name=duration_minutes></label><label>Work done<textarea name=description required></textarea></label><label>Worker<input name=worker_name></label><label>Weather<input name=weather_notes></label><button>Save activity</button></form>""",
"/expense":f"""<h2>Expense</h2><form method=post><label>Farm<select name=farm_id>{farms}</select></label><label>Date<input type=date name=expense_date required></label><label>Category<input name=category required></label><label>Description<textarea name=description required></textarea></label><label>Amount<input type=number step=.01 name=amount required></label><label>Vendor<input name=vendor></label><button>Save expense</button></form>""",
"/sale":f"""<h2>Sale</h2><form method=post><label>Farm<select name=farm_id>{farms}</select></label><label>Date<input type=date name=sale_date required></label><label>Product<input name=product_name required></label><label>Quantity<input type=number step=.01 name=quantity required></label><label>Unit<input name=unit required></label><label>Total amount<input type=number step=.01 name=total_amount required></label><label>Buyer<input name=buyer></label><button>Save sale</button></form>""",
"/crop":f"""<h2>Crop</h2><form method=post><label>Field<select name=field_id>{fields}</select></label><label>Crop name<input name=crop_name required></label><label>Variety<input name=variety></label><label>Planted<input type=date name=planted_on></label><label>Expected harvest<input type=date name=expected_harvest_on></label><button>Save crop</button></form>""",
"/livestock":f"""<h2>Livestock</h2><form method=post><label>Farm<select name=farm_id>{farms}</select></label><label>Tag number<input name=tag_number></label><label>Species<input name=species required></label><label>Breed<input name=breed></label><label>Date of birth<input type=date name=born_on></label><button>Save livestock</button></form>"""}
            self.html(layout("<main>"+forms.get(self.path,"<h2>Not found</h2>")+"</main>"))
    def do_POST(self):
        raw=self.rfile.read(int(self.headers["Content-Length"])).decode()
        v={k:x[0].strip() or None for k,x in parse_qs(raw).items()}
        maps={"/activity":("daily_activities","farm_id activity_type_id field_id activity_date duration_minutes description worker_name weather_notes"),
              "/expense":("expenses","farm_id expense_date category description amount vendor"),
              "/sale":("sales","farm_id sale_date product_name quantity unit total_amount buyer"),
              "/crop":("crops","field_id crop_name variety planted_on expected_harvest_on"),
              "/livestock":("livestock","farm_id tag_number species breed born_on")}
        table, cols=maps[self.path]; cols=cols.split()
        with db() as c: c.execute(f"INSERT INTO {table} ({','.join(cols)}) VALUES ({','.join('?'*len(cols))})",[v.get(x) for x in cols]); c.commit()
        self.html(layout("<main><div class=card><h2>Saved ✓</h2><p>Your record was added. <a href='/'>Return to dashboard</a></p></div></main>"))

print("FarmLedger running at http://localhost:8000")
ThreadingHTTPServer(("127.0.0.1",8000),App).serve_forever()
