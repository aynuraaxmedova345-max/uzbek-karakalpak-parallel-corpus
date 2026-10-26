# Sun'iy (sintetik) izohlar dataseti

2 000 ta ijtimoiy tarmoq uslubidagi o'zbekcha izoh:

| Fayl | Mazmuni |
|---|---|
| `sintetik_frazeologik.csv` | 1 000 ta izoh, har birida `frazeologik_lugat.csv` dagi bitta ibora (1 000 xil ibora) |
| `sintetik_kochma.csv` | 1 000 ta izoh, har birida `kochma_leksikon.csv` dagi bitta so'z **ko'chma ma'noda** (1 000 xil so'z) |
| `sintetik_izohlar.csv` | ikkalasi birga (2 000 qator) |
| `sintetik_izohlar.xlsx` | Excel: Umumiy (statistika), Frazeologik, Ko'chma; birlik izohda qizil bilan ajratilgan, tekshiruv uchun ha/yo'q ro'yxati bor |
| `raw/` | qo'lda yozilgan barcha izohlar (1 336 + 1 507) va ular yozilgan leksikon nomzodlari |

## Ustunlar

| Ustun | Mazmuni |
|---|---|
| `id` | `F0001…` (frazeologik), `K0001…` (ko'chma) |
| `kategoriya` | `frazeologik ibora` yoki `ko'chma ma'noli so'z` |
| `izoh` | izoh matni |
| `birlik` | leksikondagi ibora / so'z |
| `topilgan_qism` | izohdagi aynan shu birlik qatnashgan parcha |
| `manosi` | lug'atdagi frazeologik yoki ko'chma ma'no (izoh shu ma'noga mos yozilgan) |
| `togri_manosi` | so'zning to'g'ri (asl) ma'nosi — faqat ko'chma so'zlar uchun, farqni ko'rsatish uchun |
| `sentiment` | `ijobiy` / `salbiy` / `neytral` |
| `emotsiya` | `xursandchilik`, `g'azab`, `qayg'u`, `qo'rquv`, `hayrat`, `jirkanish`, `neytral` |
| `platforma` | izoh uslubi: `Telegram`, `Instagram`, `YouTube` |
| `leksikon_manbasi` | lug'at sahifasi yoki ko'chma leksikondagi `id` va ma'no raqami |

## Qanday tayyorlangan

1. Leksikonlardan izohi aniq, hozirgi tilda ishlatiladigan birliklar tanlandi
   (arxaik, OCR'da buzilgan va ma'nosi noaniq yozuvlar tashlab yuborildi).
2. Har bir birlikning lug'atdagi **ko'chma / frazeologik ma'nosi** va to'g'ri
   ma'nosi solishtirib o'qildi, so'ng izoh aynan ko'chma ma'noda yozildi
   (masalan, `bo'ron` — "savollar bo'roni", `beshik` — "Buxoro — ilm beshigi",
   `chirog'` — "kenja qizim uyimizning chirog'i").
3. Har bir izohga sentiment, emotsiya va platforma belgisi qo'yildi.
4. `scripts/comments/lexicon.py` bilan avtomatik tekshirildi: izohda aynan
   mo'ljallangan birlik topilmasa, u tashlab yuborildi (iboralarda 1 255/1 336,
   ko'chma so'zlarda 1 323/1 507 o'tdi).
5. Tekshiruvdan o'tganlar orasidan alifbo bo'ylab teng taqsimlangan 1 000 tadan
   izoh tanlandi.

Qayta yig'ish:

```bash
python scripts/comments/build_synthetic.py --n 1000
```

## Cheklovlar

- Izohlar sun'iy: real foydalanuvchilar yozmagan. Ular haqiqiy izohlarga
  o'xshatib yozilgan, lekin tabiiy izohlardagi imlo xatolari, sheva va aralash
  tillar kamroq uchraydi.
- Sentiment va emotsiya belgilari bitta muallif tomonidan qo'yilgan;
  annotatsiya uchun ishlatishdan oldin ikkinchi annotator bilan tekshirish
  tavsiya etiladi (`sintetik_izohlar.xlsx` dagi `Tekshiruv` ustuni shu uchun).
- Iboralarda salbiy izohlar ko'proq (565/1 000), chunki o'zbek frazeologizmlarining
  katta qismi salbiy baho bildiradi.
