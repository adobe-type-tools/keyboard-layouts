#!/bin/env python

import codecs
import os
import re
import sys
import time
import unicodedata

import xml.etree.ElementTree as ET

# local modules
from klc_data import (
    win_to_mac_keycodes, win_keycodes,
    klc_keynames, klc_prefix_dummy, klc_suffix_dummy
)
from locale import (
    locale_id, locale_id_long, locale_tag, locale_name, locale_name_long,
)

version_info = {
    'version': 'v 1.00',
    'date': 'November 15, 2011',
    'filler': '-' * 80,
}

# -----------------------------------------------------------------------------

__doc__ = '''\
mac2winKeyboard %(version)s, %(date)s
%(filler)s
This Python script is intended for converting Mac keyboard layouts to Windows
.klc files, the input format for "Microsoft Keyboard Layout Creator" (MSKLC).
The resulting .klc files reflect the Mac keyboard layout, and can be used in
MSKLC to compile working keyboard layouts for Windows. Should any further
modifications be desired, the .klc files can also be edited with a text editor.

%(filler)s
Originally created for converting a bulk of Pi font keyboard layouts, this
script proved being useful for converting other, 'normal' layouts as well,
so the decision was made to make the script publicly available.

DISCLAIMER:
%(filler)s
This script tries to convert keyboard layouts from Mac to Windows as verbatim
as possible. Still, it is far from a linguistically accurate tool: Some of the
niceties possible in both Mac and Win keyboard layouts are not supported - for
instance, 'ligatures'. Nevertheless, it is assumed that this script will at
least help producing good base data to be extended on.

For now, 'ligatures' (2 or more characters assigned to one key) are not
supported in this conversion script. Ligature support on Windows keyboards is
spotty (no ligatures in Caps Lock states, for instance), and limited to four
characters per key. Used in very few keyboard layouts only, the decision was
made to insert a placeholder character instead.

Also, some shift states might be dropped in the conversion. This is necessary,
as Windows only supports six shift states, two of them with reduced features.

USAGE:
%(filler)s
(Example for converting the input file "special.keylayout"):

    python mac2winKeyboard.py special.keylayout

No further options or triggers are needed.
The output .klc file will be generated alongside the input file, the name will
be truncated to a Windows-style 8+3-digit file name. If the original file name
contains periods or spaces, they are stripped, not being supported in MSKLC.
Digits in the name (indicating a series) are preserved in the output file
name.

''' % version_info

__usage__ = '''
mac2winKeyboard %(version)s, %(date)s

Converts Mac keyboard layout files (.keylayout) to
equivalent Windows files (.klc).

OPTIONS:
%(filler)s

    python mac2winKeyboard [-u] [-h]

    -u  : write usage
    -h  : show help for further explanation.

USAGE:
%(filler)s

    python mac2winKeyboard inputfile.keylayout


''' % version_info

__help__ = __doc__

error_msg_conversion = (
    'Could not convert composed character {}, '
    'inserting replacement character ({}). Sorry.'
)
error_msg_filename = (
    'Too many digits for a Windows-style (8+3) filename.'
    'Please rename the source file.')

error_msg_macwin_mismatch = (
    "// No equivalent macOS code for Windows code {} ('{}'). Skipping.")

error_msg_winmac_mismatch = (
    "// Could not match Windows code {} ('{}') to Mac OS code {}. Skipping.")


# company = 'Adobe Systems Incorporated'
company = 'myCompany'
year = time.localtime()[0]
keyboard_name = sys.argv[1][:-10].split(os.sep)[-1]
keyboard_path = os.getcwd()


# Changing the line separator.
# This is important, as the output klc file must be UTF-16 LE with
# Windows-style line breaks.
os.linesep = '\r\n'

# Placeholder character for replacing 'ligatures' (more than one character
# mapped to one key), which are not supported by this conversion script.
replacement_char = '007E'

klc_prefix = klc_prefix_dummy.format(
    locale_tag, keyboard_name, year, company, company,
    locale_name, locale_id_long)
klc_suffix = klc_suffix_dummy.format(
    locale_id, keyboard_name, locale_id, locale_name_long)


class Key(object):

    def __init__(self, keymapset, keyindex, keycode, type, result):

        self.keymapset = keymapset
        self.keyindex = keyindex
        self.keycode = keycode
        self.type = type
        self.result = result
        self.output = []

    def data(self):

        self.output = [
            str(self.keymapset),
            int(self.keyindex),
            int(self.keycode),
            str(self.type),
            self.result]
        return self.output


