"""
analyze.py
==========
Βημα 6: Αξιολογηση αποτελεσματων Weka (μετα την εκπαιδευση).

Χρηση:
    python analyze.py <csv> <predictions.csv>

Παραδειγμα:
    python analyze.py csv-arff\\kpk_wtm_v7.csv predictions.csv

Σημειωση:
    Το validation (πριν Weka) γινεται αυτοματα στο add_attributes.py.

Εξοδος:
    kpk_wtm_v7_evaluation.txt  — αναφορα αποτελεσματων
    kpk_wtm_v7_failures.csv    — λανθασμενες θεσεις για Meta-Mining
    results_history.csv        — ιστορικο εκδοσεων

Weka predictions format (Save predictions απο Weka):
    inst, actual, predicted, error, ...attributes...
    1,    1:white, 1:white,  ,      ...
    2,    2:draw,  1:white,  +,     ...
"""

import csv
import sys
import os
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


def load_predictions(filename):
    """
    Φορτωνει το αρχειο predictions του Weka.
    Υποστηριζει CSV και ARFF format.

    ARFF format (Save predictions από Weka):
      @attribute 'predicted result' {white,draw}
      @attribute result {white,draw}
      @data
      ..., draw, draw    ← predicted, actual

    CSV format:
      inst, actual, predicted, error, ...
    """
    ext  = os.path.splitext(filename)[1].lower()
    rows = []

    if ext == '.arff':
        # Διαβαζουμε ARFF — βρισκουμε τα columns απο τα @attribute
        columns = []
        in_data = False
        with open(filename, encoding='utf-8-sig') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('%'):
                    continue
                if line.lower().startswith('@attribute'):
                    # @attribute 'name' type  ή  @attribute name type
                    parts = line.split(None, 2)
                    col = parts[1].strip("'\"")
                    columns.append(col)
                elif line.lower() == '@data':
                    in_data = True
                elif in_data:
                    vals = line.split(',')
                    if len(vals) == len(columns):
                        row = dict(zip(columns, vals))
                        rows.append(row)
    else:
        # CSV format
        with open(filename, newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)

    return rows


def _is_number(s):
    try:
        int(s)
        return True
    except ValueError:
        return False


def get_attr_cols(rows):
    """
    Universal — δουλευει για ολα τα φιναλε χωρις αλλαγες.
    Αφαιρει: Weka metadata + raw squares (endswith Sq).
    """
    if not rows:
        return []
    WEKA_META = {
        'inst#', 'inst', 'actual', 'predicted', 'error',
        'prediction', 'Actual', 'Predicted', 'Error',
        'Prediction', 'result'
    }
    cols = []
    for k in rows[0].keys():
        if k in WEKA_META:
            continue
        if k.endswith('Sq'):   # wKSq, bNSq, wB1Sq κλπ
            continue
        cols.append(k)
    return cols


# ================================================================
# ΒΟΗΘΗΤΙΚΕΣ ΣΥΝΑΡΤΗΣΕΙΣ ΑΝΑΛΥΣΗΣ
# ================================================================

def general_stats(rows):
    total   = len(rows)
    results = Counter(r['result'] for r in rows)

    lines = []
    lines.append("=" * 60)
    lines.append("ΓΕΝΙΚΑ ΣΤΑΤΙΣΤΙΚΑ")
    lines.append("=" * 60)
    lines.append(f"Συνολικες θεσεις : {total}")
    for k, v in sorted(results.items()):
        lines.append(f"  {k:<8}: {v:>7}  ({100*v/total:.2f}%)")
    return lines


