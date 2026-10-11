#!/usr/bin/env python3
"""Termin nomzodlarini ajratish (2-bosqich).

  * 1–4 so'zli n-grammlar, tinish belgisi/raqamdan o'tmaydi;
  * chegaradagi (birinchi/oxirgi) so'z yordamchi so'z bo'lmasligi kerak (data/meta/stopwords_uz.txt),
    birinchi so'z ot/sifat, oxirgi so'z ot (yoki -sh/-uv harakat nomi) bo'lishi kerak (UzMorphAnalyser POS);
  * variantlar lemmalar ketma-ketligi bo'yicha guruhlanadi (UzMorphAnalyser + lemma_tuzatishlar.csv);
  * ko'p so'zlilar: C-value (Frantzi va b., 2000), bir so'zlilar: reference korpusga nisbatan
    log-likelihood (Dunning G², faqat korpusda nisbatan ko'p uchraganlar);
  * natija: output/candidates.xlsx (+ output/candidates.csv).

Ishlatish:  python scripts/extract_terms.py [--min-freq 3]
"""

import argparse
import csv
import gzip
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

from uztext import Lemmatizer, normalize, segments

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "data" / "meta" / "sources.csv"
STOP = ROOT / "data" / "meta" / "stopwords_uz.txt"
REF = ROOT / "data" / "reference" / "ref_word_freq.tsv.gz"
RAW_CACHE = ROOT / "data" / "reference" / "raw_lemmas.tsv.gz"
OUT = ROOT / "output"
STATUSES = ["norasmiy_tarjima", "asl_ozbekcha", "aniqlanmagan"]

MODDA_RE = re.compile(r"^\s*(\d+)\s*-\s*modda", re.IGNORECASE)
ROMAN_RE = re.compile(r"^[ivxlc]+$")
VERBAL_NOUN_RE = re.compile(r"(sh|uv)(i|ni|ga|da|dan|ning|dagi|lar|lari|larini|larga)?$")
CASE_END_RE = re.compile(r"(ning|ni|ga|ka|qa|da|dan|dagi|gacha|niki)$")
LL_MIN = 10.83  # p < 0.001
LIGHT_VERBS = {"et", "qil", "boʻl", "ol", "ber", "tur", "tut", "kel", "koʻr", "chiq", "qol", "bor", "ket", "yur", "de"}


def load_stop():
    return {ln.strip() for ln in STOP.read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.startswith("#")}


def load_raw_cache(lem):
    if RAW_CACHE.exists():
        with gzip.open(RAW_CACHE, "rt", encoding="utf-8") as f:
            for ln in f:
                w, l, p = ln.rstrip("\n").split("\t")
                lem.raw_cache[w] = (l, p)


def save_raw_cache(lem):
    with gzip.open(RAW_CACHE, "wt", encoding="utf-8") as f:
        for w, (l, p) in sorted(lem.raw_cache.items()):
            f.write(f"{w}\t{l}\t{p}\n")


class CachedLemmatizer(Lemmatizer):
    """Analizator javoblarini diskda keshlaydi (reference korpusning 270 mingdan ortiq so'zshakli uchun)."""

    def __init__(self, vocab=None):
        super().__init__(vocab)
        self.raw_cache = {}

    def raw(self, word):
        if word not in self.raw_cache:
            try:
                self.raw_cache[word] = super().raw(word)
            except Exception:
                self.raw_cache[word] = (word, "")
        return self.raw_cache[word]


def read_ref():
    with gzip.open(REF, "rt", encoding="utf-8") as f:
        next(f)
        for ln in f:
            w, n = ln.split("\t")[:2]
            yield w, int(n)


def build_vocab(docs):
    """Lemma tekshiruvi uchun lug'at: reference + korpus so'zshakllari chastotasi."""
    v = Counter(dict(read_ref()))
    for d in docs:
        for line in (ROOT / d["fayl"]).read_text(encoding="utf-8").splitlines():
            for seg in segments(normalize(line)):
                v.update(t for t, _, _ in seg)
    return v


def single_ok(tok, lemma, pos, stop):
    """Bir so'zli nomzod va LL hisobi uchun so'z (ikkala korpusda bir xil)."""
    if len(tok) < 3 or not ok_token(tok) or tok in stop or lemma in stop:
        return False
    if pos == "VERB" and lemma in LIGHT_VERBS:
        return False
    return nounlike(tok, pos, allow_adj=True)


