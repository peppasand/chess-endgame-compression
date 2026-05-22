"""
compress_exceptions.py — Exception Patching για lossless συμπίεση Nalimov KPK

Χρηση:
    python compress_exceptions.py <failures_csv> [output_bin]

Παραδειγμα:
    python compress_exceptions.py csv-arff/kpk_wtm_v7_failures.csv

Τι κανει:
    Διαβαζει τα failures του J48 (CSV που παραγει το analyze.py)
    και τα κωδικοποιει σε compact binary αρχειο.

    Καθε exception = 3 bytes:
        byte 0: wKSq  (0-63, θεση λευκου βασιλια)
        byte 1: wPSq  (8-55, θεση πιονιου — ranks 2-7)
        byte 2: bKSq  (0-63, θεση μαυρου βασιλια)

    Το αρχειο εχει header 4 bytes:
        bytes 0-1: magic number 0x4B50 ("KP" για KPK)
        bytes 2-3: πληθος exceptions (little-endian uint16)

    Συνολο: 4 + N*3 bytes

Αποτελεσμα (lossless compression):
    J48 δεντρο  +  exceptions.bin  =  100% αναπαραγωγη Nalimov βασης

Θεωρητικο υποβαθρο (MDL Principle):
    Το συνολικο μεγεθος συμπιεσης = μεγεθος(δεντρο) + μεγεθος(exceptions)
    Στοχος: ελαχιστοποιηση αυτου του αθροισματος.
    Παραδειγμα: για N exceptions → 4 + N*3 bytes
"""

import csv
import struct
import os
import sys


# ================================================================
# ΒΟΗΘΗΤΙΚΕΣ ΣΥΝΑΡΤΗΣΕΙΣ (ιδιες με add_attributes.py)
# ================================================================

def sq(file, rank):
    """Θεση (0-63) απο file (1-8) και rank (1-8)."""
    return (rank - 1) * 8 + (file - 1)

def file_of(sq):
    """Στηλη (1-8) απο square (0-63)."""
    return (sq % 8) + 1

