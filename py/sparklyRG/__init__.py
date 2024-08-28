from .wrapper import *
import datetime
    

class EschRG(SparkleRG):
    def __init__(self, seeds, with_time=False):
        """Initializes an EschRG instance, i.e. a deterministic
        pseudo-random number generator inheriting its security from
        that of the SPARKLE-based NIST finalist Esch.
    
        Parameters:
    
        - `seeds`: a list of objects or an object to be used as the
          PRNG seed.
    
        - `with_time` (defaults to `False`): if set, the current UNIX
          time is used as an additional seed.
    
        If you use an Esch instance in your code, printing it will
        give you a piece of valid Python code that you can use to
        create an identically initialized EschRG instance.
    
        """
        SparkleRG.__init__(self, 8, 256)
        self.absorbed = []
        blocks = []
        if isinstance(seeds, list):
            blocks = seeds[:]
        else:
            blocks.append(seeds)
        if with_time:
            time_string = datetime.datetime.now().isoformat(" ").split(".")[0]
            blocks.append(time_string.encode("UTF-8"))
        for x in blocks:
            self._absorb_block(x)        
    def __str__(self):
        return "EschRG({})".format(self.absorbed)  
    def _absorb_block(self, x):
        """Absorbs `x` into the state, performing some boring
        operations along the way to handle inputs of different
        types. You are not really supposed to use it.
    
        """
        if isinstance(x, bytes):
            to_absorb = x
        elif isinstance(x, str):
            to_absorb = x.encode("UTF-8")
        else:
            to_absorb = str(x).encode("UTF-8")
        if len(to_absorb) > 31:
                raise Exception("block is too big, max length is 31 bytes")
        else:
            self.absorbed.append(to_absorb)
            self.absorb(to_absorb)        
    def random_permutation(self, v_size):
        """Returns the set of integers {0,...,v_size-1} after
        undergoing a permutation picked uniformly at random.
    
        Relies on a Fisher-Yates shuffle to do so.
    
        https://en.wikipedia.org/wiki/Fisher%E2%80%93Yates_shuffle
    
        """
        result = list(range(0, v_size))
        for i in range(0, v_size):
            j = self(i, v_size)
            result[i], result[j] = result[j], result[i]
        return result
