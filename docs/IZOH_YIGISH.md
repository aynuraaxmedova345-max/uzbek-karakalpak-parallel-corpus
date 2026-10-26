# Frazeologik va ko'chma ma'noli birliklar bo'yicha izoh yig'ish

Bu vosita ijtimoiy tarmoqlardagi izohlardan (kommentlardan) **frazeologik iboralar**
va **ko'chma ma'noli so'zlar** qatnashganlarini avtomatik ajratib oladi.

Ishlatiladigan leksikonlar:

| Fayl | Mazmuni | Hajmi |
|---|---|---:|
| `data/lexicons/frazeologik_lugat.csv` | iboralar, izohi, variantlari | 4 092 yozuv |
| `data/lexicons/kochma_leksikon.csv` | ko'chma ma'noga ega so'zlar | 2 526 ma'no (≈2 000 so'z) |

Variantlar (`qo'llanish` ustunidagi `Varianti: ...`) ham alohida izlanadi, shuning
uchun jami ≈7 000 ta izlash namunasi hosil bo'ladi.

## O'rnatish

```bash
pip install -r scripts/comments/requirements.txt
```

## Ishlatish

### 1. YouTube

API kaliti kerak emas.

```bash
# Aniq videolar
python scripts/comments/collect_comments.py youtube \
    --url "https://www.youtube.com/watch?v=VIDEO_ID" \
    --url "https://www.youtube.com/watch?v=VIDEO_ID_2"

# Qidiruv bo'yicha: har so'rovdan 20 ta video
python scripts/comments/collect_comments.py youtube \
    --search "o'zbek film" --search "kulgu shou" --search "intervyu" \
    --videos-per-query 20

# Kanalning oxirgi videolari
python scripts/comments/collect_comments.py youtube --channel @kunuzofficial --videos-per-query 30
```

### 2. Telegram

1. <https://my.telegram.org> → *API development tools* bo'limidan `api_id` va `api_hash` oling.
2. Ularni muhit o'zgaruvchilariga yozing va ishga tushiring (birinchi safar telefon raqam va kod so'raladi):

```bash
export TG_API_ID=1234567
export TG_API_HASH=abcdef0123456789
python scripts/comments/collect_comments.py telegram \
    --channel kunuzofficial --channel daryo_uz --posts 300
```

Faqat izoh (comments) yoqilgan kanallardan izoh olinadi.

### 3. Tayyor fayl

Izohlarni boshqa yo'l bilan yig'gan bo'lsangiz (Instagram eksporti, qo'lda
yig'ilgan jadval va h.k.):

```bash
python scripts/comments/collect_comments.py file --input izohlar.csv --text-column text
python scripts/comments/collect_comments.py file --input izohlar.jsonl --text-column text
python scripts/comments/collect_comments.py file --input izohlar.txt   # har qatorda bitta izoh
```

### 4. GitHub'dagi ochiq datasetlar

Ochiq datasetlardagi haqiqiy foydalanuvchi izohlarini (Google Play sharhlari va
restoran sharhlari) yuklab, leksikon bo'yicha tahlil qilish:

```bash
python scripts/comments/fetch_public_comments.py --out data/comments/ochiq_izohlar.csv
python scripts/comments/collect_comments.py file --input data/comments/ochiq_izohlar.csv \
    --out data/comments/izohlar_mosliklar.csv --min-length 3
```

Tayyor natijalar `data/comments/` papkasida (qarang: `data/comments/README.md`).

### 5. Sun'iy dataset

Leksikon ma'nolari asosida qo'lda yozilgan 1 000 ta frazeologik va 1 000 ta
ko'chma ma'noli izoh: `data/synthetic/` (qarang: `data/synthetic/README.md`).

```bash
python scripts/comments/build_synthetic.py --n 1000
```

### Foydali parametrlar

