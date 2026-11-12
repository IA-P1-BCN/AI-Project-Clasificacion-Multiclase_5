# Data

The datasets are **not** stored in Git (`data/raw/` and `data/processed/` are
git-ignored). This file records where the raw dataset comes from so that anyone
can download exactly the same file.

## Raw dataset: Covertype

| | |
|---|---|
| Name | Covertype (Forest Cover Type) |
| Official source | UCI Machine Learning Repository, dataset 31: https://archive.ics.uci.edu/dataset/31/covertype |
| Direct download | https://archive.ics.uci.edu/static/public/31/covertype.zip |
| DOI | [10.24432/C50K5N](https://doi.org/10.24432/C50K5N) |
| Authors | Jock A. Blackard, Denis J. Dean, Charles W. Anderson (Colorado State University) |
| Version | Original UCI release, donated August 1998. Documentation (`covtype.info`) last updated 12/07/1999. UCI does not publish numbered versions; use the checksum below to identify the file. |
| License | Creative Commons Attribution 4.0 International (CC BY 4.0) |
| Downloaded on | 2026-11-12 |

### Files

Expected content of `data/raw/` after the download:

| File | Size | SHA-256 | Description |
|---|---|---|---|
| `covtype.data` | 75,169,317 bytes (71.7 MiB) | `0a9371cef7c964b5475d6053cc3e0894a5aa6f65ad1ed3ecb01c45aa96217945` | The dataset: 581,012 rows x 55 columns, comma separated, no header |
| `covtype.info` | 14,610 bytes | `15f192a8cbebbf26af940301727d1795b8ca92a80dc1cc6b3bdad2af9546bc35` | Official documentation (column names, units, class names) |
| `old_covtype.info` | 4,847 bytes | not recorded | Earlier version of the documentation, included in the archive; not used |

Only `covtype.data` is required by the code.

### Structure

- 54 features, all integers: 10 numeric (elevation, aspect, slope, distances,
  hillshade), 4 binary `Wilderness_Area` indicators and 40 binary `Soil_Type`
  indicators.
- Target: `Cover_Type`, 7 classes (1-7).
- No missing values (stated in `covtype.info` and confirmed by `src/data_audit.py`).
- The file has no header; column names are assigned in `src/data_audit.py`
  (`COLUMNS`) following `covtype.info`.

## How to download

1. Download `covertype.zip` from the direct link above (or the *Download*
   button on the dataset page).
2. Extract it. It contains `covtype.data.gz`, `covtype.info` and
   `old_covtype.info`.
3. Decompress `covtype.data.gz` and place `covtype.data` in `data/raw/`.

```bash
curl -L -o covertype.zip https://archive.ics.uci.edu/static/public/31/covertype.zip
unzip covertype.zip -d data/raw/
gunzip data/raw/covtype.data.gz
```

## How to verify

```bash
sha256sum data/raw/covtype.data      # Windows: certutil -hashfile data\raw\covtype.data SHA256
python src/data_audit.py             # expects 581,012 rows, 55 columns, 0 nulls, 0 duplicates
```

The checksum must match the table above.

## Rules

- `data/raw/` is immutable: never edit the downloaded files.
- Anything derived from the raw data goes to `data/processed/`.

## Citation

Blackard, J. (1998). *Covertype* [Dataset]. UCI Machine Learning Repository.
https://doi.org/10.24432/C50K5N
