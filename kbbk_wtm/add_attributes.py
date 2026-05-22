"""
add_attributes.py — KBBK (WTM + BTM)
======================================
Βημα 2: Υπολογισμος attributes απο RAW CSV για KBBK.

Χρηση:
    python add_attributes.py kbbk_wtm_raw.csv v1 wtm   (γεωμετρικα μονο — baseline)
    python add_attributes.py kbbk_btm_raw.csv v1 btm   (single mirroring)
    python add_attributes.py kbbk_btm_raw.csv v2 btm   (double mirroring + bK_on_edge)
    python add_attributes.py kbbk_btm_raw.csv v3 btm   (v2 + Meta-Mining attributes)

Εκδοσεις:
    v1 : γεωμετρικα attributes (χωρις sameColor) — Κυκλικη Εξορυξη Γνωσης Βημα 1
    v2 : sameColor + bK_on_edge + 17 γεωμετρικα + double mirroring
    v3 : v2 + bK_dist_corner + dist_bK_wB1 + dist_bK_wB2 (Meta-Mining)

Double Mirroring:
    1. Οριζοντιο: αν wB1 file >= 5 → καθρεφτισε οριζοντια
    2. Κατακορυφο: αν wB1 rank >= 5 → καθρεφτισε καθετα
    Αποτελεσμα: wB1 παντα στο κατω-αριστερο τεταρτο → ~75% μειωση

sameColor:
    'S' (Same)      = ιδιο χρωμα τετραγωνου → παντα Draw
    'D' (Different) = διαφορετικα χρωματα → J48 αποφασιζει

bK_on_edge:
    'Y' = μαυρος βασιλιας στην ακρη → ευνοει ματ
    'N' = μαυρος βασιλιας στο κεντρο

Μεθοδολογια WTM (Κυκλικη Εξορυξη Γνωσης):
    v1: μονο γεωμετρικα → analyze.py → IG_fail - IG_overall → νεο attribute → επαναληψη
    Αντιθεση με Θανου: το sameColor ανακαλυπτεται απο τα δεδομενα, οχι εκ των προτερων.
"""

import csv
import sys
import os


# ================================================================
# ΒΟΗΘΗΤΙΚΕΣ ΣΥΝΑΡΤΗΣΕΙΣ
# ================================================================

def f(pos):
    """Στηλη (1-8) απο square (0-63)."""
    return (pos % 8) + 1

