"""
train_weka.py — Αυτοματοποιημενη εκπαιδευση μεσω Weka CLI

Χρηση:
    # Default: CV + Training Set predictions
    python train_weka.py csv-arff\kbbk_btm_v2.arff --memory 5g

    # Feature engineering iteration: CV με predictions
    python train_weka.py csv-arff\kbbk_btm_v2.arff --mode cv --cv-predictions

    # Μονο Training Set (για exceptions.bin)
    python train_weka.py csv-arff\kbbk_btm_v2.arff --mode train --memory 5g

    # JRip σύγκριση
    python train_weka.py csv-arff\kpk_wtm_v7.arff --classifier JRip

Modes:
    cv    = μονο 10-fold CV
    train = μονο Training Set (για exceptions.bin)
    both  = και τα δυο (default)

--cv-predictions:
    Εξαγει predictions και κατα το CV (για analyze.py + feature engineering)
    Χρησιμο οταν θελεις να βελτιωσεις τα attributes χωρις να τρεχεις 2 φορες
    ΠΡΟΣΟΧΗ: Για lossless exceptions.bin χρησιμοποιησε παντα Training Set predictions
"""

import subprocess
import sys
import os
import time
import argparse

# ================================================================
WEKA_JAR = os.environ.get('WEKA_PATH',
    r"C:\Program Files\Weka-3-8-6\weka.jar")

DEFAULT_MEMORY = "5g"
DEFAULT_FOLDS  = 10

CLASSIFIERS = {
    'J48':  'weka.classifiers.trees.J48',
    'JRip': 'weka.classifiers.rules.JRip',
    'PART': 'weka.classifiers.rules.PART',
}
# ================================================================


def get_attr_indices(arff_file, attr_names_to_remove):
    """Διαβαζει το ARFF και επιστρεφει τα 1-based indices για Ablation Study."""
    if not attr_names_to_remove:
        return []
    attr_list = []
    with open(arff_file, encoding='utf-8') as f:
        for line in f:
            if line.strip().lower().startswith('@attribute'):
                name = line.strip().split()[1].strip("'\"")
                attr_list.append(name)
    names_lower = [n.strip().lower() for n in attr_names_to_remove.split(',')]
    indices = [str(i) for i, name in enumerate(attr_list[:-1], start=1)
               if name.lower() in names_lower]
    not_found = [n for n in names_lower if n not in [a.lower() for a in attr_list]]
    if not_found:
        print(f"  [WARN] Ablation: Τα attributes {not_found} δεν βρεθηκαν στο ARFF!")
    return indices

def build_cmd(weka_jar, weka_class, memory, unpruned, min_obj,
              t_file=None, d_file=None, T_file=None,
              l_file=None, folds=None, pred_file=None, remove_indices=None):

    # Ablation Study (FilteredClassifier)
    if remove_indices:
        cmd = ["java", f"-Xmx{memory}", "-cp", weka_jar, "weka.classifiers.meta.FilteredClassifier"]
        cmd += ["-F", f"weka.filters.unsupervised.attribute.Remove -R {','.join(remove_indices)}"]
        cmd += ["-W", weka_class, "--"]
    else:
        cmd = ["java", f"-Xmx{memory}", "-cp", weka_jar, weka_class]

    if 'J48' in weka_class or 'PART' in weka_class:
        if unpruned:
            cmd += ["-U"]
        cmd += ["-M", str(min_obj)]

    if t_file:  cmd += ["-t", t_file]
    if d_file:  cmd += ["-d", d_file]
    if l_file:  cmd += ["-l", l_file]
    if folds:   cmd += ["-x", str(folds)]
    if T_file:  cmd += ["-T", T_file]
    if pred_file:
        safe_path = pred_file.replace('\\', '/')
        cmd += ["-classifications",
                f"weka.classifiers.evaluation.output.prediction.CSV -file {safe_path} -suppress"]
    return cmd


