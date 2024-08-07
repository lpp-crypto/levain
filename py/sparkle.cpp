#include <cstdint>
#include <vector>

#define ROT(x, n) (((x) >> (n)) | ((x) << (32-(n))))
#define ELL(x) (ROT(((x) ^ ((x) << 16)), 16))

#define N_STEPS 4
#define MAX_BRANCHES 8
#define TANK_SIZE 48


extern "C" {

// Round constants
    static const uint32_t RCON[MAX_BRANCHES] = {
	0xB7E15162, 0xBF715880, 0x38B4DA56, 0x324E7738,
	0xBB1185EB, 0x4F7C7B57, 0xCFBFA1C8, 0xC2B3293D
    };

    class Sparkle512EDF {
    private:
	// the number of SPARKLE rounds to make each time
	unsigned int steps;
	// the state updated by the SPARKLE permutation
	uint32_t state[2*MAX_BRANCHES] ;
	// a vector of bytes containing a copy of the data in the rate
	uint8_t entropy_tank[TANK_SIZE];
	// the position of the byte in the entropy_tank we plan to grab
	unsigned int entropy_cursor;

    public:

	// !SUBSECTION! Python facing functions 
	Sparkle512EDF() :
	    steps(N_STEPS),
	    entropy_cursor(0)
	{
	    for(unsigned int i=0; i<2*MAX_BRANCHES; i++)
		state[i] = 0;
	    for(unsigned int i=0; i<TANK_SIZE; i++)
		entropy_tank[i] = 0;
	};

	
	void absorb(const std::vector<uint8_t> byte_array)
	// the length of `byte_array` must be a multiple of 4
	{
	    for(unsigned int i=0; i<byte_array.size(); i+=4)
		for(unsigned int j=0; j<4; j++)
		    state[i >> 2] ^= ((uint32_t)byte_array[i + j]) << (8*j) ;
	    _update_state();
	};


	uint64_t get_n_bit_unsigned_integer(const unsigned int n)
	{
	    uint64_t
		result = 0,
		n_bit_mask = ((uint64_t)1 << n) - 1 ;
	    // taking full bytes one by one
	    for(unsigned int i=0; i<=(n >> 3); i++)
		result = (result << 8) | _get_byte() ;
	    return result & n_bit_mask;
	}

	
	// !SUBSECTION! Inner routines 

	uint8_t _get_byte()
	{
	    if (entropy_cursor >= TANK_SIZE)
		_update_state();
	    uint8_t result = entropy_tank[entropy_cursor];
	    entropy_cursor ++;
	    return result;
	}
	
	void _update_state()
	{
	    unsigned int i, j;  // Step and branch counter
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

	    // updating the entropy_tank byte array
	    for (i=0; i<TANK_SIZE; i+=4)
		for(j=0; j<4; j++)
		    entropy_tank[i+j] = (state[i >> 2] >> (j*8)) & 0xFF;
	    entropy_cursor = 0;
	}
    };
}
