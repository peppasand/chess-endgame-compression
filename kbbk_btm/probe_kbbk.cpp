/*
 * probe_kbbk.cpp
 * ==============
 * Βημα 1: Probe των βασεων Nalimov για KBBK.
 * Παραγει RAW CSV με θεσεις + αποτελεσμα ΜΟΝΟ.
 * ΔΕΝ υπολογιζει attributes.
 *
 * Compile:
 *   g++ probe_kbbk.cpp ..\egtb.cpp -o probe_kbbk.exe -DT_INDEX64 -fpermissive -I..
 *
 * Usage:
 *   .\probe_kbbk.exe "C:\path\to\tablebases" [wtm/btm]
 *
 * Παραγει:
 *   kbbk_wtm_raw.csv  (white to move)
 *   kbbk_btm_raw.csv  (black to move)
 *
 * Format CSV:
 *   wKSq, wB1Sq, wB2Sq, bKSq, result
 *
 * Σημειωση:
 *   Οι δυο επισκοποι (B1, B2) αποθηκευονται παντα με B1 <= B2
 *   για να αποφευχθουν διπλοτυπα (B1=e1,B2=f2 == B1=f2,B2=e1).
 *
 *   Ο Θανου (2012) χρησιμοποιησε 1.000.000 τυχαιο sample απο ~3.5M θεσεις.
 *   Εμεις παραγουμε ΟΛΕΣ τις εγκυρες θεσεις.
 *
 *   Το attribute sameColor υπολογιζεται στο add_attributes.py:
 *   sameColor = (wB1Sq % 2 == wB2Sq % 2) ? 'S' : 'D'
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
            /* Επισκοπος: piece index 2 (x_pieceBishop=3, array index 2) */
            case 'B': rgsqWhite[2*C_PIECES + rgiCounters[2]++] = sq; break;
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

