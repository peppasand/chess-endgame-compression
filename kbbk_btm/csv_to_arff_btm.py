"""
csv_to_arff.py
==============
Μετατροπη CSV αρχειου σε ARFF για χρηση στο Weka.

Χρηση:
    python csv_to_arff.py <csv_file> [wtm/btm]

Παραδειγματα:
    python csv_to_arff.py kpk_wtm_v4_critical.csv wtm
    python csv_to_arff.py kpk_btm_v4_critical.csv btm

Τι κανει:
    - Διαβαζει αυτοματα τη δομη του CSV
    - Αναγνωριζει numeric vs nominal attributes
    - Δημιουργει το σωστο ARFF με σχολια
    - Οριζει αυτοματα τις κλασεις του result (wtm/btm)
"""

import csv
import sys
import os
from collections import Counter


# ================================================================
# ΟΡΙΣΜΟΙ ATTRIBUTES
# Περιγραφες για καθε γνωστο attribute
# ================================================================

ATTRIBUTE_DESCRIPTIONS = {
    # KPK attributes (Thanou)
    'distanceToFrontSquare': 'Ποιος βασιλιας ειναι πιο κοντα στο μπροστινο τετραγωνο (Thanou)',
    'opposition':            'Αν ο λευκος εχει την opposition (Thanou)',
    'wPCanBeCaptured':       'Διαφορα αποστασεων - αν κινδυνευει το πιονι (Thanou)',
    'wPAheadInTheRace':      'Αν το πιονι ειναι μπροστα απο τον μαυρο βασιλια (Thanou)',
    'wPOnFileAOrH':          'Αν το πιονι ειναι στη στηλη a η h (Thanou)',
    'raceTimeEnough':        'Αν το πιονι προλαβαινει να γινει βασιλισσα (Thanou)',
    'kingInFront':           'Αν ο λευκος βασιλιας ειναι μπροστα απο το πιονι (νεο)',
    'ruleOfSquare':          'Κανονας τετραγωνου - αν ο μαυρος δεν προλαβαινει (νεο)',
    'criticalSquare':        'Αν ο λευκος βασιλιας ειναι σε key square (νεο)',
    # Γεωμετρικα KPK
    'wKFile':      'Στηλη λευκου βασιλια (1-8)',
    'wKRank':      'Γραμμη λευκου βασιλια (1-8)',
    'wPFile':      'Στηλη πιονιου (1-8)',
    'wPRank':      'Γραμμη πιονιου (1-8)',
    'bKFile':      'Στηλη μαυρου βασιλια (1-8)',
    'bKRank':      'Γραμμη μαυρου βασιλια (1-8)',
    'fileDiffKk':  'Διαφορα στηλης: λευκος βασιλιας - μαυρος βασιλιας',
    'rankDiffKk':  'Διαφορα γραμμης: λευκος βασιλιας - μαυρος βασιλιας',
    'fileDiffKP':  'Διαφορα στηλης: λευκος βασιλιας - πιονι',
    'rankDiffKP':  'Διαφορα γραμμης: λευκος βασιλιας - πιονι',
    'fileDiffkP':  'Διαφορα στηλης: μαυρος βασιλιας - πιονι',
    'rankDiffkP':  'Διαφορα γραμμης: μαυρος βασιλιας - πιονι',
    # KQK γεωμετρικα
    'wQFile':      'Στηλη λευκης βασιλισσας (1-8)',
    'wQRank':      'Γραμμη λευκης βασιλισσας (1-8)',
    'fileDiffKQ':  'Διαφορα στηλης: λευκος βασιλιας - βασιλισσα',
    'fileDiffkQ':  'Διαφορα στηλης: μαυρος βασιλιας - βασιλισσα',
    'rankDiffKQ':  'Διαφορα γραμμης: λευκος βασιλιας - βασιλισσα',
    'rankDiffkQ':  'Διαφορα γραμμης: μαυρος βασιλιας - βασιλισσα',
    # KRK γεωμετρικα
    'wRFile':      'Στηλη λευκου πυργου (1-8)',
    'wRRank':      'Γραμμη λευκου πυργου (1-8)',
    'fileDiffKR':  'Διαφορα στηλης: λευκος βασιλιας - πυργος',
    'fileDiffkR':  'Διαφορα στηλης: μαυρος βασιλιας - πυργος',
    'rankDiffKR':  'Διαφορα γραμμης: λευκος βασιλιας - πυργος',
    'rankDiffkR':  'Διαφορα γραμμης: μαυρος βασιλιας - πυργος',
    # KBBK attributes
    'sameColor':   'Αν οι επισκοποι εχουν ιδιο χρωμα τετραγωνου: S=ιδιο D=διαφορετικο',
    'bK_on_edge':  'Αν ο μαυρος βασιλιας ειναι στην ακρη της σκακιερας (Y/N)',
    'fDiffKk':     'Διαφορα στηλης: λευκος βασιλιας - μαυρος βασιλιας',
    'rDiffKk':     'Διαφορα γραμμης: λευκος βασιλιας - μαυρος βασιλιας',
    'fDiffKM1':    'Διαφορα στηλης: λευκος βασιλιας - επισκοπος 1',
    'rDiffKM1':    'Διαφορα γραμμης: λευκος βασιλιας - επισκοπος 1',
    'fDiffKM2':    'Διαφορα στηλης: λευκος βασιλιας - επισκοπος 2',
    'rDiffKM2':    'Διαφορα γραμμης: λευκος βασιλιας - επισκοπος 2',
    'fDiffkM1':    'Διαφορα στηλης: μαυρος βασιλιας - επισκοπος 1',
    'rDiffkM1':    'Διαφορα γραμμης: μαυρος βασιλιας - επισκοπος 1',
    'fDiffkM2':    'Διαφορα στηλης: μαυρος βασιλιας - επισκοπος 2',
    'rDiffkM2':    'Διαφορα γραμμης: μαυρος βασιλιας - επισκοπος 2',
    'fDiffM1M2':   'Διαφορα στηλης: επισκοπος 1 - επισκοπος 2',
    'rDiffM1M2':   'Διαφορα γραμμης: επισκοπος 1 - επισκοπος 2',
}


