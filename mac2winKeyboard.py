#!/bin/env python
'''
Convert macOS keyboard layout files (.keylayout) to
equivalent Windows files (.klc).
'''

import os
import re
import sys
import time

import argparse
import codecs
import unicodedata

import xml.etree.ElementTree as ET

# local modules
from data.klc_data import (
    win_to_mac_keycodes, win_keycodes,
    klc_keynames, klc_prologue_dummy, klc_epilogue_dummy
)
from data.locale_data import (
    keyboard_description, language_id, language_name, language_tag
)

error_msg_conversion = (
    'Could not convert composed character {}, '
    'inserting replacement character ({}).'
)
error_msg_filename = (
    'Too many digits for a Windows-style (8+3) filename. '
    'Please rename the source file.')

error_msg_macwin_mismatch = (
    "// No equivalent macOS code for Windows code {} ('{}'). Skipping.")

error_msg_winmac_mismatch = (
    "// Could not match Windows code {} ('{}') to Mac OS code {}. Skipping.")


# Change the line separator.
# This is important, as the output klc file must be UTF-16 LE with
# Windows-style line breaks.
os.linesep = '\r\n'

# Placeholder character for replacing 'ligatures' (more than one character
# mapped to one key), which are not supported by this conversion script.
replacement_char = '007E'


