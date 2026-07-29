# Dataset Card

## Dataset name

Uzbek–Karakalpak Parallel Corpus

## Summary

This dataset contains sentence-aligned Uzbek and Karakalpak text from two thematic sections: a geography textbook and news texts. It is intended for computational linguistics, translation analysis, bilingual terminology search, educational use, and small-scale NLP experiments.

## Languages

- Uzbek
- Karakalpak

## Size

The original Excel workbook contains 1,081 data rows:

- `geografiya_darslik`: 286 rows
- `xabarlar`: 795 rows

After excluding rows missing either side of the language pair, the normalized exports contain 1,004 complete sentence pairs:

- `geografiya_darslik`: 282 pairs
- `xabarlar`: 722 pairs

## Formats

- XLSX: original source workbook
- CSV: per-domain and combined normalized exports
- JSON: per-domain and combined normalized exports
- HTML: searchable offline interface

## Intended uses

- Parallel-text lookup
- Translation comparison
- Bilingual terminology exploration
- Teaching and coursework
- Prototyping alignment, retrieval, and machine-translation experiments

## Limitations and risks

The corpus is small and limited to two domains. It may contain translation inconsistencies, spelling variation, punctuation differences, incomplete rows, and domain-specific bias. It should not be used as the sole dataset for production machine-translation systems or high-stakes language decisions.

## Data processing

The normalized exports preserve the source text and remove rows where either the Uzbek or Karakalpak field is empty. No automatic spelling correction or translation rewriting was applied.
