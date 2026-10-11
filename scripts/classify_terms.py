#!/usr/bin/env python3
"""3-bosqich: nomzodlarni qoidalar asosida tozalash, tasniflash va yakuniy ro'yxat.

Kirish:  output/candidates_full.json.gz (extract_terms.py natijasi)
Chiqish: output/terminlar_yakuniy.xlsx, output/tables/*.xlsx, output/figures/*.png, output/stats.json

Barcha qarorlar term_lexicons.py dagi ro'yxatlar va quyidagi qoidalarga tayanadi; har bir qaror
`sabab` / `auto_sabab` ustunida qoida kodi bilan yoziladi. Qo'lda tanlash yo'q.
"""

import gzip
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

import term_lexicons as L

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output"
TABLES, FIGS = OUT / "tables", OUT / "figures"
FINAL_N, SAMPLE_N, SEED = 1000, 100, 42
NEST_MAX, MIN_F, GENERAL_IPM = 0.8, 5, 50.0
NAME_PARTS = {"qizil", "xoch", "yarim", "oy", "birlashgan", "millat"}
GEO = L.PROPER - NAME_PARTS
CASE_RE = re.compile(r"(ning|ni|ga|ka|qa|da|dan|dagi|gacha)$")
PARTICIPLE_RE = re.compile(r"(gan|kan|qan|yotgan|ayotgan|uvchi|ydigan|adigan|digan|ladigan|ilgan|ingan)$")
VERBAL_NOUN_RE = re.compile(r"(ish|sh|uv|v|moq)(i|ni|ga|da|dan|ning|lar|lari)?$")
RU_RE = re.compile(r"(siya|tsiya|ziya|sion|tsion|ment|tet|izm|ator|ura|grafiya|logiya|ent|ant|ual|onal|tiv|tik|kratiya)$")
SUFFIXES = ["lashtirish", "lashtir", "lashuvchi", "lashuv", "uvchi", "chilik", "garlik", "parvarlik", "noma", "xona",
            "dor", "kor", "gar", "chi", "lik", "liq", "siz", "viy", "iy", "li", "lash", "lov", "uv"]
SAFE_SUFFIXES = {"lik", "liq", "chi", "li", "siz", "viy", "iy", "noma", "dor", "gar", "uvchi", "lashuvchi", "chilik"}
ADJ_SINGLE_RE = re.compile(r"(iy|viy|li|ual|ial|tiv|ion|tik)$")
NOUN_IY = {"homiy", "vasiy", "depozitariy", "aholi"}
# Egalik qo'shimchasisiz ot + ot birikmasida aniqlovchi bo'la olmaydigan asosiy otlar (bo'lsa — tutashuv)
CORE_NOUNS = {"davlat", "shaxs", "hudud", "tomon", "konvensiya", "shartnoma", "pakt", "protokol", "bayonnoma",
              "qonun", "sud", "jinoyat", "huquqbuzarlik", "huquq", "ishtirokchi-davlat", "qoʻmita", "organ"}
POSSESSIVE_RE = re.compile(r"(i|si|lari|ri)$")
INNER_OK = {"boʻyicha", "toʻgʻrisidagi", "oid", "doir"}
LIGHT_FIRST = {"ol", "koʻr", "koʻrsat", "ber", "qoʻlla", "belgila", "qoldir", "chiq", "hisoblan", "boʻl", "et", "qil",
               "kirit", "tanla", "yurit", "tur"}
STATUS_TOKENS = {"norasmiy_tarjima": 138082, "asl_ozbekcha": 49607, "aniqlanmagan": 6641}  # korpus_statistika.csv


# ---------------------------------------------------------------- 1. tozalash
def clean_reason(r):
    comps, n = r["lemmalar"].split(), r["sozlar_soni"]
    if n >= 2 and r["ichida_ulush"] > NEST_MAX:
        return "bolak", f"chastotaning {r['ichida_ulush']:.0%} i uzunroq nomzod ichida (> {NEST_MAX:.0%})"
    geo = [c for c in comps if c in GEO]
    if geo:
        return "nomenklatura", f"joy/atoqli nom: {', '.join(geo)}"
    if n >= 2 and any(p <= set(comps) for p in L.NAME_PAIRS):
        return "nomenklatura", "tashkilot nomi qismi: " + " ".join(c for c in comps if c in NAME_PARTS)
    if n >= 2 and comps[-1] in L.ORG_HEADS_ALWAYS:
        return "nomenklatura", f"tashkilot nomi: «{comps[-1]}» bilan tugaydigan birikma"
    if n >= 2 and comps[-1] in L.ORG_HEADS and r["bosh_harf_ulush"] >= 0.5:
        return "nomenklatura", f"tashkilot nomi: bosh so'z «{comps[-1]}», bosh harf ulushi {r['bosh_harf_ulush']:.0%}"
    if n == 1 and (comps[0] in L.ORG_ABBR or (r["qisqartma_ulush"] >= 0.5 and len(comps[0]) <= 6)):
        return "nomenklatura", "qisqartma nom"
    if n == 1:
        if r["ball_turi"] == "LL_otmadi":
            return "umumiy_leksika", "reference korpusga nisbatan ko'p uchramaydi (G² < 10,83)"
        if (r["ref_ipm"] or 0) >= GENERAL_IPM and comps[0] not in L.LEGAL:
            return "umumiy_leksika", f"reference'da {r['ref_ipm']} ipm (≥ {GENERAL_IPM:g}), huquqiy lug'atda yo'q"
    if r["chastota"] < MIN_F:
        return "zaxira", f"f = {r['chastota']} < {MIN_F}"
    return "", ""


