#!/usr/bin/env python3
"""data/meta/typos_noticed.csv ni qo'lda tekshirilgan ro'yxatdan yaratadi (repo ildizidan ishga tushiring).

Matn tuzatilmaydi: faqat saytdagi xatolar qayd etiladi."""
import csv, re, sys
B = "buzilgan_belgi"      # harf o'rnida "?"
G = "bo'shliq_tushgan"    # so'zlar qo'shilib ketgan
P = "tinish_belgisidan_keyin_bo'shliq_yo'q"
I = "imlo"
ITEMS = [
 ("03_jeneva_IV.txt", "136-moddadakoʻzda", G, "moddada koʻzda"),
 ("05_protokol_II.txt", "Jyeneva", I, "Jeneva"),
 ("06_cedaw.txt", "ahloqiy", I, "axloqiy"),
 ("06_cedaw.txt", "hususiy", I, "xususiy"),
 ("06_cedaw.txt", "ijgimoiy", I, "ijtimoiy"),
 ("06_cedaw.txt", "konsenpsiyasini", I, "konsepsiyasini"),
 ("06_cedaw.txt", "miqiyosda", I, "miqyosda"),
 ("06_cedaw.txt", "ommalashgirish", I, "ommalashtirish"),
 ("06_cedaw.txt", "tabiyasi", I, "tarbiyasi"),
 ("06_cedaw.txt", "toʻgʻisidagi", I, "toʻgʻrisidagi"),
 ("06_cedaw.txt", "vaqgda", I, "vaqtda"),
 ("06_cedaw.txt", "xaftadan", I, "haftadan"),
 ("06_cedaw.txt", "zrkaklar", I, "erkaklar"),
 ("07_fsxp_fakultativ.txt", "Protkolning", I, "Protokolning"),
 ("07_fsxp_fakultativ.txt", "Tashqiloti", I, "Tashkiloti"),
 ("08_kishinyov_konv.txt", "bir-birilariga", I, "bir-birlariga"),
 ("09_xalqaro_shart_qonun.txt", "oʻzgartishlar", I, "oʻzgartirishlar"),
 ("10_diplomat_tayinlash.txt", "qiritadi", I, "kiritadi"),
 ("11_diplomat_daraja.txt", "Boshka", I, "Boshqa"),
 ("11_diplomat_daraja.txt", "Tashkent", I, "Toshkent"),
 ("03_jeneva_IV.txt", "xolida", I, "holida"),
 ("12_inson_huquq_strat.txt", "BTMning", I, "BMTning"),
 ("12_inson_huquq_strat.txt", "qarmogʻida", I, "qaramogʻida"),
] + [("12_inson_huquq_strat.txt", w, B, "") for w in
     ["ul?rning", "?larning", "shakl?aridan", "tash?iliy", "Ban?lik", "taʼm?nlanganlik", "bila?",
      "suiiste?mol", "?aktabgacha", "?av?iyalar?i", "maʼlumo?larni"]
] + [("12_inson_huquq_strat.txt", w, G, "") for w in
     ["aniqlashningtartibi", "institutinitakomillashtirish", "ishlarinitashkil", "kuchaytirishnazarda",
      "mexanizmlarinitakomillashtirish", "mustahkamlashnazarda", "nazoratnitashkil", "organlarifaoliyatining",
      "oshirishnazarda", "qilishningtashkiliy", "savdosigaqarshi", "shakliniamalga", "shaxslarhuquqlarini",
      "sohasinitakomillashtirish", "strategiyasiniishlab", "subyektlarqatoriga", "tahririloyihasini",
      "takomillashtirishhamda", "tartibinitaʼminlash", "tayyorgarlikdanteng", "taʼminlashtartibi",
      "vakolatlarinibelgilash", "funksiyalariva", "antikorrupsiyaviychoralarni", "huquqlariva",
      "oshirishva", "taraqqiyotva"]
] + [("01_jeneva_I.txt", "xususan,ularni", P, "")] + [("12_inson_huquq_strat.txt", w, P, "") for w in
     ["vazifalari,funksiyalariva", "palatasi,Oliy", "taʼminlash,prokurorlar", "soddalashtirish,uning",
      "loyihasi,Chora-tadbirlar", "vazirligi,Yoshlar", "qilinadi,aholining", "vakil,Bosh",
      "vazirligi,Mahalla", "prokuratura,Davlat"]]

# x/h almashinuvi: xollari, xollarida, xollarni
for f, w in [("03_jeneva_IV.txt", "xollari"), ("03_jeneva_IV.txt", "xollarida"), ("02_jeneva_III.txt", "xollarni")]:
    ITEMS.append((f, w, I, "h" + w[1:]))

rows = []
for f, w, kind, note in ITEMS:
    t = open(f"data/raw/{f}", encoding="utf-8").read()
    hits = [m for m in re.finditer(r"(?<![\wʻʼ?])" + re.escape(w) + r"(?![\wʻʼ?])", t)]
    if not hits:
        sys.exit(f"TOPILMADI: {f} {w}")
    m = hits[0]
    ctx = t[max(0, m.start() - 50):m.end() + 50].replace("\n", " ⏎ ")
    rows.append({"fayl": f, "soʻz": w, "kontekst": "…" + ctx + "…", "tur": kind,
                 "ehtimoliy_toʻgʻri_shakl": note, "uchrash_soni": len(hits)})
rows.sort(key=lambda r: (r["fayl"], r["tur"], r["soʻz"].lower()))
with open("data/meta/typos_noticed.csv", "w", encoding="utf-8", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]))
    w.writeheader(); w.writerows(rows)
from collections import Counter
print(len(rows), Counter((r["fayl"][:2], r["tur"]) for r in rows))