class Action(object):

    def __init__(self, action, state, type, result):
        self.action = action
        self.state = state
        self.type = type
        self.result = result

    def data(self):
        output = [self.action, str(self.state), str(self.type), self.result]
        return output


class Parser(object):

    def __init__(self):
        # Raw keys as they are in the layout XML
        self.keylist = []

        # Raw list of actions collected from layout XML
        self.actionlist = []

        # Key output when state is None
        self.outputlist = []

        # Contains action IDs and the actual base keys (e.g. 'a', 'c' etc.)
        self.action_basekeys = {}

        # Dictionary {States : deadkeys}
        self.deadkeys = {}

        # Dictionary {deadkey: (basekey, output)}
        self.keydict = {}

        # A dictionary of dictionaries, collecting the outputs of
        # every key in each individual state.
        self.outputdict = {}

        # Actions that do not yield immediate output, but shift to a new state.
        self.empty_actions = []
        # Dictionary {keymap ID: modifier key}
        self.keymap_assignments = {}

        self.number_of_keymaps = 0

    def addKeys(self, key):
        self.key = key
        self.keylist.append(key.data())
        return self.keylist

    def addActions(self, action):
        self.action = action
        self.actionlist.append(action.data())
        return self.actionlist

    def checkSet(self, states, keymap, maxset, minset, string):
        '''
        Assign index numbers to the different shift states, by comparing
        them to the minimum and maximum possible modifier configurations.
        This is necessary as the arrangement in the Mac keyboard layout
        is arbitrary.
        '''

        if maxset.issuperset(states) and minset.issubset(states):
            self.keymap_assignments[string] = int(keymap)

    def parse(self, tree):

        idx_list = []  # Find the number of key indexes.

        default_max = set('command? caps?'.split())
        default_min = set(''.split())

        alt_max = set('anyOption caps? command?'.split())
        alt_min = set('anyOption'.split())

        shift_max = set('anyShift caps? command?'.split())
        shift_min = set('anyShift'.split())

        altshift_max = set('anyShift anyOption caps? command?'.split())
        altshift_min = set('anyShift anyOption'.split())

        cmd_max = set('command caps? anyShift? anyOption?'.split())
        cmd_min = set('command'.split())

        caps_max = set('caps anyShift? command?'.split())
        caps_min = set('caps'.split())

        cmdcaps_max = set('command caps anyShift?'.split())
        cmdcaps_min = set('command caps'.split())

        shiftcaps_max = set('anyShift caps anyOption?'.split())
        shiftcaps_min = set('anyShift caps'.split())

        for parent in tree.getiterator():

            if parent.tag == 'keyMapSelect':

                for child in parent:
                    idx = int(parent.get('mapIndex'))
                    idx_list.append(idx)

                    keymap = parent.get('mapIndex')
                    states = set(child.get('keys').split())
                    self.checkSet(
                        states, keymap, default_max, default_min, 'default')
                    self.checkSet(
                        states, keymap, shift_max, shift_min, 'shift')
                    self.checkSet(
                        states, keymap, alt_max, alt_min, 'alt')
                    self.checkSet(
                        states, keymap, altshift_max, altshift_min, 'altshift')
                    self.checkSet(
                        states, keymap, cmd_max, cmd_min, 'cmd')
                    self.checkSet(
                        states, keymap, caps_max, caps_min, 'caps')
                    self.checkSet(
                        states, keymap, cmdcaps_max, cmdcaps_min, 'cmdcaps')
                    self.checkSet(
                        states, keymap, shiftcaps_max, shiftcaps_min, 'shiftcaps')

            if parent.tag == 'keyMapSet':
                keymapset_id = parent.attrib['id']
                for child in parent:
                    keymap_index = child.attrib['index']
                    for child in child:
                        keycode = child.attrib['code']
                        if child.get('action') is None:
                            type = 'output'
                        else:
                            type = 'action'
                        output = child.get(type)
                        myKey = Key(
                            keymapset_id, keymap_index, keycode, type, output)
                        self.addKeys(myKey)

            if parent.tag == 'actions':
                for child in parent:
                    action_id = child.get('id')
                    for child in child:
                        if child.get('next') is None:
                            type = 'output'
                        else:
                            type = 'next'
                        state = child.get('state')
                        result = child.get(type)
                        myAction = Action(action_id, state, type, result)
                        self.addActions(myAction)

                        # Making a dictionary for key id to output.
                        # On the Mac keyboard, the 'a' for instance is often
                        # matched to an action, as it can produce
                        # agrave, aacute, etc.
                        if [state, type] == ['none', 'output']:
                            self.action_basekeys[action_id] = result

        self.number_of_keymaps = max(idx_list)
        # Yields the highest index assigned to a shift state - thus, the
        # number of shift states in the layout.

    def findDeadkeys(self):
        '''
        Returns dictionary self.deadkeys: contains the state ID and the Unicode
        value of actual dead key.
        (for instance, 's3': '02c6' - state 3: circumflex)
        Returns list of ids for 'empty' actions:
        this is for finding the ids of all key inputs that have
        no immediate output. This list is used later when an '@' is appended
        to the Unicode values, a Windows convention to mark dead keys.
        '''

        deadkey_id = 0
        keylist = []
        for [id, state, type, result] in self.actionlist:
            if [state, type, result] == ['none', 'output', '0020']:
                deadkey_id = id
            if id == deadkey_id and result != '0020':
                self.deadkeys[state] = result

            if [state, type] == ['none', 'next']:
                keylist.append([id, result])
                self.empty_actions.append(id)

        for i in keylist:
            if i[1] in list(self.deadkeys.keys()):
                i[1] = self.deadkeys[i[1]]

        self.action_basekeys.update(dict(keylist))
        # This is for adding the actual deadkeys (grave, acute etc)
        # to the dict action_basekeys

        return self.empty_actions
        return self.deadkeys

    def actionMatcher(self):
        '''
        Returns a list and a dictionary:
        Self.actionlist is extended by the base character, e.g.
        ['6', 's1', 'output', '00c1', '0041'] % action id, state, type, Aacute, A
        Self.action_basekeys are all the glyphs that can be combined
        with a dead key, e.g. A,E,I etc.
        '''

        for i in self.actionlist:
            if [i[1], i[2]] == ['none', 'output']:
                self.action_basekeys[i[0]] = i[3]

            if i[0] in list(self.action_basekeys.keys()):
                i.append(self.action_basekeys[i[0]])

        return self.actionlist
        return self.action_basekeys

    def findOutputs(self):
        '''
        Finding the real output values of all the keys, e.g. replacing the
        action IDs in the XML keyboard layout with the unicodes they actually
        return in their standard state.
        '''

        for i in self.keylist:
            if i[4] in self.empty_actions:
                i.append('@')
                # If the key is a real dead key, mark it.
                # This mark is used in 'makeOutputDict'.

            if i[4] in self.action_basekeys:
                i[3] = 'output'
                i[4] = self.action_basekeys[i[4]]
                self.outputlist.append(i)
            else:
                self.outputlist.append(i)

        return self.outputlist

    def makeDeadKeyTable(self):
        ''' Populates self.keydict, which maps a deadkey
        (e.g. 02dc, circumflex) to (base character, accented character)) tuples
        (e.g. 0041, 00c3 == A, Atilde)
        '''

        for i in self.actionlist:
            if i[1] in list(self.deadkeys.keys()):
                i.append(self.deadkeys[i[1]])

            if len(i) == 6:
                deadkey = i[5]
                basekey = i[4]
                result = i[3]
                if deadkey in self.keydict:
                    self.keydict[deadkey].append((basekey, result))
                else:
                    self.keydict[deadkey] = [(basekey, result)]

        return self.keydict

    def makeOutputDict(self):
        '''
        This script is configurated to work for the first keymap set of an
        XML keyboard layout only.
        Here, the filtering occurs:
        '''

        first_keymapset = self.outputlist[0][0]
        for i in self.outputlist:
            if i[0] != first_keymapset:
                self.outputlist.remove(i)
            key_id = i[2]

            li = []
            for i in range(self.number_of_keymaps + 1):
                li.append([i, '-1'])
                self.outputdict[key_id] = dict(li)

        for i in self.outputlist:
            keymapset = i[0]
            keymap_id = i[1]
            key_id = i[2]

            if len(i) == 5:
                output = i[4]
            else:
                output = i[4] + '@'
                # The string for making clear that this key is a deadkey.
                # Necessary in .klc files.

            self.outputdict[key_id][keymap_id] = output

        return self.outputdict

    def getOutput(self, dict, string):
        '''
        Used in next function, to find output per state, for every key.
        If no output, it returns '-1' (a.k.a. not defined).
        '''

        try:
            var = dict[self.keymap_assignments[string]]
        except KeyError:
            var = '-1'
        return var

    def writeKeyTable(self):
        output = []
        for d in sorted(win_keycodes.keys()):
            nwin = int(d, 16)

            if nwin not in win_to_mac_keycodes:
                print(error_msg_macwin_mismatch.format(nwin, win_keycodes[d]))
                continue
            n = win_to_mac_keycodes[nwin]
            if n not in self.outputdict:
                print(error_msg_winmac_mismatch.format(nwin, win_keycodes[d], n))
                continue

            u = self.outputdict[n]

            # Keytable follows the syntax of the .klc file.
            # The columns are as follows:

            # keytable[0]: scan code
            # keytable[1]: virtual key
            # keytable[2]: spacer (empty)
            # keytable[3]: caps (on or off, or SGCaps flag)
            # keytable[4]: output for default state
            # keytable[5]: output for shift
            # keytable[6]: output for ctrl (= cmd on mac)
            # keytable[7]: output for ctrl-shift (= cmd-caps lock on mac)
            # keytable[8]: output for altGr (= ctrl-alt)
            # keytable[9]: output for altGr-shift (= ctrl-alt-shift)
            # keytable[10]: descriptions.

            keytable = list((d, win_keycodes[d])) + ([""] * 9)

            default_output = self.getOutput(u, 'default')
            shift_output = self.getOutput(u, 'shift')
            alt_output = self.getOutput(u, 'alt')
            altshift_output = self.getOutput(u, 'altshift')
            caps_output = self.getOutput(u, 'caps')
            cmd_output = self.getOutput(u, 'cmd')
            cmdcaps_output = self.getOutput(u, 'cmdcaps')
            shiftcaps_output = self.getOutput(u, 'shiftcaps')

            # Checking if the caps lock output equals the shift key,
            # to set the caps lock status.
            if caps_output == default_output:
                keytable[3] = '0'
            elif caps_output == shift_output:
                keytable[3] = '1'
            else:
                keytable[3] = 'SGCap'
                # SGCaps are a Windows speciality, necessary if the caps lock
                # state is different from shift.
                # Usually, they accommodate an alternate writing system.
                # SGCaps + Shift is possible, boosting the available
                # shift states to 6.

            keytable[4] = default_output
            keytable[5] = shift_output
            keytable[6] = cmd_output
            keytable[7] = cmdcaps_output
            keytable[8] = alt_output
            keytable[9] = altshift_output
            keytable[10] = '// %s, %s, %s, %s, %s' % (
                udata(default_output),
                udata(shift_output),
                udata(cmd_output),
                udata(alt_output),
                udata(altshift_output))  # Key descriptions

            output.append('\t'.join(keytable))

            if keytable[3] == 'SGCap':
                output.append('-1\t-1\t\t0\t%s\t%s\t\t\t\t\t// %s, %s' % (
                    caps_output,
                    shiftcaps_output,
                    udata(caps_output),
                    udata(shiftcaps_output)))
        return output

    def writeDeadKeyTable(self):
        '''
        Writes a summary of dead keys, their results in all intended
        combinations.
        '''

        output = ['']
        for i in list(self.keydict.keys()):
            output.extend([''])
            output.append('DEADKEY\t%s' % i)
            output.append('')

            for j in self.keydict[i]:
                string = '%s\t%s\t// %s -> %s' % (
                    j[0], j[1], charFromUnicode(j[0]), charFromUnicode(j[1]))
                output.append(string)
        return output

    def writeKeynameDead(self):
        # List of dead keys contained in the keyboard layout.

        output = ['', 'KEYNAME_DEAD', '']
        for i in list(self.deadkeys.values()):
            output.append('%s\t"%s"' % (i, udata(i)))
        output.append('')

        if len(output) == 4:
            return ['', '']
        else:
            return output


