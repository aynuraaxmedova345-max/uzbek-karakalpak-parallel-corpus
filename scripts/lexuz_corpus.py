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

DOCS = [
    ("01", "jeneva_I", "-2629153"),
    ("02", "jeneva_III", "-2660045"),
    ("03", "jeneva_IV", "-2665470"),
    ("04", "protokol_I", "-2674804"),
    ("05", "protokol_II", "-2698725"),
    ("06", "cedaw", "-2685528"),
    ("07", "fsxp_fakultativ", "-2702116"),
    ("08", "kishinyov_konv", "-4907818"),
    ("09", "xalqaro_shart_qonun", "-4193761"),
    ("10", "diplomat_tayinlash", "-19064"),
    ("11", "diplomat_daraja", "-19189"),
    ("12", "inson_huquq_strat", "-4872355"),
    ("13", "jeneva_qoshilish", "-2659335"),
]

CSV_FIELDS = [
    "raqam", "fayl", "hujjat_nomi", "sana", "URL", "yozuv", "norasmiy_tarjima",
    "moddalar_soni", "so'zlar_soni", "toliq", "yuklangan_sana",
]

# Hujjat matni joylashishi mumkin bo'lgan konteynerlar (probe natijasida aniqlanadi/tasdiqlanadi).
CONTENT_SELECTORS = ["#divCont", ".docBody", "#docBody", ".document-text", "article"]
# Korpusga kirmasligi kerak bo'lgan elementlar (sharhlar, interfeys, skriptlar).
DROP_SELECTORS = [
    "script", "style", "noscript", "nav", "header", "footer", "form", "button",
    ".lx_comment", ".COMMENT", ".comment", ".lx-comment", ".dropdown-menu",
]
BLOCK_TAGS = {"p", "div", "br", "h1", "h2", "h3", "h4", "h5", "h6", "li", "tr", "table"}

ARTICLE_RE = re.compile(r"^\s*(\d+)\s*[-–]\s*modda\b", re.IGNORECASE | re.MULTILINE)
CYR_RE = re.compile(r"[Ѐ-ӿ]")
LAT_RE = re.compile(r"[A-Za-zÀ-ɏʻʼ]")
WORD_RE = re.compile(r"[\wʻʼ'‘’`-]+", re.UNICODE)


# ---------------------------------------------------------------- tarmoq

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
            except requests.RequestException as e:
                self.last = time.time()
                last_err = str(e)
            print(f"  ! {url}: {last_err} (urinish {attempt + 1})", file=sys.stderr)
        raise RuntimeError(f"{url}: {last_err}")

    def check_robots(self):
        r = self.get(BASE + "/robots.txt")
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
    for sel in ["#docMenu", ".doc-menu", ".docMenu", "#treeMenu", ".content-menu", ".toc"]:
        for el in soup.select(sel):
            nums += article_numbers("\n".join(node_to_lines(el)))
    return max(nums) if nums else None


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
    for sel in [".ACT_TITLE", "h1", "title"]:
        el = soup.select_one(sel)
        if el and el.get_text(strip=True):
            return re.sub(r"\s+", " ", el.get_text(" ", strip=True))
    return lines[0] if lines else ""


DATE_RE = re.compile(r"\b(\d{1,2}\.\d{1,2}\.\d{4})\b")


def doc_date(lines):
    for ln in lines[:15] + lines[-15:]:
        m = DATE_RE.search(ln)
        if m:
            return m.group(1)
    return ""


# ---------------------------------------------------------------- rejimlar

def probe(client):
    num, name, doc_id = next(d for d in DOCS if d[0] == "07")
    url = URL_TMPL.format(id=doc_id)
    print("robots.txt:\n" + client.check_robots())
    print(f"{url} ruxsat etilganmi: {client.allowed(url)}")
    if not client.allowed(url):
        return
    r = client.get(url)
    HTML_DIR.mkdir(parents=True, exist_ok=True)
    out = HTML_DIR / f"{num}_{name}.html"
    out.write_text(r.text, encoding="utf-8")
    soup = BeautifulSoup(r.text, "html.parser")
    print(f"HTML saqlandi: {out} ({len(r.text)} belgi)")

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
    print("\n".join("  | " + ln for ln in lines[:40]))
    print("  ...\n  oxiri:")
    print("\n".join("  | " + ln for ln in lines[-15:]))


