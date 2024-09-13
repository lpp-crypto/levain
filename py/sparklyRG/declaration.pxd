from libcpp.vector cimport vector
from libc.stdint cimport uint64_t, uint8_t

cdef extern from "./sparkle512.cpp":
    cdef cppclass Sparkle512core:
        Sparkle512core() except +
        void setup(const unsigned int steps, const unsigned int)
        void absorb(const vector[uint8_t])
        uint64_t get_n_bit_unsigned_integer(const unsigned int n)
        uint64_t get_unsigned_integer_in_range(const uint64_t lower,
                                               const uint64_t upper)
