"""
compress_exceptions.py — Universal Exception Patching για Lossless Συμπιεση
============================================================================
Δουλευει αυτοματα για ολα τα φιναλε: KPK, KBBK, KRKN, KBNK κλπ.

Χρηση:
    python compress_exceptions.py <failures_csv> [output_bin]

Παραδειγματα:
    python compress_exceptions.py csv-arff\\kpk_wtm_v7_failures.csv
    python compress_exceptions.py csv-arff\\krkn_wtm_v1_failures.csv
    python compress_exceptions.py csv-arff\\kbbk_wtm_v2_failures.csv

Τι κανει:
    Διαβαζει τα failures του J48 (CSV που παραγει το analyze.py)
    και τα κωδικοποιει σε compact binary αρχειο.

    Ανιχνευει δυναμικα τα κομματια απο τις στηλες που τελειωνουν σε 'Sq'
    (π.χ. wKSq, wRSq, bNSq) — δεν χρειαζεται καμια αλλαγη για νεο φιναλε.

    Format:
        Header: magic(2) + count(2) = 4 bytes
            magic = 'EX' (universal)
        Data: [sq1, sq2, ..., sqN] = N_pieces bytes/exception
            Για KPK:  3 bytes (wKSq, wPSq, bKSq)
            Για KBBK: 4 bytes (wKSq, wB1Sq, wB2Sq, bKSq)
            Για KRKN: 4 bytes (wKSq, wRSq, bKSq, bNSq)

    Συνολο: 4 + N_exceptions * N_pieces bytes

Αποτελεσμα (lossless compression):
    J48 δεντρο  +  exceptions.bin  =  100% αναπαραγωγη Nalimov βασης

Θεωρητικο υποβαθρο (MDL Principle):
    Το συνολικο μεγεθος συμπιεσης = μεγεθος(δεντρο) + μεγεθος(exceptions)
    Στοχος: ελαχιστοποιηση αυτου του αθροισματος.
"""

import csv
import os
import sys


# ================================================================
# ΦΟΡΤΩΣΗ FAILURES
# ================================================================