def run_streaming(cmd, out_file):
    """
    Streaming output απευθειας στο αρχειο — αποφευγει MemoryError.
    Το Weka γραφει το summary στο stdout, τα errors στο stderr.
    Καταγραφουμε και τα δυο στο αρχειο.
    """
    with open(out_file, 'w', encoding='utf-8') as f:
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding='utf-8', errors='replace'
        )
        for line in process.stdout:
            f.write(line)
        process.wait()
        stderr = ""
    return process.returncode, stderr


def run_capture(cmd):
    """Capture output στη μνήμη (για μικρα αποτελεσματα)."""
    return subprocess.run(
        cmd, capture_output=True,
        text=True, encoding='utf-8', errors='replace'
    )


def print_summary(output):
    """Εκτυπωνει summary απο Weka output."""
    lines  = output.split('\n')
    active = False
    extra  = 0
    for line in lines:
        if '=== Summary ===' in line or 'Correctly Classified' in line:
            active = True
        if active:
            print(f"  {line}")
        if active and '=== Confusion Matrix ===' in line:
            extra = 5
            continue
        if extra > 0:
            print(f"  {line}")
            extra -= 1
            if extra == 0:
                break


def train(arff_file, weka_jar, memory, folds, classifier,
          unpruned, min_obj, mode, cv_predictions=False, remove_attrs=''):

    # Absolute paths
    arff_file = os.path.abspath(arff_file)

    if not os.path.exists(arff_file):
        print(f"ERROR: {arff_file} δεν βρεθηκε"); sys.exit(1)
    if not os.path.exists(weka_jar):
        print(f"ERROR: {weka_jar} δεν βρεθηκε")
        print("  Χρησιμοποιησε --weka-path ή ορισε WEKA_PATH env variable")
        sys.exit(1)
    if classifier not in CLASSIFIERS:
        print(f"ERROR: {classifier} αγνωστος. Διαθεσιμοι: {list(CLASSIFIERS.keys())}")
        sys.exit(1)

    weka_class   = CLASSIFIERS[classifier]
    base         = os.path.splitext(arff_file)[0]

    # Ablation setup
    remove_indices  = get_attr_indices(arff_file, remove_attrs)
    ablation_suffix = "_ablation" if remove_indices else ""

    model_file      = base + f"_{classifier}{ablation_suffix}.model"
    cv_file         = base + f"_{classifier}{ablation_suffix}_cv_results.txt"
    cv_pred_file    = base + f"_{classifier}{ablation_suffix}_cv_predictions.csv"
    train_pred_file = base + f"_{classifier}{ablation_suffix}_train_predictions.csv"

    print("=" * 60)
    print(f"WEKA {classifier} | mode={mode} | memory={memory}")
    print(f"ARFF: {arff_file}")
    if 'J48' in weka_class or 'PART' in weka_class:
        print(f"Unpruned={unpruned} | MinObj={min_obj}")
    if remove_indices:
        print(f"ABLATION MODE: Αφαιρουνται: {remove_attrs} (indices: {','.join(remove_indices)})")
    if cv_predictions and mode in ('cv', 'both'):
        print(f"CV Predictions: ΝΑΙ (για feature engineering)")
    print("=" * 60)

    # ----------------------------------------------------------------
    # ΒΗΜΑ 1: Cross-validation
    # ----------------------------------------------------------------
    if mode in ('cv', 'both'):
        step = f"{'1/2' if mode=='both' else '1/1'}"
        print(f"\nΒημα {step}: {folds}-fold CV...")
        t0 = time.time()

        # Κληση 1: CV για summary (χωρις -classifications)
        cmd_summary = build_cmd(weka_jar, weka_class, memory, unpruned, min_obj,
                                t_file=arff_file, d_file=model_file, folds=folds,
                                remove_indices=remove_indices)
        retcode, stderr = run_streaming(cmd_summary, cv_file)
        print(f"  Χρονος summary: {time.time()-t0:.1f}s")

        if retcode != 0:
            print("ERROR:", stderr[-2000:]); sys.exit(1)

        print(f"  CV Results : {cv_file}")
        print(f"  Μοντελο   : {model_file}")

        with open(cv_file, 'r', encoding='utf-8', errors='replace') as f:
            print_summary(f.read())

        # Κληση 2: CV για predictions (αν ζητηθει)
        if cv_predictions:
            print(f"  Εξαγωγη CV predictions...")
            t1 = time.time()
            cmd_pred = build_cmd(weka_jar, weka_class, memory, unpruned, min_obj,
                                 t_file=arff_file, folds=folds,
                                 pred_file=cv_pred_file, remove_indices=remove_indices)
            r = run_capture(cmd_pred)
            print(f"  Χρονος predictions: {time.time()-t1:.1f}s")
            if r.returncode != 0:
                print("  WARN:", r.stderr[-500:])
            else:
                print(f"  CV Pred   : {cv_pred_file}")
                print(f"  ΠΡΟΣΟΧΗ: Για exceptions.bin χρησιμοποιησε Training Set predictions!")

    # ----------------------------------------------------------------
    # ΒΗΜΑ 2: Training Set predictions (για lossless exceptions.bin)
    # ----------------------------------------------------------------
    if mode in ('train', 'both'):
        step = f"{'2/2' if mode=='both' else '1/1'}"
        print(f"\nΒημα {step}: Training Set predictions (για exceptions.bin)...")
        t0 = time.time()

        # One-shot: train & evaluate στο ιδιο dataset — ασφαλες για FilteredClassifier
        cmd = build_cmd(weka_jar, weka_class, memory, unpruned, min_obj,
                        t_file=arff_file, d_file=model_file,
                        T_file=arff_file, pred_file=train_pred_file,
                        remove_indices=remove_indices)

        r = run_capture(cmd)
        print(f"  Χρονος: {time.time()-t0:.1f}s")

        if r.returncode != 0:
            print("  WARN:", r.stderr[-500:])
        else:
            print(f"  Train Pred: {train_pred_file}")

        # Σημειωση: os.remove(model_file) αν δεν χρειαζεται

    # ----------------------------------------------------------------
    # ΣΥΝΟΨΗ
    # ----------------------------------------------------------------
    print("\n" + "=" * 60)
    csv_file = arff_file.replace('.arff', '.csv')

    if cv_predictions and mode in ('cv', 'both'):
        print(f"Για feature engineering (analyze):")
        print(f"  python analyze.py {csv_file} {cv_pred_file}")

    if mode in ('train', 'both'):
        print(f"Για exceptions.bin (analyze + compress):")
        print(f"  python analyze.py {csv_file} {train_pred_file}")
        print(f"  python compress_exceptions.py [failures_csv]")
    print("=" * 60)