def r(pos):
    """Γραμμη (1-8) απο square (0-63)."""
    return (pos // 8) + 1

def mirror_sq(sq):
    """Οριζοντια ανακλαση τετραγωνου: file → 9 - file."""
    file = sq % 8
    rank = sq // 8
    return rank * 8 + (7 - file)

def square_color(sq):
    """Χρωμα τετραγωνου: 0=λευκο, 1=σκουρο."""
    return (sq % 2) ^ ((sq // 8) % 2)


# ================================================================
# ΟΡΙΣΜΟΙ ΕΚΔΟΣΕΩΝ
# ================================================================

VERSIONS = {
    'v1': {
        'desc': 'v1 — μονο γεωμετρικα (Κυκλικη Εξορυξη Γνωσης Βημα 1, χωρις sameColor)',
        'attrs': [
            'fDiffKk',  'rDiffKk',
            'fDiffKM1', 'rDiffKM1',
            'fDiffKM2', 'rDiffKM2',
            'fDiffkM1', 'rDiffkM1',
            'fDiffkM2', 'rDiffkM2',
            'fDiffM1M2','rDiffM1M2',
            'wKFile',   'wKRank',
            'bKFile',   'bKRank',
        ]
    },
    'v2': {
        'desc': 'v2 — sameColor + bK_on_edge + 17 γεωμετρικα + double mirroring',
        'attrs': [
            'sameColor',
            'bK_on_edge',
            'fDiffKk',  'rDiffKk',
            'fDiffKM1', 'rDiffKM1',
            'fDiffKM2', 'rDiffKM2',
            'fDiffkM1', 'rDiffkM1',
            'fDiffkM2', 'rDiffkM2',
            'fDiffM1M2','rDiffM1M2',
            'wKFile',   'wKRank',
            'bKFile',   'bKRank',
        ]
    },
    'v3': {
        'desc': 'v3 — v2 + bK_dist_corner + dist_bK_wB1 + dist_bK_wB2 (Meta-Mining)',
        'attrs': [
            'sameColor',
            'bK_on_edge',
            'bK_dist_corner',
            'dist_bK_wB1',
            'dist_bK_wB2',
            'fDiffKk',  'rDiffKk',
            'fDiffKM1', 'rDiffKM1',
            'fDiffKM2', 'rDiffKM2',
            'fDiffkM1', 'rDiffkM1',
            'fDiffkM2', 'rDiffkM2',
            'fDiffM1M2','rDiffM1M2',
            'wKFile',   'wKRank',
            'bKFile',   'bKRank',
        ]
    },
    'v4': {
        'desc': 'v4 — v3 + bK_corner_id (ποια ακρη/γωνια)',
        'attrs': [
            'sameColor',
            'bK_on_edge',
            'bK_dist_corner',
            'bK_corner_id',
            'dist_bK_wB1',
            'dist_bK_wB2',
            'fDiffKk',  'rDiffKk',
            'fDiffKM1', 'rDiffKM1',
            'fDiffKM2', 'rDiffKM2',
            'fDiffkM1', 'rDiffkM1',
            'fDiffkM2', 'rDiffkM2',
            'fDiffM1M2','rDiffM1M2',
            'wKFile',   'wKRank',
            'bKFile',   'bKRank',
        ]
    },
}


# ================================================================
# MIRRORING
# ================================================================

def mirror_sq_h(sq):
    """Οριζοντια ανακλαση: file → 9 - file."""
    file = sq % 8
    rank = sq // 8
    return rank * 8 + (7 - file)

def mirror_sq_v(sq):
    """Κατακορυφη ανακλαση: rank → 9 - rank."""
    file = sq % 8
    rank = sq // 8
    return (7 - rank) * 8 + file

def apply_mirror(wk, wb1, wb2, bk):
    """
    Double mirroring — κανονικοποιηση θεσης:
    1. Οριζοντιο: αν wB1 στο δεξι μισο (file >= 5) → καθρεφτισε οριζοντια
    2. Κατακορυφο: αν wB1 στο πανω μισο (rank >= 5) → καθρεφτισε καθετα
    Αποτελεσμα: wB1 παντα στο κατω-αριστερο τεταρτο (file 1-4, rank 1-4)
    Μειωση: ~75% του αρχικου dataset
    """
    # Οριζοντιο mirroring
    if f(wb1) >= 5:
        wk  = mirror_sq_h(wk)
        wb1 = mirror_sq_h(wb1)
        wb2 = mirror_sq_h(wb2)
        bk  = mirror_sq_h(bk)

    # Κατακορυφο mirroring
    if r(wb1) >= 5:
        wk  = mirror_sq_v(wk)
        wb1 = mirror_sq_v(wb1)
        wb2 = mirror_sq_v(wb2)
        bk  = mirror_sq_v(bk)

    return wk, wb1, wb2, bk


# ================================================================
# ΥΠΟΛΟΓΙΣΜΟΣ ATTRIBUTES
# ================================================================

def compute_attributes(wk, wb1, wb2, bk, attrs):
    """
    Υπολογιζει ολα τα attributes για μια θεση KBBK.
    Προυποθεση: εχει ηδη εφαρμοστει mirroring.
    """
    result = {}

    # sameColor: S=ιδιο χρωμα (παντα draw), D=διαφορετικο
    if 'sameColor' in attrs:
        result['sameColor'] = 'S' if square_color(wb1) == square_color(wb2) else 'D'

    # bK_on_edge: αν ο μαυρος βασιλιας ειναι στην ακρη
    if 'bK_on_edge' in attrs:
        bk_file = f(bk)
        bk_rank = r(bk)
        result['bK_on_edge'] = 'Y' if (bk_file == 1 or bk_file == 8 or
                                        bk_rank == 1 or bk_rank == 8) else 'N'

    # bK_dist_corner: αποσταση μαυρου βασιλια απο πιο κοντινη γωνια (0-3)
    # 0 = στη γωνια, 3 = στο κεντρο
    # Γωνιες: a1(0,0), a8(0,7), h1(7,0), h8(7,7) σε 0-indexed
    if 'bK_dist_corner' in attrs:
        bf = f(bk) - 1  # 0-indexed
        br = r(bk) - 1  # 0-indexed
        dist_to_edge_f = min(bf, 7 - bf)
        dist_to_edge_r = min(br, 7 - br)
        result['bK_dist_corner'] = max(dist_to_edge_f, dist_to_edge_r)

    # dist_bK_wB1: Chebyshev αποσταση μαυρου βασιλια - επισκοπος 1
    if 'dist_bK_wB1' in attrs:
        result['dist_bK_wB1'] = max(abs(f(bk)-f(wb1)), abs(r(bk)-r(wb1)))

    # dist_bK_wB2: Chebyshev αποσταση μαυρου βασιλια - επισκοπος 2
    if 'dist_bK_wB2' in attrs:
        result['dist_bK_wB2'] = max(abs(f(bk)-f(wb2)), abs(r(bk)-r(wb2)))

    # bK_corner_id: ποια ακριβως γωνια/ακρη ειναι ο μαυρος βασιλιας
    # 0=a1, 1=a8, 2=h1, 3=h8 (γωνιες)
    # 4=file_a, 5=file_h, 6=rank_1, 7=rank_8 (ακρες)
    # 8=κεντρο (δεν ειναι στην ακρη)
    if 'bK_corner_id' in attrs:
        bf = f(bk)  # 1-8
        br = r(bk)  # 1-8
        on_a = (bf == 1)
        on_h = (bf == 8)
        on_1 = (br == 1)
        on_8 = (br == 8)
        if on_a and on_1:   result['bK_corner_id'] = 0  # γωνια a1
        elif on_a and on_8: result['bK_corner_id'] = 1  # γωνια a8
        elif on_h and on_1: result['bK_corner_id'] = 2  # γωνια h1
        elif on_h and on_8: result['bK_corner_id'] = 3  # γωνια h8
        elif on_a:          result['bK_corner_id'] = 4  # ακρη a (file 1)
        elif on_h:          result['bK_corner_id'] = 5  # ακρη h (file 8)
        elif on_1:          result['bK_corner_id'] = 6  # ακρη rank 1
        elif on_8:          result['bK_corner_id'] = 7  # ακρη rank 8
        else:               result['bK_corner_id'] = 8  # κεντρο

    # Γεωμετρικες διαφορες
    if 'fDiffKk'   in attrs: result['fDiffKk']   = f(wk)  - f(bk)
    if 'rDiffKk'   in attrs: result['rDiffKk']   = r(wk)  - r(bk)
    if 'fDiffKM1'  in attrs: result['fDiffKM1']  = f(wk)  - f(wb1)
    if 'rDiffKM1'  in attrs: result['rDiffKM1']  = r(wk)  - r(wb1)
    if 'fDiffKM2'  in attrs: result['fDiffKM2']  = f(wk)  - f(wb2)
    if 'rDiffKM2'  in attrs: result['rDiffKM2']  = r(wk)  - r(wb2)
    if 'fDiffkM1'  in attrs: result['fDiffkM1']  = f(bk)  - f(wb1)
    if 'rDiffkM1'  in attrs: result['rDiffkM1']  = r(bk)  - r(wb1)
    if 'fDiffkM2'  in attrs: result['fDiffkM2']  = f(bk)  - f(wb2)
    if 'rDiffkM2'  in attrs: result['rDiffkM2']  = r(bk)  - r(wb2)
    if 'fDiffM1M2' in attrs: result['fDiffM1M2'] = f(wb1) - f(wb2)
    if 'rDiffM1M2' in attrs: result['rDiffM1M2'] = r(wb1) - r(wb2)
    if 'wKFile'    in attrs: result['wKFile']    = f(wk)
    if 'wKRank'    in attrs: result['wKRank']    = r(wk)
    if 'bKFile'    in attrs: result['bKFile']    = f(bk)
    if 'bKRank'    in attrs: result['bKRank']    = r(bk)

    return result


# ================================================================
# ΚΥΡΙΑ ΣΥΝΑΡΤΗΣΗ
# ================================================================

def add_attributes(raw_csv, version, wtm):

    if version not in VERSIONS:
        print(f"ERROR: Αγνωστη εκδοση '{version}'")
        sys.exit(1)

    mode_str = 'wtm' if wtm else 'btm'
    ver_info = VERSIONS[version]
    attrs    = ver_info['attrs']

    print("=" * 50)
    print("KBBK Attribute Calculator")
    print("=" * 50)
    print(f"Εκδοση : {version} — {ver_info['desc']}")
    print(f"Mode   : {'WTM' if wtm else 'BTM'}")
    print(f"Attrs  : {len(attrs)} (sameColor + γεωμετρικα)")

    # Φορτωση raw CSV
    rows = []
    with open(raw_csv, newline='', encoding='utf-8-sig') as f_in:
        reader = csv.DictReader(f_in)
        for row in reader:
            rows.append(row)

    print(f"Θεσεις : {len(rows)} (πριν mirroring dedup)")

    # Ονομα αρχειου εξοδου
    raw_dir  = os.path.dirname(os.path.abspath(raw_csv))
    if os.path.basename(raw_dir) == 'csv-arff':
        out_dir = raw_dir
    else:
        out_dir = os.path.join(raw_dir, 'csv-arff')
        os.makedirs(out_dir, exist_ok=True)

    base     = f"kbbk_{mode_str}_{version}.csv"
    out_file = os.path.join(out_dir, base)

    # Προσθετουμε wB1File/wB1Rank/wB2File/wB2Rank ως metadata
    # Δεν ειναι Weka attributes — χρησιμοποιουνται μονο απο compress_exceptions.py
    meta_cols  = ['wKSq', 'wB1Sq', 'wB2Sq', 'bKSq']
    fieldnames = attrs + meta_cols + ['result']

    computed_rows = []
    seen = set()  # για deduplication μετα το mirroring
    skipped = 0

    with open(out_file, 'w', newline='', encoding='utf-8-sig') as f_out:
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()

        for i, row in enumerate(rows):
            wk  = int(row['wKSq'])
            wb1 = int(row['wB1Sq'])
            wb2 = int(row['wB2Sq'])
            bk  = int(row['bKSq'])

            # Mirroring
            wk_m, wb1_m, wb2_m, bk_m = apply_mirror(wk, wb1, wb2, bk)

            # Κανονικοποιηση: wb1 <= wb2 παντα
            if wb1_m > wb2_m:
                wb1_m, wb2_m = wb2_m, wb1_m

            # Deduplication
            key = (wk_m, wb1_m, wb2_m, bk_m)
            if key in seen:
                skipped += 1
                continue
            seen.add(key)

            # Υπολογισμος attributes
            attr_vals = compute_attributes(wk_m, wb1_m, wb2_m, bk_m, attrs)

            out_row = {a: attr_vals[a] for a in attrs}
            # Metadata: squares 0-63 μετα mirroring — για compress_exceptions.py
            # Τυπος: sq = (file-1) + (rank-1)*8
            out_row['wKSq']  = wk_m
            out_row['wB1Sq'] = wb1_m
            out_row['wB2Sq'] = wb2_m
            out_row['bKSq']  = bk_m
            out_row['result']  = row['result']

            writer.writerow(out_row)
            computed_rows.append(out_row)

            # Progress
            if (i+1) % 500000 == 0:
                print(f"  Επεξεργασια: {i+1}/{len(rows)} ({len(computed_rows)} μοναδικες)")

    print(f"\nΑρχειο : {out_file}")
    print(f"Πριν   : {len(rows)} θεσεις")
    print(f"Μετα   : {len(computed_rows)} θεσεις (mirroring dedup)")
    print(f"Μειωση : {100*(1-len(computed_rows)/len(rows)):.1f}%")

    # Validation
    _run_validation(computed_rows, out_file, wtm)

    return out_file


# ================================================================
# VALIDATION
# ================================================================

def _run_validation(computed_rows, out_file, wtm=True):
    total  = len(computed_rows)
    wins   = sum(1 for r in computed_rows if r['result'] == 'white')
    blacks = sum(1 for r in computed_rows if r['result'] == 'black')
    draws  = total - wins - blacks

    print()
    print("=" * 50)
    print("VALIDATION")
    print("=" * 50)
    print(f"Θεσεις      : {total}")
    print(f"Win (white) : {wins}  ({100*wins/total:.1f}%)")
    print(f"Draw        : {draws} ({100*draws/total:.1f}%)")
    if not wtm:
        print(f"Win (black) : {blacks} ({100*blacks/total:.1f}%)")
    print()

    problems = 0

    # Ελεγχος sameColor μονο αν υπαρχει το attribute
    has_same_color = computed_rows and 'sameColor' in computed_rows[0]
    if has_same_color:
        same_color = sum(1 for r in computed_rows if r['sameColor'] == 'S')
        diff_color = total - same_color
        print(f"sameColor=S : {same_color} ({100*same_color/total:.1f}%)")
        print(f"sameColor=D : {diff_color} ({100*diff_color/total:.1f}%)")
        same_but_win = sum(1 for r in computed_rows
                           if r['sameColor'] == 'S' and r['result'] == 'white')
        if same_but_win > 0:
            print(f"  [ERROR] sameColor=S αλλα Win: {same_but_win} θεσεις!")
            problems += 1
        else:
            print(f"  [OK]   sameColor=S → παντα Draw ✅")
    else:
        print("  [INFO] sameColor δεν υπαρχει στην εκδοση αυτη (v1 baseline)")

    # Ελεγχος Win% εναντι αναμενομενου
    win_pct = 100.0 * wins / total if total > 0 else 0
    if wtm:
        # WTM: αναμενεται ~55-65% Win
        if win_pct < 50 or win_pct > 70:
            print(f"  [WARN] Win%={win_pct:.1f} (αναμενομενο WTM: ~55-65%)")
        else:
            print(f"  [OK]   Win%={win_pct:.1f} (αναμενομενο WTM: ~55-65%) ✅")
    else:
        # BTM: αναμενεται ~40% Win
        if win_pct < 35 or win_pct > 55:
            print(f"  [WARN] Win%={win_pct:.1f} (αναμενομενο BTM: ~40%)")
        else:
            print(f"  [OK]   Win%={win_pct:.1f} (αναμενομενο BTM: ~40%) ✅")

    mode_str = 'wtm' if wtm else 'btm'
    if problems == 0:
        print("\nValidation: OK")
        print(f"Επομενο βημα: python csv_to_arff.py {out_file} {mode_str}")
    else:
        print(f"\nValidation: {problems} προβληματικα.")


# ================================================================
# MAIN
# ================================================================

def main():
    if len(sys.argv) < 3:
        print("Χρηση: python add_attributes.py <raw_csv> <version> [wtm/btm]")
        print("Παραδειγμα:")
        print("  python add_attributes.py csv-arff\\kbbk_btm_raw.csv v1 btm")
        sys.exit(1)

    raw_csv = sys.argv[1]
    version = sys.argv[2]
    wtm     = True if len(sys.argv) < 4 or sys.argv[3] == 'wtm' else False

    if not os.path.exists(raw_csv):
        print(f"ERROR: Δεν βρεθηκε: {raw_csv}")
        sys.exit(1)

    add_attributes(raw_csv, version, wtm)


if __name__ == '__main__':
    main()
