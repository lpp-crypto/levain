#include<vector>
#include<cstdint>
#include<array>

#define ROT(x, n) (((x) >> (n)) | ((x) << (32-(n))))
#define ELL(x) (ROT(((x) ^ ((x) << 16)), 16))

#define N_BRANCHES 8

static const uint32_t RCON[N_BRANCHES] = {
    0xB7E15162, 0xBF715880, 0x38B4DA56, 0x324E7738,
        0xBB1185EB, 0x4F7C7B57, 0xCFBFA1C8, 0xC2B3293D
        };

class Sparkle512core {
private:
    unsigned int steps;
    std::array<uint32_t, 2*N_BRANCHES> state;
    std::vector<bool> entropy_tank;
    unsigned int entropy_cursor;
    public:
    Sparkle512core();
    void setup(const unsigned int _steps, const unsigned int _output_rate);
    void absorb(const std::vector<uint8_t> byte_array);
    uint64_t get_n_bit_unsigned_integer(const unsigned int n);
    uint64_t get_unsigned_integer_in_range(const uint64_t lower_bound,
                                           const uint64_t upper_bound);
    
    void _squeeze();
    void _permute();
};
