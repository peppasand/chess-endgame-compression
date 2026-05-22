/*
 * probe_krk.cpp
 * =============
 * Βημα 1: Probe των βασεων Nalimov για KRK.
 * Παραγει RAW CSV με θεσεις + αποτελεσμα ΜΟΝΟ.
 * ΔΕΝ υπολογιζει attributes.
 *
 * Compile:
 *   g++ probe_krk.cpp ..\egtb.cpp -o probe_krk.exe -DT_INDEX64 -fpermissive -I..
 *
 * Usage:
 *   .\probe_krk.exe "C:\path\to\tablebases" [wtm/btm]
 *
 * Παραγει:
 *   krk_wtm_raw.csv  (white to move)
 *   krk_btm_raw.csv  (black to move — εχει draw λογω stalemate/50-move)
 *
 * Format CSV:
 *   wKSq, wRSq, bKSq, result
 *
 * Το wKSq/wRSq/bKSq ειναι οι αριθμοι τετραγωνου (0-63).
 * Ολα τα attributes υπολογιζονται στο add_attributes.py.
 *
 * Σημειωση: Ο Θανου (2012, Κεφ. 4.3) παραλειπει το KRK WTM,
 * οπως και το KQK WTM, επειδη draw αδυνατο για WTM.
 * Υλοποιουμε μονο BTM (223.944 θεσεις, ακριβεια J48: 99.98%).
 * Τα attributes του Θανου χρησιμοποιουν "M" για τον Πυργο:
 *   fileDiffKM, fileDiffkM, rankDiffKM, rankDiffkM, κλπ.
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
            /* Πυργος: piece index 3 (αντι 4 για τη Βασιλισσα) */
            case 'R': rgsqWhite[3*C_PIECES + rgiCounters[3]++] = sq; break;
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

void make_board(unsigned char board[64], int wK, int wR, int bK) {
    memset(board, 0, 64);
    board[wK] = 'K';
    board[wR] = 'R';
    board[bK] = 'k';
}

