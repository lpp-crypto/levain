#include <stdint.h>

#define ROT(x, n) (((x) >> (n)) | ((x) << (32-(n))))
#define ELL(x) (ROT(((x) ^ ((x) << 16)), 16))

#define MAX_BRANCHES 8


extern "C" {

// Round constants
static const uint32_t RCON[MAX_BRANCHES] = {    \
    0xB7E15162, 0xBF715880, 0x38B4DA56, 0x324E7738, \
    0xBB1185EB, 0x4F7C7B57, 0xCFBFA1C8, 0xC2B3293D  \
};


void sparkle_512_permutation(uint32_t * state, int steps)
{
    int i, j;  // Step and branch counter
    uint32_t rc, tmpx, tmpy, x0, y0, brans=8;

    for(i = 0; i < steps; i ++)
	{
        // Add round constant
        state[1] ^= RCON[i%MAX_BRANCHES];
        state[3] ^= i;
         // ARXBOX layer
        for(j = 0; j < 2*brans; j += 2)
	    {
            rc = RCON[j>>1];
            state[j] += ROT(state[j+1], 31);
            state[j+1] ^= ROT(state[j], 24);
            state[j] ^= rc;
            state[j] += ROT(state[j+1], 17);
            state[j+1] ^= ROT(state[j], 17);
            state[j] ^= rc;
            state[j] += state[j+1];
            state[j+1] ^= ROT(state[j], 31);
            state[j] ^= rc;
            state[j] += ROT(state[j+1], 24);
            state[j+1] ^= ROT(state[j], 16);
            state[j] ^= rc;
        }
        // Linear layer
        tmpx = x0 = state[0];
        tmpy = y0 = state[1];
        for(j = 2; j < brans; j += 2)
	    {
            tmpx ^= state[j];
            tmpy ^= state[j+1];
        }
        tmpx = ELL(tmpx);
        tmpy = ELL(tmpy);
        for (j = 2; j < brans; j += 2) {
            state[j-2] = state[j+brans] ^ state[j] ^ tmpy;
            state[j+brans] = state[j];
            state[j-1] = state[j+brans+1] ^ state[j+1] ^ tmpx;
            state[j+brans+1] = state[j+1];
        }
        state[brans-2] = state[brans] ^ x0 ^ tmpy;
        state[brans] = x0;
        state[brans-1] = state[brans+1] ^ y0 ^ tmpx;
        state[brans+1] = y0;
    }
}
}