# ================================================================
# ΑΝΑΓΝΩΡΙΣΗ ΤΥΠΟΥ ATTRIBUTE
# ================================================================

def detect_type(rows, col):
    """
    Αναγνωριζει αν ενα attribute ειναι:
    - numeric: αριθμητικο
    - nominal: κατηγορικο {τιμη1, τιμη2, ...}
    """
    values = [r[col] for r in rows if r[col] != '']
    
    # Προσπαθει να μετατρεψει ολες τις τιμες σε αριθμο
    try:
        [float(v) for v in values]
        return 'numeric', None
    except ValueError:
        # Nominal - βρες ολες τις μοναδικες τιμες
        unique_vals = sorted(set(values))
        return 'nominal', unique_vals


# ================================================================
# ΔΗΜΙΟΥΡΓΙΑ ARFF
# ================================================================

def csv_to_arff(csv_filename, mode='wtm'):
    """
    Μετατρεπει CSV σε ARFF.
    mode: 'wtm' = white to move, 'btm' = black to move
    """
    
    # Φορτωση CSV
    rows = []
    with open(csv_filename, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    
    if not rows:
        print("ERROR: Κενο αρχειο!")
        return
    
    columns = list(rows[0].keys())
    attr_cols = [c for c in columns if c != 'result']
    
    # Ονομα relation απο το ονομα του αρχειου
    base_name = os.path.splitext(os.path.basename(csv_filename))[0]
    relation_name = base_name.replace('-', '_').replace(' ', '_')
    
    # Αποτελεσματα αναλογα με WTM/BTM
    if mode == 'wtm':
        result_values = '{white,draw}'
        mode_desc = 'White to Move'
    else:
        result_values = '{white,draw,black}'
        mode_desc = 'Black to Move'
    
    # Ανιχνευση τυπου φιναλε απο το ονομα αρχειου
    fname_lower = base_name.lower()
    if 'kbbk' in fname_lower:
        endgame = 'KBBK'
    elif 'kqk' in fname_lower:
        endgame = 'KQK'
    elif 'krk' in fname_lower:
        endgame = 'KRK'
    else:
        endgame = 'KPK'

    # Δημιουργια ARFF περιεχομενου
    lines = []

    # Header
    lines.append(f'% ============================================================')
    lines.append(f'% ARFF αρχειο για Weka')
    lines.append(f'% Φιναλε: {endgame} {mode_desc}')
    lines.append(f'% Πηγη  : {csv_filename}')
    lines.append(f'% Θεσεις: {len(rows)}')
    lines.append(f'% ============================================================')
    lines.append('')
    lines.append(f'@relation {relation_name}')
    lines.append('')
    
    # Attributes
    # Χωριζουμε σε ομαδες αν ειναι γνωστα
    thanou_attrs   = ['distanceToFrontSquare','opposition','wPCanBeCaptured',
                      'wPAheadInTheRace','wPOnFileAOrH','raceTimeEnough']
    new_attrs      = ['kingInFront','ruleOfSquare','criticalSquare']
    geo_attrs = [
        # KPK
        'wKFile','wKRank','wPFile','wPRank','bKFile','bKRank',
        'fileDiffKk','rankDiffKk','fileDiffKP','rankDiffKP','fileDiffkP','rankDiffkP',
        # KQK
        'wQFile','wQRank','fileDiffKQ','rankDiffKQ','fileDiffkQ','rankDiffkQ',
        # KRK
        'wRFile','wRRank','fileDiffKR','rankDiffKR','fileDiffkR','rankDiffkR',
        # KBBK
        'sameColor','bK_on_edge','fDiffKk','rDiffKk',
        'fDiffKM1','rDiffKM1','fDiffKM2','rDiffKM2',
        'fDiffkM1','rDiffkM1','fDiffkM2','rDiffkM2',
        'fDiffM1M2','rDiffM1M2',
    ]
    
    # Κατηγοριοποιηση
    has_thanou = any(c in attr_cols for c in thanou_attrs)
    has_new    = any(c in attr_cols for c in new_attrs)
    has_geo    = any(c in attr_cols for c in geo_attrs)
    
    if has_geo:
        lines.append('% --- Γεωμετρικα attributes ---')
    if has_thanou:
        if has_geo:
            lines.append('')
        lines.append('% --- Σκακιστικα attributes (Thanou, 2012) ---')
    
    written_section = False
    for col in attr_cols:
        # Εκτυπωση section header για νεα attributes
        if col in new_attrs and not written_section:
            lines.append('')
            lines.append('% --- Νεα attributes (βελτιωση) ---')
            written_section = True
        
        attr_type, nominal_vals = detect_type(rows, col)
        
        # Σχολιο με περιγραφη
        desc = ATTRIBUTE_DESCRIPTIONS.get(col, '')
        if desc:
            lines.append(f'% {desc}')
        
        # Ορισμος attribute
        if attr_type == 'numeric':
            lines.append(f'@attribute {col} numeric')
        else:
            vals_str = '{' + ','.join(nominal_vals) + '}'
            lines.append(f'@attribute {col} {vals_str}')
        
        lines.append('')
    
    # Result (class)
    lines.append('% --- Αποτελεσμα (class) ---')
    lines.append(f'% Ποιος κερδιζει με τελειο παιχνιδι')
    lines.append(f'@attribute result {result_values}')
    lines.append('')
    
    # Data section
    lines.append('@data')
    for row in rows:
        vals = [row[c] for c in columns]
        lines.append(','.join(vals))
    
    return lines


# ================================================================
# ΑΠΟΘΗΚΕΥΣΗ
# ================================================================

def save_arff(lines, csv_filename):
    # Αποθηκευση στον ιδιο φακελο με το CSV
    base = os.path.splitext(csv_filename)[0]
    arff_filename = base + '.arff'
    with open(arff_filename, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    return arff_filename


# ================================================================
# MAIN
# ================================================================

def main():
    if len(sys.argv) < 2:
        print("Χρηση: python csv_to_arff.py <csv_file> [wtm/btm]")
        print()
        print("Παραδειγματα:")
        print("  python csv_to_arff.py kpk_wtm_v4_critical.csv wtm")
        print("  python csv_to_arff.py kpk_btm_v4_critical.csv btm")
        print("  python csv_to_arff.py kpk_wtm_v1_geo.csv wtm")
        sys.exit(1)
    
    csv_filename = sys.argv[1]
    mode = sys.argv[2].lower() if len(sys.argv) > 2 else 'wtm'
    
    if mode not in ('wtm', 'btm'):
        print(f"ERROR: mode πρεπει να ειναι 'wtm' ή 'btm', οχι '{mode}'")
        sys.exit(1)
    
    if not os.path.exists(csv_filename):
        print(f"ERROR: Δεν βρεθηκε το αρχειο: {csv_filename}")
        sys.exit(1)
    
    print(f"Μετατροπη: {csv_filename} ({mode.upper()})")
    
    lines = csv_to_arff(csv_filename, mode)
    if not lines:
        sys.exit(1)
    
    arff_filename = save_arff(lines, csv_filename)
    
    # Εκτυπωση στατιστικων
    data_lines = [l for l in lines if not l.startswith('%') 
                  and not l.startswith('@') and l.strip()]
    attr_lines = [l for l in lines if l.startswith('@attribute')]
    
    print(f"Αποθηκευτηκε: {arff_filename}")
    print(f"Attributes  : {len(attr_lines) - 1}")  # -1 για το result
    print(f"Θεσεις      : {len(data_lines)}")
    print()
    print("Ετοιμο για Weka!")


if __name__ == '__main__':
    main()
