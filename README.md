# Chess Endgame Compression via Data Mining

> **Diploma Thesis** — University of Patras, Department of Electrical & Computer Engineering  
> **Author:** Andreas Peppas  
> **Supervisor:** Kyriacos Sgarbas  

Lossless semantic compression of Nalimov chess endgame tablebases using unpruned J48 decision trees and binary exception patching. Achieves **100% lossless reconstruction** with up to **98% size reduction** compared to the original Nalimov `.emd` files.

---

## Overview

Chess endgame tablebases (Nalimov format) store the theoretically correct outcome for every legal position with up to 6 pieces. While perfectly accurate, they require significant storage. This project replaces raw tablebase data with a two-component hybrid structure:

1. **Decision Tree (J48)** — an unpruned J48 classifier trained on engineered chess features that captures the general rules of the endgame
2. **`exceptions.bin`** — a compact binary file encoding only the positions where the tree fails, using 1 byte per piece per position

Together they guarantee **100% lossless reconstruction** of the original Nalimov tablebase.

---

## Results

| Endgame   | Positions  | CV Accuracy | Train Errors | exceptions.bin | Nalimov .emd | Reduction |
|-----------|------------|-------------|--------------|----------------|--------------|-----------|
| KPK WTM   | 168,024    | 99.67%      | 548          | 1,648 B        | ~17 KB       | 90%       |
| KPK BTM   | 168,024    | 99.96%      | 66           | ~200 B         | ~17 KB       | 99%       |
| KQK BTM   | ~420,000   | 99.95%      | 80           | 244 B          | ~6 KB        | 96%       |
| KRK BTM   | ~380,000   | 100%        | 0            | 0 B            | ~7 KB        | 100%      |
| KBBK BTM  | ~873,000   | 99.996%     | 116          | 468 B          | ~249 KB      | 99.8%     |
| KBBK WTM  | 794,846    | 99.997%     | 24           | ~100 B         | ~249 KB      | 99.9%     |
| KRKN WTM  | 846,565    | 98.69%      | 784          | 3,140 B        | 179,806 B    | 98.3%     |
| KRKN BTM  | 1,955,843  | 99.80%      | 3,851        | 15,408 B       | 179,806 B    | 91.4%     |

CV = 10-fold cross-validation (KRKN BTM: 3-fold). All results are **100% lossless**.

---

## Pipeline

The fully automated pipeline consists of 6 stages:

```
Nalimov .emd
    │
    ▼
1. probe_*.cpp          C++ — Query Nalimov API, apply 8-fold symmetry, filter illegal positions
    │  → *_raw.csv
    ▼
2. add_attributes.py    Python — Compute 19–31 geometric & tactical chess features
    │  → *_v2.csv
    ▼
3. csv_to_arff.py       Python — Convert to Weka ARFF format, mask raw coordinates
    │  → *_v2.arff
    ▼
4. train_weka.py        Python/Java — Train unpruned J48 (-U -M 1), run 10-fold CV
    │  → *_train_predictions.csv
    ▼
5. analyze.py           Python — Compare predictions vs ground truth, compute Info Gain
    │  → *_failures.csv
    ▼
6. compress_exceptions.py  Python — Serialize failures to compact binary
    └  → *_exceptions.bin
```

---

## Repository Structure

```
chess-endgame-compression/
├── egtb.cpp / bitlib.h / tbdecode.h / lock.h   # Nalimov API (Nalimov, 2000)
├── kpk_wtm/
│   ├── probe_kpk.cpp
│   ├── add_attributes.py
│   ├── csv_to_arff.py
│   ├── train_weka.py
│   ├── analyze.py
│   └── compress_exceptions.py
├── kpk_btm/  ...
├── kqk_btm/  ...
├── krk_btm/  ...
├── kbbk_wtm/ ...
├── kbbk_btm/ ...
├── krkn_wtm/ ...
└── krkn_btm/ ...
```

Each endgame folder is self-contained with its own pipeline scripts.

---

## Key Features

**Cyclic Knowledge Mining** — an iterative feature engineering methodology where `analyze.py` computes Information Gain specifically on misclassified positions (failures), revealing which chess concepts the model cannot "see". New attributes are added accordingly and the process repeats.

**Ray-Casting for Rook Attacks** — `wR_attacks_bN_direct` checks whether the rook has a clear line of sight to the knight, accounting for blocking pieces. This single attribute reduced KRKN training errors from 1,545 to 784.

**8-fold Symmetry** — the White King is restricted to the 10 canonical squares of the lower-left triangle (a1–d4), reducing the state space by ~8× without any information loss.

**Universal Pipeline** — `compress_exceptions.py` and `analyze.py` automatically detect piece columns via `endswith('Sq')`, making them compatible with any endgame without modification.

---

## Requirements

**C++ (probe):**
```bash
g++ probe_*.cpp egtb.cpp -o probe.exe -DT_INDEX64 -DSTOP_ON_ERROR=0 -fpermissive -I.
```

**Python pipeline:**
```
Python 3.8+
```
No external Python dependencies — only standard library (`csv`, `os`, `subprocess`, `struct`).

**Weka:**  
[Weka 3.8.6](https://waikato.github.io/weka-wiki/downloading_weka/) — set path in `train_weka.py` or via `WEKA_PATH` environment variable.

**Nalimov Tablebases:**  
Download `.emd` files from [http://tablebase.sesse.net/] or similar source.

---

## Usage

```bash
# 1. Compile and run probe (example: KRKN WTM)
cd krkn_wtm
g++ probe_krkn.cpp ../egtb.cpp -o probe_krkn.exe -DT_INDEX64 -DSTOP_ON_ERROR=0 -fpermissive -I..
.\probe_krkn.exe "C:\path\to\tablebases" wtm

# 2. Add features
python add_attributes_krkn.py csv-arff\krkn_wtm_raw.csv v2 wtm

# 3. Convert to ARFF
python csv_to_arff.py csv-arff\krkn_wtm_v2.csv wtm

# 4. Train (CV + training set predictions)
python train_weka.py csv-arff\krkn_wtm_v2.arff --mode both --memory 4g

# 5. Analyze failures
python analyze.py csv-arff\krkn_wtm_v2.csv csv-arff\krkn_wtm_v2_J48_train_predictions.csv

# 6. Compress exceptions
python compress_exceptions.py csv-arff\krkn_wtm_v2_failures.csv
```

---

## Theoretical Background

The approach is grounded in the **Minimum Description Length (MDL) principle** [Witten & Frank, 2005]:

```
L(D) = L(H) + L(D|H)
```

where `L(H)` is the size of the decision tree and `L(D|H)` is the size of the exceptions binary. Using an unpruned J48 increases `L(H)` but minimizes `L(D|H)` dramatically — the total `L(D)` is far smaller than any alternative representation.

---

## References

- Quinlan, J.R. (1993). *C4.5: Programs for Machine Learning*. Morgan Kaufmann.
- Witten, I.H. & Frank, E. (2005). *Data Mining: Practical Machine Learning Tools and Techniques*. Morgan Kaufmann.
- Rokach, L. & Maimon, O. (2008). *Data Mining with Decision Trees*. World Scientific.
- Thanou, N. (2012). *Compression of Chess Endgame Databases Using Data Mining*. Diploma Thesis, University of Patras.
- Nalimov, E., Haworth, G., Heinz, E. (2000). *Space-Efficient Indexing of Chess Endgame Tables*. ICGA Journal.

---

## License

Academic use only. The Nalimov API (`egtb.cpp`, `bitlib.h`, `tbdecode.h`, `lock.h`) is subject to its original license terms.
