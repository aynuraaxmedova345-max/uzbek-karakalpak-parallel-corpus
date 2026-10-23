# PROJECT_STATE — UzWordNet × Izohli lug'at

Oxirgi yangilanish: 2026-10-23. Bosqich: **0 — inventarizatsiya; PDF pilot bloklangan.**

## Bajarilgan ish

- Sessiya diski, shu repo branchlari va foydalanuvchining GitHub repolari qidirildi.
- Topilgan 3 ta Excel read-only o'qildi: varaqlar, sarlavhalar, qator soni, SHA-256 → `output/manifest.json`.
- RC1.1 hujjatidagi qator sonlari Excel bilan qayta sanalib tasdiqlandi.
- RC1.1 asl manba fayllari ro'yxati tiklandi (fayllarning o'zi yo'q).
- PDF pilot skripti (`scripts/pdf_pilot.py`), manifest skripti va sintetik o'z-o'zini sinash yozildi; sintetik sinov o'tdi.
- PDF bilan ishlash, maqola ajratish, OCR — **bajarilmadi** (PDF yo'q).

## Ishlatilgan fayllar (faqat o'qildi, o'zgartirilmadi)

| Fayl | Joyi | SHA-256 |
|---|---|---|
| uzwordnet_rc1_1.xlsx | github: aynuraaxmedova345-max/uzwordnet-explorer@main (commit 0d50d17), `application/` | f6f19d56c238852fd8d508c189b07ba3370d39494e4479c60d11bcb3c6ad38d0 |
| izohli_lugat_clean.xlsx | shu repo, branch `claude/quirky-einstein-103ocw`, `data/source/` | 8f4e0e3cead4be7f03d785497cbd23981dd134bcd0f195e088eea0027d91bbf0 |
| Namuna_Talaba_201.xlsx | github: aynuraaxmedova345-max/sinset-tekshiruvchi@main, `samples/` | eb1bab2934aa30298798e2686dcd7392e0c6f6d9232d0a54c7a67c082b6d7c2a |

## Sinov sahifalari

Yo'q. 1-jild PDF'i mavjud emas.

## Yaratilgan natijalar

- `output/manifest.json`
- `output/01_inventory.md`
- `output/02_pdf_pilot_report.md`
- `scripts/pdf_pilot.py`, `scripts/build_manifest.py`, `scripts/selftest_synthetic.py`, `scripts/requirements.txt`
- Yaratilmagan (ma'lumot yo'q): `extracted/volume_1/pilot_pages.jsonl`, `extracted/volume_1/pilot_articles.jsonl`, `output/pilot_review.csv`

## Topilgan muammolar

1. Izohli lug'at PDF'lari yo'q — asosiy to'siq.
2. Ikki asl UzWordNet Excel dataseti yo'q; qaysi ikkitasi nazarda tutilgani noma'lum (nomzodlar `01_inventory.md` 2.1 da).
3. Audit notebooki yo'q — ustun indekslari va sinonim tekshiruvi baholanmadi.
4. `izohli_lugat_clean.xlsx` da jild/PDF sahifasi va xom matn yo'q → manbaga bog'lab bo'lmaydi; 7 065 qator `needs_review=True`.
5. Bu ish muhitida Tesseract yo'q (foydalanuvchi kompyuterida ham tekshirilishi kerak).
6. Repo (`uzbek-karakalpak-parallel-corpus`) **ochiq**: shaxsiy datasetlar va mualliflik huquqi bilan himoyalangan PDF'larni bu yerga commit qilmaslik kerak. `.gitignore` `input/`, `dictionaries/`, sahifa rasmlari va OCR fayllarini chiqarib tashlaydi.

## Keyingi bajariladigan vazifa

1. 1-jild PDF'ini `uzwordnet_audit/dictionaries/` ga, ikki Excel va notebookni `uzwordnet_audit/input/` ga qo'yish
   (yoki ularni shaxsiy repoga yuklab, manzilini aytish).
2. Manifestni qayta yaratish, notebookni o'qish (ishga tushirmasdan).
3. `probe` → titul/qisqartmalar/birinchi maqola sahifasini PNG'da qo'lda tasdiqlash → 10 sahifa `extract` → 2–3 sahifani `render` qilib taqqoslash → `segment` → `pilot_review.csv` ni ekspert ko'rib chiqishi.

## Qayta boshlash buyrug'i

Windows (PowerShell), repo ildizidan; bir vaqtda faqat bitta buyruq:

```powershell
cd uzwordnet_audit
python -m pip install -r scripts/requirements.txt
python scripts/selftest_synthetic.py
python scripts/build_manifest.py --root . --out output/manifest.json
python scripts/pdf_pilot.py probe dictionaries/<1-JILD>.pdf --out output/pdf_probe_v1.json --scan-first 40
# probe natijasini va PNG'ni ko'rib, birinchi maqola sahifasini (S) qo'lda tasdiqlang:
python scripts/pdf_pilot.py render  dictionaries/<1-JILD>.pdf --pages S-S+2 --outdir extracted/volume_1/page_images
python scripts/pdf_pilot.py extract dictionaries/<1-JILD>.pdf --pages S-S+9 --volume 1 --outdir extracted/volume_1
python scripts/pdf_pilot.py segment --pages-jsonl extracted/volume_1/pilot_pages.jsonl --volume 1 `
    --articles extracted/volume_1/pilot_articles.jsonl --review output/pilot_review.csv
# Matn qatlami yaroqsiz bo'lsa (probe: no_text_layer/suspect) — faqat 3 sahifa:
python scripts/pdf_pilot.py ocr dictionaries/<1-JILD>.pdf --pages S-S+2 --outdir extracted/volume_1/ocr_test
```

`extract` 3-kod bilan to'xtasa — xotira kam: boshqa dasturlarni yopib, xuddi shu buyruqni qayta bering (davom etadi).
