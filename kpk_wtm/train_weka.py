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


def build_cmd(weka_jar, weka_class, memory, unpruned, min_obj,
              t_file=None, d_file=None, T_file=None,
              l_file=None, folds=None, pred_file=None):
    cmd = ["java", f"-Xmx{memory}", "-cp", weka_jar, weka_class]

    # J48 και PART υποστηριζουν -U και -M
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
        cmd += ["-classifications",
                f"weka.classifiers.evaluation.output.prediction.CSV "
                f"-file {pred_file} -suppress"]
    return cmd


def run_streaming(cmd, out_file):
    """Streaming output απευθειας στο αρχειο — αποφευγει MemoryError."""
    with open(out_file, 'w', encoding='utf-8') as f:
        process = subprocess.Popen(
            cmd, stdout=f, stderr=subprocess.PIPE,
            text=True, encoding='utf-8', errors='replace'
        )
        _, stderr = process.communicate()
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
          unpruned, min_obj, mode, cv_predictions=False):

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
    model_file   = base + f"_{classifier}.model"
    cv_file      = base + f"_{classifier}_cv_results.txt"
    # CV predictions — για feature engineering iteration
    cv_pred_file = base + f"_{classifier}_cv_predictions.csv"
    # Training Set predictions — για lossless exceptions.bin
    train_pred_file = base + f"_{classifier}_train_predictions.csv"

    print("=" * 60)
    print(f"WEKA {classifier} | mode={mode} | memory={memory}")
    print(f"ARFF: {arff_file}")
    if 'J48' in weka_class or 'PART' in weka_class:
        print(f"Unpruned={unpruned} | MinObj={min_obj}")
    if cv_predictions and mode in ('cv', 'both'):
        print(f"CV Predictions: ΝΑΙ (για feature engineering)")
    print("=" * 60)

    # ----------------------------------------------------------------
    # ΒΗΜΑ 1: Cross-validation
    # ----------------------------------------------------------------
    if mode in ('cv', 'both'):
        step = f"{'1/2' if mode=='both' else '1/1'}"
        pred_note = " + predictions" if cv_predictions else ""
        print(f"\nΒημα {step}: {folds}-fold CV{pred_note}...")
        t0 = time.time()

        cmd = build_cmd(weka_jar, weka_class, memory, unpruned, min_obj,
                        t_file=arff_file, d_file=model_file, folds=folds,
                        pred_file=cv_pred_file if cv_predictions else None)

        retcode, stderr = run_streaming(cmd, cv_file)
        print(f"  Χρονος: {time.time()-t0:.1f}s")

        if retcode != 0:
            print("ERROR:", stderr[-2000:]); sys.exit(1)

        print(f"  CV Results : {cv_file}")
        print(f"  Μοντελο   : {model_file}")
        if cv_predictions:
            print(f"  CV Pred   : {cv_pred_file}")
            print(f"  ΠΡΟΣΟΧΗ: Για exceptions.bin χρησιμοποιησε Training Set predictions!")

        with open(cv_file, 'r', encoding='utf-8', errors='replace') as f:
            print_summary(f.read())

    # ----------------------------------------------------------------
    # ΒΗΜΑ 2: Training Set predictions (για lossless exceptions.bin)
    # ----------------------------------------------------------------
    if mode in ('train', 'both'):
        step = f"{'2/2' if mode=='both' else '1/1'}"
        print(f"\nΒημα {step}: Training Set predictions (για exceptions.bin)...")
        t0 = time.time()

        if mode == 'both' and os.path.exists(model_file):
            cmd = build_cmd(weka_jar, weka_class, memory, unpruned, min_obj,
                            T_file=arff_file, l_file=model_file,
                            pred_file=train_pred_file)
        else:
            cmd = build_cmd(weka_jar, weka_class, memory, unpruned, min_obj,
                            t_file=arff_file, d_file=model_file,
                            T_file=arff_file, pred_file=train_pred_file)

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
    a = p.parse_args()
    train(a.arff_file, a.weka_path, a.memory, a.folds,
          a.classifier, not a.pruned, a.min_obj, a.mode,
          cv_predictions=a.cv_predictions)

if __name__ == '__main__':
    main()
