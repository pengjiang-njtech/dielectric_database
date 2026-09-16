import sqlite3
from pathlib import Path

DB = Path(__file__).with_name("dielectric.db")
conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
print("Database:", DB)
print("Size (MB):", round(DB.stat().st_size / 1024 / 1024, 2))
print("Integrity:", conn.execute("PRAGMA integrity_check").fetchone()[0])
for table in ["compounds", "measurements", "sources", "compound_properties", "property_provenance"]:
    try:
        n = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table}: {n:,}")
    except sqlite3.Error as e:
        print(f"{table}: ERROR - {e}")
conn.close()
