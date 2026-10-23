#!/usr/bin/env python3
"""Izohli lug'at PDF jildi uchun kam xotirali sinov (pilot) skripti.

Qoidalar:
  * Sahifalar bittadan ochiladi, har sahifadan keyin natija diskka yoziladi
    va pdfplumber keshi bo'shatiladi.
  * Bo'sh xotira chegaradan past bo'lsa yangi sahifa boshlanmaydi,
    checkpoint saqlanib, 3-kod bilan chiqiladi.
  * Parallel ishlov, multiprocessing, tashqi API yo'q.
  * Asl PDF faqat o'qiladi.
  * Avtomatik ajratilgan hamma narsa extraction_status="auto_unverified".

Buyruqlar:
  probe    PDF  --out probe.json [--scan-first 40]
  extract  PDF  --pages 25-34 --volume 1 --outdir extracted/volume_1
  render   PDF  --pages 25-27 --outdir extracted/volume_1/page_images [--dpi 100]
  ocr      PDF  --pages 25-27 --outdir extracted/volume_1/ocr_test [--lang uzb_cyrl+uzb]
  segment  --pages-jsonl extracted/volume_1/pilot_pages.jsonl --volume 1
           --articles extracted/volume_1/pilot_articles.jsonl --review output/pilot_review.csv
"""
import argparse
import csv
import gc
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path

MIN_FREE_MB_DEFAULT = 600
STATUS = "auto_unverified"


# ---------------------------------------------------------------- xotira
def available_mb():
    """Tizimdagi bo'sh (available) xotira, MB. Aniqlab bo'lmasa None."""
    try:
        import psutil  # ixtiyoriy
        return psutil.virtual_memory().available / 2**20
    except ImportError:
        pass
    if sys.platform.startswith("win"):
        try:
            import ctypes

            class MS(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
            m = MS()
            m.dwLength = ctypes.sizeof(MS)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
            return m.ullAvailPhys / 2**20
        except Exception:
            return None
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) / 1024
    except OSError:
        pass
    return None


def memory_ok(min_free_mb):
    a = available_mb()
    return (a is None or a >= min_free_mb), a