# ---------------------------------------------------------------- 2. termin tasnifi
def classify(r, stop=None):
    comps, words, n = r["lemmalar"].split(), r["termin"].split(), r["sozlar_soni"]
    pos = r["pos"].split()
    if len(words) != n:
        words = comps
    legal = [c for c in comps if c in L.LEGAL]
    if n == 1:
        c = comps[0]
        if c in L.LEGAL:
            if ((c in L.ADJ_WORDS and c != "ishtirokchi") or ADJ_SINGLE_RE.search(c)) and c not in NOUN_IY \
                    and not c.endswith(("lik", "liq")):
                return "shubhali", "T5: sifat — mustaqil termin emas, termin elementi"
            return "ha", "T1: huquqiy leksika lug'atida"
        if pos and pos[0] == "VERB":
            return "yo'q", "T2: fe'l / harakat nomi, mustaqil tushuncha nomi emas"
        if (r["ref_ipm"] or 0) < 1:
            return "shubhali", f"T3: korpusga xos (reference'da {r['ref_ipm']} ipm), lekin huquqiy lug'atda yo'q"
        return "yo'q", "T4: huquqiy lug'atda yo'q va korpusga xos emas"
    # ko'p so'zli: avval tuzilish bo'yicha rad etish
    short = [w for w in words if len(w) <= 2 and w not in L.CONJ]
    if short:
        return "yo'q", f"S0: qo'shimcha bo'lagi yoki juda qisqa token ({', '.join(short)})"
    bad = [w for w, c in zip(words, comps) if c in L.DETERMINERS or w in L.DETERMINERS or
           ((w in STOP or c in STOP) and w not in INNER_OK and c not in L.CONJ and w not in L.CONJ)]
    if bad:
        return "yo'q", f"S1: olmosh/belgilovchi bor ({', '.join(bad)}) — erkin birikma"
    if any(c in L.CONJ for c in comps):
        return "yo'q", "S2: teng bog'lovchi bor — ikki tushunchaning sanalishi"
    if any(c in L.MONTHS for c in comps):
        return "yo'q", "S3: sana / vaqt ifodasi"
    head_pos = pos[-1] if pos else ""
    verbal_head = (head_pos == "VERB" and bool(VERBAL_NOUN_RE.search(words[-1]))) or words[-1] == "mahrum"
    if " ".join(comps) in L.FIXED_VERBAL:
        return "ha", "V0: qat'iy fe'liy termin (ro'yxatda)"
    cased = [w for w, c in zip(words[:-1], comps[:-1]) if has_case(w, c)]
    if cased:
        genitive = [w for w in cased if w.endswith("ning")]
        if not genitive and verbal_head and n <= 3 and legal:
            return "ha", f"V1: fe'liy termin — kelishikli ot ({', '.join(cased)}) + harakat nomi, huquqiy komponent ({', '.join(legal)})"
        return "yo'q", f"S4: ichki komponent kelishikda ({', '.join(cased)}) — erkin sintaktik birikma"
    if has_case(words[-1], comps[-1]) and not verbal_head:
        return "yo'q", f"S7: ibora tugallanmagan — oxirgi so'z kelishikda ({words[-1]}), kelishiksiz varianti yo'q"
    cls = [comp_class(w, c, p) for w, c, p in zip(words, comps, (pos + [""] * n)[:n])]
    if cls[-1] == "sifat":
        return "yo'q", f"S8: bosh so'z sifat ({words[-1]}) — ibora tugallanmagan"
    for i in range(n - 1):
        if comps[i] in INNER_OK or comps[i] in ATTRIB or cls[i] != "ot":
            continue
        nxt = comps[i + 1]
        if (nxt in L.ADJ_WORDS and i + 1 < n - 1) or cls[i + 1] == "sifat":
            return "yo'q", f"S6: ikki birikma tutashuvi — ot ({words[i]}) dan keyin yangi aniqlovchi ({words[i + 1]})"
    if (cls[-1] == "ot" and cls[-2] == "ot" and comps[-2] in CORE_NOUNS and comps[-2] not in ATTRIB
            and not possessive(words[-1], comps[-1])):
        return "yo'q", f"S6: ikki birikma tutashuvi — egalik qo'shimchasiz ot + ot ({words[-2]} {words[-1]})"
    if possessive(words[0], comps[0]) and comps[0] not in ATTRIB:
        return "yo'q", f"P4: bo'lak — birinchi komponent egalikda ({words[0]}), qaratqichi tushib qolgan"
    if pos and pos[0] == "VERB" and PARTICIPLE_RE.search(words[0]):
        return "shubhali", f"P3: birinchi komponent sifatdosh ({words[0]}) — to'ldiruvchisi tushib qolgan bo'lishi mumkin"
    if n == 2 and pos and pos[0] == "VERB" and comps[0] in LIGHT_FIRST:
        return "shubhali", f"P2: birinchi komponent yordamchi fe'l harakat nomi ({words[0]}) — to'ldiruvchisi tushib qolgan bo'lak"
    if verbal_head:
        if legal:
            return "shubhali", f"V2: harakat nomi bilan tugaydigan ibora, huquqiy komponent bor ({', '.join(legal)})"
        return "yo'q", "S5: umumiy fe'liy ibora (harakat nomi bilan tugaydi, huquqiy komponentsiz)"
    participle = [w for w, p in zip(words[:-1], pos[:-1]) if p == "VERB" and PARTICIPLE_RE.search(w)]
    head = comps[-1]
    if head in L.LEGAL:
        if participle:
            return "shubhali", f"H1+P: bosh so'z huquqiy («{head}»), lekin sifatdoshli birikma ({', '.join(participle)})"
        return "ha", f"H1: bosh so'z huquqiy lug'atda («{head}»)"
    domain = [c for c in comps[:-1] if c in L.DOMAIN_MOD]
    if head in L.HEAD_GENERAL and (legal or domain):
        what = ", ".join(legal or domain)
        if participle:
            return "shubhali", f"H2+P: «{head}» + huquqiy/soha komponenti, lekin sifatdoshli birikma ({', '.join(participle)})"
        return "ha", f"H2: bosh so'z «{head}» + {'huquqiy' if legal else 'soha'} komponenti ({what})"
    if legal:
        if r["tarif_kontekst"] >= 2 and not participle:
            return "ha", f"H3: huquqiy komponent ({', '.join(legal)}) + ta'rif kontekstida {r['tarif_kontekst']} marta"
        return "shubhali", f"H4: huquqiy komponent bor ({', '.join(legal)}), bosh so'z «{head}» ro'yxatlarda yo'q"
    return "yo'q", "H5: huquqiy komponent yo'q"


