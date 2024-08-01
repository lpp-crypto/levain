#!/usr/bin/sage
# -*- Python -*-


from sage.all import *

from sys import argv
import os

from mylib import *



"""Files in this folder:

- `script.py` (this file) is the master script, intended to call both
  SAGE and C++ routines.

- `cpp_source.cpp` which contains the C++ source code of the
  subroutines implemented in that language.

- `mylib.pyx` which wraps all the cpython logic away in a way that
  can be imported directly from SAGE

- `cpython_declaration.pxd` describes the interface of the C++
  functions in python terms.

- `setup.py` describes how the C++ code should be compiled.


To compile the C++ part, use `sage setup.py build_ext --inplace`.

/!\ Do NOT call the c++ source file `mylib.cpp`: during compilation,
    SAGE creates its own file called `mylib.cpp`, and would erase it
    in the process!

"""

# !SECTION! Main program 

if __name__ == "__main__":
    if len(argv) < 2:
        print("needs at least one argument")
    else:
        our_print(argv[1].encode("ascii"))