class KeylayoutParser(object):

    def __init__(self, tree):
        # raw keys as they are in the layout XML
        self.key_list = []

        # raw list of actions collected from layout XML
        self.action_list = []

        # key output when state is None
        self.output_list = []

        # action IDs and actual base keys (e.g. 'a', 'c' etc.)
        self.action_basekeys = {}

        # {states: deadkeys}
        self.deadkeys = {}

        # {deadkey: (basekey, output)}
        self.deadkey_dict = {}

        # A dict of dicts, collecting the outputs of every key
        # in each individual state.
        self.output_dict = {}

        # Actions that do not yield immediate output, but shift to a new state.
        self.empty_actions = []

        # {keymap ID: modifier key}
        self.keymap_assignments = {}

        self.number_of_keymaps = 0

        self.parse(tree)
        self.find_deadkeys()
        self.match_actions()
        self.find_outputs()
        self.make_deadkey_dict()
        self.make_output_dict()

    def check_states(self, states, keymap, maxset, minset, mod_name):
        '''
        Assign index numbers to the different shift states, by comparing
        them to the minimum and maximum possible modifier configurations.
        This is necessary as the arrangement in the Mac keyboard layout
        is arbitrary.
        '''

        if maxset.issuperset(states) and minset.issubset(states):
            self.keymap_assignments[mod_name] = int(keymap)

    def parse(self, tree):

        keymap_idx_list = []  # Find the number of keymap indexes.

        default_max = {'command?', 'caps?'}
        default_min = set()

        alt_max = {'anyOption', 'caps?', 'command?'}
        alt_min = {'anyOption'}

        shift_max = {'anyShift', 'caps?', 'command?'}
        shift_min = {'anyShift'}

        altshift_max = {'anyShift', 'anyOption', 'caps?', 'command?'}
        altshift_min = {'anyShift', 'anyOption'}

        cmd_max = {'command', 'caps?', 'anyShift?', 'anyOption?'}
        cmd_min = {'command'}

        caps_max = {'caps', 'anyShift?', 'command?'}
        caps_min = {'caps'}

        cmdcaps_max = {'command', 'caps', 'anyShift?'}
        cmdcaps_min = {'command', 'caps'}

        shiftcaps_max = {'anyShift', 'caps', 'anyOption?'}
        shiftcaps_min = {'anyShift', 'caps'}

        for parent in tree.iter():

            if parent.tag == 'keyMapSelect':
                for modifier in parent:
                    keymap_index = int(parent.get('mapIndex'))
                    keymap_idx_list.append(keymap_index)

                    keymap = parent.get('mapIndex')
                    states = set(modifier.get('keys').split())

                    self.check_states(
                        states, keymap, default_max, default_min, 'default')
                    self.check_states(
                        states, keymap, shift_max, shift_min, 'shift')
                    self.check_states(
                        states, keymap, alt_max, alt_min, 'alt')
                    self.check_states(
                        states, keymap, altshift_max, altshift_min, 'altshift')
                    self.check_states(
                        states, keymap, cmd_max, cmd_min, 'cmd')
                    self.check_states(
                        states, keymap, caps_max, caps_min, 'caps')
                    self.check_states(
                        states, keymap, cmdcaps_max, cmdcaps_min, 'cmdcaps')
                    self.check_states(
                        states, keymap,
                        shiftcaps_max, shiftcaps_min, 'shiftcaps')

            if parent.tag == 'keyMapSet':
                keymapset_id = parent.attrib['id']
                for keymap in parent:
                    keymap_index = int(keymap.attrib['index'])
                    for key in keymap:
                        key_code = int(key.attrib['code'])
                        if key.get('action') is None:
                            key_type = 'output'
                        else:
                            key_type = 'action'
                        output = key.get(key_type)

                        self.key_list.append([
                            keymapset_id, keymap_index,
                            key_code, key_type, output])

            if parent.tag == 'actions':
                for action in parent:
                    action_id = action.get('id')
                    for action_trigger in action:
                        if action_trigger.get('next') is None:
                            action_type = 'output'
                        else:
                            action_type = 'next'
                        state = action_trigger.get('state')

                        # result can be a code point or another state
                        result = action_trigger.get(action_type)
                        self.action_list.append([
                            action_id, state, action_type, result])

                        # Make a dictionary for key id to output.
                        # On the Mac keyboard, the 'a' for example is often
                        # matched to an action, as it can produce
                        # agrave, aacute, etc.
                        if [state, action_type] == ['none', 'output']:
                            self.action_basekeys[action_id] = result

        # Yield the highest index assigned to a shift state - thus, the
        # number of shift states in the layout.
        self.number_of_keymaps = max(keymap_idx_list)

    def find_deadkeys(self):
        '''
        Populate dictionary self.deadkeys which contains the state ID
        and the code point of an actual dead key.
        (for instance, '3': '02c6' state 3: circumflex)

        Populate list of IDs for 'empty' actions, for finding IDs of all key
        inputs that have no immediate output.
        This list is used later when an '@' is appended to the code points,
        a Windows convention to mark dead keys.
        '''

        deadkey_id = 0
        key_list = []
        for [key_id, state, key_type, result] in self.action_list:
            if [state, key_type, result] == ['none', 'output', '0020']:
                deadkey_id = key_id
            if key_id == deadkey_id and result != '0020':
                self.deadkeys[state] = result

            if [state, key_type] == ['none', 'next']:
                key_list.append([key_id, result])
                self.empty_actions.append(key_id)

        key_list_2 = []
        for state, result_state in key_list:
            if result_state in self.deadkeys.keys():
                cp_result = self.deadkeys[result_state]
                key_list_2.append((state, cp_result))

        # Add the actual deadkeys (grave, acute etc)
        # to the dict action_basekeys
        self.action_basekeys.update(dict(key_list_2))

    def match_actions(self):
        '''
        Extend self.action_list is extended by the base character, e.g.

        [
            '6', # action id
            's1',  # state
            'output',  # type
            '00c1',  # Á
            '0041',  # A
        ]

        Populate self.action_basekeys -- all the glyphs that can be combined
        with a dead key, e.g. A,E,I etc.

        '''

        for action_data in self.action_list:
            key_id, state, key_type, result = action_data
            if [state, key_type] == ['none', 'output']:
                self.action_basekeys[key_id] = result

            if key_id in self.action_basekeys.keys():
                action_data.append(self.action_basekeys[key_id])

    def find_outputs(self):
        '''
        Find the real output values of all the keys, e.g. replacing the
        action IDs in the XML keyboard layout with the code points they
        return in their standard state.
        '''

        for key_data in self.key_list:
            output = key_data[4]
            if output in self.empty_actions:
                # If the key is a real dead key, mark it.
                # This mark is used in 'make_output_dict'.
                key_data.append('@')

            if output in self.action_basekeys:
                key_data[3] = 'output'
                key_data[4] = self.action_basekeys[output]
                self.output_list.append(key_data)
            else:
                self.output_list.append(key_data)

    def make_deadkey_dict(self):
        '''
        Populate self.deadkey_dict, which maps a deadkey
        e.g. (02dc, circumflex) to (base character, accented character) tuples
        e.g. 0041, 00c3 = A, Ã
        '''

        for action in self.action_list:
            if action[1] in self.deadkeys.keys():
                action.append(self.deadkeys[action[1]])

            if len(action) == 6:
                deadkey = action[5]
                basekey = action[4]
                result = action[3]
                if deadkey in self.deadkey_dict:
                    self.deadkey_dict[deadkey].append((basekey, result))
                else:
                    self.deadkey_dict[deadkey] = [(basekey, result)]

    def make_output_dict(self):
        '''
        This script is configured to work for the first keymap set of an
        XML keyboard layout only.
        Here, the filtering occurs:
        '''

        first_keymapset = self.output_list[0][0]
        self.output_list = [key_data
                            for key_data in self.output_list
                            if key_data[0] == first_keymapset]

        for key_data in self.output_list:
            keymap_id = key_data[1]
            key_id = key_data[2]

            # filling the key ID output dict with dummy output
            li = []
            for i in range(self.number_of_keymaps + 1):
                li.append([i, '-1'])
            self.output_dict[key_id] = dict(li)

        for key_data in self.output_list:
            keymap_id = key_data[1]
            key_id = key_data[2]

            if len(key_data) == 5:
                output = key_data[4]
            else:
                # The @ is marking this key as a deadkey in .klc files.
                output = key_data[4] + '@'

            self.output_dict[key_id][keymap_id] = output

    def get_key_output(self, key_output_dict, state):
        '''
        Used to find output per state, for every key.
        If no output, return '-1' (a.k.a. not defined).
        '''

        try:
            output = key_output_dict[self.keymap_assignments[state]]
        except KeyError:
            output = '-1'
        return output

    def get_key_table(self):
        kt_output = []
        for win_kc_hex, win_kc_name in sorted(win_keycodes.items()):
            win_kc_int = int(win_kc_hex, 16)

            if win_kc_int not in win_to_mac_keycodes:
                print(error_msg_macwin_mismatch.format(
                    win_kc_int, win_keycodes[win_kc_hex]))
                continue

            mac_kc = win_to_mac_keycodes[win_kc_int]
            if mac_kc not in self.output_dict:
                print(error_msg_winmac_mismatch.format(
                    win_kc_int, win_keycodes[win_kc_hex], mac_kc))
                continue

            outputs = self.output_dict[mac_kc]

            # The key_table follows the syntax of the .klc file.
            # The columns are as follows:

            # key_table[0]: scan code
            # key_table[1]: virtual key
            # key_table[2]: spacer (empty)
            # key_table[3]: caps (on or off, or SGCaps flag)
            # key_table[4]: output for default state
            # key_table[5]: output for shift
            # key_table[6]: output for ctrl (= cmd on mac)
            # key_table[7]: output for ctrl-shift (= cmd-caps lock on mac)
            # key_table[8]: output for altGr (= ctrl-alt)
            # key_table[9]: output for altGr-shift (= ctrl-alt-shift)
            # key_table[10]: descriptions.

            key_table = list((win_kc_hex, win_kc_name)) + ([""] * 9)

            default_output = self.get_key_output(outputs, 'default')
            shift_output = self.get_key_output(outputs, 'shift')
            alt_output = self.get_key_output(outputs, 'alt')
            altshift_output = self.get_key_output(outputs, 'altshift')
            caps_output = self.get_key_output(outputs, 'caps')
            cmd_output = self.get_key_output(outputs, 'cmd')
            cmdcaps_output = self.get_key_output(outputs, 'cmdcaps')
            shiftcaps_output = self.get_key_output(outputs, 'shiftcaps')

            # Check if the caps lock output equals the shift key,
            # to set the caps lock status.
            if caps_output == default_output:
                key_table[3] = '0'
            elif caps_output == shift_output:
                key_table[3] = '1'
            else:
                # SGCaps are a Windows speciality, necessary if the caps lock
                # state is different from shift.
                # Usually, they accommodate an alternate writing system.
                # SGCaps + Shift is possible, boosting the available
                # shift states to 6.
                key_table[3] = 'SGCap'

            key_table[4] = default_output
            key_table[5] = shift_output
            key_table[6] = cmd_output
            key_table[7] = cmdcaps_output
            key_table[8] = alt_output
            key_table[9] = altshift_output
            key_table[10] = (
                f'// {char_description(default_output)}, '
                f'{char_description(shift_output)}, '
                f'{char_description(cmd_output)}, '
                f'{char_description(cmdcaps_output)}, '
                f'{char_description(alt_output)}, '
                f'{char_description(altshift_output)}')  # key descriptions

            kt_output.append('\t'.join(key_table))

            if key_table[3] == 'SGCap':
                kt_output.append((
                    f'-1\t-1\t\t0\t{caps_output}\t'
                    f'{shiftcaps_output}\t\t\t\t\t'
                    f'// {char_description(caps_output)}, '
                    f'{char_description(shiftcaps_output)}'))
        return kt_output

    def get_deadkey_table(self):
        '''
        Summary of dead keys, and their results in all intended combinations.
        '''

        dk_table = ['']
        for cp_dead, base_result_list in self.deadkey_dict.items():
            # we want the space character to be last in the list,
            # otherwise MSKLC complains (not sure if consequential)
            sorted_base_result_list = sorted(
                base_result_list, key=lambda x: int(x[0], 16), reverse=True)
            dk_table.extend([''])
            dk_table.append(f'DEADKEY\t{cp_dead}')
            dk_table.append('')

            for cp_base, cp_result in sorted_base_result_list:
                char_base = char_from_hex(cp_base)
                char_result = char_from_hex(cp_result)
                line = (
                    f'{cp_base}\t{cp_result}\t'
                    f'// {char_base} -> {char_result}')
                dk_table.append(line)
        return dk_table

    def get_keyname_dead(self):
        '''
        List of dead keys contained in the klc keyboard layout.
        '''

        list_keyname_dead = ['', 'KEYNAME_DEAD', '']
        # for codepoint in sorted(self.deadkeys.values()):
        for codepoint in self.deadkeys.values():
            list_keyname_dead.append(
                f'{codepoint}\t"{char_description(codepoint)}"')
        list_keyname_dead.append('')

        if len(list_keyname_dead) == 4:
            # no deadkeys, no KEYNAME_DEAD list
            return ['', '']
        else:
            return list_keyname_dead


