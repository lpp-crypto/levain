#!/usr/bin/sage
#-*- Python -*-
# Time-stamp: <2024-08-07 17:43:50 lperrin>


import hashlib
import time
import os
import ctypes

from math import log, ceil
from copy import copy

from cpputils import *


# !TODO! rewrite documentation to take into account the move to SPARKLE512

# !TODO! allow outputting random functions and random permutations 

class ReproduciblePRG:
    """A simple pseudo random number generator based on a simplified
    version of SPARKLE512 (fewer rounds, bigger rate).

    """
    def __init__(self, seed):
        """Initializing the SPARKLE-based PRNG

        """
        self.edf = PySparkle512EDF()
        self.seed = []
        self.reseed(seed)

    def reseed(self, seed):
        if isinstance(seed, list):
            self.seed += seed
            for x in seed:
                self.edf.absorb(x)
        else:
            self.seed.append(seed)
            self.edf.absorb(seed)
        

    def reseed_from_time_and_pid(self):
        """Reseeds the internal state of the cipher by updating the
        state using the string representations of the current UNIX
        time and of the pid of the program.

        Returns the list of strings that have been absorbed into the
        state.

        Obviously shouldn't used to generate cryptographic keys.

        """
        blocks = [
            str(time.time()).encode("UTF-8"),        # machine time
            int(os.getpid()).to_bytes(16, "little")  # PID of the
                                                     # current program
        ]
        self.reseed(blocks)
        return blocks
        
        
    def __call__(self,
                 lower_bound=0,
                 upper_bound=2**32):
        """Returns an output `d` such that lower_bound <= d <
        upper_bound (like `range`).

        We use rejection sampling, so if the value range
        (upper_bound-lower_bound) is just above a power of 2 then we
        might need to recursively call this function up to twice on
        average before actually getting a valid output.

        """
        if lower_bound >= upper_bound:
            raise Exception(
                "upper_bound ({}) must be higher than lower_bound ({}).".format(
                    upper_bound,
                    lower_bound
                ))
        value_range = upper_bound - lower_bound
        bit_length = ceil(log(value_range, 2))
        alea = self.edf.get_n_bit_unsigned_integer(bit_length)
        potential_output = lower_bound + alea
        # rejection sampling
        if potential_output < upper_bound:
            return potential_output
        else:
            return self(lower_bound=lower_bound,
                        upper_bound=upper_bound)


    def __str__(self):
        return "ReproduciblePRG using simplified SPARKLE512 seeded with {}".format(
            self.seed
        )


# !SECTION! Tests
# ===============


def test_speed_and_bounds():
    with LogBook("prg_test_sparkle",
                 title="Testing ReproduciblePRG",
                 with_final_results=False) as lgbk:
        prg = ReproduciblePRG([b"blabli", b"blu"])
        lgbk.log_event("Succesfull initialization")
        lgbk.log_event(prg)
        s = 0
        success_counter = 0

        # import random
        # prg = random.randint
        
        for i in range(1, 2**15):
            lower = i
            upper = prg(2**20, 2**40) + prg(0, 100)
            # lower = 0 + prg(0, 256)
            # upper = 2**20 - prg(0, 256)
            r = [
                prg(lower, upper)
                for j in range(0, 10)
            ]
            for x in r:
                if x < lower or x >= upper:
                    lgbk.log_fail("{} not in [{}, {}]".format(
                        x,
                        lower,
                        upper
                    ))
                else:
                    success_counter += 1
            s += r[0]
        lgbk.log_result(s % 1000)
        lgbk.log_result({"successes" : success_counter})


if __name__ == "__main__":
    from logbook import LogBook

    # with LogBook("logbooks/replicability",
    #              title="Testing Replicability of CYTHON/SPARKLE-based PRNG",
    #              with_final_results=False) as lgbk:
    #     for run in [0, 1]:
    #         lgbk.section(1, "run {}".format(run))
    #         sp = PySparkle512EDF()
    #         lgbk.log_event("successful instantiation")
    #         sp.absorb(b"1")
    #         lgbk.log_event("successful absorption")
    #         for i in range(3, 45):
    #             lgbk.log_result(hex(sp.get_n_bit_unsigned_integer(i)))
        

    test_speed_and_bounds()
