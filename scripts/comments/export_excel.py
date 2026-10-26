#!/usr/bin/env python3
"""Yig'ilgan izohlarni annotatsiya uchun qulay Excel faylga aylantirish.

  python scripts/comments/export_excel.py \
      --matches data/comments/izohlar_mosliklar.csv \
      --all data/comments/ochiq_izohlar.csv \
      --out data/comments/izohlar.xlsx

Varaqlar: Umumiy (statistika, formulalar bilan), Iboralar, Ko'chma so'zlar,
Barcha izohlar. Izoh matnida topilgan parcha qizil qalin harf bilan ajratiladi,
"Tekshiruv" ustuni uchun ha / yo'q / shubhali ro'yxati bor.
"""

from __future__ import annotations

import argparse
import csv
import re
from collections import Counter
from pathlib import Path

from openpyxl import Workbook
from openpyxl.cell.rich_text import CellRichText, TextBlock
from openpyxl.cell.text import InlineFont
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

FONT = "Arial"
HEADER_FILL = PatternFill("solid", start_color="1F4E78")
HEADER_FONT = Font(name=FONT, bold=True, color="FFFFFF", size=10)
BODY_FONT = Font(name=FONT, size=10)
INPUT_FILL = PatternFill("solid", start_color="FFF2CC")   # annotator to'ldiradigan ustunlar
ZEBRA_FILL = PatternFill("solid", start_color="F3F6FA")
THIN = Side(style="thin", color="D0D7E2")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
WRAP_TOP = Alignment(wrap_text=True, vertical="top")
TOP = Alignment(vertical="top")
CENTER_TOP = Alignment(horizontal="center", vertical="top")

SOURCE_NAMES = {"google_play": "Google Play", "restoran": "Restoran", "youtube": "YouTube",
                "telegram": "Telegram", "file": "Fayl"}
SENTIMENT_NAMES = {"positive": "ijobiy", "negative": "salbiy", "neutral": "neytral",
                   "mixed": "aralash", "conflict": "aralash", "": ""}

_APOS = "'‘’ʻʼ`´"


def span_regex(span: str) -> re.Pattern:
    """Normallashtirilgan parchani asl matnda topish uchun: tutuq belgilari ixtiyoriy."""
    parts = []
    for ch in span:
        if ch in _APOS:
            continue
        if ch.isspace() or ch in "-":
            parts.append(r"[\s\-–—]+")
        else:
            parts.append(re.escape(ch) + f"[{_APOS}]?")
    return re.compile("".join(parts), re.IGNORECASE)


def highlight(text: str, spans: list[str]):
    """Matndagi topilgan parchalarni qizil qalin qilib ajratadi."""
    ranges = []
    for span in spans:
        m = span_regex(span).search(text)
        if m:
            ranges.append(m.span())
    if not ranges:
        return text
    ranges.sort()
    merged = [list(ranges[0])]
    for s, e in ranges[1:]:
        if s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    plain = InlineFont(rFont=FONT, sz=10)
    hot = InlineFont(rFont=FONT, sz=10, b=True, color="C00000")
    rich = CellRichText()
    pos = 0
    for s, e in merged:
        if s > pos:
            rich.append(TextBlock(plain, text[pos:s]))
        rich.append(TextBlock(hot, text[s:e]))
        pos = e
    if pos < len(text):
        rich.append(TextBlock(plain, text[pos:]))
    return rich


def write_table(ws, headers, rows, widths, wrap_cols=(), center_cols=(), input_cols=()):
    ws.append(headers)
    for c, _ in enumerate(headers, 1):
        cell = ws.cell(row=1, column=c)
        cell.font, cell.fill, cell.border = HEADER_FONT, HEADER_FILL, BORDER
        cell.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
    ws.row_dimensions[1].height = 42
    for r, row in enumerate(rows, 2):
        for c, value in enumerate(row, 1):
            cell = ws.cell(row=r, column=c, value=value)
            cell.border = BORDER
            if not isinstance(value, CellRichText):
                cell.font = BODY_FONT
            cell.alignment = WRAP_TOP if c in wrap_cols else CENTER_TOP if c in center_cols else TOP
            if c in input_cols:
                cell.fill = INPUT_FILL
            elif r % 2 == 1:
                cell.fill = ZEBRA_FILL
    for c, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(c)].width = w
    last = len(rows) + 1
    ws.freeze_panes = "B2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{max(last, 2)}"
    return last


