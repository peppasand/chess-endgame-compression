"""
analyze_errors.py
=================
Ανάλυση λανθασμένων θέσεων σε dataset KPK.

Χρήση:
    python analyze_errors.py kpk_wtm_v4_critical.csv

Τι κάνει:
    1. Φορτώνει το CSV
    2. Εμφανίζει γενικά στατιστικά
    3. Αναλύει κάθε attribute (Win% όταν Y/N)
    4. Βρίσκει τις λανθασμένες θέσεις ανά attribute
    5. Εξάγει τα αποτελέσματα σε αρχείο txt
"""

import csv
import sys
from collections import Counter


# ================================================================
# ΦΟΡΤΩΣΗ ΔΕΔΟΜΕΝΩΝ
# ================================================================

def load_csv(filename):
    rows = []
    with open(filename, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


# ================================================================
# ΓΕΝΙΚΑ ΣΤΑΤΙΣΤΙΚΑ
# ================================================================

def general_stats(rows):
    total = len(rows)
    results = Counter(r['result'] for r in rows)
    
    lines = []
    lines.append("=" * 60)
    lines.append("ΓΕΝΙΚΑ ΣΤΑΤΙΣΤΙΚΑ")
    lines.append("=" * 60)
    lines.append(f"Συνολικες θεσεις : {total}")
    for k, v in sorted(results.items()):
        lines.append(f"  {k:<8}: {v:>7} ({100*v/total:.2f}%)")
    return lines


# ================================================================
# ΑΝΑΛΥΣΗ ΚΑΘΕ ATTRIBUTE
# ================================================================

def attribute_analysis(rows):
    total = len(rows)
    lines = []
    lines.append("")
    lines.append("=" * 60)
    lines.append("ΑΝΑΛΥΣΗ ATTRIBUTES")
    lines.append("=" * 60)

    # Βρες ποια attributes υπάρχουν στο CSV
    all_cols = list(rows[0].keys())
    attr_cols = [c for c in all_cols if c != 'result']

    for attr in attr_cols:
        # Ελέγχουμε αν είναι numeric ή nominal
        sample_vals = [r[attr] for r in rows[:10]]
        is_numeric = all(_is_number(v) for v in sample_vals)

        lines.append(f"\n--- {attr} ---")

        if is_numeric:
            # Numeric attribute: εμφάνισε κατανομή τιμών
            vals = Counter(int(r[attr]) for r in rows)
            lines.append(f"  {'Τιμη':>5}  {'Θεσεις':>8}  {'Win':>8}  {'Win%':>7}  {'Draw':>8}  {'Draw%':>7}")
            for v in sorted(vals.keys()):
                cnt = vals[v]
                wins  = sum(1 for r in rows if int(r[attr])==v and r['result']=='white')
                draws = cnt - wins
                lines.append(f"  {v:>5}  {cnt:>8}  {wins:>8}  {100*wins/cnt:>6.1f}%  {draws:>8}  {100*draws/cnt:>6.1f}%")
        else:
            # Nominal attribute: εμφάνισε ανά τιμή
            vals = sorted(Counter(r[attr] for r in rows).keys())
            lines.append(f"  {'Τιμη':<8}  {'Θεσεις':>8}  {'Win':>8}  {'Win%':>7}  {'Draw':>8}  {'Draw%':>7}")
            for v in vals:
                subset = [r for r in rows if r[attr]==v]
                cnt   = len(subset)
                wins  = sum(1 for r in subset if r['result']=='white')
                draws = cnt - wins
                lines.append(f"  {v:<8}  {cnt:>8}  {wins:>8}  {100*wins/cnt:>6.1f}%  {draws:>8}  {100*draws/cnt:>6.1f}%")

    return lines


# ================================================================
# ΑΝΑΛΥΣΗ ΛΑΘΩΝ ΑΝΑ ATTRIBUTE
# ================================================================

def error_analysis(rows):
    """
    Για κάθε attribute που είναι {Y,N}:
    Βρες τις θέσεις όπου attribute=Y αλλά result=draw
    (αυτές είναι οι "ψευδείς θετικές" - ο αλγόριθμος πιστεύει Win αλλά είναι Draw)
    """
    lines = []
    lines.append("")
    lines.append("=" * 60)
    lines.append("ΑΝΑΛΥΣΗ ΛΑΘΩΝ (attribute=Y αλλα result=Draw)")
    lines.append("=" * 60)

    all_cols = list(rows[0].keys())
    attr_cols = [c for c in all_cols if c != 'result']

    for attr in attr_cols:
        # Μόνο για nominal attributes με τιμή Y
        sample_vals = set(r[attr] for r in rows[:20])
        if 'Y' not in sample_vals:
            continue

        errors = [r for r in rows if r[attr]=='Y' and r['result']=='draw']
        total_y = sum(1 for r in rows if r[attr]=='Y')

        if not errors:
            lines.append(f"\n{attr}=Y: 0 λαθη (τελειο!)")
            continue

        lines.append(f"\n{attr}=Y: {len(errors)} λαθη / {total_y} θεσεις ({100*len(errors)/total_y:.2f}%)")

        # Ανάλυση κοινών χαρακτηριστικών των λαθών
        other_attrs = [c for c in attr_cols if c != attr]
        lines.append("  Κοινα χαρακτηριστικα:")
        for other in other_attrs:
            other_vals = Counter(r[other] for r in errors)
            # Εμφάνισε μόνο αν υπάρχει κυρίαρχη τιμή (>60%)
            for val, cnt in other_vals.most_common(1):
                pct = 100 * cnt / len(errors)
                if pct >= 60:
                    lines.append(f"    {other}={val}: {cnt}/{len(errors)} ({pct:.0f}%)")

    return lines


# ================================================================
# ΑΝΑΛΥΣΗ ΣΥΝΔΥΑΣΜΩΝ (Combination Analysis)
# ================================================================

def combination_analysis(rows):
    """
    Βρες ποιοι συνδυασμοί attributes οδηγούν πάντα σε Win ή πάντα σε Draw.
    Αυτό βοηθάει στο feature engineering.
    """
    lines = []
    lines.append("")
    lines.append("=" * 60)
    lines.append("ΑΝΑΛΥΣΗ ΣΥΝΔΥΑΣΜΩΝ (100% Win ή 100% Draw)")
    lines.append("=" * 60)

    all_cols = list(rows[0].keys())
    nominal_attrs = []
    for c in all_cols:
        if c == 'result': continue
        sample_vals = set(r[c] for r in rows[:20])
        if 'Y' in sample_vals or 'NEAR' in sample_vals:
            nominal_attrs.append(c)

    # Ελέγχουμε ποια attributes όταν Y δίνουν 100% Win
    lines.append("\nAttributes με 100% Win οταν Y:")
    for attr in nominal_attrs:
        subset = [r for r in rows if r[attr]=='Y']
        if not subset: continue
        wins = sum(1 for r in subset if r['result']=='white')
        if wins == len(subset):
            lines.append(f"  {attr}=Y -> 100% Win ({len(subset)} θεσεις)")

    # Ελέγχουμε ποια attributes όταν N δίνουν 100% Draw
    lines.append("\nAttributes με 100% Draw οταν N:")
    for attr in nominal_attrs:
        subset = [r for r in rows if r[attr]=='N']
        if not subset: continue
        draws = sum(1 for r in subset if r['result']=='draw')
        if draws == len(subset):
            lines.append(f"  {attr}=N -> 100% Draw ({len(subset)} θεσεις)")

    return lines


# ================================================================
# ΠΕΡΙΛΗΨΗ
# ================================================================

def summary(rows, filename):
    lines = []
    lines.append("")
    lines.append("=" * 60)
    lines.append("ΠΕΡΙΛΗΨΗ")
    lines.append("=" * 60)

    total = len(rows)
    wins  = sum(1 for r in rows if r['result']=='white')
    draws = total - wins

    all_cols   = list(rows[0].keys())
    attr_count = len(all_cols) - 1  # εκτός του result

    lines.append(f"Αρχειο        : {filename}")
    lines.append(f"Θεσεις        : {total}")
    lines.append(f"Attributes    : {attr_count}")
    lines.append(f"Win           : {wins} ({100*wins/total:.1f}%)")
    lines.append(f"Draw          : {draws} ({100*draws/total:.1f}%)")

    # Βρες attributes με 100% accuracy
    perfect = []
    for attr in [c for c in all_cols if c != 'result']:
        sample = set(r[attr] for r in rows[:20])
        if 'Y' in sample:
            subset = [r for r in rows if r[attr]=='Y']
            if subset:
                wins_y = sum(1 for r in subset if r['result']=='white')
                if wins_y == len(subset):
                    perfect.append(f"{attr}=Y")

    if perfect:
        lines.append(f"100% Win attrs: {', '.join(perfect)}")

    return lines


# ================================================================
# ΒΟΗΘΗΤΙΚΗ ΣΥΝΑΡΤΗΣΗ
# ================================================================

def _is_number(s):
    try:
        int(s)
        return True
    except ValueError:
        return False


# ================================================================
# MAIN
# ================================================================

def main():
    if len(sys.argv) < 2:
        print("Χρηση: python analyze_errors.py <csv_file>")
        print("Παραδειγμα: python analyze_errors.py kpk_wtm_v4_critical.csv")
        sys.exit(1)

    filename = sys.argv[1]
    print(f"Φορτωση: {filename}")

    rows = load_csv(filename)
    print(f"Φορτωθηκαν {len(rows)} θεσεις")

    # Συλλογή όλων των γραμμών εξόδου
    output = []
    output += general_stats(rows)
    output += attribute_analysis(rows)
    output += error_analysis(rows)
    output += combination_analysis(rows)
    output += summary(rows, filename)

    # Εκτύπωση στην οθόνη
    for line in output:
        print(line)

    # Αποθήκευση σε αρχείο
    out_filename = filename.replace('.csv', '_analysis.txt')
    with open(out_filename, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output))
    print(f"\nΑποτελεσματα αποθηκευτηκαν: {out_filename}")


if __name__ == '__main__':
    main()
