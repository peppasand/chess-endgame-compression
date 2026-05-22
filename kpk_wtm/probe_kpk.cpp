/*
 * probe_kpk.cpp
 * =============
 * Βημα 1: Probe των βασεων Nalimov για KPK.
 * Παραγει RAW CSV με θεσεις + αποτελεσμα ΜΟΝΟ.
 * ΔΕΝ υπολογιζει attributes.
 *
 * Compile:
 *   g++ probe_kpk.cpp egtb.cpp -o probe_kpk.exe -DT_INDEX64 -fpermissive
 *
 * Usage:
 *   .\probe_kpk.exe "C:\path\to\tablebases" [wtm/btm]
 *
 * Παραγει:
 *   kpk_wtm_raw.csv  (white to move)
 *   kpk_btm_raw.csv  (black to move)
 *
 * Format CSV:
 *   wKSq, wPSq, bKSq, result
 *
 * Το wKSq/wPSq/bKSq ειναι οι αριθμοι τετραγωνου (0-63).
 * Ολα τα attributes υπολογιζονται στο add_attributes.py.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* ---- Nalimov API ---- */
#define XX       127
#define C_PIECES   3

typedef unsigned long long INDEX;
typedef unsigned int squaret;
typedef int color;

#define x_colorWhite  0
#define x_colorBlack  1
#define pageL      65536
#define tbbe_ssL   ((pageL-4)/2)
#define bev_broken (tbbe_ssL+1)
#define bev_draw   0

#if defined(_MSC_VER)
#  define TB_FASTCALL __fastcall
#else
#  define TB_FASTCALL
#endif

typedef INDEX (TB_FASTCALL *PfnCalcIndex)(squaret *, squaret *, squaret, int);

extern "C" int IInitializeTb(char *pszPath);
extern "C" int FTbSetCacheSize(void *pv, unsigned long cbSize);
extern "C" int IDescFindFromCounters(int *);
extern "C" int FRegisteredFun(int, color);
extern "C" PfnCalcIndex PfnIndCalcFun(int, color);
extern "C" int TB_FASTCALL L_TbtProbeTable(int, color, INDEX);

/* ---- Helpers ---- */
int f(int pos) { return (pos % 8) + 1; }
int r(int pos) { return (pos / 8) + 1; }

int mymax(int a, int b) { return a > b ? a : b; }
int myabs(int a)        { return a < 0 ? -a : a; }

int dist(int a, int b) {
    return mymax(myabs(f(a)-f(b)), myabs(r(a)-r(b)));
}

/* ---- Probe ---- */
int probe_with_board(unsigned char board[64], int wtm) {
    int rgiCounters[10];
    squaret rgsqWhite[C_PIECES*5+1];
    squaret rgsqBlack[C_PIECES*5+1];
    squaret *psqW, *psqB;
    int iTb, fInvert, sq, tbValue;
    color side;
    INDEX ind;

    memset(rgiCounters, 0, sizeof(rgiCounters));
    for (sq = 0; sq < 64; sq++) {
        switch (board[sq]) {
            case 'P': rgsqWhite[0*C_PIECES + rgiCounters[0]++] = sq; break;
            case 'K': rgsqWhite[5*C_PIECES]                    = sq; break;
            case 'k': rgsqBlack[5*C_PIECES]                    = sq; break;
        }
    }

    iTb = IDescFindFromCounters(rgiCounters);
    if (!iTb) return -99;

    if (iTb > 0) {
        side = wtm ? x_colorWhite : x_colorBlack;
        fInvert = 0; psqW = rgsqWhite; psqB = rgsqBlack;
    } else {
        side = wtm ? x_colorBlack : x_colorWhite;
        fInvert = 1; psqW = rgsqBlack; psqB = rgsqWhite;
        iTb = -iTb;
    }

    if (!FRegisteredFun(iTb, side)) return -99;
    ind     = PfnIndCalcFun(iTb, side)(psqW, psqB, (squaret)XX, fInvert);
    tbValue = L_TbtProbeTable(iTb, side, ind);

    if (tbValue == (int)bev_broken) return -99;
    if (tbValue == bev_draw)        return 0;
    if (tbValue > 0) return (wtm ?  1 : -1);
    return              (wtm ? -1 :  1);
}

void make_board(unsigned char board[64], int wK, int wP, int bK) {
    memset(board, 0, 64);
    board[wK] = 'K';
    board[wP] = 'P';
    board[bK] = 'k';
}

