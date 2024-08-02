#!/usr/bin/sage
#-*- Python -*-
# Time-stamp: <2024-08-02 17:49:23 lperrin> 

import datetime
import sys
import os

from collections import defaultdict


# !SECTION! Setting up default parameters and the context 
# =======================================================


# !SUBSECTION! Checking the presence of gitpython

# if you want the logbook to read data from the git repository, you
# need install the package gitpython (`pip install gitpython` and
# `sage -pip install gitpython`)
try:
    import git
    IS_GIT = True
except:
    IS_GIT = False


# !SUBSECTION! Is SAGE used? 

# Handling different cases depending on whether the program is called
# from SAGE or from python. The main difference between both cases is
# that SAGE brings in more types, that then must be handled when
# printing data.

# to figure out if the class is called from SAGE or from Python, we
# try importing SAGE.
try:
    import sage
    IS_SAGE = True
except:
    IS_SAGE = False

# In SAGE, there are more number types than in plain python
if IS_SAGE:
    from sage.all import *
    int_types = (int, Integer)
    float_types = (float, sage.rings.real_mpfr.RealNumber)
else:
    int_types = (int)
    float_types = (float)
    from math import floor # needed when computing elapsed time
    

# !SECTION! Printing
# ==================

# !SUBSECTION! Default strings

# The default strings used when printing both to stdout and to files
INDENT = " "
DEFAULT_INT_FORMAT = "{:3d}"
DEFAULT_FLOAT_FORMAT = "{:8.3e}"


# !SUBSECTION! To have colors in the terminal

# explanations: https://stackoverflow.com/questions/287871/how-do-i-print-colored-text-to-the-terminal
T_COLORS = {
    "red" : '\033[91m',
    "green" : '\033[92m',
    "yellow" : '\033[93m',
    "blue" : '\033[94m',
    "purple" : '\033[95m',
    "cyan" : '\033[96m',
    "black" : '\033[98m',
    "endcol" : '\033[0m',
    "bold" : '\033[1m',
    "underline" : '\033[4m',
}
    
def stylize(line, style):
    if style not in T_COLORS.keys():
        raise Exception("unknown style: '{}".format(style))
    return T_COLORS[style] + line + T_COLORS["endcol"]


# !SUBSECTION!  Printing functions

# Several functions that print their input in a pretty way, either for
# humain readability or for Python readability.

def pretty_result(r,
                  int_format=DEFAULT_INT_FORMAT,
                  float_format=DEFAULT_FLOAT_FORMAT,):
    """Outputs a human readable pretty string representating the input
    `r`.

    It is intended to play well with stdout output as well as both
    markdown and org.
    
    Inputs:

    - `r`: the information to print.

    - `int_format` (defaults to DEFAULT_INT_FORMAT): the format string
      used to print integers (and associated types).
    
    - `float_format` (defaults to DEFAULT_INT_FORMAT): the format
      string used to print floats (and associated types).

    """
    if isinstance(r, dict) or isinstance(r, defaultdict):
        result = ""
        for k in sorted(r.keys()):
            result += "{}={}, ".format(pretty_result(k), pretty_result(r[k]))
        return result[:-2]
    elif (isinstance(r, list) and len(r) > 0):
        if isinstance(r[0], list):
            # case of a matrix as a list of list
            result = "table:\n"
            for row in r:
                for x in row:
                    result += "| {} ".format(pretty_result(x))
                result += "|\n"
            return result
        else:
            # case of a plain list
            return str(r)
    elif isinstance(r, int_types):
        return int_format.format(r)
    elif isinstance(r, float_types):
        return float_format.format(r)
    elif IS_SAGE:
        if "sage.matrix" in str(type(r)):
            return pretty_result([[x for x in row] for row in r.rows()])
        else:
            pass
    return str(r)
    

def python_readable_string(y):
    """Returns a string representation of `y` that is both human
    readable *and* Python readable.

    It is supposed to look like the code a human would write to
    generate a variable equal to `y`.

    Input:

    - `y`: the data to print

    """
    if isinstance(y, list):
        result = "["
        for x in y:
            result += "{}, ".format(python_readable_string(x))
        return result[:-2] + "]"
    elif isinstance(y, str):
        return '"{}"'.format(y)
    elif isinstance(y, dict):
        result = "{"
        for k in y.keys():
            result += "{}: {}, ".format(python_readable_string(k),
                                        python_readable_string(y[k]))
        return result[:-2] + "}"
    elif IS_SAGE:
        if "sage.matrix" in str(type(y)):
            return "Matrix({}, {}, {})".format(
                y.nrows(),
                y.ncols(),
                str(y.rows())
            )
        else:
            pass
    return str(y)
            
        