void make_board(unsigned char board[64], int wK, int wB1, int wB2, int bK) {
    memset(board, 0, 64);
    board[wK]  = 'K';
    board[wB1] = 'B';
    board[wB2] = 'B';
    board[bK]  = 'k';
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

    int wtm = 1;
    if (argc >= 3 && strcmp(argv[2], "btm") == 0) wtm = 0;

    const char *mode_str = wtm ? "wtm" : "btm";

    printf("=== KBBK Probe Generator ===\n");
    printf("Path: %s\n", path);
    printf("Mode: %s\n\n", wtm ? "White to Move" : "Black to Move");

    /* Αρχικοποιηση Nalimov */
    int init = IInitializeTb(path);
    if (init < 4) { printf("ERROR: init=%d (χρειαζεται >=4 για KBBK)\n", init); return 1; }
    printf("Tablebases OK (max pieces: %d)\n", init);

    unsigned long cacheSize = 64 * 1024 * 1024;  /* 64MB για 4-men */
    void *pCache = malloc(cacheSize);
    if (!pCache || !FTbSetCacheSize(pCache, cacheSize)) {
        printf("ERROR: Cache init failed\n"); return 1;
    }
    printf("Cache OK (64MB)\n\n");

    /* Sanity checks για KBBK
     * wK=e1(4), wB1=c1(2), wB2=f1(5), bK=a8(56) WTM => Win
     * (κλασικη θεση — λευκος νικα με 2 επισκοπους διαφορετικου χρωματος) */
    unsigned char board[64];

    make_board(board, 4, 2, 5, 56);  /* wK=e1, wB1=c1(λευκο), wB2=f1(μαυρο), bK=a8 */
    int sanity1 = probe_with_board(board, 1);
    printf("Test: wK=e1 wB1=c1 wB2=f1 bK=a8 WTM => %s (expected: Win)\n",
           sanity1==1?"Win":sanity1==0?"Draw":"Loss/ERROR");

    /* Θεση με ιδιο χρωμα επισκοπων => Draw */
    make_board(board, 4, 2, 16, 56); /* wK=e1, wB1=c1(λευκο), wB2=a3(λευκο), bK=a8 */
    int sanity2 = probe_with_board(board, 1);
    printf("Test: wK=e1 wB1=c1 wB2=a3 bK=a8 WTM => %s (expected: Draw - same color)\n\n",
           sanity2==0?"Draw":sanity2==1?"Win":"Loss/ERROR");

    /* Ονομα αρχειου εξοδου */
    char outfile[256];
    sprintf(outfile, "csv-arff\\kbbk_%s_raw.csv", mode_str);
    system("if not exist csv-arff mkdir csv-arff");

    FILE *fp = fopen(outfile, "w");
    if (!fp) { printf("ERROR: Cannot create %s\n", outfile); return 1; }

    /* CSV header — 4 κομματια */
    fprintf(fp, "wKSq,wB1Sq,wB2Sq,bKSq,result\n");

    int wK, wB1, wB2, bK;
    int cnt_valid=0, cnt_win=0, cnt_draw=0, cnt_skip=0;

    printf("Παραγωγη CSV (αναμενεται χρονος ~10-30 λεπτα)...\n");
    fflush(stdout);

    for (wK = 0; wK < 64; wK++) {
        for (wB1 = 0; wB1 < 64; wB1++) {
            for (wB2 = wB1+1; wB2 < 64; wB2++) { /* wB1 < wB2 παντα */
                for (bK = 0; bK < 64; bK++) {

                    /* Ελεγχος συγκρουσεων */
                    if (wK==wB1 || wK==wB2 || wK==bK) { cnt_skip++; continue; }
                    if (wB1==bK || wB2==bK)            { cnt_skip++; continue; }
                    if (dist(wK, bK) < 2)              { cnt_skip++; continue; }

                    make_board(board, wK, wB1, wB2, bK);
                    int result = probe_with_board(board, wtm);
                    if (result == -99) { cnt_skip++; continue; }

                    cnt_valid++;
                    if (result ==  1) cnt_win++;
                    if (result ==  0) cnt_draw++;

                    const char *res_str;
                    if (wtm) {
                        res_str = (result==1) ? "white" : "draw";
                    } else {
                        res_str = (result==1) ? "white" : "draw";
                    }

                    fprintf(fp, "%d,%d,%d,%d,%s\n", wK, wB1, wB2, bK, res_str);
                }
            }
        }
        /* Progress report καθε 8 wK τιμες */
        if (wK % 8 == 7) {
            printf("  Progress: wK=%d/63 (valid=%d)\n", wK, cnt_valid);
            fflush(stdout);
        }
    }
    fclose(fp);

    printf("\n=== Αποτελεσματα ===\n");
    printf("Εγκυρες θεσεις: %d\n", cnt_valid);
    printf("  Win  : %d (%.1f%%)\n", cnt_win,  cnt_valid>0?100.0*cnt_win/cnt_valid:0);
    printf("  Draw : %d (%.1f%%)\n", cnt_draw, cnt_valid>0?100.0*cnt_draw/cnt_valid:0);
    printf("Skip   : %d\n", cnt_skip);
    printf("Αρχειο : %s\n", outfile);

    /* VALIDATION */
    printf("\n=== Validation ===\n");
    int errors = 0;

    /* KBBK: περιπου 1.5-2M εγκυρες θεσεις (ολο το συνολο) */
    if (cnt_valid < 1000000) {
        printf("  [WARN] Λιγες θεσεις: %d\n", cnt_valid);
    } else {
        printf("  [OK] Θεσεις: %d\n", cnt_valid);
    }

    /* Draw% αναμενεται ~37% (sameColor = S) */
    if (cnt_valid > 0) {
        float draw_pct = 100.0f * cnt_draw / cnt_valid;
        if (draw_pct < 30.0f || draw_pct > 45.0f) {
            printf("  [WARN] Draw%%=%.1f (αναμενομενο: ~37%%)\n", draw_pct);
        } else {
            printf("  [OK] Draw%%=%.1f Win%%=%.1f\n",
                   draw_pct, 100.0f*cnt_win/cnt_valid);
        }
    }

    if (sanity1 != 1) {
        printf("  [ERROR] Sanity test 1 (different color bishops => Win)\n");
        errors++;
    } else {
        printf("  [OK] Sanity test 1 (different bishops WTM=Win)\n");
    }

    if (sanity2 != 0) {
        printf("  [ERROR] Sanity test 2 (same color bishops => Draw)\n");
        errors++;
    } else {
        printf("  [OK] Sanity test 2 (same bishops WTM=Draw)\n");
    }

    if (errors == 0)
        printf("\nValidation OK\n");
    else
        printf("\nValidation FAILED - %d σφαλματα!\n", errors);

    return (errors == 0) ? 0 : 1;
}
