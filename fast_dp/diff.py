from __future__ import absolute_import, division, print_function

from fast_dp.image_readers import XDS_INP_to_dict

def diff(xds_inp_a, xds_inp_b):
    '''Compare the parameters in a, b; write out the differences'''

    all_keys = list(sorted(set(xds_inp_a).union(xds_inp_b)))

    for key in all_keys:
        a = xds_inp_a.get(key, '')
        b = xds_inp_b.get(key. '')
        if a == b:
            continue
        print('%s:\n\t%s\n\t%s' % (key, a, b))


if __name__ == '__main__':
    import sys

    if len(sys.argv) != 3:
        raise RuntimeError, '%s XDS.INP ../other/XDS.INP' % sys.argv[1]

    a = open(sys.argv[1]).read()
    b = open(sys.argv[2]).read()
    diff(a, b)
