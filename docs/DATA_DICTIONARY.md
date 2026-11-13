# Data dictionary — Covertype

Reference for every column of the Forest Cover Type (Covertype) dataset, built
for milestone M1, issue #5. Column names, types, units and descriptions come
from the official UCI documentation (`data/raw/covtype.info`) and
`src/data_audit.py` (`COLUMNS`); observed ranges are computed from
`data/raw/covtype.data`.

## Overview

| Property | Value |
|---|---|
| Observations (rows) | 581,012 (one per 30 x 30 m cell) |
| Columns | 55 = 54 features + 1 target (`Cover_Type`) |
| Stored dtype | all `int64` |
| Missing values | none |
| Duplicate rows | none |
| Feature groups | 10 numeric (quantitative) + 4 wilderness-area + 40 soil-type binary indicators |

The raw file has no header; names are assigned from the official documentation
in column order. Audit facts reproduce with `python src/data_audit.py`; see
[EDA.md](EDA.md) for distributions and [ontology.md](../specs/ontology.md) for
the shared vocabulary.

## 1. Numeric features (quantitative)

Columns `COLUMNS[0:10]`. Mean and standard deviation are the official
whole-dataset values from `covtype.info`; min/max are observed in the raw file.

| # | Column | Type | Unit | Observed range (min–max) | Mean ± SD | Description |
|---|---|---|---|---|---|---|
| 1 | `Elevation` | int (continuous) | meters | 1859 – 3858 | 2959.4 ± 280.0 | Elevation above sea level. Most discriminative feature (eta squared 0.616). |
| 2 | `Aspect` | int (continuous) | degrees azimuth (0–360) | 0 – 360 | 155.7 ± 111.9 | Compass direction the slope faces. Circular variable. |
| 3 | `Slope` | int (continuous) | degrees | 0 – 66 | 14.1 ± 7.5 | Steepness of the terrain. |
| 4 | `Horizontal_Distance_To_Hydrology` | int (continuous) | meters | 0 – 1397 | 269.4 ± 212.6 | Horizontal distance to nearest surface water. Right-skewed. |
| 5 | `Vertical_Distance_To_Hydrology` | int (continuous) | meters | −173 – 601 | 46.4 ± 58.3 | Vertical distance to nearest surface water. Can be negative (below water level); heaviest tails. |
| 6 | `Horizontal_Distance_To_Roadways` | int (continuous) | meters | 0 – 7117 | 2350.2 ± 1559.3 | Horizontal distance to nearest roadway. |
| 7 | `Hillshade_9am` | int (continuous) | index 0–255 | 0 – 254 | 212.2 ± 26.8 | Hillshade at 9am, summer solstice. Left-skewed. |
| 8 | `Hillshade_Noon` | int (continuous) | index 0–255 | 0 – 254 | 223.3 ± 19.8 | Hillshade at noon, summer solstice. Left-skewed. |
| 9 | `Hillshade_3pm` | int (continuous) | index 0–255 | 0 – 254 | 142.5 ± 38.3 | Hillshade at 3pm, summer solstice. |
| 10 | `Horizontal_Distance_To_Fire_Points` | int (continuous) | meters | 0 – 7173 | 1980.3 ± 1324.2 | Horizontal distance to nearest wildfire ignition point. Right-skewed. |

## 2. Wilderness areas (binary indicators)

Columns `COLUMNS[10:14]`. One-hot encoding of a single qualitative variable:
exactly one is `1` per row, the rest `0`. Values: `0` = absence, `1` = presence.

| Column | Area name | Note (from `covtype.info`) |
|---|---|---|
| `Wilderness_Area1` | Rawah | Lower mean elevation; mostly lodgepole pine. |
| `Wilderness_Area2` | Neota | Highest mean elevation; mostly spruce/fir. |
| `Wilderness_Area3` | Comanche Peak | Lower mean elevation; mostly lodgepole pine. |
| `Wilderness_Area4` | Cache la Poudre | Lowest mean elevation; ponderosa pine, Douglas-fir, cottonwood/willow. |

## 3. Soil types (binary indicators)

Columns `COLUMNS[14:54]`. One-hot encoding of the soil type: exactly one is `1`
per row. Values: `0` = absence, `1` = presence. Each type maps to a USFS
Ecological Landtype Unit (ELU); the first ELU digit is the climatic zone and the
second the geologic zone.

