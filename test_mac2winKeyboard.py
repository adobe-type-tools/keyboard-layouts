import sys
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
        test_file = os.path.join('tests', 'unfiltered.keylayout')
        nonexistent_file = os.path.join('tests', 'nonexistent')
        self.assertEqual(
            verify_input_file(parser, test_file), test_file
        )
        self.assertRaises(
            verify_input_file(parser, nonexistent_file), 2
        )

    def test_filter_xml(self):
        self.assertEqual(
            filter_xml(
                os.path.join('tests', 'unfiltered.keylayout')),
            '\n'.join(read_file(
                os.path.join('tests', 'filtered.keylayout')))
        )

    def test_make_klc_data(self):
        input_keylayout = os.path.join('tests', 'us_test.keylayout')
        output_klc = os.path.join('tests', 'us_test.klc')
        keyboard_data = process_input_keylayout(input_keylayout)
        keyboard_name = make_keyboard_name(input_keylayout)
        with codecs.open(output_klc, 'r', 'utf-16') as raw_klc:
            klc_data = raw_klc.read()
        self.assertEqual(
            make_klc_data(keyboard_name, keyboard_data),
            klc_data.splitlines())




if __name__ == "__main__":
    sys.exit(unittest.main())
