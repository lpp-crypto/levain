#!/usr/bin/env python
# Time-stamp: <2025-01-05 21:43:26>

import re


# !SECTION! Identifying and parsing items 

BEGIN_TITLE      = r"!"
END_TITLE        = r"!"
CONTINUED_PREFIX = r"!"
TITLE_REGEXP     = re.compile(r".*" + BEGIN_TITLE + r"(\w+)" + END_TITLE + r"(.*)")
CONTINUED_REGEXP = re.compile(r"\W*" + CONTINUED_PREFIX + r" *(.*)")



def extract_header_if_present(line):
    content = TITLE_REGEXP.findall(line)
    if content:
        header = content[0][0]
        text = content[0][1].strip()
        return header, text
    else:
        return ""
    

def extract_continued_content_if_present(line):
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
        return -1


# !SUBSECTION! MeuporgItem, the class corresponding to the data extracte 

class MeuporgItem:
    """Corresponds to a meup.org item: stores a title, a content, and
    its line number.

    It also handles their tree structure: a MeuporgItem can have
    successors, and exactly one predecessor.

    """
    def __init__(self, title, content, line_number):
        self.title = title
        self.content = content
        self.line_number = line_number
        # currently unset parameters
        self.successors = []
        self.predecessor = None
        self.depth = get_title_depth(title) 


    def finalize(self):
        if self.predecessor == None:
            return self
        else:
            if self not in self.predecessor.successors:
                self.predecessor.successors.append(self)
            return self.predecessor

        
    def absorb_item(self, new_entry):
        # handling leaves
        if new_entry.depth == -1:
            new_entry.depth = self.depth + 1
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
            self.predecessor.successors.append(new_entry)
            return new_entry
        else:
            cursor = self
            while cursor.depth > new_entry.depth:
                cursor = cursor.finalize()
            return cursor

            

# !SUBSECTION! The ItemScanner class, used to parse a file and extract items


# the possible states of the Scanner
SCANNING = 0
IN_ITEM  = 1


class ItemScanner:
    """Is initialized with a list of strings, and extracts all the
    meuporg items in it as MeuporgItem:s. Then, can be used to iterate
    through them in order of arrival:

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
    def __init__(self, lines):
        self.state = SCANNING
        self.current_item = None
        self.line_number = 0
        self.item_list = []
        for x in lines:
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
                self.line_number
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


def parse_lines(lines):
    cursor = MeuporgItem(
        "main",
        "",
        0
    )
    cursor.depth = 0
    for x in ItemScanner(lines):
        cursor = cursor.absorb_item(x)
    while cursor.depth > 0:
        cursor = cursor.finalize()
    return cursor.finalize()



def format_MeuporgItem(it, file_path, title):
    result = ""
    if it.title == "main":
        result = "* {}\n".format(title)
        for x in it.successors:
            result += format_MeuporgItem(x, file_path, title)
    elif it.successors == None:
        result += "{} {} ({})\n".format(
            "*" * (it.depth + 1),
            it.title,
            it.line_number,
        )
        if len(it.content) > 0:
            result += it.content + "\n"
    else:
        result += "{} {} ({})\n".format(
                "*" * (it.depth + 1),
                it.content,
                it.line_number,
        )
        for x in it.successors:
            result += format_MeuporgItem(x, file_path, title)
    return result



# !SECTION!  Main program


if __name__ == "__main__":
    test = [
        "blublu",
        "code ++",
        "  !bla!   stufff",
        "  ! and also stufff stuff blabli",
        "code ++",
        " !blu! jcoqidkcj",
        " test test",
        " ! fals continuation",
        " test",
        "!bla! blibla !blue! bla isn't a valid title here, only blue is",
        "!SECTION! huhu",
        "!SUBSECTION! blibla",
        " stuff",
        "!TODO! something non-sensical",
        " stuff",
        "!TODO! something rather sensical",
        "// ! let's be serious for once",
        " blu blue",
        "!SECTION! another section"
    ]
    for line in test:
        print(line)
    print("\nPARSING\n")
    for it in ItemScanner(test):
        print(it.title, it.content)
    print("\nSORTING\n")
    
    print(format_MeuporgItem(parse_lines(test),
                             "fictitious/file.txt",
                             "Fictitious Tasks"))