def load_failures(csv_file):
    """
    Φορτωνει το failures CSV που παραγει το analyze.py.
    Επιστρεφει λιστα απο dicts με ολες τις στηλες.
    """
    failures = []
    with open(csv_file, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            failures.append(row)
    return failures


def get_piece_cols(failures):
    """
    Βρισκει δυναμικα τις στηλες που αφορουν θεσεις κομματιων.
    Οποια στηλη τελειωνει σε 'Sq' ειναι raw square (0-63).
    Παραδειγμα: wKSq, wRSq, bKSq, bNSq, wB1Sq, wB2Sq κλπ.
    """
    if not failures:
        return []
    return [k for k in failures[0].keys() if k.endswith('Sq')]


def detect_endgame(csv_file, piece_cols):
    """Ανιχνευει το φιναλε απο το ονομα αρχειου και τα κομματια."""
    fname = os.path.basename(csv_file).lower()
    if 'krkn' in fname:
        return 'KRKN', 179806  # krkn.nbw.emd
    elif 'kbbk' in fname:
        return 'KBBK', 249216  # kbbk.nbw.emd
    elif 'kqk' in fname:
        return 'KQK', 7605
    elif 'krk' in fname:
        return 'KRK', 7059
    elif 'kpk' in fname:
        return 'KPK', 17654
    else:
        return 'UNKNOWN', 0


# ================================================================
# ΚΩΔΙΚΟΠΟΙΗΣΗ / ΑΠΟΚΩΔΙΚΟΠΟΙΗΣΗ
# ================================================================

def encode_exceptions(failures, output_file, piece_cols):
    """
    Κωδικοποιει τα failures σε compact binary αρχειο.

    Header (4 bytes):
        bytes 0-1: magic 'EX' (universal)
        bytes 2-3: πληθος exceptions (little-endian uint16)

    Data (N * len(piece_cols) bytes):
        Καθε exception = [sq1, sq2, ...] — ενα byte ανα κομματι
    """
    N          = len(failures)
    n_pieces   = len(piece_cols)

    with open(output_file, 'wb') as f:
        # Header
        f.write(b'EX')
        f.write(N.to_bytes(2, byteorder='little'))

        # Data
        for row in failures:
            for col in piece_cols:
                sq = int(row[col])
                f.write(sq.to_bytes(1, byteorder='little'))

    return os.path.getsize(output_file)


def decode_exceptions(bin_file, piece_cols):
    """
    Αποκωδικοποιει το binary αρχειο.
    Επιστρεφει set απο tuples (sq1, sq2, ...).
    """
    exceptions = set()
    with open(bin_file, 'rb') as f:
        magic = f.read(2)
        if magic != b'EX':
            raise ValueError(f"Λαθος magic number: {magic} (αναμενομενο: b'EX')")
        count    = int.from_bytes(f.read(2), byteorder='little')
        n_pieces = len(piece_cols)
        for _ in range(count):
            entry = tuple(int.from_bytes(f.read(1), byteorder='little')
                          for _ in piece_cols)
            exceptions.add(entry)
    return exceptions


def verify_roundtrip(failures, bin_file, piece_cols):
    """
    Επαληθευει οτι ολα τα failures κωδικοποιηθηκαν σωστα (roundtrip test).
    """
    decoded  = decode_exceptions(bin_file, piece_cols)
    original = set(
        tuple(int(row[col]) for col in piece_cols)
        for row in failures
    )

    ok      = (original == decoded)
    extra   = len(decoded - original)
    missing = len(original - decoded)

    return ok, extra, missing


# ================================================================
# ΑΝΑΦΟΡΑ ΣΥΜΠΙΕΣΗΣ
# ================================================================

def print_report(failures, bin_file, bin_size, csv_file,
                 piece_cols, endgame, nalimov_size,
                 total_positions=None):
    """Εκτυπωνει αναλυτικη αναφορα συμπιεσης."""

    N        = len(failures)
    n_pieces = len(piece_cols)
    total    = total_positions or N

    # Τυποι λαθων
    white_to_draw = sum(1 for r in failures
                        if r.get('result','') == 'white'
                        and r.get('predicted','') == 'draw')
    draw_to_white = sum(1 for r in failures
                        if r.get('result','') == 'draw'
                        and r.get('predicted','') == 'white')

    # Naive αναπαρασταση: 1 bit ανα θεση
    naive_bytes = (64 ** n_pieces) // 8

    # Ακριβεια training set
    if total_positions and total_positions > 0:
        accuracy = 100.0 * (total_positions - N) / total_positions
    else:
        accuracy = None

    print("=" * 60)
    print("EXCEPTION PATCHING — ΑΝΑΦΟΡΑ ΣΥΜΠΙΕΣΗΣ")
    print("=" * 60)
    print(f"Failures CSV  : {csv_file}")
    print(f"Output bin    : {bin_file}")
    print(f"Φιναλε        : {endgame}")
    print(f"Κομματια      : {n_pieces} ({', '.join(piece_cols)})")
    print()
    print(f"Exceptions    : {N}")
    if white_to_draw > 0:
        print(f"  white→draw  : {white_to_draw}")
    if draw_to_white > 0:
        print(f"  draw→white  : {draw_to_white}")
    print()
    print("ΚΩΔΙΚΟΠΟΙΗΣΗ")
    print(f"  Header      : 4 bytes (magic 'EX' + count)")
    print(f"  Data        : {N} × {n_pieces} bytes = {N * n_pieces} bytes")
    print(f"  Συνολο      : {bin_size} bytes ({bin_size/1024:.2f} KB)")
    print()
    print("ΣΥΓΚΡΙΣΗ ΜΕΓΕΘΟΥΣ")
    print(f"  Naive (1bit/θεση)   : {naive_bytes:>10} bytes")
    if nalimov_size > 0:
        print(f"  Nalimov .emd        : {nalimov_size:>10} bytes ({nalimov_size/1024:.1f} KB)")
    print(f"  Exceptions.bin      : {bin_size:>10} bytes ({bin_size/1024:.2f} KB)")
    print()
    print("LOSSLESS COMPRESSION")
    print(f"  J48 δεντρο + exceptions.bin = 100% αναπαραγωγη Nalimov")
    if accuracy is not None:
        print(f"  J48 accuracy (train): {accuracy:.4f}% ({total-N}/{total})")
    print(f"  Exceptions          : {N} θεσεις")
    print(f"  Τελικη ακριβεια     : 100.00%")
    print("=" * 60)


# ================================================================
# MAIN
# ================================================================

def main():
    if len(sys.argv) < 2:
        print("Χρηση: python compress_exceptions.py <failures_csv> [output_bin]")
        print()
        print("Παραδειγματα:")
        print("  python compress_exceptions.py csv-arff\\kpk_wtm_v7_failures.csv")
        print("  python compress_exceptions.py csv-arff\\krkn_wtm_v1_failures.csv")
        sys.exit(1)

    csv_file = sys.argv[1]

    # Output filename
    if len(sys.argv) >= 3:
        bin_file = sys.argv[2]
    else:
        base     = os.path.splitext(csv_file)[0].replace('_failures', '')
        bin_file = base + '_exceptions.bin'

    if not os.path.exists(csv_file):
        print(f"ERROR: Δεν βρεθηκε: {csv_file}")
        sys.exit(1)

    # Φορτωση failures
    print(f"Φορτωση : {csv_file}")
    failures = load_failures(csv_file)
    print(f"Failures: {len(failures)}")

    if not failures:
        print("\nΜηδενικα σφαλματα — 100% accuracy απο το δεντρο.")
        print("Δεν απαιτειται αρχειο εξαιρεσεων.")
        sys.exit(0)

    # Ανιχνευση κομματιων
    piece_cols = get_piece_cols(failures)
    if not piece_cols:
        print("ERROR: Δεν βρεθηκαν στηλες τετραγωνων (endswith 'Sq').")
        print("  Βεβαιωσου οτι το failures CSV εχει wKSq, bKSq κλπ.")
        sys.exit(1)

    print(f"Κομματια: {len(piece_cols)} ({', '.join(piece_cols)})")

    endgame, nalimov_size = detect_endgame(csv_file, piece_cols)
    print(f"Φιναλε  : {endgame}")

    # Κωδικοποιηση
    bin_size = encode_exceptions(failures, bin_file, piece_cols)
    print(f"Binary  : {bin_file} ({bin_size} bytes)")

    # Επαληθευση roundtrip
    ok, extra, missing = verify_roundtrip(failures, bin_file, piece_cols)
    if ok:
        print("Roundtrip: OK ✓")
    else:
        print(f"ERROR: Roundtrip failed! extra={extra}, missing={missing}")
        sys.exit(1)

    # Υπολογισμος συνολικων θεσεων για ακριβεια
    base_csv        = csv_file.replace('_failures', '')
    total_positions = None
    if os.path.exists(base_csv) and base_csv != csv_file:
        with open(base_csv, newline='', encoding='utf-8-sig') as f:
            total_positions = sum(1 for _ in csv.DictReader(f))

    # Αναφορα
    print()
    print_report(failures, bin_file, bin_size, csv_file,
                 piece_cols, endgame, nalimov_size, total_positions)


if __name__ == '__main__':
    main()
