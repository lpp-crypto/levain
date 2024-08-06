#!/usr/bin/python3
#-*- Python -*-
# Time-stamp: <2024-08-06 17:12:42 lperrin>


import hashlib
import time
import os

from math import log, ceil




class ReproduciblePRG:
    """A simple pseudo random number generator based on hashing an
    increasing counter using SHA256, the state of the hash function
    being initialized with the seed.

    """
    def __init__(self, seed, hash_state=hashlib.sha512):
        """We initialize the state of a SHA512 instance with the given
        seed. This is a deterministic procedure.

        The hash function can be specified using the
        `hash_state`. SHA512 was experimentally found to yield
        marginally faster ReproduciblePRG instances.

        """
        self.state = hash_state()
        self.reseed(seed)
        self.masks = [int(1 << i)-1 for i in range(0, 8)]

    def reseed(self, seed):
        self.counter = 0
        self.entropy_reserve = []
        self.cursor = 2**30
        self.seed = seed
        if isinstance(seed, list):
            for x in seed:
                self.state.update(x)
        else:
            self.state.update(seed)
        

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
            # if the content is empty, we absorb a new counter
            self.counter += 1
            tmp = self.state.copy()
            tmp.update(self.counter.to_bytes(16, "little"))
            self.entropy_reserve = tmp.digest()
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
        return "ReproduciblePRG using {} and seeded with {}".format(
            self.state.name,
            self.seed
        )


if __name__ == "__main__":
    from logbook import LogBook

    
    with LogBook("prg_test_sha256",
                 title="Testing ReproduciblePRG",
                 with_final_results=False) as lgbk:
        prg = ReproduciblePRG([b"blabli", b"blu"],
                              hash_state=hashlib.sha512)
        lgbk.log_event("Succesfull initialization")
        lgbk.log_event(prg)
        s = 0
        success_counter = 0
        for i in range(1, 2**15):
            lower = i
            upper = prg(2**20, 2**40) + prg(100)
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