def read_file(path):
    '''
    Read a file, make list of the lines, close the file.
    '''

    with open(path, 'r', encoding='utf-8') as f:
        data = f.read().splitlines()
    return data


def codepoint_from_char(character):
    '''
    Return a 4 or 5-digit Unicode hex string for the passed character.
    '''

    try:
        return '{0:04x}'.format(ord(character))

        # For now, 'ligatures' (2 or more code points assigned to one key)
        # are not supported in this conversion script.
        # Ligature support on Windows keyboards is spotty (no ligatures in
        # Caps Lock states, for instance), and limited to four code points
        # per key. Used in very few keyboard layouts only, the decision was
        # made to insert a placeholder instead.

    except TypeError:
        print(error_msg_conversion.format(
            character, char_description(replacement_char)))
        return replacement_char


def char_from_hex(hex_string):
    '''
    Return character from a Unicode code point.
    '''

    return chr(int(hex_string, 16))


def char_description(hex_string):
    '''
    Return description of characters, e.g. 'DIGIT ONE', 'EXCLAMATION MARK' etc.
    '''
    if hex_string in ['-1', '']:
        return '<none>'
    hex_string = hex_string.rstrip('@')

    try:
        return unicodedata.name(char_from_hex(hex_string))
    except ValueError:
        return 'PUA {}'.format(hex_string)


