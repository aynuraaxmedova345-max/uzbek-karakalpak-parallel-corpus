# 2.1. Tadqiqot materiali va terminlarni ajratish metodikasi

## 2.1.1. Korpus

Tadqiqot materiali sifatida O'zbekiston Respublikasi Qonunchilik ma'lumotlari milliy bazasidan (lex.uz) olingan 30 ta hujjatning o'zbek tilidagi lotin yozuvidagi matnlari xizmat qildi: 25 ta xalqaro shartnoma va 5 ta milliy hujjat (qonun, farmon, qaror). Hujjatlar saytdagi HTML sahifalardan avtomatik ajratib olindi; sayt interfeysi elementlari, "LexUZ sharhi", tahrir manbasi izohlari, klassifikator indekslari va "(imzolar)" belgisi matndan chiqarilib, har biri `data/meta/removed_lines.csv` faylida qayd etildi. Matn mazmuniga hech qanday tuzatish kiritilmadi; saytdagi imlo xatolari (118 ta holat) alohida ro'yxatga (`typos_noticed.csv`) yozildi.

Korpus hajmi 194 330 so'zni tashkil etadi (tokenizator bo'yicha 191 092 token). Sohalar bo'yicha taqsimot: xalqaro gumanitar huquq — 37,5 %, inson huquqlari — 24,7 %, huquqiy yordam — 20,7 %, jinoyatchilikka qarshi kurash — 13,7 %, shartnomalar huquqi — 3,0 %, diplomatik huquq — 0,4 %. Gumanitar huquq ulushi dastlabki 64 % dan korpusni kengaytirish orqali 40 % dan pastga tushirildi. Matn maqomi sahifadagi ma'lumot asosida aniqlandi: "Norasmiy tarjima" belgisi bor matnlar — 71,1 % (20 hujjat); o'zbek tilidagi matni autentik deb ko'rsatilgan ikki tomonlama shartnomalar va milliy hujjatlar — 25,5 % (8 hujjat); maqomini sahifadan aniqlab bo'lmaganlar — 3,4 % (2 hujjat). Bir qator muhim konvensiyalar (shartnomalar huquqi, diplomatik va konsullik munosabatlari to'g'risidagi Vena konvensiyalari, ShHT Xartiyasi va b.) lex.uz da faqat rus tilida berilgani sababli korpusga kiritilmadi (12 ta hujjat, `ruscha_faqat.csv`).

## 2.1.2. Reference korpus

Termin nomzodlarining umumiy tildagi qo'llanishini baholash uchun lotin yozuvidagi umumiy matnlardan iborat reference korpus tuzildi (jami 8 967 533 token, 272 723 so'zshakl): (1) Amerika Ovozi o'zbek xizmatining 2002–2025-yillardagi 27 426 ta maqolasi (Multilingual Open Text to'plami, 8 453 528 token) va (2) "Uzbek Corpus Sample" to'plamining takrorlardan tozalangan 95 019 jumlasi (514 005 token). Ikkala manba CC BY 4.0 litsenziyasi ostida. Reference korpus asosan publitsistik uslubni aks ettiradi; bu uning cheklovi sifatida qayd etiladi.

## 2.1.3. Nomzodlarni ajratish

Har ikki korpus bir xil qoidalar bilan qayta ishlandi: apostrof variantlari yagona shaklga keltirildi (oʻ, gʻ va tutuq belgisi), matn tinish belgilari va raqamlar bo'yicha bo'laklarga ajratildi. Lemmatizatsiya UzMorphAnalyser (0.0.22) yordamida bajarildi. Analizator natijalari tekshirilganda tizimli xatolar aniqlandi (ot va sifatlarni fe'l deb tahlil qilish, asos oxirini qo'shimcha deb kesish, k/q ~ g/gʻ almashinuvini tiklamaslik, -chi va -noma qo'shimchalarini kesish); ularning 50 ta tasdiqlangan misoli `stemmer_xatolari.csv` da keltirilgan. Xatolar ikki bosqichda tuzatildi: (a) lug'at tekshiruvi — analizator bergan asos korpuslarda mustaqil so'z sifatida uchramasa yoki fe'l tahlili soxta bo'lsa, ot qo'shimchalari kesilib, lug'atda mavjud asos tanlandi; (b) 61 ta qo'lda tuzilgan tuzatish qoidasi (`lemma_tuzatishlar.csv`).

Nomzod sifatida 1–6 so'zli n-grammlar olindi. Chegara qoidalari: birinchi va oxirgi so'z yordamchi so'zlar ro'yxatida bo'lmasligi, birinchi so'z ot yoki sifat, oxirgi so'z ot yoki harakat nomi bo'lishi shart. Variantlar lemmalar ketma-ketligi bo'yicha guruhlandi. Korpusda kamida 3 marta uchragan 13 507 nomzod ajratildi (11 230 ko'p so'zli, 2 277 bir so'zli).