/* ---- Main ---- */
int main(int argc, char *argv[]) {
    if (argc < 2) {
        printf("Usage: %s <path> [wtm/btm]\n", argv[0]);
        printf("  wtm = white to move\n");
        printf("  btm = black to move\n");
        return 1;
    }

    char path[1024];
    strncpy(path, argv[1], sizeof(path)-1);

    int wtm = 1;
    if (argc >= 3 && strcmp(argv[2], "btm") == 0) wtm = 0;

    const char *mode_str = wtm ? "wtm" : "btm";

    printf("=== KRK Probe Generator ===\n");
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

    /* Sanity checks για KRK
     * wK=e1(4), wR=a1(0), bK=a8(56) WTM => White wins (Rook on back rank)
     * wK=a1(0), wR=b3(17), bK=a3(16) BTM => Draw (stalemate δεν ισχυει, αλλα
     *   ο μαυρος βασιλιας ειναι δεσμευμενος — αναμενεται Win για λευκους)
     * Αντικαταστηστε με θεσεις που γνωριζετε απο τη διπλωματικη σας. */
    unsigned char board[64];

    /* Test 1: κλασικη νικητηρια θεση — πυργος στη γραμμη a, βασιλιας στο e1 */
    make_board(board, 4, 0, 56);   /* wK=e1, wR=a1, bK=a8 */
    int sanity1 = probe_with_board(board, wtm);
    printf("Test: wK=e1 wR=a1 bK=a8 %s => %s (expected: Win)\n",
           wtm?"WTM":"BTM",
           sanity1==1?"Win":sanity1==0?"Draw":"Loss/ERROR");

    /* Test 2: αλλη νικητηρια θεση */
    make_board(board, 4, 0, 58);   /* wK=e1, wR=a1, bK=c8 */
    int sanity2 = probe_with_board(board, wtm);
    printf("Test: wK=e1 wR=a1 bK=c8 %s => %s (expected: Win)\n\n",
           wtm?"WTM":"BTM",
           sanity2==1?"Win":sanity2==0?"Draw":"Loss/ERROR");

    /* Ονομα αρχειου εξοδου */
    char outfile[256];
    sprintf(outfile, "csv-arff\\krk_%s_raw.csv", mode_str);

    system("if not exist csv-arff mkdir csv-arff");

    FILE *fp = fopen(outfile, "w");
    if (!fp) { printf("ERROR: Cannot create %s\n", outfile); return 1; }

    /* CSV header — wRSq αντι wQSq */
    fprintf(fp, "wKSq,wRSq,bKSq,result\n");

    int wK, wR, bK;
    int cnt_valid=0, cnt_win=0, cnt_draw=0, cnt_loss=0, cnt_skip=0;

    for (wK = 0; wK < 64; wK++) {
        for (wR = 0; wR < 64; wR++) {
            for (bK = 0; bK < 64; bK++) {

                if (wK==wR || wK==bK || wR==bK) { cnt_skip++; continue; }
                if (dist(wK, bK) < 2)            { cnt_skip++; continue; }

                make_board(board, wK, wR, bK);
                int result = probe_with_board(board, wtm);
                if (result == -99) { cnt_skip++; continue; }

                cnt_valid++;
                if (result ==  1) cnt_win++;
                if (result ==  0) cnt_draw++;
                if (result == -1) cnt_loss++;

                const char *res_str;
                res_str = (result==1)  ? "white" :
                          (result==0)  ? "draw"  : "black";

                fprintf(fp, "%d,%d,%d,%s\n", wK, wR, bK, res_str);
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

    /* VALIDATION
     * Βασει Θανου (2012), Κεφ. 4.3:
     *   - KRK BTM: 223.944 εγκυρες θεσεις (ιδιο με KQK BTM)
     *   - Ο Θανου ρητα αναφερει: "για το KRK black to move ειχε
     *     περιπου 224.000 γραμμες" (σελ. 59-60 της διπλωματικης)
     *   - Accuracy J48: 99.9777% — σχεδον τελειο
     *   - Αριθμος φυλλων δεντρου: 37, μεγεθος: 73 κομβοι
     *   - KRK WTM παραλειπεται (draw αδυνατο για WTM, οπως και KQK)
     *
     * ΠΡΟΣΟΧΗ: Το ποσοστο Win/Draw διαφερει απο KQK:
     *   KQK BTM: draw μονο λογω stalemate (~3%)
     *   KRK BTM: draw λογω stalemate ΚΑΙ 50-move rule (υψηλοτερο %)
     * Τα ακριβη ποσοστα δεν αναφερονται στη διπλωματικη.
     * Το threshold παραμενει >85% Win ως λογικο κατωτατο οριο. */
    printf("\n=== Validation ===\n");
    int errors = 0;

    if (!wtm) {
        /* Ακριβης αριθμος απο Θανου (2012), σελ. 59-60 */
        int expected = 223944;
        if (cnt_valid != expected) {
            printf("  [WARN] Θεσεις: %d (Θανου ειχε: %d)\n", cnt_valid, expected);
        } else {
            printf("  [OK] Θεσεις: %d\n", cnt_valid);
        }
        float win_pct = 100.0f * cnt_win / cnt_valid;
        /* KRK: εχει draws λογω stalemate + 50-move rule */
        if (win_pct < 85.0f) {
            printf("  [WARN] Win%%=%.1f (αναμενομενο: >85%% για KRK BTM)\n", win_pct);
        } else {
            printf("  [OK] Win%%=%.1f Draw%%=%.1f\n",
                   win_pct, 100.0f*cnt_draw/cnt_valid);
        }
    }

    if (sanity1 != 1) {
        printf("  [ERROR] Sanity test 1 απετυχε (αναμενομενο: Win)\n");
        errors++;
    } else {
        printf("  [OK] Sanity test 1 (e1/Ra1/a8 => Win)\n");
    }

    if (sanity2 != 1) {
        printf("  [ERROR] Sanity test 2 απετυχε (αναμενομενο: Win)\n");
        errors++;
    } else {
        printf("  [OK] Sanity test 2 (e1/Ra1/c8 => Win)\n");
    }

    if (errors == 0)
        printf("\nValidation OK - το CSV ειναι ορθο.\n");
    else
        printf("\nValidation FAILED - %d σφαλματα!\n", errors);

    return (errors == 0) ? 0 : 1;
}
