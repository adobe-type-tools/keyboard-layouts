win_to_mac_keycodes = {
    1: 53,
    2: 18,
    3: 19,
    4: 20,
    5: 21,
    6: 23,
    7: 22,
    8: 26,
    9: 28,
    10: 25,
    11: 29,
    12: 27,
    13: 24,
    14: 51,
    15: 48,
    16: 12,
    17: 13,
    18: 14,
    19: 15,
    20: 17,
    21: 16,
    22: 32,
    23: 34,
    24: 31,
    25: 35,
    26: 33,
    27: 30,
    28: 36,
    29: 59,
    30: 0,
    31: 1,
    32: 2,
    33: 3,
    34: 5,
    35: 4,
    36: 38,
    37: 40,
    38: 37,
    39: 41,
    40: 39,
    41: 50,
    42: 56,
    43: 42,
    44: 6,
    45: 7,
    46: 8,
    47: 9,
    48: 11,
    49: 45,
    50: 46,
    51: 43,
    52: 47,
    53: 44,
    54: 60,
    55: 67,
    56: 58,
    57: 49,
    58: 57,
    59: 122,
    60: 120,
    61: 99,
    62: 118,
    63: 96,
    64: 97,
    65: 98,
    66: 100,
    67: 101,
    68: 109,
    69: 113,
    70: 107,
    71: 89,
    72: 91,
    73: 92,
    74: 78,
    75: 86,
    76: 87,
    77: 88,
    78: 69,
    79: 83,
    80: 84,
    81: 85,
    82: 82,
    83: 65,
    86: 10,
    87: 103,
    88: 111,
}

# Windows key codes and their standard names
win_keycodes = {
    '02': '1',
    '03': '2',
    '04': '3',
    '05': '4',
    '06': '5',
    '07': '6',
    '08': '7',
    '09': '8',
    '0a': '9',
    '0b': '0',
    '0c': 'OEM_MINUS',
    '0d': 'OEM_PLUS',
    '10': 'Q',
    '11': 'W',
    '12': 'E',
    '13': 'R',
    '14': 'T',
    '15': 'Y',
    '16': 'U',
    '17': 'I',
    '18': 'O',
    '19': 'P',
    '1a': 'OEM_4',
    '1b': 'OEM_6',
    '1e': 'A',
    '1f': 'S',
    '20': 'D',
    '21': 'F',
    '22': 'G',
    '23': 'H',
    '24': 'J',
    '25': 'K',
    '26': 'L',
    '27': 'OEM_1',
    '28': 'OEM_7',
    '29': 'OEM_3',
    '2b': 'OEM_5',
    '2c': 'Z',
    '2d': 'X',
    '2e': 'C',
    '2f': 'V',
    '30': 'B',
    '31': 'N',
    '32': 'M',
    '33': 'OEM_COMMA',
    '34': 'OEM_PERIOD',
    '35': 'OEM_2',
    '39': 'SPACE',
    '56': 'OEM_102',
    '53': 'DECIMAL',
    # Keys not accounted for, as they don't have a counterpart in a Mac layout:
    # '1d': 'CTRL',
    # '2a': 'SHIFT',
    # '36': 'Right SHIFT',
    # '38': 'ALT',
    # '54': 'Sys Req',
}

# Standard data common to all Windows keyboard layouts
klc_keynames = [
    '',
    '',
    'KEYNAME',
    '',
    '01\tEsc',
    '0e\tBackspace',
    '0f\tTab',
    '1c\tEnter',
    '1d\tCtrl',
    '2a\tShift',
    '36\t"Right Shift"',
    '37\t"Num *"',
    '38\tAlt',
    '39\tSpace',
    '3a\t"Caps Lock"',
    '3b\tF1',
    '3c\tF2',
    '3d\tF3',
    '3e\tF4',
    '3f\tF5',
    '40\tF6',
    '41\tF7',
    '42\tF8',
    '43\tF9',
    '44\tF10',
    '45\tPause',
    '46\t"Scroll Lock"',
    '47\t"Num 7"',
    '48\t"Num 8"',
    '49\t"Num 9"',
    '4a\t"Num -"',
    '4b\t"Num 4"',
    '4c\t"Num 5"',
    '4d\t"Num 6"',
    '4e\t"Num +"',
    '4f\t"Num 1"',
    '50\t"Num 2"',
    '51\t"Num 3"',
    '52\t"Num 0"',
    '53\t"Num Del"',
    '54\t"Sys Req"',
    '57\tF11',
    '58\tF12',
    '7c\tF13',
    '7d\tF14',
    '7e\tF15',
    '7f\tF16',
    '80\tF17',
    '81\tF18',
    '82\tF19',
    '83\tF20',
    '84\tF21',
    '85\tF22',
    '86\tF23',
    '87\tF24',
    '',
    'KEYNAME_EXT',
    '',
    '1c\t"Num Enter"',
    '1d\t"Right Ctrl"',
    '35\t"Num /"',
    '37\t"Prnt Scrn"',
    '38\t"Right Alt"',
    '45\t"Num Lock"',
    '46\tBreak',
    '47\tHome',
    '48\tUp',
    '49\t"Page Up"',
    '4b\tLeft',
    '4d\tRight',
    '4f\tEnd',
    '50\tDown',
    '51\t"Page Down"',
    '52\tInsert',
    '53\tDelete',
    '54\t<00>',
    '56\tHelp',
    '5b\t"Left Windows"',
    '5c\t"Right Windows"',
    '5d\tApplication']

klc_prologue_dummy = (
    '''KBD\t{}\t"{}"\r'''
    '''\r'''
    '''COPYRIGHT\t"(c) {} {}"\r'''
    '''\r'''
    '''COMPANY\t"{}"\r'''
    '''\r'''
    '''LOCALENAME\t"{}"\r'''
    '''\r'''
    '''LOCALEID\t"{}"\r'''
    '''\r'''
    '''VERSION\t1.0\r'''
    '''\r'''
    '''SHIFTSTATE\r'''
    '''\r'''
    '''0\t//Column 4\r'''
    '''1\t//Column 5 : Shft\r'''
    '''2\t//Column 6 :       Ctrl\r'''
    '''3\t//Column 7 : Shft  Ctrl\r'''
    '''6\t//Column 8 :       Ctrl Alt\r'''
    '''7\t//Column 9 : Shft  Ctrl Alt\r'''
    '''\r'''
    '''LAYOUT\t\t;an extra '@' at the end is a dead key\r'''
    '''\r'''
    '''//SC\tVK_\t\tCap\t0\t1\t2\t3\t6\t7\r'''
    '''//--\t----\t\t----\t----\t----\t----\t----\t----\t----\r'''
    '''\r'''
)
# (name, keyboard_name, year, company, company, locale_name, locale_id_long)

klc_epilogue_dummy = (
    '''DESCRIPTIONS\r'''
    '''\r'''
    '''{}\t{}\r'''
    '''\r'''
    '''LANGUAGENAMES\r'''
    '''\r'''
    '''{}\t{}\r'''
    '''\r'''
    '''ENDKBD'''
)
# (locale_id, keyboard_name, locale_id, locale_name_long)