## 2.1.4. Ballar

Ko'p so'zli nomzodlar uchun C-value ko'rsatkichi hisoblandi: C(a) = log₂|a| · (f(a) − Σf(b)/|Tₐ|), bu yerda Tₐ — a ni o'z ichiga olgan uzunroq nomzodlar to'plami. Bir so'zli nomzodlar uchun reference korpusga nisbatan Dunning log-likelihood (G²) ko'rsatkichi hisoblandi; faqat korpusda nisbatan ko'p uchragan va G² ≥ 10,83 (p < 0,001) bo'lganlar ijobiy baholandi. Ikki turdagi ballarni yagona ro'yxatda tartiblash uchun har bir ball o'z turidagi eng yuqori ballga bo'linib, norm_ball hosil qilindi.

## 2.1.5. Tozalash qoidalari

Qoidalar quyidagi tartibda qo'llandi; nomzodga birinchi mos kelgan qoida yozildi:

| Qoida | Mezon | Chiqarilgan |
|---|---|---:|
| bo'lak | ko'p so'zli nomzod chastotasining 80 % dan ko'prog'i uzunroq nomzod ichida keladi | 4 841 |
| nomenklatura | joy yoki atoqli nom komponenti; "Birlashgan Millatlar", "Qizil Xoch" kabi nom juftlari; vazirlik, assambleya, mahkama, palata kabi so'zlar bilan tugaydigan birikma; bosh harf bilan yoziladigan tashkilot nomlari; qisqartma nomlar | 297 |
| umumiy leksika | bir so'zli: G² < 10,83 yoki reference korpusda ≥ 50 ipm va huquqiy leksika lug'atida yo'q | 1 539 |
| zaxira | f < 5 | 3 874 |

"Bo'lak" qoidasi faqat ko'p so'zli nomzodlarga qo'llandi. Bir so'zli nomzodlarga qo'llanganda u 302 ta asosiy terminni ("huquq", "davlat", "ratifikatsiya" va b.) chiqarib yuborar edi, chunki yakka so'z deyarli har doim uzunroq birikma tarkibida keladi.

## 2.1.6. Tasnif mezonlari