def parse_pages(spec):
    out = []
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-")
            out.extend(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return out


# ---------------------------------------------------------------- matn sifati
CYR = re.compile(r"[А-Яа-яЁёЎўҚқҒғҲҳ]")
LAT = re.compile(r"[A-Za-zʻʼ‘’']")
BAD = re.compile(r"\(cid:\d+\)|�")


def text_quality(text):
    n = len(text)
    if n == 0:
        return {"chars": 0, "cyrillic_share": 0, "latin_share": 0, "bad_glyphs": 0, "verdict": "no_text_layer"}
    cyr = len(CYR.findall(text))
    lat = len(LAT.findall(text))
    bad = len(BAD.findall(text))
    letters = cyr + lat
    words = re.findall(r"\w+", text)
    avg_w = sum(map(len, words)) / len(words) if words else 0
    verdict = "ok"
    if n < 200:
        verdict = "too_little_text"
    elif bad > 5 or letters / n < 0.5 or avg_w > 15 or avg_w < 2:
        verdict = "suspect"
    return {"chars": n, "cyrillic_share": round(cyr / n, 3), "latin_share": round(lat / n, 3),
            "bad_glyphs": bad, "avg_word_len": round(avg_w, 2), "verdict": verdict}


FRONT_KEYS = {
    "title": [r"ИЗОҲЛИ\s+ЛУҒАТИ", r"IZOHLI\s+LUG.ATI", r"ТИЛИНИНГ", r"TILINING"],
    "imprint": [r"ISBN", r"УДК|UDK", r"ББК|BBK", r"Тошкент|Toshkent", r"нашриёт|nashriyot", r"©"],
    "abbreviations": [r"ШАРТЛИ\s+ҚИСҚАРТМАЛАР", r"SHARTLI\s+QISQARTMALAR", r"ҚИСҚАРТМАЛАР", r"QISQARTMALAR",
                      r"ШАРТЛИ\s+БЕЛГИЛАР", r"SHARTLI\s+BELGILAR"],
    "preface": [r"СЎЗ\s*БОШИ", r"SO.Z\s*BOSHI", r"ЛУҒАТНИНГ\s+ТУЗИЛИШИ", r"LUG.ATNING\s+TUZILISHI"],
}


# ---------------------------------------------------------------- probe
def cmd_probe(a):
    import pdfplumber
    from pypdf import PdfReader

    pdf_path = Path(a.pdf)
    n_pages = len(PdfReader(str(pdf_path)).pages)
    res = {"file": pdf_path.name, "size_bytes": pdf_path.stat().st_size, "pdf_pages": n_pages,
           "scanned": [], "front_matter_hits": {k: [] for k in FRONT_KEYS}, "first_article_page_guess": None}
    with pdfplumber.open(str(pdf_path)) as pdf:
        for i in range(min(a.scan_first, n_pages)):
            ok, av = memory_ok(a.min_free_mb)
            if not ok:
                res["stopped_low_memory_at_page"] = i + 1
                break
            page = pdf.pages[i]
            txt = page.extract_text() or ""
            q = text_quality(txt)
            q.update({"pdf_page": i + 1, "images": len(page.images), "avail_mb": None if av is None else int(av)})
            # bosh so'z belgisi: qatordagi birinchi so'z qalin va katta harfli
            starts = bold_caps_line_starts(page)
            q["bold_caps_line_starts"] = starts
            res["scanned"].append(q)
            for k, pats in FRONT_KEYS.items():
                if any(re.search(p, txt, re.I) for p in pats):
                    res["front_matter_hits"][k].append(i + 1)
            if res["first_article_page_guess"] is None and starts >= 8 and q["verdict"] == "ok":
                res["first_article_page_guess"] = i + 1
            page.flush_cache() if hasattr(page, "flush_cache") else None
            page.close() if hasattr(page, "close") else None
            del page, txt
            gc.collect()
    verdicts = [s["verdict"] for s in res["scanned"]]
    res["text_layer_summary"] = {v: verdicts.count(v) for v in set(verdicts)}
    res["note"] = ("first_article_page_guess va front_matter_hits faqat avtomatik taxmin; "
                   "sahifa tasvirida qo'lda tasdiqlash shart.")
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("pdf_pages", "front_matter_hits", "first_article_page_guess",
                                          "text_layer_summary")}, ensure_ascii=False, indent=2))


# ---------------------------------------------------------------- extract
def is_bold(fontname):
    return bool(re.search(r"bold|black|heavy|semibold|demi|,B\b|-B\b", fontname or "", re.I))


def is_italic(fontname):
    return bool(re.search(r"italic|oblique|,I\b|-I\b", fontname or "", re.I))


def is_caps_word(w):
    letters = [c for c in w if c.isalpha()]
    return len(letters) >= 1 and all(c.isupper() for c in letters)


def words_of(page_or_crop):
    return page_or_crop.extract_words(extra_attrs=["fontname", "size"], keep_blank_chars=False,
                                      use_text_flow=False, x_tolerance=1.5, y_tolerance=3)


def bold_caps_line_starts(page):
    lines = group_lines(words_of(page))
    return sum(1 for ln in lines if ln and is_bold(ln[0]["fontname"]) and is_caps_word(ln[0]["text"])
               and len(ln[0]["text"]) > 1)


def group_lines(words, tol=3):
    lines = []
    for w in sorted(words, key=lambda w: (round(w["top"]), w["x0"])):
        if lines and abs(lines[-1][0]["top"] - w["top"]) <= tol:
            lines[-1].append(w)
        else:
            lines.append([w])
    return [sorted(ln, key=lambda w: w["x0"]) for ln in lines]


def find_gutter(words, width):
    """Ikki ustun orasidagi bo'sh joyni (x) topadi. Topilmasa None (bir ustunli)."""
    lo, hi = width * 0.30, width * 0.70
    step = 2.0
    best, best_x = None, None
    x = lo
    while x <= hi:
        crossing = sum(1 for w in words if w["x0"] < x < w["x1"])
        if best is None or crossing < best:
            best, best_x = crossing, x
        x += step
    left = sum(1 for w in words if w["x1"] <= best_x)
    right = sum(1 for w in words if w["x0"] >= best_x)
    if best is not None and best <= max(1, len(words) * 0.01) and left > 20 and right > 20:
        return best_x
    return None