def combination_analysis(rows):
    lines = []
    lines.append("")
    lines.append("=" * 60)
    lines.append("100% WIN / 100% DRAW ATTRIBUTES")
    lines.append("=" * 60)

    nominal = []
    for c in get_attr_cols(rows):
        sample = set(r[c] for r in rows[:20])
        if 'Y' in sample or 'NEAR' in sample:
            nominal.append(c)

    lines.append("\nAttributes με 100% Win οταν Y:")
    found = False
    for attr in nominal:
        subset = [r for r in rows if r[attr]=='Y']
        if not subset: continue
        wins = sum(1 for r in subset if r['result']=='white')
        if wins == len(subset):
            lines.append(f"  {attr}=Y -> 100% Win ({len(subset)} θεσεις)")
            found = True
    if not found:
        lines.append("  (κανενα)")

    lines.append("\nAttributes με 100% Draw οταν N:")
    found = False
    for attr in nominal:
        subset = [r for r in rows if r[attr]=='N']
        if not subset: continue
        draws = sum(1 for r in subset if r['result']=='draw')
        if draws == len(subset):
            lines.append(f"  {attr}=N -> 100% Draw ({len(subset)} θεσεις)")
            found = True
    if not found:
        lines.append("  (κανενα)")

    return lines


def symmetry_analysis(rows):
    """
    Ελεγχει αν τα λαθη (attribute=Y αλλα result=Draw)
    ειναι ομοιομορφα κατανεμημενα στη σκακιερα.
    Αν οχι, μπορει να υπαρχει bug στη λογικη mirror.
    """
    lines = []
    lines.append("")
    lines.append("=" * 60)
    lines.append("SYMMETRY ANALYSIS")
    lines.append("=" * 60)

    # Βρες nominal attrs με Y
    nominal = [c for c in get_attr_cols(rows)
               if 'Y' in set(r[c] for r in rows[:20])]

    for attr in nominal:
        errors = [r for r in rows if r[attr]=='Y' and r['result']=='draw']
        if not errors:
            continue

        # Ελεγχος αν εχουμε wPFile στα columns
        if 'wPFile' not in rows[0]:
            continue

        lines.append(f"\n{attr}=Y λαθη ανα wPFile (στηλη πιονιου):")
        by_file = Counter(r['wPFile'] for r in errors)
        total_e = len(errors)
        for file_val in sorted(by_file.keys(), key=lambda x: int(x)):
            cnt = by_file[file_val]
            col_name = 'abcdefgh'[int(file_val)-1]
            lines.append(f"  {col_name}({file_val}): {cnt:>5} ({100*cnt/total_e:.1f}%)")

        # Ελεγχος συμμετριας a vs h, b vs g κλπ
        lines.append("  Συμμετρια (a vs h, b vs g, c vs f, d vs e):")
        for lo, hi in [(1,8),(2,7),(3,6),(4,5)]:
            lo_cnt = by_file.get(str(lo), 0)
            hi_cnt = by_file.get(str(hi), 0)
            diff   = abs(lo_cnt - hi_cnt)
            status = "OK" if diff <= max(2, total_e*0.02) else "ΑΣΥΜΜΕΤΡΟ"
            col_lo = 'abcdefgh'[lo-1]
            col_hi = 'abcdefgh'[hi-1]
            lines.append(f"    {col_lo} vs {col_hi}: {lo_cnt} vs {hi_cnt} [{status}]")

    return lines


# ================================================================
# EVALUATION (μετα Weka)
# ================================================================

def parse_weka_class(val):
    """
    Το Weka εξαγει κλασεις ως '1:white' η '2:draw'.
    Επιστρεφει μονο το ονομα: 'white' η 'draw'.
    """
    return val.split(':')[-1].strip() if ':' in val else val.strip()


