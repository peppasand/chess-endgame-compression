"""
add_attributes.py — KRK
=======================
Βημα 2: Υπολογισμος attributes απο RAW CSV για KRK.

Χρηση:
    python add_attributes.py krk_btm_raw.csv v1 btm

Εκδοσεις:
    v1 : Γεωμετρικα attributes (Θανου 2012) — διαφορες + απολυτες θεσεις

Σημειωση:
    Ο Θανου χρησιμοποιησε μονο γεωμετρικα attributes για KRK BTM
    και πετυχε 99.9777% με μολις 37 φυλλα δεντρου.
    Το KRK ειναι πιο "κανονικο" απο KQK — ο πυργος δεν δημιουργει
    τοσους stalemate κινδυνους οσο η βασιλισσα.
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

def sq(file, rank):
    """Square (0-63) απο file (1-8) και rank (1-8)."""
    return (rank - 1) * 8 + (file - 1)

def dist(a, b):
    """Αποσταση Chebyshev μεταξυ δυο τετραγωνων."""
    return max(abs(f(a)-f(b)), abs(r(a)-r(b)))


# ================================================================
# ΟΡΙΣΜΟΙ ΕΚΔΟΣΕΩΝ
# ================================================================

VERSIONS = {
    'v1': {
        'desc': 'v1 — Γεωμετρικα attributes Θανου (διαφορες + απολυτες θεσεις)',
        'attrs': [
            # Γεωμετρικες διαφορες (Θανου)
            'fileDiffKk',   # λευκος βασιλιας - μαυρος βασιλιας (στηλη)
            'fileDiffKR',   # λευκος βασιλιας - πυργος (στηλη)
            'fileDiffkR',   # μαυρος βασιλιας - πυργος (στηλη)
            'rankDiffKk',   # λευκος βασιλιας - μαυρος βασιλιας (γραμμη)
            'rankDiffKR',   # λευκος βασιλιας - πυργος (γραμμη)
            'rankDiffkR',   # μαυρος βασιλιας - πυργος (γραμμη)
            # Απολυτες θεσεις (Θανου)
            'wKFile', 'wKRank',
            'wRFile', 'wRRank',
            'bKFile', 'bKRank',
        ]
    },
}


# ================================================================
# ΥΠΟΛΟΓΙΣΜΟΣ ATTRIBUTES
# ================================================================

def compute_attribute(attr, wk, wr, bk, wtm):
    """
    Υπολογιζει ενα attribute για μια θεση KRK.
    wk: white king square (0-63)
    wr: white rook square (0-63)
    bk: black king square (0-63)
    """

    # --- Γεωμετρικες διαφορες ---

    if attr == 'fileDiffKk':
        return f(wk) - f(bk)

    if attr == 'fileDiffKR':
        return f(wk) - f(wr)

    if attr == 'fileDiffkR':
        return f(bk) - f(wr)

    if attr == 'rankDiffKk':
        return r(wk) - r(bk)

    if attr == 'rankDiffKR':
        return r(wk) - r(wr)

    if attr == 'rankDiffkR':
        return r(bk) - r(wr)

    # --- Απολυτες θεσεις ---

    if attr == 'wKFile': return f(wk)
    if attr == 'wKRank': return r(wk)
    if attr == 'wRFile': return f(wr)
    if attr == 'wRRank': return r(wr)
    if attr == 'bKFile': return f(bk)
    if attr == 'bKRank': return r(bk)

    raise ValueError(f"Αγνωστο attribute: {attr}")


# ================================================================
# ΚΥΡΙΑ ΣΥΝΑΡΤΗΣΗ
# ================================================================

def add_attributes(raw_csv, version, wtm):
    """
    Διαβαζει το RAW CSV και προσθετει attributes.
    Αποθηκευει στο csv-arff/ με το ονομα krk_{mode}_{version}.csv
    """

    if version not in VERSIONS:
        print(f"ERROR: Αγνωστη εκδοση '{version}'. Διαθεσιμες: {list(VERSIONS.keys())}")
        sys.exit(1)

    mode_str = 'wtm' if wtm else 'btm'
    ver_info = VERSIONS[version]
    attrs    = ver_info['attrs']

    print("=" * 50)
    print("KRK Attribute Calculator")
    print("=" * 50)
    print(f"Εκδοση : {version} — {ver_info['desc']}")
    print(f"Mode   : {'WTM' if wtm else 'BTM'}")
    print(f"Attrs  : {len(attrs)} γεωμετρικα")

    # Φορτωση raw CSV
    rows = []
    with open(raw_csv, newline='', encoding='utf-8-sig') as f_in:
        reader = csv.DictReader(f_in)
        for row in reader:
            rows.append(row)

    print(f"Θεσεις : {len(rows)}")

    # Ονομα αρχειου εξοδου — αποθηκευση στο csv-arff/
    raw_dir  = os.path.dirname(os.path.abspath(raw_csv))
    # Αν το raw CSV ειναι σε csv-arff/, βγαινουμε εκει
    # Αλλιως δημιουργουμε csv-arff/ διπλα στο raw CSV
    if os.path.basename(raw_dir) == 'csv-arff':
        out_dir = raw_dir
    else:
        out_dir = os.path.join(raw_dir, 'csv-arff')
        os.makedirs(out_dir, exist_ok=True)

    base     = f"krk_{mode_str}_{version}.csv"
    out_file = os.path.join(out_dir, base)

    # Εγγραφη enriched CSV
    fieldnames = ['wKFile', 'wKRank', 'wQFile', 'wQRank', 'bKFile', 'bKRank'] + \
                 [a for a in attrs if a not in
                  ['wKFile','wKRank','wQFile','wQRank','bKFile','bKRank']] + \
                 ['result']

    # Χρησιμοποιουμε τη σειρα των attrs απο τον ορισμο της εκδοσης
    fieldnames = attrs + ['result']

    computed_rows = []
    with open(out_file, 'w', newline='', encoding='utf-8-sig') as f_out:
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()

        for row in rows:
            wk   = int(row['wKSq'])
            wr   = int(row['wRSq'])
            bk   = int(row['bKSq'])

            out_row = {}
            for attr in attrs:
                out_row[attr] = compute_attribute(attr, wk, wr, bk, wtm)
            out_row['result'] = row['result']

            writer.writerow(out_row)
            computed_rows.append(out_row)

    print(f"Αρχειο : {out_file}")

    # Validation
    _run_validation(computed_rows, out_file, wtm)

    return out_file


# ================================================================
# VALIDATION
# ================================================================

def _run_validation(computed_rows, out_file, wtm=True):
    """
    Ελεγχει την ορθοτητα του dataset.
    Για KRK BTM: αναμενεται ~90.1% Win, ~9.9% Draw.
    """
    total = len(computed_rows)
    wins  = sum(1 for r in computed_rows if r['result'] == 'white')
    draws = total - wins

    print()
    print("=" * 50)
    print("VALIDATION")
    print("=" * 50)
    print(f"Θεσεις  : {total}")
    print(f"Win     : {wins}  ({100*wins/total:.1f}%)")
    print(f"Draw    : {draws} ({100*draws/total:.1f}%)")
    print()

    problems = 0

    if not wtm:
        win_pct = 100 * wins / total
        print("  [INFO] BTM mode")
        print(f"  [INFO] Win%={win_pct:.1f}% (αναμενομενο ~90.1% για KRK BTM)")
        if 85.0 <= win_pct <= 95.0:
            print(f"  [OK]   Win% εντος αναμενομενου ευρους (85-95%)")
        else:
            print(f"  [WARN] Win% εκτος αναμενομενου ευρους (85-95%)")
            problems += 1
    else:
        win_pct = 100 * wins / total
        print(f"  [INFO] WTM mode — Win%={win_pct:.1f}%")
        if win_pct < 99.0:
            print(f"  [WARN] KRK WTM αναμενεται ~100% Win")
            problems += 1
        else:
            print(f"  [OK]   Win% εντος αναμενομενου ευρους")

    print()
    if problems == 0:
        print("Validation: OK")
        print(f"Επομενο βημα: python csv_to_arff.py {out_file} btm")
    else:
        print(f"Validation: {problems} προβληματικα.")


# ================================================================
# MAIN
# ================================================================

def main():
    if len(sys.argv) < 3:
        print("Χρηση: python add_attributes.py <raw_csv> <version> [wtm/btm]")
        print()
        print("Παραδειγμα:")
        print("  python add_attributes.py csv-arff\\krk_btm_raw.csv v1 btm")
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