Qolgan 2 956 nomzod uchun "auto_termin" (ha / shubhali / yo'q) qiymati qoidalar asosida avtomatik aniqlandi; har bir qarorning qoida kodi va izohi `auto_sabab` ustunida berilgan. Qoidalar ushbu loyiha doirasida tuzilgan lug'atlarga tayanadi: tor huquqiy leksika (167 so'z), umumiy bosh so'zlar (66), soha aniqlovchilari (22). Asosiy mezonlar:

- **Bir so'zli:** huquqiy leksika lug'atida bo'lsa — ha (T1). Lug'atdagi sifatlar, masalan "huquqiy" yoki "jinoiy" — shubhali (T5), chunki ular mustaqil termin emas, termin elementidir. Korpusga xos, lekin lug'atda yo'q so'zlar — shubhali (T3). Fe'l yoki harakat nomi (T2), shuningdek lug'atda yo'q va korpusga xos bo'lmagan so'zlar (T4) — yo'q.
- **Ko'p so'zli, rad etish mezonlari (yo'q):**
  - olmosh, belgilovchi yoki yordamchi so'z bor (S1);
  - teng bog'lovchi bor (S2);
  - sana bor (S3);
  - ichki komponent kelishikda (S4);
  - ibora tugallanmagan: oxirgi so'z kelishikda (S7) yoki bosh so'z sifat (S8);
  - ikki birikma tutashuvi (S6);
  - huquqiy komponentsiz fe'liy ibora (S5);
  - birinchi komponent egalikda (P4).
- **Ko'p so'zli, qabul qilish mezonlari (ha):**
  - bosh so'z huquqiy lug'atda (H1);
  - umumiy bosh so'z ("davlat", "kuch", "yordam" kabi) va huquqiy yoki soha aniqlovchisi (H2);
  - "kelishikli ot + harakat nomi" qolipidagi fe'liy termin, huquqiy komponent bilan (V1), masalan "jinoyatchini berish", "qamoqqa olish".
- **Shubhali:** sifatdoshli birikmalar (H1+P, H2+P), bosh so'zi ro'yxatlarda yo'q birikmalar (H4), yordamchi fe'l bilan boshlanadigan bo'laklar (P2, P3).

Natija: ha — 410, shubhali — 222, yo'q — 2 324. Rad etishning eng ko'p uchragan sabablari: ichki komponent kelishikda (790), huquqiy komponent yo'q (326), yordamchi so'z bor (322).

## 2.1.7. Yakuniy ro'yxat va tavsif

"Ha" deb topilgan barcha 410 nomzod yakuniy ro'yxatga kiritildi. Rejalashtirilgan 1 000 taga yetmadi; shubhali nomzodlar qo'shilmadi. Har bir termin uchun quyidagilar avtomatik aniqlandi:

- mavzuiy guruh: komponentlar bo'yicha kalit so'zlar ro'yxati;
- tuzilishi: sodda, yasama, qo'shma, birikma yoki qisqartma;
- tuzilish modeli: komponentlarning so'z turkumi bo'yicha;
- yasovchi qo'shimchalar;
- kelib chiqishi: o'zak bo'yicha, loyiha uchun tuzilgan 435 o'zakli lug'at va o'zlashma qo'shimchalar asosida. Komponentlarning 96,5 % i uchun aniqlandi.

Dublet klasterlari ikki yo'l bilan topildi: imlo variantlari ("ishtirokchi davlat" / "ishtirokchi-davlat") va komponentlari sinonim juftlardan iborat terminlar ("protokol" / "bayonnoma", "prinsip" / "tamoyil"). Natijada 10 ta klaster aniqlandi, ularga 21 ta termin kiradi. Yasalishi jihatidan bog'liq, lekin mazmunan boshqa tushunchalar (masalan, "qonun" / "qonunchilik") dublet hisoblanmadi.

Kelib chiqish va mavzuiy guruh lug'atlari, shuningdek huquqiy leksika ro'yxatlari qo'lda (mutaxassis bahosisiz) tuzilgan va mutaxassis tomonidan tekshirilishi lozim. "Gibrid" toifasiga ichida ko'makchi ("bo'yicha") bo'lgan birikmalar ham kiradi.

## 2.1.8. Sifatni baholash

Avtomatik tasnifning aniqligini baholash uchun yakuniy ro'yxatdan 100 ta termin tasodifiy tanlandi (random seed = 42). Tanlanma mavzuiy guruhlar ulushiga proporsional bo'lib, eng katta qoldiq usulida taqsimlandi: huquqiy yordam va jinoiy protsess — 31, huquq manbalari — 17, gumanitar huquq — 17, inson huquqlari — 10, subyektlar — 10, nizolar va javobgarlik — 5, xalqaro tashkilotlar — 4, qolgan guruhlar — 2 tadan. Har bir termin kontekst bilan birga qo'lda baholanadi ("to'g'ri" / "noto'g'ri"). Aniqlik (precision) Wilson usuli bo'yicha 95 % ishonch oralig'i bilan hisoblanadi (`scripts/precision.py`). Guruhlar ulushi bilan tortilgan baho ham beriladi. Tanlanma faqat aniqlikni baholaydi; "yo'q" va "shubhali" deb rad etilgan nomzodlar orasidagi haqiqiy terminlar ulushi (to'liqlik, recall) bu baholashga kirmaydi.