### HELPER FUNCTIONS ###

def readFile(path):
    '''
    Read a file, make list of the lines, close the file.
    '''

    file = open(path, 'r')
    data = file.read().splitlines()
    file.close()
    return data


def uni_from_char(character):
    '''
    Returns a 4 or 5-digit Unicode hex string for the passed character.
    '''

    try:
        return '{0:04x}'.format(ord(character))

        # For now, 'ligatures' (2 or more characters assigned to one key)
        # are not supported in this conversion script.
        # Ligature support on Windows keyboards is spotty (no ligatures in
        # Caps Lock states, for instance), and limited to four characters
        # per key. Used in very few keyboard layouts only, the decision was
        # made to insert a placeholder character instead.

    except TypeError:
        print(error_msg_conversion.format(character, udata(replacement_char)))
        return replacement_char

    except ValueError:
        print(error_msg_conversion.format(character, udata(replacement_char)))
        return replacement_char


def charFromUnicode(unicodestring):
    '''
    Return character from a Unicode code point.
    '''

    if len(unicodestring) > 5:
        return unicodestring
    else:
        return chr(int(unicodestring, 16))


def udata(unicodestring):
    '''
    Return description of characters, e.g. 'DIGIT ONE', 'EXCLAMATION MARK' etc.
    '''

    if unicodestring in ['-1', '']:
        return '<none>'
    if unicodestring.endswith('@'):
        unicodestring = unicodestring[0:-1]
    else:
        unicodestring = unicodestring

    try:
        return unicodedata.name(charFromUnicode(unicodestring))
    except ValueError:
        return 'PUA %s' % (unicodestring)


