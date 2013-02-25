#!/bin/env python


d = {
'version': 'v 1.00',
'date': 'November 15, 2011',
'filler': '-' * 80,
}

__copyright__ =  '''\
Copyright (c) 2011 Adobe Systems Incorporated

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
the Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''
#-------------------------------------------------------------------------------

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
This script tries to convert keyboard layouts from Mac to Windows as verbatim as
possible. Still, it is far from a linguistically accurate tool: Some of the
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
contains periods and/or spaces, they are stripped, not being supported in MSKLC.
Digits in the name (indicating a series), those are preserved in the output file
name.

''' % d

__usage__ = '''
mac2winKeyboard %(version)s, %(date)s
Converts Mac keyboard layout files (.keylayout) to equivalent Windows files (.klc).

OPTIONS:
%(filler)s

	python mac2winKeyboard [-u] [-h]

	-u	: write usage
	-h	: show help for further explanation.

USAGE:
%(filler)s

	python mac2winKeyboard inputfile.keylayout


''' % d

__help__ = __doc__




import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element, SubElement
import sys, time, re, os
import unicodedata, codecs

#company = 'Adobe Systems Incorporated'
company = 'myCompany'
year = time.localtime()[0]
keyboard_name = sys.argv[1][:-10].split(os.sep)[-1]
keyboard_path = os.sep.join(sys.argv[1].split(os.sep)[:-1])

### Neutral:

locale_id = '0000'
locale_id_long = '00000000'
name = 'NE'
locale_name = 'ne-NE'
locale_name_long = 'Neutral (Neutral)'

### US English:

# locale_id = '0409'
# locale_id_long = '00000409'
# name = 'US'
# locale_name = 'en-US'
# locale_name_long = 'English (US)'

### German:

# locale_id = '0C07'
# locale_id_long = '00000C07'
# name = 'DE'
# locale_name = 'de-DE'
# locale_name_long = 'German (DE)'

### French:

# locale_id = '080C'
# locale_id_long = '0000080C'
# name = 'FR'
# locale_name = 'fr-FR'
# locale_name_long = 'French (FR)'

### more: http://msdn.microsoft.com/en-us/library/windows/desktop/dd318693(v=vs.85).aspx

os.linesep = '\r\n' # This is important, as the resulting text file must be UTF-16 LE with Windows-style line breaks.
replacement_char = '007E' # Placeholder character for replacing 'ligatures' (more than one character mapped to one key), which are not supported by this conversion script.

