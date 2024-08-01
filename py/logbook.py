#!/usr/bin/sage
#-*- Python -*-
# Time-stamp: <2024-08-01 15:49:19 lperrin> 

import datetime
import sys
import time
import tracemalloc

from collections import defaultdict

# for test
from math import floor
from statistics import mean, variance

INDENT = " "
DEFAULT_INT_FORMAT = "{:3d}"
DEFAULT_FLOAT_FORMAT = "{:8.3e}"

try:
    import sage
    IS_SAGE = True
except:
    IS_SAGE = False

if IS_SAGE:
    from sage.all import *


def pretty_result(r,
                  int_format=DEFAULT_INT_FORMAT,
                  float_format=DEFAULT_FLOAT_FORMAT,):
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
    else:
        if IS_SAGE:
            # checking if sage matrix
            try:
                x = Matrix(r)
                if x == r:
                    return pretty_result([[x for x in row] for row in r.rows()])
            except:
                pass
        # checking if int
        try:
            x = int(r)
            if x == r:
                return int_format.format(x)
        except:
            pass
        # checking if real
        try:
            x = float(r)
            if x == r:
                return float_format.format(x)
        except:
            pass        
        return str(r)
    

def python_readable_string(y):
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
    else:
        if IS_SAGE:
            try:
                x = Matrix(y)
                if x == y:
                    return "Matrix({}, {}, {})".format(
                        x.nrows(),
                        x.ncols(),
                        str(x.rows())
                    )
            except:
                pass
        return str(y)
            
        

class LogBook:
    def __init__(self,
                 file_name,
                 title="Experiment",
                 verbose=False,
                 print_format=None,
                 result_file=False,
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
            self.title = "#+TITLE: " + title
        elif self.print_format == "md":
            self.headings = lambda depth : "#" * (depth + 1)
            self.bullet = "*"
            self.title = "{}\n{}".format(title, "="*len(title))
        else:
            raise Exception("unsuported print format: {}".format(self.print_format))
        # initializing the state
        self.with_time = with_time
        self.with_mem = with_mem
        self.results = []
        self.story = []

        
    def section(self, depth, heading):
        self.story.append([depth, heading])
        self.current_toc_depth = depth
        if self.verbose:
            print("{}{} {}".format(
                "\n\n" if depth == 1 else "\n" if depth == 2 else "",                
                self.headings(depth),
                heading
            ))
        
        
    def log_event(self, event):
        timed_event = [
            datetime.datetime.now().isoformat(" ").split(".")[0],
            event
        ]
        self.story.append(timed_event)
        if self.verbose:
            print("{} {} [{}] {}".format(
                INDENT * self.current_toc_depth,
                self.bullet,
                timed_event[0],
                timed_event[1],
            ))

    def log_result(self, result):
        self.results.append(result)
        self.log_event("[result] " + pretty_result(result))

        
    def save_to_file(self):
        with open(self.file_name, "w") as f:
            f.write("{}\n".format(self.title))
            f.write("Experimental log generated on the {}.\n\n".format(
                datetime.datetime.now().strftime("%a. %b. %Y at %H:%M")
            ))
            for line in self.story:
                if isinstance(line, list):
                    if isinstance(line[0], str): # case of a time-stamp
                        f.write("{} [{}] {}\n".format(self.bullet,
                                                      line[0],
                                                      line[1]))
                    else: # case of a heading
                        depth = line[0]
                        f.write("{}{} {}\n".format(
                            "\n\n" if depth == 1 else "\n" if depth == 2 else "",                
                            self.headings(depth),
                            line[1]
                        ))
                else:
                    f.write("{} {}\n".format(self.bullet, str(line)))



    def __enter__(self):
        if self.with_time:
            self.start_time = datetime.datetime.now()
        if self.with_mem:
            tracemalloc.start()
        if self.verbose:
            print(self.title + "\n")
        return self

    def __exit__(self, *args):
        self.section(1, "Finished")
        if self.with_time or self.with_mem:
            self.section(2, "Performances")
        if self.with_time:
            # handling time
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
            self.story.append(elapsed_time_description)
            if self.verbose:
                print(self.bullet + " " + elapsed_time_description)
        # handling memory
        if self.with_mem:
            memory_size, memory_peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
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
            self.story.append(memory_description)
            if self.verbose:
                print(self.bullet + " " + memory_description)
        # handling results (if any)
        if len(self.results) == 0:
            results_description = "no results found"
        else:
            results_description = "{:d} result(s) found".format(len(self.results))
            self.section(2, results_description)
            number_length = len(str(len(self.results)))
            counter = 0
            for res in self.results:
                counter += 1
                pretty_res = pretty_result(res)
                self.story.append(pretty_res)
                print("{}{:d}. {}{}".format(
                    INDENT,
                    counter,
                    " "*(number_length - len(str(counter))),
                    pretty_res
                ))
        self.save_to_file()
        # handling possible additional file for results
        if self.result_file != None:
            with open(self.result_file, "w") as f:
                if IS_SAGE:
                    f.write("from sage.all import *\n\n")
                f.write("results = [\n")
                for x in self.results:
                    f.write(python_readable_string(x) + ",\n")
                f.write("]\n")
            if self.print_format == "org":
                self.section(2, "results written to [[./{}][{}]".format(
                    self.result_file,
                    self.result_file
                ))
            else:
                self.section(2, "results written to {}".format(
                    self.result_file
                ))

                
            
        


if __name__ == "__main__":
    with LogBook("file.org",
                 verbose=True,
                 result_file="res.py",
                 ) as lgbk:
        lgbk.section(1, "starting up")
        lgbk.log_event("bli")
        lgbk.log_event("blu")
        time.sleep(1)
        blu = []
        for x in range(0, 2**5):
            blu.append(x**3)
        lgbk.log_result(sum(blu))
        lgbk.log_result({
            "mean": mean(blu),
            "var": float(variance(blu))/2**20 + 0.1
        })
        for x in range(0, 12):
            lgbk.log_result({"padding" : x})
        if IS_SAGE:
            lgbk.log_result(Matrix([[0, 1], [2,300000]]))
        else:
            lgbk.log_result([[0, 1], [2,300000]])
        time.sleep(1)
        lgbk.section(2, "loading stuff")
        lgbk.log_event("bli bla blu")
        lgbk.section(1, "investigating")




    import res
    print(res.results)