def line_text(ln):
    return " ".join(w["text"] for w in ln)


def cmd_extract(a):
    import pdfplumber

    outdir = Path(a.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    raw_dir = outdir / "raw_text"
    raw_dir.mkdir(exist_ok=True)
    jsonl = outdir / "pilot_pages.jsonl"
    ckpt = outdir / "pilot_checkpoint.json"
    done = set()
    if jsonl.exists():
        for line in jsonl.open(encoding="utf-8"):
            if line.strip():
                done.add(json.loads(line)["pdf_page"])
    pages = parse_pages(a.pages)
    pdf_path = Path(a.pdf)
    with pdfplumber.open(str(pdf_path)) as pdf:
        n_pages = len(pdf.pages)
        for p in pages:
            if p in done:
                continue
            if not 1 <= p <= n_pages:
                print(f"sahifa {p} PDF chegarasidan tashqarida ({n_pages})", file=sys.stderr)
                continue
            ok, av = memory_ok(a.min_free_mb)
            if not ok:
                ckpt.write_text(json.dumps({"stopped_before_page": p, "avail_mb": int(av), "done": sorted(done),
                                            "reason": "low_memory"}, ensure_ascii=False, indent=2), encoding="utf-8")
                print(f"Bo'sh xotira {int(av)} MB < {a.min_free_mb} MB. {p}-sahifadan oldin to'xtatildi.",
                      file=sys.stderr)
                sys.exit(3)
            page = pdf.pages[p - 1]
            rec = extract_page(page, p, pdf_path.name, a.volume)
            (raw_dir / f"page_{p:04d}.raw.txt").write_text(rec.pop("_raw_text"), encoding="utf-8")
            rec["avail_mb_before"] = None if av is None else int(av)
            with jsonl.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            done.add(p)
            ckpt.write_text(json.dumps({"last_done": p, "done": sorted(done)}, indent=2), encoding="utf-8")
            if hasattr(page, "flush_cache"):
                page.flush_cache()
            if hasattr(page, "close"):
                page.close()
            del page, rec
            gc.collect()
            print(f"sahifa {p}: saqlandi")


def extract_page(page, p, fname, volume):
    raw = page.extract_text() or ""
    W, H = page.width, page.height
    words = words_of(page)
    # kolontitul: yuqori/pastki 7% zona
    top_band, bot_band = H * 0.07, H * 0.93
    header_words = [w for w in words if w["bottom"] <= top_band]
    footer_words = [w for w in words if w["top"] >= bot_band]
    body = [w for w in words if top_band < w["bottom"] and w["top"] < bot_band]
    num_cands = [w["text"] for w in header_words + footer_words if re.fullmatch(r"\d{1,4}", w["text"])]
    printed = int(num_cands[0]) if len(set(num_cands)) == 1 else None
    issues = []
    if len(set(num_cands)) > 1:
        issues.append(f"printed_page_ambiguous:{sorted(set(num_cands))}")
    if not num_cands:
        issues.append("printed_page_not_found")
    gutter = find_gutter(body, W)
    columns = []
    if gutter is None:
        cols = [("single", body)]
        issues.append("single_column_or_gutter_not_found")
    else:
        cols = [("left", [w for w in body if w["x1"] <= gutter + 1]),
                ("right", [w for w in body if w["x0"] >= gutter - 1])]
        straddle = [w for w in body if w["x0"] < gutter - 1 and w["x1"] > gutter + 1]
        if straddle:
            issues.append(f"words_crossing_gutter:{len(straddle)}")
    for name, ws in cols:
        lines = []
        for ln in group_lines(ws):
            lines.append({
                "text": line_text(ln),
                "x0": round(ln[0]["x0"], 1), "top": round(ln[0]["top"], 1),
                "first_bold": is_bold(ln[0]["fontname"]),
                "tokens": [{"t": w["text"], "b": is_bold(w["fontname"]), "i": is_italic(w["fontname"]),
                            "s": round(w["size"], 1), "y": round(w["top"], 1)} for w in ln],
            })
        columns.append({"column": name, "lines": lines})
    fonts = sorted({w["fontname"] for w in body})
    if not any(is_bold(f) for f in fonts):
        issues.append("no_bold_font_detected")
    q = text_quality(raw)
    if q["verdict"] != "ok":
        issues.append(f"text_quality:{q['verdict']}")
    return {
        "source_file": fname, "volume": volume, "pdf_page": p, "printed_page": printed,
        "printed_page_candidates": num_cands,
        "header_text": " ".join(w["text"] for w in header_words),
        "footer_text": " ".join(w["text"] for w in footer_words),
        "gutter_x": None if gutter is None else round(gutter, 1),
        "column_order": [c["column"] for c in columns],
        "text_quality": q, "fonts": fonts, "columns": columns,
        "extraction_method": "pdf_text_layer/pdfplumber", "issues": issues,
        "_raw_text": raw,
    }


# ---------------------------------------------------------------- render / ocr
def cmd_render(a):
    import pdfplumber
    out = Path(a.outdir)
    out.mkdir(parents=True, exist_ok=True)
    with pdfplumber.open(a.pdf) as pdf:
        for p in parse_pages(a.pages):
            ok, av = memory_ok(a.min_free_mb)
            if not ok:
                print(f"Bo'sh xotira kam ({int(av)} MB), {p}-sahifada to'xtatildi.", file=sys.stderr)
                sys.exit(3)
            page = pdf.pages[p - 1]
            im = page.to_image(resolution=a.dpi)
            im.save(str(out / f"page_{p:04d}.png"))
            del im
            if hasattr(page, "close"):
                page.close()
            gc.collect()
            print(f"sahifa {p}: rasm saqlandi")


def cmd_ocr(a):
    exe = shutil.which("tesseract")
    if not exe:
        print("Tesseract o'rnatilmagan. OCR sinovi bajarilmadi. O'rnatish: "
              "https://github.com/UB-Mannheim/tesseract/wiki (Windows), keyin 'uzb' va 'uzb_cyrl' "
              "tessdata fayllarini qo'shing.", file=sys.stderr)
        sys.exit(2)
    langs = subprocess.run([exe, "--list-langs"], capture_output=True, text=True).stdout
    for l in a.lang.split("+"):
        if l not in langs.split():
            print(f"Tesseract tili topilmadi: {l}", file=sys.stderr)
            sys.exit(2)
    pages = parse_pages(a.pages)
    if len(pages) > 3 and not a.allow_more:
        print("OCR sinovi 3 sahifa bilan cheklangan (--allow-more bilan oshiriladi).", file=sys.stderr)
        sys.exit(2)
    import pdfplumber
    out = Path(a.outdir)
    out.mkdir(parents=True, exist_ok=True)
    with pdfplumber.open(a.pdf) as pdf:
        for p in pages:
            ok, av = memory_ok(a.min_free_mb)
            if not ok:
                print(f"Bo'sh xotira kam ({int(av)} MB), {p}-sahifada to'xtatildi.", file=sys.stderr)
                sys.exit(3)
            png = out / f"_tmp_page_{p:04d}.png"
            page = pdf.pages[p - 1]
            page.to_image(resolution=300).save(str(png))
            if hasattr(page, "close"):
                page.close()
            gc.collect()
            base = out / f"page_{p:04d}.ocr"
            subprocess.run([exe, str(png), str(base), "-l", a.lang, "--psm", "4"], check=True)
            png.unlink()  # vaqtinchalik rasm o'chiriladi
            print(f"sahifa {p}: OCR saqlandi -> {base}.txt")


# ---------------------------------------------------------------- segment
CYR2LAT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo", "ж": "j", "з": "z", "и": "i",
    "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t",
    "у": "u", "ф": "f", "х": "x", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sh", "ъ": "ʼ", "ы": "i", "ь": "",
    "э": "e", "ю": "yu", "я": "ya", "ў": "oʻ", "қ": "q", "ғ": "gʻ", "ҳ": "h",
}
APOS = str.maketrans({"'": "ʻ", "‘": "ʻ", "’": "ʼ", "`": "ʻ", "ʹ": "ʼ"})
SUPERSCRIPT = "¹²³⁴⁵⁶⁷⁸⁹⁰"
HOMONYM_RE = re.compile(r"^(.*?)(?:\s*([" + SUPERSCRIPT + r"]+|\d{1,2}|I{1,3}|IV|V))$")
# Lug'at ichki havolalari: avtomatik sinonim emas, xom havola sifatida saqlanadi.
XREF_RE = re.compile(r"(?<!\w)(Айн\.|Ayn\.|Қ\.|Q\.|қаранг|qarang|Зид\.|Zid\.|зид\.|zid\.)\s*"
                     r"([^.;]{1,80}?)(?=[.;]|$)")