# ---------------------------------------------------------------- 3. tavsif ustunlari
FALLBACK_GROUP = {
    "mulk": "huquqiy_yordam_va_jinoiy_protsess", "mulkiy": "huquqiy_yordam_va_jinoiy_protsess",
    "meros": "huquqiy_yordam_va_jinoiy_protsess", "egalik": "huquqiy_yordam_va_jinoiy_protsess",
    "dalil": "huquqiy_yordam_va_jinoiy_protsess", "layoqat": "huquqiy_yordam_va_jinoiy_protsess",
    "layoqatsiz": "huquqiy_yordam_va_jinoiy_protsess", "layoqatlilik": "huquqiy_yordam_va_jinoiy_protsess",
    "protsedura": "huquqiy_yordam_va_jinoiy_protsess", "taomil": "huquqiy_yordam_va_jinoiy_protsess",
    "tartib-taomil": "huquqiy_yordam_va_jinoiy_protsess", "protsess": "huquqiy_yordam_va_jinoiy_protsess",
    "instansiya": "huquqiy_yordam_va_jinoiy_protsess", "yurisdiksiya": "huquqiy_yordam_va_jinoiy_protsess",
    "tranzit": "huquqiy_yordam_va_jinoiy_protsess", "ekspertiza": "huquqiy_yordam_va_jinoiy_protsess",
    "reglament": "xalqaro_tashkilotlar", "kvorum": "xalqaro_tashkilotlar", "petitsiya": "xalqaro_tashkilotlar",
    "petitsiyachi": "xalqaro_tashkilotlar", "guvohnoma": "huquq_manbalari_va_hujjatlar",
    "xabarnoma": "huquq_manbalari_va_hujjatlar", "bildirishnoma": "huquq_manbalari_va_hujjatlar",
    "ishonchnoma": "huquq_manbalari_va_hujjatlar", "dalolatnoma": "huquq_manbalari_va_hujjatlar",
    "xatti-harakat": "nizolar_va_javobgarlik", "maʼmuriy": "nizolar_va_javobgarlik",
    "intizomiy": "nizolar_va_javobgarlik", "majburiyat": "huquq_manbalari_va_hujjatlar",
    "vakolat": "subyektlar", "vakolatli": "subyektlar", "gumanitar": "gumanitar_huquq",
    "mol-mulk": "huquqiy_yordam_va_jinoiy_protsess", "notarial": "huquqiy_yordam_va_jinoiy_protsess",
}


ATTRIB = (L.ADJ_WORDS | L.DOMAIN_MOD | {"manfaatdor", "istilochi", "homiy", "dushman", "fuqaro", "muayyan",
                                       "tomonlama", "inson", "bola", "odam", "gender"}) - {"davlat"}


def rem_after_lemma(word, lemma):
    if word.startswith(lemma):
        return word[len(lemma):]
    for k in (1, 2):                                # undosh almashinuvi: qonunchilik -> qonunchiligi
        if word.startswith(lemma[:-k]):
            return word[len(lemma) - k + 1:] if len(word) > len(lemma) else ""
    return None


def has_case(word, lemma):
    rem = rem_after_lemma(word, lemma)
    return bool(CASE_RE.search(rem)) if rem is not None else bool(CASE_RE.search(word))


def possessive(word, lemma):
    rem = rem_after_lemma(word, lemma)
    return bool(rem) and bool(POSSESSIVE_RE.search(rem)) and not CASE_RE.search(rem)


def group(comps):
    if "huquqiy" in comps and "yordam" in comps:
        return "huquqiy_yordam_va_jinoiy_protsess"
    for name, words in L.GROUPS:
        if any(c in words for c in comps):
            return name
    for c in comps:
        if c in FALLBACK_GROUP:
            return FALLBACK_GROUP[c]
    if comps[-1] == "huquq":                    # "X huquqi" — sub'yektiv huquq
        return "inson_huquqlari"
    if "huquq" in comps or "huquqiy" in comps:   # huquqiy tizim, xalqaro huquq ...
        return "huquq_manbalari_va_hujjatlar"
    return "boshqa"


