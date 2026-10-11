#!/usr/bin/env python3
"""lex.uz dan xalqaro huquq hujjatlarining o'zbekcha matnlarini yuklab, korpus tayyorlash.

Ishlatish:
    python scripts/lexuz_corpus.py probe          # 1-qadam: faqat 07-hujjat, HTML tuzilishini o'rganish
    python scripts/lexuz_corpus.py fetch --confirmed   # barcha hujjatlar (tuzilish tasdiqlangandan keyin)
    python scripts/lexuz_corpus.py fetch --confirmed --only 01 02

Skript matnni hech qachon o'zgartirmaydi yoki to'ldirmaydi: faqat HTML'dagi
matn tugunlari olinadi, bo'shliqlar normallashtiriladi, xolos.
"""

import argparse
import csv
import random
import re
import sys
import time
from collections import Counter
from datetime import date
from pathlib import Path
from urllib import robotparser

import requests
from bs4 import BeautifulSoup, NavigableString, Tag

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
HTML_DIR = ROOT / "data" / "html"
META_DIR = ROOT / "data" / "meta"
SOURCES_CSV = META_DIR / "sources.csv"

BASE = "https://lex.uz"
URL_TMPL = BASE + "/uz/docs/{id}"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
DELAY_RANGE = (3.0, 5.0)
MAX_RETRIES = 2

# (raqam, nom, lex.uz id, qatlam, soha)
XS, MH = "xalqaro_shartnoma", "milliy_hujjat"
DOCS = [
    ("01", "jeneva_I", "-2629153", XS, "gumanitar_huquq"),
    ("02", "jeneva_III", "-2660045", XS, "gumanitar_huquq"),
    ("03", "jeneva_IV", "-2665470", XS, "gumanitar_huquq"),
    ("04", "protokol_I", "-2674804", XS, "gumanitar_huquq"),
    ("05", "protokol_II", "-2698725", XS, "gumanitar_huquq"),
    ("06", "cedaw", "-2685528", XS, "inson_huquqlari"),
    ("07", "fsxp_fakultativ", "-2702116", XS, "inson_huquqlari"),
    ("08", "kishinyov_konv", "-4907818", XS, "huquqiy_yordam"),
    ("09", "xalqaro_shart_qonun", "-4193761", MH, "shartnomalar_huquqi"),
    ("10", "diplomat_tayinlash", "-19064", MH, "diplomatik_huquq"),
    ("11", "diplomat_daraja", "-19189", MH, "diplomatik_huquq"),
    ("12", "inson_huquq_strat", "-4872355", MH, "inson_huquqlari"),
    ("13", "jeneva_qoshilish", "-2659335", MH, "gumanitar_huquq"),
    ("14", "jeneva_II", "-2627590", XS, "gumanitar_huquq"),
]

# Qo'lda tekshirilgan tuzatishlar (foydalanuvchi qarori bilan): ustun -> qiymat
OVERRIDES = {
    "08": {
        "uz_kuchga_kirgan": "",
        "izoh": "Saytdagi 12.07.1994 sanasi ziddiyatli. O'zbekiston 26.08.2019 dagi O'RQ-554 qonuni "
                "bilan qo'shilgan: https://lex.uz/acts/-4487576",
    },
}

CSV_FIELDS = [
    "raqam", "fayl", "hujjat_nomi", "sana", "URL", "yozuv", "norasmiy_tarjima",
    "moddalar_soni", "so'zlar_soni", "toliq", "yuklangan_sana",
    "uz_kuchga_kirgan", "qoshilish_qarori_url", "qatlam", "soha", "izoh",
]

# lex.uz tuzilishi (07-hujjat probe natijasi bo'yicha):
#   #divCont          — hujjat matni (server tomonida render qilinadi, JS shart emas)
#   .lx_elem2         — har paragraf ichidagi tugmalar ("Hujjatga taklif yuborish" va h.k.)
#   .INDEXES_ON_REF   — OKOZ/TSZ klassifikator indekslari
#   .COMMENT          — "LexUZ sharhi" (tahririyat izohi)
#   .UNOFFIAL         — "Norasmiy tarjima" belgisi
#   .CHANGES_ORIGINS  — "(... Qonuni tahririda ...)" tahrir manbasi izohi
#   .PUBLICATION_ORIGIN — "(Qonun hujjatlari maʼlumotlari milliy bazasi ...)" nashr manbasi
#   #dvToc            — mundarija (matndan tashqarida)
CONTENT_SELECTORS = ["#divCont"]
# Korpusga kirmasligi kerak bo'lgan elementlar (sharhlar, interfeys, skriptlar).
DROP_SELECTORS = [
    "script", "style", "noscript", "button", "img",
    ".lx_elem2", ".INDEXES_ON_REF", ".COMMENT", ".UNOFFIAL", ".CHANGES_ORIGINS", ".PUBLICATION_ORIGIN",
    ".COMMENT_FOR_WARNING",
]
SUPERSCRIPT = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")
TOC_SELECTOR = "#dvToc"
BLOCK_TAGS = {"p", "div", "br", "h1", "h2", "h3", "h4", "h5", "h6", "li", "tr", "table"}