ETYM_RE = re.compile(r"^\s*\[([^\]]{1,200})\]")
MARK_RE = re.compile(r"^\s*((?:[a-zа-яўқғҳʻʼ]{1,8}\.\s*){1,4})")


def search_key(hw):
    s = unicodedata.normalize("NFC", hw).lower().translate(APOS)
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    s = unicodedata.normalize("NFC", s)
    s = "".join(CYR2LAT.get(c, c) for c in s)
    s = re.sub(r"[" + SUPERSCRIPT + r"0-9]", "", s)
    return re.sub(r"\s+", " ", s).strip(" -,.")


def iter_lines(pages):
    for pg in pages:
        for col in pg["columns"]:
            for ln in col["lines"]:
                yield pg, col["column"], ln


def headword_tokens(ln):
    """Qator boshidagi qalin + to'liq katta harfli tokenlar. Faqat birinchi harfi katta
    so'z bosh so'z hisoblanmaydi. Bosh so'zdan keyingi raqam omonim belgisi deb faqat
    u kichikroq shriftda yoki yuqoriga ko'tarilgan bo'lsa olinadi; aks holda u ma'no raqami."""
    toks = ln["tokens"]
    if not toks:
        return []
    first = toks[0]
    t0 = first["t"].strip(",")
    if not (first["b"] and is_caps_word(t0) and any(c.isalpha() for c in t0)):
        return []
    hw = [first["t"]]
    for t in toks[1:]:
        txt = t["t"].strip(",")
        if re.fullmatch(r"[" + SUPERSCRIPT + r"]+", txt):
            hw.append(t["t"])
            break
        if re.fullmatch(r"\d{1,2}", txt):
            small = t.get("s") and first.get("s") and t["s"] < 0.85 * first["s"]
            raised = t.get("y") is not None and first.get("y") is not None and t["y"] < first["y"] - 1
            if small or raised:
                hw.append(t["t"])
            break
        if t["b"] and is_caps_word(txt) and any(c.isalpha() for c in txt):
            hw.append(t["t"])  # ko'p so'zli bosh so'z
        else:
            break
    return hw