def decompose(lemma):
    """(o'zak, yasovchi qo'shimchalar, o'zak kelib chiqishi)."""
    if "-" in lemma and lemma not in L.ETYM:          # chiziqchali: har qism alohida
        parts = [decompose(x) for x in lemma.split("-")]
        origins = {o for _, _, o in parts}
        known = origins - {"aniqlanmagan"}
        origin = "gibrid" if len(known) > 1 else "aniqlanmagan" if "aniqlanmagan" in origins else origins.pop()
        return lemma, [s for _, ss, _ in parts for s in ss], origin
    if lemma in L.ETYM:
        root, suf = lemma, []
    else:
        root, suf, found = lemma, [], None
        w, acc = lemma, []
        for _ in range(3):                         # o'zak lug'atda topilguncha ketma-ket kesish
            for s in SUFFIXES:
                if w.endswith(s) and len(w) - len(s) >= 2:
                    w, acc = w[: -len(s)], [s] + acc
                    break
            else:
                break
            if w in L.ETYM:
                found = (w, list(acc))
                break
        if found:
            root, suf = found
        else:                                      # lug'atda yo'q: faqat ishonchli qo'shimchalar
            w, acc = lemma, []
            for s in sorted(SAFE_SUFFIXES, key=len, reverse=True):
                if w.endswith(s) and len(w) - len(s) >= 3:
                    w, acc = w[: -len(s)], [s]
                    break
            root, suf = w, acc
    origin = L.ETYM.get(root) or (L.RU if RU_RE.search(lemma) or RU_RE.search(root) else "aniqlanmagan")
    return root, suf, origin


def comp_class(word, lemma, p):
    if lemma == "ishtirokchi":
        return "ot"
    if lemma in L.ADJ_WORDS or p == "ADJ" or (re.search(r"(iy|viy|li|siz)$", lemma) and lemma not in NOUN_IY):
        return "sifat"
    if p == "VERB":
        if VERBAL_NOUN_RE.search(word):
            return "harakat nomi"
        if PARTICIPLE_RE.search(word):
            return "sifatdosh"
        return "fe'l"
    if p == "NUM" and lemma in {"bir", "ikki", "uch"}:
        return "son"
    return "ot"


def describe(r):
    comps, words, n = r["lemmalar"].split(), r["termin"].split(), r["sozlar_soni"]
    pos = (r["pos"].split() + [""] * n)[:n]
    if len(words) != n:
        words = comps
    parts = [decompose(c) for c in comps]
    suf = [f"-{s} ({c})" for c, (_, ss, _) in zip(comps, parts) for s in ss]
    origins = [o for _, _, o in parts]
    known = set(origins) - {"aniqlanmagan"}
    overall = ("gibrid" if len(known) > 1 else "aniqlanmagan" if "aniqlanmagan" in origins
               else origins[0])
    if n == 1:
        c = comps[0]
        if r["qisqartma_ulush"] >= 0.5:
            tuz = "qisqartma"
        elif "-" in c or c in L.COMPOUNDS or any(m in c for m in L.COMPOUND_MARKERS):
            tuz = "qo'shma"
        elif parts[0][1]:
            tuz = "yasama"
        else:
            tuz = "sodda"
    else:
        tuz = "birikma"
    model = " + ".join(comp_class(w, c, p) for w, c, p in zip(words, comps, pos))
    return {
        "mavzuiy_guruh": group(comps), "tuzilish": tuz, "komponentlar_soni": n, "model": model,
        "yasovchi_qoshimcha": "; ".join(suf), "kelib_chiqish_komponentlar": "; ".join(
            f"{c}: {o}" for c, (_, _, o) in zip(comps, parts)),
        "kelib_chiqish": overall,
    }


