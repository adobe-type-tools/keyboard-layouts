import re
import sys
import time
import unittest

from mac2winKeyboard import *


class KLTest(unittest.TestCase):

    def test_char_description(self):
        self.assertEqual(
            char_description(hex(ord('1'))), 'DIGIT ONE')
        self.assertEqual(
            char_description(hex(ord('A'))), 'LATIN CAPITAL LETTER A')
        self.assertEqual(
            char_description(hex(ord('A')) + '@'), 'LATIN CAPITAL LETTER A')
        self.assertEqual(
            char_description(hex(ord('!'))), 'EXCLAMATION MARK')
        self.assertEqual(
            char_description('-1'), '<none>')
        self.assertEqual(
            char_description(''), '<none>')
        self.assertEqual(
            char_description('E000'), 'PUA E000')

    def test_make_keyboard_name(self):
        self.assertEqual(
            make_keyboard_name('test'), 'test')
        self.assertEqual(
            make_keyboard_name('test.keylayout'), 'test')
        self.assertEqual(
            make_keyboard_name('~/Desktop/test.keylayout'), 'test')
        self.assertEqual(
            make_keyboard_name('perfect layout.keylayout'), 'perfect layout')

    def test_make_klc_filename(self):
        self.assertEqual(
            make_klc_filename('test'), 'test.klc')
        self.assertEqual(
            make_klc_filename('t.e.s.t'), 'test.klc')
        self.assertEqual(
            make_klc_filename('test test'), 'testtest.klc')
        self.assertEqual(
            make_klc_filename('test test test'), 'testtest.klc')
        self.assertEqual(
            make_klc_filename('longfilename'), 'longfile.klc')
        self.assertEqual(
            make_klc_filename('longfilename1'), 'longfi_1.klc')
        self.assertEqual(
            make_klc_filename('longfilename100'), 'long_100.klc')
        self.assertEqual(
            make_klc_filename('x1000000'), '_1000000.klc')

        with self.assertRaises(SystemExit) as cm:
            make_klc_filename('100000000')
        self.assertEqual(cm.exception.code, -1)

    def test_read_file(self):
        self.assertEqual(
            read_file(os.path.join('tests', 'dummy.txt')), ['a', 'b', 'c']
        )

    def test_verify_input_file(self):
        import argparse
        parser = argparse.ArgumentParser()
        test_file = os.path.join('tests', 'dummy.keylayout')
        non_klc_file = os.path.join('tests', 'dummy.txt')
        nonexistent_file = os.path.join('tests', 'nonexistent')
        self.assertEqual(
            verify_input_file(parser, test_file), test_file
        )

        with self.assertRaises(SystemExit) as cm:
            verify_input_file(parser, nonexistent_file)
        self.assertEqual(cm.exception.code, 2)

        with self.assertRaises(SystemExit) as cm:
            verify_input_file(parser, non_klc_file)
        self.assertEqual(cm.exception.code, 2)

    def test_get_args(self):
        with self.assertRaises(SystemExit) as cm:
            get_args([])
        self.assertEqual(cm.exception.code, 2)

    def test_filter_xml(self):
        self.assertEqual(
            filter_xml(
                os.path.join('tests', 'dummy.keylayout')),
            '\n'.join(read_file(
                os.path.join('tests', 'dummy_filtered.keylayout')))
        )

    def test_make_klc_data(self):
        input_keylayout = os.path.join('tests', 'us_test.keylayout')
        output_klc = os.path.join('tests', 'us_test.klc')
        keyboard_data = process_input_keylayout(input_keylayout)
        keyboard_name = make_keyboard_name(input_keylayout)
        with codecs.open(output_klc, 'r', 'utf-16') as raw_klc:
            klc_data = actualize_copyright_year(raw_klc.read())
        self.assertEqual(
            make_klc_data(keyboard_name, keyboard_data),
            klc_data.splitlines())

        input_keylayout = os.path.join('tests', 'dummy.keylayout')
        output_klc = os.path.join('tests', 'dummy.klc')
        keyboard_data = process_input_keylayout(input_keylayout)
        keyboard_name = make_keyboard_name(input_keylayout)
        with codecs.open(output_klc, 'r', 'utf-16') as raw_klc:
            klc_data = actualize_copyright_year(raw_klc.read())
        self.assertEqual(
            make_klc_data(keyboard_name, keyboard_data),
            klc_data.splitlines())

    def test_run(self):
        import tempfile

        for sample_keylayout in ['us_test.keylayout', 'sgcap.keylayout']:
            klc_filename = sample_keylayout.split('.')[0] + '.klc'
            temp_dir = tempfile.gettempdir()
            args = argparse.ArgumentParser()
            input_keylayout = os.path.join('tests', sample_keylayout)
            args.input = input_keylayout
            args.output_dir = temp_dir
            run(args)
            output_klc = os.path.join(temp_dir, klc_filename)
            example_klc = os.path.join('tests', klc_filename)
            with open(example_klc, 'r', encoding='utf-16') as xklc:
                example_klc_data = actualize_copyright_year(xklc.read())
            with open(output_klc, 'r', encoding='utf-16') as oklc:
                output_klc_data = oklc.read()
            self.assertEqual(example_klc_data, output_klc_data)

    def test_simplify_modifier_set(self):
        # Converts left keys to 'any' keys
        self.assertEqual(
            simplify_modifier_set({'shift', 'option', 'control'}),
            {'anyShift', 'anyOption', 'anyControl'}
        )

        # Removes optionals
        self.assertEqual(
            simplify_modifier_set(
                {'shift?', 'rightShift?', 'anyShift?', 'option?',
                 'rightOption?', 'anyOption?', 'control?',
                 'rightControl?', 'anyControl?', 'command?',
                 'caps?'}),
            set()
        )

        # Leaves right and 'any' keys unchanged
        self.assertEqual(
            simplify_modifier_set(
                {'anyShift', 'anyOption', 'anyControl',
                 'rightOption', 'rightShift', 'rightControl',
                 'command', 'caps'}),
            {'anyShift', 'anyOption', 'anyControl', 'rightOption',
             'rightShift', 'rightControl', 'command', 'caps'}
        )

    def test_get_name_of_simplified_modifier_set(self):
        # Returns the expected value for the supported modifier sets
        self.assertEqual(
            get_name_of_simplified_modifier_set(set()),
            'default'
        )
        self.assertEqual(
            get_name_of_simplified_modifier_set({'anyShift'}),
            'shift'
        )
        self.assertEqual(
            get_name_of_simplified_modifier_set({'anyOption'}),
            'alt'
        )
        self.assertEqual(
            get_name_of_simplified_modifier_set({'anyOption', 'anyShift'}),
            'altshift'
        )
        self.assertEqual(
            get_name_of_simplified_modifier_set({'command'}),
            'cmd'
        )
        self.assertEqual(
            get_name_of_simplified_modifier_set({'caps'}),
            'caps'
        )
        self.assertEqual(
            get_name_of_simplified_modifier_set({'command', 'caps'}),
            'cmdcaps'
        )
        self.assertEqual(
            get_name_of_simplified_modifier_set({'anyShift', 'caps'}),
            'shiftcaps'
        )

        # Returns None for the unsupported modifier sets
        self.assertEqual(
            get_name_of_simplified_modifier_set({'rightShift'}),
            None
        )
        self.assertEqual(
            get_name_of_simplified_modifier_set({'control'}),
            None
        )


def actualize_copyright_year(s):
    year = time.localtime()[0]
    return re.sub(r'COPYRIGHT\t\"\(c\) \d+ ', f'COPYRIGHT\t"(c) {year} ', s)


if __name__ == "__main__":
    sys.exit(unittest.main())
