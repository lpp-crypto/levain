#!/usr/bin/env python3
# Time-stamp: <2025-04-16 11:22:56>

import re
import os
import argparse



# !SECTION! Parameters
# ====================

STD_IGNORE_FILES = [
    re.compile(r".*~"),
    re.compile(r".*#"),
    re.compile(r"\..*"),
    re.compile(r"CMakeCache"),
]

STD_IGNORE_FOLDERS = [
    re.compile(r"\..*"),
    re.compile(r".*CMake.*"),
    re.compile(r".*auto.*"),
    "__pycache__"
]

VALID_EXTENSIONS = [re.compile(r".*\.{}$".format(ext))
    for ext in [
            "c", "cpp", "h", "hpp", "cc", "hh",
            "py", "sage",
            "txt", "tex",
            "org", "md",
            "sh", "zsh",
            "el"
    ]
]

# the following is used to simplify links
HOME_DIR_LENGTH = len(os.path.realpath(os.path.expanduser("~")))

# !SECTION! Identifying and parsing items
# =======================================

BEGIN_TITLE      = r"!"
END_TITLE        = r"!"
CONTINUED_PREFIX = r"!"
TITLE_REGEXP     = re.compile(r".*" + BEGIN_TITLE + r"(\w+)" + END_TITLE + r"(.*)")
CONTINUED_REGEXP = re.compile(r"\W*" + CONTINUED_PREFIX + r" *(.*)")


def strip_final_newline(line):
    if len(line) == 0:
        return line
    elif line[-1] == "\n":
        return line[:-1]
    else:
        return line
    


def extract_header_if_present(line):
    line = strip_final_newline(line)
    content = TITLE_REGEXP.findall(line)
    if content:
        header = content[0][0]
        text = content[0][1].strip()
        return header, text
    else:
        return ""
    

def extract_continued_content_if_present(line):
    line = strip_final_newline(line)
    content = CONTINUED_REGEXP.findall(line)
    if content:
        return content[0].strip() + " "
    else:
        return ""
        

# !SECTION! The classes used to store and parse the files
# =======================================================



SUBSECTION_PREFIX = "SUB"
SECTION_SUFFIX = "SECTION"
SECTION_REGEXP = re.compile(r"({})*{}".format(SUBSECTION_PREFIX,
                                              SECTION_SUFFIX))

def get_title_depth(title):
    if SECTION_REGEXP.match(title):
        return 1 + int((len(title) - len(SECTION_SUFFIX)) / len(SUBSECTION_PREFIX))
    else:
        return None


# !SUBSECTION! MeuporgItem, the class corresponding to the data extracte 

class MeuporgItem:
    """Corresponds to a meup.org item: stores a title, a content, and
    its line number.

    It also handles their tree structure: a MeuporgItem can have
    successors, and exactly one predecessor.

    """
    def __init__(self, title, content, line_number, path, base_depth):
        self.title = title
        self.content = content
        self.line_number = line_number
        self.path = path
        # currently unset parameters
        self.successors = []
        self.predecessor = None
        heading_depth = get_title_depth(title)
        if line_number in ["folder", "file"]:
            self.depth = base_depth
            self.is_heading = True
        elif heading_depth == None:
            self.depth = -1
            self.is_heading = False
        else:
            self.depth = base_depth + heading_depth
            self.is_heading = True


    def top(self):
        cursor = self
        while cursor.predecessor != None:
            cursor = cursor.predecessor
        return cursor

        
    def absorb_item(self, new_entry):
        #print("inserting ", new_entry.is_heading, new_entry)
        # handling leaves
        if not new_entry.is_heading:
            new_entry.successors = None
            new_entry.predecessor = self
            self.successors.append(new_entry)
            return self
        # handling structural item
        elif new_entry.depth > self.depth:
            self.successors.append(new_entry)
            new_entry.predecessor = self
            return new_entry
        elif new_entry.depth == self.depth:
            new_entry.predecessor = self.predecessor
            self.predecessor.successors.append(new_entry)
            return new_entry
        else:
            while new_entry.depth < self.depth :
                self = self.predecessor
            if self.depth == new_entry.depth:
                new_entry.predecessor = self.predecessor
                self.predecessor.successors.append(new_entry)
            else:
                self.successors.append(new_entry)
            return self

        
    def __str__(self):
        return "title: '{}', content: '{}', line_number: {}, depth: {:d}, path: {}".format(
            self.title,
            self.content,
            self.line_number,
            self.depth,
            self.path
        )

            

