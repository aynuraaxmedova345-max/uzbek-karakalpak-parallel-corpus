#!/usr/bin/env python3
"""Umumiy o'zbek tili reference korpusi uchun so'zshakllar chastotasi.

Manbalar (ikkalasi ham CC BY 4.0, lotin yozuvi):
  1. Multilingual Open Text (MOT), VOA O'zbek xizmati (amerikaovozi.com) maqolalari
     https://github.com/bltlab/mot  ->  releases/latest/download/uzb_amerikaovozi.tgz
  2. Uzbek Corpus Sample (100 000 jumla)  https://github.com/elmurod1202/Uzbek-Corpus-Sample

Ishlatish:
    python scripts/build_reference.py --voa <.../uzb_amerikaovozi/article> --sample <.../uzbek_corpus.txt>

Natija: data/reference/ref_word_freq.tsv.gz (so'zshakl, chastota, manba bo'yicha) va ref_meta.json.
Xom matnlar repoga qo'shilmaydi (hajmi katta), faqat chastotalar saqlanadi.
"""

import argparse
import gzip
import json
import os
import re
from collections import Counter
from pathlib import Path

from uztext import normalize, segments

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "reference"
CYR_RE = re.compile(r"[Ѐ-ӿ]")
LAT_RE = re.compile(r"[A-Za-z]")


def is_latin(text):
    cyr, lat = len(CYR_RE.findall(text)), len(LAT_RE.findall(text))
    return lat > 0 and cyr / (cyr + lat) < 0.01


def count(texts):
    c = Counter()
    for t in texts:
        for line in normalize(t).splitlines():
            for seg in segments(line):
                c.update(tok for tok, _, _ in seg)
    return c


def voa_texts(d, stats):
    for f in sorted(os.listdir(d)):
        j = json.load(open(os.path.join(d, f), encoding="utf-8"))
        t = "\n".join(j.get("paragraphs") or [])
        if is_latin(t):
            stats["voa_maqolalar"] += 1
            yield t
        else:
            stats["voa_chiqarilgan_lotin_emas"] += 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--voa", required=True)
    ap.add_argument("--sample", required=True)
    a = ap.parse_args()
    stats = Counter()
    voa = count(voa_texts(a.voa, stats))
    lines = [ln for ln in open(a.sample, encoding="utf-8").read().splitlines() if ln.strip()]
    uniq = list(dict.fromkeys(lines))  # takroriy jumlalar bir marta olinadi
    stats["sample_jumlalar"], stats["sample_takror_chiqarilgan"] = len(uniq), len(lines) - len(uniq)
    sample = count(l for l in uniq if is_latin(l))
    OUT.mkdir(parents=True, exist_ok=True)
    with gzip.open(OUT / "ref_word_freq.tsv.gz", "wt", encoding="utf-8") as f:
        f.write("soz\tjami\tvoa\tsample\n")
        for w, n in (voa + sample).most_common():
            f.write(f"{w}\t{n}\t{voa[w]}\t{sample[w]}\n")
    meta = {
        "manbalar": [
            {"nomi": "MOT (VOA O'zbek xizmati, amerikaovozi.com), maqolalar", "litsenziya": "CC BY 4.0",
             "url": "https://github.com/bltlab/mot/releases/latest/download/uzb_amerikaovozi.tgz",
             "tokenlar": sum(voa.values())},
            {"nomi": "Uzbek Corpus Sample", "litsenziya": "CC BY 4.0",
             "url": "https://github.com/elmurod1202/Uzbek-Corpus-Sample", "commit": "6286141e04196c627d00df156a4004d1f0dc8b46",
             "tokenlar": sum(sample.values())},
        ],
        "jami_tokenlar": sum((voa + sample).values()),
        "turli_sozshakllar": len(voa + sample),
        **stats,
    }
    (OUT / "ref_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
