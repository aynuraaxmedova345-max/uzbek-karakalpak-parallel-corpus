# 01. Kirish fayllari inventari

Sana: 2026-10-23. Ish muhiti: bulutdagi Claude Code sessiyasi (foydalanuvchining Windows kompyuteri emas).
Batafsil ma'lumot: `output/manifest.json`.

## 1. Loyiha papkalari

| Papka | Holat |
|---|---|
| `input/` | **bo'sh** — ikkala Excel va audit notebooki bu muhitga yuklanmagan |
| `dictionaries/` | **bo'sh** — izohli lug'at PDF'lari yo'q |
| `extracted/` | bo'sh (PDF yo'qligi sababli pilot bajarilmadi) |
| `output/` | shu hisobotlar |

Qidirilgan joylar: sessiyadagi butun disk (`*.pdf`, `*.ipynb`, `*.xlsx`), shu repodagi barcha branchlar,
foydalanuvchining GitHub repolari (`uzwordnet-explorer`, `sinset-tekshiruvchi`).

## 2. Topilgan fayllar (loyiha papkasidan tashqarida, faqat o'qildi)

| Fayl | Joyi | Hajm | SHA-256 (boshi) | Nima |
|---|---|---:|---|---|
| `uzwordnet_rc1_1.xlsx` | `uzwordnet-explorer@main:application/` (private repo) | 6 950 238 | `f6f19d56c238852f` | UzWordNet Explorer Dataset RC1.1 — **asl datasetlardan hosil qilingan relizi**, asl dataset emas |
| `izohli_lugat_clean.xlsx` | shu repo, `claude/quirky-einstein-103ocw` branchi, `data/source/` | 8 793 276 | `8f4e0e3cead4be7f` | Izohli lug'atning OCR qilingan va lotinga o'girilgan jadvali. **PDF sahifa raqami ustuni yo'q** |
| `Namuna_Talaba_201.xlsx` | `sinset-tekshiruvchi@main:samples/` | 18 632 | `eb1bab2934aa3029` | Talaba topshirig'i namunasi (70 qator) |

Nusxa olinmadi: RC1.1 shaxsiy repoda, bu repo esa ochiq. Faqat metama'lumot (nom, hajm, hash, ustunlar, qator soni) yozildi.

### 2.1 `uzwordnet_rc1_1.xlsx` (read-only)

| Varaq | Ma'lumot qatorlari | Ustunlar |
|---|---:|---|
| Release Summary | 16 | (jadval emas: ko'rsatkich/qiymat) |
| Synsets | 15 818 | synset_id, pos, definition, definition_status, domain, release_tier, validation_status, confidence, source_record_ids, candidate_synset_key |
| Senses | 26 884 | sense_id, synset_id, lemma, normalized_lemma, script, pos, sense_number, release_tier, validation_status, confidence, source_dataset, source_file, source_sheet, source_row, candidate_sense_key, style |
| Relations | 265 | source_synset_id, target_synset_id, relation_type, direction, confidence, release_tier, validation_status, source_dataset, source_sheet, source_row, source_term, target_term, mapping_key, relation_id |
| Examples | 15 674 | example_id, synset_id, example_text, release_tier, validation_status, source_record_ids, classification, classification_reason, display_as_example |
| Ontology | 149 | ontology_annotation_id, sense_id, synset_id, ontology_concept, ontology_category, domain, original_category, release_tier, validation_status, source_file, source_sheet, source_row |
| Derivational | 9 | derivational_relation_id, root_sense_id, form_sense_id, derivational_root, derivational_form, derivational_affix, release_tier, validation_status, source_file, source_sheet, source_row |
| Search Index | 26 884 | normalized_lemma, display_lemma, sense_id, synset_id, pos, definition_preview, synonyms, relation_count, release_tier, validation_status |

Qayta tekshiruv: `uzwordnet-explorer/docs/DATASET_INTEGRATION.md` dagi sonlar (15 818 / 26 884 / 265 / 15 674 / 149 / 9 / 26 884)
Excel varaqlari bilan **mos keldi** (qatorlar qayta sanaldi). Bu faqat qator soni mosligi; mazmun sifati tekshirilmadi.

RC1.1 `Senses.source_file` bo'yicha asl manbalar (sense soni):

| Asl fayl | Varaq | Sense |
|---|---|---:|
| Sinset_UzWordNet_11178(23.05)(1).xlsx | UzWordNet | 13 304 |
| II. Giper-giponim lug'ati(1).xlsx | Giper-giponim | 5 224 |
| IV. Polisemiya lug'ati(1).xlsx | Sheet1 | 3 642 |
| V. Antonim lug'ati(1).xlsx | Лист1 | 1 935 |
| III. Xolonim-meronim(1).xlsx | Xolonim-meronim lug'ati | 1 716 |
| UzWordNet_Giperonim_Giponim_Eliboyeva_Shaxnoza_!!!(1).xlsx | Sheet1 | 708 |
| I. Sinset lugati(1).xlsx | Leksik sinonimlar | 181 |
| Polisemiya lug'ati.xlsx | Sheet1 | 168 |
| Giper-giponim lug'ati.xlsx | Giper-giponim | 6 |

Bu fayllarning hech biri mavjud emas. Topshiriqdagi "ikki UzWordNet Excel dataseti" qaysilar ekani aniqlanmadi.

### 2.2 `izohli_lugat_clean.xlsx` (read-only)

- `Izohli lugat`: 46 608 qator, 31 472 noyob so'z; `needs_review=True` — 7 065 qator; `homonym` to'ldirilgan — 92 qator.
- Ustunlar: So'z, Ma'no raqami, Gloss (izoh), Kontekst misoli, POS, POS_manba, manba_muallif, etimologiya, uslub_belgisi, id, entry_index, homonym, merged_entry, needs_review, needs_review_sabab.
- `Junk (chiqarilgan)`: 2 qator (titul sahifasi matni).
- Cheklov: jild va PDF sahifasi ko'rsatilmagan, xom matn yo'q. Shuning uchun **PDF o'rnini bosa olmaydi**; faqat keyinchalik qiyoslash uchun yordamchi manba.

## 3. Yetishmayotgan fayllar

1. UzWordNet Excel dataseti #1 (asl).
2. UzWordNet Excel dataseti #2 (asl).
3. Audit notebooki (`.ipynb`) — hech qayerda topilmadi.
4. Izohli lug'at PDF'lari (1-jild va boshqalar).

## 4. Audit notebooki (A.4–A.5)

Notebook yo'q, shuning uchun uning ustun indekslari haqiqiy sarlavhalarga mosligi va sinonimlar tekshiruvga
kirgani **tekshirilmadi**. Yaqin vosita — `sinset-tekshiruvchi/python/sinset_tekshiruvchi.py` (talaba fayllarini
tekshiradi) — ustunlarni indeks bo'yicha emas, sarlavha nomi bo'yicha topadi va `sinonim` ustunini talab qilinganlar
qatoriga kiritadi. U notebook emas va ishga tushirilmadi.

## 5. Oldingi hisobot sonlari

RC1.1 hujjatlaridagi qator sonlari qayta sanalib tasdiqlandi (2.1). Boshqa oldingi hisobot sonlari
(masalan, "POS issues found 312") tekshirilmadi va tasdiqlangan fakt deb olinmadi.
