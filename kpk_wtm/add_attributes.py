"""
add_attributes.py
=================
Βημα 2: Υπολογισμος attributes απο RAW CSV + inline Validation.

Διαβαζει το kpk_raw.csv (απο probe_kpk.exe),
προσθετει τα επιλεγμενα attributes και ελεγχει
αμεσα την ορθοτητα τους (χωρις αναγνωση αρχειου).

Χρηση:
    python add_attributes.py <raw_csv> <version> [wtm/btm]

Παραδειγματα:
    python add_attributes.py kpk_wtm_raw.csv v4 wtm
    python add_attributes.py kpk_btm_raw.csv v6 btm

Εκδοσεις (version):
    v1 : Γεωμετρικα attributes (απολυτες θεσεις)
    v2 : Σκακιστικα attributes (Thanou, 2012)
    v3 : v2 + kingInFront + ruleOfSquare
    v4 : v3 + criticalSquare
    v5 : Γεωμετρικα Θανου (διαφορες) + v4 σκακιστικα
    v6 : v5 + measure (3 ξεχωριστα συστατικα)
    v7 : v6 + απολυτες θεσεις ολων των κομματιων
    v8 : v7 + bKCanBlock + bKInFrontOfPawn + distToPromotion_diff
    v9 : v7 με distToPromotion_diff ΑΝΤΙ distanceToFrontSquare
    v10: v7 + distToPromotion_diff (και τα δυο, 22 attributes)

Παραγει:
    kpk_wtm_vX.csv        — dataset με attributes
    kpk_wtm_vX_analysis.txt — validation report
"""

import csv
import sys
import os
from collections import Counter


# ================================================================
# ΒΟΗΘΗΤΙΚΕΣ ΣΥΝΑΡΤΗΣΕΙΣ (ιδιες με C++ κωδικα)
# ================================================================

def f(sq):
    """Στηλη τετραγωνου (1-8), a=1 ... h=8"""
    return (sq % 8) + 1