ARTICLE_RE = re.compile(r"^\s*(\d+)\s*[-–]\s*modda\b", re.IGNORECASE | re.MULTILINE)
CYR_RE = re.compile(r"[Ѐ-ӿ]")
LAT_RE = re.compile(r"[A-Za-zÀ-ɏʻʼ]")
WORD_RE = re.compile(r"[\wʻʼ'‘’`-]+", re.UNICODE)


# ---------------------------------------------------------------- tarmoq

class HTTPClientError(RuntimeError):
    def __init__(self, status, msg):
        super().__init__(msg)
        self.status = status


class Client:
    def __init__(self):
        self.s = requests.Session()
        self.s.headers.update({
            "User-Agent": USER_AGENT,
            "Accept-Language": "uz,ru;q=0.8,en;q=0.6",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })
        self.last = 0.0
        self.robots = None

    def _wait(self):
        delay = random.uniform(*DELAY_RANGE)
        elapsed = time.time() - self.last
        if elapsed < delay:
            time.sleep(delay - elapsed)

    def get(self, url):
        last_err = None
        for attempt in range(1 + MAX_RETRIES):
            self._wait()
            try:
                r = self.s.get(url, timeout=60)
                self.last = time.time()
                if r.status_code == 200:
                    r.encoding = r.apparent_encoding if not r.encoding or r.encoding.lower() == "iso-8859-1" else r.encoding
                    return r
                last_err = f"HTTP {r.status_code}"
                if 400 <= r.status_code < 500 and r.status_code != 429:
                    raise HTTPClientError(r.status_code, f"{url}: {last_err}")
            except requests.RequestException as e:
                self.last = time.time()
                last_err = str(e)
            print(f"  ! {url}: {last_err} (urinish {attempt + 1})", file=sys.stderr)
        raise RuntimeError(f"{url}: {last_err}")

    def check_robots(self):
        try:
            r = self.get(BASE + "/robots.txt")
        except HTTPClientError as e:
            # robots.txt yo'q (404) — standart bo'yicha cheklov yo'q
            self.robots = None
            return f"(robots.txt topilmadi: HTTP {e.status} — cheklov yo'q deb hisoblanadi)"
        rp = robotparser.RobotFileParser()
        rp.parse(r.text.splitlines())
        self.robots = rp
        return r.text

    def allowed(self, url):
        return self.robots is None or self.robots.can_fetch(USER_AGENT, url)


# ---------------------------------------------------------------- tahlil

def find_content(soup):
    for sel in CONTENT_SELECTORS:
        node = soup.select_one(sel)
        if node and len(node.get_text(strip=True)) > 200:
            return sel, node
    return None, None


def node_to_lines(node):
    """Blok elementlar chegarasida qator ajratib, matnni o'zgartirmasdan oladi."""
    node = BeautifulSoup(str(node), "html.parser")
    for sel in DROP_SELECTORS:
        for el in node.select(sel):
            el.decompose()
    # "23<sup>1</sup>" -> "23¹" (aks holda "231" bo'lib qo'shilib ketadi)
    for el in node.select("sup"):
        t = el.get_text()
        el.replace_with(t.translate(SUPERSCRIPT) if t.strip().isdigit() else t)
    parts = []

    def walk(el):
        for child in el.children:
            if isinstance(child, NavigableString):
                parts.append(str(child))
            elif isinstance(child, Tag):
                block = child.name in BLOCK_TAGS
                if block:
                    parts.append("\n")
                walk(child)
                if block:
                    parts.append("\n")

    walk(node)
    text = "".join(parts).replace("\xa0", " ")
    lines = [re.sub(r"[ \t\r\f\v]+", " ", ln).strip() for ln in text.split("\n")]
    return [ln for ln in lines if ln]