def cmd_segment(a):
    pages = [json.loads(l) for l in open(a.pages_jsonl, encoding="utf-8") if l.strip()]
    pages.sort(key=lambda r: r["pdf_page"])
    bold_available = any(any(ln["first_bold"] for c in pg["columns"] for ln in c["lines"]) for pg in pages)
    arts, cur, orphan = [], None, []
    for pg, col, ln in iter_lines(pages):
        hw = headword_tokens(ln) if bold_available else []
        if hw:
            if cur:
                arts.append(cur)
            cur = {"hw": hw, "lines": [], "pdf_pages": [], "printed_pages": [], "cols": []}
        if cur is None:
            orphan.append((pg["pdf_page"], ln))
            continue
        cur["lines"].append(ln)
        if pg["pdf_page"] not in cur["pdf_pages"]:
            cur["pdf_pages"].append(pg["pdf_page"])
            cur["printed_pages"].append(pg["printed_page"])
        cur["cols"].append(f'{pg["pdf_page"]}{col[0]}')
    if cur:
        arts.append(cur)
    vol = a.volume
    src = pages[0]["source_file"] if pages else None
    out = []
    for n, art in enumerate(arts, 1):
        out.append(build_article(art, n, vol, src))
    if orphan:
        out.insert(0, {
            "article_id": f"v{vol}-p{orphan[0][0]:04d}-cont", "headword_raw": None, "headword_search_key": None,
            "homonym_marker": None, "senses": [], "cross_references": [], "etymology_raw": None,
            "source_file": src, "volume": vol, "pdf_pages": sorted({p for p, _ in orphan}),
            "printed_pages": [], "raw_text": "\n".join(l["text"] for _, l in orphan),
            "extraction_method": "pdf_text_layer/pdfplumber+rules", "extraction_status": STATUS,
            "issues": ["continuation_from_previous_page_outside_pilot"],
        })
    if not bold_available:
        print("Ogohlantirish: qalin shrift aniqlanmadi; bosh so'zlar ajratilmadi.", file=sys.stderr)
    Path(a.articles).parent.mkdir(parents=True, exist_ok=True)
    with open(a.articles, "w", encoding="utf-8") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    write_review(out, a.review)
    print(f"{len(out)} ta yozuv -> {a.articles}; ko'rib chiqish jadvali -> {a.review}")