def filter_xml(input_keylayout):
    '''
    Filter xml-based .keylayout file.
    Unicode entities (&#x0000;) make the ElementTree xml parser choke,
    that’s why some replacement operations are necessary.
    Also, all literal output characters are converted to code points
    (0000, ffff, 1ff23 etc) for easier handling downstream.
    '''

    rx_uni_lig = re.compile(r'((&#x[a-fA-F0-9]{4};){2,})')
    rx_hex_escape = re.compile(r'&#x([a-fA-F0-9]{4,6});')
    rx_output_line = re.compile(r'(output=[\"\'])(.+?)([\"\'])')

    # Fixing the first line to make ElementTree not stumble
    # over a capitalized XML tag
    filtered_xml = ['<?xml version="1.0" encoding="UTF-8"?>']

    for line in read_file(input_keylayout)[1:]:

        if re.search(rx_output_line, line):
            if re.search(rx_uni_lig, line):
                # More than 1 output character.
                # Not supported, so fill in replacement char instead.
                lig_characters = re.search(rx_uni_lig, line).group(1)
                print(error_msg_conversion.format(
                    lig_characters, char_description(replacement_char)))
                line = re.sub(rx_uni_lig, replacement_char.lower(), line)
            elif re.search(rx_hex_escape, line):
                # Escaped code point, e.g. &#x0020;
                # Remove everything except the code point.
                query = re.search(rx_hex_escape, line)
                codepoint = query.group(1).lower()
                line = re.sub(rx_hex_escape, codepoint, line)
            else:
                # Normal character output.
                # Replace the character by a code point
                query = re.search(rx_output_line, line)
                char_pre = query.group(1)  # output="
                character = query.group(2)
                codepoint = codepoint_from_char(character).lower()
                char_suff = query.group(3)  # "
                replacement_line = ''.join((char_pre, codepoint, char_suff))
                line = re.sub(rx_output_line, replacement_line, line)

        filtered_xml.append(line)

    return '\n'.join(filtered_xml)


