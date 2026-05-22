/*
 * probe_kbbk.cpp
 * ==============
 * Βημα 1: Probe των βασεων Nalimov για KBBK.
 * Παραγει RAW CSV με θεσεις + αποτελεσμα ΜΟΝΟ.
 * ΔΕΝ υπολογιζει attributes.
 *
 * Compile:
 *   g++ probe_kbbk.cpp ..\egtb.cpp -o probe_kbbk.exe -DT_INDEX64 -DSTOP_ON_ERROR=0 -fpermissive -I..
 *
 * Usage:
 *   .\probe_kbbk.exe "C:\path\to\tablebases" [wtm/btm]
 *
 * Παραγει:
 *   kbbk_wtm_raw.csv  (white to move)  ~789,885 θεσεις
 *   kbbk_btm_raw.csv  (black to move)  ~873,642 θεσεις
 *
 * Format CSV:
 *   wKSq, wB1Sq, wB2Sq, bKSq, result
 *
 * Κανονικοποιηση (8-fold symmetry):
 *   Ο wK κανονικοποιειται στο κατω-αριστερο τριγωνο (10 canonical τετραγωνα):
 *   a1,b1,c1,d1,b2,c2,d2,c3,d3,d4
 *   Κριτηριο: file<=3, rank<=3, file<=rank
 *   Αυτο μειωνει τις θεσεις κατα ~8x vs brute force.
 *   Οι αξιωματικοι αποθηκευονται παντα με wB1 <= wB2.
 *
 * WTM illegal positions:
 *   Φιλτραρουμε θεσεις οπου ο μαυρος βασιλιας ειναι σε σαχ (παρανομες για WTM).
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
extern "C" int TB_CRC_CHECK;

/* ---- Helpers ---- */
int sq_file(int sq) { return sq % 8; }
int sq_rank(int sq) { return sq / 8; }
int mymax(int a, int b) { return a > b ? a : b; }
int myabs(int a)        { return a < 0 ? -a : a; }
int dist(int a, int b) {
    return mymax(myabs(sq_file(a)-sq_file(b)),
                 myabs(sq_rank(a)-sq_rank(b)));
}

/* ---- WTM Illegal Position Filter ---- */
bool bishop_attacks_king(int bSq, int kSq, int block1, int block2) {
    int bf = sq_file(bSq), br = sq_rank(bSq);
    int kf = sq_file(kSq), kr = sq_rank(kSq);
    int df = kf - bf, dr = kr - br;
    if (myabs(df) != myabs(dr) || df == 0) return false;
    int sf = (df > 0) ? 1 : -1;
    int sr = (dr > 0) ? 1 : -1;
    int ff = bf + sf, rr = br + sr;
    while (ff != kf || rr != kr) {
        int sq = rr * 8 + ff;
        if (sq == block1 || sq == block2) return false;
        ff += sf; rr += sr;
    }
    return true;
}