def build_article(art, n, vol, src):
    hw_raw = " ".join(art["hw"]).strip(" ,")
    m = HOMONYM_RE.match(hw_raw)
    homonym = None
    base = hw_raw
    if m and m.group(2):
        base, homonym = m.group(1).strip(), m.group(2)
    raw_text = "\n".join(l["text"] for l in art["lines"])
    # bosh so'zdan keyingi matn
    first = art["lines"][0]["tokens"][len(art["hw"]):]
    rest_tokens = list(first) + [t for l in art["lines"][1:] for t in l["tokens"]]
    body = " ".join(t["t"] for t in rest_tokens)
    body = re.sub(r"(\w)- (\w)", r"\1\2", body)  # satr oxiridagi bo'g'in ko'chirish (taxminiy)
    issues = []
    ety = None
    em = ETYM_RE.match(body)
    if em:
        ety = em.group(1).strip()
        body = body[em.end():]
    senses = split_senses(rest_tokens, body, issues)
    xrefs = [{"marker": x.group(1), "target_raw": x.group(2).strip()} for x in XREF_RE.finditer(body)]
    pdf_pages = art["pdf_pages"]
    if len(pdf_pages) > 1:
        issues.append("spans_pages")
    if len(set(c[-1] for c in art["cols"])) > 1 and len(pdf_pages) == 1:
        issues.append("spans_columns")
    if homonym:
        issues.append("homonym_marker_detected_check_visually")
    if any(p is None for p in art["printed_pages"]):
        issues.append("printed_page_unknown")
    return {
        "article_id": f"v{vol}-p{pdf_pages[0]:04d}-{n:04d}", "headword_raw": hw_raw,
        "headword_search_key": search_key(base), "homonym_marker": homonym, "senses": senses,
        "cross_references": xrefs, "etymology_raw": ety, "source_file": src, "volume": vol,
        "pdf_pages": pdf_pages, "printed_pages": art["printed_pages"], "raw_text": raw_text,
        "extraction_method": "pdf_text_layer/pdfplumber+rules", "extraction_status": STATUS, "issues": issues,
    }


