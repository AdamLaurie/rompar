import os

from mrom.util import add_bool_arg

from mrom import mcs48
#from mrom import mb8623x
#from mrom import snes_

arch2d = {
    'd8041ah':  mcs48.D8041AH,
    #'mb86233':  mb8623x.MB86233,
    #'msl8042':  mcs48.MSL8042,
    #'snes_cic': snes.SnesCIC,
    #'snes_pif': snes.SnesPIF,
}

# Invert bytes as they are written to file
class InvFile(object):
    def __init__(self, f):
        self.f = f

    def flush(self):
        self.f.flush()

    def write(self, s):
        data = bytearray(s)
        # invert
        for i in xrange(len(data)):
            data[i] ^= 0xFF
        self.f.write(data)

def run(arch, fn_in, fn_out, invert=None, verbose=False):
    dc = arch2d[arch]
    f_in = open(fn_in, 'r')
    f_out = open(fn_out, "wb")
    # TODO: maybe its better to invert the input
    # There might be partial word conventions

    if invert is None:
        invert = dc.invert()
    if invert:
        f_out = InvFile(f_out)
    d = dc(f_in, f_out, verbose=verbose)
    d.txt2bin()

def list_arch():
    for a in arch2d.keys():
        print a

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Convert Mitsubishi MSL8042 ROM physical layout to binary')
    parser.add_argument('--verbose', action='store_true', help='')
    add_bool_arg(parser, '--invert', default=None, help='Default: auto')
    parser.add_argument('--arch', help='Decoder to use (required)')
    parser.add_argument('--list-arch', action='store_true', help='Extended help')
    parser.add_argument('fn_in', nargs='?', help='.txt file in')
    parser.add_argument('fn_out', nargs='?', help='.bin file out')
    args = parser.parse_args()

    if args.list_arch:
        list_arch()
    else:
        fn_out = args.fn_out
        if not fn_out:
            prefix, postfix = os.path.splitext(args.fn_in)
            if not postfix:
                raise Exception("Can't auto name output file")
            fn_out = prefix + '.bin'
        run(args.arch, args.fn_in, fn_out, invert=args.invert, verbose=args.verbose)