def r(sq):
    """Γραμμη τετραγωνου (1-8)"""
    return (sq // 8) + 1

def dist(sq1, sq2):
    """Chebyshev distance (κινηση βασιλια)"""
    return max(abs(f(sq1)-f(sq2)), abs(r(sq1)-r(sq2)))

def dist2(bk, pawn):
    """
    Διορθωμενη αποσταση μαυρου βασιλια απο πιονι.
    +1 αν ο μαυρος ειναι στα διαγωνια τετραγωνα του πιονιου.
    """
    diag_l = pawn
    diag_r = pawn
    for _ in range(6):
        diag_l += 7
        diag_r += 9
        if bk == diag_l or bk == diag_r:
            return dist(bk, pawn) + 1
        else:
            return dist(bk, pawn)
    return dist(bk, pawn)

def spare_move(wk, pawn):
    """Αν ο λευκος βασιλιας εχει εφεδρικη κινηση"""
    return 1 if r(wk) - r(pawn) >= 2 else 0


# ================================================================
# ΥΠΟΛΟΓΙΣΜΟΣ ATTRIBUTES
# ================================================================

# --- Attributes Θάνου (v2) ---

def attr_distanceToFrontSquare(wk, pawn, bk):
    """
    NEAR: λευκος πιο κοντα στο μπροστινο τετραγωνο
    FAR:  μαυρος πιο κοντα
    """
    if pawn + 7 < 64 and pawn + 16 < 64:
        a = min(dist(wk, pawn+7) - dist(bk, pawn+16),
                dist(wk, pawn+9) - dist(bk, pawn+16))
    else:
        a = 0
    return 'NEAR' if a <= 0 else 'FAR'

def attr_opposition(wk, pawn, bk):
    """Αν ο λευκος εχει direct opposition"""
    if f(wk) == f(bk) and (r(bk) - r(wk) - 1) == 1:
        opp = 0 if spare_move(wk, pawn) == 0 else 1
    else:
        opp = 0
    return 'Y' if opp else 'N'

def attr_wPCanBeCaptured(wk, pawn, bk):
    """Numeric: διαφορα αποστασεων (αρνητικο=ασφαλες, θετικο=κινδυνος)"""
    a = dist(wk, pawn) - dist2(bk, pawn)
    if pawn + 8 < 64:
        a = min(a, dist(wk, pawn+8) - dist2(bk, pawn+8))
    if pawn + 16 < 64:
        a = min(a, dist(wk, pawn+16) - dist2(bk, pawn+16))
    return a

def attr_wPAheadInTheRace(wk, pawn, bk):
    """Y αν το πιονι ειναι μπροστα απο τον μαυρο βασιλια"""
    if r(pawn) > r(bk) and wk != pawn + 8:
        return 'Y'
    if r(pawn) == r(bk) and r(pawn) == 2 and wk != pawn+8 and wk != pawn+16:
        return 'Y'
    return 'N'

def attr_wPOnFileAOrH(pawn):
    """Y αν το πιονι ειναι στη στηλη a η h"""
    return 'Y' if f(pawn) in (1, 8) else 'N'

def attr_raceTimeEnough(wk, pawn, bk):
    """Y αν το πιονι προλαβαινει να γινει βασιλισσα"""
    flag_king_ahead = 0
    sq = pawn + 8
    while sq <= 63:
        if sq == wk:
            flag_king_ahead = 1
        sq += 8
    last_rank_sq = sq - 8

    if flag_king_ahead == 0:
        return 'Y' if dist(pawn, last_rank_sq) - dist(bk, last_rank_sq) < -1 else 'N'
    else:
        return 'Y' if dist(pawn, last_rank_sq) - dist(bk, last_rank_sq) < -2 else 'N'

# --- Νέα attributes (v3) ---

def attr_kingInFront(wk, pawn):
    """Y αν ο λευκος βασιλιας ειναι μπροστα απο το πιονι"""
    rank_diff = r(wk) - r(pawn)
    file_diff = abs(f(wk) - f(pawn))
    return 'Y' if rank_diff > 0 and file_diff <= 1 else 'N'

def attr_ruleOfSquare(pawn, bk, wtm):
    """Y αν ο μαυρος δεν προλαβαινει το πιονι (κανονας τετραγωνου)"""
    promotion_sq = (7 * 8) + (f(pawn) - 1)
    pawn_dist = 8 - r(pawn)
    if wtm:
        pawn_dist -= 1
    king_dist = dist(bk, promotion_sq)
    return 'Y' if king_dist > pawn_dist else 'N'

# --- Νέα attributes (v4) ---

def attr_criticalSquare(wk, pawn):
    """
    Y αν ο λευκος βασιλιας ειναι σε key square.

    Κανονας:
    - Ακραια πιονια (a,h): key square μονο στην παρακειμενη στηλη
      ΚΑΙ ο βασιλιας δεν πρεπει να ειναι μπροστα απο το πιονι
    - Κεντρικα πιονια: key squares 2 γραμμες μπροστα (±1 στηλη)
      ΚΑΙ ο βασιλιας δεν πρεπει να ειναι μπροστα απο το πιονι
    """
    pawn_file = f(pawn)
    pawn_rank = r(pawn)
    king_file = f(wk)
    king_rank = r(wk)

    # Ο βασιλιας δεν πρεπει να εμποδιζει το πιονι:
    # μπλοκαρει μονο αν ειναι ΑΚΡΙΒΩΣ 1 γραμμη μπροστα (οχι 2+)
    king_blocks = (king_rank == pawn_rank + 1 and king_file == pawn_file)
    if king_blocks:
        return 'N'

    # Για ακραια πιονια: αποκλεισμος αν βασιλιας μπροστα στην ιδια η διπλανη στηλη
    # ΕΞΑΙΡΕΣΗ: για πιονι rank 7, ο βασιλιας ΠΡΕΠΕΙ να ειναι στη rank 8 (key square)
    if pawn_file == 1 or pawn_file == 8:
        if pawn_rank < 7:  # μονο για ranks 2-6
            king_in_front_edge = (king_rank > pawn_rank and abs(king_file - pawn_file) <= 1)
            if king_in_front_edge:
                return 'N'

    # Υπολογισμος key rank
    if pawn_rank <= 5:
        key_rank = pawn_rank + 2
    elif pawn_rank == 6:
        key_rank = pawn_rank + 1
    else:
        key_rank = 8

    # Ακραια πιονια
    if pawn_file == 1 or pawn_file == 8:
        key_file = 2 if pawn_file == 1 else 7
        return 'Y' if king_file == key_file and king_rank == key_rank else 'N'

    # Κεντρικα πιονια
    min_file = max(1, pawn_file - 1)
    max_file = min(8, pawn_file + 1)
    return 'Y' if (king_rank == key_rank and
                   min_file <= king_file <= max_file) else 'N'


# ================================================================
# ΝΕΑ ATTRIBUTES v6 — Measure (Θάνου) ξεχωριστά
# ================================================================

def attr_abs_fileDiff_bKP(pawn, bk):
    """
    Οριζόντια απόσταση μαύρου βασιλιά από πιόνι (απόλυτη τιμή).
    Μεγάλη τιμή = μαύρος μακριά οριζόντια = καλό για λευκό.
    Συστατικό 1 του measure του Θάνου: abs(f(bK) - f(pawn))
    """
    return abs(f(pawn) - f(bk))

def attr_abs_fileDiff_wKP(pawn, wk):
    """
    Οριζόντια απόσταση λευκού βασιλιά από πιόνι (απόλυτη τιμή).
    Μικρή τιμή = λευκός κοντά οριζόντια = καλό για λευκό.
    Συστατικό 2 του measure του Θάνου: abs(f(wK) - f(pawn))
    """
    return abs(f(pawn) - f(wk))

def attr_abs_rankDiff_bKP(pawn, bk):
    """
    Κάθετη απόσταση μαύρου βασιλιά από πιόνι (απόλυτη τιμή).
    Μεγάλη τιμή = μαύρος μακριά κάθετα = καλό για λευκό.
    Συστατικό 3 του measure του Θάνου: abs(r(bK) - r(pawn))
    """
    return abs(r(pawn) - r(bk))

def attr_measure(pawn, wk, bk):
    """
    Το 'measure' του Θάνου — συνδυασμός των 3 παραπάνω:
    measure = abs(f(bK)-f(pawn)) - abs(f(wK)-f(pawn)) + abs(r(bK)-r(pawn))
    Μεγάλη τιμή = καλή θέση για λευκό.
    ΣΗΜΕΙΩΣΗ: Τα 3 ξεχωριστά attributes (v6) δίνουν περισσότερη πληροφορία
    από το ενιαίο measure, όπως αναφέρει ο Θάνου.
    """
    return attr_abs_fileDiff_bKP(pawn, bk) \
         - attr_abs_fileDiff_wKP(pawn, wk) \
         + attr_abs_rankDiff_bKP(pawn, bk)


# ================================================================
# ΝΕΑ ATTRIBUTES v8 — Σκακιστικά από ανάλυση failures v7
# ================================================================

def attr_bKCanBlock(pawn, bk):
    """
    Y αν ο μαύρος βασιλιάς μπορεί να μπει εμπρός από το πιόνι σε 1 κίνηση.
    Blocking square = το τετράγωνο ακριβώς μπροστά από το πιόνι (pawn+8).
    Αυτό καλύπτει το hotspot abs_fileDiff=1 & abs_rankDiff=1 (87% failures v7).
    Σκακιστική ερμηνεία: αν ο μαύρος μπλοκάρει, το πιόνι δεν μπορεί να προχωρήσει.
    """
    blocking_sq = pawn + 8
    if blocking_sq > 63:
        return 'N'
    return 'Y' if dist(bk, blocking_sq) == 1 else 'N'

def attr_bKInFrontOfPawn(pawn, bk):
    """
    Y αν ο μαύρος βασιλιάς είναι ήδη εμπρός από το πιόνι.
    Εμπρός = ίδια ή διπλανή στήλη (±1) ΚΑΙ γραμμή > γραμμή πιονιού.
    Σκακιστική ερμηνεία: ο μαύρος ελέγχει τα τετράγωνα προαγωγής.
    """
    return 'Y' if (r(bk) > r(pawn) and abs(f(bk) - f(pawn)) <= 1) else 'N'

def attr_distToPromotion_diff(pawn, bk):
    """
    Διαφορά αποστάσεων πιονιού και μαύρου βασιλιά από το promotion square.
    Αρνητικό: πιόνι πιο κοντά → Win πιθανό.
    Θετικό:   μαύρος πιο κοντά → Draw πιθανό.
    Αντικαθιστά το grοσσ FAR/NEAR του distanceToFrontSquare.
    """
    promo_sq = (7 * 8) + (f(pawn) - 1)  # rank 8, ίδια στήλη με πιόνι
    return dist(pawn, promo_sq) - dist(bk, promo_sq)


# ================================================================
# ΟΡΙΣΜΟΣ ΕΚΔΟΣΕΩΝ
# ================================================================

VERSIONS = {
    'v1': {
        'desc': 'Γεωμετρικα attributes μονο',
        'attrs': []  # Τα γεωμετρικα ειναι ηδη στο raw CSV
    },
    'v2': {
        'desc': 'Σκακιστικα attributes (Thanou, 2012)',
        'attrs': ['distanceToFrontSquare', 'opposition', 'wPCanBeCaptured',
                  'wPAheadInTheRace', 'wPOnFileAOrH', 'raceTimeEnough']
    },
    'v3': {
        'desc': 'v2 + kingInFront + ruleOfSquare',
        'attrs': ['distanceToFrontSquare', 'opposition', 'wPCanBeCaptured',
                  'wPAheadInTheRace', 'wPOnFileAOrH', 'raceTimeEnough',
                  'kingInFront', 'ruleOfSquare']
    },
    'v4': {
        'desc': 'v3 + criticalSquare',
        'attrs': ['distanceToFrontSquare', 'opposition', 'wPCanBeCaptured',
                  'wPAheadInTheRace', 'wPOnFileAOrH', 'raceTimeEnough',
                  'kingInFront', 'ruleOfSquare', 'criticalSquare']
    },
    'v5': {
        'desc': 'Γεωμετρικα Θανου + v4 σκακιστικα (συνδυασμος)',
        'attrs': ['distanceToFrontSquare', 'opposition', 'wPCanBeCaptured',
                  'wPAheadInTheRace', 'wPOnFileAOrH', 'raceTimeEnough',
                  'kingInFront', 'ruleOfSquare', 'criticalSquare']
        # Τα γεωμετρικα του Θανου (fileDiffKk κλπ) προστιθενται ξεχωριστα
        # στη συναρτηση add_attributes() για την v5
    },
    'v6': {
        'desc': 'v5 + measure (3 ξεχωριστα συστατικα Θανου)',
        'attrs': ['distanceToFrontSquare', 'opposition', 'wPCanBeCaptured',
                  'wPAheadInTheRace', 'wPOnFileAOrH', 'raceTimeEnough',
                  'kingInFront', 'ruleOfSquare', 'criticalSquare',
                  'abs_fileDiff_bKP', 'abs_fileDiff_wKP', 'abs_rankDiff_bKP']
    },
    'v7': {
        'desc': 'v6 + απολυτες θεσεις ολων κομματιων (γεωμ. Θανου + abs)',
        'attrs': ['distanceToFrontSquare', 'opposition', 'wPCanBeCaptured',
                  'wPAheadInTheRace', 'wPOnFileAOrH', 'raceTimeEnough',
                  'kingInFront', 'ruleOfSquare', 'criticalSquare',
                  'abs_fileDiff_bKP', 'abs_fileDiff_wKP', 'abs_rankDiff_bKP']
        # v7 = v6 + γεωμ. Θανου (diff) + απολυτες θεσεις (wKFile,wKRank,wPFile,wPRank,bKFile,bKRank)
        # τα γεωμετρικα προστιθενται στη συναρτηση add_attributes() για v7
    },
    'v8': {
        'desc': 'v7 + 3 νεα σκακιστικα (bKCanBlock, bKInFrontOfPawn, distToPromotion_diff)',
        'attrs': ['distanceToFrontSquare', 'opposition', 'wPCanBeCaptured',
                  'wPAheadInTheRace', 'wPOnFileAOrH', 'raceTimeEnough',
                  'kingInFront', 'ruleOfSquare', 'criticalSquare',
                  'abs_fileDiff_bKP', 'abs_fileDiff_wKP', 'abs_rankDiff_bKP',
                  'bKCanBlock', 'bKInFrontOfPawn', 'distToPromotion_diff']
        # v8 = v7 + 3 νεα attributes απο αναλυση failures v7:
        #   bKCanBlock:          μαυρος μπορει να μπλοκαρει το πιονι σε 1 κινηση
        #   bKInFrontOfPawn:     μαυρος ειναι ηδη εμπροσθεν πιονιου
        #   distToPromotion_diff: αριθμητικη διαφορα αποστασεων (αντικ. FAR/NEAR)
    },
    'v9': {
        'desc': 'v7 με distToPromotion_diff ΑΝΤΙ distanceToFrontSquare',
        'attrs': ['distToPromotion_diff', 'opposition', 'wPCanBeCaptured',
                  'wPAheadInTheRace', 'wPOnFileAOrH', 'raceTimeEnough',
                  'kingInFront', 'ruleOfSquare', 'criticalSquare',
                  'abs_fileDiff_bKP', 'abs_fileDiff_wKP', 'abs_rankDiff_bKP']
        # v9 = v7 με ΑΝΤΙΚΑΤΑΣΤΑΣΗ:
        #   distanceToFrontSquare (FAR/NEAR, IG=0.209) →
        #   distToPromotion_diff  (αριθμητικη, IG=0.367)
        # Αποτελεσμα: 596 λαθη (vs 548 v7) — οριακα χειροτερο
    },
    'v10': {
        'desc': 'v7 + distToPromotion_diff (και τα δυο, 22 attributes)',
        'attrs': ['distanceToFrontSquare', 'opposition', 'wPCanBeCaptured',
                  'wPAheadInTheRace', 'wPOnFileAOrH', 'raceTimeEnough',
                  'kingInFront', 'ruleOfSquare', 'criticalSquare',
                  'abs_fileDiff_bKP', 'abs_fileDiff_wKP', 'abs_rankDiff_bKP',
                  'distToPromotion_diff']
        # v10 = v7 + distToPromotion_diff (χωρις αφαιρεση)
        # Υποθεση: το distToPromotion_diff (IG=0.367) παρεχει
        # συμπληρωματικη πληροφορια στο distanceToFrontSquare (IG=0.209)
        # τα γεωμετρικα προστιθενται στη συναρτηση add_attributes() οπως v7
    }
}


# ================================================================
# ΥΠΟΛΟΓΙΣΜΟΣ ΕΝΟΣ ATTRIBUTE
# ================================================================

def compute_attribute(attr_name, wk, pawn, bk, wtm):
    """Υπολογιζει ενα attribute για μια θεση."""
    if attr_name == 'distanceToFrontSquare':
        return attr_distanceToFrontSquare(wk, pawn, bk)
    elif attr_name == 'opposition':
        return attr_opposition(wk, pawn, bk)
    elif attr_name == 'wPCanBeCaptured':
        return attr_wPCanBeCaptured(wk, pawn, bk)
    elif attr_name == 'wPAheadInTheRace':
        return attr_wPAheadInTheRace(wk, pawn, bk)
    elif attr_name == 'wPOnFileAOrH':
        return attr_wPOnFileAOrH(pawn)
    elif attr_name == 'raceTimeEnough':
        return attr_raceTimeEnough(wk, pawn, bk)
    elif attr_name == 'kingInFront':
        return attr_kingInFront(wk, pawn)
    elif attr_name == 'ruleOfSquare':
        return attr_ruleOfSquare(pawn, bk, wtm)
    elif attr_name == 'criticalSquare':
        return attr_criticalSquare(wk, pawn)
    elif attr_name == 'abs_fileDiff_bKP':
        return attr_abs_fileDiff_bKP(pawn, bk)
    elif attr_name == 'abs_fileDiff_wKP':
        return attr_abs_fileDiff_wKP(pawn, wk)
    elif attr_name == 'abs_rankDiff_bKP':
        return attr_abs_rankDiff_bKP(pawn, bk)
    elif attr_name == 'measure':
        return attr_measure(pawn, wk, bk)
    elif attr_name == 'bKCanBlock':
        return attr_bKCanBlock(pawn, bk)
    elif attr_name == 'bKInFrontOfPawn':
        return attr_bKInFrontOfPawn(pawn, bk)
    elif attr_name == 'distToPromotion_diff':
        return attr_distToPromotion_diff(pawn, bk)
    else:
        raise ValueError(f"Αγνωστο attribute: {attr_name}")


# ================================================================
# ΚΥΡΙΑ ΣΥΝΑΡΤΗΣΗ
# ================================================================

def add_attributes(raw_csv, version, wtm=True):
    if version not in VERSIONS:
        print(f"ERROR: Αγνωστη εκδοση '{version}'")
        print(f"Διαθεσιμες: {', '.join(VERSIONS.keys())}")
        return

    ver_info = VERSIONS[version]
    attrs    = ver_info['attrs']
    mode_str = 'wtm' if wtm else 'btm'

    print(f"Εκδοση : {version} — {ver_info['desc']}")
    print(f"Mode   : {mode_str.upper()}")
    print(f"Attrs  : {len(attrs)} σκακιστικα + γεωμετρικα")

    # Φορτωση raw CSV
    rows = []
    with open(raw_csv, newline='', encoding='utf-8-sig') as f_in:
        reader = csv.DictReader(f_in)
        for row in reader:
            rows.append(row)

    print(f"Θεσεις : {len(rows)}")

    # Ονομα αρχειου εξοδου - αποθηκευση στον φακελο csv-arff
    base = os.path.splitext(os.path.basename(raw_csv))[0]
    out_base = base.replace('_raw', f'_{version}')
    
    # Φτιαχνουμε τον φακελο csv-arff αν δεν υπαρχει
    out_dir = os.path.dirname(raw_csv) or '.'
    os.makedirs(out_dir, exist_ok=True)
    
    out_file = os.path.join(out_dir, out_base + '.csv')

    # Γεωμετρικα columns (υπολογιζονται απο τα squares)
    geo_cols_abs = ['wKFile','wKRank','wPFile','wPRank','bKFile','bKRank']

    # Γεωμετρικα Θανου (διαφορες θεσεων - υπολογιζονται)
    geo_cols_thanou = ['fileDiffKk','rankDiffKk','fileDiffKP','rankDiffKP',
                       'fileDiffkP','rankDiffkP']

    with open(out_file, 'w', newline='', encoding='utf-8') as f_out:
        # Header αναλογα με την εκδοση
        if version == 'v1':
            header = geo_cols_abs + ['result']
        elif version in ('v5', 'v6'):
            # v5/v6: γεωμετρικα Θανου (διαφορες) + σκακιστικα
            header = geo_cols_thanou + attrs + ['result']
        elif version in ('v7', 'v9', 'v10'):
            # v7: γεωμετρικα Θανου (διαφορες) + απολυτες θεσεις + σκακιστικα
            header = geo_cols_thanou + geo_cols_abs + attrs + ['result']
        else:
            # v2,v3,v4: απολυτες θεσεις + σκακιστικα
            header = geo_cols_abs + attrs + ['result']

        writer = csv.DictWriter(f_out, fieldnames=header)
        writer.writeheader()

        computed_rows = []  # για inline validation

        for row in rows:
            wk   = int(row['wKSq'])
            pawn = int(row['wPSq'])
            bk   = int(row['bKSq'])

            out_row = {}

            if version in ('v5', 'v6', 'v7', 'v9', 'v10'):
                # Γεωμετρικα Θανου: διαφορες στηλων/γραμμων
                out_row['fileDiffKk']  = f(wk)   - f(bk)
                out_row['rankDiffKk']  = r(wk)   - r(bk)
                out_row['fileDiffKP']  = f(wk)   - f(pawn)
                out_row['rankDiffKP']  = r(wk)   - r(pawn)
                out_row['fileDiffkP']  = f(bk)   - f(pawn)
                out_row['rankDiffkP']  = r(bk)   - r(pawn)

            if version not in ('v5', 'v6'):
                # v1,v2,v3,v4,v7: απολυτες θεσεις (υπολογιζονται απο squares)
                out_row['wKFile'] = f(wk)
                out_row['wKRank'] = r(wk)
                out_row['wPFile'] = f(pawn)
                out_row['wPRank'] = r(pawn)
                out_row['bKFile'] = f(bk)
                out_row['bKRank'] = r(bk)

            # Σκακιστικα attributes (υπολογισμος)
            for attr in attrs:
                out_row[attr] = compute_attribute(attr, wk, pawn, bk, wtm)

            out_row['result'] = row['result']
            writer.writerow(out_row)
            computed_rows.append(out_row)

    print(f"Αρχειο : {out_file}")

    # ── INLINE VALIDATION ──────────────────────────────────────
    # Τρεχει αμεσα μετα την παραγωγη του CSV, χωρις να
    # ξαναδιαβαστει το αρχειο — χρησιμοποιει τα computed_rows.
    _run_validation(computed_rows, out_file, attrs)

    return out_file


def _run_validation(computed_rows, out_file, attrs):
    """
    Ελεγχει αν τα attributes ειναι λογικα συνεπη με τα αποτελεσματα.
    Τρεχει αμεσα μετα το add_attributes() χωρις αναγνωση αρχειου.
    """
    total  = len(computed_rows)
    wins   = sum(1 for r in computed_rows if r['result']=='white')
    draws  = total - wins

    print()
    print("=" * 50)
    print("VALIDATION")
    print("=" * 50)
    print(f"Θεσεις  : {total}")
    print(f"Win     : {wins}  ({100*wins/total:.1f}%)")
    print(f"Draw    : {draws} ({100*draws/total:.1f}%)")
    print()

    problems  = 0
    report    = []

    # Ελεγχος nominal attributes: Y αλλα result=draw
    nominal_attrs = [a for a in attrs
                     if 'Y' in set(r.get(a,'') for r in computed_rows[:20])]

    for attr in nominal_attrs:
        errors  = [r for r in computed_rows if r.get(attr)=='Y'
                   and r['result']=='draw']
        total_y = sum(1 for r in computed_rows if r.get(attr)=='Y')
        if not total_y:
            continue

        if errors:
            pct = 100*len(errors)/total_y
            msg = f"  [WARN] {attr}=Y: {len(errors)} λαθη ({pct:.1f}%)"
            print(msg)
            report.append(msg)
            problems += 1

            # Κοινα χαρακτηριστικα λαθων (>60%)
            other = [a for a in nominal_attrs if a != attr]
            for o in other:
                cnt_y = sum(1 for r in errors if r.get(o)=='Y')
                if cnt_y and 100*cnt_y/len(errors) >= 60:
                    detail = f"    → {o}=Y: {cnt_y}/{len(errors)} ({100*cnt_y/len(errors):.0f}%)"
                    print(detail)
                    report.append(detail)
        else:
            print(f"  [OK]   {attr}=Y: 100% Win ({total_y} θεσεις)")

    # 100% Win attributes
    perfect = [a for a in nominal_attrs
               if all(r['result']=='white'
                      for r in computed_rows if r.get(a)=='Y')
               and any(r.get(a)=='Y' for r in computed_rows)]
    if perfect:
        print()
        print(f"100% Win: {', '.join(f'{a}=Y' for a in perfect)}")

    print()
    if problems == 0:
        print("Validation: OK — Ολα τα attributes ειναι συνεπη.")
        print(f"Επομενο βημα: python csv_to_arff.py {out_file} wtm")
    else:
        print(f"Validation: {problems} προβληματικα attributes.")
        print("Επομενο βημα: Διορθωση στο add_attributes.py")

        # Αποθηκευση report μονο αν υπαρχουν προβληματα
        report_file = out_file.replace('.csv', '_analysis.txt')
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(f"Validation report: {out_file}\n")
            f.write(f"Θεσεις: {total}  Win: {wins} ({100*wins/total:.1f}%)  Draw: {draws}\n\n")
            f.write('\n'.join(report))
        print(f"Report  : {report_file}")


# ================================================================
# MAIN
# ================================================================

def main():
    if len(sys.argv) < 3:
        print("Χρηση: python add_attributes.py <raw_csv> <version> [wtm/btm]")
        print()
        print("Παραδειγματα:")
        print("  python add_attributes.py kpk_wtm_raw.csv v4 wtm")
        print("  python add_attributes.py kpk_btm_raw.csv v2 btm")
        print()
        print("Εκδοσεις:")
        for v, info in VERSIONS.items():
            print(f"  {v}: {info['desc']}")
        sys.exit(1)

    raw_csv = sys.argv[1]
    version = sys.argv[2]
    wtm     = True if len(sys.argv) < 4 or sys.argv[3] == 'wtm' else False

    if not os.path.exists(raw_csv):
        print(f"ERROR: Δεν βρεθηκε: {raw_csv}")
        sys.exit(1)

    print("=" * 50)
    print("KPK Attribute Calculator")
    print("=" * 50)

    out = add_attributes(raw_csv, version, wtm)


if __name__ == '__main__':
    main()
