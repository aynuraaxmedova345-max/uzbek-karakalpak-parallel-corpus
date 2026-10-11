"""Korpus va reference korpus uchun umumiy normallashtirish, tokenizatsiya va lemmatizatsiya.

Ikkala korpus aynan bir xil qoidalar bilan ishlanadi, aks holda log-likelihood taqqoslash noto'g'ri bo'ladi.
"""

import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEMMA_FIXES = ROOT / "data" / "meta" / "lemma_tuzatishlar.csv"

APOS = "'ʻʼ‘’`´"
OKINA = "ʻ"     # oʻ, gʻ
TUTUQ = "ʼ"     # taʼlim, maʼlumot
_APOS_RE = re.compile(f"([OoGg])[{APOS}]|[{APOS}]")


def normalize(text):
    """Apostrof variantlarini yagona shaklga keltiradi. Uzunlik o'zgarmaydi (belgi -> belgi)."""
    return _APOS_RE.sub(lambda m: m.group(1) + OKINA if m.group(1) else TUTUQ, text)


WORD_RE = re.compile(r"[A-Za-zʻʼ]+(?:-[A-Za-zʻʼ]+)*")
# n-gramm chegaralari: tinish belgilari, raqamlar, qavslar
SEGMENT_RE = re.compile(r"[^.,;:!?()\[\]«»“”\"„—–…/\d§№]+")


def segments(line):
    """Normallashtirilgan qatorni tinish belgilari bo'yicha bo'laklarga ajratadi: [(token, start, end), ...]."""
    for seg in SEGMENT_RE.finditer(line):
        toks = [(m.group().lower(), seg.start() + m.start(), seg.start() + m.end())
                for m in WORD_RE.finditer(seg.group())]
        toks = [t for t in toks if t[0].strip(OKINA + TUTUQ)]
        if toks:
            yield toks


# Ot so'z turkumi qo'shimchalari zanjirlari (ko'plik + egalik + kelishik), uzunidan qisqasiga
_PLURAL = ["lar"]
_POSS = ["imiz", "ingiz", "lari", "si", "im", "ing", "i"]
_CASE = ["ning", "ni", "ga", "ka", "qa", "da", "dan", "dagi", "gacha", "dek", "day", "niki"]
NOUN_CHAINS = sorted({p + o + c for p in [""] + _PLURAL for o in [""] + _POSS for c in [""] + _CASE} - {""},
                     key=len, reverse=True)
NUMERALS = {"bir", "ikki", "uch", "toʻrt", "besh", "olti", "yetti", "sakkiz", "toʻqqiz", "oʻn", "yigirma",
            "oʻttiz", "qirq", "ellik", "oltmish", "yetmish", "sakson", "toʻqson", "yuz", "ming"}
VERB_PROBES =["adi", "ydi", "di", "ish", "sh", "ib", "gan", "moq", "ilgan", "lgan", "ladi", "adilar"]


