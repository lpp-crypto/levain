#!/usr/bin/sage
#-*- Python -*-
# Time-stamp: <2024-08-08 11:39:46 lperrin> 

import datetime
import sys
import os
import pickle

from collections import defaultdict


# !SECTION! Setting up default parameters and the context 
# =======================================================


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

def time_stamp():
    """Returns a string representation of the current date and time."""
    return datetime.datetime.now().isoformat(" ").split(".")[0]


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

# !TODO! update documentation to take new interface into account:
# !replacing `print`, and providing high level functions (SECTION,
# !etc).
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

    - `with_preamble`: if set to True, the output (both in the
      terminal and in the file) will contain a preamble describing
      when the script was executed, how the script was called, and the
      current git state of the file (if GitPython is
      installed). Defaults to True.

    - `with_conclusion`: if set to True, the output (both in the
      terminal and in the file) will contain a conclusion describing
      the time and memory complexities of the program, as a well the
      number of results obtained. Defaults to True.

    - `with_final_results`: if set to True, the items in the `results`
      list will be listed at the end of the conclusion. Defaults to
      False.

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
                 title,
                 verbose=True,
                 print_format="org",
                 result_file=None,
                 with_time=True,
                 with_mem=True,
                 with_preamble=True,
                 with_conclusion=True,
                 with_final_results=False,
                 ):
        # figuring out the proper file name and inferring the
        # print_format if it is not specified
        self.result_file = result_file
        self.file_name = "logbooks/{} {}.{}".format(
            time_stamp(),
            title,
            print_format).replace(" ", "_")
        # setting up displaying infrastructure
        self.verbose = verbose
        self.current_toc_depth = 0
        self.print_format = print_format
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
        # initializing parameters
        self.with_time = with_time
        self.with_mem = with_mem
        self.with_preamble = with_preamble 
        self.with_conclusion = with_conclusion
        self.with_final_results = with_final_results
        self.title = title
        # initializing the state
        self.results = []
        self.story = []
        if self.with_mem:
            import tracemalloc
            self.mem_tracer = tracemalloc
        self.enum_counter = None
        self.display = print
        self.old_print = print
        

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
            self.display(line)
        
        
    def log_event(self, event, desc="t"):
        tstamp = time_stamp()
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
                self.display(stylize(
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
                self.display(stylize(
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
                self.display(stylize(
                    "{} {}{}{}".format(INDENT * self.current_toc_depth,
                                       full_event["tstamp"],
                                       prefix_terminal,
                                       full_event["content"]),
                    style
                ))
        full_event["content"] = prefix_text + str(full_event["content"])
        self.story.append(full_event)


            
    def log_result(self, result):
        # !TODO! change log_result to `store`
        self.results.append(result)
        self.log_event(pretty_result(result),
                       desc="l1")

    # !TODO! add a `log_success ` method
        
    def log_fail(self, result):
        # !TODO! handle absence of input, and add a fail_counter
        # !attribute
        self.log_event(pretty_result(result),
                       desc="l0")


    # !SUBSECTION! Writing story to file 
        
    def save_to_file(self):
        with open(self.file_name, "w") as f:
            f.write("{}\n".format(self.pretty_title))
            # writing the story
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
        if self.verbose:
            self.display("\n" + stylize(stylize(self.title, "bold"), "underline") + "\n")
        # handling the preamble (if relevant)
        if self.with_preamble:
            self.section(1, "Preamble")
            self.log_event(
                "Experimental log started on {}.".format(
                    datetime.datetime.now().strftime("%a. %b. %Y at %H:%M")
                ),
                desc="l*"
            )
            self.log_event(
                "Running script {} with command line args {}.".format(
                    __file__,
                    sys.argv
                ),
                desc="l*"
            )
            try:
                # try to use GitPython to find a parent directory with
                # a git folder
                from git import Repo
                commit = Repo(".", search_parent_directories=True).commit()
                self.log_event(
                    "The working directory is at commit {}.".format(commit),
                    desc="l*"
                )
            except:
                self.log_fail("No git information to write.")
            self.log_event("logbook saved in " + self.file_name,
                           desc="l*")
            self.section(1, "Experiment starts now")
        # initializing measurements
        if self.with_time:
            self.start_time = datetime.datetime.now()
        if self.with_mem:
            self.mem_tracer.start()
        # declaring all useful functions
        global SECTION, SUBSECTION, SUBSUBSECTION, print
        print         = self.log_event
        SECTION       = lambda x : self.section(1, x)
        SUBSECTION    = lambda x : self.section(2, x)
        SUBSUBSECTION = lambda x : self.section(3, x)
        return self
    

    def __exit__(self, *args):
        if self.with_conclusion:
            self.section(1, "Conclusion")
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
            # handling results in the logbook itself
            if len(self.results) == 0:
                results_description = "no results found"
            else:
                results_description = "{:d} result(s) found".format(len(self.results))
                self.section(2, results_description)
                if self.with_final_results:
                    for res in self.results:
                        self.log_event(pretty_result(res), desc="n*")
        # storing the results
        if self.result_file != None and len(self.results) > 0:
            archive_basket(
                {
                    "results" : self.results,
                    "title" : self.title,
                    "Time-stamp" : time_stamp()
                },
                self.result_file           
            )
            self.section(2, "Results written to {}".format(
                self.result_file
            ))
        self.save_to_file()
        global print
        print = self.old_print

                

# !SECTION! Post-processing of results
# ====================================


# !TODO! store baskets in a dedicated folder, and add a high-level
# !script to dump their content. We need a post-processing module.
def archive_basket(results, file_name):
    with open(file_name, "wb") as f:
        pickle.dump(results, f)


def fetch_basket(file_name):
    with open(file_name, "rb") as f:
        return pickle.load(f)
        

# !SECTION! Testing Area
# =======================


# !SUBSECTION! Small tests

def test_colors():
    for k in T_COLORS.keys():
        if k != "endcol":
            print(T_COLORS[k] + k + T_COLORS["endcol"])


# !SUBSECTION! Testing the LogBook class

def test_logbook():
    # generating a dummy logbook
    with LogBook("Testing the LogBook class"):# as lgbk:

        SECTION("starting up")
        print("bli", desc="t*")

        SUBSECTION("doing useless enumerations")
        for i in range(0, 4):
            print("a useless enumeration ({})".format(i), desc="n*")
        print("and I cut the enumeration...", desc="t")
        print("...and I put back the enumeration!", desc="t")
        for i in range(0, 4):
            print("another useless enumeration ({})".format(i), desc="n*")

        SUBSECTION("a second subheading")
        print("plain text line", desc="t*")
        print("plain text line with time-stamp", desc="t")
        
        SECTION("moving on to pointless computations")
        
        # blu = []
        # for x in range(0, 2**5):
        #     blu.append(x**3)
        # lgbk.log_result(sum(blu))
        # lgbk.log_result({
        #     "sum of cubes": sum(x**3 for x in blu),
        #     "sum of squares": sum(x**2 for x in blu)
        # })
        # for x in range(0, 4):
        #     lgbk.log_result({"padding" : x})
        # lgbk.log_fail("a failure")
        # if IS_SAGE:
        #     lgbk.log_result(Matrix([[0, 1], [2,300000]]))
        # else:
        #     lgbk.log_result([[0, 1], [2,300000]])
        
    # # testing reimport of the results
    # import res
    # print(res.results)
    print("printing should now be normal", " and thus handle ",
          3, "or more variadic inputs")


# !SUBSECTION! Main program

if __name__ == "__main__":
    test_logbook()

    # with LogBook("lgbk",
    #              title="Experimenting with pickle",
    #              # result_file="big.pkl",
    #              with_final_results=False
    #              ) as lgbk:
    #     file_name = "big.pkl"

    #     # lgbk.section(2, "storing")
    #     # if IS_SAGE:
    #     #     X = GF(17).polynomial_ring().gen()
    #     # else:
    #     #     X = 47
    #     # s = []
    #     # for d in range(0, 100):
    #     #     s.append( X**d )
    #     # for k in range(0, 100, 20):
    #     #     lgbk.log_result(s[k])
    #     # archive_result(lgbk.results, file_name)
    #     # lgbk.log_event("result stored in " + file_name)

    #     lgbk.section(2, "grabbing")
    #     s = fetch_archive(file_name)
    #     print(s)
    #     for x in s:
    #         lgbk.log_result(x)