# !SECTION! The LogBook class

class LogBook:
    """A class helping with keeping track of the data generated while
    a script is running.

    It does so by generating a pretty output while it is run (which
    can be printed in real-time), and as a file in a convenient markup
    format (either markdown or orgmode).

    It keeps track of two distinct things:

    - "story" (stored in `self.story`), which is simply a list of
      events intended to describe *how* the script is running. Its
      elements are either headings (with a given depth), or pairs
      (time-stamp, string). The time-stamps are generated
      automatically. It is output to stdout if `verbose` is set to
      True, and to a specified file.
    
    - "results" (stored in `self.results`), which are intended to
      correspond to the specific data that was intended to be
      generated by the script. They are added to the "story" as they
      are generated. Optionnally, a python script regenerating them
      can be generated as well, the idea being to ease
      post-processing: said python script can simply be imported to
      reobtain the `results`.

    Inputs:
    
    - `file_name`: the path to the file in which the logbook should be
      written.

    - `title`: the title of the logbook, defaults to "Experiment". Try
      to give a meaningful one, it will help in the long term.

    - `verbose`: if set to True, the logbook is printed in stdout as
      it is written. Defaults to True.

    - `print_format`: the style to use when printing (both to the file
      and in stdout if `verbose` is set to True); defaults to "md" for
      Markdown, and can also be equal to "org" for orgmode.

    - `result_file`: the file in which the `results` will be
      written. Defaults to `None`, meaning that no such file is
      generated.

    - `with_time`: if set to True, the time during which the LogBook
      is used is computed and output in the end. Defaults to True.

    - `with_mem`: if set to True, the maximum memory used while the
      LogBook is used is computed and output in the end. Defaults to
      True.
    

    Usage:

    with LogBook(args*) as lgbk:
        lgbk.section(1, "starting up") # 1 indicates the heading level,
                                       # with 1 being highest, then 2...
        # ... do stuff
        lgbk.log_event("string")
        # the string will be added to the `story` with a time-stamp
        lgbk.log_result(data)
        # `data` will be added to the `results` (and this fact will also
        # be added to the `story`)

    """


    # !SUBSECTION! Initialization
    
    def __init__(self,
                 file_name,
                 title="Experiment",
                 verbose=True,
                 print_format=None,
                 result_file=None,
                 with_time=True,
                 with_mem=True
                 ):
        # figuring out the proper file name and inferring the
        # print_format if it is not specified
        self.result_file = result_file
        if print_format == None:
            if file_name[-2:] == "md":
                self.print_format = "md"
            else:
                self.print_format = "org"
        else:
            self.print_format = "md" # defaulting to markdown
        self.file_name = file_name
        if self.file_name[-len(self.print_format)-1:] != "."+self.print_format:
            self.file_name += "." + self.print_format
        # setting up displaying infrastructure
        self.verbose = verbose
        self.current_toc_depth = 0
        if self.print_format == "org":
            self.headings = lambda depth : "*" * depth
            self.bullet = "-"
            self.pretty_title = "#+TITLE: {}\n".format(title)
        elif self.print_format == "md":
            self.headings = lambda depth : "#" * (depth + 1)
            self.bullet = "*"
            self.pretty_title = "{}\n{}\n".format(title, "="*len(title))
        else:
            raise Exception("unsuported print format: {}".format(self.print_format))
        # initializing the state
        self.title = title
        self.with_time = with_time
        self.with_mem = with_mem
        self.results = []
        self.story = []
        if self.with_mem:
            import tracemalloc
            self.mem_tracer = tracemalloc
        self.enum_counter = None


    # !SUBSECTION! Logging events and results
    
    def section(self, depth, heading):
        self.story.append({
            "content": heading,
            "type": "head" + str(depth)
        })
        self.current_toc_depth = depth
        if self.verbose:
            line = "{}{} {}".format(
                "\n" if depth == 1 else "",                
                self.headings(depth),
                heading
            )
            line = stylize(line, "purple")
            if depth == 1:
                line = stylize(line, "bold")
            print(line)
        
        
    def log_event(self, event, desc="l"):
        tstamp = datetime.datetime.now().isoformat(" ").split(".")[0]
        full_event = {"content": event}
        # do we need the time-stamp?
        if "*" in desc:
            full_event["tstamp"] = ""
        else:
            full_event["tstamp"] = "({}) ".format(tstamp)
        # do we need a color?
        if "r" in desc:
            style = "red"
        elif "g" in desc:
            style = "green"
        else:
            style = "black"
        # do we need a prefix?
        if "0" in desc:
            prefix_terminal = stylize("[FAIL] ", "red")
            prefix_text = "[FAIL] "
        elif "1" in desc:
            prefix_terminal = stylize("[result] ", "green")
            prefix_text = "[result] "
        else:
            prefix_terminal, prefix_text = "", ""
        # handling the different styles
        if "l" in desc:         # -- plain list
            self.enum_counter = None # stopping an enumeration (if any)
            full_event["type"] = "list"
            if self.verbose:
                print(stylize(
                    "{} {} {}{} {}".format(INDENT * self.current_toc_depth,
                                           self.bullet,
                                           full_event["tstamp"],
                                           prefix_terminal,
                                           full_event["content"]),
                    style
                ))
        elif "n" in desc:       # -- numbered list
            if self.enum_counter == None:
                self.enum_counter = 0
            else:
                self.enum_counter += 1
            full_event["type"] = "enum" + str(self.enum_counter)
            if self.verbose:
                print(stylize(
                    "{} {}.{}{} {}".format(INDENT * self.current_toc_depth,
                                           self.enum_counter,
                                           full_event["tstamp"],
                                           prefix_terminal,
                                           full_event["content"]),
                    style
                ))
        else:                   # -- plain text
            self.enum_counter = None # stopping an enumeration (if any)
            full_event["type"] = "text"
            if self.verbose:
                print(stylize(
                    "{} {}{}{}".format(INDENT * self.current_toc_depth,
                                       full_event["tstamp"],
                                       prefix_terminal,
                                       full_event["content"]),
                    style
                ))
        full_event["content"] = prefix_text + full_event["content"]
        self.story.append(full_event)


            
    def log_result(self, result):
        self.results.append(result)
        self.log_event(pretty_result(result),
                       desc="l1")
            
    def log_fail(self, result):
        self.log_event(pretty_result(result),
                       desc="l0")

        
    def save_to_file(self):
        with open(self.file_name, "w") as f:
            f.write("{}\n".format(self.pretty_title))
            f.write("Experimental log generated on {}.\n".format(
                datetime.datetime.now().strftime("%a. %b. %Y at %H:%M")
            ))
            f.write("We ran script {} with command line args {}.\n".format(
                __file__,
                sys.argv
            ))
            # !TODO! write the commit/branch etc. 
            for line in self.story:
                if "type" not in line.keys():
                    raise Exception(
                        "error: a story line doesn't have a type (story line: {})".format(line)
                    )
                elif line["type"][:4] == "head":
                    depth = int(line["type"][4:], 10)
                    f.write("{}{} {}\n".format(
                        "\n\n" if depth == 1 else "",                
                        self.headings(depth),
                        line["content"]
                    ))
                elif line["type"][:4] == "enum":
                    depth = int(line["type"][4:], 10)
                    f.write("{}.{} {}\n".format(
                        depth,
                        line["tstamp"],
                        line["content"]
                    ))
                elif line["type"] == "list":
                    f.write("{} {}{}\n".format(
                        self.bullet,
                        line["tstamp"],
                        line["content"]
                    ))
                else:
                    f.write("{}{}\n".format(
                        line["tstamp"],
                        line["content"]
                    ))


    # !SUBSECTION!  The functions needed by the "with" logic

    def __enter__(self):
        if self.with_time:
            self.start_time = datetime.datetime.now()
        if self.with_mem:
            self.mem_tracer.start()
        if self.verbose:
            print("\n" + stylize(stylize(self.title, "bold"), "underline"))
        return self
    

    def __exit__(self, *args):
        self.section(1, "Finished")
        if self.with_time or self.with_mem:
            self.section(2, "Performances")
        # handling time complexity
        if self.with_time:
            elapsed_time = datetime.datetime.now() - self.start_time
            tot_secs = floor(elapsed_time.total_seconds())
            days = floor(tot_secs / 86400)
            hours = floor((tot_secs % 86400) / 3600)
            minutes = floor((tot_secs % 3600) / 60)
            seconds = (tot_secs % 60) + elapsed_time.total_seconds() - tot_secs
            elapsed_time_description = "elapsed time: {}s ({})".format(
                elapsed_time.total_seconds(),
                "{:d}d {:02d}h {:02d}m {:5.03f}s".format(
                    days,
                    hours,
                    minutes,
                    seconds
            ))
            self.log_event(elapsed_time_description, desc="l*")
        # handling memory complexity
        if self.with_mem:       
            memory_size, memory_peak = self.mem_tracer.get_traced_memory()
            self.mem_tracer.stop()
            if memory_peak > 1024**3:
                pretty_peak = "(= {:.2f}GB)".format(memory_peak / 1024**3)
            elif memory_peak > 1024**2:
                pretty_peak = "(= {:.2f}MB)".format(memory_peak / 1024**2)
            elif memory_peak > 1024:
                pretty_peak = "(= {:.2f}kB)".format(memory_peak / 1024)
            else:
                pretty_peak = ""
            memory_description = "peak memory usage: {}B {}".format(
                memory_peak,
                pretty_peak
            )
            self.log_event(memory_description, desc="l*")
        # handling results
        # -- in the separated file (if relevant)
        if self.result_file != None and len(self.results) > 0:
            with open(self.result_file, "w") as f:
                f.write("# Output of \"{}\", generated on {}\n".format(
                    self.title,
                    datetime.datetime.now().isoformat(" ").split(".")[0]
                ))
                f.write("# see LogBook at {}\n".format(self.file_name))
                if IS_SAGE:
                    f.write("from sage.all import *\n\n")
                f.write("results = [\n")
                counter = 0
                for x in self.results:
                    f.write("{},    # {:d}\n".format(
                        python_readable_string(x),
                        counter
                    ))
                    counter += 1
                f.write("]\n")
            self.section(2, "Results written to {}".format(
                self.result_file
            ))
        # -- in the logbook itself
        if len(self.results) == 0:
            results_description = "no results found"
        else:
            results_description = "{:d} result(s) found".format(len(self.results))
            self.section(2, results_description)
            for res in self.results:
                self.log_event(pretty_result(res), desc="n*")
        self.save_to_file()

                
            
        

