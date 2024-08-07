#!/usr/bin/sage
#-*- Python -*-
# Time-stamp: <2024-08-07 17:11:33 lperrin>


from libcpp cimport bool
from libcpp.vector cimport vector
from libcpp.map cimport map
from libcpp.string cimport string
from libc.stdint cimport uint64_t, uint8_t

cdef extern from "./sparkle.cpp":
    cdef cppclass Sparkle512EDF:
        Sparkle512EDF() except +
        void absorb(const vector[uint8_t])
        uint64_t get_n_bit_unsigned_integer(const unsigned int n)