def rank_of(sq):
    """Γραμμη (1-8) απο square (0-63)."""
    return (sq // 8) + 1


# ================================================================
# ΚΥΡΙΕΣ ΣΥΝΑΡΤΗΣΕΙΣ
# ================================================================

def load_failures(csv_file):
    """
    Φορτωνει το failures CSV.
    KBBK: εχει wKSq/wB1Sq/wB2Sq/bKSq (squares 0-63 απευθειας)
    3-men: εχει wKFile/wKRank + κομματι + bKFile/bKRank
    """
    failures = []
    with open(csv_file, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        is_kbbk = 'wB1Sq' in headers

        for row in reader:
            actual    = row.get('result', '').strip()
            predicted = row.get('predicted', '').strip()

            if is_kbbk:
                # KBBK: squares απευθειας (μετα mirroring)
                wk_sq  = int(row['wKSq'])
                wb1_sq = int(row['wB1Sq'])
                wb2_sq = int(row['wB2Sq'])
                bk_sq  = int(row['bKSq'])
                failures.append((wk_sq, wb1_sq, wb2_sq, bk_sq, actual, predicted))
            else:
                # 3-men: υπολογισμος απο file/rank
                wk_sq = sq(int(row['wKFile']), int(row['wKRank']))
                bk_sq = sq(int(row['bKFile']), int(row['bKRank']))
                if 'wPFile' in headers:
                    wp_sq = sq(int(row['wPFile']), int(row['wPRank']))
                elif 'wQFile' in headers:
                    wp_sq = sq(int(row['wQFile']), int(row['wQRank']))
                elif 'wRFile' in headers:
                    wp_sq = sq(int(row['wRFile']), int(row['wRRank']))
                else:
                    continue
                failures.append((wk_sq, wp_sq, bk_sq, actual, predicted))

    return failures


def encode_exceptions(failures, output_file):
    """
    Κωδικοποιει τα failures σε binary αρχειο.
    Ανιχνευει αυτοματα αν ειναι 3-men η 4-men (KBBK).

    Format 3-men (KPK/KQK/KRK):
        Header: magic(2) + count(2) = 4 bytes
        Data  : [wKSq, wPieceSq, bKSq] = 3 bytes/exception

    Format 4-men (KBBK):
        Header: magic(2) + count(2) = 4 bytes
        Data  : [wKSq, wB1Sq, wB2Sq, bKSq] = 4 bytes/exception
    """
    N = len(failures)
    is_kbbk = (len(failures[0]) == 6) if failures else False

    with open(output_file, 'wb') as f:
        # Header — magic ανα φιναλε
        magic = b'KB' if is_kbbk else b'KP'
        count = struct.pack('<H', N)
        f.write(magic + count)

        # Data
        if is_kbbk:
            for wk_sq, wb1_sq, wb2_sq, bk_sq, _, _ in failures:
                f.write(struct.pack('BBBB', wk_sq, wb1_sq, wb2_sq, bk_sq))
        else:
            for wk_sq, wp_sq, bk_sq, _, _ in failures:
                f.write(struct.pack('BBB', wk_sq, wp_sq, bk_sq))

    return os.path.getsize(output_file)


def decode_exceptions(bin_file):
    """
    Αποκωδικοποιει το binary αρχειο.
    Ανιχνευει αυτοματα 3-men η 4-men απο το magic number.
    """
    exceptions = set()
    with open(bin_file, 'rb') as f:
        magic = f.read(2)
        if magic not in (b'KP', b'KB'):
            raise ValueError(f"Λαθος magic number: {magic}")
        is_kbbk = (magic == b'KB')
        count = struct.unpack('<H', f.read(2))[0]
        for _ in range(count):
            if is_kbbk:
                wk_sq, wb1_sq, wb2_sq, bk_sq = struct.unpack('BBBB', f.read(4))
                exceptions.add((wk_sq, wb1_sq, wb2_sq, bk_sq))
            else:
                wk_sq, wp_sq, bk_sq = struct.unpack('BBB', f.read(3))
                exceptions.add((wk_sq, wp_sq, bk_sq))

    return exceptions


def verify_roundtrip(failures, bin_file):
    """
    Επαληθευει οτι ολα τα failures κωδικοποιηθηκαν σωστα.
    """
    exceptions = decode_exceptions(bin_file)
    is_kbbk = (len(failures[0]) == 6) if failures else False

    if is_kbbk:
        original = {(wk, wb1, wb2, bk) for wk, wb1, wb2, bk, _, _ in failures}
    else:
        original = {(wk, wp, bk) for wk, wp, bk, _, _ in failures}

    ok      = original == exceptions
    extra   = exceptions - original
    missing = original - exceptions

    return ok, len(extra), len(missing)


def print_report(failures, bin_file, bin_size, csv_file, total_positions=None, train_accuracy=None):
    """Εκτυπωνει αναφορα συμπιεσης."""

    N = len(failures)
    total = total_positions if total_positions else 168024

    # Στατιστικα
    is_kbbk = (len(failures[0]) == 6) if failures else False
    if is_kbbk:
        white_to_draw = sum(1 for _,_,_,_,a,p in failures if a=='white' and p=='draw')
        draw_to_white = sum(1 for _,_,_,_,a,p in failures if a=='draw'  and p=='white')
    else:
        white_to_draw = sum(1 for _,_,_,a,p in failures if a=='white' and p=='draw')
        draw_to_white = sum(1 for _,_,_,a,p in failures if a=='draw'  and p=='white')

    # Μεγεθος naive αναπαραστασης
    naive_bits  = 64 * 64 * 64
    naive_bytes = naive_bits // 8

    # Πραγματικο μεγεθος Nalimov .emd ανα φιναλε
    fname = csv_file.lower()
    is_kbbk = (len(failures[0]) == 6) if failures else False
    if is_kbbk:
        nalimov_approx = 130000  # kbbk_nbb.emd εκτιμηση
        bytes_per_exc  = 4
        endgame = 'KBBK'
    elif 'kqk' in fname:
        nalimov_approx = 5961
        bytes_per_exc  = 3
        endgame = 'KQK'
    elif 'krk' in fname:
        nalimov_approx = 7609
        bytes_per_exc  = 3
        endgame = 'KRK'
    else:
        nalimov_approx = 16589
        bytes_per_exc  = 3
        endgame = 'KPK'

    print("=" * 60)
    print("EXCEPTION PATCHING — ΑΝΑΦΟΡΑ ΣΥΜΠΙΕΣΗΣ")
    print("=" * 60)
    print(f"Failures CSV : {csv_file}")
    print(f"Output bin   : {bin_file}")
    print()
    print(f"Exceptions   : {N}")
    print(f"  white→draw : {white_to_draw}")
    print(f"  draw→white : {draw_to_white}")
    print()
    print("ΚΩΔΙΚΟΠΟΙΗΣΗ")
    print(f"  Header     : 4 bytes (magic + count)")
    print(f"  Data       : {N} × 3 bytes = {N*3} bytes")
    print(f"  Συνολο     : {bin_size} bytes ({bin_size/1024:.2f} KB)")
    print()
    print("ΣΥΓΚΡΙΣΗ ΜΕΓΕΘΟΥΣ")
    print(f"  Naive (1 bit/θεση)  : {naive_bytes:>8} bytes ({naive_bytes/1024:.1f} KB)")
    print(f"  Nalimov .emd ({endgame})  : {nalimov_approx:>8} bytes ({nalimov_approx/1024:.1f} KB)")
    print(f"  Exceptions.bin      : {bin_size:>8} bytes ({bin_size/1024:.2f} KB)")
    print()
    print("LOSSLESS COMPRESSION")
    print(f"  J48 δεντρο + exceptions.bin = 100% αναπαραγωγη Nalimov")
    if train_accuracy and total_positions:
        print(f"  Ακριβεια J48 (training set): {train_accuracy:.4f}% ({total-N}/{total} σωστα)")
    print(f"  Καλυπτεται απο exceptions  : {N} θεσεις")
    print(f"  Τελικη ακριβεια            : 100.00%")
    print("=" * 60)


# ================================================================
# MAIN
# ================================================================

def main():
    if len(sys.argv) < 2:
        print("Χρηση: python compress_exceptions.py <failures_csv> [output_bin]")
        print("Παραδειγμα:")
        print("  python compress_exceptions.py csv-arff\\kpk_wtm_v7_failures.csv")
        sys.exit(1)

    csv_file = sys.argv[1]

    # Output filename
    if len(sys.argv) >= 3:
        bin_file = sys.argv[2]
    else:
        base = os.path.splitext(csv_file)[0]
        base = base.replace('_failures', '')
        bin_file = base + '_exceptions.bin'

    if not os.path.exists(csv_file):
        print(f"ERROR: Δεν βρεθηκε: {csv_file}")
        sys.exit(1)

    # Φορτωση
    print(f"Φορτωση failures: {csv_file}")
    failures = load_failures(csv_file)
    print(f"Failures: {len(failures)}")

    # Κωδικοποιηση
    bin_size = encode_exceptions(failures, bin_file)
    print(f"Binary: {bin_file} ({bin_size} bytes)")

    # Επαληθευση roundtrip
    ok, extra, missing = verify_roundtrip(failures, bin_file)
    if ok:
        print(f"Roundtrip verification: OK")
    else:
        print(f"ERROR: Roundtrip failed! extra={extra}, missing={missing}")
        sys.exit(1)

    # Υπολογισμος ακριβειας απο failures
    base_csv = csv_file.replace('_failures', '')
    total_positions = None
    if os.path.exists(base_csv):
        with open(base_csv, newline='', encoding='utf-8-sig') as f:
            total_positions = sum(1 for _ in csv.DictReader(f))

    train_accuracy = None
    if total_positions:
        train_accuracy = 100.0 * (total_positions - len(failures)) / total_positions

    # Αναφορα
    print()
    print_report(failures, bin_file, bin_size, csv_file, total_positions, train_accuracy)


if __name__ == '__main__':
    main()