class Key(object):

	def __init__(self, keymapset, keyindex, keycode, type, result):

		self.keymapset = keymapset
		self.keyindex = keyindex
		self.keycode = keycode
		self.type = type
		self.result = result
		self.output = []

	def data(self):

		self.output = [str(self.keymapset), int(self.keyindex), int(self.keycode), str(self.type), self.result]
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
		self.keylist = [] 				# Raw keys as they are in the layout XML
 		self.actionlist = [] 			# Raw list of actions collected from layout XML
 		self.outputlist = [] 			# Key output when state == None
 		self.action_basekeys = {} 		# Contains action IDs and the actual base keys (e.g. 'a', 'c' etc.)
		self.deadkeys = {} 				# Dictionary {States : deadkeys}
 		self.keydict = {} 				# Dictionary {deadkey: (basekey, output)}
 		self.outputdict = {}			# A dictionary of dictionaries, collecting the outputs of every key in each individual state.
		self.empty_actions = []			# Actions that do not yield immediate output, but shift to a new state.
		self.keymap_assignments = {}	# Dictionary {keymap ID: modifier key}
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
		# Assigns index numbers to the different shift states, by comparing them to the minimum and maximum possible modifier configurations.
		# This is necessary as the arrangement in the Mac keyboard layout is arbitrary.

		if maxset.issuperset(states) and minset.issubset(states):
			self.keymap_assignments[string] = int(keymap)

	def parse(self, tree):

		idx_list = [] # Finding the number of key indexes.

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
					self.checkSet(states, keymap, default_max, default_min, 'default')
					self.checkSet(states, keymap, shift_max, shift_min, 'shift')
					self.checkSet(states, keymap, alt_max, alt_min, 'alt')
					self.checkSet(states, keymap, altshift_max, altshift_min, 'altshift')
					self.checkSet(states, keymap, cmd_max, cmd_min, 'cmd')
					self.checkSet(states, keymap, caps_max, caps_min, 'caps')
					self.checkSet(states, keymap, cmdcaps_max, cmdcaps_min, 'cmdcaps')
					self.checkSet(states, keymap, shiftcaps_max, shiftcaps_min, 'shiftcaps')


			if parent.tag == 'keyMapSet':
				keymapset_id = parent.attrib['id']
				for child in parent:
					keymap_index = child.attrib['index']
					for child in child:
						keycode = child.attrib['code']
						if child.get('action') == None:
							type = 'output'
						else:
							type = 'action'
						output = child.get(type)
						myKey = Key(keymapset_id, keymap_index, keycode, type, output)
						self.addKeys(myKey)


			if parent.tag == 'actions':
				for child in parent:
					action_id = child.get('id')
					for child in child:
						if child.get('next') == None:
							type = 'output'
						else:
							type = 'next'
						state = child.get('state')
						result = child.get(type)
						myAction = Action(action_id, state, type, result)
						self.addActions(myAction)

						# Making a dictionary for key id to output.
						# On the Mac keyboard, the 'a' for instance is often matched to an action, as it can produce agrave, aacute, etc.
						if [state, type] == ['none', 'output']:
							self.action_basekeys[action_id] = result

		self.number_of_keymaps = max(idx_list)	# Yields the highest index assigned to a shift state - thus, the number of shift states in the layout.

	def findDeadkeys(self):
		# Returns dictionary self.deadkeys: contains the state ID and the unicode value of actual dead key (for instance, 's3': '02c6' - state 3: circumflex)
		# Returns list of ids for 'empty' actions: this is for finding the ids of all key inputs that have no immediate output.
		# This list is used later when an '@' is appended to the unicode values, a Windows convention to mark dead keys.

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
			if i[1] in self.deadkeys.keys():
				i[1] = self.deadkeys[i[1]]

		self.action_basekeys.update(dict(keylist)) # This is for adding the actual deadkeys (grave, acute etc) to the dict action_basekeys

 		return self.empty_actions
		return self.deadkeys


	def actionMatcher(self):
		# Returns a list and a dictionary:
		# Self.actionlist is extended by the base character, e.g. ['6', 's1', 'output', '00c1', '0041'] % action id, state, type, Aacute, A
		# Self.action_basekeys are all the glyphs that can be combined with a dead key, e.g. A,E,I etc.

		for i in self.actionlist:
			if [i[1], i[2]] == ['none', 'output']:
				self.action_basekeys[i[0]] = i[3]

			if i[0] in self.action_basekeys.keys():
				i.append(self.action_basekeys[i[0]])

		return self.actionlist
 		return self.action_basekeys


	def findOutputs(self):
		# Finding the real output values of all the keys, e.g. replacing the actions IDs in the XML keyboard layout with the unicodes they actually return in their standard state.

 		for i in self.keylist:
 			if i[4] in self.empty_actions:
  				i.append('@') # If the key is a real dead key, mark it. This mark is being used in 'makeOutputDict'.

			if self.action_basekeys.has_key(i[4]):
				i[3] = 'output'
				i[4] = self.action_basekeys[i[4]]
				self.outputlist.append(i)
 			else:
 				self.outputlist.append(i)

		return self.outputlist


	def makeDeadKeyTable(self):
		# Populates self.keydict, which maps a deadkey (e.g. 02dc, circumflex) to (base character, accented character)) tuples (e.g. 0041, 00c3 == A, Atilde)

		for i in self.actionlist:
			if i[1] in self.deadkeys.keys():
				i.append(self.deadkeys[i[1]])

			if len(i) == 6:
				deadkey = i[5]
				basekey = i[4]
				result = i[3]
 				if self.keydict.has_key(deadkey):
					self.keydict[deadkey].append((basekey, result))
				else:
					self.keydict[deadkey] = [(basekey, result)]

		return self.keydict

	def makeOutputDict(self):
		# This script is configurated to work for the first keymap set of an XML keyboard layout only.
		# Here, the filtering occurs:

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
				output = i[4] + '@' # The string for making clear that this key is a deadkey. Necessary in .klc files.

			self.outputdict[key_id][keymap_id] = output

		return self.outputdict

	def getOutput(self, dict, string):
			# Used in next function, to find output per state, for every key. If no output, it returns '-1' (a.k.a. not defined).

			try: var = dict[self.keymap_assignments[string]]
			except KeyError: var = '-1'
			return var


	def writeKeyTable(self):
		output = []
		for d in sorted(windata.keys()):
			nwin = int(d, 16)

			if not nwin in winmac:
				print "// No equivalent Mac OS code for Windows code %s ('%s'). Skipping." % (nwin, windata[d])
				continue
			n = winmac[nwin]
			if not n in self.outputdict:
				print "// Could not match Windows code %s ('%s') to Mac OS code %s. Skipping." % (nwin, windata[d], n)
				continue

			u = self.outputdict[n]

			# Keytable follows the syntax of the .klc file. The columns are as follows:
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

			keytable = list((d, windata[d])) + ([""]*9)


			default_output = self.getOutput(u, 'default')
			shift_output = self.getOutput(u, 'shift')
			alt_output = self.getOutput(u, 'alt')
			altshift_output = self.getOutput(u, 'altshift')
			caps_output = self.getOutput(u, 'caps')
			cmd_output = self.getOutput(u, 'cmd')
			cmdcaps_output = self.getOutput(u, 'cmdcaps')
			shiftcaps_output = self.getOutput(u, 'shiftcaps')

			# Checking if the caps lock output equals the shift key, to set the caps lock status.
			if caps_output == default_output:
				keytable[3] = '0'
			elif caps_output == shift_output:
				keytable[3] = '1'
 			else:
				keytable[3] = 'SGCap'
				# SGCaps are a Windows speciality, necessary if the caps lock state is different from shift.
				# Usually, they accommodate an alternate writing system. SGCaps + Shift is possible, boosting the available shift states to 6.

			keytable[4] = default_output
			keytable[5] = shift_output
			keytable[6] = cmd_output
			keytable[7] = cmdcaps_output
			keytable[8] = alt_output
			keytable[9] = altshift_output
			keytable[10] = '// %s, %s, %s, %s, %s' % (udata(default_output), udata(shift_output), udata(cmd_output), udata(alt_output), udata(altshift_output))	# Key descriptions

			output.append('\t'.join(keytable))

			if keytable[3] == 'SGCap':
				output.append('-1\t-1\t\t0\t%s\t%s\t\t\t\t\t// %s, %s' % (caps_output, shiftcaps_output, udata(caps_output), udata(shiftcaps_output)))
		return output

	def writeDeadKeyTable(self):
		# Writes a summary of dead keys, their results in all intended combinations.

		output = ['']
		for i in self.keydict.keys():
			output.extend([''])
			output.append('DEADKEY\t%s' % i)
			output.append('')

			for j in self.keydict[i]:
 				string = '%s\t%s\t// %s -> %s' % (j[0], j[1], charFromUnicode(j[0]), charFromUnicode(j[1]))
 				output.append(string)
		return output

	def writeKeynameDead(self):
		# List of dead keys contained in the keyboard layout.

		output = ['', 'KEYNAME_DEAD', '']
		for i in self.deadkeys.values():
			output.append( '%s\t"%s"' % (i, udata(i)))
		output.append('')

		if len(output) == 4:
			return ['', '']
		else:
			return output