def script_stats(text):
    cyr = len(CYR_RE.findall(text))
    lat = len(LAT_RE.findall(text))
    total = cyr + lat
    share = cyr / total if total else 0.0
    return share, ("kirill" if share > 0.5 else "lotin")


def article_numbers(text):
    return [int(m.group(1)) for m in ARTICLE_RE.finditer(text)]


def toc_last_article(soup):
    """Sahifadagi mundarija (agar bo'lsa) dan oxirgi modda raqami."""
    nums = []
    for el in soup.select(TOC_SELECTOR):
        nums += article_numbers("\n".join(node_to_lines(el)))
    return max(nums) if nums else None


def toc_missing(soup, content):
    """Mundarijadagi bandlar (scrollText('ID')) matnda borligini tekshiradi."""
    ids = re.findall(r"scrollText\('([^']+)'\)", str(soup.select_one(TOC_SELECTOR) or ""))
    missing = [i for i in ids if not content.find(id=i) or not content.find(id=i).get_text(strip=True)]
    return len(ids), missing


def lexuz_comments(content):
    """LexUZ sharhlari (korpusga kirmaydi) — matni va undagi hujjat havolalari."""
    out = []
    for el in content.select(".COMMENT"):
        out.append((re.sub(r"\s+", " ", el.get_text(" ", strip=True)), external_links(el)))
    return out


def external_links(content):
    """Qo'shilish qarori sahifasidagi boshqa lex.uz hujjatlariga havolalar."""
    out = []
    for a in content.select("a[href]"):
        href = a["href"]
        if "/docs/" in href:
            full = href if href.startswith("http") else BASE + href
            out.append((a.get_text(" ", strip=True), full))
    return out


def page_title(soup, lines):
    """<title> odatda "DD.MM.YYYY. Nomi" ko'rinishida: sanani olib tashlab nomni qaytaradi."""
    parts = [re.sub(r"\s+", " ", el.get_text(" ", strip=True))
             for el in soup.select("#divCont .ACT_TITLE > div[id], #divCont .ACT_FORM > div[id]")]
    if parts:
        return " ".join(parts)
    el = soup.select_one("title")
    if el and el.get_text(strip=True):
        return re.sub(r"^\d{1,2}\.\d{1,2}\.\d{4}\.\s*", "", re.sub(r"\s+", " ", el.get_text(" ", strip=True)))
    return lines[0] if lines else ""


DATE_RE = re.compile(r"\b(\d{1,2}\.\d{1,2}\.\d{4})\b")


def doc_date(soup, lines):
    el = soup.select_one("title")
    if el:
        # "DD.MM.YYYY. Nomi" yoki "649-XII-сон DD.MM.YYYY. Nomi"
        m = re.match(r"^(?:\S+\s+)?(\d{1,2}\.\d{1,2}\.\d{4})\.", el.get_text(strip=True))
        if m:
            return m.group(1)
    for ln in lines[:15] + lines[-15:]:
        m = DATE_RE.search(ln)
        if m:
            return m.group(1)
    return ""


# ---------------------------------------------------------------- rejimlar