def add_check_column(ws, col: int, last: int):
    letter = get_column_letter(col)
    dv = DataValidation(type="list", formula1='"ha,yo\'q,shubhali"', allow_blank=True,
                        promptTitle="Tekshiruv", prompt="ha - ko'chma/frazeologik ma'noda;\n"
                        "yo'q - to'g'ri ma'noda yoki xato topilgan;\nshubhali - aniq emas")
    ws.add_data_validation(dv)
    dv.add(f"{letter}2:{letter}{last}")
    rng = f"A2:{get_column_letter(ws.max_column)}{last}"
    ws.conditional_formatting.add(rng, FormulaRule(
        formula=[f'${letter}2="ha"'], fill=PatternFill("solid", start_color="E2EFDA")))
    ws.conditional_formatting.add(rng, FormulaRule(
        formula=[f'${letter}2="yo\'q"'], fill=PatternFill("solid", start_color="FCE4E4")))


def match_sheet(wb, title, rows, kind):
    ws = wb.create_sheet(title)
    # Bitta izohdagi barcha parchalar har bir qatorda ajratilsin.
    spans_by_comment: dict[str, list[str]] = {}
    for r in rows:
        spans_by_comment.setdefault(r["izoh_id"], []).append(r["topilgan_qism"])
    extra_header = "Lug'at sahifasi" if kind == "frazeologik" else "Uslub belgisi"
    headers = ["№", "Izoh ID", "Manba", "Sentiment", "Izoh matni", "Topilgan parcha",
               "Leksikon birligi", "Lug'aviy izoh (ma'nosi)", extra_header,
               "Tekshiruv\n(ha / yo'q / shubhali)", "Annotator izohi"]
    data = []
    for i, r in enumerate(rows, 1):
        data.append([
            i, r["izoh_id"], SOURCE_NAMES.get(r["manba"], r["manba"]),
            SENTIMENT_NAMES.get(r.get("sentiment", ""), r.get("sentiment", "")),
            highlight(r["izoh_matni"], [r["topilgan_qism"]]),
            r["topilgan_qism"], r["birlik"].replace(" || ", "\n"),
            r["izoh_manosi"].replace(" || ", "\n").replace(" | ", "\n"),
            r["manba_sahifa"] if kind == "frazeologik" else r["uslub"],
            r.get("tekshiruv_belgisi", ""), "",
        ])
    last = write_table(ws, headers, data,
                       widths=[6, 14, 12, 10, 60, 24, 28, 50, 12, 14, 24],
                       wrap_cols=(5, 6, 7, 8, 11), center_cols=(1, 3, 4, 9, 10),
                       input_cols=(10, 11))
    add_check_column(ws, 10, last)
    return ws, last


def all_sheet(wb, comments, matched_ids):
    ws = wb.create_sheet("Barcha izohlar")
    headers = ["№", "Izoh ID", "Manba", "Sentiment", "Izoh matni", "Moslik bormi", "Dataset"]
    data = [[i, c["id"], SOURCE_NAMES.get(c["source"], c["source"]),
             SENTIMENT_NAMES.get(c.get("sentiment", ""), c.get("sentiment", "")),
             c["text"], "ha" if c["id"] in matched_ids else "yo'q", c.get("dataset", "")]
            for i, c in enumerate(comments, 1)]
    last = write_table(ws, headers, data, widths=[7, 14, 12, 10, 80, 10, 50],
                       wrap_cols=(5,), center_cols=(1, 3, 4, 6))
    return ws, last


