#!/usr/bin/env python3
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "database" / "dielectric_database.db"
OUT = ROOT / "data"
OUT.mkdir(parents=True, exist_ok=True)

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row

def dump(name, payload):
    with (OUT / name).open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"), allow_nan=False)

sources = [dict(r) for r in con.execute("SELECT id,source_key,source_name,source_type FROM sources ORDER BY id")]

compound_sql = """
SELECT c.id,c.name_en,c.name_cn,c.cas,
       p.smiles,p.mass_g_mol,p.dipole_moment_d,p.hbond_acceptors,p.hbond_donors,
       p.logp,p.polar_surface_area_a2,p.polarizability_a3,p.molar_volume_cm3_mol,
       p.refractive_index,p.refractive_index_temperature_c,p.melting_point_c,
       p.boiling_point_c,p.density_g_cm3,p.density_temperature_c,
       p.viscosity_mpas,p.viscosity_temperature_c,p.molecular_formula,
       COUNT(DISTINCT m.id) AS measurement_count
FROM compounds c
LEFT JOIN compound_properties p ON p.compound_id=c.id
LEFT JOIN measurements m ON m.compound_id=c.id OR m.component1_id=c.id OR m.component2_id=c.id
GROUP BY c.id ORDER BY c.name_en COLLATE NOCASE
"""
compounds = [dict(r) for r in con.execute(compound_sql)]

measurement_columns = [
    "id","sample_type","compound_id","component1_id","component2_id","x1","x2",
    "composition_basis","temperature_c","frequency_ghz","epsilon_static","epsilon_real",
    "epsilon_imag","data_kind","source_id","source_detail","doi","notes","data_quality","method"
]
measurement_sql = "SELECT " + ",".join(measurement_columns) + " FROM measurements ORDER BY id"
measurement_rows = [list(r) for r in con.execute(measurement_sql)]

prov_columns = [
    "compound_id","property_name","value","unit","temperature_c","pressure_kpa","data_type",
    "source_type","source_name","doi","reference","original_value","original_unit","notes"
]
prov_sql = "SELECT " + ",".join(prov_columns) + " FROM property_provenance ORDER BY compound_id,property_name,id"
prov_rows = [list(r) for r in con.execute(prov_sql)]

source_counts = [dict(r) for r in con.execute("""
SELECT s.id,s.source_key,s.source_name,s.source_type,COUNT(m.id) AS count
FROM sources s LEFT JOIN measurements m ON m.source_id=s.id
GROUP BY s.id ORDER BY count DESC
""")]

summary = dict(con.execute("""
SELECT COUNT(*) AS measurements,
SUM(sample_type='pure') AS pure_count,
SUM(sample_type='mixture') AS mixture_count,
COUNT(DISTINCT source_id) AS used_sources,
MIN(temperature_c) AS temperature_min,
MAX(temperature_c) AS temperature_max,
MIN(frequency_ghz) AS frequency_min,
MAX(frequency_ghz) AS frequency_max
FROM measurements
""").fetchone())
summary["compounds"] = len(compounds)
summary["sources_total"] = len(sources)

dump("meta.json", {"summary": summary, "sources": sources, "source_counts": source_counts})
dump("compounds.json", compounds)
dump("measurements.json", {"columns": measurement_columns, "rows": measurement_rows})
dump("provenance.json", {"columns": prov_columns, "rows": prov_rows})
con.close()
print(json.dumps({"compounds": len(compounds), "measurements": len(measurement_rows), "provenance": len(prov_rows)}, ensure_ascii=False))
