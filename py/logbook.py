#!/usr/bin/env sage 
#-*- Python -*-
# Time-stamp: <2025-01-10 16:35:58> 

import datetime, time
import sys, os
import pickle
import re
from rich.progress import Progress

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


# !SUBSECTION! The ONGOING_LOGBOOK global variable

# In order to have a convenient access to high level functions, we
# keep track of the current logbook in this global variable. 
ONGOING_LOGBOOK = None
import builtins
old_print = builtins.print
    
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
    "white" : '\033[2m',
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
            return str(r)
    return str(r)


def input_for_print(to_print):
    """# !TODO! documentation

    # !TODO! doesn't quite work as intended: need to check the format
    # !of its input in log-event and how it handles it

    """
    if len(to_print) == 1:
        return str(to_print[0])
    else:
        result = ""
        for x in to_print:
            result += "  {}\n".format(pretty_result(x))
        return result[:-1]
        


# !SECTION! Measuring tools
# =========================


class Chronograph:
    def __init__(self, title):
        self.title = title
        self.start_time = datetime.datetime.now()

    def __str__(self):
        elapsed_time = datetime.datetime.now() - self.start_time
        tot_secs = floor(elapsed_time.total_seconds())
        days = floor(tot_secs / 86400)
        hours = floor((tot_secs % 86400) / 3600)
        minutes = floor((tot_secs % 3600) / 60)
        seconds = (tot_secs % 60) + elapsed_time.total_seconds() - tot_secs
        return "\"{}\" lasted {}s ({})".format(
            self.title,
            elapsed_time.total_seconds(),
            "{:d}d {:02d}h {:02d}m {:5.03f}s".format(
                days,
                hours,
                minutes,
                seconds
        ))
        


class MemTracer:
    def __init__(self):
        import tracemalloc as local_mem_tracer
        self.mem_tracer = local_mem_tracer
        self.mem_tracer.start()

    def __str__(self):
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
        return "peak memory usage: {}B {}".format(
            memory_peak,
            pretty_peak
        )
        



# !SECTION! The LogBook class