### DATA ###

# Translating from Windows key codes to Mac key codes
winmac = { 1: 53, 2: 18, 3: 19, 4: 20, 5: 21, 6: 23, 7: 22, 8: 26, 9: 28, 10: 25, 11: 29, 12: 27, 13: 24, 14: 51, 15: 48, 16: 12, 17: 13, 18: 14, 19: 15, 20: 17, 21: 16, 22: 32, 23: 34, 24: 31, 25: 35, 26: 33, 27: 30, 28: 36, 29: 59, 30: 0, 31: 1, 32: 2, 33: 3, 34: 5, 35: 4, 36: 38, 37: 40, 38: 37, 39: 41, 40: 39, 41: 50, 42: 56, 43: 42, 44: 6, 45: 7, 46: 8, 47: 9, 48: 11, 49: 45, 50: 46, 51: 43, 52: 47, 53: 44, 54: 60, 55: 67, 56: 58, 57: 49, 58: 57, 59: 122, 60: 120, 61: 99, 62: 118, 63: 96, 64: 97, 65: 98, 66: 100, 67: 101, 68: 109, 69: 113, 70: 107, 71: 89, 72: 91, 73: 92, 74: 78, 75: 86, 76: 87, 77: 88, 78: 69, 79: 83, 80: 84, 81: 85, 82: 82, 83: 65, 86: 10, 87: 103, 88: 111}