# ---------------------------------------------------------------- 4. dublet klasterlari
def clusters(terms):
    syn = {}
    for i, s in enumerate(L.SYNONYMS):
        for w in s:
            syn.setdefault(w, set()).add(i)
    roots = {t["lemmalar"]: tuple(decompose(c)[0] for c in t["lemmalar"].split()) for t in terms}
    parent = list(range(len(terms)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]; i = parent[i]
        return i

    def same(a, b):
        return a == b or bool(syn.get(a, set()) & syn.get(b, set()))

    reason = {}
    by_len = defaultdict(list)
    for i, t in enumerate(terms):
        by_len[t["sozlar_soni"]].append(i)
        key = t["lemmalar"].replace("-", " ")
        by_len[("flat", key)].append(i)
    for k, idx in by_len.items():
        if isinstance(k, tuple):                       # imlo varianti: chiziqcha / probel
            for j in idx[1:]:
                parent[find(j)] = find(idx[0]); reason[find(idx[0])] = "imlo varianti"
            continue
        for a in range(len(idx)):
            for b in range(a + 1, len(idx)):
                i, j = idx[a], idx[b]
                ca, cb = terms[i]["lemmalar"].split(), terms[j]["lemmalar"].split()
                diff = [(x, y) for x, y in zip(ca, cb) if x != y]
                if not diff:
                    continue
                if all(same(x, y) for x, y in diff):
                    why = "sinonim komponent"
                elif (len(ca) > 1 and len(diff) == 1 and ca[-1] == cb[-1]
                      and roots[terms[i]["lemmalar"]] == roots[terms[j]["lemmalar"]]):
                    why = "bir o'zakli aniqlovchi varianti"   # fuqaroviy / fuqarolik huquqlar
                else:
                    continue
                ri, rj = find(i), find(j)
                if ri != rj:
                    parent[rj] = ri
                    reason[ri] = why
    groups = defaultdict(list)
    for i in range(len(terms)):
        groups[find(i)].append(i)
    out = {}
    cl = sorted((g for g in groups.values() if len(g) > 1), key=lambda g: -sum(terms[i]["chastota"] for i in g))
    for k, g in enumerate(cl, 1):
        for i in g:
            out[i] = f"D{k:03d}"
    return out, cl


# ---------------------------------------------------------------- 5. tanlanma
def stratified_sample(terms, n, seed):
    rnd = random.Random(seed)
    by = defaultdict(list)
    for t in terms:
        by[t["mavzuiy_guruh"]].append(t)
    total = len(terms)
    quota = {g: n * len(v) / total for g, v in by.items()}
    alloc = {g: int(q) for g, q in quota.items()}
    for g in sorted(quota, key=lambda g: -(quota[g] - alloc[g]))[: n - sum(alloc.values())]:
        alloc[g] += 1
    sample = []
    for g in sorted(by):
        sample += rnd.sample(by[g], min(alloc[g], len(by[g])))
    return sample, alloc


# ---------------------------------------------------------------- 6. statistika va rasmlar
def dist(terms, key, label):
    c = Counter(t[key] for t in terms)
    return [{label: k, "soni": v, "ulush_%": round(100 * v / len(terms), 1)} for k, v in c.most_common()]


def crosstab(terms, rk, ck):
    rows, cols = sorted({t[rk] for t in terms}), sorted({t[ck] for t in terms})
    c = Counter((t[rk], t[ck]) for t in terms)
    return [{rk: r, **{col: c[(r, col)] for col in cols}, "jami": sum(c[(r, col)] for col in cols)} for r in rows]


def dominant_soha(t):
    return t["sohalar"].split(":")[0]


def figures(stats, terms):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})
    FIGS.mkdir(parents=True, exist_ok=True)

    def bar(rows, key, title, fname, xlabel="Terminlar soni"):
        rows = rows[::-1]
        fig, ax = plt.subplots(figsize=(8, 0.42 * len(rows) + 1.4))
        ax.barh([r[key] for r in rows], [r["soni"] for r in rows], color="#3b6ea5")
        for i, r in enumerate(rows):
            ax.text(r["soni"], i, f" {r['soni']} ({r['ulush_%']}%)", va="center", fontsize=9)
        ax.set_title(title); ax.set_xlabel(xlabel)
        ax.spines[["top", "right"]].set_visible(False)
        ax.set_xlim(0, max(r["soni"] for r in rows) * 1.25)
        fig.tight_layout(); fig.savefig(FIGS / fname, dpi=300, bbox_inches="tight"); plt.close(fig)

    bar(stats["mavzuiy_guruh"], "mavzuiy_guruh", "Terminlarning mavzuiy guruhlar bo'yicha taqsimoti", "mavzuiy_guruh.png")
    bar(stats["tuzilish"], "tuzilish", "Terminlarning tuzilishi", "tuzilish.png")
    bar(stats["kelib_chiqish"], "kelib_chiqish", "Terminlarning kelib chiqishi", "kelib_chiqish.png")
    bar(stats["komponentlar_soni"], "komponentlar_soni", "Komponentlar soni bo'yicha taqsimot", "komponentlar_soni.png")
    bar(stats["model"][:15], "model", "Eng ko'p uchraydigan 15 ta tuzilish modeli", "model.png")

    import numpy as np
    def heat(table, rk, title, fname, value_label):
        cols = [k for k in table[0] if k not in (rk, "jami")]
        m = np.array([[row[c] for c in cols] for row in table], dtype=float)
        fig, ax = plt.subplots(figsize=(1.1 * len(cols) + 3, 0.5 * len(table) + 2))
        im = ax.imshow(m, cmap="Blues")
        ax.set_xticks(range(len(cols)), [c.replace("_", " ") for c in cols], rotation=40, ha="right")
        ax.set_yticks(range(len(table)), [row[rk].replace("_", " ") for row in table])
        for i in range(m.shape[0]):
            for j in range(m.shape[1]):
                ax.text(j, i, f"{m[i, j]:g}", ha="center", va="center", fontsize=8,
                        color="white" if m[i, j] > m.max() * 0.6 else "black")
        ax.set_title(title); fig.colorbar(im, ax=ax, label=value_label)
        fig.tight_layout(); fig.savefig(FIGS / fname, dpi=300, bbox_inches="tight"); plt.close(fig)

    heat(stats["soha_x_guruh"], "soha", "Soha × mavzuiy guruh (terminlar soni)", "soha_x_guruh.png", "terminlar soni")
    heat(stats["maqom_x_kelib_chiqish_ipm"], "kelib_chiqish",
         "Kelib chiqish × matn maqomi (1 mln so'zga qo'llanish)", "maqom_x_kelib_chiqish.png", "ipm")


# ---------------------------------------------------------------- asosiy
STOP = set()


WB_PATH = OUT / "terminlar_yakuniy.xlsx"
YES, NO = {"ha"}, {"yo'q", "yoʻq", "yo‘q", "yoq"}