def main():
    p = argparse.ArgumentParser(
        description='Αυτοματοποιημενη εκπαιδευση ταξινομητη μεσω Weka CLI')
    p.add_argument('arff_file')
    p.add_argument('--weka-path',  default=WEKA_JAR)
    p.add_argument('--memory',     default=DEFAULT_MEMORY)
    p.add_argument('--folds',      type=int, default=DEFAULT_FOLDS)
    p.add_argument('--classifier', default='J48', choices=list(CLASSIFIERS.keys()))
    p.add_argument('--pruned',     action='store_true')
    p.add_argument('--min-obj',    type=int, default=1)
    p.add_argument('--mode',       default='both',
                   choices=['cv', 'train', 'both'])
    p.add_argument('--cv-predictions', action='store_true',
                   help='Εξαγε predictions και κατα το CV (για feature engineering iteration)')
    p.add_argument('--remove-attrs', default='',
                   help='Ablation: comma-separated ονοματα attributes (π.χ. sameColor,bK_on_edge)')
    a = p.parse_args()
    train(a.arff_file, a.weka_path, a.memory, a.folds,
          a.classifier, not a.pruned, a.min_obj, a.mode,
          cv_predictions=a.cv_predictions, remove_attrs=a.remove_attrs)

if __name__ == '__main__':
    main()