def evaluation_stats(rows, preds, csv_filename):
    """
    Συγκρινει τα actual αποτελεσματα με τις προβλεψεις του Weka.
    Υποστηριζει ARFF format (predicted result + result)
    και CSV format (actual + predicted).
    """
    lines = []
    lines.append("")
    lines.append("=" * 60)
    lines.append("EVALUATION — ΑΠΟΤΕΛΕΣΜΑΤΑ WEKA")
    lines.append("=" * 60)

    # Αναγνωριση format: ARFF εχει 'predicted' και 'result'
    combined = []
    if preds and 'predicted' in preds[0] and 'result' in preds[0]:
        # ARFF format απο Weka "Save predictions"
        for pred in preds:
            predicted = pred.get('predicted', '').strip()
            actual    = pred.get('result', '').strip()
            combined.append({
                'actual':    actual,
                'predicted': predicted,
                'row':       pred
            })
    else:
        # CSV format: inst#, actual, predicted, error, prediction
        #
        # ΣΗΜΑΝΤΙΚΟ: Το Weka CV επιστρεφει inst# ανα fold (1..N/10)
        # οχι globally — δεν μπορει να χρησιμοποιηθει για matching.
        #
        # Λυση: Χτιζουμε index απο το actual result + position
        # Για CV: χρησιμοποιουμε sequential matching (rows[i])
        # Για Training Set: το inst# ειναι global (1..N) — χρησιμοποιουμε inst#
        #
        # Ανιχνευση αν ειναι Training Set (inst# max == len(rows))
        # Ανιχνευση training set: το inst# ειναι sequential 1..N
        # και το max ισουται με το συνολο των θεσεων
        try:
            inst_vals = [int(str(p.get('inst#', p.get('inst', '0'))).strip())
                         for p in preds]
            max_inst = max(inst_vals) if inst_vals else 0
            # Training set: inst# παει απο 1 εως len(rows) ακριβως
            is_training_set = (max_inst == len(rows) and len(preds) == len(rows))
        except:
            is_training_set = False

        for i, pred in enumerate(preds):
            actual    = parse_weka_class(pred.get('actual', pred.get('Actual', '')))
            predicted = parse_weka_class(pred.get('predicted', pred.get('Predicted', '')))

            if is_training_set:
                # Training Set: inst# ειναι global 1-indexed
                inst_str = pred.get('inst#', pred.get('inst', ''))
                try:
                    idx = int(str(inst_str).strip()) - 1
                    row = rows[idx] if 0 <= idx < len(rows) else {}
                except:
                    row = rows[i] if i < len(rows) else {}
            else:
                # CV: sequential matching (καλυτερη εκτιμηση)
                row = rows[i] if i < len(rows) else {}

            combined.append({
                'actual':    actual,
                'predicted': predicted,
                'row':       row
            })

    total    = len(combined)
    correct  = sum(1 for c in combined if c['actual']==c['predicted'])
    wrong    = total - correct
    accuracy = 100.0 * correct / total if total > 0 else 0

    lines.append(f"Συνολικες θεσεις : {total}")
    lines.append(f"Σωστες           : {correct} ({accuracy:.4f}%)")
    lines.append(f"Λαθος            : {wrong}   ({100-accuracy:.4f}%)")

    # Confusion matrix
    lines.append("\nConfusion Matrix:")
    classes = sorted(set(c['actual'] for c in combined))
    header  = f"  {'':>8}" + "".join(f"  {c:>8}" for c in classes)
    lines.append(header)
    for actual_cls in classes:
        row_str = f"  {actual_cls:>8}"
        for pred_cls in classes:
            cnt = sum(1 for c in combined
                      if c['actual']==actual_cls and c['predicted']==pred_cls)
            row_str += f"  {cnt:>8}"
        lines.append(row_str)

    # Precision / Recall / F1 ανα κλαση
    # Κρισιμο για imbalanced dataset (76.5% Win / 23.5% Draw)
    lines.append("")
    lines.append(f"  {'Κλαση':<8}  {'TP':>7}  {'FP':>7}  {'FN':>7}  {'Precision':>10}  {'Recall':>8}  {'F1':>8}")
    lines.append("  " + "-" * 65)
    for cls in classes:
        tp = sum(1 for c in combined if c['actual']==cls and c['predicted']==cls)
        fp = sum(1 for c in combined if c['actual']!=cls and c['predicted']==cls)
        fn = sum(1 for c in combined if c['actual']==cls and c['predicted']!=cls)
        precision = tp/(tp+fp) if (tp+fp) > 0 else 0.0
        recall    = tp/(tp+fn) if (tp+fn) > 0 else 0.0
        f1        = 2*precision*recall/(precision+recall) if (precision+recall) > 0 else 0.0
        lines.append(f"  {cls:<8}  {tp:>7}  {fp:>7}  {fn:>7}  {precision:>10.4f}  {recall:>8.4f}  {f1:>8.4f}")

    return lines, combined