def load_previous():
    """Oldingi faylda foydalanuvchi to'ldirgan qiymatlarni o'qiydi: shubhalilar qarori va tekshiruv tanlanmasi."""
    decisions, review = {}, None
    if not WB_PATH.exists():
        return decisions, review
    from openpyxl import load_workbook
    wb = load_workbook(WB_PATH, read_only=True)
    if "shubhali_korib_chiqish" in wb.sheetnames:
        rows = list(wb["shubhali_korib_chiqish"].iter_rows(values_only=True))
        h = list(rows[0])
        for r in rows[1:]:
            v = (str(r[h.index("qaror")]).strip().lower() if r[h.index("qaror")] is not None else "")
            if v:
                decisions[r[h.index("lemmalar")]] = "ha" if v in YES else "yo'q" if v in NO else v
    if "tekshiruv_100" in wb.sheetnames:
        rows = list(wb["tekshiruv_100"].iter_rows(values_only=True))
        review = [dict(zip(rows[0], r)) for r in rows[1:]]
    return decisions, review


def main():
    decisions, prev_review = load_previous()
    if WB_PATH.exists():                         # foydalanuvchi to'ldirgan faylning zaxira nusxasi
        import shutil
        shutil.copy2(WB_PATH, OUT / "terminlar_yakuniy.oldingi.xlsx")
    STOP.update(ln.strip() for ln in (ROOT / "data/meta/stopwords_uz.txt").read_text(encoding="utf-8").splitlines()
                if ln.strip() and not ln.startswith("#"))
    rows = json.load(gzip.open(OUT / "candidates_full.json.gz", "rt", encoding="utf-8"))
    removed, kept = [], []
    for r in rows:
        why, detail = clean_reason(r)
        if why:
            r["sabab"], r["sabab_tafsiloti"] = why, detail
            removed.append(r)
        else:
            r["auto_termin"], r["auto_sabab"] = classify(r)
            kept.append(r)
    shubhali = sorted((r for r in kept if r["auto_termin"] == "shubhali"),
                      key=lambda r: (-r["norm_ball"], -r["hujjatlar_soni"], -r["chastota"]))
    for r in shubhali:
        r["qaror"] = decisions.get(r["lemmalar"], "")
    bad_dec = sorted({v for v in decisions.values() if v not in ("ha", "yo'q")})
    if bad_dec:
        print("Tanilmagan qaror qiymatlari (e'tiborsiz qoldirildi):", bad_dec)
    promoted = [r for r in shubhali if r["qaror"] == "ha"]
    for r in promoted:
        r["auto_termin"], r["auto_sabab"] = "ha", "Q: shubhali, qo'lda tasdiqlangan; " + r["auto_sabab"]
    ha = [r for r in kept if r["auto_termin"] == "ha"]
    ha.sort(key=lambda r: (-r["norm_ball"], -r["hujjatlar_soni"], -r["chastota"]))
    final = ha[:FINAL_N]
    final_ids = {id(r) for r in final}
    for r in kept:
        if id(r) not in final_ids:
            r["sabab"] = {"yo'q": "tasnif_yoq", "shubhali": "tasnif_shubhali"}.get(r["auto_termin"], "ha_1000_dan_tashqari")
            r["sabab_tafsiloti"] = r["auto_sabab"]
            removed.append(r)
    for r in final:
        if r["sozlar_soni"] == 1:
            r["termin"] = r["lemmalar"]          # bir so'zli: lug'at shakli (variantlar ustunida barcha shakllar)
        r.update(describe(r))
    cl_of, clusters_list = clusters(final)
    for i, r in enumerate(final):
        r["variant_klaster"] = cl_of.get(i, "")
    for i, r in enumerate(final, 1):
        r["orin"] = i

    sample, alloc = stratified_sample(final, SAMPLE_N, SEED)
    if prev_review:                              # baholash boshlangan tanlanma o'zgarmasin
        sample = prev_review
        alloc = dict(Counter(r["mavzuiy_guruh"] for r in prev_review))

    # statistika
    stats = {k: dist(final, k, k) for k in ["mavzuiy_guruh", "tuzilish", "model", "komponentlar_soni", "kelib_chiqish"]}
    suf = Counter(s.split(" (")[0] for r in final for s in r["yasovchi_qoshimcha"].split("; ") if s)
    with_suf = sum(1 for r in final if r["yasovchi_qoshimcha"])
    stats["yasovchi_qoshimcha"] = [{"yasovchi_qoshimcha": k, "soni": v, "ulush_%": round(100 * v / len(final), 1)}
                                   for k, v in suf.most_common()]
    for r in final:
        r["soha"] = dominant_soha(r)
    stats["soha_x_guruh"] = crosstab(final, "soha", "mavzuiy_guruh")
    origins = sorted({r["kelib_chiqish"] for r in final})
    occ = {o: Counter() for o in origins}
    for r in final:
        for s in STATUS_TOKENS:
            occ[r["kelib_chiqish"]][s] += r[f"f_{s}"]
    stats["maqom_x_kelib_chiqish"] = [{"kelib_chiqish": o, **{s: occ[o][s] for s in STATUS_TOKENS},
                                       "jami": sum(occ[o].values())} for o in origins]
    stats["maqom_x_kelib_chiqish_ipm"] = [{"kelib_chiqish": o, **{s: round(occ[o][s] / STATUS_TOKENS[s] * 1e6)
                                                                  for s in STATUS_TOKENS}} for o in origins]
    stats["maqom_x_kelib_chiqish_terminlar"] = crosstab(
        [dict(r, maqom=max(STATUS_TOKENS, key=lambda s: r[f"f_{s}"] / STATUS_TOKENS[s])) for r in final],
        "maqom", "kelib_chiqish")
    dub = []
    for k, g in enumerate(clusters_list[:20], 1):
        dub.append({"klaster": f"D{k:03d}", "terminlar_soni": len(g),
                    "jami_chastota": sum(final[i]["chastota"] for i in g),
                    "terminlar": "; ".join(f"{final[i]['termin']} ({final[i]['chastota']})"
                                           for i in sorted(g, key=lambda i: -final[i]["chastota"])),
                    "f_norasmiy_tarjima": sum(final[i]["f_norasmiy_tarjima"] for i in g),
                    "f_asl_ozbekcha": sum(final[i]["f_asl_ozbekcha"] for i in g)})
    stats["dubletlar_top20"] = dub

    counts = {
        "nomzodlar_jami": len(rows),
        "tozalash": dict(Counter(r["sabab"] for r in removed if r["sabab"] in
                                 ("bolak", "nomenklatura", "umumiy_leksika", "zaxira"))),
        "tasnif": dict(Counter(r["auto_termin"] for r in kept)),
        "tasnif_sabablari": dict(Counter(r["auto_sabab"].split(":")[0] for r in kept)),
        "ha_jami": len(ha), "yakuniy": len(final), "shubhali_jami": len(shubhali),
        "shubhali_qaror_berilgan": sum(1 for r in shubhali if r["qaror"]), "qolda_tasdiqlangan": len(promoted), "dublet_klasterlari": len(clusters_list),
        "dubletga_kirgan_terminlar": sum(len(g) for g in clusters_list),
        "tanlanma_taqsimoti": alloc,
        "kelib_chiqish_aniqlangan_komponentlar_%": round(100 * sum(
            1 for r in final for x in r["kelib_chiqish_komponentlar"].split("; ") if not x.endswith("aniqlanmagan"))
            / sum(r["komponentlar_soni"] for r in final), 1),
        "bir_sozli_bolak_qoidasi_qollanganda_chiqishi_mumkin_edi": sum(
            1 for r in rows if r["sozlar_soni"] == 1 and r["ichida_ulush"] > NEST_MAX and r["chastota"] >= MIN_F),
        "yasovchili_terminlar": with_suf,
    }
    (OUT / "stats.json").write_text(json.dumps({"counts": counts, **stats}, ensure_ascii=False, indent=1), encoding="utf-8")
    write_tables(stats)
    figures(stats, final)
    write_workbook(final, sample, stats, removed, counts, shubhali)
    print(json.dumps(counts, ensure_ascii=False, indent=1))