def make_klc_filename(keyboard_name):
    '''
    Windows .dll files allow for 8-character file names only, which is why the
    output file name is truncated. If the input file name contains a number
    (being part of a series), this number is appended to the end of the output
    file name. If this number is longer than 8 digits, the script will gently
    ask to modify the input file name.

    Periods and spaces in the file name are not supported; MSKLC will not
    build the .dll if the .klc has any.
    This is why they are stripped here.
    '''

    # strip periods and spaces
    filename = re.sub(r'[. ]', '', keyboard_name)

    # find digit(s) at tail of file name
    rx_digit = re.compile(r'(\d+?)$')
    match_digit = rx_digit.search(filename)

    if match_digit:
        trunc = 8 - len(match_digit.group(1)) - 1
        if trunc < 0:
            print(error_msg_filename)
            sys.exit(-1)
        else:
            filename = '{}_{}.klc'.format(
                filename[:trunc], match_digit.group(1))
    else:
        filename = '{}.klc'.format(filename[:8])
    return filename


def process_input_keylayout(input_keylayout):
    filtered_xml = filter_xml(input_keylayout)
    tree = ET.XML(filtered_xml)
    keyboard_data = KeylayoutParser(tree)
    return keyboard_data


def make_keyboard_name(input_path):
    '''
    Return the base name of the .keylayout file
    '''
    input_file = os.path.basename(input_path)
    return os.path.splitext(input_file)[0]


def verify_input_file(parser, input_file):
    '''
    Check if the input file exists, and if the suffix is .keylayout

    https://stackoverflow.com/a/15203955
    '''
    if not os.path.exists(input_file):
        parser.error('This input file does not exist')

    suffix = os.path.splitext(input_file)[-1]

    if suffix.lower() != '.keylayout':
        parser.error('Please use a xml-based .keylayout file')
    return input_file


def make_klc_prologue(keyboard_name):

    # company = 'Adobe Systems Incorporated'
    company = 'myCompany'
    year = time.localtime()[0]

    return klc_prologue_dummy.format(
        keyboard_name, keyboard_description, year, company, company,
        language_tag, language_id)


def make_klc_epilogue():

    return klc_epilogue_dummy.format(
        keyboard_description, language_name)


def make_klc_data(keyboard_name, keyboard_data):
    klc_prologue = make_klc_prologue(keyboard_name)
    klc_epilogue = make_klc_epilogue()

    klc_data = []
    klc_data.extend(klc_prologue.splitlines())
    klc_data.extend(keyboard_data.get_key_table())
    klc_data.extend(keyboard_data.get_deadkey_table())
    klc_data.extend(klc_keynames)
    klc_data.extend(keyboard_data.get_keyname_dead())
    klc_data.extend(klc_epilogue.splitlines())
    return klc_data


def get_args(args=None):

    parser = argparse.ArgumentParser(
        description=__doc__)

    parser.add_argument(
        'input',
        type=lambda input_file: verify_input_file(parser, input_file),
        help='input .keylayout file'
    )

    parser.add_argument(
        '-o', '--output_dir',
        help='output directory',
        metavar='DIR',
    )

    return parser.parse_args(args)


def run(args):
    input_file = args.input

    if args.output_dir:
        output_dir = args.output_dir
    else:
        output_dir = os.path.abspath(os.path.dirname(input_file))

    keyboard_data = process_input_keylayout(input_file)
    keyboard_name = make_keyboard_name(input_file)
    klc_filename = make_klc_filename(keyboard_name)
    klc_data = make_klc_data(keyboard_name, keyboard_data)

    output_path = os.sep.join((output_dir, klc_filename))
    with codecs.open(output_path, 'w', 'utf-16') as output_file:
        for line in klc_data:
            output_file.write(line)
            output_file.write(os.linesep)

    print(f'{keyboard_name} written to {klc_filename}')


if __name__ == '__main__':
    args = get_args()
    run(args)