def probe(client, local=False):
    num, name, doc_id = next(d for d in DOCS if d[0] == "07")[:3]
    url = URL_TMPL.format(id=doc_id)
    out = HTML_DIR / f"{num}_{name}.html"
    if local and out.exists():
        html = out.read_text(encoding="utf-8")
        print(f"Saqlangan HTML ishlatildi (saytga so'rov yuborilmadi): {out}")
    else:
        print("robots.txt:\n" + client.check_robots())
        print(f"{url} ruxsat etilganmi: {client.allowed(url)}")
        if not client.allowed(url):
            return
        html = client.get(url).text
        HTML_DIR.mkdir(parents=True, exist_ok=True)
        out.write_text(html, encoding="utf-8")
        print(f"HTML saqlandi: {out} ({len(html)} belgi)")
    soup = BeautifulSoup(html, "html.parser")

    # Eng ko'p matnli id/class lar — tuzilishni o'rganish uchun
    counts = Counter()
    for el in soup.find_all(True):
        n = len(el.get_text(strip=True))
        key = el.name + (f"#{el['id']}" if el.get("id") else "") + "".join(f".{c}" for c in el.get("class", []))
        counts[key] = max(counts[key], n)
    print("\nEng ko'p matn saqlagan elementlar:")
    for key, n in counts.most_common(25):
        print(f"  {n:>8}  {key}")
    classes = Counter(c for el in soup.find_all(True) for c in el.get("class", []))
    print("\nEng ko'p uchraydigan classlar:", classes.most_common(40))

    sel, content = find_content(soup)
    print(f"\nTanlangan konteyner: {sel}")
    if content is None:
        print("Matn konteyneri topilmadi — ehtimol JavaScript orqali yuklanadi (Playwright kerak).")
        return
    lines = node_to_lines(content)
    print(f"Qatorlar: {len(lines)}; boshi:")
    print("\n".join("  | " + ln for ln in lines[:25]))
    print("  ...\n  oxiri:")
    print("\n".join("  | " + ln for ln in lines[-15:]))

    text = "\n".join(lines) + "\n"
    share, script = script_stats(text)
    arts = article_numbers(text)
    print("\nTekshiruvlar:")
    print(f"  nomi: {page_title(soup, lines)}")
    print(f"  sana: {doc_date(soup, lines)}")
    print(f"  yozuv: {script} (kirill ulushi {share:.2%})")
    print(f"  norasmiy tarjima: {'ha' if soup.select('#divCont .UNOFFIAL') else 'yo`q'}")
    print(f"  mundarijadagi oxirgi modda: {toc_last_article(soup)}; matndagi oxirgi: {max(arts) if arts else None}")
    print(f"  so'zlar: {len(WORD_RE.findall(text))}; qatorlar: {len(lines)}")
    for t, links in lexuz_comments(content):
        print(f"  LexUZ sharhi (chiqarib tashlandi): {t}")
        for lt, lu in links:
            print(f"     havola: {lt} -> {lu}")


REMOVED_CSV = META_DIR / "removed_lines.csv"
TYPOS_CSV = META_DIR / "typos_noticed.csv"

UZ_MONTHS = {
    "yanvar": 1, "fevral": 2, "mart": 3, "aprel": 4, "may": 5, "iyun": 6, "iyul": 7,
    "avgust": 8, "sentabr": 9, "sentyabr": 9, "oktabr": 10, "oktyabr": 10, "noyabr": 11, "dekabr": 12,
}
# "(Oʻzbekiston Respublikasi uchun 1995-yil 28-dekabrdan kuchga kirgan)" kabi qavsli izohlar
UZ_FORCE_RE = re.compile(r"^\(.*kuchga\s+kir.*\)$", re.IGNORECASE)
UZ_FORCE_DATE_RE = re.compile(r"(\d{4})\s*-\s*yil\s+(\d{1,2})\s*-\s*([a-zʻʼ'‘’]+)", re.IGNORECASE)
SIGNATURES_RE = re.compile(r"^\(\s*imzolar\s*\)$", re.IGNORECASE)
ACCESSION_RE = re.compile(r"qo.?shil|ratifika", re.IGNORECASE)


def uz_force_date(line):
    m = UZ_FORCE_DATE_RE.search(line)
    if not m:
        return line
    month = next((n for k, n in UZ_MONTHS.items() if m.group(3).lower().startswith(k)), None)
    return f"{int(m.group(2)):02d}.{month:02d}.{m.group(1)}" if month else line


def download(client, only, cached):
    client.check_robots()
    HTML_DIR.mkdir(parents=True, exist_ok=True)
    failed = {}
    for num, name, doc_id, *_ in DOCS:
        if only and num not in only:
            continue
        url = URL_TMPL.format(id=doc_id)
        out = HTML_DIR / f"{num}_{name}.html"
        if cached and out.exists():
            print(f"[{num}] {name}: saqlangan HTML ishlatiladi")
            continue
        if not client.allowed(url):
            failed[num] = "robots.txt ruxsat bermaydi"
            continue
        print(f"[{num}] {name} <- {url}")
        try:
            out.write_text(client.get(url).text, encoding="utf-8")
        except RuntimeError as e:
            failed[num] = f"yuklanmadi: {e}"
    return failed