/* ---- Main ---- */
int main(int argc, char *argv[]) {
    if (argc < 2) {
        printf("Usage: %s <path> [wtm/btm]\n", argv[0]);
        printf("  wtm = white to move (default)\n");
        printf("  btm = black to move\n");
        return 1;
    }

    char path[1024];
    strncpy(path, argv[1], sizeof(path)-1);

    /* wtm=1 (default) ή btm=0 */
    int wtm = 1;
    if (argc >= 3 && strcmp(argv[2], "btm") == 0) wtm = 0;

    const char *mode_str = wtm ? "wtm" : "btm";

    printf("=== KPK Probe Generator ===\n");
    printf("Path: %s\n", path);
    printf("Mode: %s\n\n", wtm ? "White to Move" : "Black to Move");

    /* Αρχικοποιηση Nalimov */
    int init = IInitializeTb(path);
    if (init < 3) { printf("ERROR: init=%d\n", init); return 1; }
    printf("Tablebases OK (max pieces: %d)\n", init);

    unsigned long cacheSize = 32 * 1024 * 1024;
    void *pCache = malloc(cacheSize);
    if (!pCache || !FTbSetCacheSize(pCache, cacheSize)) {
        printf("ERROR: Cache init failed\n"); return 1;
    }
    printf("Cache OK (32MB)\n\n");

    /* Sanity checks */
    unsigned char board[64];

    make_board(board, 44, 36, 60);  /* wK=e6, wP=e5, bK=e8 */
    int sanity1 = probe_with_board(board, 1);
    printf("Test: wK=e6 wP=e5 bK=e8 WTM => %s (expected: Win)\n",
           sanity1==1?"Win":sanity1==0?"Draw":"ERROR");

    make_board(board, 0, 48, 56);   /* wK=a1, wP=a7, bK=a8 */
    int sanity2 = probe_with_board(board, 1);
    printf("Test: wK=a1 wP=a7 bK=a8 WTM => %s (expected: Draw)\n\n",
           sanity2==0?"Draw":sanity2==1?"Win":"ERROR");

    /* Ονομα αρχειου εξοδου - αποθηκευση στον φακελο csv-arff */
    char outfile[256];
    sprintf(outfile, "csv-arff\\kpk_%s_raw.csv", mode_str);

    /* Δημιουργια φακελου csv-arff αν δεν υπαρχει */
    system("if not exist csv-arff mkdir csv-arff");

    FILE *fp = fopen(outfile, "w");
    if (!fp) { printf("ERROR: Cannot create %s\n", outfile); return 1; }

    /* CSV header: μονο τα τετραγωνα (0-63) και το αποτελεσμα.
     * Ολα τα attributes υπολογιζονται στο add_attributes.py */
    fprintf(fp, "wKSq,wPSq,bKSq,result\n");

    int wK, wP, bK;
    int cnt_valid=0, cnt_win=0, cnt_draw=0, cnt_loss=0, cnt_skip=0;

    for (wK = 0; wK < 64; wK++) {
        for (wP = 8; wP < 56; wP++) {   /* πιονια ranks 2-7 */
            for (bK = 0; bK < 64; bK++) {

                if (wK==wP || wK==bK || wP==bK) { cnt_skip++; continue; }
                if (dist(wK, bK) < 2)            { cnt_skip++; continue; }

                make_board(board, wK, wP, bK);
                int result = probe_with_board(board, wtm);
                if (result == -99) { cnt_skip++; continue; }

                cnt_valid++;
                if (result ==  1) cnt_win++;
                if (result ==  0) cnt_draw++;
                if (result == -1) cnt_loss++;

                /* result string */
                const char *res_str;
                if (wtm) {
                    res_str = (result==1) ? "white" :
                              (result==0) ? "draw"  : "black";
                } else {
                    res_str = (result==-1) ? "white" :
                               (result==0) ? "draw"  : "black";
                }

                fprintf(fp, "%d,%d,%d,%s\n",
                    wK, wP, bK,
                    res_str);
            }
        }
    }
    fclose(fp);

    printf("=== Αποτελεσματα ===\n");
    printf("Εγκυρες θεσεις: %d\n", cnt_valid);
    printf("  Win  : %d (%.1f%%)\n", cnt_win,  100.0*cnt_win /cnt_valid);
    printf("  Draw : %d (%.1f%%)\n", cnt_draw, 100.0*cnt_draw/cnt_valid);
    if (cnt_loss > 0)
    printf("  Loss : %d (%.1f%%)\n", cnt_loss, 100.0*cnt_loss/cnt_valid);
    printf("Skip   : %d\n", cnt_skip);
    printf("Αρχειο : %s\n", outfile);

    /* ================================================================
     * VALIDATION — Ελεγχος ορθοτητας CSV
     * ================================================================ */
    printf("\n=== Validation ===\n");
    int errors = 0;

    /* Ελεγχος 1: Αναμενομενος αριθμος θεσεων
     * KPK WTM: 168024, KPK BTM: 168024 */
    int expected = 168024;
    if (cnt_valid != expected) {
        printf("  [ERROR] Θεσεις: %d (αναμενομενο: %d)\n", cnt_valid, expected);
        errors++;
    } else {
        printf("  [OK] Θεσεις: %d\n", cnt_valid);
    }

    /* Ελεγχος 2: Win% για WTM
     * Αναμενομενο: ~76.5% Win, ~23.5% Draw */
    if (wtm) {
        float win_pct  = 100.0f * cnt_win  / cnt_valid;
        float draw_pct = 100.0f * cnt_draw / cnt_valid;
        if (win_pct < 75.0f || win_pct > 78.0f) {
            printf("  [ERROR] Win%%=%.1f (αναμενομενο: ~76.5%%)\n", win_pct);
            errors++;
        } else {
            printf("  [OK] Win%%=%.1f Draw%%=%.1f\n", win_pct, draw_pct);
        }
    }

    /* Ελεγχος 3: Sanity tests — χρησιμοποιουμε τα αποτελεσματα
     * που ηδη υπολογιστηκαν παραπανω, χωρις νεο probe */
    if (wtm && sanity1 != 1) {
        printf("  [ERROR] wK=e6 wP=e5 bK=e8 WTM: αναμενομενο Win\n");
        errors++;
    } else {
        printf("  [OK] Sanity test 1 (e6/e5/e8 WTM=Win)\n");
    }

    if (wtm && sanity2 != 0) {
        printf("  [ERROR] wK=a1 wP=a7 bK=a8 WTM: αναμενομενο Draw\n");
        errors++;
    } else {
        printf("  [OK] Sanity test 2 (a1/a7/a8 WTM=Draw)\n");
    }

    /* Συνοψη */
    if (errors == 0)
        printf("\nValidation OK - το CSV ειναι ορθο.\n");
    else
        printf("\nValidation FAILED - %d σφαλματα!\n", errors);

    return (errors == 0) ? 0 : 1;
}