# Windows key codes and their standard names
windata = { '02': '1', '03': '2', '04': '3', '05': '4', '06': '5', '07': '6', '08': '7', '09': '8', '0a': '9', '0b': '0', '0c': 'OEM_MINUS', '0d': 'OEM_PLUS', '10': 'Q', '11': 'W', '12': 'E', '13': 'R', '14': 'T', '15': 'Y', '16': 'U', '17': 'I', '18': 'O', '19': 'P', '1a': 'OEM_4', '1b': 'OEM_6', '1e': 'A', '1f': 'S', '20': 'D', '21': 'F', '22': 'G', '23': 'H', '24': 'J', '25': 'K', '26': 'L', '27': 'OEM_1', '28': 'OEM_7', '29': 'OEM_3', '2b': 'OEM_5', '2c': 'Z', '2d': 'X', '2e': 'C', '2f': 'V', '30': 'B', '31': 'N', '32': 'M', '33': 'OEM_COMMA', '34': 'OEM_PERIOD', '35': 'OEM_2', '39': 'SPACE', '56': 'OEM_102', '53': 'DECIMAL'}

# Keys not accounted for, as they don't have a counterpart in a Mac layout:
# '1d': 'CTRL',
# '2a': 'SHIFT',
# '36': 'Right SHIFT',
# '38': 'ALT',
# '54': 'Sys Req',

# Standard data common to all Windows keyboard layouts
keynames = ['', '', 'KEYNAME', '', '01\tEsc', '0e\tBackspace', '0f\tTab', '1c\tEnter', '1d\tCtrl', '2a\tShift', '36\t"Right Shift"', '37\t"Num *"', '38\tAlt', '39\tSpace', '3a\t"Caps Lock"', '3b\tF1', '3c\tF2', '3d\tF3', '3e\tF4', '3f\tF5', '40\tF6', '41\tF7', '42\tF8', '43\tF9', '44\tF10', '45\tPause', '46\t"Scroll Lock"', '47\t"Num 7"', '48\t"Num 8"', '49\t"Num 9"', '4a\t"Num -"', '4b\t"Num 4"', '4c\t"Num 5"', '4d\t"Num 6"', '4e\t"Num +"', '4f\t"Num 1"', '50\t"Num 2"', '51\t"Num 3"', '52\t"Num 0"', '53\t"Num Del"', '54\t"Sys Req"', '57\tF11', '58\tF12', '7c\tF13', '7d\tF14', '7e\tF15', '7f\tF16', '80\tF17', '81\tF18', '82\tF19', '83\tF20', '84\tF21', '85\tF22', '86\tF23', '87\tF24', '', 'KEYNAME_EXT', '', '1c\t"Num Enter"', '1d\t"Right Ctrl"', '35\t"Num /"', '37\t"Prnt Scrn"', '38\t"Right Alt"', '45\t"Num Lock"', '46\tBreak', '47\tHome', '48\tUp', '49\t"Page Up"', '4b\tLeft', '4d\tRight', '4f\tEnd', '50\tDown', '51\t"Page Down"', '52\tInsert', '53\tDelete', '54\t<00>', '56\tHelp', '5b\t"Left Windows"', '5c\t"Right Windows"', '5d\tApplication']

prefix = '''KBD\t%s\t"%s"\r\rCOPYRIGHT\t"(c) %s %s"\r\rCOMPANY\t"%s"\r\rLOCALENAME\t"%s"\r\rLOCALEID\t"%s"\r\rVERSION\t1.0\r\rSHIFTSTATE\r\r0\t//Column 4\r1\t//Column 5 : Shft\r2\t//Column 6 :       Ctrl\r3\t//Column 7 : Shft  Ctrl\r6\t//Column 8 :       Ctrl Alt\r7\t//Column 9 : Shft  Ctrl Alt\r\rLAYOUT\t\t;an extra '@' at the end is a dead key\r\r//SC\tVK_\t\tCap\t0\t1\t2\t3\t6\t7\r//--\t----\t\t----\t----\t----\t----\t----\t----\t----\r\r''' % (name, keyboard_name, year, company, company, locale_name, locale_id_long)

suffix = '''\rDESCRIPTIONS\r\r%s\t%s\r\rLANGUAGENAMES\r\r%s\t%s\r\rENDKBD''' % (locale_id, keyboard_name, locale_id, locale_name_long)





### HELPER FUNCTIONS ###

def readFile(path):
	# Reading a file, making list of the lines, closing the file.

	file = open(path, 'r')
	data = file.read().splitlines()
	file.close()
	return data