def ok_token(tok):
    return len(tok) >= 2 and not ROMAN_RE.match(tok)


def nounlike(tok, pos, allow_adj):
    if pos == "VERB":
        return bool(VERBAL_NOUN_RE.search(tok))
    return pos in ("NOUN", "NUM", "", "Undefined") or (allow_adj and pos == "ADJ")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-freq", type=int, default=3)
    ap.add_argument("--max-n", type=int, default=6)
    args = ap.parse_args()
    stop = load_stop()
    docs = list(csv.DictReader(SOURCES.open(encoding="utf-8")))
    vocab = build_vocab(docs)
    lem = CachedLemmatizer(vocab)
    load_raw_cache(lem)

    occ = defaultdict(list)          # key -> [(doc_i, line_i, start, end, modda)]
    surf = defaultdict(Counter)      # key -> sirt shakllar
    surf_pos = {}                    # (key, sirt shakl) -> POS teglari
    target_lemmas = Counter()
    target_tokens = 0
    lines_by_doc = []
    for di, d in enumerate(docs):
        lines = (ROOT / d["fayl"]).read_text(encoding="utf-8").splitlines()
        lines_by_doc.append(lines)
        modda = ""
        for li, line in enumerate(lines):
            norm = normalize(line)
            m = MODDA_RE.match(norm)
            if m:
                modda = f"{m.group(1)}-modda"
            for seg in segments(norm):
                info = [(t, *lem(t)) for t, _, _ in seg]   # (token, lemma, pos)
                target_tokens += len(seg)
                target_lemmas.update(l for t, l, p in info if single_ok(t, l, p, stop))
                for n in range(1, args.max_n + 1):
                    for i in range(len(seg) - n + 1):
                        g = info[i:i + n]
                        if not all(ok_token(t) for t, _, _ in g):
                            continue
                        (t0, l0, p0), (tn, ln_, pn) = g[0], g[-1]
                        if t0 in stop or tn in stop or l0 in stop or ln_ in stop:
                            continue
                        if n == 1:
                            if not single_ok(t0, l0, p0, stop):
                                continue
                        elif not (nounlike(t0, p0, allow_adj=True) and nounlike(tn, pn, allow_adj=False)):
                            continue
                        key = tuple(l for _, l, _ in g)
                        occ[key].append((di, li, seg[i][1], seg[i + n - 1][2], modda))
                        sv = " ".join(t for t, _, _ in g)
                        surf[key][sv] += 1
                        surf_pos.setdefault((key, sv), tuple(p for _, _, p in g))

    # Reference korpus lemmalari
    ref_lemmas, ref_tokens = Counter(), 0
    for w, n in read_ref():
        ref_tokens += n
        l, p = lem(w)
        if single_ok(w, l, p, stop):
            ref_lemmas[l] += n
    save_raw_cache(lem)

    has_modda = [any(MODDA_RE.match(normalize(l)) for l in lines) for lines in lines_by_doc]
    freq = {k: len(v) for k, v in occ.items()}
    multi = {k for k, f in freq.items() if len(k) > 1 and f >= args.min_freq}
    single = {k for k, f in freq.items() if len(k) == 1 and f >= args.min_freq}

    # C-value
    nested_in = defaultdict(list)
    for b in multi:
        for n in range(2, len(b)):
            for i in range(len(b) - n + 1):
                a = b[i:i + n]
                if a in multi:
                    nested_in[a].append(b)
    scores = {}
    for a in multi:
        bs = set(nested_in[a])
        f = freq[a] - (sum(freq[b] for b in bs) / len(bs) if bs else 0)
        scores[a] = ("C-value", math.log2(len(a)) * f)

    # Log-likelihood
    c, d = target_tokens, ref_tokens
    for k in single:
        a, b = target_lemmas[k[0]], ref_lemmas[k[0]]
        if a / c <= b / d:
            continue
        e1, e2 = c * (a + b) / (c + d), d * (a + b) / (c + d)
        ll = 2 * (a * math.log(a / e1) + (b * math.log(b / e2) if b else 0))
        if ll >= LL_MIN:
            scores[k] = ("LL", ll)
    ll_failed = single - set(scores)

    # Uzunroq nomzod ichida kelish ulushi (bo'lak tekshiruvi uchun), satr darajasida
    cand = multi | single
    spans = defaultdict(list)
    for k in cand:
        for di, li, st, en, _ in occ[k]:
            spans[(di, li)].append((st, en))
    nested_occ = Counter()
    for k in cand:
        for di, li, st, en, _ in occ[k]:
            if any(a <= st and b >= en and (a, b) != (st, en) for a, b in spans[(di, li)]):
                nested_occ[k] += 1

    # Kontekst belgilari: bosh harf, qisqartma, ta'rif va qo'shtirnoq
    DEF_RE = re.compile(r"deganda|deb ataladi|deb yuritiladi|deb nomlanadi|tushuniladi|atamasi|degan ibora", re.I)
    feats = {}
    for k in cand:
        cap = upper = dfn = quo = 0
        for di, li, st, en, _ in occ[k]:
            line = lines_by_doc[di][li]
            words = line[st:en].split()
            cap += all(w[:1].isupper() for w in words)
            upper += all(w.isupper() and len(w) >= 2 for w in words)
            dfn += bool(DEF_RE.search(line))
            quo += line[max(0, st - 1):st] in "“«\"„" and st > 0
        f = len(occ[k])
        feats[k] = {"ichida_ulush": round(nested_occ[k] / f, 3), "bosh_harf_ulush": round(cap / f, 3),
                    "qisqartma_ulush": round(upper / f, 3), "tarif_kontekst": dfn, "qoshtirnoq": quo}

    maxs = {t: max(s for tt, s in scores.values() if tt == t) for t in ("C-value", "LL")}
    for k in ll_failed:
        a, b = target_lemmas[k[0]], ref_lemmas[k[0]]
        scores[k] = ("LL_otmadi", 0.0)
    rows = []
    for k, (stype, score) in scores.items():
        o = occ[k]
        variants = surf[k].most_common()
        base = [v for v, _ in variants if not CASE_END_RE.search(v.split()[-1])]
        term = base[0] if base else variants[0][0]
        if len(k) == 1 and k[0] in surf[k]:
            term = k[0]                    # bir so'zli: lemma matnda uchrasa, o'zi
        doc_ids = Counter(di for di, *_ in o)
        soha = Counter(docs[di]["soha"] for di, *_ in o)
        status = Counter(docs[di]["matn_maqomi"] for di, *_ in o)
        # kontekstlar: imkon qadar turli hujjatlardan va matni takrorlanmaydigan
        def snippet(x):
            di, li, st, en, modda = x
            line = lines_by_doc[di][li]
            left, right = max(0, st - 70), min(len(line), en + 70)
            return (("…" if left else "") + line[left:st] + "«" + line[st:en] + "»" + line[en:right]
                    + ("…" if right < len(line) else ""))
        ctx, seen_docs, seen_txt = [], set(), set()
        for pass_ in (0, 1):
            for x in o:
                if len(ctx) == 3:
                    break
                txt = snippet(x)
                if txt in seen_txt or (pass_ == 0 and x[0] in seen_docs):
                    continue
                seen_docs.add(x[0]); seen_txt.add(txt)
                where = x[4] or ("kirish qismi" if has_modda[x[0]] else "—")
                ctx.append(f"[{Path(docs[x[0]]['fayl']).name} | {where}] {txt}")
        row = {
            "termin": term, "lemmalar": " ".join(k), "sozlar_soni": len(k),
            "variantlar": "; ".join(f"{v} ({n})" for v, n in variants),
            "chastota": freq[k], "hujjatlar_soni": len(doc_ids),
            "sohalar": "; ".join(f"{s}:{n}" for s, n in soha.most_common()),
            **{f"f_{s}": status[s] for s in STATUSES},
            "ball": round(score, 2), "ball_turi": stype,
            "norm_ball": round(score / maxs[stype], 4) if stype in maxs else 0.0,
            "pos": " ".join(surf_pos[(k, variants[0][0])]),
            "ref_ipm": round(ref_lemmas[k[0]] / ref_tokens * 1e6, 2) if len(k) == 1 else "",
            "korpus_ipm": round(target_lemmas[k[0]] / target_tokens * 1e6, 2) if len(k) == 1 else "",
            **feats[k],
        }
        if stype == "LL":
            row["ref_chastota"] = ref_lemmas[k[0]]
        for i in range(3):
            row[f"kontekst_{i + 1}"] = ctx[i] if i < len(ctx) else ""
        row["holat"] = ""
        rows.append(row)
    rows.sort(key=lambda r: (-r["norm_ball"], -r["chastota"]))
    for i, r in enumerate(rows, 1):
        r["orin"] = i

    cols = ["orin", "termin", "variantlar", "chastota", "hujjatlar_soni", "sohalar",
            *[f"f_{s}" for s in STATUSES], "ball", "ball_turi", "norm_ball", "sozlar_soni", "lemmalar",
            "ref_chastota", "kontekst_1", "kontekst_2", "kontekst_3", "holat"]
    meta = {
        "korpus_tokenlari": target_tokens, "reference_tokenlari": ref_tokens,
        "min_chastota": args.min_freq, "LL_chegara": LL_MIN,
        "nomzodlar_kop_sozli": sum(1 for r in rows if r["sozlar_soni"] > 1),
        "nomzodlar_bir_sozli": sum(1 for r in rows if r["sozlar_soni"] == 1),
        "max_n": args.max_n, "LL_otmagan_bir_sozli": len(ll_failed),
        "C_value_manfiy_yoki_nol": sum(1 for r in rows if r["ball_turi"] == "C-value" and r["ball"] <= 0),
    }
    OUT.mkdir(exist_ok=True)
    with (OUT / "candidates.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)
    write_xlsx(rows, cols, meta)
    with gzip.open(OUT / "candidates_full.json.gz", "wt", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False)
    (OUT / "candidates_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False))


def write_xlsx(rows, cols, meta):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    widths = {"termin": 34, "variantlar": 40, "sohalar": 30, "kontekst_1": 70, "kontekst_2": 70, "kontekst_3": 70,
              "lemmalar": 28, "holat": 14}
    for title, data in [("nomzodlar", rows), ("top100", rows[:100])]:
        ws = wb.active if title == "nomzodlar" else wb.create_sheet(title)
        ws.title = title
        ws.append(cols)
        for c in ws[1]:
            c.font = Font(bold=True)
        for r in data:
            ws.append([r.get(c, "") for c in cols])
        for i, c in enumerate(cols, 1):
            ws.column_dimensions[get_column_letter(i)].width = widths.get(c, 11)
        ws.freeze_panes = "C2"
        ws.auto_filter.ref = ws.dimensions
    for sheet, path in [("stemmer_xatolari", OUT / "stemmer_xatolari.csv"),
                        ("lemma_tuzatishlar", ROOT / "data" / "meta" / "lemma_tuzatishlar.csv")]:
        if path.exists():
            ws = wb.create_sheet(sheet)
            for r in csv.reader(path.open(encoding="utf-8")):
                ws.append(r)
            for c in ws[1]:
                c.font = Font(bold=True)
            for i in range(1, ws.max_column + 1):
                ws.column_dimensions[get_column_letter(i)].width = 22
    ws = wb.create_sheet("metod")
    for k, v in [
        ("Nomzodlar", "1–4 so'zli n-grammlar; tinish belgisi va raqamlardan o'tmaydi"),
        ("Chegaralar", "birinchi/oxirgi so'z data/meta/stopwords_uz.txt da yo'q; birinchi — ot/sifat, oxirgi — ot yoki -sh/-uv harakat nomi"),
        ("Lemmatizatsiya", "UzMorphAnalyser 0.0.22 + data/meta/lemma_tuzatishlar.csv (qo'lda tekshirilgan)"),
        ("Ko'p so'zlilar balli", "C-value = log2|a|·(f(a) − ichiga olgan uzunroq nomzodlar chastotasining o'rtachasi)"),
        ("Bir so'zlilar balli", "Dunning log-likelihood (G²), reference korpusga nisbatan; faqat korpusda nisbatan ko'p uchraganlar, G² ≥ 10.83"),
        ("norm_ball", "ball / shu turdagi eng yuqori ball (C-value va LL ni bitta ro'yxatda tartiblash uchun)"),
        ("Reference korpus", "data/reference/ref_meta.json: VOA O'zbek (MOT) + Uzbek Corpus Sample, CC BY 4.0"),
        *[(k, v) for k, v in meta.items()],
    ]:
        ws.append([k, str(v)])
    ws.column_dimensions["A"].width = 26
    ws.column_dimensions["B"].width = 120
    wb.save(OUT / "candidates.xlsx")


if __name__ == "__main__":
    main()