# !SUBSECTION! The ItemScanner class, used to parse a file and extract items


# the possible states of the Scanner
SCANNING = 0
IN_ITEM  = 1


class ItemScanner:
    """Is initialized with a string corresponding to a path, and
    extracts all the meuporg items in it as MeuporgItem:s. Then, can
    be used to iterate through them in order of arrival:

    for x in ItemScanner(list_of_lines):
        <some processing of the MeuporgItem x>


    The inspiration for the ItemScanner is a Turing machine where the
    file is the input tape, and each line is a cell. The action
    undertaken depends on the state of the Scanner, and said state can
    be updated depending on the cell being scanned.

    It does *not* handle the context in which items are found, that is
    the job of FileMap class. It returns the items as they are found,
    nothing more.

    """
    def __init__(self, path, base_depth):
        self.state = SCANNING
        self.current_item = None
        self.line_number = 0
        self.item_list = []
        self.path = path
        self.base_depth = base_depth
        with open(path, "r") as f:
            try:
                rows = f.readlines()
            except:
                raise Exception("couldn't read " + path)
            for x in rows:
                self.process_new_line(x)
        self.finalize_current_item()

        
    def finalize_current_item(self):
        if self.current_item != None:
            self.item_list.append(self.current_item)
            self.current_item = None
        self.state = SCANNING
         

    def process_new_line(self, line):
        self.line_number += 1
        potential_item = extract_header_if_present(line)
        if potential_item:
            # we have obtained a new item
            self.finalize_current_item()
            self.current_item = MeuporgItem(
                potential_item[0],
                potential_item[1],
                self.line_number,
                self.path,
                self.base_depth
            )
            self.state = IN_ITEM
        elif (self.state == IN_ITEM):
            potential_continuation = extract_continued_content_if_present(line)
            if potential_continuation:
                self.current_item.content += potential_continuation
            else:
                self.finalize_current_item()
        else:
            self.finalize_current_item()

            
    def __len__(self):
        return len(self.item_list)

    
    def __iter__(self):
        for x in self.item_list:
            yield x



# !SECTION! Putting it all together: generating the meuporg item tree
# ===================================================================


# !SUBSECTION! Functions to decide whether we proceed with item extraction
# ------------------------------------------------------------------------

def should_parse_file(file_name, to_ignore):
    for ig in to_ignore:
        if isinstance(ig, str): # case of a simple string
            if ig in file_name:
                return False
        elif ig.match(file_name): # case of a regexp
            return False
    for val in VALID_EXTENSIONS:
        if val.match(file_name):
            return True
    return False


def should_explore_folder(folder_name, to_ignore):
    for ig in to_ignore:
        if isinstance(ig, str): # case of a simple string
            if ig in folder_name:
                return False
        elif ig.match(folder_name): # case of a regexp
            return False
    return True



# !SUBSECTION! Obtaining the items
# --------------------------------

def parse_file(path, depth):
    cursor = MeuporgItem(
        os.path.basename(path),
        path,
        "file",
        path,
        depth
    )
    cursor.is_heading = True
    for x in ItemScanner(path, depth):
        cursor = cursor.absorb_item(x)
    while cursor.depth > depth:
        cursor = cursor.predecessor
    return cursor


def parse_folder(folder_name,
                 depth,
                 ignored_files=None,
                 ignored_folders=None):
    cursor = MeuporgItem(
        folder_name,
        folder_name,
        "folder",
        folder_name,
        depth
    )
    cursor.is_heading = True
    cursor.successors = []
    # if there is a .projectile file in the folder, we use its content to obtain files to ignore
    if ignored_files == None:
        ignored_files = STD_IGNORE_FILES
    if ignored_folders == None:
        ignored_folders = STD_IGNORE_FOLDERS
    if os.path.isfile(".projectile"):
        with open(".projectile", "r") as f:
            for line in f.readlines():
                to_ignore.append(re.compile(r"{}".format(line[2:])))
    # finding all folders and files in the folder
    folders, files = [], []
    for entry in os.listdir(folder_name):
        if os.path.isfile(folder_name + entry):
            if should_parse_file(entry, ignored_files):
                files.append(entry)
        elif should_explore_folder(entry, ignored_folders):
            folders.append(entry)
    # parsing the files
    for file_name in files:
        cursor = cursor.absorb_item(parse_file(
            folder_name + file_name,
            depth + 1
        ))
    # parsing the folder
    for subfolder_name in folders:
        cursor = cursor.absorb_item(parse_folder(
            folder_name + subfolder_name + "/",
            depth + 1,
            ignored_files=ignored_files,
            ignored_folders=ignored_folders,
        ))
    while cursor.depth > depth:
        cursor = cursor.predecessor
    return cursor




