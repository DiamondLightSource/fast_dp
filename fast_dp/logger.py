from __future__ import absolute_import, division, print_function

import os

class _writer:
    '''A specialist class to write to the screen and fast_dp.log.'''

    def __init__(self):
        self._fout = None
        self._filename = 'fast_dp.log'
        return

    def set_filename(self, filename):
        self._filename = filename

    def __del__(self):
        if self._fout:
            self._fout.close()
        self._fout = None
        return

    def __call__(self, record):
        self.write(record)

    def write(self, record):
        if not self._fout:
            self._fout = open(self._filename, 'w')

        self._fout.write('%s\n' % record)
        print(record)
        return

write = _writer()

def set_filename(filename):
    write.set_filename(filename)