bool is_wtm_illegal(int wK, int wB1, int wB2, int bK) {
    if (bishop_attacks_king(wB1, bK, wK, wB2)) return true;
    if (bishop_attacks_king(wB2, bK, wK, wB1)) return true;
    return false;
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
        return 1;
    }

    char path[1024];
    strncpy(path, argv[1], sizeof(path)-1);

    int wtm = 1;
    if (argc >= 3 && strcmp(argv[2], "btm") == 0) wtm = 0;
    const char *mode_str = wtm ? "wtm" : "btm";

    printf("=== KBBK Probe Generator ===\n");
    printf("Path: %s\n", path);
    printf("Mode: %s (8-fold symmetry)\n\n", wtm ? "White to Move" : "Black to Move");

    int init = IInitializeTb(path);
    if (init < 4) { printf("ERROR: init=%d\n", init); return 1; }
    printf("Tablebases OK (max pieces: %d)\n", init);

    unsigned long cacheSize = 128 * 1024 * 1024;
    void *pCache = malloc(cacheSize);
    if (!pCache || !FTbSetCacheSize(pCache, cacheSize)) {
        printf("ERROR: Cache init failed\n"); return 1;
    }
    TB_CRC_CHECK = 0;
    printf("Cache OK (128MB, CRC disabled)\n\n");

    /* Sanity checks */
    unsigned char board[64];
    make_board(board, 4, 2, 5, 56);
    int sanity1 = probe_with_board(board, 1);
    printf("Test: wK=e1 wB1=c1 wB2=f1 bK=a8 WTM => %s (expected: Win)\n",
           sanity1==1?"Win":sanity1==0?"Draw":"ERROR");

    make_board(board, 4, 2, 16, 56);
    int sanity2 = probe_with_board(board, 1);
    printf("Test: wK=e1 wB1=c1 wB2=a3 bK=a8 WTM => %s (expected: Draw)\n\n",
           sanity2==0?"Draw":sanity2==1?"Win":"ERROR");

    char outfile[256];
    sprintf(outfile, "csv-arff\\kbbk_%s_raw.csv", mode_str);
    system("if not exist csv-arff mkdir csv-arff");

    FILE *fp = fopen(outfile, "w");
    if (!fp) { printf("ERROR: Cannot create %s\n", outfile); return 1; }
    fprintf(fp, "wKSq,wB1Sq,wB2Sq,bKSq,result\n");

    int wK, wB1, wB2, bK;
    int cnt_valid=0, cnt_win=0, cnt_draw=0, cnt_black=0, cnt_skip=0;
    int canonical_count = 0;

    printf("Παραγωγη CSV...\n");
    fflush(stdout);

    for (wK = 0; wK < 64; wK++) {
        int f = sq_file(wK), r = sq_rank(wK);

        /* 8-fold: κρατα μονο canonical wK (file<=3, rank<=3, file<=rank) */
        if (f > 3 || r > 3 || f > r) continue;

        canonical_count++;
        printf("  wK=%d (canonical %d/10)...\n", wK, canonical_count);
        fflush(stdout);

        for (wB1 = 0; wB1 < 64; wB1++) {
            for (wB2 = wB1+1; wB2 < 64; wB2++) {
                for (bK = 0; bK < 64; bK++) {

                    if (wK==wB1 || wK==wB2 || wK==bK) { cnt_skip++; continue; }
                    if (wB1==bK || wB2==bK)            { cnt_skip++; continue; }
                    if (dist(wK, bK) < 2)              { cnt_skip++; continue; }

                    if (wtm && is_wtm_illegal(wK, wB1, wB2, bK)) {
                        cnt_skip++; continue;
                    }

                    make_board(board, wK, wB1, wB2, bK);
                    int result = probe_with_board(board, wtm);
                    if (result == -99) { cnt_skip++; continue; }

                    cnt_valid++;
                    if (result ==  1) cnt_win++;
                    if (result ==  0) cnt_draw++;
                    if (result == -1) cnt_black++;

                    const char *res_str;
                    if (wtm) {
                        res_str = (result==1) ? "white" : "draw";
                    } else {
                        if      (result ==  1) res_str = "white";
                        else if (result == -1) res_str = "black";
                        else                   res_str = "draw";
                    }

                    fprintf(fp, "%d,%d,%d,%d,%s\n", wK, wB1, wB2, bK, res_str);
                }
            }
        }
    }
    fclose(fp);

    printf("\n=== Αποτελεσματα ===\n");
    printf("Εγκυρες θεσεις: %d\n", cnt_valid);
    printf("  White: %d (%.1f%%)\n", cnt_win,  cnt_valid>0?100.0*cnt_win/cnt_valid:0);
    printf("  Draw : %d (%.1f%%)\n", cnt_draw, cnt_valid>0?100.0*cnt_draw/cnt_valid:0);
    if (!wtm)
    printf("  Black: %d (%.1f%%)\n", cnt_black,cnt_valid>0?100.0*cnt_black/cnt_valid:0);
    printf("Skip   : %d\n", cnt_skip);
    printf("Αρχειο : %s\n", outfile);

    printf("\n=== Validation ===\n");
    int errors = 0;

    int expected = wtm ? 789885 : 873642;
    int tolerance = 10000;
    if (cnt_valid < expected - tolerance || cnt_valid > expected + tolerance) {
        printf("  [WARN] Θεσεις: %d (αναμενομενο: ~%d)\n", cnt_valid, expected);
    } else {
        printf("  [OK] Θεσεις: %d (αναμενομενο: ~%d)\n", cnt_valid, expected);
    }

    if (cnt_valid > 0) {
        float draw_pct = 100.0f * cnt_draw / cnt_valid;
        if (draw_pct < 33.0f || draw_pct > 41.0f) {
            printf("  [WARN] Draw%%=%.1f (αναμενομενο: ~37%%)\n", draw_pct);
        } else {
            printf("  [OK] Draw%%=%.1f\n", draw_pct);
        }
    }

    if (sanity1 != 1) { printf("  [ERROR] Sanity 1 failed\n"); errors++; }
    else printf("  [OK] Sanity 1 (different color bishops => Win)\n");

    if (sanity2 != 0) { printf("  [ERROR] Sanity 2 failed\n"); errors++; }
    else printf("  [OK] Sanity 2 (same color bishops => Draw)\n");

    if (errors == 0) printf("\nValidation OK\n");
    else printf("\nValidation FAILED - %d σφαλματα!\n", errors);

    return (errors == 0) ? 0 : 1;
}
