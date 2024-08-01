#!/usr/bin/sage
#-*- Python -*-
# Time-stamp: <2024-08-01 16:32:37 lperrin>

import os
from cpython_declaration cimport *

def our_print(to_print):
    cpp_print(to_print)