def new_xml(file):
    '''
    Creates a new XML file in memory.
    Literal Unicode entities (&#x0000;) make the XML parser choke,
    that's why some replacement operations are necessary.
    Also, all literal output characters are converted to Unicode strings
    (0000, FFFF, 1FF23 etc).
    '''

    newxml = []
    output_line = re.compile(r'(output=[\"\'])(.+?)([\"\'])')
    uni_value = re.compile(r'&#x([a-fA-F0-9]{4,6});')
    uni_lig = re.compile(r'((&#x[a-fA-F0-9]{4};){2,})')

    for line in readFile(file):

        if line[:5] == '<?XML':
            line = '<?xml%s' % line[5:]
            # This avoids the parser to fail right in the first line:
            # sometimes, files start with '<?XML' rather than '<?xml',
            # which causes mayhem.

        if re.search(output_line, line):
            if re.search(uni_lig, line):
                print(error_msg_conversion.format(
                    re.search(uni_lig, line).group(1),
                    udata(replacement_char)))
                line = re.sub(uni_lig, replacement_char, line)
            elif re.search(uni_value, line):
                line = re.sub(uni_value, r'\1', line)
            else:
                query = re.search(output_line, line)
                character = query.group(2)
                replacement = '%s%s%s' % (
                    query.group(1), uni_from_char(character), query.group(3))
                line = re.sub(output_line, replacement, line)

        newxml.append(line)
    return '\r'.join(newxml)