def summary_sheet(ws, fraz_last, koch_last, all_last, top_items, sources):
    ws.title = "Umumiy"
    ws.sheet_view.showGridLines = False
    ws.column_dimensions["A"].width = 46
    ws.column_dimensions["B"].width = 14
    ws.column_dimensions["C"].width = 14
    ws.column_dimensions["D"].width = 14
    ws.column_dimensions["E"].width = 14

    def h(cell, text, size=10):
        ws[cell] = text
        ws[cell].font = Font(name=FONT, bold=True, size=size, color="1F4E78")

    def header_row(row, labels):
        for c, label in enumerate(labels, 1):
            cell = ws.cell(row=row, column=c, value=label)
            cell.font, cell.fill, cell.border = HEADER_FONT, HEADER_FILL, BORDER
            cell.alignment = Alignment(horizontal="center" if c > 1 else "left", vertical="center")

    def body(row, values, pct_cols=()):
        for c, v in enumerate(values, 1):
            cell = ws.cell(row=row, column=c, value=v)
            cell.font, cell.border = BODY_FONT, BORDER
            if c > 1:
                cell.alignment = Alignment(horizontal="center")
                cell.number_format = "0.0%" if c in pct_cols else "#,##0"

    h("A1", "Frazeologik va ko'chma ma'noli birliklar qatnashgan izohlar", 14)
    ws["A2"] = ("Manba: GitHub'dagi ochiq datasetlar (Google Play ilova sharhlari, UzABSA restoran "
                "sharhlari). Leksikonlar: frazeologik_lugat.csv, kochma_leksikon.csv.")
    ws["A2"].font = Font(name=FONT, size=9, italic=True, color="595959")

    F, K, A = "Iboralar", "'Ko''chma so''zlar'", "'Barcha izohlar'"

    # 1. Manbalar bo'yicha
    h("A4", "1. Manbalar bo'yicha")
    header_row(5, ["Manba", "Jami izoh", "Mos izohlar", "Ulushi"])
    r = 6
    for key in sources:
        name = SOURCE_NAMES.get(key, key)
        body(r, [name,
                 f'=COUNTIF({A}!$C$2:$C${all_last},A{r})',
                 f'=COUNTIFS({A}!$C$2:$C${all_last},A{r},{A}!$F$2:$F${all_last},"ha")',
                 f"=IF(B{r}=0,0,C{r}/B{r})"], pct_cols=(4,))
        r += 1
    body(r, ["Jami", f"=SUM(B6:B{r-1})", f"=SUM(C6:C{r-1})", f"=IF(B{r}=0,0,C{r}/B{r})"], pct_cols=(4,))
    for c in range(1, 5):
        ws.cell(row=r, column=c).font = Font(name=FONT, size=10, bold=True)
    r += 2

    # 2. Leksikonlar bo'yicha va tekshiruv holati
    h(f"A{r}", "2. Leksikonlar bo'yicha va tekshiruv holati")
    r += 1
    header_row(r, ["Varaq", "Mosliklar", "ha", "yo'q", "Tekshirilmagan"])
    r += 1
    for label, sheet, last in (("Frazeologik iboralar", F, fraz_last), ("Ko'chma so'zlar", K, koch_last)):
        body(r, [label,
                 f"=COUNTA({sheet}!$A$2:$A${last})",
                 f'=COUNTIF({sheet}!$J$2:$J${last},"ha")',
                 f'=COUNTIF({sheet}!$J$2:$J${last},"yo\'q")',
                 f'=COUNTBLANK({sheet}!$J$2:$J${last})'])
        r += 1
    r += 1

    # 3. Eng ko'p uchragan iboralar
    h(f"A{r}", "3. Eng ko'p uchragan frazeologik iboralar")
    r += 1
    header_row(r, ["Ibora", "Soni"])
    r += 1
    for item in top_items:
        body(r, [item, f'=COUNTIF({F}!$G$2:$G${fraz_last},A{r})'])
        ws.cell(row=r, column=1).alignment = Alignment(wrap_text=True, vertical="top")
        ws.cell(row=r, column=2).alignment = Alignment(horizontal="center", vertical="top")
        lines = item.count("\n") + 1 + len(item) // 60
        if lines > 1:
            ws.row_dimensions[r].height = 13 * lines
        r += 1
    r += 1

    h(f"A{r}", "Qanday ishlatiladi")
    notes = [
        "• Iboralar va Ko'chma so'zlar varaqlarida sariq ustun - annotator to'ldiradi.",
        "• Tekshiruv: ro'yxatdan ha / yo'q / shubhali tanlang; qator yashil yoki qizil rangga kiradi.",
        "• Izoh matnida topilgan parcha qizil qalin harf bilan ajratilgan.",
        "• Ko'chma so'zlar ko'pincha to'g'ri ma'noda keladi - ularni ayniqsa diqqat bilan tekshiring.",
        "• Har ustun sarlavhasida filtr bor; bitta izohda bir nechta birlik bo'lsa, u bir necha qatorda keladi.",
    ]
    for n in notes:
        r += 1
        ws[f"A{r}"] = n
        ws[f"A{r}"].font = Font(name=FONT, size=10)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--matches", default="data/comments/izohlar_mosliklar.csv")
    p.add_argument("--all", default="data/comments/ochiq_izohlar.csv")
    p.add_argument("--out", default="data/comments/izohlar.xlsx")
    p.add_argument("--top", type=int, default=20)
    args = p.parse_args()

    with open(args.matches, encoding="utf-8-sig", newline="") as fh:
        matches = list(csv.DictReader(fh))
    with open(args.all, encoding="utf-8-sig", newline="") as fh:
        comments = list(csv.DictReader(fh))

    fraz = [m for m in matches if m["leksikon"] == "frazeologik"]
    koch = [m for m in matches if m["leksikon"] == "kochma"]
    matched_ids = {m["izoh_id"] for m in matches}

    wb = Workbook()
    summary = wb.active
    _, fraz_last = match_sheet(wb, "Iboralar", fraz, "frazeologik")
    _, koch_last = match_sheet(wb, "Ko'chma so'zlar", koch, "kochma")
    _, all_last = all_sheet(wb, comments, matched_ids)

    top_items = [item.replace(" || ", "\n") for item, _ in
                 Counter(m["birlik"] for m in fraz).most_common(args.top)]
    sources = list(dict.fromkeys(c["source"] for c in comments))
    summary_sheet(summary, fraz_last, koch_last, all_last, top_items, sources)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out)
    print(f"Saqlandi: {out}  (iboralar: {len(fraz)}, ko'chma: {len(koch)}, jami izoh: {len(comments)})")


if __name__ == "__main__":
    main()