| Column | ELU code | Description |
|---|---|---|
| `Soil_Type1` | 2702 | Cathedral family – Rock outcrop complex, extremely stony. |
| `Soil_Type2` | 2703 | Vanet – Ratake families complex, very stony. |
| `Soil_Type3` | 2704 | Haploborolis – Rock outcrop complex, rubbly. |
| `Soil_Type4` | 2705 | Ratake family – Rock outcrop complex, rubbly. |
| `Soil_Type5` | 2706 | Vanet family – Rock outcrop complex complex, rubbly. |
| `Soil_Type6` | 2717 | Vanet – Wetmore families – Rock outcrop complex, stony. |
| `Soil_Type7` | 3501 | Gothic family. |
| `Soil_Type8` | 3502 | Supervisor – Limber families complex. |
| `Soil_Type9` | 4201 | Troutville family, very stony. |
| `Soil_Type10` | 4703 | Bullwark – Catamount families – Rock outcrop complex, rubbly. |
| `Soil_Type11` | 4704 | Bullwark – Catamount families – Rock land complex, rubbly. |
| `Soil_Type12` | 4744 | Legault family – Rock land complex, stony. |
| `Soil_Type13` | 4758 | Catamount family – Rock land – Bullwark family complex, rubbly. |
| `Soil_Type14` | 5101 | Pachic Argiborolis – Aquolis complex. |
| `Soil_Type15` | 5151 | Unspecified in the USFS Soil and ELU Survey. |
| `Soil_Type16` | 6101 | Cryaquolis – Cryoborolis complex. |
| `Soil_Type17` | 6102 | Gateview family – Cryaquolis complex. |
| `Soil_Type18` | 6731 | Rogert family, very stony. |
| `Soil_Type19` | 7101 | Typic Cryaquolis – Borohemists complex. |
| `Soil_Type20` | 7102 | Typic Cryaquepts – Typic Cryaquolls complex. |
| `Soil_Type21` | 7103 | Typic Cryaquolls – Leighcan family, till substratum complex. |
| `Soil_Type22` | 7201 | Leighcan family, till substratum, extremely bouldery. |
| `Soil_Type23` | 7202 | Leighcan family, till substratum – Typic Cryaquolls complex. |
| `Soil_Type24` | 7700 | Leighcan family, extremely stony. |
| `Soil_Type25` | 7701 | Leighcan family, warm, extremely stony. |
| `Soil_Type26` | 7702 | Granile – Catamount families complex, very stony. |
| `Soil_Type27` | 7709 | Leighcan family, warm – Rock outcrop complex, extremely stony. |
| `Soil_Type28` | 7710 | Leighcan family – Rock outcrop complex, extremely stony. |
| `Soil_Type29` | 7745 | Como – Legault families complex, extremely stony. |
| `Soil_Type30` | 7746 | Como family – Rock land – Legault family complex, extremely stony. |
| `Soil_Type31` | 7755 | Leighcan – Catamount families complex, extremely stony. |
| `Soil_Type32` | 7756 | Catamount family – Rock outcrop – Leighcan family complex, extremely stony. |
| `Soil_Type33` | 7757 | Leighcan – Catamount families – Rock outcrop complex, extremely stony. |
| `Soil_Type34` | 7790 | Cryorthents – Rock land complex, extremely stony. |
| `Soil_Type35` | 8703 | Cryumbrepts – Rock outcrop – Cryaquepts complex. |
| `Soil_Type36` | 8707 | Bross family – Rock land – Cryumbrepts complex, extremely stony. |
| `Soil_Type37` | 8708 | Rock outcrop – Cryumbrepts – Cryorthents complex, extremely stony. |
| `Soil_Type38` | 8771 | Leighcan – Moran families – Cryaquolls complex, extremely stony. |
| `Soil_Type39` | 8772 | Moran family – Cryorthents – Leighcan family complex, extremely stony. |
| `Soil_Type40` | 8776 | Moran family – Cryorthents – Rock land complex, extremely stony. |

ELU first digit (climatic zone): 1 lower montane dry, 2 lower montane, 3 montane
dry, 4 montane, 5 montane dry and montane, 6 montane and subalpine, 7 subalpine,
8 alpine. Second digit (geologic zone): 1 alluvium, 2 glacial, 3 shale,
4 sandstone, 5 mixed sedimentary, 6 unspecified, 7 igneous and metamorphic,
8 volcanic. Soil presence is very uneven across the 40 types (from `Soil_Type15`
with 3 cells to `Soil_Type29` with 115,247 cells).

## 4. Target

| Column | Type | Values | Description |
|---|---|---|---|
| `Cover_Type` | integer (categorical) | 1 – 7 | Dominant tree cover type of the cell. The variable to predict. |

| `Cover_Type` | Name | Count | Share |
|---|---|---|---|
| 1 | Spruce/Fir | 211,840 | 36.46% |
| 2 | Lodgepole Pine | 283,301 | 48.76% |
| 3 | Ponderosa Pine | 35,754 | 6.15% |
| 4 | Cottonwood/Willow | 2,747 | 0.47% |
| 5 | Aspen | 9,493 | 1.63% |
| 6 | Douglas-fir | 17,367 | 2.99% |
| 7 | Krummholz | 20,510 | 3.53% |

The target is strongly imbalanced (min/max ratio about 1:103); classes 1 and 2
hold about 85% of the rows. See [EDA.md](EDA.md) for the implications.

## Reproducing the ranges

```bash
python -c "import sys; sys.path.insert(0,'src'); from data_audit import load_raw, COLUMNS; print(load_raw()[COLUMNS[:10]].agg(['min','max']).T)"
```
