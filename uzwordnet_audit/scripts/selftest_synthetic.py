#!/usr/bin/env python3
"""pdf_pilot.py mexanikasini SINTETIK (o'ylab topilgan) PDFda sinash.

Bu yerdagi "maqolalar" haqiqiy lug'at matni EMAS — faqat dastur ishlashini
tekshirish uchun yasalgan belgilar. Natija vaqtinchalik papkaga yoziladi va
loyiha natijalariga qo'shilmaydi.

  python selftest_synthetic.py
Talab: reportlab va oddiy/qalin/kursiv TTF shriftlar (bo'lmasa sinov o'tkazib yuboriladi).
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
FONT_SETS = [
    ("/usr/share/fonts/truetype/dejavu", "DejaVuSans.ttf", "DejaVuSans-Bold.ttf", "DejaVuSans-Oblique.ttf"),
    ("/usr/share/fonts/truetype/freefont", "FreeSans.ttf", "FreeSansBold.ttf", "FreeSansOblique.ttf"),
    ("C:/Windows/Fonts", "arial.ttf", "arialbd.ttf", "ariali.ttf"),
]

# (bosh so'z, matn bo'laklari) — har bo'lak: (matn, uslub) ; uslub: r=oddiy, b=qalin, i=kursiv
ENTRIES = [("ТЕСТНОЛ", [("Чегараларни сурувчи синтетик матн. " * 2, "r")])] + [
    ("ТЕСТА", [("[синт.]", "r"), ("от", "r"), ("Синтетик таъриф бир.", "r"), ("Синтетик мисол гап.", "i"),
               ("Муаллиф, Асар.", "r")]),
    ("ТЕСТБ¹", [("1", "b"), ("Биринчи синтетик маъно.", "r"), ("2", "b"), ("Иккинчи синтетик маъно.", "r")]),
    ("ТЕСТБ²", [("Омоним синтетик таъриф.", "r")]),
    ("ТЕСТВ", [("Айн.", "r"), ("тесто.", "r")]),
    ("ТЕСТГ", [("Узун синтетик таъриф " * 12, "r")]),  # ustun/sahifa o'rtasida uzilishi uchun
] * 40


def build_pdf(path, fonts):
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas
    pdfmetrics.registerFont(TTFont("R", str(fonts["r"])))
    pdfmetrics.registerFont(TTFont("B", str(fonts["b"])))
    pdfmetrics.registerFont(TTFont("I", str(fonts["i"])))
    W, H = 595, 842
    c = canvas.Canvas(str(path), pagesize=(W, H))
    cols = [(40, 280), (315, 555)]
    page_no, col, y = 101, 0, H - 80

    def new_page():
        nonlocal page_no
        c.setFont("R", 9)
        c.drawString(W / 2, 30, str(page_no))
        c.showPage()
        page_no += 1

    for hw, parts in ENTRIES:
        x0, x1 = cols[col]
        x = x0
        tokens = [(hw, "b")] + [(w, st) for txt, st in parts for w in txt.split()]
        for t, st in tokens:
            font = {"r": "R", "b": "B", "i": "I"}[st]
            wdt = pdfmetrics.stringWidth(t + " ", font, 10)
            if x + wdt > x1:
                y -= 14
                x = x0 + 8
            if y < 70:
                col += 1
                if col == 2:
                    new_page()
                    col = 0
                y = H - 80
                x0, x1 = cols[col]
                x = x0 + 8
            c.setFont(font, 10)
            c.drawString(x, y, t)
            x += wdt
        y -= 18
    new_page()
    c.save()


def main():
    try:
        import reportlab  # noqa
    except ImportError:
        print("reportlab yo'q — sinov o'tkazib yuborildi")
        return 0
    fonts = None
    for d, r, b, i in FONT_SETS:
        d = Path(d)
        cand = {"r": d / r, "b": d / b, "i": d / i}
        if all(p.exists() for p in cand.values()):
            fonts = cand
            break
    if not fonts:
        print("Mos TTF shriftlar topilmadi — sinov o'tkazib yuborildi")
        return 0
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        pdf = td / "synthetic.pdf"
        build_pdf(pdf, fonts)
        run = lambda *a: subprocess.run([sys.executable, str(HERE / "pdf_pilot.py"), *a], check=True,
                                        capture_output=True, text=True)
        run("probe", str(pdf), "--out", str(td / "probe.json"), "--scan-first", "5")
        run("extract", str(pdf), "--pages", "1-2", "--volume", "0", "--outdir", str(td / "ex"))
        run("extract", str(pdf), "--pages", "1-2", "--volume", "0", "--outdir", str(td / "ex"))  # resume: no dup
        run("segment", "--pages-jsonl", str(td / "ex/pilot_pages.jsonl"), "--volume", "0",
            "--articles", str(td / "a.jsonl"), "--review", str(td / "r.csv"))
        pages = [json.loads(l) for l in open(td / "ex/pilot_pages.jsonl", encoding="utf-8")]
        arts = [json.loads(l) for l in open(td / "a.jsonl", encoding="utf-8")]
        assert len(pages) == 2, "resume duplicated pages"
        assert pages[0]["printed_page"] == 101 and pages[0]["column_order"] == ["left", "right"], pages[0]
        hws = [a["headword_raw"] for a in arts]
        assert hws[:5] == ["ТЕСТНОЛ", "ТЕСТА", "ТЕСТБ¹", "ТЕСТБ²", "ТЕСТВ"], hws[:6]
        a0, a1, a2, a3 = arts[1:5]
        assert a0["etymology_raw"] == "синт." and a0["senses"][0]["examples_raw"] == ["Синтетик мисол гап."]
        assert [s["sense_number"] for s in a1["senses"]] == ["1", "2"] and a1["homonym_marker"] == "¹"
        assert a1["headword_search_key"] == "testb"
        assert a3["cross_references"] == [{"marker": "Айн.", "target_raw": "тесто"}]
        assert all(a["extraction_status"] == "auto_unverified" for a in arts)
        spans = [a for a in arts if "spans_pages" in a["issues"] or "spans_columns" in a["issues"]]
        assert any("spans_pages" in a["issues"] for a in arts), "no cross-page article detected"
        assert any("spans_columns" in a["issues"] for a in arts), "no cross-column article detected"
        print(f"OK: {len(pages)} sahifa, {len(arts)} sintetik yozuv, ustunlar/sahifalararo: {len(spans)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