def split_senses(tokens, body, issues):
    """Ma'no raqamlari: qalin raqam tokenlari ('1', '2.' ...). Raqam yo'q bo'lsa — bitta ma'no."""
    idx = [i for i, t in enumerate(tokens) if t["b"] and re.fullmatch(r"\d{1,2}\.?", t["t"])]
    nums = [int(tokens[i]["t"].rstrip(".")) for i in idx]
    if nums and nums != list(range(1, len(nums) + 1)):
        issues.append(f"sense_numbers_not_sequential:{nums}")
    chunks = []
    if not idx:
        chunks.append((None, tokens))
    else:
        if idx[0] > 0:
            chunks.append(("pre", tokens[:idx[0]]))
        for k, i in enumerate(idx):
            end = idx[k + 1] if k + 1 < len(idx) else len(tokens)
            chunks.append((tokens[i]["t"].rstrip("."), tokens[i + 1:end]))
    senses = []
    for num, toks in chunks:
        if num == "pre":
            # birinchi raqamdan oldingi umumiy belgilar (turkum va h.k.)
            pre = " ".join(t["t"] for t in toks).strip()
            if pre:
                issues.append("text_before_first_sense_number")
                senses.append({"sense_number": None, "role": "pre_sense_text", "text_raw": pre})
            continue
        text = " ".join(t["t"] for t in toks).strip()
        ety = ETYM_RE.match(text)
        if ety:
            text = text[ety.end():].strip()
        mk = MARK_RE.match(text)
        marks = mk.group(1).split() if mk else []
        if mk:
            text = text[mk.end():].strip()
        # misollar: kursiv tokenlar ketma-ketligi
        examples, buf = [], []
        defin = []
        for t in toks:
            if t["i"]:
                buf.append(t["t"])
            else:
                if buf:
                    examples.append(" ".join(buf))
                    buf = []
                if not examples:
                    defin.append(t["t"])
        if buf:
            examples.append(" ".join(buf))
        definition = " ".join(defin).strip()
        if mk:
            definition = definition[len(mk.group(1).strip()):].strip() if definition.startswith(
                mk.group(1).strip()) else definition
        senses.append({
            "sense_number": num, "grammatical_style_marks_raw": marks, "definition_raw": definition,
            "examples_raw": examples, "example_sources": [],  # manba ajratish tekshirilmagan
            "text_raw": text,
        })
    if not any(t["i"] for t in tokens):
        issues.append("no_italic_detected_examples_not_separated")
    return senses


def write_review(arts, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["article_id", "volume", "pdf_pages", "printed_pages", "headword_raw", "homonym_marker",
                    "n_senses", "cross_references", "etymology_raw", "issues", "extraction_status",
                    "reviewer_headword_ok", "reviewer_senses_ok", "reviewer_examples_ok", "reviewer_note"])
        for r in arts:
            w.writerow([r["article_id"], r["volume"], ";".join(map(str, r["pdf_pages"])),
                        ";".join("" if p is None else str(p) for p in r["printed_pages"]), r["headword_raw"],
                        r["homonym_marker"], len([s for s in r["senses"] if s.get("role") != "pre_sense_text"]),
                        " | ".join(f'{x["marker"]} {x["target_raw"]}' for x in r["cross_references"]),
                        r["etymology_raw"], ";".join(r["issues"]), r["extraction_status"], "", "", "", ""])


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--min-free-mb", type=int, default=MIN_FREE_MB_DEFAULT)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("probe"); p.add_argument("pdf"); p.add_argument("--out", required=True)
    p.add_argument("--scan-first", type=int, default=40)
    p = sp.add_parser("extract"); p.add_argument("pdf"); p.add_argument("--pages", required=True)
    p.add_argument("--volume", type=int, required=True); p.add_argument("--outdir", required=True)
    p = sp.add_parser("render"); p.add_argument("pdf"); p.add_argument("--pages", required=True)
    p.add_argument("--outdir", required=True); p.add_argument("--dpi", type=int, default=100)
    p = sp.add_parser("ocr"); p.add_argument("pdf"); p.add_argument("--pages", required=True)
    p.add_argument("--outdir", required=True); p.add_argument("--lang", default="uzb_cyrl+uzb")
    p.add_argument("--allow-more", action="store_true")
    p = sp.add_parser("segment"); p.add_argument("--pages-jsonl", required=True)
    p.add_argument("--volume", type=int, required=True); p.add_argument("--articles", required=True)
    p.add_argument("--review", required=True)
    a = ap.parse_args()
    {"probe": cmd_probe, "extract": cmd_extract, "render": cmd_render, "ocr": cmd_ocr,
     "segment": cmd_segment}[a.cmd](a)


if __name__ == "__main__":
    main()
