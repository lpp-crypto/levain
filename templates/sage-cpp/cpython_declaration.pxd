#!/usr/bin/sage
#-*- Python -*-
# Time-stamp: <2024-08-01 16:31:14 lperrin>


from libcpp cimport bool
from libcpp.vector cimport vector
from libcpp.map cimport map
from libcpp.string cimport string
from libc.stdint cimport int64_t, uint64_t

cdef extern from "cpp_source.cpp":
    cdef void cpp_print(const string to_print)
