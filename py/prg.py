#!/usr/bin/python3
#-*- Python -*-
# Time-stamp: <2024-08-07 15:06:22 lperrin>


import hashlib
import time
import os
import ctypes

from math import log, ceil
from copy import copy


class SimplifiedSparkle512:
    def __init__(self, n_rounds=4):
        self.perm = ctypes.CDLL('./sparkle.so').sparkle_512_permutation
        zeroes = [ctypes.c_uint32(0)]*16
        self.state = (ctypes.c_uint32 * 16)(*zeroes)
        self.n_rounds = n_rounds
        self.rate = 32          # eight 32-bit words, so 32 bytes

    def absorb(self, x):
        if len(x) >= self.rate:
            raise Exception("Trying to absorb too big a chunk")
        x += bytearray([0] * (self.rate - len(x))) # padding with 0
        for i in range(0, len(x) >> 2):
            y_i = 0
            for j in range(0, 4):
                y_i = (y_i << 8) | x[4*i + j]
            self.state[i] = self.state[i] ^ y_i
        self.iterate()

    def iterate(self):
        self.state = (ctypes.c_uint32 * 16)(*self.state)
        self.perm(self.state, self.n_rounds)
        
    def squeeze(self):
        result = []
        for x in self.state:
            x_i = x
            for i in range(0, 4):
                result.append(x_i & 0xFF)
                x_i = x_i >> 8
        return result
        



# !TODO! rewrite documentation to use SPARKLE instead of SHA512

# !TODO! write a dedicated C++ class called SPARKLE_EDF, and let
# !ReproduciblePRG be a simple wrapper for it.

# !TODO! allow outputting random functions and random permutations 

class ReproduciblePRG:
    """A simple pseudo random number generator based on hashing an
    increasing counter using SHA512, the state of the hash function
    being initialized with the seed.

    """
    def __init__(self, seed):
        """We initialize the state of a SHA512 instance with the given
        seed. This is a deterministic procedure.

        The hash function can be specified using the
        `hash_state`. SHA512 was experimentally found to yield
        marginally faster ReproduciblePRG instances.

        """
        self.state = SimplifiedSparkle512(n_rounds=4)
        self.seed = []
        self.reseed(seed)
        self.masks = [int(1 << i)-1 for i in range(0, 8)]

    def reseed(self, seed):
        self.entropy_reserve = []
        self.cursor = 2**30
        if isinstance(seed, list):
            self.seed += seed
            for x in seed:
                self.state.absorb(x)
        else:
            self.seed.append(seed)
            self.state.absorb(seed)
        

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
    

    def _get_next_byte(self):
        """An inner routine returning a single pseudo-random byte.

        Either pops such a byte from the self.entropy_reserve, or if
        its empty then:

        1. increases the internal counter,

        2. copies the main state, absorbs the new counter, and sets
        the new self.entropy_reserve to be the digest obtained.

        """
        if self.cursor >= len(self.entropy_reserve):
            # if the content is empty, we update the state
            self.state.iterate()
            self.entropy_reserve = self.state.squeeze()
            self.cursor = 0
        output = self.entropy_reserve[self.cursor]
        self.cursor += 1
        return output
        
        
        
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
        reachable_bound = 1
        alea = 0
        value_range = int(upper_bound - lower_bound)
        n_bits = ceil(log(value_range, 2))
        while n_bits >= 8:
            alea = int((alea << 8) | self._get_next_byte())
            n_bits -= 8
        alea = (alea << n_bits) | (self._get_next_byte() & self.masks[n_bits])
        potential_output = lower_bound + alea
        # rejection sampling
        if potential_output < upper_bound:
            return potential_output
        else:
            return self(lower_bound=lower_bound,
                        upper_bound=upper_bound)


    def __str__(self):
        return "ReproduciblePRG using SPARKLE512 with {} rounds and seeded with {}".format(
            self.state.n_rounds,
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

    # with LogBook("ctypes for sparkle",
    #              title="Playing with ctypes",
    #              with_final_results=False) as lgbk:
    #     sparkle = ctypes.CDLL('./sparkle.so')
    #     lgbk.log_event(sparkle)
    #     lgbk.log_event(dir(sparkle))
    #     zeroes = [0]*16
    #     state = (ctypes.c_uint32 * 16)(*zeroes)
    #     lgbk.log_event({"before" : state})
    #     sparkle.sparkle_512_permutation(state, 3)
    #     lgbk.log_event({"after " : state})
    #     for x in state:
    #         lgbk.log_result("{:08x}".format(x))
        

    test_speed_and_bounds()
