from pathlib import Path
import sqlite3
root = Path(__file__).parent
with sqlite3.connect(root / "farmledger.db") as db:
    db.executescript((root / "database" / "schema.sql").read_text())
    db.executescript((root / "database" / "seed.sql").read_text())
print("FarmLedger database created.")