def uni_from_char(string):
	# Returns a 4 or 5-digit string containing the Unicode value of passed glyph.

	try:
		unistring = unicode(string, 'utf-8')
		ordstring = ord(unistring)
		return hex(ordstring)[2:].zfill(4)

		# For now, 'ligatures' (2 or more characters assigned to one key) are not supported in this conversion script.
		# Ligature support on Windows keyboards is spotty (no ligatures in Caps Lock states, for instance), and limited to four characters per key.
		# Used in very few keyboard layouts only, the decision was made to insert a placeholder character instead.

	except TypeError:
		print 'Could not convert composed character %s, inserting replacement character (%s). Sorry.' % (string, udata(replacement_char))
		return replacement_char

	except ValueError:
		print 'Could not convert composed character %s, inserting replacement character (%s). Sorry.' % (string, udata(replacement_char))
		return replacement_char

def charFromUnicode(unicodestring):
	# Returns character from a Unicode code point.

	if len(unicodestring) > 5:
		return unicodestring
	else:
		return unichr(int(unicodestring, 16))

def udata(unicodestring):
	# Returns description of characters, e.g. 'DIGIT ONE', 'EXCLAMATION MARK' etc.

	if unicodestring in ['-1', '']:
		return '<none>'
	if unicodestring.endswith('@'):
		unicodestring = unicodestring[0:-1]
	else: unicodestring = unicodestring

	try:
		return unicodedata.name(charFromUnicode(unicodestring))
	except ValueError:
		return 'PUA %s' % (unicodestring)

def new_xml(file):
	# Creates a new XML file in memory.
	# Literal Unicode entities (&#x0000;) make the XML parser choke, that's why some replacing operations are necessary.
	# Also, all literal output characters are converted to Unicode strings (0000, FFFF, 1FF23 etc).

	newxml = []
	output_line = re.compile(r'(output=[\"\'])(.+?)([\"\'])')
	uni_value = re.compile(r'&#x([a-fA-F0-9]{4,6});')
	uni_lig = re.compile(r'((&#x[a-fA-F0-9]{4};){2,})')

	for line in readFile(file):

 		if line[:5] == '<?XML':
 			line = '<?xml%s' % line[5:]
			# This avoids the parser to fail right in the first line: sometimes, files start with '<?XML' rather than '<?xml', which causes mayhem.

		if re.search(output_line, line):
			if re.search(uni_lig, line):
				print 'Could not convert composed character %s, inserting replacement character (%s). Sorry.' % (re.search(uni_lig, line).group(1), udata(replacement_char))
				line = re.sub(uni_lig, replacement_char, line)
			elif re.search(uni_value, line):
				line = re.sub(uni_value, r'\1', line)
			else:
				query = re.search(output_line, line)
				character = query.group(2)
				replacement = '%s%s%s' % (query.group(1), uni_from_char(character), query.group(3))
				line = re.sub(output_line, replacement, line)

		newxml.append(line)
	return '\r'.join(newxml)





### THE ACTUAL FUNCTION ###

def run():

	if '-u' in sys.argv:
		print __usage__
		return

	if "-h" in sys.argv:
		print __help__
		return

	if "-d" in sys.argv:
		print __doc__
		return


	inputfile = sys.argv[1]
	if inputfile.split('.')[1] != 'keylayout':
		print
		print 'Input file not recognized.'
		print 'Please use an XML-based *.keylayout file.'
		print
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
	output.extend(prefix.splitlines())
	output.extend(keyboardData.writeKeyTable())
	output.extend(keyboardData.writeDeadKeyTable())
	output.extend(keynames)
	output.extend(keyboardData.writeKeynameDead())
	output.extend(suffix.splitlines())





### FILE HANDLING ###

	# As the Windows .dll files allow for 8-digit file names only, the output file name is truncated.
	# If the input file name contains a digit (being part of a series), this digit is appended to the end of the output file name.
	# If this digit is longer than 8 digits, the script will gently ask to modify the input file name.

	# Periods and spaces in the file name are not supported; MSKLC will not build the .dll if the .klc has any. This is why they are being stripped here:

	filename = re.sub(r'[. ]', '', keyboard_name)

	digit = re.compile(r'(\d+)')
	digit_m = digit.search(filename)

	if digit_m:
		trunc = 8 - len(digit_m.group(1))
		if trunc <= 0:
			print 'Too many digits for a Windows-style (8+3) filename. Please rename the source file.'
			sys.exit()
		else:
			filename = '%s%s.klc' % (filename[:trunc], digit_m.group(1))
	else:
		filename = '%s.klc' % (filename[:8])

	outputfile = codecs.open(os.sep.join((keyboard_path,filename)), 'w', 'utf-16')
	for i in output:
 		outputfile.write(i)
 		outputfile.write(os.linesep)
	outputfile.close()

	print 'done'

if __name__ == "__main__":
	run()