def failures_analysis(combined):
    """
    Αναλυει τις λανθασμενες θεσεις.
    """
    lines = []
    lines.append("")
    lines.append("=" * 60)
    lines.append("ΑΝΑΛΥΣΗ ΛΑΘΩΝ (Weka misclassified)")
    lines.append("=" * 60)

    failures = [c for c in combined if c['actual'] != c['predicted']]
    if not failures:
        lines.append("Κανενα λαθος!")
        return lines

    lines.append(f"Συνολο λαθων: {len(failures)}")

    # Κατανομη λαθων ανα τυπο
    lines.append("\nΤυπος λαθους:")
    by_type = Counter(f"{c['actual']}→{c['predicted']}" for c in failures)
    for t, cnt in by_type.most_common():
        lines.append(f"  {t}: {cnt} ({100*cnt/len(failures):.1f}%)")

    # Κοινα χαρακτηριστικα των λαθων
    if failures and failures[0]['row']:
        attr_cols = get_attr_cols([c['row'] for c in failures])
        nominal   = [a for a in attr_cols
                     if 'Y' in set(c['row'].get(a,'') for c in failures[:20])]

        if nominal:
            lines.append("\nΚοινα attributes στα λαθη:")
            for attr in nominal:
                cnt_y = sum(1 for c in failures if c['row'].get(attr)=='Y')
                if cnt_y > 0:
                    pct = 100*cnt_y/len(failures)
                    if pct >= 50:
                        lines.append(f"  {attr}=Y: {cnt_y}/{len(failures)} ({pct:.0f}%)")

    return lines