class LogBook:
    """A class helping with keeping track of the data generated while
    a script is running.

    It does so by generating a pretty output while it is run (which
    can be printed in real-time), and as a file in a convenient markup
    format (orgmode by default, though it can handle markdown).

    It keeps track of two distinct things:

    - The "story" (stored in `self.story`), which is simply a list of
      events intended to describe *how* the script is running. Its
      elements are either headings (with a given depth), or pairs
      (time-stamp, string). The time-stamps are generated
      automatically. It is output to stdout if `verbose` is set to
      True, and to a specified file.
    
    - The "basket" (stored in `self.basket`), which correspond to
      things that are intended to be kept at the end of the
      execution. It is stored in a separate file that can be easily
      loaded from python for later use.


    Inputs:
    
    - the first input (and the only mandatory one) is the title of the
      logbook. Try to give a meaningful one, it will help in the long
      term.

    - `verbose`: if set to True, the logbook is printed in stdout as
      it is written. Defaults to True.

    - `print_format`: the style to use when printing (both to the file
      and in stdout if `verbose` is set to True); defaults to "md" for
      Markdown, and can also be equal to "org" for orgmode.

    - `basket_file`: the file in which the `basket` will be
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

    Usage:

    The context defined when using this class defines contains new
    functions:

    - it replaces `print` by its own implementation,

    - SECTION(str), SUBSECTION(str), and SUBSUBSECTION(str) become
      available. Using them adds sections (etc) to the story, and as a
      nice side effect also helps you structure your code.

    - SUCCESS(content=None) simply prints "[SUCCESS]" in green,
      followed by the possible `content` input. It also increments an
      internal success counter which is printed when leaving the scope
      of the LogBook.
    
    - FAIL(content=None) like SUCCESS, but prints "[FAIL]" in
      red. Aslo increments a counter that is printed in the end.

    - to_basket(x, identifier=None) will store x in a pickled file at
      the end of the execution, using either the provided identifier
      as a key. If no identifier is provided, then an increasing
      counter is used. If the same identifier is supplied twice, then
      its first occurence is concatenated with 0, and the following
      ones with an increasing counter.

    In the end, your code could look like this:

    with LogBook("My Fascinating Experiment"):
    
        # the preamble already gets printed when the interpreter
        # reaches this part of the code
    
        SECTION("starting up")

        # ... do stuff
    
        print("string") # this call to `print` instead calls the
                        # `log_event` function of the LogBook instance

                        # `string` will be added to the `story` with
                        # a time-stamp
    
        to_basket(data)
        # `data` will be added to the `results` (and this fact will also
        # be added to the `story`) with key `0`

        to_basket(other_data, "key")
        # added to the basket as well, this time indexed by `"key"`.

        SUCCESS("all good so far!)

    # now that we left the context of the LogBook instance, the
    # conclusion is printed.
    
    print("now not in logbook anymore") # this call to `print` works normally

    """


    # !SUBSECTION! Initialization
    
    def __init__(self,
                 title,
                 verbose=True,
                 print_format="org",
                 with_time=True,
                 with_mem=False,
                 with_preamble=True,
                 with_conclusion=True,
                 ):
        # creating the directories needed if they don't exit yet
        try:
            os.mkdir("logbooks")
        except:
            pass
        try:
            os.mkdir("baskets")
        except:
            pass
        # figuring out the relevant file names 
        name = "{} {}".format(
            time_stamp(),
            title
        ).replace(" ", "_")
        self.file_name = "logbooks/" + name + "." + print_format
        self.basket_file = "baskets/" + name + ".pkl"
        # setting up displaying infrastructure
        self.verbose = verbose
        self.current_toc_depth = 0
        # !TODO! maybe get rid of the toc_depth feature? 
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
        if self.with_mem:
            self.log_event("WARNING: measuring memory usage messes with time complexities!",
                           desc="tr*")
        self.with_preamble = with_preamble 
        self.with_conclusion = with_conclusion
        self.title = title
        # initializing the state
        self.loop_depth = 0
        self.basket = {}
        self.story = []
        self.enum_counter = None
        self.investigated = None
        self.measurements = {
            "elapsed_time": {},
            "max_memory": None
        }
        self.display = old_print
        # -- successes
        self.success_counter = 0
        self.fail_counter = 0
        self.care_about_success_or_fail = False
            
        

    # !SUBSECTION! Logging events and results
    
    def section(self, depth, heading, with_timer=False):
        # checking if there is any on-going timer
        for d in reversed(sorted(self.measurements["elapsed_time"].keys())):
            if d >= depth:
                elapsed = str(self.measurements["elapsed_time"][d])
                self.log_to_basket("elapsed_time", elapsed, desc="t*")
                del self.measurements["elapsed_time"][d]
        # adding to the story
        self.story.append({
            "content": heading,
            "type": "head" + str(depth)
        })
        # starting a timer if necessary
        if with_timer:
            self.measurements["elapsed_time"][depth] = Chronograph(heading)
        self.current_toc_depth = depth
        if self.verbose:
            line = "{}{} {}".format(
                "\n" if depth == 1 else "",
                self.headings(depth),
                heading,
            )
            line = stylize(line, "purple")
            if depth == 1:
                line = stylize(line, "bold")
            line += stylize(" ({}) ".format(time_stamp()), "white")
            self.display(line)
        
        
    def log_event(self, *event, desc="t*"):
        tstamp = time_stamp()
        all_events = []
        for x in event:
            all_events.append(x)
        full_event = {"content": all_events}
        # do we need the time-stamp?
        if "*" in desc:
            full_event["tstamp"] = ""
        else:
            full_event["tstamp"] = stylize("({}) ".format(tstamp), "white")
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
            prefix_terminal = stylize("[SUCCESS] ", "green")
            prefix_text = "[SUCCESS] "
        else:
            prefix_terminal, prefix_text = "", ""
        # handling the different styles
        if "l" in desc:         # -- plain list
            self.enum_counter = None # stopping an enumeration (if any)
            full_event["type"] = "list"
            if self.verbose:
                self.display(full_event["tstamp"] +
                             stylize(" {}{} {}".format(self.bullet,
                                                       prefix_terminal,
                                                       input_for_print(full_event["content"])),
                                     style))
        elif "n" in desc:       # -- numbered list
            if self.enum_counter == None:
                self.enum_counter = 0
            else:
                self.enum_counter += 1
            full_event["type"] = "enum" + str(self.enum_counter)
            if self.verbose:
                self.display(full_event["tstamp"] +
                             stylize(" {:2d}.{} {}".format(self.enum_counter,
                                                           prefix_terminal,
                                                           input_for_print(full_event["content"])),
                                     style))
        else:                   # -- plain text
            self.enum_counter = None # stopping an enumeration (if any)
            full_event["type"] = "text"
            if self.verbose:
                self.display(full_event["tstamp"] +
                             stylize("{}{}".format(prefix_terminal,
                                                   input_for_print(full_event["content"])),
                                     style))
        full_event["content"] = prefix_text + str(full_event["content"])
        self.story.append(full_event)

            
    def log_to_basket(self, key, entry, desc="t"):
        if key in self.basket.keys():
            self.basket[key].append(entry)
        else:
            self.basket[key] = [entry]
        self.log_event("{}: {}".format(key, entry), desc=desc)


    def log_success(self, *args):
        self.care_about_success_or_fail = True
        text = [x for x in args]
        if len(text) > 0:
            to_print = input_for_print(text)
        else:
            to_print = ""
        self.log_event(to_print, desc="t1")
        self.success_counter += 1

        
    def log_fail(self, *args):
        self.care_about_success_or_fail = True
        text = [x for x in args]
        if len(text) > 0:
            to_print = input_for_print(text)
        else:
            to_print = ""
        self.log_event(to_print, desc="t0")
        self.fail_counter += 1
        


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
                    f.write("{}. {} {}\n".format(
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


    # !SUBSECTION! The functions needed by the "with" logic

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
                "Running script {}/{} with command line args {}.".format(
                    os.path.dirname(os.getcwd()),
                    os.path.basename(sys.argv[0]),
                    sys.argv[1:]
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
                self.log_event("No git information to write.", desc="l*r")
            self.log_event("logbook to be saved in " + self.file_name,
                           desc="l*")
        # initializing measurements
        if self.with_time:
            self.measurements["elapsed_time"][0] = Chronograph("The experiment")
        if self.with_mem:
            self.measurements["max_memory"] = MemTracer()
        # setting up global variables
        global ONGOING_LOGBOOK
        ONGOING_LOGBOOK = self
        builtins.print = self.log_event
        return self
    

    def __exit__(self, *args):
        if self.with_conclusion:
            self.section(1, "Conclusion")
            if self.with_time or self.with_mem:
                self.section(2, "Performances")
            # handling time complexity
            if self.with_time:
                self.log_event(
                    str(self.measurements["elapsed_time"][0]),
                    desc="l*"
                )
            # handling memory complexity
            if self.with_mem:
                self.log_event(
                    str(self.measurements["max_memory"]),
                    desc="l*"
                )
            # handling results in the logbook itself
            self.section(2, "Outcome")
            if len(self.basket.keys()) == 0:
                basket_description = "basket is empty"
            else:
                basket_description = "basket was filled"
            self.section(3, basket_description)
            for k in self.basket.keys():
                self.display("{} {}: {}".format(self.bullet,
                                                k,
                                                len(self.basket[k])))
            if self.care_about_success_or_fail:
                self.section(3, "Successes and Failures")
                total = self.success_counter + self.fail_counter
                line = "- successes: {}".format(self.success_counter)
                if self.success_counter > 0:
                    line += " (proportion = {:5.3f} = 2^{:4.3f})".format(
                        float(self.success_counter / total),
                        float(log(self.success_counter, 2) - log(total, 2))
                    )
                self.display(line)
                line = "- failures : {}".format(self.fail_counter)
                if self.fail_counter > 0:
                    line += " (proportion = {:5.3f} = 2^{:4.3f})".format(
                        float(self.fail_counter / total),
                        float(log(self.fail_counter, 2) - log(total, 2))
                    )
                self.display(line)
        # storing the results
        if len(self.basket.keys()) > 0:
            self.basket["title"] = self.title
            self.basket["finished at"] = time_stamp()
            self.basket["file name"] = self.basket_file
            archive_basket(self.basket, self.basket_file)
            self.section(2, "Basket written to {}".format(
                self.basket_file
            ))
        self.save_to_file()
        # undoing global modifications
        builtins.print = old_print
        ONGOING_LOGBOOK = None
        


    # !SUBSECTION! Pretty loops
    
    def loop_over(self, some_set, text):
        """Uses rich to generate a pre-configured progress
        bar that ends when `some_set` has been fully iterated
        over. `text` is a description of the set being looped over.

        """
        # we (re)initialize the progress tracker if we get to depth 0
        if self.loop_depth == 0:
            self.progress_tracker = Progress(transient=True)
            self.progress_tracker.__enter__()
        # dealing with the current loop
        self.loop_depth += 1
        if self.loop_depth > 1:
            title = "{} {} ".format(" " * (self.loop_depth-1) + "└", text)
        else:
            title = "[red]{} ".format(text)
        if "__len__" in dir(some_set):
            task = self.progress_tracker.add_task(title, total=len(some_set))
        else:
            task = self.progress_tracker.add_task(title)
        for i in some_set:
            # !TOSTART! do something clever about the context (use self.investigated somewhere)
            #self.investigated = i
            yield i
            self.progress_tracker.update(task, advance=1)
        # undoing the depth increase once this loop is finished
        self.loop_depth -= 1
        if self.loop_depth == 0:
            self.progress_tracker.__exit__(0, 0, 0)

            

    

# !SUBSECTION! Using the current LogBook instance


# !TODO! write the documentation of these functions 

# !SUBSUBSECTION! Table of content

def SECTION(heading, timed=True):
    ONGOING_LOGBOOK.section(1, heading, with_timer=timed)
    
def SUBSECTION(heading, timed=False):
    ONGOING_LOGBOOK.section(2, heading, with_timer=timed)
    
def SUBSUBSECTION(heading, timed=False):
    ONGOING_LOGBOOK.section(3, heading, with_timer=timed)

def to_basket(key, entry, desc="t*"):
    ONGOING_LOGBOOK.log_to_basket(key, entry, desc=desc)


# !SUBSUBSECTION!  Pretty loop

def ELEMENTS_OF(some_set, text):
    return ONGOING_LOGBOOK.loop_over(some_set, text)

# !SUBSUBSECTION!  Success/failures

def SUCCESS(content):
    ONGOING_LOGBOOK.log_success(content)
                
def FAIL(content):
    ONGOING_LOGBOOK.log_fail(content)

def N_FAILURES():
    return ONGOING_LOGBOOK.fail_counter

def N_SUCCESSES():
    return ONGOING_LOGBOOK.success_counter


# !SECTION! Post-processing of results
# ====================================


# !TODO! add a high-level script to dump their content. We need a
# !post-processing module.
def archive_basket(results, file_name):
    with open(file_name, "wb") as f:
        pickle.dump(results, f)


def open_basket(file):
    with open(file, "rb") as f:
        return pickle.load(f)


def grab_last_basket(*args):
    filters = []
    for x in args:
        if isinstance(x, list):
            filters += x
        else:
            filters.append(x)
    try:
        basket_list = os.listdir("./baskets")
    except:
        raise Exception("could not open ./baskets directory!")
    if len(filters) == 0:
        # default case: we grab the latest
        basket_list.sort()
        return open_basket("./baskets/" + basket_list[-1])
    else:
        # otherwise, we grab the first that matches all the inputs
        for name in reversed(basket_list):
            good = True
            for x in filters:
                if not re.search(x, name):
                    good = False
                    break
            if good:
                return open_basket("./baskets/" + name)
    raise Exception("Could not find a basket matching ", filters)


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
    with LogBook("Testing the LogBook class") as l:

        SECTION("starting up")
        print("bli", desc="t*")

        SUBSECTION("doing useless enumerations")
        for i in range(0, 4):
            print("a useless enumeration ({})".format(i), desc="n*")
        print("and I cut the enumeration...", desc="t")
        print("...and I put back the enumeration!", desc="t")
        for i in range(0, 4):
            print("another useless enumeration, but with time-stamps ({})".format(i), desc="n")

        SUBSECTION("a second subheading")
        print("plain text line", desc="t*")
        print("plain text line with time-stamp", desc="t")
        
        SECTION("moving on to pointless computations", timed=True)
        SUBSECTION("Sums", timed=True)
        blu = []
        for x in range(0, 2**7):
            blu.append(x**3)
        to_basket("sum", sum(blu))
        to_basket("sum", sum(x**2 for x in blu))
        to_basket("sum", sum(x**3 for x in blu))
        SUBSECTION("Successes and Failures", timed=True)
        SUCCESS("happy !")
        FAIL("SAD")
        SUCCESS("happy !")
        time.sleep(1)
        
    # testing reimport of the results
    print("grabbing")
    d = grab_last_basket()
    print(d)


# !SUBSECTION! Main program


if __name__ == "__main__":
    #test_logbook()
    # if len(sys.argv) > 1:
    #     if sys.argv[1] == "grab":
    #         d = grab_last_basket(sys.argv[2:])
    #         print(d)
    with LogBook("loop test"):
        for x in ELEMENTS_OF(range(0, 4), "main loop"):
            print(x)
            for y in ELEMENTS_OF(range(0, 3), "secondary loop"):
                for z in ELEMENTS_OF(range(0, 3), "tertiary loop"):
                    time.sleep(0.3)

