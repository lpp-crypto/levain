from declaration cimport *

cdef class SparkleRG:
    cdef Sparkle512core core
    
    def __init__(self, steps, output_rate):
        self.core = Sparkle512core()
        self.core.setup(steps, output_rate)


    def absorb(self, x):
        to_absorb = x + b"1" + b"0"*(63 - len(x))
        self.core.absorb(to_absorb)

        
    def get_n_bit_unsigned_integer(self, n):
        if n > 64:
            raise Exception("Cannot return integers more than 64-bit long")
        return self.core.get_n_bit_unsigned_integer(n)

    
    def __call__(self, lower, upper):
        if upper <= lower:
            raise Exception("`upper` must be strictly higher than `lower`")
        return self.core.get_unsigned_integer_in_range(lower, upper)