FINAL_COLS = ["orin", "termin", "variantlar", "chastota", "hujjatlar_soni", "sohalar", "mavzuiy_guruh", "tuzilish",
              "komponentlar_soni", "model", "yasovchi_qoshimcha", "kelib_chiqish_komponentlar", "kelib_chiqish",
              "variant_klaster", "f_norasmiy_tarjima", "f_asl_ozbekcha", "f_aniqlanmagan", "ball", "ball_turi",
              "norm_ball", "auto_termin", "auto_sabab", "kontekst_1", "kontekst_2", "lemmalar"]
REMOVED_COLS = ["termin", "sabab", "sabab_tafsiloti", "chastota", "hujjatlar_soni", "sozlar_soni", "ball", "ball_turi",
                "norm_ball", "ichida_ulush", "bosh_harf_ulush", "ref_ipm", "sohalar", "lemmalar", "kontekst_1"]


def write_tables(stats):
    from openpyxl import Workbook
    TABLES.mkdir(parents=True, exist_ok=True)
    for name, rows in stats.items():
        if not rows:
            continue
        wb = Workbook(); ws = wb.active; ws.title = name[:31]
        cols = list(rows[0]); ws.append(cols)
        for r in rows:
            ws.append([r[c] for c in cols])
        wb.save(TABLES / f"{name}.xlsx")


