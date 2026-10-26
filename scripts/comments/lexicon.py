"""Frazeologik va ko'chma ma'noli so'zlar leksikonlari bo'yicha matndan moslik izlash.

Ikki leksikon ishlatiladi (data/lexicons/):
  * frazeologik_lugat.csv  - iboralar (ibora, lug'aviy_izoh, qo'llanish, ...)
  * kochma_leksikon.csv    - ko'chma ma'noga ega so'zlar (soz, kochma_izoh, ...)

Izohlar (kommentlar) odatda imlo qoidasiz yoziladi: tutuq belgisisiz ("koz"),
kirill alifbosida ("кўз"), so'z qo'shimchalari bilan. Shuning uchun:
  1. matn va leksikon bir xil normallashtiriladi (kirill -> lotin, kichik harf,
     barcha tutuq belgilari bitta ' ga keltiriladi);
  2. leksikondagi o' / g' matnda ' siz yozilgan bo'lsa ham topiladi;
  3. har bir so'zning o'zagi ajratiladi: otlarga faqat ot qo'shimchalari
     (-lar, -im, -ning, -dan ...) qo'shilishi mumkin, fe'llar esa erkin
     tuslanadi (otlarda k/q -> g almashinuvi ham hisobga olinadi);
  4. ibora so'zlari ketma-ket keladi (gap=N bilan orasida N tagacha boshqa
     so'z kelishiga ruxsat berish mumkin).

Natija - "nomzod" mosliklar: ko'chma so'z to'g'ri ma'noda ham kelgan bo'lishi
mumkin, shuning uchun yig'ilgan izohlar qo'lda tekshirilishi kerak.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LEXICON_DIR = ROOT / "data" / "lexicons"
FRAZ_PATH = LEXICON_DIR / "frazeologik_lugat.csv"
KOCHMA_PATH = LEXICON_DIR / "kochma_leksikon.csv"

# --------------------------------------------------------------------------
# Normallashtirish
# --------------------------------------------------------------------------

_CYR = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "ё": "yo", "ж": "j",
    "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n",
    "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f",
    "х": "x", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sh", "ъ": "'", "ы": "i",
    "ь": "", "э": "e", "ю": "yu", "я": "ya", "ў": "o'", "қ": "q", "ғ": "g'",
    "ҳ": "h",
}
_CYR_VOWELS = set("аеёиоуэюяў")
_APOSTROPHES = re.compile(r"[‘’ʻʼ`´]")


def _translit_cyrillic(text: str) -> str:
    out = []
    prev = ""
    for ch in text:
        if ch == "е":
            # So'z boshida yoki unlidan keyin "ye", aks holda "e".
            out.append("ye" if (not prev.isalpha() or prev in _CYR_VOWELS) else "e")
        else:
            out.append(_CYR.get(ch, ch))
        prev = ch
    return "".join(out)


def normalize(text: str) -> str:
    """Matnni solishtirish uchun yagona ko'rinishga keltiradi.

    o' va g' saqlanadi, boshqa tutuq belgilari (a'zo -> azo) va qo'shtirnoq
    sifatidagi ' lar olib tashlanadi.
    """
    text = text.lower()
    if re.search(r"[а-яёўқғҳ]", text):
        text = _translit_cyrillic(text)
    text = _APOSTROPHES.sub("'", text)
    text = re.sub(r"([og])'(?=\w)", lambda m: m.group(1) + "\x00", text)  # o' / g' ni vaqtincha himoyalaymiz
    text = text.replace("'", "")
    return text.replace("\x00", "'")


def _plain(text: str) -> str:
    return text.replace("'", "")


# --------------------------------------------------------------------------
# O'zak ajratish
# --------------------------------------------------------------------------

# Fe'l shakllari (eng uzunidan boshlab tekshiriladi).
_VERB_ENDINGS = sorted(
    """moq mak maslik mas may mayin madi magan maydi moqda moqchi
    ayotgan yotgan ib di dim ding dik dingiz dilar gan kan qan
    adi aman asan ydi yman ysan""".split(),
    key=len, reverse=True,
)
# Ot/sifat qo'shimchalari.
_NOUN_SUFFIXES = sorted(
    """lar ning ni ga ka da dan i si im ing imiz ingiz m ng miz ngiz
    lari dagi cha day dek gacha mi chi u yu ku dir lik li siz roq gina""".split(),
    key=len, reverse=True,
)
# Ko'chma otlar uchun qo'shimchalar zanjiri (aniqroq moslik uchun).
_NOUN_TAIL = "(?:" + "|".join(_NOUN_SUFFIXES + ["gi", "ki"]) + "){0,4}"
# Ko'chma fe'llar uchun: o'zakdan keyin albatta fe'l qo'shimchasi kelishi shart
# (bularni != bula+moq, qorani != qor+moq, uch != uchmoq).
_VERB_TAIL = "(?:" + "|".join(sorted(
    """ma mo may mas di gan kan qan ib yap ayap ayotgan yotgan adi aman
    asan amiz asiz ay sa gun guncha gani ish ishdi tir dir il in
    ydi yman ysan""".split(), key=len, reverse=True)) + r")[\w']*"

_MIN_STEM = 3

# Ko'chma so'z sifatida hisoblanmaydigan ko'p uchraydigan vazifadosh so'zlar.
_FUNCTION_WORDS = re.compile(
    r"^(?:bu|shu|u|ul|o'sha|ana|mana|men|sen|biz|siz|ular|bular|shular|"
    r"nima|kim|qanday|qayer|hamma|o'z|bir|ikki|uch|har|hech)"
    + _NOUN_TAIL + "$"
)


# Izohlarda asosan yordamchi fe'l sifatida keladigan so'zlar: ular ko'chma
# leksikonda bo'lsa ham, yakka holda topilsa juda ko'p shovqin beradi.
AUX_VERBS = {
    "turmoq", "yotmoq", "o'tirmoq", "yurmoq", "qolmoq", "ketmoq", "olmoq",
    "bermoq", "ko'rmoq", "qo'ymoq", "chiqmoq", "boshlamoq", "bo'lmoq",
    "qilmoq", "demoq", "kelmoq", "bormoq", "tashlamoq", "yubormoq", "bilmoq",
}


def _strip_suffixes(word: str, last: bool) -> tuple[str, bool]:
    """So'zdan qo'shimchalarni olib tashlaydi. (o'zak, fe'lmi) qaytaradi.

    Iboraning oxirgi so'zidan bitta fe'l qo'shimchasi olinadi; agar u fe'l
    bo'lmasa (yoki so'z oxirgi bo'lmasa), 2 tagacha ot qo'shimchasi olinadi.
    """
    if last:
        for end in _VERB_ENDINGS:
            if word.endswith(end) and len(_plain(word)) - len(end) >= _MIN_STEM:
                return word[: -len(end)], True
    stem = word
    for _ in range(2):
        for end in _NOUN_SUFFIXES:
            if stem.endswith(end) and len(_plain(stem)) - len(end) >= _MIN_STEM:
                stem = stem[: -len(end)]
                break
        else:
            break
    return stem, False


def _stem_regex(stem: str, alternate: bool = True) -> str:
    """O'zakni regexga aylantiradi.

    * leksikondagi o' / g' matnda ' siz yozilsa ham mos keladi;
    * otlarda oxirgi k/q -> g almashinuvi (yurak -> yuragi, qishloq -> qishlog'i).
    """
    tail = ""
    if alternate and len(_plain(stem)) >= 3 and stem[-1] == "q":
        stem, tail = stem[:-1], "(?:q|g'?)"
    elif alternate and len(_plain(stem)) >= 3 and stem[-1] == "k":
        stem, tail = stem[:-1], "[kg]"
    body = re.escape(stem).replace("o'", "o'?").replace("g'", "g'?")
    return body + tail


_BRACKET_WORD = re.compile(r"(^|\s)\[[^\]]*\]")       # [olib] - butun so'z ixtiyoriy
_HOMONYM_MARK = re.compile(r"\s+(?:i{1,3}|iv|v|I{1,3}|IV|V)\.?$")


def _clean_phrase(phrase: str) -> list[tuple[str, bool]]:
    """Iborani [(o'zak, fe'lmi), ...] ro'yxatiga aylantiradi."""
    phrase = _HOMONYM_MARK.sub("", phrase.strip())
    phrase = _BRACKET_WORD.sub(" ", phrase)
    tokens = []
    # "kim?", "nimaning?" - grammatik izoh, ibora qismi emas
    raws = [r for r in phrase.split() if "?" not in r]
    for i, raw in enumerate(raws):
        # Qavs ichidagi qism va undan keyingi qo'shimcha o'zakka kirmaydi:
        # yurag(i)ga -> yurag, do'ppi(si)ni -> do'ppi
        core = re.split(r"[\(\[]", raw, maxsplit=1)[0]
        core = re.sub(r"[\]\)\[\(]", "", core)
        core = normalize(core).strip(".,;:!«»\"'")
        if not core:
            continue
        if "(" in raw or "[" in raw:
            tokens.append((core, False))
        else:
            tokens.append(_strip_suffixes(core, last=(i == len(raws) - 1)))
    return tokens


# --------------------------------------------------------------------------
# Leksikon yozuvlari
# --------------------------------------------------------------------------

@dataclass
class Entry:
    lexicon: str              # "frazeologik" yoki "kochma"
    item: str                 # leksikondagi asl ko'rinish
    meaning: str              # izoh
    pattern: re.Pattern
    anchors: tuple[str, ...]  # tez filtrlash uchun o'zaklarning boshlanishi
    extra: dict = field(default_factory=dict)


def _anchor(stem: str) -> str:
    """Tez filtrlash kaliti: o'zakning 3 harfli boshlanishi (' siz)."""
    s = re.match(r"\w*", _plain(stem)).group(0) or _plain(stem)
    if len(s) <= 3 and s[-1] in "kq":
        return s[:-1] or s
    return s[:3]


_START = r"(?<![\w'])"
_END = r"(?![\w'])"


def _gap(n: int) -> str:
    """Iboradagi so'zlar orasida 0..n ta boshqa so'z kelishiga ruxsat."""
    sep = r"[\s\-\u2013\u2014]+"  # faqat bo'shliq/chiziqcha: "birga, dunyoda" != "bir dunyo"
    if n <= 0:
        return sep
    return r"(?:%s[\w']+){0,%d}?%s" % (sep, n, sep)


def _phrase_pattern(stems: list[tuple[str, bool]], gap: int) -> re.Pattern:
    parts = []
    for s, verb in stems:
        if verb:   # fe'l: shakllari juda ko'p, davomi erkin
            parts.append(_START + _stem_regex(s, alternate=False) + r"[\w']*")
        else:      # ot/sifat: faqat qo'shimchalar zanjiri (bosh != boshlanib)
            parts.append(_START + _stem_regex(s) + _NOUN_TAIL + _END)
    return re.compile(_gap(gap).join(parts))


def _short(text: str, limit: int = 200) -> str:
    text = re.sub(r"\s+", " ", (text or "")).strip().lstrip("–- ").strip()
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + "…"


def load_frazeologik(path: Path = FRAZ_PATH, gap: int = 0) -> list[Entry]:
    entries: list[Entry] = []
    seen: set[tuple] = set()
    with path.open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            ibora = (row.get("ibora") or "").strip()
            meaning = _short(row.get("lug‘aviy_izoh") or "")
            usage = row.get("qo‘llanish") or ""
            variants = [ibora]
            m = re.search(r"Varianti:\s*(.+?)(?:Sinonim|Antonim|Omonim|Paronim|$)", usage)
            if m:
                variants += [v.strip(" .") for v in m.group(1).split(";")]
            for variant in variants:
                stems = _clean_phrase(variant)
                # Bitta so'zli yozuvlar (OCR qoldiqlari: "bosh", "ekan") tashlab
                # yuboriladi; faqat uzun chiziqchali birikmalar qoladi.
                if len(stems) < 2 and not (stems and "-" in stems[0][0] and len(stems[0][0]) >= 7):
                    continue
                key = tuple(stems)
                if key in seen:
                    continue
                seen.add(key)
                entries.append(Entry(
                    lexicon="frazeologik",
                    item=ibora if variant == ibora else f"{variant} (varianti: {ibora})",
                    meaning=meaning,
                    pattern=_phrase_pattern(stems, gap),
                    anchors=tuple(_anchor(s) for s, _ in stems),
                    extra={"ibora": ibora, "manba_sahifa": row.get("manba_sahifa", "")},
                ))
    return entries


def load_kochma(path: Path = KOCHMA_PATH, include_aux: bool = False, gap: int = 0) -> list[Entry]:
    by_word: dict[str, list[dict]] = {}
    with path.open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            word = normalize((row.get("soz") or "").strip())
            if len(_plain(word)) < 3 or (not include_aux and word in AUX_VERBS):
                continue
            by_word.setdefault(word, []).append(row)

    entries: list[Entry] = []
    for word, rows in by_word.items():
        stems = []
        for w in word.split():
            if w.endswith(("moq", "mak")) and len(w) > 5:
                stems.append((w[:-3], True))
            else:
                stems.append((w, False))
        parts = []
        for stem, is_verb in stems:
            if is_verb:
                parts.append(_START + _stem_regex(stem, alternate=False) + _VERB_TAIL + _END)
            else:
                parts.append(_START + _stem_regex(stem) + _NOUN_TAIL + _END)
        meanings = " | ".join(
            f"{r.get('ma‘no_raqami', '')}) {_short(r.get('kochma_izoh') or '', 150)}"
            for r in rows
        )
        entries.append(Entry(
            lexicon="kochma",
            item=rows[0].get("soz", word),
            meaning=meanings,
            pattern=re.compile(_gap(gap).join(parts)),
            anchors=tuple(_anchor(s) for s, _ in stems),
            extra={"uslub": "; ".join(sorted({r.get("uslub_belgilari") or "" for r in rows} - {""}))},
        ))
    return entries


# --------------------------------------------------------------------------
# Moslik izlovchi
# --------------------------------------------------------------------------

@dataclass
class Match:
    lexicon: str
    item: str
    meaning: str
    span: str
    extra: dict


class LexiconMatcher:
    def __init__(self, use_frazeologik: bool = True, use_kochma: bool = True,
                 fraz_path: Path = FRAZ_PATH, kochma_path: Path = KOCHMA_PATH,
                 include_aux: bool = False, gap: int = 0):
        self.entries: list[Entry] = []
        if use_frazeologik:
            self.entries += load_frazeologik(fraz_path, gap)
        if use_kochma:
            self.entries += load_kochma(kochma_path, include_aux, gap)
        # Har bir yozuv birinchi so'zining boshlanishi bo'yicha indekslanadi.
        self._index: dict[str, list[Entry]] = {}
        for e in self.entries:
            self._index.setdefault(e.anchors[0], []).append(e)

    def find(self, text: str) -> list[Match]:
        norm = normalize(text)
        words = [_plain(w) for w in re.findall(r"[\w']+", norm)]
        prefixes = {w[:n] for w in words for n in (1, 2, 3)}
        hits: list[tuple[Entry, re.Match]] = []
        for prefix in prefixes:
            for e in self._index.get(prefix, ()):
                if not all(a in prefixes for a in e.anchors):
                    continue
                m = e.pattern.search(norm)
                if not m:
                    continue
                if e.lexicon == "kochma" and _FUNCTION_WORDS.match(m.group(0)):
                    continue
                hits.append((e, m))

        phrase_spans = [m.span() for e, m in hits if e.lexicon == "frazeologik"]
        # Frazeologik moslik ichidagi ko'chma so'z alohida sanalmaydi.
        hits = [(e, m) for e, m in hits
                if e.lexicon == "frazeologik"
                or not any(s <= m.start() < t for s, t in phrase_spans)]
        # Bir ibora uzunroq iboraning ichida qolsa (variantlar), qisqasi tashlanadi.
        hits.sort(key=lambda h: (h[0].lexicon, -(h[1].end() - h[1].start())))
        final: list[tuple[Entry, re.Match]] = []
        for e, m in hits:
            if e.lexicon == "frazeologik" and any(
                    f.lexicon == "frazeologik" and fm.start() <= m.start() and m.end() <= fm.end()
                    and f.extra["ibora"] == e.extra["ibora"]
                    for f, fm in final):
                continue
            final.append((e, m))
        # Bir xil parchaga bir nechta yozuv mos kelsa (amalga oshmoq / amalga
        # oshirmoq), ular bitta natijaga birlashtiriladi.
        merged: dict[tuple, Match] = {}
        for e, m in final:
            key = (e.lexicon, m.span())
            if key in merged:
                prev = merged[key]
                prev.item += " || " + e.item
                prev.meaning += " || " + e.meaning
                for k, v in e.extra.items():
                    if v and v != prev.extra.get(k):
                        prev.extra[k] = f"{prev.extra.get(k, '')} || {v}".strip(" |")
            else:
                merged[key] = Match(e.lexicon, e.item, e.meaning, m.group(0), dict(e.extra))
        return sorted(merged.values(), key=lambda r: norm.find(r.span))
