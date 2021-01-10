mac2winKeyboard.py
=====
v 2.00, January 10, 2021

This Python script is intended for converting Mac keyboard layouts to Windows .klc files, the input format for [Microsoft Keyboard Layout Creator]. The resulting .klc files reflect the Mac keyboard layout, and can be used in MSKLC to compile working keyboard layouts for Windows. Should any further modifications be desired, the .klc output files can also be edited with a text editor.

Originally created for converting a bulk of Pi font keyboard layouts, this script proved being useful for converting other, “normal” layouts as well, so the decision was made to make the script publicly available.


#### Disclaimer:

This script tries to convert keyboard layouts from Mac to Windows as verbatim as possible. Still, it is far from being a linguistically accurate tool: Some of the niceties possible in both Mac and Win keyboard layouts are not supported; for instance, _ligatures_ (more on ligatures below). Nevertheless, it is assumed that this script will at least help producing good base data to build on.

For now, _ligatures_ (2 or more output characters assigned to a single key) are not supported in this conversion script. Ligature support on Windows keyboards is spotty (no ligatures in Caps Lock states, for instance), and limited to four characters per key. Used in very few keyboard layouts only, the decision was made to insert a placeholder character instead.

Also, some shift states might be dropped in the conversion. This is necessary, as Windows only supports six shift states, two of them with reduced features.


#### Usage:

Example for converting the input file `special.keylayout` to output file `special.klc`:

	python mac2winKeyboard.py special.keylayout

No further options or triggers are needed. The output .klc file will be generated alongside the input file, the name will be truncated to a Windows-style 8+3-digit file name. If the original file name contains periods and/or spaces, they are stripped (not supported in MSKLC keyboard names). Digits in the original keyboard name (indicating a series), are preserved in the output file name.


#### How to create a Windows keyboard layout from a macOS keyboard layout

In Ukelele:
- create a new keyboard layot (e.g. “New from current input source”)
- (edit to your liking)
- save as .keylayout file (for example, special.keylayout)

On the command line, run the script:

	python mac2winKeyboard.py special.keylayout

A .klc file will be created in the same directory.

In MSKLC:

- open the .klc file and export it as an installable .dll (Project → Build DLL and Setup Package)

Install the Windows Keyboard Layout using the freshly-created setup file.


#### General information and tools for creating keyboard layouts:


[Blog Post], March 2012  
[Slides and notes from ATypI presentation], September 2011  

[Ukelele], a keyboard layout editor for Mac, from SIL  
[Microsoft Keyboard Layout Creator]  
[UnicodeChecker], a Unicode exploring tool  


[Microsoft Keyboard Layout Creator]: https://www.microsoft.com/en-us/download/details.aspx?id=102134  
[Slides and notes from ATypI presentation]: https://blog.typekit.com/wp-content/uploads/2012/03/keyboard_layouts_annotated.pdf
[Blog Post]: https://blog.typekit.com/2012/03/06/on-keyboard-layouts/
[Ukelele]: https://software.sil.org/ukelele/
[UnicodeChecker]: https://earthlingsoft.net/UnicodeChecker/