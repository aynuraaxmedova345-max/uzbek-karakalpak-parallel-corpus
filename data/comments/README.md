# Yig'ilgan izohlar

Izohlar `scripts/comments/fetch_public_comments.py` bilan GitHub'dagi ochiq
datasetlardan olingan. YouTube va Telegram'dan yig'ish uchun
`scripts/comments/collect_comments.py youtube|telegram` ni internetga ulangan
kompyuterda ishga tushiring (qarang: `docs/IZOH_YIGISH.md`).

| Fayl | Mazmuni |
|---|---|
| `ochiq_izohlar.csv` | barcha manba izohlari (5 370 ta, takrorlarsiz): `id,text,source,sentiment,dataset` |
| `izohlar_mosliklar.csv` | leksikondagi birlik topilgan izohlar, har moslik bitta qator |
| `frazeologik_izohlar.csv` | faqat frazeologik iboralar (432 moslik, 399 izoh) |
| `kochma_izohlar.csv` | faqat ko'chma ma'noli so'zlar (1 928 moslik, 1 479 izoh) |

`tekshiruv_belgisi` ustuni bo'sh: so'z yoki ibora shu izohda haqiqatan ham
ko'chma/frazeologik ma'noda kelganini annotator `ha` / `yo'q` deb belgilaydi.
Ko'chma so'zlar ro'yxatidagi ko'p so'zlar (`katta`, `til`, `foydali`) izohlarda
asosan to'g'ri ma'noda keladi, shuning uchun bu fayl qo'lda tekshirilishi kerak.

## Manbalar va litsenziyalar

| `source` | Izohlar | Manba |
|---|---:|---|
| `google_play` | 3 719 | Google Play'dagi top-100 ilovaga o'zbekcha sharhlar (qo'lda belgilangan qism; mashina tarjimasi olinmagan). [SanatbekMatlatipov/uzbek-sentiment-analysis](https://github.com/SanatbekMatlatipov/uzbek-sentiment-analysis). Iqtibos: Kuriyozov, Matlatipov, Alonso, Gómez-Rodríguez. *Construction and Evaluation of Sentiment Datasets for Low-Resource Languages: The Case of Uzbek*. LTC 2019, LNCS 13212. |
| `restoran` | 1 651 | Restoran sharhlari, UzABSA. [SanatbekMatlatipov/UzABSA](https://github.com/SanatbekMatlatipov/UzABSA) (GPL-3.0). Iqtibos: Matlatipov, Rajabov, Kuriyozov, Aripov. *UzABSA: Aspect-Based Sentiment Analysis for the Uzbek Language*. SIGUL 2024. |

Izohlardan foydalanganda yuqoridagi manbalarga havola qiling.
