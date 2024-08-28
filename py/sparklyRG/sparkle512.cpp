#include "sparkle512.hpp"

Sparkle512core::Sparkle512core():
    steps(0),
    state{{0}},
    entropy_tank(0, false),
    entropy_cursor(0) {}

void Sparkle512core::setup(const unsigned int _steps, const unsigned int _output_rate)
{
    steps = _steps;
    entropy_tank.assign(_output_rate, false);
}

void Sparkle512core::_permute()
{
    unsigned int i, j;  // Step and branch counter
    uint32_t rc, tmpx, tmpy, x0, y0;
  
    for(i = 0; i < steps; i ++) {
        // Add round constant
        state[1] ^= RCON[i % N_BRANCHES];
        state[3] ^= i;
        // ARXBOX layer
        for(j = 0; j < 2*N_BRANCHES; j += 2) {
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
        for(j = 2; j < N_BRANCHES; j += 2) {
            tmpx ^= state[j];
            tmpy ^= state[j+1];
        }
        tmpx = ELL(tmpx);
        tmpy = ELL(tmpy);
        for (j = 2; j < N_BRANCHES; j += 2) {
            state[j-2] = state[j+N_BRANCHES] ^ state[j] ^ tmpy;
            state[j+N_BRANCHES] = state[j];
            state[j-1] = state[j+N_BRANCHES+1] ^ state[j+1] ^ tmpx;
            state[j+N_BRANCHES+1] = state[j+1];
        }
        state[N_BRANCHES-2] = state[N_BRANCHES] ^ x0 ^ tmpy;
        state[N_BRANCHES] = x0;
        state[N_BRANCHES-1] = state[N_BRANCHES+1] ^ y0 ^ tmpx;
        state[N_BRANCHES+1] = y0;
    }
}

void Sparkle512core::_squeeze()
{
    uint32_t tmp;
    for (unsigned int i=0; i<entropy_tank.size(); i += 32)
    {
        unsigned int k = i / 32; 
        tmp = state[k]; 
        for(unsigned int j=0; j<32; j++)
            entropy_tank[i+j] = (__builtin_parityll(state[k] >> j));
    }
    entropy_cursor = 0;
}

void Sparkle512core::absorb(const std::vector<uint8_t> byte_array)
{
    state[2*N_BRANCHES-1] ^= 1;
    for(unsigned int i=0; i<byte_array.size(); i+=4)
    {
        for(unsigned int j=0; j<4; j++)
            state[i >> 2] ^= ((uint32_t)byte_array[i + j]) << (8*j) ;
    }
    _permute();
    state[2*N_BRANCHES-1] ^= 2;
    _permute();
    _squeeze();
}

uint64_t Sparkle512core::get_n_bit_unsigned_integer(const unsigned int n)
{
    uint64_t result = 0;
    for (unsigned int i=0; i<n; i ++)
    {
        if (entropy_cursor == entropy_tank.size())
        {
            _permute();
            _squeeze();
        }
        if (entropy_tank[entropy_cursor])
            result |= (1 << i);
        entropy_cursor ++;
    }
    return result;
}

uint64_t Sparkle512core::get_unsigned_integer_in_range(
    const uint64_t lower_bound,
    const uint64_t upper_bound)
{
    uint64_t
        bit_length = 64 - __builtin_clzll(upper_bound - lower_bound),
        range = upper_bound - lower_bound,
        output ;
    do
    {
        output = get_n_bit_unsigned_integer(bit_length);
    } while (output >= range) ;
    return lower_bound + output;    
}