| Parametr | Vazifasi |
|---|---|
| `--out FILE.csv` | natija fayli (default `data/comments/izohlar_mosliklar.csv`) |
| `--lexicon frazeologik` | faqat iboralar (`kochma` – faqat ko'chma so'zlar, `both` – ikkalasi) |
| `--append` | mavjud faylga qo'shish, takroriy izohlar tashlab yuboriladi |
| `--limit 500` | 500 ta mos izoh topilgach to'xtash |
| `--gap 1` | ibora so'zlari orasida 1 ta boshqa so'z kelishiga ruxsat ("yuragim **hech** dov bermadi") |
| `--save-all all.jsonl` | barcha izohlarni ham saqlash (keyin qayta tahlil qilish uchun `file` rejimiga bering) |
| `--include-aux` | `turmoq`, `qolmoq`, `bermoq` kabi yordamchi fe'llarni ham ko'chma so'z sifatida izlash |
| `--keep-author` | muallif ismini saqlash (default: anonim xesh `u_…`) |

## Natija fayli

Har bir topilgan moslik – alohida qator (bitta izohda 2 ta ibora bo'lsa – 2 qator,
`izoh_id` bir xil bo'ladi):

| Ustun | Mazmuni |
|---|---|
| `izoh_id`, `manba`, `manba_id`, `manba_nomi` | izoh va u olingan video/post |
| `muallif`, `sana`, `layklar` | metama'lumot (muallif anonimlashtirilgan) |
| `izoh_matni` | izohning to'liq matni |
| `leksikon` | `frazeologik` yoki `kochma` |
| `birlik` | leksikondagi ibora/so'z (bir nechtasi bo'lsa ` \|\| ` bilan) |
| `topilgan_qism` | izohdagi mos kelgan parcha (normallashtirilgan) |
| `izoh_manosi` | lug'aviy / ko'chma izoh |
| `uslub`, `manba_sahifa` | leksikondagi uslub belgisi, lug'at sahifasi |
| `tekshiruv_belgisi` | bo'sh – annotator `ha` / `yo'q` deb to'ldiradi |

## Qanday izlaydi

Izohlar odatda imlo qoidasiz yoziladi, shuning uchun matn va leksikon bir xil
ko'rinishga keltiriladi:

- kirill → lotin (`кўнглим` → `ko'nglim`), kichik harf;
- `‘ ’ ʻ ʼ` belgilarining hammasi bitta `'` ga; leksikondagi `o'`/`g'` matnda
  `'` siz yozilgan bo'lsa ham topiladi (`kozim uchib`), lekin teskarisi emas
  (`qoldik` ≠ `qo'l`);
- lug'atdagi `(i)`, `[ta]` kabi ixtiyoriy qismlar hisobga olinadi;
- otlarga faqat ot qo'shimchalari qo'shilishi mumkin (`bosh` → `boshi`,
  `boshimdan`, lekin `boshlanib` emas), fe'llar esa erkin tuslanadi
  (`topmoq` → `topolmay`); `yurak → yuragi`, `qishloq → qishlog'i` almashinuvi ham bor;
- `kim?`, `nimaning?` kabi grammatik izohlar ibora tarkibidan chiqariladi;
  bitta so'zli OCR qoldiqlari (`bosh`, `ekan`) tashlab yuboriladi.

## Cheklovlar

- Natija – **nomzodlar**. Ayniqsa ko'chma so'zlar (`davlat`, `yo'l`, `suv`)
  ko'pincha to'g'ri ma'noda keladi, shuning uchun `tekshiruv_belgisi` ustunini
  qo'lda to'ldirish tavsiya etiladi. Faqat iboralar kerak bo'lsa `--lexicon frazeologik`
  bilan ishlating.
- Lug'atdagi ba'zi yozuvlarda OCR xatolari bor (`ajdasrho`), ular izohlarda topilmaydi.
- Platformalarning foydalanish shartlariga rioya qiling, so'rovlar orasida
  pauza (`--delay`) qoldiring va shaxsiy ma'lumotlarni ochiq tarqatmang.

## Tekshirish

```bash
python scripts/comments/test_lexicon.py
```
