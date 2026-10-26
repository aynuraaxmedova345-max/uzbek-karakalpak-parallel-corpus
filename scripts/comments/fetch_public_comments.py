#!/usr/bin/env python3
"""GitHub'dagi ochiq datasetlardan haqiqiy o'zbekcha foydalanuvchi izohlarini yig'ish.

Manbalar (faqat odamlar yozgan izohlar; mashina tarjimasi olinmaydi):
  * google_play  - Google Play'dagi top-100 ilovaga yozilgan sharhlar
                   github.com/SanatbekMatlatipov/uzbek-sentiment-analysis
                   (Kuriyozov va b., LTC 2019) - UZ_positive.txt, UZ_negative.txt
  * restoran     - restoran sharhlari, UzABSA (Matlatipov va b., SIGUL 2024)
                   github.com/SanatbekMatlatipov/UzABSA - rest.xml, rest-manual-gold.xml

Natija: id,text,source,sentiment,dataset ustunli CSV. Uni collect_comments.py
`file` rejimiga berib, leksikon bo'yicha mos izohlarni ajratish mumkin.

  python scripts/comments/fetch_public_comments.py --out data/comments/ochiq_izohlar.csv
"""

from __future__ import annotations

import argparse
import csv
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

REPOS = {
    "uzbek-sentiment-analysis": "https://github.com/SanatbekMatlatipov/uzbek-sentiment-analysis",
    "UzABSA": "https://github.com/SanatbekMatlatipov/UzABSA",
}


def clone(url: str, dest: Path) -> Path:
    if not dest.exists():
        subprocess.run(["git", "clone", "-q", "--depth", "1", url, str(dest)], check=True)
    return dest


def google_play(repo: Path):
    for name, label in (("UZ_positive.txt", "positive"), ("UZ_negative.txt", "negative")):
        with (repo / "Datasets" / name).open(encoding="utf-8-sig", errors="replace") as fh:
            for i, line in enumerate(fh, 1):
                if line.strip():
                    yield f"gp_{label[:3]}_{i}", line.strip(), "google_play", label


def restoran(repo: Path):
    base = repo / "uzabsa-base-eval-valid"
    for path in (base / "rest.xml", base / "rest-manual-gold.xml"):
        root = ET.parse(path).getroot()
        for sent in root.iter("sentence"):
            text = (sent.findtext("text") or "").strip()
            if not text:
                continue
            pols = {o.get("polarity") for o in sent.iter("aspectCategory")} | \
                   {o.get("polarity") for o in sent.iter("aspectTerm")}
            pols.discard(None)
            label = pols.pop() if len(pols) == 1 else ("mixed" if pols else "")
            yield f"rest_{sent.get('ID') or sent.get('id')}", text, "restoran", label


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", default="data/comments/ochiq_izohlar.csv")
    p.add_argument("--workdir", help="repozitoriylar yuklanadigan papka (default: vaqtinchalik)")
    args = p.parse_args()

    work = Path(args.workdir or tempfile.mkdtemp(prefix="uz_izoh_"))
    work.mkdir(parents=True, exist_ok=True)
    sa = clone(REPOS["uzbek-sentiment-analysis"], work / "uzbek-sentiment-analysis")
    absa = clone(REPOS["UzABSA"], work / "UzABSA")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    counts: dict[str, int] = {}
    with out.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "text", "source", "sentiment", "dataset"])
        for gen, dataset in ((google_play(sa), REPOS["uzbek-sentiment-analysis"]),
                             (restoran(absa), REPOS["UzABSA"])):
            for cid, text, source, label in gen:
                key = " ".join(text.lower().split())
                if key in seen:
                    continue
                seen.add(key)
                counts[source] = counts.get(source, 0) + 1
                w.writerow([cid, text, source, label, dataset])
    print(f"Saqlandi: {out}  {counts}  jami={sum(counts.values())}", file=sys.stderr)


if __name__ == "__main__":
    main()