### THE ACTUAL FUNCTION ###

def run():

    if '-u' in sys.argv:
        print(__usage__)
        return

    if "-h" in sys.argv:
        print(__help__)
        return

    if "-d" in sys.argv:
        print(__doc__)
        return

    inputfile = sys.argv[1]
    if inputfile.split('.')[1] != 'keylayout':
        print()
        print('Input file not recognized.')
        print('Please use an XML-based *.keylayout file.')
        print()
        return

    newxml = new_xml(inputfile)
    tree = ET.XML(newxml)

    keyboardData = Parser()
    keyboardData.parse(tree)
    keyboardData.findDeadkeys()
    keyboardData.actionMatcher()
    keyboardData.findOutputs()
    keyboardData.makeDeadKeyTable()
    keyboardData.makeOutputDict()

    output = []
    output.extend(klc_prefix.splitlines())
    output.extend(keyboardData.writeKeyTable())
    output.extend(keyboardData.writeDeadKeyTable())
    output.extend(klc_keynames)
    output.extend(keyboardData.writeKeynameDead())
    output.extend(klc_suffix.splitlines())


### FILE HANDLING ###

    # As the Windows .dll files allow for 8-digit file names only, the output
    # file name is truncated. If the input file name contains a number (being
    # part of a series), this number is appended to the end of the output file
    # name. If this number is longer than 8 digits, the script will gently
    # ask to modify the input file name.

    # Periods and spaces in the file name are not supported; MSKLC will not
    # build the .dll if the .klc has any.
    # This is why they are being stripped here:

    filename = re.sub(r'[. ]', '', keyboard_name)

    digit = re.compile(r'(\d+)')
    digit_m = digit.search(filename)

    if digit_m:
        trunc = 8 - len(digit_m.group(1))
        if trunc <= 0:
            print(error_msg_filename)
            sys.exit()
        else:
            filename = '%s%s.klc' % (filename[:trunc], digit_m.group(1))
    else:
        filename = '%s.klc' % (filename[:8])

    outputfile = codecs.open(
        os.sep.join((keyboard_path, filename)), 'w', 'utf-16')
    for i in output:
        outputfile.write(i)
        outputfile.write(os.linesep)
    outputfile.close()

    print('done')


if __name__ == "__main__":
    run()
