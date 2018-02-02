rompar
======

Masked ROM optical data extraction tool.

Latest version:

  https://github.com/AdamLaurie/rompar
  https://github.com/SiliconAnalysis/rompar

Original version by Adam Laurie, but significant changes by John McMaster


mrom library

Set of utilities to convert resulting .txt into binaries
The canonical image orientation should be with the row/address decode circuitry to the lower and right of the image
This makes it so that they can be optionally included in images and not effect the position
When there already exists a strong convention otherwise, note it in the decode module
Consider moving if shared between monkeys and such

Original message:

Note that this initial version is very much a quick-and-dirty 'see if this method is useful'
kind of tool. If it is, hopefully it will evolve into something pretty and elegant!

  usage: rompar.py <IMAGE> <BITS PER GROUP> <ROWS PER GROUP> [GRID FILE]

Hit 'h' when the image has focus to produce some keystroke help in the calling window.

For a walked through example, read this:

  http://adamsblog.rfidiot.org/2013/01/fun-with-masked-roms.html

Enjoy!
Adam

