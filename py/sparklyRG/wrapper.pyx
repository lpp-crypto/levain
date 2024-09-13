from declaration cimport *

cdef class SparkleRG:
    cdef Sparkle512core core
    steps: uint64_t
    output_rate: uint64_t 
    
    def __init__(self, steps, output_rate):
        self.core = Sparkle512core()
        self.steps = steps
        self.output_rate = output_rate
        self.core.setup(self.steps, self.output_rate)


    def absorb(self, x):
        # handling padding
        to_absorb = x + bytearray([0] * (48 - len(x)))
        self.core.absorb(to_absorb)


    def get_n_bit_unsigned_integer(self, n):
        if n > 64:
            raise Exception("Cannot return integers more than 64-bit long")
        return self.core.get_n_bit_unsigned_integer(n)

    def __call__(self, lower, upper):
        if upper <= lower:
            raise Exception("`upper` must be strictly higher than `lower`")
        return self.core.get_unsigned_integer_in_range(lower, upper)

    def __str__(self):
        return "SparklyRG({},{}) ; absorbed={}".format(
            self.steps,
            self.output_rate,
            []
        )