# !SUBSECTION! Formatting the tree
# --------------------------------

def simplify_path(file_path):
    file_path = os.path.realpath(file_path)
    file_path = "~" + file_path[HOME_DIR_LENGTH:]
    return file_path

def format_MeuporgItem(it,
                       file_path,
                       sparse=False):
    result = ""
    if not it.is_heading: # case of a regular item
        result += "{} {} :: [[file:{}::{}][(→)]] ".format(
            "-",
            it.title,
            simplify_path(file_path),
            it.line_number,
        )
        if len(it.content) > 0:
            result += it.content
        result += "\n"
    else:  # case of a heading
        if it.line_number == "file": # case of a file in a folder
            to_add = "{} {} [[file:{}][(→)]]\n".format(
                "*" * (it.depth + 1),
                it.title,
                simplify_path(it.path),
            )
        elif it.line_number == "folder": # case of a folder
            to_add = "{} ={}=\n".format(
                "*" * (it.depth + 1),
                simplify_path(file_path),
            )
        else: # case of a heading in a file
            to_add = "{} {} [[file:{}::{}][(→)]]\n".format(
                "*" * (it.depth + 1),
                it.content,
                simplify_path(it.path),
                it.line_number,
            )
        empty_section = True
        for x in it.successors:
            next_items = format_MeuporgItem(
                x,
                file_path if not it.line_number == "folder" else x.content,
                sparse=sparse
            )
            if len(next_items) > 0:
                to_add += next_items
                empty_section = False
        if (not empty_section) or (not sparse):
            result += to_add
    return result



# !SECTION! Tests

def test_file_parsing():
    file_name = "meuporg.py"
    print(format_MeuporgItem(parse_file(file_name, 1),
                             file_name,
                             "Meuporg Python"))

def test_folder_parsing():
    folder_name = "/home/leo/research/sbox-utils/"
    i = parse_folder(
        folder_name,
        0,
        ignored_files=STD_IGNORE_FILES,
        ignored_folders=STD_IGNORE_FOLDERS + ["fftw", "build", "linux", "CMakeFiles", "known_functions"]
    )
    print(format_MeuporgItem(
        i.top(),
        folder_name,
        "sboxU",
        sparse=True
    ))
    

# !SECTION!  Main program


if __name__ == "__main__":

    # !SUBSECTION! Initializing the arguments using argparse
    parser = argparse.ArgumentParser(
                    prog='Meuporg Parser',
                    description='Detects all the meuporg items in a file/directory and displays them as an orgmode tree.',
                    epilog='')
    parser.add_argument("path",
                        help="The path to the file or folder to parse")
    parser.add_argument("-a", "--all",
                        action="store_true",
                        help="Lists the full structure of the project, not just the headings leading to an item")
    parser.add_argument("-i", "--ignore",
                        nargs="+",
                        type=str,
                        help="A space separated list of regexp: files and folder that contain any of them will be ignored")
    parser.add_argument("-d", "--depth",
                        type=int,
                        default=0,
                        help="The offset to add to the depth when displaying the org tree.")
    args = parser.parse_args()

    # !SUBSECTION! processing the folder (or file) 
    if not os.path.isfile(args.path):
        ign = args.ignore
        if ign == None:
            ign = []
        if args.path[-1] != "/":
            args.path += "/"
        its = parse_folder(
            args.path,
            args.depth,
            ignored_files=STD_IGNORE_FILES + ign,
            ignored_folders=STD_IGNORE_FOLDERS + ign
        )
    else:
        its = parse_file(args.path, args.depth)
    print(format_MeuporgItem(its.top(),
                             args.path,
                             sparse=not args.all))

