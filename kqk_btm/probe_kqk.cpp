/*
 * probe_kqk.cpp
 * =============
 * Βημα 1: Probe των βασεων Nalimov για KQK.
 * Παραγει RAW CSV με θεσεις + αποτελεσμα ΜΟΝΟ.
 * ΔΕΝ υπολογιζει attributes.
 *
 * Compile:
 *   g++ probe_kqk.cpp ..\egtb.cpp -o probe_kqk.exe -DT_INDEX64 -fpermissive -I..
 *
 * Usage:
 *   .\probe_kqk.exe "C:\path\to\tablebases" [wtm/btm]
 *
 * Παραγει:
 *   kqk_wtm_raw.csv  (white to move — trivial, παντα win)
 *   kqk_btm_raw.csv  (black to move — εχει draw λογω stalemate)
 *
 * Format CSV:
 *   wKSq, wQSq, bKSq, result
 *
 * Το wKSq/wQSq/bKSq ειναι οι αριθμοι τετραγωνου (0-63).
 * Ολα τα attributes υπολογιζονται στο add_attributes.py.
 *
 * Σημειωση: KQK WTM παραλειπεται απο τον Θανου (2012) γιατι
 * ποτε δεν καταληγει σε ισοπαλια. Εμεις υλοποιουμε BTM.
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
            case 'Q': rgsqWhite[4*C_PIECES + rgiCounters[4]++] = sq; break;
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

void make_board(unsigned char board[64], int wK, int wQ, int bK) {
    memset(board, 0, 64);
    board[wK] = 'K';
    board[wQ] = 'Q';
    board[bK] = 'k';
}

/* ---- Main ---- */
int main(int argc, char *argv[]) {
    if (argc < 2) {
        printf("Usage: %s <path> [wtm/btm]\n", argv[0]);
        printf("  wtm = white to move\n");
        printf("  btm = black to move (default για KQK)\n");
        return 1;
    }

    char path[1024];
    strncpy(path, argv[1], sizeof(path)-1);

    int wtm = 1;
    if (argc >= 3 && strcmp(argv[2], "btm") == 0) wtm = 0;

    const char *mode_str = wtm ? "wtm" : "btm";

    printf("=== KQK Probe Generator ===\n");
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

    /* Sanity checks για KQK BTM
     * wK=e1(4), wQ=d1(3), bK=a8(56) BTM => White wins
     * wK=a1(0), wQ=c3(18), bK=a8(56) BTM => Stalemate (draw) */
    unsigned char board[64];

    make_board(board, 4, 3, 56);   /* wK=e1, wQ=d1, bK=a8 */
    int sanity1 = probe_with_board(board, wtm);
    printf("Test: wK=e1 wQ=d1 bK=a8 %s => %s (expected: Win)\n",
           wtm?"WTM":"BTM",
           sanity1==1?"Win":sanity1==0?"Draw":"Loss/ERROR");

    make_board(board, 4, 3, 58);   /* wK=e1, wQ=d1, bK=c8 */
    int sanity2 = probe_with_board(board, wtm);
    printf("Test: wK=e1 wQ=d1 bK=c8 %s => %s (expected: Win)\n\n",
           wtm?"WTM":"BTM",
           sanity2==1?"Win":sanity2==0?"Draw":"Loss/ERROR");

    /* Ονομα αρχειου εξοδου */
    char outfile[256];
    sprintf(outfile, "csv-arff\\kqk_%s_raw.csv", mode_str);

    system("if not exist csv-arff mkdir csv-arff");

    FILE *fp = fopen(outfile, "w");
    if (!fp) { printf("ERROR: Cannot create %s\n", outfile); return 1; }

    /* CSV header */
    fprintf(fp, "wKSq,wQSq,bKSq,result\n");

    int wK, wQ, bK;
    int cnt_valid=0, cnt_win=0, cnt_draw=0, cnt_loss=0, cnt_skip=0;

    /* Βασιλισσα: ολα τα τετραγωνα 0-63 */
    for (wK = 0; wK < 64; wK++) {
        for (wQ = 0; wQ < 64; wQ++) {
            for (bK = 0; bK < 64; bK++) {

                if (wK==wQ || wK==bK || wQ==bK) { cnt_skip++; continue; }
                if (dist(wK, bK) < 2)            { cnt_skip++; continue; }

                make_board(board, wK, wQ, bK);
                int result = probe_with_board(board, wtm);
                if (result == -99) { cnt_skip++; continue; }

                cnt_valid++;
                if (result ==  1) cnt_win++;
                if (result ==  0) cnt_draw++;
                if (result == -1) cnt_loss++;

                const char *res_str;
                if (wtm) {
                    res_str = (result==1) ? "white" :
                              (result==0) ? "draw"  : "black";
                } else {
                    /* BTM: result=1 = λευκος νικα */
                    res_str = (result==1)  ? "white" :
                              (result==0)  ? "draw"  : "black";
                }

                fprintf(fp, "%d,%d,%d,%s\n", wK, wQ, bK, res_str);
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

    /* VALIDATION */
    printf("\n=== Validation ===\n");
    int errors = 0;

    /* KQK BTM: Θανου εχει 223.944 θεσεις */
    if (!wtm) {
        int expected = 223944;
        if (cnt_valid != expected) {
            printf("  [WARN] Θεσεις: %d (Θανου ειχε: %d)\n", cnt_valid, expected);
        } else {
            printf("  [OK] Θεσεις: %d\n", cnt_valid);
        }
        /* Win% BTM: αναμενεται >95% */
        float win_pct = 100.0f * cnt_win / cnt_valid;
        if (win_pct < 90.0f) {
            printf("  [WARN] Win%%=%.1f (αναμενομενο: >90%%)\n", win_pct);
        } else {
            printf("  [OK] Win%%=%.1f Draw%%=%.1f\n",
                   win_pct, 100.0f*cnt_draw/cnt_valid);
        }
    }

    /* Sanity tests */
    if (sanity1 != 1) {
        printf("  [ERROR] Sanity test 1 απετυχε (αναμενομενο: Win)\n");
        errors++;
    } else {
        printf("  [OK] Sanity test 1 (e1/d1/a8 => Win)\n");
    }

    if (sanity2 != 1) {
        printf("  [ERROR] Sanity test 2 απετυχε (αναμενομενο: Win)\n");
        errors++;
    } else {
        printf("  [OK] Sanity test 2 (e1/d1/c8 => Win)\n");
    }

    if (errors == 0)
        printf("\nValidation OK - το CSV ειναι ορθο.\n");
    else
        printf("\nValidation FAILED - %d σφαλματα!\n", errors);

    return (errors == 0) ? 0 : 1;
}