# !SECTION!  Main program testing the LogBook class

if __name__ == "__main__":
    # generating a dummy logbook
    with LogBook("lgbk.org",
                 verbose=True,
                 result_file="res.py",
                 ) as lgbk:

        lgbk.section(1, "starting up")
        lgbk.log_event("bli", desc="t*")

        lgbk.section(2, "doing useless enumerations")
        for i in range(0, 4):
            lgbk.log_event("a useless enumeration ({})".format(i), desc="n*")
        lgbk.log_event("and I cut the enumeration...", desc="t")
        lgbk.log_event("...and I put back the enumeration!", desc="t")
        for i in range(0, 4):
            lgbk.log_event("another useless enumeration ({})".format(i), desc="n*")

        lgbk.section(2, "a second subheading")
        lgbk.log_event("plain text line", desc="t*")
        lgbk.log_event("plain text line with time-stamp", desc="t")
        
        lgbk.section(1, "moving on to pointless computations")
        blu = []
        for x in range(0, 2**5):
            blu.append(x**3)
        lgbk.log_result(sum(blu))
        lgbk.log_result({
            "sum of cubes": sum(x**3 for x in blu),
            "sum of squares": sum(x**2 for x in blu)
        })
        for x in range(0, 4):
            lgbk.log_result({"padding" : x})
        lgbk.log_fail("a failure")
        if IS_SAGE:
            lgbk.log_result(Matrix([[0, 1], [2,300000]]))
        else:
            lgbk.log_result([[0, 1], [2,300000]])
        
    # testing reimport of the results
    import res
    print(res.results)
    for k in T_COLORS.keys():
        if k != "endcol":
            print(T_COLORS[k] + k + T_COLORS["endcol"])