def fetch(client, only):
    client.check_robots()
    for d in (RAW_DIR, HTML_DIR, META_DIR):
        d.mkdir(parents=True, exist_ok=True)
    rows, report = [], []
    for num, name, doc_id in DOCS:
        if only and num not in only:
            continue
        url = URL_TMPL.format(id=doc_id)
        print(f"[{num}] {name} <- {url}")
        issues = []
        if not client.allowed(url):
            report.append((num, name, 0, "yo'q", ["robots.txt ruxsat bermaydi"]))
            continue
        try:
            r = client.get(url)
        except RuntimeError as e:
            report.append((num, name, 0, "yo'q", [f"yuklanmadi: {e}"]))
            continue
        (HTML_DIR / f"{num}_{name}.html").write_text(r.text, encoding="utf-8")
        soup = BeautifulSoup(r.text, "html.parser")
        sel, content = find_content(soup)
        if content is None:
            report.append((num, name, 0, "yo'q", ["matn konteyneri topilmadi (JS?)"]))
            continue
        lines = node_to_lines(content)
        text = "\n".join(lines) + "\n"
        fname = f"{num}_{name}.txt"
        (RAW_DIR / fname).write_text(text, encoding="utf-8")

        cyr_share, script = script_stats(text)
        if script != "lotin":
            issues.append(f"kirill ulushi {cyr_share:.1%}")
        unofficial = "norasmiy tarjima" in text.lower() or "норасмий таржима" in text.lower()
        arts = article_numbers(text)
        n_arts = max(arts) if arts else 0
        toc_last = toc_last_article(soup)
        words = len(WORD_RE.findall(text))
        if toc_last is None:
            complete = "shubhali" if not arts else "ha"
            if not arts:
                issues.append("moddalar topilmadi")
            else:
                issues.append("mundarija topilmadi — faqat matndagi moddalar ketma-ketligi tekshirildi")
                missing = sorted(set(range(1, n_arts + 1)) - set(arts))
                if missing:
                    complete = "shubhali"
                    issues.append(f"tushib qolgan moddalar: {missing[:10]}")
        elif toc_last == n_arts:
            complete = "ha"
        else:
            complete = "yo'q"
            issues.append(f"mundarijada {toc_last}-modda, matnda oxirgisi {n_arts}")
        if words < 1500 and not arts:
            links = external_links(content)
            if links:
                complete = "shubhali"
                issues.append("faqat qo'shilish qarori bo'lishi mumkin; havolalar: "
                              + "; ".join(f"{t} -> {u}" for t, u in links[:5]))

        rows.append({
            "raqam": num, "fayl": f"data/raw/{fname}", "hujjat_nomi": page_title(soup, lines),
            "sana": doc_date(lines), "URL": url, "yozuv": script,
            "norasmiy_tarjima": "ha" if unofficial else "yo'q", "moddalar_soni": n_arts,
            "so'zlar_soni": words, "toliq": complete, "yuklangan_sana": date.today().isoformat(),
        })
        report.append((num, name, words, complete, issues))

    write_sources(rows)
    print_report(report)


def write_sources(rows):
    existing = {}
    if SOURCES_CSV.exists():
        with SOURCES_CSV.open(encoding="utf-8") as f:
            existing = {r["raqam"]: r for r in csv.DictReader(f)}
    for r in rows:
        existing[r["raqam"]] = r
    with SOURCES_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        w.writeheader()
        for k in sorted(existing):
            w.writerow(existing[k])


def print_report(report):
    print("\n| № | Hujjat | So'zlar | To'liq | Muammolar |\n|---|---|---:|---|---|")
    for num, name, words, complete, issues in report:
        print(f"| {num} | {name} | {words} | {complete} | {'; '.join(issues) or '—'} |")
    print(f"\nJami korpus: {sum(r[2] for r in report)} so'z, {len(report)} hujjat")
    bad = [r for r in report if r[3] != "ha" or r[4]]
    if bad:
        print("\nMuammoli hujjatlar:")
        for num, name, _, complete, issues in bad:
            print(f"  - {num} {name} ({complete}): {'; '.join(issues)}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("probe")
    f = sub.add_parser("fetch")
    f.add_argument("--confirmed", action="store_true", help="HTML tuzilishi tasdiqlangan")
    f.add_argument("--only", nargs="*", default=[])
    args = ap.parse_args()
    client = Client()
    if args.cmd == "probe":
        probe(client)
    else:
        if not args.confirmed:
            sys.exit("Avval `probe` natijasini tasdiqlang, keyin --confirmed bilan ishga tushiring.")
        fetch(client, set(args.only))


if __name__ == "__main__":
    main()
