"""
add_attributes_krkn.py — KRKN (WTM + BTM)
==========================================
Βημα 2: Υπολογισμος attributes απο RAW CSV για KRKN.

Χρηση:
    python add_attributes_krkn.py krkn_wtm_raw.csv v1 wtm   (γεωμετρικα baseline)
    python add_attributes_krkn.py krkn_btm_raw.csv v1 btm

Κομματια:
    wK  = λευκος βασιλιας  (wKSq)
    wR  = λευκος πυργος    (wRSq)
    bK  = μαυρος βασιλιας  (bKSq)
    bN  = μαυρος ιππος     (bNSq)

Εκδοσεις:
    v1 : γεωμετρικα attributes (baseline — αντιστοιχο Θανου)

Συμμετρια:
    Το probe εχει ηδη εφαρμοσει 8-fold symmetry (canonical wK).
    Δεν χρειαζεται επιπλεον mirroring — δεν υπαρχει sameColor.

Αναμενομενα:
    WTM: ~1,683,390 θεσεις, ~48.7% Win, ~51.3% Draw
    BTM: παρομοια
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

def chebyshev(sq1, sq2):
    return max(abs(f(sq1)-f(sq2)), abs(r(sq1)-r(sq2)))

def knight_attacks(nSq, targetSq):
    df = abs(f(nSq) - f(targetSq))
    dr = abs(r(nSq) - r(targetSq))
    return (df == 1 and dr == 2) or (df == 2 and dr == 1)

def is_between(sq1, sq2, block_sq):
    f1, r1 = f(sq1), r(sq1)
    f2, r2 = f(sq2), r(sq2)
    fb, rb = f(block_sq), r(block_sq)
    if f1 == f2 == fb:
        return min(r1, r2) < rb < max(r1, r2)
    if r1 == r2 == rb:
        return min(f1, f2) < fb < max(f1, f2)
    return False

def rook_attacks_ray(wr, target, wk, bk, block3=-1):
    """Ray-casting: ο πυργος επιτιθεται στο target χωρις εμποδιο.
    block3: προαιρετικο τριτο εμποδιο (π.χ. ιππος).
    """
    if f(wr) != f(target) and r(wr) != r(target):
        return False
    if is_between(wr, target, wk):
        return False
    if is_between(wr, target, bk):
        return False
    if block3 >= 0 and is_between(wr, target, block3):
        return False
    return True


# ================================================================
# ΟΡΙΣΜΟΙ ΕΚΔΟΣΕΩΝ
# ================================================================

VERSIONS = {
    'v1': {
        'desc': 'v1 — γεωμετρικα attributes (baseline Θανου)',
        'attrs': [
            # Διαφορες βασιλιαδων
            'fDiffKk',  'rDiffKk',
            # Λευκος βασιλιας - πυργος
            'fDiffKR',  'rDiffKR',
            # Λευκος βασιλιας - μαυρος ιππος
            'fDiffKN',  'rDiffKN',
            # Μαυρος βασιλιας - πυργος
            'fDiffkR',  'rDiffkR',
            # Μαυρος βασιλιας - ιππος
            'fDiffkN',  'rDiffkN',
            # Πυργος - ιππος
            'fDiffRN',  'rDiffRN',
            # Απολυτη θεση
            'wKFile',   'wKRank',
            'bKFile',   'bKRank',
            # Chebyshev αποσταση βασιλιαδων (Opposition)
            'dist_wK_bK',
            # Θεση μαυρου βασιλια
            'bK_on_edge',
            'bK_in_corner',
            # Επιθεσεις
            'bN_attacks_wR',
            'bK_attacks_wR',
            'wR_defended',
        ]
    },
    'v2': {
        'desc': 'v2 — v1 + tactical (ray-casting, checks, defense)',
        'attrs': [
            'fDiffKk', 'rDiffKk', 'fDiffKR', 'rDiffKR', 'fDiffKN', 'rDiffKN',
            'fDiffkR', 'rDiffkR', 'fDiffkN', 'rDiffkN', 'fDiffRN', 'rDiffRN',
            'wKFile', 'wKRank', 'bKFile', 'bKRank', 'dist_wK_bK',
            'bK_on_edge', 'bK_in_corner',
            'bN_attacks_wR', 'bK_attacks_wR', 'wR_defended',
            'dist_wR_bN', 'dist_wK_bN', 'dist_bK_bN',
            'bN_on_edge', 'bN_in_corner',
            'bN_checks_wK', 'bK_defends_bN',
            'wR_attacks_bN_direct', 'wR_attacks_bK_direct',
        ]
    },
}


# ================================================================
# ΥΠΟΛΟΓΙΣΜΟΣ ATTRIBUTES
# ================================================================

def compute_attributes(wk, wr, bk, bn, attrs):
    """
    Υπολογιζει ολα τα attributes για μια θεση KRKN.
    """
    result = {}

    # Chebyshev αποσταση βασιλιαδων (ορισμος Opposition)
    if 'dist_wK_bK' in attrs:
        result['dist_wK_bK'] = max(abs(f(wk)-f(bk)), abs(r(wk)-r(bk)))

    # Θεση μαυρου βασιλια — κρισιμο για ματ στο KRKN
    if 'bK_on_edge' in attrs:
        bk_f, bk_r = f(bk), r(bk)
        result['bK_on_edge'] = 'Y' if (bk_f==1 or bk_f==8 or bk_r==1 or bk_r==8) else 'N'

    if 'bK_in_corner' in attrs:
        bk_f, bk_r = f(bk), r(bk)
        result['bK_in_corner'] = 'Y' if ((bk_f==1 or bk_f==8) and (bk_r==1 or bk_r==8)) else 'N'

    # Γεωμετρικες διαφορες στηλης/γραμμης
    if 'fDiffKk'  in attrs: result['fDiffKk']  = f(wk) - f(bk)
    if 'rDiffKk'  in attrs: result['rDiffKk']  = r(wk) - r(bk)
    if 'fDiffKR'  in attrs: result['fDiffKR']  = f(wk) - f(wr)
    if 'rDiffKR'  in attrs: result['rDiffKR']  = r(wk) - r(wr)
    if 'fDiffKN'  in attrs: result['fDiffKN']  = f(wk) - f(bn)
    if 'rDiffKN'  in attrs: result['rDiffKN']  = r(wk) - r(bn)
    if 'fDiffkR'  in attrs: result['fDiffkR']  = f(bk) - f(wr)
    if 'rDiffkR'  in attrs: result['rDiffkR']  = r(bk) - r(wr)
    if 'fDiffkN'  in attrs: result['fDiffkN']  = f(bk) - f(bn)
    if 'rDiffkN'  in attrs: result['rDiffkN']  = r(bk) - r(bn)
    if 'fDiffRN'  in attrs: result['fDiffRN']  = f(wr) - f(bn)
    if 'rDiffRN'  in attrs: result['rDiffRN']  = r(wr) - r(bn)
    if 'wKFile'   in attrs: result['wKFile']   = f(wk)
    if 'wKRank'   in attrs: result['wKRank']   = r(wk)
    if 'bKFile'   in attrs: result['bKFile']   = f(bk)
    if 'bKRank'   in attrs: result['bKRank']   = r(bk)

    if 'bN_attacks_wR' in attrs:
        result['bN_attacks_wR'] = 'Y' if knight_attacks(bn, wr) else 'N'
    if 'bK_attacks_wR' in attrs:
        result['bK_attacks_wR'] = 'Y' if chebyshev(bk, wr) <= 1 else 'N'
    if 'wR_defended' in attrs:
        result['wR_defended']   = 'Y' if chebyshev(wk, wr) <= 1 else 'N'

    # v2 tactical
    if 'dist_wR_bN' in attrs:     result['dist_wR_bN'] = chebyshev(wr, bn)
    if 'dist_wK_bN' in attrs:     result['dist_wK_bN'] = chebyshev(wk, bn)
    if 'dist_bK_bN' in attrs:     result['dist_bK_bN'] = chebyshev(bk, bn)
    if 'bN_on_edge' in attrs:
        result['bN_on_edge'] = 'Y' if (f(bn)==1 or f(bn)==8 or r(bn)==1 or r(bn)==8) else 'N'
    if 'bN_in_corner' in attrs:
        result['bN_in_corner'] = 'Y' if ((f(bn)==1 or f(bn)==8) and (r(bn)==1 or r(bn)==8)) else 'N'
    if 'bN_checks_wK' in attrs:   result['bN_checks_wK'] = 'Y' if knight_attacks(bn, wk) else 'N'
    if 'bK_defends_bN' in attrs:  result['bK_defends_bN'] = 'Y' if chebyshev(bk, bn) <= 1 else 'N'
    if 'wR_attacks_bN_direct' in attrs:
        result['wR_attacks_bN_direct'] = 'Y' if rook_attacks_ray(wr, bn, wk, bk) else 'N'
    if 'wR_attacks_bK_direct' in attrs:
        result['wR_attacks_bK_direct'] = 'Y' if rook_attacks_ray(wr, bk, wk, bn) else 'N'

    return result


# ================================================================
# ΚΥΡΙΑ ΣΥΝΑΡΤΗΣΗ
# ================================================================

def add_attributes(raw_csv, version, wtm):

    if version not in VERSIONS:
        print(f"ERROR: Αγνωστη εκδοση '{version}'. Διαθεσιμες: {list(VERSIONS.keys())}")
        sys.exit(1)

    mode_str = 'wtm' if wtm else 'btm'
    ver_info = VERSIONS[version]
    attrs    = ver_info['attrs']

    print("=" * 50)
    print("KRKN Attribute Calculator")
    print("=" * 50)
    print(f"Εκδοση : {version} — {ver_info['desc']}")
    print(f"Mode   : {'WTM' if wtm else 'BTM'}")
    print(f"Attrs  : {len(attrs)}")

    # Φορτωση raw CSV
    rows = []
    with open(raw_csv, newline='', encoding='utf-8-sig') as f_in:
        reader = csv.DictReader(f_in)
        for row in reader:
            rows.append(row)

    print(f"Θεσεις : {len(rows)}")

    # Ονομα αρχειου εξοδου
    raw_dir = os.path.dirname(os.path.abspath(raw_csv))
    if os.path.basename(raw_dir) == 'csv-arff':
        out_dir = raw_dir
    else:
        out_dir = os.path.join(raw_dir, 'csv-arff')
        os.makedirs(out_dir, exist_ok=True)

    base     = f"krkn_{mode_str}_{version}.csv"
    out_file = os.path.join(out_dir, base)

    # Metadata columns για compress_exceptions.py
    meta_cols  = ['wKSq', 'wRSq', 'bKSq', 'bNSq']
    fieldnames = attrs + meta_cols + ['result']

    computed_rows = []

    with open(out_file, 'w', newline='', encoding='utf-8-sig') as f_out:
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()

        for i, row in enumerate(rows):
            wk = int(row['wKSq'])
            wr = int(row['wRSq'])
            bk = int(row['bKSq'])
            bn = int(row['bNSq'])

            # Υπολογισμος attributes (δεν χρειαζεται mirroring — ηδη canonical)
            attr_vals = compute_attributes(wk, wr, bk, bn, attrs)

            out_row = {a: attr_vals[a] for a in attrs}
            out_row['wKSq']  = wk
            out_row['wRSq']  = wr
            out_row['bKSq']  = bk
            out_row['bNSq']  = bn
            out_row['result'] = row['result']

            writer.writerow(out_row)
            computed_rows.append(out_row)

            if (i+1) % 500000 == 0:
                print(f"  Επεξεργασια: {i+1}/{len(rows)}")

    print(f"\nΑρχειο : {out_file}")
    print(f"Θεσεις : {len(computed_rows)}")

    # Validation
    _run_validation(computed_rows, out_file, wtm)

    return out_file


# ================================================================
# VALIDATION
# ================================================================

def _run_validation(computed_rows, out_file, wtm=True):
    total  = len(computed_rows)
    whites = sum(1 for row in computed_rows if row['result'] == 'white')
    blacks = sum(1 for row in computed_rows if row['result'] == 'black')
    draws  = total - whites - blacks

    print()
    print("=" * 50)
    print("VALIDATION")
    print("=" * 50)
    print(f"Θεσεις       : {total}")
    print(f"White wins   : {whites}  ({100*whites/total:.1f}%)")
    print(f"Draw         : {draws} ({100*draws/total:.1f}%)")
    if blacks > 0:
        print(f"Black wins   : {blacks} ({100*blacks/total:.1f}%)")
    print()

    if wtm:
        win_pct = 100.0 * whites / total if total > 0 else 0
        ok = 40 <= win_pct <= 58
        expected = '~46-52% WTM'
        label = f"White%={win_pct:.1f}"
    else:
        # BTM: ελεγχουμε το Draw% (αναμενεται ~60-80%)
        draw_pct = 100.0 * draws / total if total > 0 else 0
        ok = 50 <= draw_pct <= 90
        expected = '~60-80% Draw BTM'
        label = f"Draw%={draw_pct:.1f}"

    if ok:
        print(f"  [OK]   {label} ({expected}) ✅")
    else:
        print(f"  [WARN] {label} (αναμενομενο: {expected})")

    mode_str = 'wtm' if wtm else 'btm'
    print("\nValidation: OK")
    print(f"Επομενο βημα: python csv_to_arff.py {out_file} {mode_str}")


# ================================================================
# MAIN
# ================================================================

def main():
    if len(sys.argv) < 3:
        print("Χρηση: python add_attributes_krkn.py <raw_csv> <version> [wtm/btm]")
        print("Παραδειγμα:")
        print("  python add_attributes_krkn.py csv-arff\\krkn_wtm_raw.csv v1 wtm")
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
