#!/usr/bin/env python3
"""UzMorphAnalyser xatolarining qo'lda tekshirilgan 50 ta misoli -> output/stemmer_xatolari.csv.

Har bir misol uchun: korpusdagi chastota, analizator javobi, to'g'ri lemma (qo'lda aniqlangan),
xato turi va pipeline'dagi tuzatish natijasi (avtomatik lug'at tekshiruvi yoki qo'lda tuzatish).
"""
import csv
import sys
from collections import Counter

import extract_terms as et
from uztext import normalize, segments

T_CHI = "-chi agentlik qo'shimchasi kesilgan"
T_NOMA = "-noma (-ma) qo'shimchasi kesilgan"
T_ALT = "k/q ~ g/gʻ almashinuvi tiklanmagan"
T_OVER = "asosning oxiri qo'shimcha deb kesilgan"
T_VERB = "ot/sifat fe'l deb tahlil qilingan"
T_CAUS = "orttirma nisbat (-ir) tashlab yuborilgan"
T_DERIV = "so'z yasovchi qo'shimcha kesilgan (boshqa so'z)"

# so'z -> (to'g'ri lemma, xato turi); har biri korpus kontekstida qo'lda tekshirilgan
EXAMPLES = {
    "ahdlashuvchi": ("ahdlashuvchi", T_CHI), "ishtirokchi": ("ishtirokchi", T_CHI),
    "istilochi": ("istilochi", T_CHI), "ayblanuvchi": ("ayblanuvchi", T_CHI),
    "iltimosnoma": ("iltimosnoma", T_NOMA), "bayonnoma": ("bayonnoma", T_NOMA),
    "guvohnoma": ("guvohnoma", T_NOMA), "xabarnoma": ("xabarnoma", T_NOMA), "soʻrovnoma": ("soʻrovnoma", T_NOMA),
    "qonunchiligiga": ("qonunchilik", T_ALT), "vazirligi": ("vazirlik", T_ALT), "fuqaroligi": ("fuqarolik", T_ALT),
    "xavfsizligiga": ("xavfsizlik", T_ALT), "sogʻligʻi": ("sogʻliq", T_ALT), "yorligʻi": ("yorliq", T_ALT),
    "qoʻmitaga": ("qoʻmita", T_OVER), "modda": ("modda", T_OVER), "yordam": ("yordam", T_OVER),
    "taʼlim": ("taʼlim", T_OVER), "muomala": ("muomala", T_OVER), "sudlov": ("sudlov", T_OVER),
    "masala": ("masala", T_OVER), "muhim": ("muhim", T_OVER), "pochta": ("pochta", T_OVER),
    "shaxsini": ("shaxs", T_OVER), "tomoni": ("tomon", T_OVER), "majlisi": ("majlis", T_OVER),
    "hukmi": ("hukm", T_OVER), "dushman": ("dushman", T_OVER), "maqsadi": ("maqsad", T_OVER),
    "sodir": ("sodir", T_VERB), "protokol": ("protokol", T_VERB), "vakil": ("vakil", T_VERB),
    "muassasa": ("muassasa", T_VERB), "sanitar": ("sanitar", T_VERB), "javobgar": ("javobgar", T_VERB),
    "ruxsat": ("ruxsat", T_VERB), "zarar": ("zarar", T_VERB), "organlari": ("organ", T_VERB),
    "erkin": ("erkin", T_VERB), "tartib": ("tartib", T_VERB), "taʼqib": ("taʼqib", T_VERB),
    "kotib": ("kotib", T_VERB), "markaz": ("markaz", T_VERB), "qizil": ("qizil", T_VERB),
    "yuridik": ("yuridik", T_VERB), "tarkib": ("tarkib", T_VERB),
    "oshirish": ("oshir", T_CAUS),
    "qilmish": ("qilmish", T_DERIV), "xavfsizligi": ("xavfsizlik", T_DERIV),
}


def main():
    docs = list(csv.DictReader(et.SOURCES.open(encoding="utf-8")))
    vocab = et.build_vocab(docs)
    lem = et.CachedLemmatizer(vocab)
    et.load_raw_cache(lem)
    freq = Counter()
    for d in docs:
        for line in (et.ROOT / d["fayl"]).read_text(encoding="utf-8").splitlines():
            for seg in segments(normalize(line)):
                freq.update(t for t, _, _ in seg)
    rows, bad = [], []
    for w, (good, kind) in EXAMPLES.items():
        raw_l, raw_p = lem.raw(w)
        fin, _, how = lem.analyse(w)
        if raw_l == good:
            bad.append(f"{w}: analizator to'g'ri ({raw_l})")
        if fin != good:
            bad.append(f"{w}: pipeline {fin} != {good}")
        rows.append({"soz": w, "korpusdagi_chastota": freq[w], "analizator_lemmasi": raw_l, "analizator_pos": raw_p,
                     "togri_lemma": good, "xato_turi": kind,
                     "tuzatish": {"qolda": "qo'lda (lemma_tuzatishlar.csv)", "": "—"}.get(how, f"avtomatik: {how}"),
                     "pipeline_natijasi": fin})
    rows.sort(key=lambda r: (r["xato_turi"], -r["korpusdagi_chastota"]))
    et.OUT.mkdir(exist_ok=True)
    with (et.OUT / "stemmer_xatolari.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print(len(rows), "misol;", Counter(r["xato_turi"] for r in rows))
    if bad:
        print("TEKSHIRUV XATOLARI:\n  " + "\n  ".join(bad)); sys.exit(1)


if __name__ == "__main__":
    main()
