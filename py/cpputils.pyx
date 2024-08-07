#!/usr/bin/sage
#-*- Python -*-
# Time-stamp: <2024-08-07 17:32:23 lperrin>
# distutils: language = c++

import os
from cpputils_declaration cimport *



cdef class PySparkle512EDF:
    cdef Sparkle512EDF edf
    
    def __init__(self):
        self.edf = Sparkle512EDF()

    def absorb(self, x):
        to_absorb = x + bytearray([0] * (48 - len(x)))
        self.edf.absorb(to_absorb)

    def get_n_bit_unsigned_integer(self, n):
        return self.edf.get_n_bit_unsigned_integer(n)