def export_failures(combined, csv_filename):
    """
    Εξαγει τις λανθασμενες θεσεις σε CSV για Meta-Mining και compress_exceptions.py.
    """
    failures = [c for c in combined if c['actual'] != c['predicted']]
    if not failures:
        return None

    base     = os.path.splitext(csv_filename)[0]
    out_file = base + '_failures.csv'

    # Βρες το πρωτο non-empty row για τα fieldnames
    sample_row = next((c['row'] for c in failures if c['row']), {})
    if not sample_row:
        print("  [WARN] Failures rows ειναι αδεια — το failures.csv δεν θα εχει attributes")
        return None

    fieldnames = list(sample_row.keys()) + ['predicted']

    with open(out_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for c in failures:
            if not c['row']:
                continue  # παραλειπε αδεια rows
            row = dict(c['row'])
            row['predicted'] = c['predicted']
            writer.writerow(row)

    return out_file


def update_history(csv_filename, accuracy, wrong, attr_count, leaf_count=None):
    """
    Κρατα ιστορικο αποτελεσματων ανα εκδοση.
    """
    # Αποθηκευση παντα στον φακελο csv-arff του CSV
    csv_dir      = os.path.dirname(os.path.abspath(csv_filename))
    history_file = os.path.join(csv_dir, 'results_history.csv')
    exists       = os.path.exists(history_file)

    version = os.path.splitext(os.path.basename(csv_filename))[0]

    with open(history_file, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not exists:
            writer.writerow(['version','accuracy','wrong','attributes','leaves'])
        writer.writerow([version, f"{accuracy:.4f}", wrong, attr_count,
                         leaf_count if leaf_count else 'N/A'])

    return history_file


def information_gain_analysis(rows, combined):
    """
    Υπολογιζει Information Gain για καθε attribute ως προς:
    1. Το πραγματικο result (ολο το dataset)
    2. Τα failures (ποια attributes διαχωριζουν τα λαθη)

    Βασιζεται στη μεθοδολογια του Θανου (InfoGainAttributeEval).
    Τυπος: H(S) - Σ(|Sv|/|S|) * H(Sv)
    """
    import math

    def entropy(rows):
        total = len(rows)
        if total == 0:
            return 0.0
        counts = Counter(r['result'] for r in rows)
        h = 0.0
        for c in counts.values():
            p = c / total
            if p > 0:
                h -= p * math.log2(p)
        return h

    def split_info(rows, attr):
        total  = len(rows)
        if total == 0:
            return 0.0
        groups = {}
        for r in rows:
            v = r.get(attr, '')
            groups.setdefault(v, []).append(r)
        si = 0.0
        for g in groups.values():
            p = len(g) / total
            if p > 0:
                si -= p * math.log2(p)
        return si

    def info_gain(rows, attr):
        total   = len(rows)
        h_total = entropy(rows)
        groups  = {}
        for r in rows:
            v = r.get(attr, '')
            groups.setdefault(v, []).append(r)
        weighted = sum((len(g)/total) * entropy(g) for g in groups.values())
        return h_total - weighted

    def gain_ratio(rows, attr):
        ig = info_gain(rows, attr)
        si = split_info(rows, attr)
        return ig / si if si > 0 else 0.0

    lines = []
    lines.append("")
    lines.append("=" * 60)
    lines.append("INFORMATION GAIN ΑΝΑΛΥΣΗ")
    lines.append("=" * 60)

    attr_cols = get_attr_cols(rows)
    failures  = [c['row'] for c in combined if c['actual'] != c['predicted']]

    # Υπολογισμος IG και GainRatio για ολο το dataset
    gains_all = []
    for attr in attr_cols:
        ig = info_gain(rows, attr)
        gr = gain_ratio(rows, attr)
        gains_all.append((attr, ig, gr))
    gains_all.sort(key=lambda x: x[1], reverse=True)

    lines.append("")
    lines.append("Ranking attributes (InfoGain + GainRatio vs result):")
    lines.append(f"  {'Attribute':<25} {'InfoGain':>9}  {'GainRatio':>9}  {'Αξιολογηση'}")
    lines.append("  " + "-" * 65)
    for attr, ig, gr in gains_all:
        if ig > 0.1:
            rating = "ΥΨΗΛΟ ★★★"
        elif ig > 0.01:
            rating = "ΜΕΤΡΙΟ ★★"
        elif ig > 0.001:
            rating = "ΧΑΜΗΛΟ ★"
        else:
            rating = "ΑΣΗΜΑΝΤΟ"
        lines.append(f"  {attr:<25} {ig:>9.6f}  {gr:>9.6f}  {rating}")

    # IG στα failures — ποια attributes διαχωριζουν τα λαθη
    if failures:
        lines.append("")
        lines.append(f"Ranking attributes στα {len(failures)} failures:")
        lines.append(f"  {'Attribute':<25} {'IG failures':>12}  {'IG overall':>10}  {'Διαφορα'}")
        lines.append("  " + "-" * 65)

        gains_fail = []
        ig_dict = dict((a, ig) for a, ig, gr in gains_all)
        gr_dict = dict((a, gr) for a, ig, gr in gains_all)
        for attr in attr_cols:
            ig_f = info_gain(failures, attr)
            gr_f = gain_ratio(failures, attr)
            gains_fail.append((attr, ig_f, gr_f, ig_dict.get(attr, 0)))
        gains_fail.sort(key=lambda x: x[1], reverse=True)

        lines.append(f"  {'Attribute':<25} {'IG fail':>8}  {'GR fail':>8}  {'IG all':>8}  {'Διαφορα'}")
        lines.append("  " + "-" * 70)
        for attr, ig_f, gr_f, ig_a in gains_fail[:10]:
            diff   = ig_f - ig_a
            marker = " ←" if diff > 0.01 else ""
            lines.append(f"  {attr:<25} {ig_f:>8.5f}  {gr_f:>8.5f}  {ig_a:>8.5f}  {diff:+.5f}{marker}")

        lines.append("")
        lines.append("← = Attribute πιο σημαντικο στα failures απ οσο στο συνολο")
        lines.append("  → Υποψηφιο για νεο/βελτιωμενο attribute στο v_next")

    return lines


def evaluation_summary(csv_filename, accuracy, wrong, combined):
    lines = []
    lines.append("")
    lines.append("=" * 60)
    lines.append("EVALUATION ΠΕΡΙΛΗΨΗ")
    lines.append("=" * 60)

    total = len(combined)
    lines.append(f"Αρχειο   : {csv_filename}")
    lines.append(f"Accuracy : {accuracy:.4f}%")
    lines.append(f"Λαθη     : {wrong}/{total}")
    lines.append("")

    if accuracy >= 99.9:
        lines.append("Αποτελεσμα: ΕΞΑΙΡΕΤΙΚΟ (>=99.9%)")
    elif accuracy >= 99.0:
        lines.append("Αποτελεσμα: ΠΟΛΥ ΚΑΛΟ (>=99.0%)")
    elif accuracy >= 98.0:
        lines.append("Αποτελεσμα: ΚΑΛΟ (>=98.0%)")
    else:
        lines.append("Αποτελεσμα: Χρειαζεται βελτιωση (<98.0%)")
        lines.append("Επομενο βημα: Βελτιωση attributes στο add_attributes.py")

    return lines


# ================================================================
# MAIN
# ================================================================

def main():
    if len(sys.argv) < 3:
        print("Χρηση:")
        print("  python analyze.py <csv> <predictions.csv>")
        print()
        print("Παραδειγμα:")
        print("  python analyze.py csv-arff\\kpk_wtm_v7.csv predictions.csv")
        print()
        print("Σημειωση:")
        print("  Το validation (πριν Weka) γινεται αυτοματα στο add_attributes.py")
        sys.exit(1)

    csv_file  = sys.argv[1]
    pred_file = sys.argv[2]

    if not os.path.exists(csv_file):
        print(f"ERROR: Δεν βρεθηκε: {csv_file}")
        sys.exit(1)

    if not os.path.exists(pred_file):
        print(f"ERROR: Δεν βρεθηκε: {pred_file}")
        sys.exit(1)

    print(f"Φορτωση : {csv_file}")
    rows = load_csv(csv_file)
    print(f"Θεσεις  : {len(rows)}")

    print(f"Predictions: {pred_file}")
    preds = load_predictions(pred_file)
    print(f"Predictions: {len(preds)}")

    print("\n=== EVALUATION (μετα Weka) ===\n")

    output = []
    output += general_stats(rows)

    eval_lines, combined = evaluation_stats(rows, preds, csv_file)
    output += eval_lines

    output += failures_analysis(combined)
    output += information_gain_analysis(rows, combined)
    output += combination_analysis(rows)
    output += symmetry_analysis(rows)

    total    = len(combined)
    correct  = sum(1 for c in combined if c['actual']==c['predicted'])
    wrong    = total - correct
    accuracy = 100.0 * correct / total if total > 0 else 0
    attr_cnt = len(get_attr_cols(rows))

    output += evaluation_summary(csv_file, accuracy, wrong, combined)

    for line in output:
        print(line)

    # Αποθηκευση evaluation report
    eval_file = os.path.splitext(os.path.basename(csv_file))[0] + '_evaluation.txt'
    with open(eval_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output))
    print(f"\nEvaluation report: {eval_file}")

    # Εξαγωγη failures CSV
    failures_file = export_failures(combined, csv_file)
    if failures_file:
        print(f"Failures CSV   : {failures_file}")
        print(f"  → Φορτωσε στο Weka για Meta-Mining")

    # Ενημερωση ιστορικου
    history_file = update_history(csv_file, accuracy, wrong, attr_cnt)
    print(f"Ιστορικο       : {history_file}")


if __name__ == '__main__':
    main()