def process(only, failed=None):
    """Saqlangan HTML'lardan toza matn, sources.csv va removed_lines.csv tayyorlaydi."""
    failed = failed or {}
    for d in (RAW_DIR, META_DIR):
        d.mkdir(parents=True, exist_ok=True)
    rows, report, removed = [], [], []
    for num, name, doc_id, layer, domain in DOCS:
        if only and num not in only:
            continue
        url = URL_TMPL.format(id=doc_id)
        html_path = HTML_DIR / f"{num}_{name}.html"
        fname = f"{num}_{name}.txt"
        if num in failed or not html_path.exists():
            report.append(dict(num=num, name=name, words=0, complete="yo'q", toc=None, text_last=None,
                               unofficial="", issues=[failed.get(num, "HTML yo'q")]))
            continue
        soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "html.parser")
        issues = []
        sel, content = find_content(soup)
        if content is None:
            report.append(dict(num=num, name=name, words=0, complete="yo'q", toc=None, text_last=None,
                               unofficial="", issues=["matn konteyneri topilmadi (JS?)"]))
            continue

        if content.select(".COMMENT_FOR_WARNING"):
            issues.append("sahifada o'zbekcha matn yo'q: \"Hujjat matni rus tilida berilgan\"")
        # Korpusdan chiqariladigan, lekin qayd etiladigan elementlar
        for cls, reason in [(".INDEXES_ON_REF", "OKOZ/TSZ klassifikator indeksi"),
                            (".UNOFFIAL", "\"Norasmiy tarjima\" belgisi (sources.csv da qayd etilgan)"),
                            (".COMMENT", "LexUZ sharhi"),
                            (".CHANGES_ORIGINS", "tahrir manbasi izohi (LexUZ)"),
                            (".PUBLICATION_ORIGIN", "rasmiy nashr manbasi (LexUZ)")]:
            for el in content.select(cls):
                removed.append((fname, re.sub(r"\s+", " ", el.get_text(" ", strip=True)), reason))
        uz_force = []
        for el in content.select(".TEXT_CENTER"):
            t = re.sub(r"\s+", " ", el.get_text(" ", strip=True))
            if UZ_FORCE_RE.match(t):
                uz_force.append(uz_force_date(t))
                removed.append((fname, t, "O'zbekiston uchun kuchga kirish izohi (uz_kuchga_kirgan ustuniga)"))
                el.decompose()

        lines = []
        for ln in node_to_lines(content):
            if SIGNATURES_RE.match(ln):
                removed.append((fname, ln, "\"(imzolar)\" belgisi"))
            else:
                lines.append(ln)
        text = "\n".join(lines) + "\n"
        (RAW_DIR / fname).write_text(text, encoding="utf-8")

        cyr_share, script = script_stats(text)
        if script != "lotin" or cyr_share > 0.01:
            issues.append(f"kirill harflar ulushi {cyr_share:.1%}")
        unofficial = bool(soup.select("#divCont .UNOFFIAL")) or "norasmiy tarjima" in text.lower()
        arts = article_numbers(text)
        n_arts = max(arts) if arts else 0
        toc_last = toc_last_article(soup)
        words = len(WORD_RE.findall(text))
        missing = sorted(set(range(1, n_arts + 1)) - set(arts))
        n_toc, toc_gone = toc_missing(soup, content)
        complete = "ha"
        if toc_gone:
            complete = "yo'q"
            issues.append(f"mundarijadagi {len(toc_gone)}/{n_toc} band matnda yo'q")
        if not arts:
            issues.append(f"\"N-modda\" tuzilishi yo'q (mundarija bandlari: {n_toc}, hammasi matnda)"
                          if n_toc and not toc_gone else "\"N-modda\" tuzilishi yo'q, mundarija ham yo'q")
            if not n_toc:
                # mundarija yo'q: hujjat oxiridagi rekvizit (raqam) bo'lsa, matn oxirigacha olingan
                if content.select(".ACT_ESSENTIAL_ELEMENTS_NUM"):
                    issues[-1] += "; oxiridagi rekvizitlar (sana, raqam) mavjud"
                else:
                    complete = "shubhali"
        elif toc_last is not None and toc_last != n_arts:
            complete = "yo'q"
            issues.append(f"mundarijada oxirgi {toc_last}-modda, matnda {n_arts}-modda")
        if content.select(".COMMENT_FOR_WARNING"):
            complete = "yo'q"
        if missing:
            complete = "shubhali" if complete == "ha" else complete
            issues.append(f"matnda tushib qolgan modda raqamlari: {missing[:15]}")

        # Qo'shilish/ratifikatsiya qarorlari: LexUZ sharhidagi havolalar (yuklanmaydi)
        accession = []
        for t, links in lexuz_comments(content):
            if ACCESSION_RE.search(t):
                accession += [u for _, u in links]
        title = page_title(soup, lines)
        # Sahifaning o'zi qaror bo'lsa — shartnoma matniga havolalarni ko'rsatish
        body = BeautifulSoup(str(content), "html.parser")
        for el in body.select(".COMMENT"):
            el.decompose()
        body_links = external_links(body)
        if not arts and ACCESSION_RE.search(title):
            treaty_links = [(t, u) for t, u in body_links if "#" not in u]
            issues.append("sahifa — qo'shilish qarori, shartnoma matnlari boshqa havolalarda (yuklanmadi): "
                          + ("; ".join(f"{t} -> {u}" for t, u in treaty_links) or "havola yo'q"))

        rows.append({
            "raqam": num, "fayl": f"data/raw/{fname}", "hujjat_nomi": title,
            "sana": doc_date(soup, lines), "URL": url, "yozuv": script,
            "norasmiy_tarjima": "ha" if unofficial else "yo'q", "moddalar_soni": n_arts,
            "so'zlar_soni": words, "toliq": complete,
            "yuklangan_sana": date.fromtimestamp(html_path.stat().st_mtime).isoformat(),
            "uz_kuchga_kirgan": "; ".join(uz_force),
            "qoshilish_qarori_url": "; ".join(dict.fromkeys(accession)),
            "qatlam": layer, "soha": domain, "izoh": "",
        })
        rows[-1].update(OVERRIDES.get(num, {}))
        report.append(dict(num=num, name=name, words=words, complete=complete, toc=toc_last,
                           text_last=n_arts, unofficial="ha" if unofficial else "yo'q", issues=issues))

    write_sources(rows)
    write_removed(removed, {f"{d[0]}_{d[1]}.txt" for d in DOCS if not only or n in only})
    print_report(report)