def write_workbook(final, sample, stats, removed, counts, shubhali):
    from openpyxl import Workbook
    from openpyxl.worksheet.datavalidation import DataValidation
    from openpyxl.styles import Font
    from openpyxl.utils import get_column_letter
    wb = Workbook()

    def sheet(title, cols, rows, widths=None, first=False):
        ws = wb.active if first else wb.create_sheet()
        ws.title = title
        ws.append(cols)
        for c in ws[1]:
            c.font = Font(bold=True)
        for r in rows:
            ws.append([r.get(c, "") for c in cols])
        for i, c in enumerate(cols, 1):
            ws.column_dimensions[get_column_letter(i)].width = (widths or {}).get(c, 14)
        ws.freeze_panes = "B2"
        ws.auto_filter.ref = ws.dimensions
        return ws

    w = {"termin": 34, "variantlar": 40, "kontekst_1": 80, "kontekst_2": 80, "auto_sabab": 45, "model": 28,
         "kelib_chiqish_komponentlar": 40, "yasovchi_qoshimcha": 26, "sohalar": 30, "sabab_tafsiloti": 50,
         "kontekst": 90}
    sheet("terminlar_yakuniy", FINAL_COLS, final, w, first=True)
    if sample and "mening_bahoim" in sample[0]:  # oldingi (to'ldirilayotgan) tanlanma o'zgarishsiz
        srows = sample
    else:
        srows = [{"№": i, "termin": t["termin"], "mavzuiy_guruh": t["mavzuiy_guruh"], "kontekst": t["kontekst_1"],
                  "avtomatik_qaror": t["auto_termin"], "auto_sabab": t["auto_sabab"], "mening_bahoim": ""}
                 for i, t in enumerate(sample, 1)]
    ws = sheet("tekshiruv_100", list(srows[0]), srows, w)
    dv = DataValidation(type="list", formula1='"to\'g\'ri,noto\'g\'ri"', allow_blank=True)
    ws.add_data_validation(dv)
    dv.add(f"{get_column_letter(list(srows[0]).index('mening_bahoim') + 1)}2:"
           f"{get_column_letter(list(srows[0]).index('mening_bahoim') + 1)}{len(srows) + 1}")
    scols = ["№", "termin", "kontekst_1", "kontekst_2", "auto_sabab", "chastota", "hujjatlar_soni", "norm_ball",
             "lemmalar", "qaror"]
    ws = sheet("shubhali_korib_chiqish", scols, [dict(r, **{"№": i}) for i, r in enumerate(shubhali, 1)],
               {**w, "kontekst_1": 70, "kontekst_2": 70, "lemmalar": 24})
    dv = DataValidation(type="list", formula1='"ha,yo\'q"', allow_blank=True,
                        promptTitle="Qaror", prompt="ha — yakuniy ro'yxatga qo'shiladi; yo'q — chiqariladi")
    ws.add_data_validation(dv)
    col = get_column_letter(len(scols))
    dv.add(f"{col}2:{col}{len(shubhali) + 1}")
    ws = wb.create_sheet("statistika")
    for name, rows in stats.items():
        if name == "dubletlar_top20" or not rows:
            continue
        ws.append([name]); ws.cell(ws.max_row, 1).font = Font(bold=True)
        cols = list(rows[0]); ws.append(cols)
        for r in rows:
            ws.append([r[c] for c in cols])
        ws.append([])
    ws.column_dimensions["A"].width = 34
    sheet("dubletlar", list(stats["dubletlar_top20"][0]), stats["dubletlar_top20"], {"terminlar": 90})
    removed.sort(key=lambda r: (r["sabab"], -r["chastota"]))
    sheet("chiqarilganlar", REMOVED_COLS, removed, w)
    ek = OUT / "kelib_chiqish_tekshiruv.xlsx"     # check_etymology.py natijasi
    if ek.exists():
        from openpyxl import load_workbook
        src = list(load_workbook(ek, read_only=True).active.iter_rows(values_only=True))
        sheet("kelib_chiqish_tekshiruv", list(src[0]), [dict(zip(src[0], r)) for r in src[1:]],
              {"etimologiya_xom": 60, "natija": 45})
    ws = wb.create_sheet("metod")
    for k, v in METHOD_ROWS(counts):
        ws.append([k, v])
    ws.column_dimensions["A"].width = 30; ws.column_dimensions["B"].width = 130
    wb.save(WB_PATH)


def METHOD_ROWS(c):
    t = c["tozalash"]
    return [
        ("Manba", "output/candidates_full.json.gz (extract_terms.py, 1–6 so'zli nomzodlar, f ≥ 3)"),
        ("Tozalash tartibi", "qoidalar shu tartibda, birinchi mos kelgani yoziladi"),
        ("bolak", f"faqat ko'p so'zli; chastotaning > 80 % i uzunroq nomzod ichida → {t.get('bolak', 0)}"),
        ("nomenklatura", f"joy/atoqli nom bor yoki tashkilot bosh so'zi + bosh harf ≥ 50 %, qisqartma nom → {t.get('nomenklatura', 0)}"),
        ("umumiy_leksika", f"bir so'zli: G² < 10,83 yoki reference ≥ 50 ipm va huquqiy lug'atda yo'q → {t.get('umumiy_leksika', 0)}"),
        ("zaxira", f"f < 5 → {t.get('zaxira', 0)}"),
        ("Tasnif", "T1–T4 (bir so'zli), S1–S5 (tuzilish bo'yicha rad), H1–H5 (bosh so'z va huquqiy komponent); classify_terms.py"),
        ("Tasnif natijasi", json.dumps(c["tasnif"], ensure_ascii=False)),
        ("Yakuniy ro'yxat", f"auto_termin = ha: {c['ha_jami']}; norm_ball, hujjatlar_soni, chastota bo'yicha birinchi {c['yakuniy']}"),
        ("Tanlanma", f"{SAMPLE_N} ta, seed = {SEED}, mavzuiy guruhlar bo'yicha proporsional: {json.dumps(c['tanlanma_taqsimoti'], ensure_ascii=False)}"),
        ("Aniqlik", "scripts/precision.py — tekshiruv_100 varag'idagi 'mening_bahoim' bo'yicha, Wilson 95 % oraliq"),
        ("Kelib chiqish", f"o'zak bo'yicha term_lexicons.ETYM + -siya/-tsiya kabi o'zlashma qo'shimchalar; aniqlangan komponentlar {c['kelib_chiqish_aniqlangan_komponentlar_%']} %"),
    ]


if __name__ == "__main__":
    main()
