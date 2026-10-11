#!/usr/bin/env python3
"""sources.csv bo'yicha korpus statistikasi: soha, matn_maqomi, qatlam kesimida (data/meta/korpus_statistika.csv)."""
import csv
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
rows = list(csv.DictReader((ROOT / "data/meta/sources.csv").open(encoding="utf-8")))
total = sum(int(r["so'zlar_soni"]) for r in rows)
out = []
for col in ["soha", "matn_maqomi", "qatlam"]:
    agg = defaultdict(lambda: [0, 0])
    for r in rows:
        agg[r[col]][0] += 1
        agg[r[col]][1] += int(r["so'zlar_soni"])
    for k, (n, w) in sorted(agg.items(), key=lambda x: -x[1][1]):
        out.append({"kesim": col, "qiymat": k, "hujjatlar": n, "sozlar": w, "ulush_%": round(100 * w / total, 1)})
out.append({"kesim": "jami", "qiymat": "", "hujjatlar": len(rows), "sozlar": total, "ulush_%": 100.0})
with (ROOT / "data/meta/korpus_statistika.csv").open("w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
for o in out:
    print(f"{o['kesim']:12} {o['qiymat']:24} {o['hujjatlar']:>3} {o['sozlar']:>8} {o['ulush_%']:>6}")