def write_removed(removed, files):
    keep = []
    if REMOVED_CSV.exists():
        with REMOVED_CSV.open(encoding="utf-8") as f:
            keep = [r for r in csv.DictReader(f) if r["fayl"] not in files]
    with REMOVED_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["fayl", "qator_matni", "sabab"])
        w.writeheader()
        w.writerows(keep)
        for fname, t, reason in removed:
            w.writerow({"fayl": fname, "qator_matni": t, "sabab": reason})


def write_sources(rows):
    existing = {}
    if SOURCES_CSV.exists():
        with SOURCES_CSV.open(encoding="utf-8") as f:
            existing = {r["raqam"]: r for r in csv.DictReader(f)}
    for r in rows:
        existing[r["raqam"]] = r
    with SOURCES_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS, restval="")
        w.writeheader()
        for k in sorted(existing):
            w.writerow(existing[k])


def print_report(report):
    print("\n| № | Hujjat | So'zlar | Mundarija / matn (oxirgi modda) | Norasmiy | To'liq | Muammolar |")
    print("|---|---|---:|---|---|---|---|")
    for r in report:
        print(f"| {r['num']} | {r['name']} | {r['words']} | {r['toc']} / {r['text_last']} | "
              f"{r['unofficial']} | {r['complete']} | {'; '.join(r['issues']) or '—'} |")
    print(f"\nJami korpus: {sum(r['words'] for r in report)} so'z, {len(report)} hujjat")
    bad = [r for r in report if r["complete"] != "ha"]
    if bad:
        print("\nKesilgan yoki shubhali hujjatlar:")
        for r in bad:
            print(f"  - {r['num']} {r['name']} ({r['complete']}): {'; '.join(r['issues'])}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    pr = sub.add_parser("probe")
    pr.add_argument("--local", action="store_true", help="saqlangan HTML'dan foydalanish (so'rovsiz)")
    f = sub.add_parser("fetch")
    f.add_argument("--confirmed", action="store_true", help="HTML tuzilishi tasdiqlangan")
    f.add_argument("--only", nargs="*", default=[])
    f.add_argument("--cached", action="store_true", help="mavjud HTML'larni qayta yuklamaslik")
    pc = sub.add_parser("process", help="faqat saqlangan HTML'larni qayta ishlash (so'rovsiz)")
    pc.add_argument("--only", nargs="*", default=[])
    args = ap.parse_args()
    if args.cmd == "probe":
        probe(Client(), args.local)
    elif args.cmd == "process":
        process(set(args.only))
    else:
        if not args.confirmed:
            sys.exit("Avval `probe` natijasini tasdiqlang, keyin --confirmed bilan ishga tushiring.")
        failed = download(Client(), set(args.only), args.cached)
        process(set(args.only), failed)


if __name__ == "__main__":
    main()
