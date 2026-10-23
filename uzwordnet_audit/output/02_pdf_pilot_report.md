# 02. PDF pilot hisoboti — 1-jild

## Holat: BAJARILMADI (PDF mavjud emas)

`dictionaries/` papkasi bo'sh; sessiyada, repoda va foydalanuvchining GitHub repolarida izohli lug'at PDF'i topilmadi.
Shu sababli quyidagilar **bajarilmadi va natija yozilmadi**:

| Band | Holat |
|---|---|
| B.1 sahifalar soni, hajm, matn qatlami | aniqlanmadi |
| B.2 titul, nashr ma'lumoti, shartli qisqartmalar | topilmadi |
| B.3 birinchi maqola sahifasi va 10 sinov sahifasi | tanlanmadi |
| B.5 matnni sahifa tasviri bilan taqqoslash | **vizual tekshirilmadi** |
| B.6 3 sahifalik OCR sinovi | bajarilmadi; bundan tashqari bu muhitda Tesseract o'rnatilmagan |
| C. kamida 20 maqola | 0 ta maqola ajratildi |

`extracted/volume_1/pilot_pages.jsonl`, `extracted/volume_1/pilot_articles.jsonl` va `output/pilot_review.csv`
ataylab yaratilmadi: bo'sh yoki o'ylab topilgan yozuvlar bilan to'ldirish noto'g'ri bo'lardi.
`izohli_lugat_clean.xlsx` (OCR jadvali) PDF o'rniga ishlatilmadi — unda PDF sahifasi, jild va xom matn yo'q.

## Tayyorlangan vositalar (foydalanuvchi kompyuterida ishga tushirish uchun)

`scripts/pdf_pilot.py` — 4 GB RAM uchun mo'ljallangan:

- sahifalar bittadan ochiladi, har sahifadan keyin `pilot_pages.jsonl` ga yoziladi va kesh bo'shatiladi;
- bo'sh xotira `--min-free-mb` (standart 600 MB) dan kam bo'lsa, yangi sahifa boshlanmaydi, `pilot_checkpoint.json` saqlanadi, chiqish kodi 3;
- qayta ishga tushirilganda tayyor sahifalar o'tkazib yuboriladi;
- multiprocessing, parallel OCR, LLM va tashqi API yo'q;
- `probe`: sahifalar soni, dastlabki N sahifada matn qatlami sifati, titul/nashr/qisqartmalar sahifalarini kalit so'z bo'yicha **taxmin qiladi** (qo'lda tasdiqlash shart);
- `extract`: ikki ustun orasidagi bo'shliqni topib, avval chap, keyin o'ng ustunni o'qiydi; kolontitul raqamini bosma sahifa deb faqat bitta aniq nomzod bo'lsa oladi, aks holda `null` + `issues`;
- `render`: tekshirish uchun bitta sahifani PNG qiladi (100 dpi);
- `ocr`: Tesseract bo'lsa, ko'pi bilan 3 sahifa, vaqtinchalik rasm keyin o'chiriladi; bo'lmasa aniq xabar beradi;
- `segment`: bosh so'z = qator boshidagi **qalin va to'liq katta harfli** token (faqat birinchi harfi katta so'z bosh so'z hisoblanmaydi); omonim belgisi faqat kichik/yuqoriga ko'tarilgan raqam bo'lsa; qalin raqamlar ma'no raqami; kursiv — misol; `[...]` — etimologiya; `Айн./Ayn./Қ./Q./қаранг/зид.` — xom havola (sinonimga aylantirilmaydi); sinov oralig'idan oldingi davom etayotgan matn alohida `-cont` yozuv bo'ladi; hamma yozuv `extraction_status=auto_unverified`.

### Mexanik sinov (faqat dastur uchun)

`scripts/selftest_synthetic.py` o'zi yasagan **sintetik** 2 ustunli PDFda (haqiqiy lug'at matni emas) tekshirdi:
ustunlar tartibi, bosma sahifa raqami, omonim belgisi vs ma'no raqami, etimologiya, kursiv misol, `Айн.` havolasi,
sahifa va ustun chegarasidan o'tuvchi yozuv, qayta ishga tushirishda takrorlanmaslik, xotira chegarasida to'xtash,
Tesseract yo'qligi xabari. Natija: `OK`. Bu haqiqiy PDFdagi aniqlikni **isbotlamaydi**: haqiqiy lug'atdagi
shriftlar, kolontitul, defis bilan ko'chirish va misol manbalari boshqacha bo'lishi mumkin.

Ma'lum cheklovlar (haqiqiy PDFda tekshirilishi kerak):
- misol manbasi (muallif, asar) avtomatik ajratilmaydi — `example_sources` bo'sh qoladi;
- grammatik/uslubiy belgilar faqat xom ko'rinishda (`grammatical_style_marks_raw`), tasniflanmagan;
- satr oxiridagi defisli ko'chirish taxminiy birlashtiriladi;
- skanerlangan (matn qatlamisiz) PDFda qalin/kursiv ma'lumoti bo'lmaydi; OCR natijasidan maqola ajratish hali yozilmagan.

## Keyingi qadam (PDF qo'yilgandan keyin)

`PROJECT_STATE.md` dagi "Qayta boshlash buyrug'i" bo'limiga qarang.
