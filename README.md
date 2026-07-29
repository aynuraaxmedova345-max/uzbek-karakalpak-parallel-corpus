# Uzbek–Karakalpak Parallel Corpus

A bilingual Uzbek–Karakalpak sentence-aligned corpus with a browser-based search interface, reusable CSV/JSON exports, the original Excel dataset, and project documentation.

## Live demo

After enabling GitHub Pages, the searchable interface is available from the repository's Pages URL.

## Dataset overview

| Domain | Worksheet rows | Complete aligned pairs |
|---|---:|---:|
| Geography textbook | 286 | 282 |
| News texts | 795 | 722 |
| **Total** | **1,081** | **1,004** |

The original workbook contains 1,081 data rows. The normalized CSV and JSON exports include only rows where both Uzbek and Karakalpak texts are present.

## Features

- Uzbek ↔ Karakalpak bilingual search
- Offline browser interface
- Domain-based corpus sections
- CSV, JSON, and XLSX formats
- UTF-8 encoded text
- Dataset validation script
- GitHub Pages ready (`index.html` in the repository root)

## Repository structure

```text
uzbek-karakalpak-parallel-corpus/
├── index.html
├── data/
│   ├── csv/
│   │   ├── geografiya_darslik.csv
│   │   ├── xabarlar.csv
│   │   └── parallel_corpus_all.csv
│   ├── json/
│   │   ├── geografiya_darslik.json
│   │   ├── xabarlar.json
│   │   └── parallel_corpus_all.json
│   └── source/
│       └── parallel_corpus_dataset.xlsx
├── docs/
│   ├── DATA_CARD.md
│   └── project_report.docx
├── scripts/
│   └── validate_dataset.py
├── CITATION.cff
├── DATA_LICENSE.md
├── LICENSE
└── README.md
```

## Data schema

| Field | Description |
|---|---|
| `id` | Row identifier within the original worksheet |
| `uzbek` | Uzbek sentence |
| `karakalpak` | Karakalpak aligned sentence |
| `domain` | Source section: `geografiya_darslik` or `xabarlar` |

## Quick start

Open `index.html` directly in a browser. No server or internet connection is required.

To validate the normalized data:

```bash
python scripts/validate_dataset.py
```

## Suggested citation

Please use the citation information in `CITATION.cff`.

## Limitations

- Sentence alignment and translation quality have not been independently benchmarked.
- Some rows in the original workbook are incomplete; normalized exports exclude them.
- The corpus currently covers two domains and should not be treated as representative of all Uzbek or Karakalpak usage.

## Future work

- Add semantic search and embeddings
- Add linguistic annotations
- Expand domain coverage
- Add quality-control labels
- Publish corpus statistics and benchmarks
