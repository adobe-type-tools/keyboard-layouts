__mac2winKeyboard.py__
=====
v 1.00, November 15, 2011

This Python script is intended for converting Mac keyboard layouts to Windows
.klc files, the input format for "Microsoft Keyboard Layout Creator" (MSKLC).
The resulting .klc files reflect the Mac keyboard layout, and can be used in
MSKLC to compile working keyboard layouts for Windows. Should any further
modifications be desired, the .klc files can also be edited with a text editor.

Originally created for converting a bulk of Pi font keyboard layouts, this
script proved being useful for converting other, 'normal' layouts as well, 
so the decision was made to make the script publicly available.

Disclaimer:
----

This script tries to convert keyboard layouts from Mac to Windows as verbatim as
possible. Still, it is far from a linguistically accurate tool: Some of the
niceties possible in both Mac and Win keyboard layouts are not supported; for
instance, 'ligatures'. Nevertheless, it is assumed that this script will at
least help producing good base data to be extended on.

For now, 'ligatures' (2 or more characters assigned to one key) are not
supported in this conversion script. Ligature support on Windows keyboards is
spotty (no ligatures in Caps Lock states, for instance), and limited to four
characters per key. Used in very few keyboard layouts only, the decision was
made to insert a placeholder character instead.

Also, some shift states might be dropped in the conversion. This is necessary,
as Windows only supports six shift states, two of them with reduced features.

Usage:
----

(Example for converting the input file "special.keylayout"):

	python mac2winKeyboard.py special.keylayout

No further options or triggers are needed.
The output .klc file will be generated alongside the input file, the name will
be truncated to a Windows-style 8+3-digit file name. If the original file name
contains periods and/or spaces, they are stripped, not being supported in MSKLC keyboard names.
Digits in the original keyboard name (indicating a series), are preserved in the output file
name.
