mac2winKeyboard.py
=====
v 1.00, November 15, 2011

This Python script is intended for converting Mac keyboard layouts to Windows
.klc files, the input format for “[Microsoft Keyboard Layout Creator](http://msdn.microsoft.com/en-us/goglobal/bb964665.aspx)” (MSKLC).
The resulting .klc files reflect the Mac keyboard layout, and can be used in
MSKLC to compile working keyboard layouts for Windows. Should any further
modifications be desired, the .klc output files can also be edited with a text editor.

Originally created for converting a bulk of Pi font keyboard layouts, this
script proved being useful for converting other, “normal” layouts as well, 
so the decision was made to make the script publicly available.

#### Disclaimer:

This script tries to convert keyboard layouts from Mac to Windows as verbatim as
possible. Still, it is far from being a linguistically accurate tool: Some of the
niceties possible in both Mac and Win keyboard layouts are not supported; for
instance, “ligatures”. Nevertheless, it is assumed that this script will at
least help producing good base data to build on.

For now, “ligatures” (2 or more characters assigned to one key) are not
supported in this conversion script. Ligature support on Windows keyboards is
spotty (no ligatures in Caps Lock states, for instance), and limited to four
characters per key. Used in very few keyboard layouts only, the decision was
made to insert a placeholder character instead.

Also, some shift states might be dropped in the conversion. This is necessary,
as Windows only supports six shift states, two of them with reduced features.

#### Usage:

Example for converting the input file `special.keylayout` to output file `special.klc`:

	python mac2winKeyboard.py special.keylayout

No further options or triggers are needed.
The output .klc file will be generated alongside the input file, the name will
be truncated to a Windows-style 8+3-digit file name. If the original file name
contains periods and/or spaces, they are stripped, not being supported in MSKLC keyboard names.
Digits in the original keyboard name (indicating a series), are preserved in the output file
name.


#### General information and tools for creating keyboard layouts:


[Adobe Typblography blog post](http://blogs.adobe.com/typblography/2012/03/on-keyboard-layouts.html), March 2012  
[Slides and notes from ATypI presentation](http://blogs.adobe.com/typblography/files/2012/03/keyboard_layouts_annotated.pdf), September 2011  

[Ukelele](http://scripts.sil.org/ukelele), a keyboard layout editor for Mac, from SIL  
[Microsoft Keyboard Layout Creator](http://msdn.microsoft.com/en-us/goglobal/bb964665.aspx)  
[UnicodeChecker](http://earthlingsoft.net/UnicodeChecker), a Unicode exploring tool  