class Lemmatizer:
    """UzMorphAnalyser + ikki bosqichli tuzatish.

    1) Lug'at tekshiruvi (vocab berilganda): analizator lemmasi mustaqil so'z sifatida uchramasa,
       yoki fe'l deb tahlil qilingan, lekin bu asosdan fe'l shakllari umuman uchramasa, so'zdan ot
       qo'shimchalari zanjiri kesilib, lug'atda bor eng qisqa asos olinadi (k/g, q/gʻ almashinuvi bilan).
    2) Qo'lda tuzatishlar (data/meta/lemma_tuzatishlar.csv): so'z_boshi + analizator_lemmasi -> to'g'ri lemma.
    """

    def __init__(self, vocab=None, min_attest=3):
        from UzMorphAnalyser import UzMorphAnalyser
        self.a = UzMorphAnalyser()
        self.cache = {}
        self.vocab = vocab or {}
        self.min_attest = min_attest
        self.fixes = []
        if LEMMA_FIXES.exists():
            with LEMMA_FIXES.open(encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    self.fixes.append((r["soz_boshi"], r["analizator_lemmasi"], r["togri_lemma"]))
            self.fixes.sort(key=lambda x: -len(x[0]))

    def raw(self, word):
        """Analizatorning tuzatilmagan javobi: (lemma, pos)."""
        r = self.a.analyze(word.replace(OKINA, "‘"))[0]
        return r["lemma"].replace("‘", OKINA).replace("’", TUTUQ).lower(), r["pos"]

    def attested(self, w):
        return len(w) >= 2 and self.vocab.get(w, 0) >= self.min_attest

    def paradigm(self, stem):
        """stem + ot qo'shimchasi ko'rinishidagi lug'atda bor shakllar soni."""
        return sum(1 for ch in NOUN_CHAINS if self.attested(stem + ch))

    def noun_stem(self, word):
        """Ot qo'shimchalarini kesib, lug'atda bor eng qisqa asos (yo'q bo'lsa None)."""
        best = word if self.attested(word) else None
        for ch in NOUN_CHAINS:
            if word.endswith(ch) and len(word) - len(ch) >= 3:
                s = word[: -len(ch)]
                cands = [s]
                if ch[0] in "aeiou":  # undosh almashinuvi: qonunchilig+i -> qonunchilik
                    if s.endswith("g"):
                        cands.append(s[:-1] + "k")
                    if s.endswith("gʻ"):
                        cands.append(s[:-2] + "q")
                for c in cands:
                    if self.attested(c) and (best is None or len(c) < len(best)):
                        best = c
        return best

    def correct(self, word, lemma, pos):
        """Lug'at tekshiruvi (1-bosqich): (lemma, pos, sabab)."""
        if not self.vocab or pos == "PRN" or (pos == "NUM" and lemma in NUMERALS):
            return lemma, pos, ""
        ns = self.noun_stem(word)
        if ns is None or ns == lemma:
            return lemma, pos, ""
        reason = "ortiqcha_kesilgan" if self.attested(lemma) else "lemma_lugatda_yoq"
        if pos == "VERB":
            verb_forms = sum(self.vocab.get(lemma + p, 0) for p in VERB_PROBES)
            if verb_forms < 5 and (not self.attested(lemma) or len(lemma) < len(ns)):
                return ns, "NOUN", "soxta_fel_tahlili"
            return lemma, pos, ""
        rem = word[len(lemma):] if word.startswith(lemma) else None
        if rem is not None and (rem == "" or rem in NOUN_CHAINS):
            # analizator so'zni asos + ot qo'shimchasiga ajratgan: qaysi asos ko'proq shaklda uchrasa, o'sha
            if rem[:1] == "i" and (lemma.endswith("ch") or
                                   any(self.attested(lemma + "i" + x) for x in ("lar", "si", "lari"))):
                return lemma + "i", pos, reason          # -chi: ahdlashuvch+i -> ahdlashuvchi
            for g, k in (("gʻ", "q"), ("g", "k")):       # qonunchilig+iga -> qonunchilik
                if lemma.endswith(g) and rem[:1] in tuple("aeiou") and (
                        self.attested(lemma[: -len(g)] + k) or lemma.endswith("lig")):
                    return lemma[: -len(g)] + k, pos, reason
            if self.paradigm(ns) > self.paradigm(lemma):
                return ns, pos, reason                   # shax+sini -> shaxs, mod+da -> modda
            return lemma, pos, ""                        # tavsif+ini, zimma+siga, oy+dan
        return ns, pos, reason                           # qoʻmi+ta, tegish+li, nuqta+yi

    def analyse(self, word):
        """(lemma, pos, tuzatish_turi) — tuzatish_turi: '' / avtomatik sabab / 'qolda'."""
        try:
            lemma, pos = self.raw(word)
        except Exception:
            return word, "", "analizator_xatosi"
        for prefix, bad, good in self.fixes:
            if word.startswith(prefix) and lemma == bad:
                return good, pos if pos != "NUM" else "NOUN", "qolda"
        return self.correct(word, lemma, pos)

    def __call__(self, word):
        if word not in self.cache:
            lemma, pos, _ = self.analyse(word)
            self.cache[word] = (lemma, pos)
        return self.cache[word]
